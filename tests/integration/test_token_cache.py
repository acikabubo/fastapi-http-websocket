"""
Tests for JWT token claim caching functionality.

This module tests the Redis-based token caching system that reduces CPU overhead
and Keycloak validation load by caching decoded JWT claims.

Test Coverage:
- Cache hit behavior (returns cached claims)
- Cache miss behavior (returns None)
- Cache TTL calculation and expiration
- Cache invalidation
- Metrics tracking (hits/misses)
- Fail-open behavior when Redis unavailable
- Token hash as cache key (security)
"""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.utils.cache_keys import CacheKeyFactory
from app.utils.token_cache import (
    TOKEN_CACHE_BUFFER_SECONDS,
    cache_token_claims,
    get_cached_token_claims,
    invalidate_token_cache,
)


@pytest.mark.asyncio
async def test_token_cache_hit():
    """Test cache returns cached claims on hit."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123", "exp": int(time.time()) + 300}

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(claims))

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        cached_claims = await get_cached_token_claims(token)

    assert cached_claims == claims

    # Verify Redis was queried with correct key
    cache_key = CacheKeyFactory.generate_with_hash("token:claims", token)
    mock_redis.get.assert_called_once_with(cache_key)


@pytest.mark.asyncio
async def test_token_cache_miss():
    """Test cache miss returns None."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        cached_claims = await get_cached_token_claims(token)

    assert cached_claims is None


@pytest.mark.asyncio
async def test_token_cache_stores_claims():
    """Test caching stores claims with correct TTL."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123", "exp": int(time.time()) + 300}

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await cache_token_claims(token, claims)

    # Verify Redis setex was called
    cache_key = CacheKeyFactory.generate_with_hash("token:claims", token)

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args[0]

    assert call_args[0] == cache_key
    assert call_args[2] == json.dumps(claims)

    # Verify TTL is token expiration minus buffer
    ttl = call_args[1]
    expected_ttl = 300 - TOKEN_CACHE_BUFFER_SECONDS
    assert expected_ttl - 2 <= ttl <= expected_ttl + 2  # Allow 2s variance


@pytest.mark.asyncio
async def test_token_cache_ttl_calculation():
    """Test cache TTL matches token expiration with buffer."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    exp_time = int(time.time()) + 600  # 10 minutes
    claims = {"sub": "user123", "exp": exp_time}

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await cache_token_claims(token, claims)

    call_args = mock_redis.setex.call_args[0]
    ttl = call_args[1]

    # TTL should be exp_time - now - buffer
    expected_ttl = 600 - TOKEN_CACHE_BUFFER_SECONDS
    assert expected_ttl - 2 <= ttl <= expected_ttl + 2


@pytest.mark.asyncio
async def test_token_cache_skip_expired():
    """Test cache skips tokens that are already expired."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {
        "sub": "user123",
        "exp": int(time.time()) - 10,  # Already expired
    }

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await cache_token_claims(token, claims)

    # setex should NOT be called for expired tokens
    mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_token_cache_invalidation():
    """Test cache invalidation deletes cached claims."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await invalidate_token_cache(token)

    # Verify Redis delete was called with correct key
    cache_key = CacheKeyFactory.generate_with_hash("token:claims", token)
    mock_redis.delete.assert_called_once_with(cache_key)


@pytest.mark.asyncio
async def test_token_cache_redis_unavailable():
    """Test cache fails gracefully when Redis unavailable."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"

    # Simulate Redis connection failure
    with patch(
        "app.utils.token_cache.get_redis_connection", return_value=None
    ):
        cached_claims = await get_cached_token_claims(token)

    # Should return None (cache miss) without raising exception
    assert cached_claims is None


@pytest.mark.asyncio
async def test_token_cache_stores_when_redis_unavailable():
    """Test cache storage fails gracefully when Redis unavailable."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123", "exp": int(time.time()) + 300}

    # Simulate Redis connection failure
    with patch(
        "app.utils.token_cache.get_redis_connection", return_value=None
    ):
        # Should not raise exception
        await cache_token_claims(token, claims)


@pytest.mark.asyncio
async def test_token_cache_redis_error():
    """Test cache handles Redis errors gracefully."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        cached_claims = await get_cached_token_claims(token)

    # Should return None without raising exception
    assert cached_claims is None


@pytest.mark.asyncio
async def test_token_cache_metrics_hit():
    """Test cache hit increments metrics counter."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123", "exp": int(time.time()) + 300}

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(claims))

    with (
        patch(
            "app.utils.token_cache.get_redis_connection",
            return_value=mock_redis,
        ),
        patch("app.utils.metrics.token_cache_hits_total") as mock_hits,
    ):
        await get_cached_token_claims(token)

    # Verify hits metric was incremented
    mock_hits.inc.assert_called_once()


@pytest.mark.asyncio
async def test_token_cache_metrics_miss():
    """Test cache miss increments metrics counter."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    with (
        patch(
            "app.utils.token_cache.get_redis_connection",
            return_value=mock_redis,
        ),
        patch("app.utils.metrics.token_cache_misses_total") as mock_misses,
    ):
        await get_cached_token_claims(token)

    # Verify misses metric was incremented
    mock_misses.inc.assert_called_once()


@pytest.mark.asyncio
async def test_token_hash_as_cache_key():
    """Test token hash (not full token) is used as cache key."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123", "exp": int(time.time()) + 300}

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await cache_token_claims(token, claims)

    # Verify cache key uses hash, not token
    expected_key = CacheKeyFactory.generate_with_hash("token:claims", token)

    call_args = mock_redis.setex.call_args[0]
    assert call_args[0] == expected_key
    assert token not in call_args[0]  # Full token NOT in key


@pytest.mark.asyncio
async def test_token_cache_custom_ttl():
    """Test caching with explicit TTL overrides token expiration."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123", "exp": int(time.time()) + 600}
    custom_ttl = 120  # 2 minutes

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await cache_token_claims(token, claims, ttl=custom_ttl)

    # Verify custom TTL was used
    call_args = mock_redis.setex.call_args[0]
    assert call_args[1] == custom_ttl


@pytest.mark.asyncio
async def test_token_cache_no_exp_claim():
    """Test caching skips tokens without exp claim."""
    token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
    claims = {"sub": "user123"}  # No exp claim

    mock_redis = AsyncMock()

    with patch(
        "app.utils.token_cache.get_redis_connection",
        return_value=mock_redis,
    ):
        await cache_token_claims(token, claims)

    # setex should NOT be called without exp claim
    mock_redis.setex.assert_not_called()
