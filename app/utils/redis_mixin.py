"""
Mixin providing lazy Redis connection management.

Classes that need a single lazy Redis connection should inherit from
``RedisClientMixin`` instead of duplicating the ``_get_redis`` pattern.
"""

from redis.asyncio import Redis

from app.storage.redis import get_redis_connection


class RedisClientMixin:
    """Mixin for classes that need a lazy Redis connection."""

    def __init__(self) -> None:
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis | None:
        """Return the cached Redis connection, creating it on first call."""
        if self._redis is None:
            self._redis = await get_redis_connection()
        return self._redis

    async def _close_redis(self) -> None:
        """Close and release the Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
