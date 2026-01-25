import asyncio
import logging
from functools import partial
from json import loads
from typing import Any, Callable

from pybreaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerListener,
    CircuitBreakerState,
)
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.constants import KC_SESSION_EXPIRY_BUFFER_SECONDS
from app.logging import logger
from app.schemas.user import UserModel
from app.settings import app_settings


class RedisCircuitBreakerListener(CircuitBreakerListener):  # type: ignore[misc]
    """
    Listener for Redis circuit breaker events.

    Tracks state changes and failures, updating Prometheus metrics.
    """

    def before_call(
        self,
        _cb: CircuitBreaker,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Called before circuit breaker calls the function."""
        pass  # No action needed before call

    def success(self, _cb: CircuitBreaker) -> None:
        """Called when circuit breaker call succeeds."""
        pass  # No action needed on success

    def failure(self, _cb: CircuitBreaker, exc: BaseException) -> None:
        """Called when circuit breaker call fails."""
        logger.error(f"Redis circuit breaker failure: {exc}")

        from app.utils.metrics import circuit_breaker_failures_total

        circuit_breaker_failures_total.labels(service="redis").inc()

    def state_change(
        self,
        _cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        """Called when circuit breaker state changes."""
        old_state_name = old_state.name if old_state else "unknown"
        new_state_name = new_state.name

        logger.warning(
            f"Redis circuit breaker state changed: "
            f"{old_state_name} → {new_state_name}"
        )

        # Lazy import to avoid circular dependency
        from app.utils.metrics import (
            circuit_breaker_state,
            circuit_breaker_state_changes_total,
        )

        # Map states to numeric values for Gauge metric
        state_mapping = {"closed": 0, "open": 1, "half_open": 2}

        circuit_breaker_state.labels(service="redis").set(
            state_mapping.get(new_state_name, 0)
        )
        circuit_breaker_state_changes_total.labels(
            service="redis",
            from_state=old_state_name,
            to_state=new_state_name,
        ).inc()


# Initialize Redis circuit breaker
redis_circuit_breaker: CircuitBreaker | None = None

if app_settings.CIRCUIT_BREAKER_ENABLED:
    redis_circuit_breaker = CircuitBreaker(
        fail_max=app_settings.REDIS_CIRCUIT_BREAKER_FAIL_MAX,
        reset_timeout=app_settings.REDIS_CIRCUIT_BREAKER_TIMEOUT,
        name="redis",
        listeners=[RedisCircuitBreakerListener()],
    )
    logger.info(
        f"Redis circuit breaker initialized "
        f"(fail_max={app_settings.REDIS_CIRCUIT_BREAKER_FAIL_MAX}, "
        f"timeout={app_settings.REDIS_CIRCUIT_BREAKER_TIMEOUT}s)"
    )

    # Initialize metrics with default values (circuit breaker starts in closed state)
    from app.utils.metrics import circuit_breaker_state

    circuit_breaker_state.labels(service="redis").set(0)  # 0 = closed
else:
    logger.info("Redis circuit breaker disabled")


class RedisPool:
    """
    Redis connection pool manager.

    Manages Redis connection instances per database index with connection pooling.
    Each database gets its own connection pool with configurable settings.
    """

    __instances: dict[int, Redis] = {}
    __pools: dict[
        int, ConnectionPool
    ] = {}  # Store pools for metrics and shutdown

    @classmethod
    async def get_instance(cls, db: int = 1) -> Redis:
        """
        Get or create a Redis instance for the specified database.

        Args:
            db: Redis database index (default: 1)

        Returns:
            Redis: Redis instance connected to the specified database
        """
        if db not in cls.__instances:
            cls.__instances[db] = await cls._create_instance(db)
        return cls.__instances[db]

    @classmethod
    async def _create_instance(cls, db: int) -> Redis:
        """
        Create a new Redis instance with connection pool.

        Args:
            db: Redis database index

        Returns:
            Redis: Configured Redis instance
        """
        pool = ConnectionPool.from_url(
            f"redis://{app_settings.REDIS_IP}:{app_settings.REDIS_PORT}",
            db=db,
            encoding="utf-8",
            decode_responses=True,
            max_connections=app_settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=app_settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=app_settings.REDIS_CONNECT_TIMEOUT,
            health_check_interval=app_settings.REDIS_HEALTH_CHECK_INTERVAL,
            retry_on_timeout=app_settings.REDIS_RETRY_ON_TIMEOUT,
        )

        # Store pool for metrics and shutdown
        cls.__pools[db] = pool

        # Update Prometheus metrics for this pool
        from app.utils.metrics import (
            redis_pool_info,
            redis_pool_max_connections,
        )

        redis_pool_max_connections.labels(db=str(db)).set(pool.max_connections)
        redis_pool_info.labels(
            db=str(db),
            host=app_settings.REDIS_IP,
            port=str(app_settings.REDIS_PORT),
            socket_timeout=str(app_settings.REDIS_SOCKET_TIMEOUT),
            connect_timeout=str(app_settings.REDIS_CONNECT_TIMEOUT),
            health_check_interval=str(
                app_settings.REDIS_HEALTH_CHECK_INTERVAL
            ),
        ).set(1)

        redis_instance = await Redis.from_pool(pool)

        # Attach helper method to Redis instance for convenience
        redis_instance.add_kc_user_session = partial(
            cls.add_kc_user_session, redis_instance
        )

        return redis_instance

    @classmethod
    async def close_all(cls) -> None:
        """
        Close all Redis connection pools gracefully.

        This should be called during application shutdown to ensure
        all connections are properly closed.
        """
        logger.info("Closing all Redis connection pools...")
        for db, pool in cls.__pools.items():
            try:
                await pool.disconnect()
                logger.info(f"Closed Redis pool for database {db}")
            except (RedisError, ConnectionError, RuntimeError) as ex:
                # RedisError: Redis operation errors
                # ConnectionError: Network issues
                # RuntimeError: Async context issues
                logger.error(
                    f"Error closing Redis pool for database {db}: {ex}"
                )

        cls.__pools.clear()
        cls.__instances.clear()
        logger.info("All Redis connection pools closed")

    @classmethod
    def get_pool_stats(cls, db: int | None = None) -> dict[str, Any]:
        """
        Get connection pool statistics for monitoring.

        Args:
            db: Specific database index, or None for all pools

        Returns:
            dict: Pool statistics including max connections and current usage
        """
        if db is not None:
            pool = cls.__pools.get(db)
            if not pool:
                return {}
            return {
                "db": db,
                "max_connections": pool.max_connections,
                "connection_kwargs": {
                    "socket_timeout": app_settings.REDIS_SOCKET_TIMEOUT,
                    "socket_connect_timeout": app_settings.REDIS_CONNECT_TIMEOUT,
                    "health_check_interval": app_settings.REDIS_HEALTH_CHECK_INTERVAL,
                },
            }

        # Return stats for all pools
        return {
            db: {  # type: ignore[misc]
                "max_connections": pool.max_connections,
                "connection_kwargs": {
                    "socket_timeout": app_settings.REDIS_SOCKET_TIMEOUT,
                    "socket_connect_timeout": app_settings.REDIS_CONNECT_TIMEOUT,
                    "health_check_interval": app_settings.REDIS_HEALTH_CHECK_INTERVAL,
                },
            }
            for db, pool in cls.__pools.items()
        }

    @classmethod
    def update_pool_metrics(cls) -> None:
        """
        Update Prometheus metrics for all Redis connection pools.

        Collects current pool statistics and updates Prometheus gauges
        for monitoring pool usage and detecting potential exhaustion.

        Should be called periodically (e.g., every 10-30 seconds) to keep
        metrics current.
        """
        from app.utils.metrics import (
            redis_pool_connections_available,
            redis_pool_connections_created_total,
            redis_pool_connections_in_use,
        )

        for db, pool in cls.__pools.items():
            db_label = str(db)

            # Get pool statistics from internal connection pool
            # Note: These are estimates based on pool's internal tracking
            try:
                # Number of connections currently checked out from pool
                in_use = len(pool._in_use_connections)

                # Total connections created (both in use and available)
                created = pool._created_connections

                # Available connections = created - in_use
                available = created - in_use

                # Update Prometheus gauges
                redis_pool_connections_in_use.labels(db=db_label).set(in_use)
                redis_pool_connections_available.labels(db=db_label).set(
                    available
                )

                # Track total created (cumulative counter)
                redis_pool_connections_created_total.labels(db=db_label).set(
                    created
                )

            except AttributeError:
                # Pool implementation may vary - fail gracefully
                logger.debug(
                    f"Could not access pool internal stats for db={db}"
                )
            except Exception as ex:  # noqa: BLE001
                logger.error(f"Error updating pool metrics for db={db}: {ex}")

    @staticmethod
    async def add_kc_user_session(r: Redis, user: UserModel) -> None:
        user_session_key = (
            app_settings.USER_SESSION_REDIS_KEY_PREFIX + user.username
        )
        await r.set(user_session_key, 1)
        await r.pexpire(
            user_session_key,
            (user.expired_seconds + KC_SESSION_EXPIRY_BUFFER_SECONDS) * 1000,
        )
        logger.debug(f"Added user session in redis for: {user.username}")


async def get_redis_connection(
    db: int = app_settings.MAIN_REDIS_DB,
) -> Redis | None:
    """
    Get Redis connection with circuit breaker protection.

    Protected by circuit breaker pattern to prevent cascading failures
    when Redis is unavailable. If circuit breaker is open, fails fast
    with CircuitBreakerError.

    Args:
        db: Redis database index

    Returns:
        Redis instance or None if connection fails
    """

    async def _get_connection() -> Redis:
        """Inner function to be protected by circuit breaker."""
        return await RedisPool.get_instance(db)

    try:
        if redis_circuit_breaker:
            return await redis_circuit_breaker.call(_get_connection)
        else:
            return await _get_connection()
    except CircuitBreakerError:
        logger.warning(f"Redis circuit breaker open, failing fast for db={db}")
        return None
    except (ConnectionError, TimeoutError, OSError) as ex:
        logger.error(f"Redis connection/network error: {ex}")
        return None
    except Exception as ex:  # noqa: BLE001
        # Catch-all for graceful degradation
        logger.error(f"Unexpected Redis error: {ex}")
        return None


async def get_auth_redis_connection() -> Redis | None:
    return await get_redis_connection(db=app_settings.AUTH_REDIS_DB)


class REventHandler:
    """
    Event handler for Redis pub/sub channels.

    Manages subscriptions and callbacks for Redis pub/sub messages.
    """

    @staticmethod
    def get_logger() -> logging.Logger:
        return logging.getLogger(REventHandler.__name__)

    def __init__(self, redis: Redis, channel: str) -> None:
        self.channel = channel
        self.redis = redis
        self.rch: Any = None
        self.callbacks: list[tuple[Callable[..., Any], dict[str, Any]]] = []

    def add_callback(
        self, callback: tuple[Callable[..., Any], dict[str, Any]]
    ) -> None:
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    async def handle(self, ch_name: str, data: str) -> None:
        for callback, kw in self.callbacks:
            try:
                await callback(ch_name, loads(data), **kw)
            except (ValueError, TypeError) as ex:
                # ValueError: JSON decode error
                # TypeError: Invalid callback arguments
                self.get_logger().error(f"Callback {callback} failed: {ex}")
                break
            except Exception as ex:  # noqa: BLE001
                # Catch-all for callback errors (don't fail the loop)
                self.get_logger().error(
                    f"Unexpected error in callback {callback}: {ex}"
                )
                break

    async def loop(self) -> None:
        self.get_logger().info(f"Started REventHandler for {self.channel}")
        while True:
            try:
                if self.rch is None:
                    self.rch = self.redis.pubsub()
                    await self.rch.subscribe(self.channel)

                msg = await self.rch.get_message(
                    ignore_subscribe_messages=True, timeout=1
                )
                if msg:
                    await self.handle(msg["channel"], msg["data"])
            except asyncio.CancelledError:
                self.get_logger().info(
                    f"REventHandler on {self.channel} cancelled!"
                )
                break
            except (RedisError, ConnectionError, TimeoutError) as ex:
                # RedisError: Redis operation errors
                # ConnectionError: Network issues
                # TimeoutError: Message timeout
                self.get_logger().error(
                    f"Error in REventHandler {self.channel}: {ex}"
                )
                await asyncio.sleep(0.5)


class RedisHandler:
    """
    Handler for Redis pub/sub subscriptions.

    Manages multiple Redis event handlers and their associated tasks for
    subscribing to and processing messages from Redis channels.
    """

    event_handlers: dict[str, REventHandler] = {}
    tasks: list[asyncio.Task[None]] = []

    async def subscribe(
        self, channel: str, callback: Callable[..., Any], **kwargs: Any
    ) -> None:
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback argument must be a coroutine")

        if channel not in self.event_handlers:
            redis = await get_redis_connection()
            if redis is None:
                raise RuntimeError("Failed to get Redis connection")
            handler = REventHandler(redis, channel)

            self.event_handlers[channel] = handler
            self.tasks.append(asyncio.create_task(handler.loop()))

        self.event_handlers[channel].add_callback((callback, kwargs))


class RRedis(RedisHandler):
    """
    Redis handler for pub/sub operations.

    Note: This class is instantiated as a module-level singleton (r_redis) below.
    Import and use r_redis instead of creating new instances.
    """

    pass


# Module-level singleton instance
r_redis = RRedis()
