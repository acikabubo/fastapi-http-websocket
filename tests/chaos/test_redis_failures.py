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
            "app.utils.rate_limiter.get_main_redis_connection"
        ) as mock_get_redis:
            mock_get_redis.return_value = None  # Redis connection failed

            # Rate limiter should fail open (allow requests)
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            assert is_allowed is True, (
                "Should allow requests when Redis unavailable"
            )
            assert remaining == 0, (
                "Remaining should be 0 when Redis unavailable"
            )

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_timeout(self):
        """Test rate limiter when Redis operations timeout."""
        limiter = RateLimiter()

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(
            side_effect=RedisTimeoutError("Connection timeout")
        )

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis,
        ):
            # Should handle timeout gracefully
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Fail-open behavior
            assert is_allowed is True, "Should allow on timeout"
            assert remaining == 0, "Remaining should be 0 on timeout"

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_connection_error(self):
        """Test rate limiter when Redis connection drops mid-operation."""
        limiter = RateLimiter()

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(
            side_effect=RedisConnectionError("Connection lost")
        )

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis,
        ):
            # Should handle connection error gracefully
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Fail-open behavior
            assert is_allowed is True, "Should allow on connection error"

    @pytest.mark.asyncio
    async def test_connection_limiter_redis_unavailable(self):
        """Test connection limiter when Redis is unavailable."""
        limiter = ConnectionLimiter(max_connections=5)

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection"
        ) as mock_get_redis:
            mock_get_redis.return_value = None

            # Should allow connection when Redis unavailable (fail-open)
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # In fail-open mode, should allow
            assert result is True, (
                "Should allow connections when Redis unavailable"
            )

    @pytest.mark.asyncio
    async def test_connection_limiter_redis_error_during_check(self):
        """Test connection limiter when Redis errors during connection check."""
        limiter = ConnectionLimiter(max_connections=5)

        mock_redis = AsyncMock()
        mock_redis.scard = AsyncMock(
            side_effect=RedisError("Redis internal error")
        )

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis,
        ):
            # Should handle error gracefully
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # Fail-open: allow connection despite error
            assert result is True, "Should allow on Redis error"


class TestRedisPartialFailures:
    """Tests for partial Redis operation failures."""

    @pytest.mark.asyncio
    async def test_rate_limiter_incr_succeeds_expire_fails(self):
        """Test rate limiter when INCR succeeds but EXPIRE fails."""
        limiter = RateLimiter()

        mock_redis = AsyncMock()
        # INCR succeeds, returning count
        mock_redis.incr = AsyncMock(return_value=1)
        # EXPIRE fails
        mock_redis.expire = AsyncMock(
            side_effect=RedisError("EXPIRE command failed")
        )

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis,
        ):
            # Should still process the request even if EXPIRE fails
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # INCR worked, so rate limit check should succeed
            assert is_allowed is True
            assert remaining == 9  # 10 - 1 = 9

    @pytest.mark.asyncio
    async def test_connection_limiter_sadd_succeeds_expire_fails(self):
        """Test connection limiter when SADD succeeds but EXPIRE fails."""
        limiter = ConnectionLimiter(max_connections=5)

        mock_redis = AsyncMock()
        mock_redis.scard = AsyncMock(return_value=0)  # No existing connections
        mock_redis.sadd = AsyncMock(return_value=1)  # Add succeeds
        mock_redis.expire = AsyncMock(
            side_effect=RedisError("EXPIRE failed")
        )  # Expire fails

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis,
        ):
            # Should still add connection even if EXPIRE fails
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            assert result is True, (
                "Should allow connection even if EXPIRE fails"
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
            "app.utils.rate_limiter.get_main_redis_connection"
        ) as mock_get_redis:
            mock_get_redis.return_value = None

            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            assert is_allowed is True, (
                "Should fail-open when Redis unavailable"
            )

        # Second call: Redis recovers
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis,
        ):
            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )

            # Should work normally when Redis recovers
            assert is_allowed is True
            assert remaining == 9
            mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_limiter_handles_flapping_redis(self):
        """Test connection limiter with flapping Redis (up/down/up)."""
        limiter = ConnectionLimiter(max_connections=3)

        # Round 1: Redis available
        mock_redis_1 = AsyncMock()
        mock_redis_1.scard = AsyncMock(return_value=0)
        mock_redis_1.sadd = AsyncMock(return_value=1)
        mock_redis_1.expire = AsyncMock(return_value=True)

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis_1,
        ):
            result1 = await limiter.add_connection("user1", "conn1")
            assert result1 is True

        # Round 2: Redis fails
        with patch(
            "app.utils.rate_limiter.get_main_redis_connection"
        ) as mock_get_redis:
            mock_get_redis.return_value = None

            result2 = await limiter.add_connection("user1", "conn2")
            assert result2 is True, "Should fail-open when Redis unavailable"

        # Round 3: Redis recovers
        mock_redis_3 = AsyncMock()
        mock_redis_3.scard = AsyncMock(
            return_value=2
        )  # Simulates 2 connections
        mock_redis_3.sadd = AsyncMock(return_value=1)
        mock_redis_3.expire = AsyncMock(return_value=True)

        with patch(
            "app.utils.rate_limiter.get_main_redis_connection",
            return_value=mock_redis_3,
        ):
            result3 = await limiter.add_connection("user1", "conn3")
            assert result3 is True  # Should work again
