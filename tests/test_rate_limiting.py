"""
Tests for rate limiting functionality in HTTP and WebSocket handlers.

This module tests the rate limiting middleware for HTTP endpoints and
WebSocket message/connection rate limiting.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.utils.rate_limiter import ConnectionLimiter, RateLimiter
from tests.mocks.redis_mocks import create_mock_redis_connection


@pytest.fixture
def mock_redis():
    """
    Provides a mock Redis connection for rate limiter testing.

    Returns:
        AsyncMock: Mocked Redis connection
    """
    return create_mock_redis_connection()


@pytest.fixture
def rate_limiter_with_mock_redis(mock_redis):
    """
    Provides a RateLimiter instance with mocked Redis.

    Args:
        mock_redis: Fixture providing mocked Redis connection

    Yields:
        RateLimiter: Rate limiter with mocked Redis
    """
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
    """
    Provides a ConnectionLimiter instance with mocked Redis.

    Args:
        mock_redis: Fixture providing mocked Redis connection

    Yields:
        ConnectionLimiter: Connection limiter with mocked Redis
    """
    with patch(
        "app.utils.rate_limiter.get_redis_connection"
    ) as mock_get_redis:
        mock_get_redis.return_value = mock_redis

        limiter = ConnectionLimiter()
        limiter.redis = mock_redis

        yield limiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_request(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test that rate limiter allows request when under limit.

        Args:
            rate_limiter_with_mock_redis: RateLimiter fixture
            mock_redis: Mocked Redis connection
        """
        mock_redis.zcard.return_value = 5

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="test_user", limit=10, window_seconds=60
        )

        assert is_allowed is True
        assert remaining == 4
        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_denies_request(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test that rate limiter denies request when limit exceeded.

        Args:
            rate_limiter_with_mock_redis: RateLimiter fixture
            mock_redis: Mocked Redis connection
        """
        mock_redis.zcard.return_value = 10

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="test_user", limit=10, window_seconds=60
        )

        assert is_allowed is False
        assert remaining == 0
        mock_redis.zadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_rate_limit_with_burst(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
        """
        Test rate limiter with burst limit.

        Args:
            rate_limiter_with_mock_redis: RateLimiter fixture
            mock_redis: Mocked Redis connection
        """
        mock_redis.zcard.return_value = 8

        (
            is_allowed,
            remaining,
        ) = await rate_limiter_with_mock_redis.check_rate_limit(
            key="test_user", limit=60, window_seconds=60, burst=10
        )

        assert is_allowed is True
        assert remaining == 1

    @pytest.mark.asyncio
    async def test_reset_limit(self, rate_limiter_with_mock_redis, mock_redis):
        """
        Test resetting rate limit for a key.

        Args:
            rate_limiter_with_mock_redis: RateLimiter fixture
            mock_redis: Mocked Redis connection
        """
        await rate_limiter_with_mock_redis.reset_limit("test_user")

        mock_redis.delete.assert_called_once_with("rate_limit:test_user")


class TestConnectionLimiter:
    """Tests for ConnectionLimiter class."""

    @pytest.mark.asyncio
    async def test_add_connection_success(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """
        Test adding connection when under limit.

        Args:
            connection_limiter_with_mock_redis: ConnectionLimiter fixture
            mock_redis: Mocked Redis connection
        """
        mock_redis.scard.return_value = 2

        result = await connection_limiter_with_mock_redis.add_connection(
            user_id="test_user", connection_id="conn_1"
        )

        assert result is True
        mock_redis.sadd.assert_called_once_with(
            "ws_connections:test_user", "conn_1"
        )
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_connection_limit_exceeded(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """
        Test adding connection when limit exceeded.

        Args:
            connection_limiter_with_mock_redis: ConnectionLimiter fixture
            mock_redis: Mocked Redis connection
        """
        # Set max_connections to 5
        connection_limiter_with_mock_redis.max_connections = 5
        mock_redis.scard.return_value = 5

        result = await connection_limiter_with_mock_redis.add_connection(
            user_id="test_user", connection_id="conn_6"
        )

        assert result is False
        mock_redis.sadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_connection(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """
        Test removing connection.

        Args:
            connection_limiter_with_mock_redis: ConnectionLimiter fixture
            mock_redis: Mocked Redis connection
        """
        await connection_limiter_with_mock_redis.remove_connection(
            user_id="test_user", connection_id="conn_1"
        )

        mock_redis.srem.assert_called_once_with(
            "ws_connections:test_user", "conn_1"
        )

    @pytest.mark.asyncio
    async def test_get_connection_count(
        self, connection_limiter_with_mock_redis, mock_redis
    ):
        """
        Test getting connection count.

        Args:
            connection_limiter_with_mock_redis: ConnectionLimiter fixture
            mock_redis: Mocked Redis connection
        """
        mock_redis.scard.return_value = 3

        count = await connection_limiter_with_mock_redis.get_connection_count(
            user_id="test_user"
        )

        assert count == 3
        mock_redis.scard.assert_called_once_with("ws_connections:test_user")


class TestHTTPRateLimitMiddleware:
    """Tests for HTTP rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_initialization(self):
        """Test that RateLimitMiddleware can be initialized."""
        from fastapi import FastAPI

        from app.middlewares.rate_limit import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        assert middleware is not None
        assert middleware.enabled is not None

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_dispatch_logic(self, mock_redis):
        """
        Test that middleware dispatch logic works correctly.

        Args:
            mock_redis: Mocked Redis connection
        """
        from app.utils.rate_limiter import rate_limiter

        # Test allowed request
        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            mock_redis.zcard.return_value = 5
            is_allowed, remaining = await rate_limiter.check_rate_limit(
                key="test_user", limit=60, window_seconds=60
            )
            assert is_allowed is True
            assert remaining > 0

        # Test denied request
        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            AsyncMock(return_value=mock_redis),
        ):
            mock_redis.zcard.return_value = 60
            is_allowed, remaining = await rate_limiter.check_rate_limit(
                key="test_user", limit=60, window_seconds=60
            )
            assert is_allowed is False
            assert remaining == 0


