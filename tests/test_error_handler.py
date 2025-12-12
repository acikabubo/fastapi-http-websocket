"""
Tests for error handler decorators.

Tests the handle_ws_errors, handle_http_errors, and handle_errors decorators
to ensure proper exception handling and response formatting.
"""

import json

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.ws.constants import PkgID, RSPCode
from app.exceptions import (
    AppException,
    AuthorizationError,
    NotFoundError,
    ValidationError as AppValidationError,
)
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.utils.error_handler import (
    handle_errors,
    handle_http_errors,
    handle_ws_errors,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_request():
    """Create a sample WebSocket request for testing."""
    from uuid import uuid4

    return RequestModel(
        pkg_id=PkgID.GET_AUTHORS,
        req_id=uuid4(),
        data={},
    )


# ============================================================================
# WebSocket Error Handler Tests
# ============================================================================


class TestHandleWSErrors:
    """Test handle_ws_errors decorator for WebSocket handlers."""

    @pytest.mark.asyncio
    async def test_successful_execution(self, sample_request):
        """Should return successful response when no exception occurs."""

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data={"message": "success"},
            )

        response = await handler(sample_request)

        assert response.pkg_id == sample_request.pkg_id
        assert response.req_id == sample_request.req_id
        assert response.status_code == RSPCode.OK
        assert response.data == {"message": "success"}

    @pytest.mark.asyncio
    async def test_handles_app_exception(self, sample_request):
        """Should convert AppException to error ResponseModel."""

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            raise AppValidationError("Invalid author name")

        response = await handler(sample_request)

        assert response.pkg_id == sample_request.pkg_id
        assert response.req_id == sample_request.req_id
        assert response.status_code == RSPCode.INVALID_DATA
        assert response.data["msg"] == "Invalid author name"

    @pytest.mark.asyncio
    async def test_handles_not_found_exception(self, sample_request):
        """Should convert NotFoundError to ERROR response."""

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            raise NotFoundError("Author not found")

        response = await handler(sample_request)

        assert response.status_code == RSPCode.ERROR
        assert response.data["msg"] == "Author not found"

    @pytest.mark.asyncio
    async def test_handles_permission_denied_exception(self, sample_request):
        """Should convert AuthorizationError to PERMISSION_DENIED response."""

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            raise AuthorizationError("Insufficient permissions")

        response = await handler(sample_request)

        assert response.status_code == RSPCode.PERMISSION_DENIED
        assert response.data["msg"] == "Insufficient permissions"

    @pytest.mark.asyncio
    async def test_handles_sqlalchemy_error(self, sample_request):
        """Should convert SQLAlchemy errors to ERROR response."""

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            raise IntegrityError("statement", "params", "orig")

        response = await handler(sample_request)

        assert response.pkg_id == sample_request.pkg_id
        assert response.req_id == sample_request.req_id
        assert response.status_code == RSPCode.ERROR
        assert response.data["msg"] == "Database error occurred"

    @pytest.mark.asyncio
    async def test_preserves_request_context(self, sample_request):
        """Should preserve pkg_id and req_id in error responses."""

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            raise AppValidationError("Test error")

        response = await handler(sample_request)

        assert response.pkg_id == sample_request.pkg_id
        assert response.req_id == sample_request.req_id


# ============================================================================
# HTTP Error Handler Tests
# ============================================================================


