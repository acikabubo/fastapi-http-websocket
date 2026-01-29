"""
Tests for layered cache manager (memory + Redis).

Tests cover:
- Basic get/set/invalidate operations
- Two-tier caching (memory L1 + Redis L2)
- LRU eviction policy
- TTL expiration
- Pattern-based invalidation
- Cache statistics
- Singleton pattern
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.managers.cache_manager import (
    CacheEntry,
    CacheManager,
    get_cache_manager,
)


class TestCacheEntry:
    """Tests for CacheEntry class."""

    def test_cache_entry_with_ttl(self) -> None:
        """Test cache entry with TTL."""
        entry = CacheEntry("test_value", ttl=60)

        assert entry.value == "test_value"
        assert entry.expires_at is not None
        assert not entry.is_expired()

    def test_cache_entry_without_ttl(self) -> None:
        """Test cache entry without TTL (no expiration)."""
        entry = CacheEntry("test_value", ttl=None)

        assert entry.value == "test_value"
        assert entry.expires_at is None
        assert not entry.is_expired()

    def test_cache_entry_expiration(self) -> None:
        """Test cache entry expiration."""
        # Create entry with 1 second TTL
        entry = CacheEntry("test_value", ttl=1)

        # Not expired yet
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(1.1)

        # Now expired
        assert entry.is_expired()

    def test_cache_entry_touch(self) -> None:
        """Test updating last access time."""
        entry = CacheEntry("test_value")
        original_time = entry.last_accessed

        # Wait a bit
        time.sleep(0.1)

        # Touch entry
        entry.touch()

        # Last accessed time should be updated
        assert entry.last_accessed > original_time


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def cache_manager(self) -> CacheManager:
        """Create cache manager instance for testing."""
        return CacheManager(max_memory_entries=3, default_ttl=300)

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        """Create mock Redis connection."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()
        redis.delete = AsyncMock(return_value=1)
        redis.scan = AsyncMock(return_value=(0, []))
        return redis

    async def test_set_and_get_memory_cache(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test setting and getting from memory cache (L1)."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set value
            await cache_manager.set("key1", "value1", ttl=300)

            # Get value (should hit memory cache)
            value = await cache_manager.get("key1")

            assert value == "value1"
            # Redis get should not be called (memory cache hit)
            mock_redis.get.assert_not_called()

    async def test_redis_fallback(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test Redis fallback when memory cache misses (L2)."""
        # Mock Redis to return a value
        mock_redis.get = AsyncMock(return_value='{"name": "John"}')

        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Get value (memory miss, Redis hit)
            value = await cache_manager.get("user:123")

            assert value == {"name": "John"}
            # Redis get should be called
            mock_redis.get.assert_called_once_with("user:123")

    async def test_cache_miss_both_tiers(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test cache miss in both memory and Redis."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Get non-existent key
            value = await cache_manager.get("nonexistent")

            assert value is None
            # Redis get should be called
            mock_redis.get.assert_called_once_with("nonexistent")

    async def test_lru_eviction(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test LRU eviction when cache is full."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set 3 entries (max capacity)
            await cache_manager.set("key1", "value1")
            await cache_manager.set("key2", "value2")
            await cache_manager.set("key3", "value3")

            # Memory cache should have 3 entries
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 3

            # Set 4th entry (should evict oldest - key1)
            await cache_manager.set("key4", "value4")

            # Memory cache should still have 3 entries
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 3

            # key1 should be evicted from memory
            # (will fallback to Redis if we try to get it)
            value = await cache_manager.get("key1")
            # Since Redis mock returns None, this will be None
            assert value is None

            # key4 should be in memory
            mock_redis.get.reset_mock()
            value = await cache_manager.get("key4")
            assert value == "value4"
            # Should not call Redis (memory hit)
            mock_redis.get.assert_not_called()

    async def test_ttl_expiration(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test TTL expiration in memory cache."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set value with 1 second TTL
            await cache_manager.set("key1", "value1", ttl=1)

            # Immediately get value (should be present)
            value = await cache_manager.get("key1")
            assert value == "value1"

            # Wait for expiration
            await asyncio.sleep(1.1)

            # Get expired value (should return None)
            # Memory cache will detect expiration and remove entry
            value = await cache_manager.get("key1")
            assert value is None

    async def test_invalidate(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test cache invalidation (both tiers)."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set value
            await cache_manager.set("key1", "value1")

            # Verify it's in cache
            value = await cache_manager.get("key1")
            assert value == "value1"

            # Invalidate
            await cache_manager.invalidate("key1")

            # Should be removed from memory
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 0

            # Redis delete should be called
            mock_redis.delete.assert_called_once_with("key1")

    async def test_invalidate_pattern(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test pattern-based invalidation."""
        # Mock Redis scan to return matching keys
        mock_redis.scan = AsyncMock(
            return_value=(0, [b"session:user:123", b"session:user:456"])
        )
        mock_redis.delete = AsyncMock(return_value=2)

        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set some values in memory cache
            await cache_manager.set("session:user:123", {"id": 123})
            await cache_manager.set("other:key", "value")

            # Invalidate pattern
            deleted_count = await cache_manager.invalidate_pattern("session:*")

            # Entire memory cache should be cleared
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 0

            # Redis scan and delete should be called
            mock_redis.scan.assert_called()
            assert deleted_count == 2

    async def test_clear_memory_cache(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test clearing memory cache."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set multiple values
            await cache_manager.set("key1", "value1")
            await cache_manager.set("key2", "value2")
            await cache_manager.set("key3", "value3")

            # Clear cache
            await cache_manager.clear()

            # Memory cache should be empty
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 0

    async def test_get_stats(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test cache statistics."""
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Initially empty
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 0
            assert stats["memory_cache_max"] == 3
            assert stats["memory_usage_percent"] == 0.0
            assert stats["default_ttl"] == 300

            # Add 2 entries
            await cache_manager.set("key1", "value1")
            await cache_manager.set("key2", "value2")

            # Check stats
            stats = await cache_manager.get_stats()
            assert stats["memory_cache_size"] == 2
            assert stats["memory_usage_percent"] == pytest.approx(
                66.67, rel=0.1
            )

    async def test_redis_unavailable_graceful_degradation(
        self, cache_manager: CacheManager
    ) -> None:
        """Test graceful degradation when Redis is unavailable."""
        # Mock RedisPool to return None (Redis unavailable)
        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=None,
        ):
            # Set should still work (memory only)
            await cache_manager.set("key1", "value1")

            # Get should work from memory
            value = await cache_manager.get("key1")
            assert value == "value1"

            # Invalidate should work (memory only)
            await cache_manager.invalidate("key1")

            # Value should be gone
            value = await cache_manager.get("key1")
            assert value is None

    async def test_redis_error_handling(
        self, cache_manager: CacheManager, mock_redis: AsyncMock
    ) -> None:
        """Test error handling for Redis operations."""
        from redis.exceptions import RedisError

        # Mock Redis to raise error
        mock_redis.get = AsyncMock(side_effect=RedisError("Connection failed"))
        mock_redis.setex = AsyncMock(
            side_effect=RedisError("Connection failed")
        )

        with patch(
            "app.managers.cache_manager.RedisPool.get_instance",
            return_value=mock_redis,
        ):
            # Set should not crash (memory cache still works)
            await cache_manager.set("key1", "value1")

            # Get from memory should work
            value = await cache_manager.get("key1")
            assert value == "value1"

            # Get non-existent key should return None (not crash)
            value = await cache_manager.get("key2")
            assert value is None


class TestCacheManagerSingleton:
    """Tests for CacheManager singleton pattern."""

    def test_singleton_pattern(self) -> None:
        """Test that get_cache_manager returns same instance."""
        # Reset global instance
        import app.managers.cache_manager as cm

        cm._cache_manager = None

        # First call creates instance
        cache1 = get_cache_manager(max_memory_entries=100)

        # Second call returns same instance
        cache2 = get_cache_manager(max_memory_entries=200)

        # Should be same instance
        assert cache1 is cache2

        # Configuration from first call is used
        assert cache1.max_memory_entries == 100

    def test_singleton_configuration(self) -> None:
        """Test singleton configuration."""
        # Reset global instance
        import app.managers.cache_manager as cm

        cm._cache_manager = None

        # Create with custom configuration
        cache = get_cache_manager(
            max_memory_entries=500,
            default_ttl=600,
        )

        assert cache.max_memory_entries == 500
        assert cache.default_ttl == 600
