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

from {{cookiecutter.module_name}}.middlewares.logging_context import LoggingContextMiddleware


@pytest.fixture
def app():
    """
    Provides a FastAPI app instance.

    Returns:
        FastAPI: Test app
    """
    return FastAPI()


class TestLoggingContextMiddleware:
    """Tests for LoggingContextMiddleware class."""

    @pytest.mark.asyncio
    async def test_middleware_sets_basic_context(self, app):
        """Test that middleware sets endpoint and method in log context."""
        middleware = LoggingContextMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"
        request.state = MagicMock()

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "{{cookiecutter.module_name}}.middlewares.logging_context.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check that set_log_context was called with endpoint and method
            set_calls = mock_set.call_args_list
            assert any(
                call[1] == {"endpoint": "/api/authors", "method": "GET"}
                for call in set_calls
            )

    @pytest.mark.asyncio
    async def test_middleware_adds_user_id_from_user_id_attribute(self, app):
        """Test that middleware adds user_id from user.user_id attribute."""
        middleware = LoggingContextMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"
        request.state = MagicMock()

        # User with user_id attribute
        mock_user = MagicMock()
        mock_user.user_id = "user123"
        request.state.user = mock_user

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "{{cookiecutter.module_name}}.middlewares.logging_context.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check that user_id was added to context
            set_calls = mock_set.call_args_list
            assert any(call[1] == {"user_id": "user123"} for call in set_calls)

    @pytest.mark.asyncio
    async def test_middleware_adds_user_id_from_sub_attribute(self, app):
        """Test that middleware adds user_id from user.sub attribute."""
        middleware = LoggingContextMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"
        request.state = MagicMock()

        # User with sub attribute (no user_id)
        mock_user = MagicMock(spec=["sub"])
        mock_user.sub = "sub456"
        request.state.user = mock_user

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "{{cookiecutter.module_name}}.middlewares.logging_context.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check that user_id was added from sub
            set_calls = mock_set.call_args_list
            assert any(call[1] == {"user_id": "sub456"} for call in set_calls)

    @pytest.mark.asyncio
    async def test_middleware_without_authenticated_user(self, app):
        """Test middleware when request has no authenticated user."""
        middleware = LoggingContextMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/public"
        request.method = "GET"
        request.state = MagicMock()
        request.state.user = None

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "{{cookiecutter.module_name}}.middlewares.logging_context.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Should not set user_id
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

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "POST"
        request.state = MagicMock()

        call_next = AsyncMock(return_value=Response(status_code=201))

        with patch(
            "{{cookiecutter.module_name}}.middlewares.logging_context.set_log_context"
        ) as mock_set:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 201

            # Check that status_code was added to context
            set_calls = mock_set.call_args_list
            assert any(call[1] == {"status_code": 201} for call in set_calls)

    @pytest.mark.asyncio
    async def test_middleware_clears_context_after_request(self, app):
        """Test that middleware clears log context after request completes."""
        middleware = LoggingContextMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"
        request.state = MagicMock()

        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch(
            "{{cookiecutter.module_name}}.middlewares.logging_context.clear_log_context"
        ) as mock_clear:
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check that clear_log_context was called
            mock_clear.assert_called_once()