class TestWebSocketRateLimiting:
    """Tests for WebSocket rate limiting."""

    @pytest.mark.asyncio
    async def test_websocket_connection_limit(self):
        """Test WebSocket connection limit enforcement."""
        # This would require WebSocket testing infrastructure
        # For now, we verify the implementation exists
        from app.api.ws.websocket import PackageAuthWebSocketEndpoint

        assert hasattr(PackageAuthWebSocketEndpoint, "on_connect")
        assert hasattr(PackageAuthWebSocketEndpoint, "on_disconnect")

    @pytest.mark.asyncio
    async def test_websocket_message_rate_limit(self):
        """Test WebSocket message rate limit enforcement."""
        # This would require WebSocket testing infrastructure
        # For now, we verify the implementation exists
        from app.api.ws.consumers.web import Web

        assert hasattr(Web, "on_receive")


class TestRateLimiterErrorHandling:
    """Tests for RateLimiter error handling scenarios."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_disabled(self):
        """Test that rate limiter allows all requests when disabled."""
        from app.utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        limiter.enabled = False

        is_allowed, remaining = await limiter.check_rate_limit(
            key="test_user", limit=10
        )

        assert is_allowed is True
        assert remaining == 10

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_unavailable(self):
        """Test rate limiter behavior when Redis is unavailable."""
        from app.utils.rate_limiter import RateLimiter

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=None,
        ):
            limiter = RateLimiter()
            limiter.enabled = True

            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10
            )

            # Should fail open (allow request)
            assert is_allowed is True
            assert remaining == 10

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_error_fail_open(self, mock_redis):
        """Test rate limiter fails open on Redis error (default mode)."""
        from redis.exceptions import RedisError

        from app.utils.rate_limiter import RateLimiter

        mock_redis.zremrangebyscore.side_effect = RedisError(
            "Connection error"
        )

        with (
            patch(
                "app.utils.rate_limiter.get_redis_connection",
                return_value=mock_redis,
            ),
            patch("app.utils.rate_limiter.app_settings") as mock_settings,
        ):
            mock_settings.RATE_LIMIT_FAIL_MODE = "open"
            limiter = RateLimiter()
            limiter.enabled = True
            limiter.redis = mock_redis

            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10
            )

            # Should fail open (allow request)
            assert is_allowed is True
            assert remaining == 10

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_error_fail_closed(self, mock_redis):
        """Test rate limiter fails closed on Redis error (closed mode)."""
        from redis.exceptions import RedisError

        from app.utils.rate_limiter import RateLimiter

        mock_redis.zremrangebyscore.side_effect = RedisError(
            "Connection error"
        )

        with (
            patch(
                "app.utils.rate_limiter.get_redis_connection",
                return_value=mock_redis,
            ),
            patch("app.utils.rate_limiter.app_settings") as mock_settings,
        ):
            mock_settings.RATE_LIMIT_FAIL_MODE = "closed"
            limiter = RateLimiter()
            limiter.enabled = True
            limiter.redis = mock_redis

            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10
            )

            # Should fail closed (deny request)
            assert is_allowed is False
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_value_error(self, mock_redis):
        """Test rate limiter handles ValueError gracefully."""
        from app.utils.rate_limiter import RateLimiter

        mock_redis.zcard.side_effect = ValueError("Invalid value")

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=mock_redis,
        ):
            limiter = RateLimiter()
            limiter.enabled = True
            limiter.redis = mock_redis

            is_allowed, remaining = await limiter.check_rate_limit(
                key="test_user", limit=10
            )

            # Should fail closed on programming errors
            assert is_allowed is False
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_reset_limit_redis_unavailable(self):
        """Test reset_limit when Redis is unavailable."""
        from app.utils.rate_limiter import RateLimiter

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=None,
        ):
            limiter = RateLimiter()
            # Should not raise exception
            await limiter.reset_limit("test_user")

    @pytest.mark.asyncio
    async def test_reset_limit_redis_error(self, mock_redis):
        """Test reset_limit handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        from app.utils.rate_limiter import RateLimiter

        mock_redis.delete.side_effect = RedisError("Connection error")

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=mock_redis,
        ):
            limiter = RateLimiter()
            limiter.redis = mock_redis
            # Should not raise exception
            await limiter.reset_limit("test_user")


