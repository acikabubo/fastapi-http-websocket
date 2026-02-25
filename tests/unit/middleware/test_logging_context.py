"""
Tests for logging context middleware.

This module tests the LoggingContextMiddleware functionality including
contextual field injection and cleanup.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from fastapi_correlation import LoggingContextMiddleware


@pytest.fixture
def app():
    """
    Provides a FastAPI app instance.

    Returns:
        FastAPI: Test app
    """
    return FastAPI()


def make_request(path="/api/authors", method="GET", user=None):
    """Build a mock Request with scope dict for LoggingContextMiddleware tests."""
    request = MagicMock(spec=Request)
    request.url.path = path
    request.method = method
    if user is not None:
        request.scope = {"user": user}
        request.user = user
    else:
        request.scope = {}
    return request


class TestLoggingContextMiddleware:
    """Tests for LoggingContextMiddleware class."""

    @pytest.mark.asyncio
    async def test_middleware_sets_basic_context(self, app):
        """Test that middleware sets endpoint and method in log context."""
        middleware = LoggingContextMiddleware(app)
        request = make_request()
        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "fastapi_correlation.context_middleware.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            set_calls = mock_set.call_args_list
            assert any(
                call[1] == {"endpoint": "/api/authors", "method": "GET"}
                for call in set_calls
            )

    @pytest.mark.asyncio
    async def test_middleware_adds_user_id_from_username(self, app):
        """Test that middleware adds user_id from user.username attribute."""
        middleware = LoggingContextMiddleware(app)

        mock_user = MagicMock()
        mock_user.username = "user123"
        request = make_request(user=mock_user)

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "fastapi_correlation.context_middleware.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            set_calls = mock_set.call_args_list
            assert any(call[1] == {"user_id": "user123"} for call in set_calls)

    @pytest.mark.asyncio
    async def test_middleware_without_authenticated_user(self, app):
        """Test middleware when request has no authenticated user."""
        middleware = LoggingContextMiddleware(app)
        request = make_request(path="/api/public")
        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "fastapi_correlation.context_middleware.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            set_calls = mock_set.call_args_list
            assert not any(
                "user_id" in call[1]
                for call in set_calls
                if call[1] != {"endpoint": "/api/public", "method": "GET"}
                and call[1] != {"status_code": 200}
            )

    @pytest.mark.asyncio
    async def test_middleware_adds_status_code_to_context(self, app):
        """Test that middleware adds response status code to context."""
        middleware = LoggingContextMiddleware(app)
        request = make_request(method="POST")
        call_next = AsyncMock(return_value=Response(status_code=201))

        with patch(
            "fastapi_correlation.context_middleware.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 201

            set_calls = mock_set.call_args_list
            assert any(call[1] == {"status_code": 201} for call in set_calls)

    @pytest.mark.asyncio
    async def test_middleware_clears_context_after_request(self, app):
        """Test that middleware clears log context after request completes."""
        middleware = LoggingContextMiddleware(app)
        request = make_request()
        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "fastapi_correlation.context_middleware.clear_log_context"
        ) as mock_clear:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            mock_clear.assert_called_once()
