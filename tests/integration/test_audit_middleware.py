"""
Tests for HTTP audit logging middleware.

This module tests the AuditMiddleware functionality including request logging,
filtering, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Response
from starlette.requests import Request

from app.middlewares.audit_middleware import AuditMiddleware
from app.schemas.user import UserModel


@pytest.fixture
def mock_user():
    """
    Provides a mock authenticated user.

    Returns:
        UserModel: Mock user instance
    """
    return UserModel(
        sub="user123",
        exp=9999999999,
        preferred_username="testuser",
        azp="test-client",
        resource_access={"test-client": {"roles": ["user", "admin"]}},
    )


@pytest.fixture
def app():
    """
    Provides a FastAPI app instance.

    Returns:
        FastAPI: Test app
    """
    return FastAPI()


class TestAuditMiddleware:
    """Tests for AuditMiddleware class."""

    @pytest.mark.asyncio
    async def test_middleware_disabled(self, app):
        """Test that middleware passes through when disabled."""
        middleware = AuditMiddleware(app)
        middleware.enabled = False

        request = MagicMock(spec=Request)
        call_next = AsyncMock(return_value=Response(status_code=200))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_skips_excluded_paths(self, app):
        """Test that middleware skips excluded paths."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/health"

        with patch(
            "app.middlewares.audit_middleware.app_settings"
        ) as mock_settings:
            mock_settings.EXCLUDED_PATHS.match.return_value = True

            call_next = AsyncMock(return_value=Response(status_code=200))

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_skips_unauthenticated_requests(self, app):
        """Test that middleware skips unauthenticated requests."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.user = None

        with patch(
            "app.middlewares.audit_middleware.app_settings"
        ) as mock_settings:
            mock_settings.EXCLUDED_PATHS.match.return_value = False

            call_next = AsyncMock(return_value=Response(status_code=200))

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_logs_successful_request(self, app, mock_user):
        """Test that middleware logs successful authenticated requests."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"
        request.user = mock_user
        request.headers = {"user-agent": "Test Browser"}
        request.state = MagicMock()
        request.state.request_id = "req-123"

        with (
            patch(
                "app.middlewares.audit_middleware.app_settings"
            ) as mock_settings,
            patch(
                "app.middlewares.audit_middleware.extract_ip_address"
            ) as mock_extract_ip,
            patch(
                "app.middlewares.audit_middleware.log_user_action"
            ) as mock_log_action,
        ):
            mock_settings.EXCLUDED_PATHS.match.return_value = False
            mock_extract_ip.return_value = "192.168.1.100"

            call_next = AsyncMock(return_value=Response(status_code=200))

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args[1]

            assert call_args["user_id"] == "user123"
            assert call_args["username"] == "testuser"
            assert call_args["action_type"] == "GET"
            assert call_args["resource"] == "/api/authors"
            assert call_args["outcome"] == "success"
            assert call_args["response_status"] == 200
            assert call_args["ip_address"] == "192.168.1.100"
            assert call_args["user_agent"] == "Test Browser"
            assert call_args["request_id"] == "req-123"
            assert "duration_ms" in call_args

    @pytest.mark.asyncio
    async def test_middleware_logs_error_response(self, app, mock_user):
        """Test that middleware logs error responses (4xx, 5xx)."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/api/forbidden"
        request.method = "POST"
        request.user = mock_user
        request.headers = {"user-agent": "Test Browser"}
        request.state = MagicMock()
        request.state.request_id = "req-456"

        with (
            patch(
                "app.middlewares.audit_middleware.app_settings"
            ) as mock_settings,
            patch(
                "app.middlewares.audit_middleware.extract_ip_address"
            ) as mock_extract_ip,
            patch(
                "app.middlewares.audit_middleware.log_user_action"
            ) as mock_log_action,
        ):
            mock_settings.EXCLUDED_PATHS.match.return_value = False
            mock_extract_ip.return_value = "192.168.1.101"

            call_next = AsyncMock(return_value=Response(status_code=403))

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 403
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args[1]

            assert call_args["outcome"] == "error"
            assert call_args["response_status"] == 403

    @pytest.mark.asyncio
    async def test_middleware_logs_exception(self, app, mock_user):
        """Test that middleware logs exceptions and re-raises."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/api/crash"
        request.method = "DELETE"
        request.user = mock_user
        request.headers = {"user-agent": "Test Browser"}
        request.state = MagicMock()
        request.state.request_id = "req-789"

        test_exception = ValueError("Test error")

        with (
            patch(
                "app.middlewares.audit_middleware.app_settings"
            ) as mock_settings,
            patch(
                "app.middlewares.audit_middleware.extract_ip_address"
            ) as mock_extract_ip,
            patch(
                "app.middlewares.audit_middleware.log_user_action"
            ) as mock_log_action,
        ):
            mock_settings.EXCLUDED_PATHS.match.return_value = False
            mock_extract_ip.return_value = "192.168.1.102"

            call_next = AsyncMock(side_effect=test_exception)

            # Should re-raise the exception
            with pytest.raises(ValueError, match="Test error"):
                await middleware.dispatch(request, call_next)

            # But should still log the error
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args[1]

            assert call_args["outcome"] == "error"
            assert call_args["error_message"] == "Test error"
            assert "duration_ms" in call_args

    @pytest.mark.asyncio
    async def test_middleware_without_request_id(self, app, mock_user):
        """Test middleware when request state has no request_id."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.user = mock_user
        request.headers = {}
        request.state = MagicMock()
        # No request_id attribute
        del request.state.request_id

        with (
            patch(
                "app.middlewares.audit_middleware.app_settings"
            ) as mock_settings,
            patch(
                "app.middlewares.audit_middleware.extract_ip_address"
            ) as mock_extract_ip,
            patch(
                "app.middlewares.audit_middleware.log_user_action"
            ) as mock_log_action,
        ):
            mock_settings.EXCLUDED_PATHS.match.return_value = False
            mock_extract_ip.return_value = "192.168.1.103"

            call_next = AsyncMock(return_value=Response(status_code=200))

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args[1]

            # request_id should be None
            assert call_args["request_id"] is None

    @pytest.mark.asyncio
    async def test_middleware_tracks_duration(self, app, mock_user):
        """Test that middleware correctly tracks request duration."""
        middleware = AuditMiddleware(app)
        middleware.enabled = True

        request = MagicMock(spec=Request)
        request.url.path = "/api/slow"
        request.method = "GET"
        request.user = mock_user
        request.headers = {}
        request.state = MagicMock()
        request.state.request_id = "req-slow"

        async def slow_call_next(req):
            """Simulate slow endpoint."""
            import asyncio

            await asyncio.sleep(0.1)  # 100ms delay
            return Response(status_code=200)

        with (
            patch(
                "app.middlewares.audit_middleware.app_settings"
            ) as mock_settings,
            patch(
                "app.middlewares.audit_middleware.extract_ip_address"
            ) as mock_extract_ip,
            patch(
                "app.middlewares.audit_middleware.log_user_action"
            ) as mock_log_action,
        ):
            mock_settings.EXCLUDED_PATHS.match.return_value = False
            mock_extract_ip.return_value = "192.168.1.104"

            response = await middleware.dispatch(request, slow_call_next)

            assert response.status_code == 200
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args[1]

            # Duration should be >= 100ms
            assert call_args["duration_ms"] >= 100