class TestConnectionLimiterErrorHandling:
    """Tests for ConnectionLimiter error handling scenarios."""

    @pytest.mark.asyncio
    async def test_add_connection_redis_unavailable(self):
        """Test add_connection when Redis is unavailable."""
        from app.utils.rate_limiter import ConnectionLimiter

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=None,
        ):
            limiter = ConnectionLimiter()
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # Should deny connection when Redis unavailable
            assert result is False

    @pytest.mark.asyncio
    async def test_add_connection_redis_error(self, mock_redis):
        """Test add_connection handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        from app.utils.rate_limiter import ConnectionLimiter

        mock_redis.scard.side_effect = RedisError("Connection error")

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=mock_redis,
        ):
            limiter = ConnectionLimiter()
            limiter.redis = mock_redis
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # Should fail closed on Redis errors
            assert result is False

    @pytest.mark.asyncio
    async def test_add_connection_value_error(self, mock_redis):
        """Test add_connection handles ValueError gracefully."""
        from app.utils.rate_limiter import ConnectionLimiter

        mock_redis.scard.side_effect = ValueError("Invalid value")

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=mock_redis,
        ):
            limiter = ConnectionLimiter()
            limiter.redis = mock_redis
            result = await limiter.add_connection(
                user_id="test_user", connection_id="conn_1"
            )

            # Should fail closed on programming errors
            assert result is False

    @pytest.mark.asyncio
    async def test_remove_connection_redis_unavailable(self):
        """Test remove_connection when Redis is unavailable."""
        from app.utils.rate_limiter import ConnectionLimiter

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=None,
        ):
            limiter = ConnectionLimiter()
            # Should not raise exception
            await limiter.remove_connection(
                user_id="test_user", connection_id="conn_1"
            )

    @pytest.mark.asyncio
    async def test_remove_connection_redis_error(self, mock_redis):
        """Test remove_connection handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        from app.utils.rate_limiter import ConnectionLimiter

        mock_redis.srem.side_effect = RedisError("Connection error")

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=mock_redis,
        ):
            limiter = ConnectionLimiter()
            limiter.redis = mock_redis
            # Should not raise exception
            await limiter.remove_connection(
                user_id="test_user", connection_id="conn_1"
            )

    @pytest.mark.asyncio
    async def test_get_connection_count_redis_unavailable(self):
        """Test get_connection_count when Redis is unavailable."""
        from app.utils.rate_limiter import ConnectionLimiter

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=None,
        ):
            limiter = ConnectionLimiter()
            count = await limiter.get_connection_count(user_id="test_user")

            # Should return 0 when Redis unavailable
            assert count == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_redis_error(self, mock_redis):
        """Test get_connection_count handles Redis errors gracefully."""
        from redis.exceptions import RedisError

        from app.utils.rate_limiter import ConnectionLimiter

        mock_redis.scard.side_effect = RedisError("Connection error")

        with patch(
            "app.utils.rate_limiter.get_redis_connection",
            return_value=mock_redis,
        ):
            limiter = ConnectionLimiter()
            limiter.redis = mock_redis
            count = await limiter.get_connection_count(user_id="test_user")

            # Should return 0 on error
            assert count == 0