class TestHandleHTTPErrors:
    """Test handle_http_errors decorator for HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Should return result when no exception occurs."""

        @handle_http_errors
        async def handler() -> dict:
            return {"message": "success"}

        result = await handler()

        assert result == {"message": "success"}

    @pytest.mark.asyncio
    async def test_handles_app_exception(self):
        """Should convert AppException to error envelope JSONResponse."""

        @handle_http_errors
        async def handler():
            raise AppValidationError("Invalid input")

        response = await handler()

        assert response.status_code == 400
        content = json.loads(response.body)
        assert "error" in content
        assert content["error"]["code"] == "validation_error"
        assert content["error"]["msg"] == "Invalid input"

    @pytest.mark.asyncio
    async def test_handles_not_found_exception(self):
        """Should convert NotFoundError to 404 error envelope."""

        @handle_http_errors
        async def handler():
            raise NotFoundError("Resource not found")

        response = await handler()

        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["error"]["code"] == "not_found"
        assert content["error"]["msg"] == "Resource not found"

    @pytest.mark.asyncio
    async def test_handles_permission_denied_exception(self):
        """Should convert AuthorizationError to 403 error envelope."""

        @handle_http_errors
        async def handler():
            raise AuthorizationError("Access denied")

        response = await handler()

        assert response.status_code == 403
        content = json.loads(response.body)
        assert content["error"]["code"] == "permission_denied"
        assert content["error"]["msg"] == "Access denied"

    @pytest.mark.asyncio
    async def test_handles_sqlalchemy_error(self):
        """Should convert SQLAlchemy errors to 500 error envelope."""

        @handle_http_errors
        async def handler():
            raise IntegrityError("statement", "params", "orig")

        response = await handler()

        assert response.status_code == 500
        content = json.loads(response.body)
        assert content["error"]["code"] == "database_error"
        assert content["error"]["msg"] == "Database error occurred"


# ============================================================================
# Auto-detecting Error Handler Tests
# ============================================================================


class TestHandleErrors:
    """Test handle_errors auto-detecting decorator."""

    @pytest.mark.asyncio
    async def test_detects_websocket_handler(self, sample_request):
        """Should apply ws error handling for RequestModel parameter."""

        @handle_errors
        async def ws_handler(request: RequestModel) -> ResponseModel:
            raise AppValidationError("Invalid data")

        response = await ws_handler(sample_request)

        # Should return ResponseModel (WS behavior)
        assert isinstance(response, ResponseModel)
        assert response.status_code == RSPCode.INVALID_DATA

    @pytest.mark.asyncio
    async def test_detects_http_handler(self):
        """Should apply HTTP error handling for non-RequestModel parameter."""

        @handle_errors
        async def http_handler(data: dict) -> dict:
            raise NotFoundError("Not found")

        # Should return JSONResponse with error envelope (HTTP behavior)
        response = await http_handler({"test": "data"})

        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["error"]["code"] == "not_found"
        assert content["error"]["msg"] == "Not found"

    @pytest.mark.asyncio
    async def test_successful_websocket_execution(self, sample_request):
        """Should work correctly for successful WS handlers."""

        @handle_errors
        async def ws_handler(request: RequestModel) -> ResponseModel:
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data={"result": "ok"},
            )

        response = await ws_handler(sample_request)

        assert response.data == {"result": "ok"}
        assert response.status_code == RSPCode.OK

    @pytest.mark.asyncio
    async def test_successful_http_execution(self):
        """Should work correctly for successful HTTP handlers."""

        @handle_errors
        async def http_handler(value: int) -> int:
            return value * 2

        result = await http_handler(21)

        assert result == 42


# ============================================================================
# Integration Tests
# ============================================================================


class TestErrorHandlerIntegration:
    """Integration tests for error handlers in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_websocket_handler_with_nested_exceptions(self, sample_request):
        """Should handle exceptions raised from nested function calls."""

        async def nested_function():
            raise AppValidationError("Nested error")

        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            await nested_function()
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data={},
            )

        response = await handler(sample_request)

        assert response.status_code == RSPCode.INVALID_DATA
        assert response.data["msg"] == "Nested error"

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Should preserve original function name and docstring."""

        @handle_ws_errors
        async def my_handler(request: RequestModel) -> ResponseModel:
            """Original docstring."""
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data={},
            )

        assert my_handler.__name__ == "my_handler"
        assert "Original docstring" in my_handler.__doc__

    @pytest.mark.asyncio
    async def test_works_with_multiple_decorators(self, sample_request):
        """Should work correctly when combined with other decorators."""

        def log_calls(func):
            """Dummy decorator for testing."""

            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        @log_calls
        @handle_ws_errors
        async def handler(request: RequestModel) -> ResponseModel:
            raise AppValidationError("Test error")

        response = await handler(sample_request)

        assert response.status_code == RSPCode.INVALID_DATA
