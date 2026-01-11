"""
Chaos tests for Redis failure scenarios.

Tests application resilience when Redis is unavailable or fails.

Run with: pytest tests/chaos/test_redis_failures.py -v -m chaos
"""

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.utils.rate_limiter import ConnectionLimiter, RateLimiter

# Mark all tests in this module as chaos tests
pytestmark = pytest.mark.chaos


class TestRedisConnectionFailures:
    """Tests for Redis connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_unavailable(self):
        """Test rate limiter behavior when Redis is completely unavailable."""
        limiter = RateLimiter()

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=None),
        ):
            # Rate limiter should fail open (allow requests)
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            assert is_allowed is True, (
                "Should allow requests when Redis unavailable"
            )
            assert remaining == 10, (
                "Remaining should be limit when Redis unavailable (fail-open)"
            )

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_timeout(self):
        """Test rate limiter when Redis operations timeout."""
        limiter = RateLimiter()

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(
            side_effect=RedisTimeoutError("Connection timeout")
        )

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            # Should handle timeout gracefully
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Fail-open behavior (default)
            assert is_allowed is True, "Should allow on timeout"
            assert remaining == 10, (
                "Remaining should be limit on timeout (fail-open)"
            )

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_connection_error(self):
        """Test rate limiter when Redis connection drops mid-operation."""
        limiter = RateLimiter()

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(
            side_effect=RedisConnectionError("Connection lost")
        )

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            # Should handle connection error gracefully
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Fail-open behavior (default)
            assert is_allowed is True, "Should allow on connection error"
            assert remaining == 10, (
                "Remaining should be limit on error (fail-open)"
            )

    @pytest.mark.asyncio
    async def test_connection_limiter_redis_unavailable(self):
        """Test connection limiter when Redis is unavailable."""
        limiter = ConnectionLimiter()

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=None),
        ):
            # Should deny connection when Redis unavailable (fail-closed for security)
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # In fail-closed mode (security), should deny
            assert result is False, (
                "Should deny connections when Redis unavailable (fail-closed)"
            )

    @pytest.mark.asyncio
    async def test_connection_limiter_redis_error_during_check(self):
        """Test connection limiter when Redis errors during connection check."""
        limiter = ConnectionLimiter()

        mock_redis = AsyncMock()
        mock_redis.scard = AsyncMock(
            side_effect=RedisError("Redis internal error")
        )

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            # Should handle error gracefully
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # Fail-closed: deny connection on Redis error (security)
            assert result is False, "Should deny on Redis error (fail-closed)"


class TestRedisPartialFailures:
    """Tests for partial Redis operation failures."""

    @pytest.mark.asyncio
    async def test_rate_limiter_zremrangebyscore_succeeds_expire_fails(self):
        """Test rate limiter when ZREMRANGEBYSCORE succeeds but EXPIRE fails."""
        limiter = RateLimiter()

        mock_redis = AsyncMock()
        # Sorted set operations succeed
        mock_redis.zremrangebyscore = AsyncMock(return_value=0)
        mock_redis.zcard = AsyncMock(return_value=0)  # No requests in window
        mock_redis.zadd = AsyncMock(return_value=1)
        # EXPIRE fails
        mock_redis.expire = AsyncMock(
            side_effect=RedisError("EXPIRE command failed")
        )

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            # Should still process the request even if EXPIRE fails
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Operations worked, so rate limit check should fail-open
            assert is_allowed is True, "Should allow when EXPIRE fails"
            assert remaining == 10, "Should return full limit on error"

    @pytest.mark.asyncio
    async def test_connection_limiter_sadd_succeeds_expire_fails(self):
        """Test connection limiter when SADD succeeds but EXPIRE fails."""
        limiter = ConnectionLimiter()

        mock_redis = AsyncMock()
        mock_redis.scard = AsyncMock(return_value=0)  # No existing connections
        mock_redis.sadd = AsyncMock(return_value=1)  # Add succeeds
        mock_redis.expire = AsyncMock(
            side_effect=RedisError("EXPIRE failed")
        )  # Expire fails

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            # Should still add connection even if EXPIRE fails
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            assert result is False, (
                "Should deny connection when EXPIRE fails (fail-closed)"
            )
            mock_redis.sadd.assert_called_once()


class TestRedisIntermittentFailures:
    """Tests for intermittent Redis failures and recovery."""

    @pytest.mark.asyncio
    async def test_rate_limiter_recovers_from_intermittent_failures(self):
        """Test rate limiter recovers when Redis becomes available again."""
        limiter = RateLimiter()

        # First call: Redis fails
        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=None),
        ):
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            assert is_allowed is True, (
                "Should fail-open when Redis unavailable"
            )
            assert remaining == 10, (
                "Remaining should be limit when unavailable"
            )

        # Second call: Redis recovers
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(return_value=0)
        mock_redis.zcard = AsyncMock(return_value=0)  # No requests yet
        mock_redis.zadd = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Should work normally when Redis recovers
            assert is_allowed is True
            assert remaining == 9  # 10 - 1 (current request) = 9
            mock_redis.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_limiter_handles_flapping_redis(self):
        """Test connection limiter with flapping Redis (up/down/up)."""
        # Round 1: Redis available
        mock_redis_1 = AsyncMock()
        mock_redis_1.scard = AsyncMock(return_value=0)
        mock_redis_1.sadd = AsyncMock(return_value=1)
        mock_redis_1.expire = AsyncMock(return_value=True)

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis_1),
        ):
            limiter1 = ConnectionLimiter()
            result1 = await limiter1.add_connection("user1", "conn1")
            assert result1 is True

        # Round 2: Redis fails (new limiter instance to avoid caching)
        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=None),
        ):
            limiter2 = ConnectionLimiter()
            result2 = await limiter2.add_connection("user1", "conn2")
            assert result2 is False, (
                "Should fail-closed when Redis unavailable (security)"
            )

        # Round 3: Redis recovers (new limiter instance)
        mock_redis_3 = AsyncMock()
        mock_redis_3.scard = AsyncMock(
            return_value=2
        )  # Simulates 2 connections
        mock_redis_3.sadd = AsyncMock(return_value=1)
        mock_redis_3.expire = AsyncMock(return_value=True)

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis_3),
        ):
            limiter3 = ConnectionLimiter()
            result3 = await limiter3.add_connection("user1", "conn3")
            assert result3 is True  # Should work again
