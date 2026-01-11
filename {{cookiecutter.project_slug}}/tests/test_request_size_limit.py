"""
Tests for request size limit middleware.

This module tests the RequestSizeLimitMiddleware functionality including
request size validation and rejection of oversized payloads.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from {{cookiecutter.module_name}}.middlewares.request_size_limit import RequestSizeLimitMiddleware


@pytest.fixture
def app():
    """
    Provides a FastAPI app instance.

    Returns:
        FastAPI: Test app
    """
    return FastAPI()


class TestRequestSizeLimitMiddleware:
    """Tests for RequestSizeLimitMiddleware class."""

    @pytest.mark.asyncio
    async def test_middleware_allows_request_without_content_length(self, app):
        """Test that middleware allows requests without Content-Length header."""
        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {}

        call_next = AsyncMock(return_value=Response(status_code=200))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_allows_request_within_limit(self, app):
        """Test that middleware allows requests within size limit."""
        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {"content-length": "512"}

        call_next = AsyncMock(return_value=Response(status_code=200))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_allows_request_at_exact_limit(self, app):
        """Test that middleware allows requests at exact size limit."""
        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {"content-length": "1024"}

        call_next = AsyncMock(return_value=Response(status_code=200))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_rejects_oversized_request(self, app):
        """Test that middleware rejects requests exceeding size limit."""
        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {"content-length": "2048"}

        call_next = AsyncMock(return_value=Response(status_code=200))

        response = await middleware.dispatch(request, call_next)

        # Should return 413 Payload Too Large
        assert response.status_code == 413
        assert b"Request body too large" in response.body
        assert b"Maximum allowed: 1024 bytes" in response.body
        # call_next should NOT be called
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_content_length(self, app):
        """Test that middleware handles invalid Content-Length header gracefully."""
        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {"content-length": "invalid"}

        call_next = AsyncMock(return_value=Response(status_code=200))

        response = await middleware.dispatch(request, call_next)

        # Should allow request through (FastAPI will handle invalid request)
        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_uses_default_max_size_from_settings(self, app):
        """Test that middleware uses app_settings.MAX_REQUEST_BODY_SIZE by default."""
        from unittest.mock import patch

        with patch(
            "{{cookiecutter.module_name}}.middlewares.request_size_limit.app_settings"
        ) as mock_settings:
            mock_settings.MAX_REQUEST_BODY_SIZE = 512

            middleware = RequestSizeLimitMiddleware(app)

            # Verify max_size is set from settings
            assert middleware.max_size == 512

            request = MagicMock(spec=Request)
            request.headers = {"content-length": "1024"}  # Exceeds 512 limit

            call_next = AsyncMock(return_value=Response(status_code=200))

            response = await middleware.dispatch(request, call_next)

            # Should reject
            assert response.status_code == 413
            call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_custom_max_size_overrides_settings(self, app):
        """Test that custom max_size parameter overrides settings."""
        from unittest.mock import patch

        with patch(
            "{{cookiecutter.module_name}}.middlewares.request_size_limit.app_settings"
        ) as mock_settings:
            mock_settings.MAX_REQUEST_BODY_SIZE = 512

            # Custom max_size should override settings
            middleware = RequestSizeLimitMiddleware(app, max_size=2048)

            assert middleware.max_size == 2048

            request = MagicMock(spec=Request)
            request.headers = {"content-length": "1024"}  # Within 2048 limit

            call_next = AsyncMock(return_value=Response(status_code=200))

            response = await middleware.dispatch(request, call_next)

            # Should allow (within custom limit)
            assert response.status_code == 200
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_logs_rejection(self, app):
        """Test that middleware logs when rejecting oversized requests."""
        from unittest.mock import patch

        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {"content-length": "2048"}

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch("{{cookiecutter.module_name}}.middlewares.request_size_limit.logger") as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Should log warning
            assert response.status_code == 413
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Request rejected" in warning_msg
            assert "2048 bytes" in warning_msg
            assert "1024 bytes" in warning_msg

    @pytest.mark.asyncio
    async def test_middleware_logs_invalid_content_length(self, app):
        """Test that middleware logs invalid Content-Length header."""
        from unittest.mock import patch

        middleware = RequestSizeLimitMiddleware(app, max_size=1024)

        request = MagicMock(spec=Request)
        request.headers = {"content-length": "not-a-number"}

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch("{{cookiecutter.module_name}}.middlewares.request_size_limit.logger") as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Should log warning and allow request through
            assert response.status_code == 200
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Invalid Content-Length header" in warning_msg
            assert "not-a-number" in warning_msg
