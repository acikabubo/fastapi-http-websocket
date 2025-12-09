"""
Tests for rate limiting functionality in HTTP and WebSocket handlers.

This module tests the rate limiting middleware for HTTP endpoints and
WebSocket message/connection rate limiting.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_redis():
    """
    Provides a mock Redis connection for rate limiter testing.

    Returns:
        AsyncMock: Mocked Redis connection
    """
    redis_mock = AsyncMock()
    redis_mock.zremrangebyscore = AsyncMock()
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.scard = AsyncMock(return_value=0)
    redis_mock.sadd = AsyncMock()
    redis_mock.srem = AsyncMock()
    return redis_mock


@pytest.fixture
def rate_limiter_with_mock_redis(mock_redis):
    """
    Provides a RateLimiter instance with mocked Redis.

    Args:
        mock_redis: Fixture providing mocked Redis connection

    Yields:
        RateLimiter: Rate limiter with mocked Redis
    """
    from {{cookiecutter.module_name}}.utils.rate_limiter import RateLimiter

    with patch(
        "{{cookiecutter.module_name}}.utils.rate_limiter.get_redis_connection"
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
    from {{cookiecutter.module_name}}.utils.rate_limiter import ConnectionLimiter

    with patch(
        "{{cookiecutter.module_name}}.utils.rate_limiter.get_redis_connection"
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

        is_allowed, remaining = (
            await rate_limiter_with_mock_redis.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )
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

        is_allowed, remaining = (
            await rate_limiter_with_mock_redis.check_rate_limit(
                key="test_user", limit=10, window_seconds=60
            )
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

        is_allowed, remaining = (
            await rate_limiter_with_mock_redis.check_rate_limit(
                key="test_user", limit=60, window_seconds=60, burst=10
            )
        )

        assert is_allowed is True
        assert remaining == 1

    @pytest.mark.asyncio
    async def test_reset_limit(
        self, rate_limiter_with_mock_redis, mock_redis
    ):
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

        from {{cookiecutter.module_name}}.middlewares.rate_limit import RateLimitMiddleware

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
        from {{cookiecutter.module_name}}.utils.rate_limiter import rate_limiter

        # Test allowed request
        with patch(
            "{{cookiecutter.module_name}}.utils.rate_limiter.get_redis_connection",
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
            "{{cookiecutter.module_name}}.utils.rate_limiter.get_redis_connection",
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
        from {{cookiecutter.module_name}}.api.ws.websocket import PackageAuthWebSocketEndpoint

        assert hasattr(PackageAuthWebSocketEndpoint, "on_connect")
        assert hasattr(PackageAuthWebSocketEndpoint, "on_disconnect")

    @pytest.mark.asyncio
    async def test_websocket_message_rate_limit(self):
        """Test WebSocket message rate limit enforcement."""
        # This would require WebSocket testing infrastructure
        # For now, we verify the implementation exists
        from {{cookiecutter.module_name}}.api.ws.consumers.web import Web

        assert hasattr(Web, "on_receive")
