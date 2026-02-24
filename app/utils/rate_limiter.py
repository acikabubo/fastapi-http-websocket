"""
Redis-based rate limiter using sliding window algorithm.

This module provides rate limiting functionality for both HTTP and WebSocket
connections using Redis as the backend storage.
"""

import time

from redis.asyncio import RedisError as AsyncRedisError
from redis.exceptions import RedisError as SyncRedisError

from app.logging import logger
from app.settings import app_settings
from app.utils.redis_mixin import RedisClientMixin
from app.utils.redis_safe import redis_safe


class RateLimiter(RedisClientMixin):
    """
    Redis-based rate limiter using sliding window algorithm.

    Tracks request counts per user within a time window and enforces
    configurable rate limits.
    """

    def __init__(self) -> None:
        """Initialize the rate limiter with Redis connection."""
        super().__init__()
        self.enabled = app_settings.RATE_LIMIT_ENABLED

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
        burst: int | None = None,
    ) -> tuple[bool, int]:
        """
        Check if a request is within rate limits using sliding window.

        Args:
            key: Unique identifier for the rate limit (e.g., user_id, IP).
            limit: Maximum number of requests allowed in the window.
            window_seconds: Time window in seconds (default: 60).
            burst: Optional burst limit for short-term spikes.

        Returns:
            Tuple of (is_allowed, remaining_requests).

        Raises:
            Exception: If Redis connection fails.

        Examples:
            >>> # Basic rate limiting (60 requests per minute)
            >>> limiter = RateLimiter()
            >>> is_allowed, remaining = await limiter.check_rate_limit(
            ...     key="user:123", limit=60, window_seconds=60
            ... )
            >>> if not is_allowed:
            ...     raise HTTPException(429, "Rate limit exceeded")
            >>> print(f"Remaining requests: {remaining}")

            >>> # With burst allowance for traffic spikes
            >>> is_allowed, remaining = await limiter.check_rate_limit(
            ...     key="ip:192.168.1.1",
            ...     limit=100,
            ...     window_seconds=60,
            ...     burst=20,  # Allow 120 total (100 + 20 burst)
            ... )

            >>> # Different windows for different actions
            >>> # Login attempts: 5 per minute
            >>> is_allowed, remaining = await limiter.check_rate_limit(
            ...     key="login:user123", limit=5, window_seconds=60
            ... )
            >>> # API calls: 1000 per hour
            >>> is_allowed, remaining = await limiter.check_rate_limit(
            ...     key="api:user123", limit=1000, window_seconds=3600
            ... )

            >>> # Per-endpoint rate limiting
            >>> endpoint = "/api/expensive-operation"
            >>> is_allowed, remaining = await limiter.check_rate_limit(
            ...     key=f"endpoint:{endpoint}:user:123",
            ...     limit=10,
            ...     window_seconds=60,
            ... )
        """
        if not self.enabled:
            return True, limit

        try:
            redis = await self._get_redis()
            if redis is None:
                logger.error("Redis connection not available")
                return True, limit  # Fail open

            redis_key = f"rate_limit:{key}"
            current_time = time.time()
            window_start = current_time - window_seconds

            # Remove old entries outside the time window
            await redis.zremrangebyscore(redis_key, 0, window_start)

            # Count requests in current window
            request_count = await redis.zcard(redis_key)

            # Check burst limit if configured
            effective_limit = min(burst, limit) if burst else limit

            if request_count >= effective_limit:
                remaining = 0
                return False, remaining

            # Add current request with timestamp as score
            await redis.zadd(redis_key, {str(current_time): current_time})

            # Set expiration on the key to auto-cleanup
            await redis.expire(redis_key, window_seconds * 2)

            remaining = effective_limit - request_count - 1
            return True, remaining

        except (AsyncRedisError, SyncRedisError) as ex:
            logger.error(f"Redis error for rate limit key {key}: {ex}")
            # Respect configured fail mode for rate limiting
            if app_settings.RATE_LIMIT_FAIL_MODE == "closed":
                logger.warning(
                    f"Rate limiter failing closed due to Redis error for key {key}"
                )
                return False, 0  # Deny request
            # Default: fail open to prevent service disruption
            return True, limit  # Allow request
        except (ValueError, TypeError) as ex:
            logger.error(f"Invalid parameters for rate limit key {key}: {ex}")
            # Programming error - fail closed
            return False, 0

    @redis_safe(fail_value=None, operation_name="reset_rate_limit")
    async def reset_limit(self, key: str) -> None:
        """
        Reset rate limit for a specific key.

        Args:
            key: The rate limit key to reset.
        """
        redis = await self._get_redis()
        if redis is None:
            logger.error("Redis connection not available")
            return
        redis_key = f"rate_limit:{key}"
        await redis.delete(redis_key)


class ConnectionLimiter(RedisClientMixin):
    """
    Manages per-user connection limits for WebSocket connections.

    Tracks active connections per user and enforces maximum connection limits.
    """

    def __init__(self) -> None:
        """Initialize the connection limiter with Redis connection."""
        super().__init__()
        self.max_connections = app_settings.WS_MAX_CONNECTIONS_PER_USER

    @redis_safe(fail_value=False, operation_name="add_ws_connection")
    async def add_connection(self, user_id: str, connection_id: str) -> bool:
        """
        Add a new connection for a user.

        Args:
            user_id: The unique user identifier.
            connection_id: Unique identifier for this connection.

        Returns:
            True if connection was added, False if limit exceeded.
        """
        redis = await self._get_redis()
        if redis is None:
            logger.error("Redis connection not available")
            return False

        redis_key = f"ws_connections:{user_id}"

        # Get current connection count
        connection_count = await redis.scard(redis_key)

        if connection_count >= self.max_connections:
            logger.warning(
                f"User {user_id} exceeded max connections limit "
                f"({self.max_connections})"
            )
            return False

        # Add connection to set
        await redis.sadd(redis_key, connection_id)

        # Set expiration (cleanup stale connections)
        await redis.expire(redis_key, 3600)  # 1 hour

        logger.info(
            f"Added connection {connection_id} for user {user_id}. "
            f"Total: {connection_count + 1}/{self.max_connections}"
        )
        return True

    @redis_safe(fail_value=None, operation_name="remove_ws_connection")
    async def remove_connection(
        self, user_id: str, connection_id: str
    ) -> None:
        """
        Remove a connection for a user.

        Args:
            user_id: The unique user identifier.
            connection_id: Unique identifier for the connection to remove.
        """
        redis = await self._get_redis()
        if redis is None:
            logger.error("Redis connection not available")
            return

        redis_key = f"ws_connections:{user_id}"
        await redis.srem(redis_key, connection_id)
        logger.info(f"Removed connection {connection_id} for user {user_id}")

    @redis_safe(fail_value=0, operation_name="get_ws_connection_count")
    async def get_connection_count(self, user_id: str) -> int:
        """
        Get the current number of connections for a user.

        Args:
            user_id: The unique user identifier.

        Returns:
            Number of active connections for the user.
        """
        redis = await self._get_redis()
        if redis is None:
            logger.error("Redis connection not available")
            return 0

        redis_key = f"ws_connections:{user_id}"
        return await redis.scard(redis_key)


# Singleton instances
rate_limiter = RateLimiter()
connection_limiter = ConnectionLimiter()
