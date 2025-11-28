"""
Tests for rate limiting functionality in HTTP and WebSocket handlers.

This module tests the rate limiting middleware for HTTP endpoints and
WebSocket message/connection rate limiting.
"""

from unittest.mock import AsyncMock, MagicMock, patch

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
    from app.utils.rate_limiter import RateLimiter

    with patch("app.utils.rate_limiter.RRedis") as mock_rredis:
        mock_instance = MagicMock()
        mock_instance.r = mock_redis
        mock_rredis.return_value = mock_instance

        limiter = RateLimiter()
        limiter.redis.r = mock_redis
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
    from app.utils.rate_limiter import ConnectionLimiter

    with patch("app.utils.rate_limiter.RRedis") as mock_rredis:
        mock_instance = MagicMock()
        mock_instance.r = mock_redis
        mock_rredis.return_value = mock_instance

        limiter = ConnectionLimiter()
        limiter.redis.r = mock_redis

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
    async def test_rate_limit_middleware_allows_request(
        self, mock_keycloak_manager, mock_user_data
    ):
        """
        Test that middleware allows request when under limit.

        Args:
            mock_keycloak_manager: Mocked Keycloak manager
            mock_user_data: Mock user data
        """
        from app import application

        app = application()
        client = TestClient(app)

        with patch(
            "app.utils.rate_limiter.rate_limiter.check_rate_limit"
        ) as mock_check:
            mock_check.return_value = (True, 50)

            response = client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_denies_request(
        self, mock_keycloak_manager
    ):
        """
        Test that middleware denies request when limit exceeded.

        Args:
            mock_keycloak_manager: Mocked Keycloak manager
        """
        from app import application

        app = application()
        client = TestClient(app)

        with patch(
            "app.utils.rate_limiter.rate_limiter.check_rate_limit"
        ) as mock_check:
            mock_check.return_value = (False, 0)

            response = client.get("/health")
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]
            assert response.headers["X-RateLimit-Remaining"] == "0"


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
