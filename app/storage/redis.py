import asyncio
import logging
from functools import partial
from json import loads

from redis.asyncio import ConnectionPool, Redis

from app.logging import logger
from app.schemas.user import UserModel
from app.settings import app_settings
from app.utils.singleton import SingletonMeta


class RedisPool:
    """
    Redis connection pool manager.

    Manages Redis connection instances per database index with connection pooling.
    Each database gets its own connection pool with configurable settings.
    """

    __instances = {}
    __pools = {}  # Store pools for metrics and shutdown

    @classmethod
    async def get_instance(cls, db=1):
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
    async def _create_instance(cls, db):
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
        from app.utils.metrics import redis_pool_info, redis_pool_max_connections

        redis_pool_max_connections.labels(db=str(db)).set(pool.max_connections)
        redis_pool_info.labels(
            db=str(db),
            host=app_settings.REDIS_IP,
            port=str(app_settings.REDIS_PORT),
            socket_timeout=str(app_settings.REDIS_SOCKET_TIMEOUT),
            connect_timeout=str(app_settings.REDIS_CONNECT_TIMEOUT),
            health_check_interval=str(app_settings.REDIS_HEALTH_CHECK_INTERVAL),
        ).set(1)

        redis_instance = await Redis.from_pool(pool)

        # Attach helper method to Redis instance for convenience
        redis_instance.add_kc_user_session = partial(
            cls.add_kc_user_session, redis_instance
        )

        return redis_instance

    @classmethod
    async def close_all(cls):
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
            except Exception as ex:
                logger.error(f"Error closing Redis pool for database {db}: {ex}")

        cls.__pools.clear()
        cls.__instances.clear()
        logger.info("All Redis connection pools closed")

    @classmethod
    def get_pool_stats(cls, db: int | None = None) -> dict:
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
            db: {
                "max_connections": pool.max_connections,
                "connection_kwargs": {
                    "socket_timeout": app_settings.REDIS_SOCKET_TIMEOUT,
                    "socket_connect_timeout": app_settings.REDIS_CONNECT_TIMEOUT,
                    "health_check_interval": app_settings.REDIS_HEALTH_CHECK_INTERVAL,
                },
            }
            for db, pool in cls.__pools.items()
        }

    @staticmethod
    async def add_kc_user_session(r: Redis, user: UserModel):
        user_session_key = (
            app_settings.USER_SESSION_REDIS_KEY_PREFIX + user.username
        )
        await r.set(user_session_key, 1)
        await r.pexpire(user_session_key, (user.expired_seconds + 10) * 1000)
        logger.debug(f"Added user session in redis for: {user.username}")


async def get_redis_connection(db=app_settings.MAIN_REDIS_DB):
    try:
        return await RedisPool.get_instance(db)
    except (ConnectionError, TimeoutError, OSError) as ex:
        logger.error(f"Redis connection/network error: {ex}")
        return None
    except Exception as ex:
        # Catch-all for graceful degradation
        logger.error(f"Unexpected Redis error: {ex}")
        return None


async def get_auth_redis_connection():
    return await get_redis_connection(db=app_settings.AUTH_REDIS_DB)


class REventHandler:
    """
    Event handler for Redis pub/sub channels.

    Manages subscriptions and callbacks for Redis pub/sub messages.
    """

    @staticmethod
    def get_logger():
        return logging.getLogger(REventHandler.__name__)

    def __init__(self, redis, channel):
        self.channel = channel
        self.redis = redis
        self.rch = None
        self.callbacks = []

    def add_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    async def handle(self, ch_name, data):
        for callback, kw in self.callbacks:
            try:
                await callback(ch_name, loads(data), **kw)
            except Exception as ex:
                self.get_logger().error(f"Callback {callback} failed: {ex}")
                break

    async def loop(self):
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
            except Exception as ex:
                self.get_logger().error(
                    f"Error in REventHandler {self.channel}: {ex}"
                )
                await asyncio.sleep(0.5)


class RedisHandler(object):
    """
    Handler for Redis pub/sub subscriptions.

    Manages multiple Redis event handlers and their associated tasks for
    subscribing to and processing messages from Redis channels.
    """

    event_handlers = {}
    tasks = []

    async def subscribe(self, channel, callback, **kwargs):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback argument must be a coroutine")

        if channel not in self.event_handlers:
            redis = await get_redis_connection()
            handler = REventHandler(redis, channel)

            self.event_handlers[channel] = handler
            self.tasks.append(asyncio.create_task(handler.loop()))

        self.event_handlers[channel].add_callback((callback, kwargs))


class RRedis(RedisHandler, metaclass=SingletonMeta):
    """Singleton Redis handler for pub/sub operations."""

    pass
