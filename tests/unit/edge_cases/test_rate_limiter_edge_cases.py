"""
Comprehensive edge case tests for rate limiting functionality.

This module tests critical edge cases in rate limiting including Redis failures,
clock skew, burst limits, and concurrent rate limit checks.
"""

from unittest.mock import patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.utils.rate_limiter import ConnectionLimiter, RateLimiter
from tests.mocks.redis_mocks import create_mock_redis_connection


@pytest.fixture
def mock_redis():
    """Provides a mock Redis connection for rate limiter testing."""
    return create_mock_redis_connection()


@pytest.fixture
def rate_limiter_with_mock_redis(mock_redis):
    """Provides a RateLimiter instance with mocked Redis."""
    with patch(
        "app.utils.rate_limiter.get_redis_connection"
    ) as mock_get_redis:
        mock_get_redis.return_value = mock_redis

        limiter = RateLimiter()
        limiter.redis = mock_redis
        limiter.enabled = True

        yield limiter


@pytest.fixture
def connection_limiter_with_mock_redis(mock_redis):
    """Provides a ConnectionLimiter instance with mocked Redis."""
    with patch(
        "app.utils.rate_limiter.get_redis_connection"
    ) as mock_get_redis:
        mock_get_redis.return_value = mock_redis

        limiter = ConnectionLimiter()
        limiter.redis = mock_redis

        yield limiter


class TestRedisFailureScenarios:
    """Test rate limiter behavior when Redis fails."""

    @pytest.mark.asyncio
    async def test_redis_connection_error_fail_open(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test fail-open behavior when Redis connection fails.

        When Redis is unavailable, rate limiter should allow requests through.
        """
        # Simulate Redis connection error
        mock_redis.zadd.side_effect = RedisConnectionError(
            "Connection refused"
        )

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60
        )

        # Should fail-open (allow request)
        assert is_allowed is True
        assert remaining == 10  # Full limit returned on fail-open

    @pytest.mark.asyncio
    async def test_redis_timeout_fail_open(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """Test fail-open when Redis times out."""
        mock_redis.zadd.side_effect = RedisTimeoutError("Operation timed out")

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60
        )

        assert is_allowed is True
        assert remaining == 10  # Full limit returned on fail-open

    @pytest.mark.asyncio
    async def test_redis_generic_error_fail_open(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """Test fail-open for generic Redis errors."""
        mock_redis.zadd.side_effect = RedisError("Unknown Redis error")

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60
        )

        assert is_allowed is True
        assert remaining == 10  # Full limit returned on fail-open

    @pytest.mark.asyncio
    async def test_redis_failure_mid_operation(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test partial failure scenario.

        ZADD succeeds but EXPIRE fails - should still fail-open gracefully.
        """
        # ZADD succeeds
        mock_redis.zadd.return_value = 1
        mock_redis.zcard.return_value = 5

        # EXPIRE fails
        mock_redis.expire.side_effect = RedisError("EXPIRE command failed")

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60
        )

        # Should allow request despite partial failure
        assert is_allowed is True


