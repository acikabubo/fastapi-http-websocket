"""
Tests for pagination count caching utilities.

This module tests Redis-based count caching for pagination performance
optimization.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.utils.pagination_cache import (
    DEFAULT_COUNT_CACHE_TTL,
    _generate_count_cache_key,
    get_cached_count,
    invalidate_count_cache,
    set_cached_count,
)


class TestGenerateCountCacheKey:
    """Tests for _generate_count_cache_key function."""

    def test_generate_key_without_filters(self):
        """Test cache key generation without filters."""
        key = _generate_count_cache_key("Author", None)
        assert key == "pagination:count:Author:all"

    def test_generate_key_with_filters(self):
        """Test cache key generation with filters."""
        filters = {"status": "active", "page": 1}
        key = _generate_count_cache_key("Author", filters)

        # Should contain model name and hash
        assert key.startswith("pagination:count:Author:")
        assert key != "pagination:count:Author:all"
        # Hash should be 8 characters
        hash_part = key.split(":")[-1]
        assert len(hash_part) == 8

    def test_generate_key_deterministic(self):
        """Test that same filters produce same key."""
        filters = {"status": "active", "page": 1}
        key1 = _generate_count_cache_key("Author", filters)
        key2 = _generate_count_cache_key("Author", filters)

        assert key1 == key2

    def test_generate_key_order_independent(self):
        """Test that filter order doesn't affect key."""
        key1 = _generate_count_cache_key(
            "Author", {"status": "active", "page": 1}
        )
        key2 = _generate_count_cache_key(
            "Author", {"page": 1, "status": "active"}
        )

        assert key1 == key2


class TestGetCachedCount:
    """Tests for get_cached_count function."""

    @pytest.mark.asyncio
    async def test_get_cached_count_hit(self):
        """Test cache hit returns cached count."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"42")

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            count = await get_cached_count("Author", {"status": "active"})

        assert count == 42
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_count_miss(self):
        """Test cache miss returns None."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            count = await get_cached_count("Author")

        assert count is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_count_redis_unavailable(self):
        """Test returns None when Redis is unavailable."""
        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=None,
        ):
            count = await get_cached_count("Author")

        assert count is None

    @pytest.mark.asyncio
    async def test_get_cached_count_handles_exception(self):
        """Test handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RedisError("Redis error"))

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            count = await get_cached_count("Author")

        assert count is None


class TestSetCachedCount:
    """Tests for set_cached_count function."""

    @pytest.mark.asyncio
    async def test_set_cached_count_success(self):
        """Test successfully caching count."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            await set_cached_count("Author", 42, {"status": "active"})

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[1] == DEFAULT_COUNT_CACHE_TTL  # Default TTL
        assert call_args[2] == "42"  # Count as string

    @pytest.mark.asyncio
    async def test_set_cached_count_custom_ttl(self):
        """Test caching with custom TTL."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            await set_cached_count("Author", 42, ttl=600)

        call_args = mock_redis.setex.call_args[0]
        assert call_args[1] == 600  # Custom TTL

    @pytest.mark.asyncio
    async def test_set_cached_count_redis_unavailable(self):
        """Test handles Redis unavailable gracefully."""
        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=None,
        ):
            # Should not raise exception
            await set_cached_count("Author", 42)

    @pytest.mark.asyncio
    async def test_set_cached_count_handles_exception(self):
        """Test handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=RedisError("Redis error"))

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            # Should not raise exception
            await set_cached_count("Author", 42)


class TestInvalidateCountCache:
    """Tests for invalidate_count_cache function."""

    @pytest.mark.asyncio
    async def test_invalidate_specific_filter(self):
        """Test invalidating specific filter combination."""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            await invalidate_count_cache("Author", {"status": "active"})

        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_all_for_model(self):
        """Test invalidating all counts for a model."""
        mock_redis = AsyncMock()
        # Simulate scan returning keys in first call, then empty
        mock_redis.scan = AsyncMock(
            side_effect=[
                (
                    0,
                    [
                        b"pagination:count:Author:key1",
                        b"pagination:count:Author:key2",
                    ],
                )
            ]
        )
        mock_redis.delete = AsyncMock(return_value=2)

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            await invalidate_count_cache("Author", None)

        mock_redis.scan.assert_called_once()
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_all_multiple_scans(self):
        """Test invalidating with multiple scan iterations."""
        mock_redis = AsyncMock()
        # First scan returns cursor 100 with keys
        # Second scan returns cursor 0 (end) with more keys
        mock_redis.scan = AsyncMock(
            side_effect=[
                (100, [b"key1", b"key2"]),
                (0, [b"key3"]),
            ]
        )
        mock_redis.delete = AsyncMock(return_value=1)

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            await invalidate_count_cache("Author", None)

        assert mock_redis.scan.call_count == 2
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_redis_unavailable(self):
        """Test handles Redis unavailable gracefully."""
        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=None,
        ):
            # Should not raise exception
            await invalidate_count_cache("Author")

    @pytest.mark.asyncio
    async def test_invalidate_handles_exception(self):
        """Test handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(side_effect=RedisError("Redis error"))

        with patch.object(
            __import__("app.storage.redis").storage.redis.RedisPool,
            "get_instance",
            return_value=mock_redis,
        ):
            # Should not raise exception
            await invalidate_count_cache("Author", {"status": "active"})
