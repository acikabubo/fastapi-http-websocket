"""
Tests for RateLimitMiddleware.

This module tests the HTTP rate limiting middleware dispatch logic,
including enabled/disabled states, excluded paths, and rate limit enforcement.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request, Response

from app.middlewares.rate_limit import RateLimitMiddleware
from app.schemas.user import UserModel


@pytest.fixture
def mock_app():
    """
    Provides a mock FastAPI application.

    Returns:
        FastAPI: Mock application instance
    """
    return FastAPI()


@pytest.fixture
def mock_request():
    """
    Provides a mock Request object.

    Returns:
        MagicMock: Mocked request
    """
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = "/api/test"
    request.method = "GET"
    request.state = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_call_next():
    """
    Provides a mock call_next function.

    Returns:
        AsyncMock: Mocked call_next function
    """

    async def call_next(request):
        return Response(content="OK", status_code=200)

    return AsyncMock(side_effect=call_next)


class TestRateLimitMiddlewareInit:
    """Tests for RateLimitMiddleware initialization."""

    def test_middleware_initialization(self, mock_app):
        """
        Test middleware initialization with settings.

        Args:
            mock_app: Mock FastAPI application
        """
        middleware = RateLimitMiddleware(mock_app)

        assert middleware is not None
        assert hasattr(middleware, "enabled")
        assert hasattr(middleware, "rate_limit")
        assert hasattr(middleware, "burst_limit")


class TestRateLimitMiddlewareDispatch:
    """Tests for RateLimitMiddleware dispatch method."""

    @pytest.mark.asyncio
    async def test_dispatch_when_disabled(
        self, mock_app, mock_request, mock_call_next
    ):
        """
        Test that middleware passes through when disabled.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
            mock_call_next: Mock call_next function
        """
        with patch("app.middlewares.rate_limit.app_settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = False

            middleware = RateLimitMiddleware(mock_app)
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 200
            mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(
        self, mock_app, mock_request, mock_call_next
    ):
        """
        Test that excluded paths bypass rate limiting.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
            mock_call_next: Mock call_next function
        """
        mock_request.url.path = "/health"

        with patch("app.middlewares.rate_limit.app_settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_pattern = MagicMock()
            mock_pattern.match.return_value = True
            mock_settings.EXCLUDED_PATHS = mock_pattern

            middleware = RateLimitMiddleware(mock_app)
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 200
            mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_allowed(
        self, mock_app, mock_request, mock_call_next
    ):
        """
        Test successful request when under rate limit.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
            mock_call_next: Mock call_next function
        """
        mock_request.state.user = None

        with patch("app.middlewares.rate_limit.app_settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.RATE_LIMIT_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST = 10
            mock_pattern = MagicMock()
            mock_pattern.match.return_value = False
            mock_settings.EXCLUDED_PATHS = mock_pattern

            with patch(
                "app.middlewares.rate_limit.rate_limiter"
            ) as mock_limiter:
                mock_limiter.check_rate_limit = AsyncMock(
                    return_value=(True, 55)
                )

                middleware = RateLimitMiddleware(mock_app)
                response = await middleware.dispatch(
                    mock_request, mock_call_next
                )

                assert response.status_code == 200
                assert "X-RateLimit-Limit" in response.headers
                assert response.headers["X-RateLimit-Limit"] == "60"
                assert response.headers["X-RateLimit-Remaining"] == "55"
                mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_exceeded(
        self, mock_app, mock_request, mock_call_next
    ):
        """
        Test request rejection when rate limit exceeded.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
            mock_call_next: Mock call_next function
        """
        mock_request.state.user = None

        with patch("app.middlewares.rate_limit.app_settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.RATE_LIMIT_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST = 10
            mock_pattern = MagicMock()
            mock_pattern.match.return_value = False
            mock_settings.EXCLUDED_PATHS = mock_pattern

            with patch(
                "app.middlewares.rate_limit.rate_limiter"
            ) as mock_limiter:
                mock_limiter.check_rate_limit = AsyncMock(return_value=(False, 0))

                middleware = RateLimitMiddleware(mock_app)
                response = await middleware.dispatch(
                    mock_request, mock_call_next
                )

                assert response.status_code == 429
                assert "X-RateLimit-Limit" in response.headers
                assert response.headers["X-RateLimit-Remaining"] == "0"
                assert "Retry-After" in response.headers
                mock_call_next.assert_not_called()


class TestGetRateLimitKey:
    """Tests for _get_rate_limit_key method."""

    def test_get_rate_limit_key_with_user(self, mock_app, mock_request):
        """
        Test rate limit key generation with authenticated user.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
        """
        user = UserModel(
            sub="user-id-123",
            exp=1700000000,
            preferred_username="testuser",
            azp="test-client",
            resource_access={"test-client": {"roles": ["user"]}},
        )
        mock_request.state.user = user

        middleware = RateLimitMiddleware(mock_app)
        key = middleware._get_rate_limit_key(mock_request)

        assert key == "user:testuser"

    def test_get_rate_limit_key_without_user(self, mock_app, mock_request):
        """
        Test rate limit key generation with IP address.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
        """
        mock_request.state.user = None
        mock_request.client.host = "192.168.1.100"

        middleware = RateLimitMiddleware(mock_app)
        key = middleware._get_rate_limit_key(mock_request)

        assert key == "ip:192.168.1.100"

    def test_get_rate_limit_key_no_client(self, mock_app, mock_request):
        """
        Test rate limit key generation when client is None.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
        """
        mock_request.state.user = None
        mock_request.client = None

        middleware = RateLimitMiddleware(mock_app)
        key = middleware._get_rate_limit_key(mock_request)

        assert key == "ip:unknown"

    def test_get_rate_limit_key_user_without_username(
        self, mock_app, mock_request
    ):
        """
        Test rate limit key falls back to IP when user has no username.

        Args:
            mock_app: Mock FastAPI application
            mock_request: Mock HTTP request
        """
        user = MagicMock(spec=UserModel)
        user.username = None
        mock_request.state.user = user
        mock_request.client.host = "10.0.0.1"

        middleware = RateLimitMiddleware(mock_app)
        key = middleware._get_rate_limit_key(mock_request)

        assert key == "ip:10.0.0.1"