class TestBurstLimitEdgeCases:
    """Test burst limit boundary conditions."""

    @pytest.mark.asyncio
    async def test_exactly_at_burst_threshold(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """Test behavior when exactly at burst limit."""
        # Simulate exactly at burst threshold
        mock_redis.zcard.return_value = 10  # Exactly at burst limit
        mock_redis.zadd.return_value = 1

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=60, window_seconds=60, burst=10
        )

        # Should deny (request_count >= effective_limit, so 10 >= 10 is True)
        assert is_allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_one_over_burst_threshold(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """Test rejection when one request over burst limit."""
        # Simulate one over burst threshold
        mock_redis.zcard.return_value = 11  # One over burst limit of 10
        mock_redis.zadd.return_value = 1

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=60, window_seconds=60, burst=10
        )

        # Should reject
        assert is_allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_burst_limit_zero(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """Test burst limit of zero (no burst allowed)."""
        mock_redis.zcard.return_value = 0
        mock_redis.zadd.return_value = 1

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=60, window_seconds=60, burst=0
        )

        # First request should be allowed
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_burst_greater_than_limit(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test when burst is configured larger than total limit.

        This is a misconfiguration case.
        """
        mock_redis.zcard.return_value = 5
        mock_redis.zadd.return_value = 1

        # Burst (100) > limit (10) - misconfigured
        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60, burst=100
        )

        # Should still work, using limit as upper bound
        assert is_allowed is True


class TestClockSkewAndTimeDrift:
    """Test rate limiter behavior with time-related edge cases."""

    @pytest.mark.asyncio
    async def test_clock_skew_old_timestamps(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test handling of very old timestamps in sorted set.

        Old timestamps should be removed by ZREMRANGEBYSCORE.
        """
        mock_redis.zcard.return_value = 0  # All old entries removed
        mock_redis.zadd.return_value = 1

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60
        )

        assert is_allowed is True

        # Verify old entries were attempted to be removed
        mock_redis.zremrangebyscore.assert_called_once()

    @pytest.mark.asyncio
    async def test_future_timestamps_ignored(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test that timestamps in the future don't affect rate limiting.

        Future timestamps (clock ahead) should not be counted in current window.
        """
        # Simulate timestamps: some current, some in future
        mock_redis.zcard.return_value = 2  # Only count current window
        mock_redis.zadd.return_value = 1

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="user:123", limit=10, window_seconds=60
        )

        assert is_allowed is True
        assert remaining > 0


class TestConcurrentRateLimitChecks:
    """Test concurrent rate limit checks for race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_checks_same_key(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test multiple concurrent rate limit checks for same key.

        Simulates race condition where multiple requests check limit
        simultaneously.
        """
        import asyncio

        # Configure mock to allow first 10 requests
        call_count = [0]

        def mock_zcard(*args, **kwargs):
            call_count[0] += 1
            return min(call_count[0], 10)

        mock_redis.zcard.side_effect = mock_zcard
        mock_redis.zadd.return_value = 1

        # Send 15 concurrent requests
        tasks = [
            rate_limiter_with_mock_redis.check_rate_limit(
                key="user:123", limit=10, window_seconds=60
            )
            for _ in range(15)
        ]

        results = await asyncio.gather(*tasks)

        # At least some should be allowed
        allowed_count = sum(1 for is_allowed, _ in results if is_allowed)
        assert allowed_count > 0

    @pytest.mark.asyncio
    async def test_concurrent_checks_different_keys(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test concurrent rate limit checks for different keys.

        Different keys should not interfere with each other.
        """
        import asyncio

        mock_redis.zcard.return_value = 0
        mock_redis.zadd.return_value = 1

        # Concurrent checks for different users
        tasks = [
            rate_limiter_with_mock_redis.check_rate_limit(
                key=f"user:{i}", limit=10, window_seconds=60
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should be allowed (different keys)
        assert all(is_allowed for is_allowed, _ in results)


class TestConnectionLimiterEdgeCases:
    """Test connection limiter edge cases."""

    @pytest.mark.asyncio
    async def test_add_connection_at_limit(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """Test adding connection when exactly at limit."""
        # Simulate exactly at limit (5 connections, default WS_MAX_CONNECTIONS_PER_USER)
        mock_redis.scard.return_value = 5

        is_allowed = await connection_limiter_with_mock_redis.add_connection(
            user_id="user123", connection_id="conn6"
        )

        # Should reject (already at limit)
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_add_connection_one_below_limit(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """Test adding connection when one below limit."""
        # Simulate one below limit (4 connections, limit 5)
        mock_redis.scard.return_value = 4
        mock_redis.sadd.return_value = 1

        is_allowed = await connection_limiter_with_mock_redis.add_connection(
            user_id="user123", connection_id="conn5"
        )

        # Should allow
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent_connection(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """Test removing a connection that doesn't exist."""
        mock_redis.srem.return_value = 0  # Nothing removed

        # Should not raise error
        await connection_limiter_with_mock_redis.remove_connection(
            user_id="user123", connection_id="nonexistent"
        )

        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_limiter_redis_failure(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """Test connection limiter fails closed when Redis unavailable."""
        mock_redis.scard.side_effect = RedisConnectionError(
            "Connection failed"
        )

        is_allowed = await connection_limiter_with_mock_redis.add_connection(
            user_id="user123", connection_id="conn1"
        )

        # Should fail-closed (deny connection for security)
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_duplicate_connection_id(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """Test adding same connection ID twice."""
        mock_redis.scard.return_value = 1
        mock_redis.sadd.return_value = 0  # Already exists

        is_allowed = await connection_limiter_with_mock_redis.add_connection(
            user_id="user123", connection_id="conn1"
        )

        # Should allow (SADD is idempotent)
        assert is_allowed is True


class TestRateLimiterDisabled:
    """Test rate limiter behavior when disabled."""

    @pytest.mark.asyncio
    async def test_rate_limiter_disabled_allows_all(self, mock_redis):
        """Test that disabled rate limiter allows all requests."""
        with patch(
            "app.utils.rate_limiter.get_redis_connection"
        ) as mock_get_redis:
            mock_get_redis.return_value = mock_redis

            limiter = RateLimiter()
            limiter.redis = mock_redis
            limiter.enabled = False  # Disabled

            is_allowed, remaining = await limiter.check_rate_limit(
                key="user:123", limit=1, window_seconds=60
            )

            # Should allow without checking Redis
            assert is_allowed is True
            mock_redis.zadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limiter_none_redis_allows_all(self):
        """Test that rate limiter with None redis allows all requests."""
        with patch(
            "app.utils.rate_limiter.get_redis_connection"
        ) as mock_get_redis:
            mock_get_redis.return_value = None  # Redis unavailable

            limiter = RateLimiter()
            limiter.enabled = True

            is_allowed, remaining = await limiter.check_rate_limit(
                key="user:123", limit=1, window_seconds=60
            )

            # Should fail-open
            assert is_allowed is True
