"""
Layered cache manager with in-memory cache + Redis fallback.

Singleton manager providing two-tier caching strategy:
1. In-memory cache (L1) - Fastest access, no network latency
2. Redis cache (L2) - Shared across instances, persistent

Use cases:
- Hot keys that are accessed very frequently
- Reducing Redis network round-trips
- Improving cache hit latency

Trade-offs:
- Increased memory usage per application instance
- Cache invalidation complexity (must invalidate both layers)
- Stale data risk in multi-instance deployments

Deployment considerations:
- Single instance: Memory cache provides significant benefit
- Horizontally scaled: Use with caution (cache coherence issues)
"""

import asyncio
import json
import time
from collections import OrderedDict
from typing import Any, TypeVar

from redis.exceptions import RedisError

from app.logging import logger
from app.storage.redis import RedisPool
from app.utils.metrics.redis import (
    memory_cache_evictions_total,
    memory_cache_hits_total,
    memory_cache_misses_total,
    memory_cache_size,
)

T = TypeVar("T")


class CacheEntry:
    """
    Cache entry with value and expiration time.

    Attributes:
        value: Cached value (any JSON-serializable type).
        expires_at: Unix timestamp when entry expires (None = no expiry).
        last_accessed: Unix timestamp of last access (for LRU eviction).
    """

    __slots__ = ("value", "expires_at", "last_accessed")

    def __init__(self, value: Any, ttl: int | None = None) -> None:
        """
        Initialize cache entry.

        Args:
            value: Value to cache.
            ttl: Time-to-live in seconds (None = no expiry).
        """
        self.value = value
        self.expires_at = time.time() + ttl if ttl is not None else None
        self.last_accessed = time.time()

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Update last access time (for LRU)."""
        self.last_accessed = time.time()


class CacheManager:
    """
    Layered cache manager with in-memory (L1) + Redis (L2) tiers.

    Features:
    - Two-tier caching: memory (fast) + Redis (shared)
    - LRU eviction policy for memory cache
    - Automatic expiration handling
    - Thread-safe operations with asyncio locks
    - Prometheus metrics for monitoring

    Example:
        >>> cache = CacheManager(max_memory_entries=1000)
        >>> await cache.set("user:123", {"name": "John"}, ttl=300)
        >>> value = await cache.get("user:123")
        >>> await cache.invalidate("user:123")
    """

    def __init__(
        self,
        max_memory_entries: int = 1000,
        default_ttl: int = 300,
    ) -> None:
        """
        Initialize cache manager.

        Args:
            max_memory_entries: Maximum entries in memory cache (LRU eviction).
            default_ttl: Default TTL in seconds for cached entries.
        """
        self.max_memory_entries = max_memory_entries
        self.default_ttl = default_ttl

        # In-memory cache (L1) - OrderedDict for LRU eviction
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Lock for thread-safe memory cache access
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized CacheManager: max_memory_entries={max_memory_entries}, "
            f"default_ttl={default_ttl}s"
        )

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache (memory first, Redis fallback).

        Cache lookup order:
        1. Check in-memory cache (L1)
        2. If miss, check Redis (L2)
        3. If found in Redis, populate memory cache

        Args:
            key: Cache key to lookup.

        Returns:
            Cached value if found and not expired, None otherwise.
        """
        # Try memory cache first (L1)
        async with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]

                # Check expiration
                if entry.is_expired():
                    # Remove expired entry
                    del self._memory_cache[key]
                    memory_cache_size.set(len(self._memory_cache))
                    logger.debug(f"Memory cache expired: {key}")
                else:
                    # Cache hit - update LRU order
                    entry.touch()
                    self._memory_cache.move_to_end(key)
                    memory_cache_hits_total.inc()
                    logger.debug(f"Memory cache hit: {key}")
                    return entry.value

            memory_cache_misses_total.inc()

        # Try Redis cache (L2)
        try:
            redis = await RedisPool.get_instance()
            if redis is None:
                logger.warning("Redis unavailable, cache lookup failed")
                return None

            cached_value = await redis.get(key)
            if cached_value is not None:
                # Redis hit - deserialize and populate memory cache
                value = json.loads(cached_value)
                logger.debug(f"Redis cache hit: {key}")

                # Populate memory cache for future requests
                await self._set_memory(key, value, ttl=self.default_ttl)

                return value

            logger.debug(f"Cache miss (both tiers): {key}")
            return None

        except (RedisError, ConnectionError, json.JSONDecodeError) as ex:
            logger.error(f"Error reading from Redis cache: {ex}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set value in both memory and Redis caches.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds (None = use default_ttl).
        """
        if ttl is None:
            ttl = self.default_ttl

        # Set in memory cache (L1)
        await self._set_memory(key, value, ttl=ttl)

        # Set in Redis cache (L2)
        try:
            redis = await RedisPool.get_instance()
            if redis is None:
                logger.warning(
                    "Redis unavailable, value cached in memory only"
                )
                return

            serialized = json.dumps(value)
            await redis.setex(key, ttl, serialized)
            logger.debug(f"Cached in both tiers: {key} (TTL: {ttl}s)")

        except (RedisError, ConnectionError, TypeError) as ex:
            logger.error(f"Error writing to Redis cache: {ex}")
            # Value still cached in memory

    async def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry in both memory and Redis.

        CRITICAL: Both tiers must be invalidated to prevent stale data.

        Args:
            key: Cache key to invalidate.
        """
        # Invalidate memory cache (L1)
        async with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                memory_cache_size.set(len(self._memory_cache))
                logger.debug(f"Invalidated memory cache: {key}")

        # Invalidate Redis cache (L2)
        try:
            redis = await RedisPool.get_instance()
            if redis is None:
                logger.warning(
                    "Redis unavailable, memory cache invalidated only"
                )
                return

            deleted = await redis.delete(key)
            if deleted:
                logger.debug(f"Invalidated Redis cache: {key}")

        except (RedisError, ConnectionError) as ex:
            logger.error(f"Error invalidating Redis cache: {ex}")

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching pattern.

        Uses Redis SCAN to find matching keys. Memory cache is cleared
        entirely to avoid missing keys.

        WARNING: This operation is expensive for large key sets.

        Args:
            pattern: Redis key pattern (e.g., "user:*", "session:*").

        Returns:
            Number of keys invalidated.
        """
        # Clear entire memory cache (cannot match pattern efficiently)
        async with self._lock:
            self._memory_cache.clear()
            memory_cache_size.set(0)
            logger.info("Cleared entire memory cache (pattern invalidation)")

        # Invalidate matching keys in Redis
        try:
            redis = await RedisPool.get_instance()
            if redis is None:
                logger.warning(
                    "Redis unavailable, pattern invalidation failed"
                )
                return 0

            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await redis.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    deleted_count += await redis.delete(*keys)

                if cursor == 0:
                    break

            logger.info(
                f"Invalidated {deleted_count} keys matching pattern: {pattern}"
            )
            return deleted_count

        except (RedisError, ConnectionError) as ex:
            logger.error(f"Error invalidating pattern in Redis: {ex}")
            return 0

    async def clear(self) -> None:
        """Clear both memory and Redis caches entirely."""
        # Clear memory cache
        async with self._lock:
            self._memory_cache.clear()
            memory_cache_size.set(0)
            logger.info("Cleared memory cache")

        # Note: Redis cache is shared across instances, so we don't clear it
        # Use invalidate_pattern("*") if you really need to clear Redis

    async def _set_memory(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in memory cache with LRU eviction.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.
        """
        async with self._lock:
            # Add or update entry
            entry = CacheEntry(value, ttl=ttl)
            self._memory_cache[key] = entry
            self._memory_cache.move_to_end(key)  # Mark as most recently used

            # Evict oldest entry if cache is full (LRU)
            if len(self._memory_cache) > self.max_memory_entries:
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]
                memory_cache_evictions_total.inc()
                logger.debug(
                    f"Evicted LRU entry: {oldest_key} "
                    f"(cache size: {len(self._memory_cache)})"
                )

            memory_cache_size.set(len(self._memory_cache))

    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics.
        """
        async with self._lock:
            memory_size = len(self._memory_cache)

        return {
            "memory_cache_size": memory_size,
            "memory_cache_max": self.max_memory_entries,
            "memory_usage_percent": (
                (memory_size / self.max_memory_entries) * 100
                if self.max_memory_entries > 0
                else 0
            ),
            "default_ttl": self.default_ttl,
        }


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager(
    max_memory_entries: int = 1000,
    default_ttl: int = 300,
) -> CacheManager:
    """
    Get or create global cache manager instance (singleton).

    Args:
        max_memory_entries: Maximum entries in memory cache.
        default_ttl: Default TTL in seconds.

    Returns:
        Global CacheManager instance.
    """
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager(
            max_memory_entries=max_memory_entries,
            default_ttl=default_ttl,
        )

    return _cache_manager
