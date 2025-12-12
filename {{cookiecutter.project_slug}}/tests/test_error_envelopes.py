"""
Tests for unified error envelope models and formatters.

Tests verify that:
- Error envelope models serialize correctly
- HTTP and WebSocket error responses have consistent shapes
- Exception-to-error-code mapping works correctly
- Error formatters produce valid error envelopes
"""

from uuid import UUID, uuid4

import pytest

from {{cookiecutter.module_name}}.api.ws.constants import PkgID, RSPCode
from {{cookiecutter.module_name}}.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from {{cookiecutter.module_name}}.schemas.errors import (
    ErrorCode,
    ErrorEnvelope,
    HTTPErrorResponse,
    WebSocketErrorResponse,
)
from {{cookiecutter.module_name}}.utils.error_formatter import (
    create_error_envelope,
    exception_to_error_code,
    http_error_from_exception,
    http_error_response,
    ws_error_from_exception,
    ws_error_response,
)


class TestErrorEnvelopeModels:
    """Test error envelope Pydantic models."""

    def test_error_envelope_basic(self):
        """Test basic ErrorEnvelope creation."""
        envelope = ErrorEnvelope(
            code="test_error",
            msg="Test error message",
        )

        assert envelope.code == "test_error"
        assert envelope.msg == "Test error message"
        assert envelope.details is None

    def test_error_envelope_with_details(self):
        """Test ErrorEnvelope with details."""
        envelope = ErrorEnvelope(
            code="validation_error",
            msg="Invalid field",
            details={"field": "name", "constraint": "min_length"},
        )

        assert envelope.code == "validation_error"
        assert envelope.msg == "Invalid field"
        assert envelope.details == {"field": "name", "constraint": "min_length"}

    def test_http_error_response(self):
        """Test HTTPErrorResponse structure."""
        error = HTTPErrorResponse(
            error=ErrorEnvelope(
                code="not_found",
                msg="Resource not found",
                details={"resource_id": 42},
            )
        )

        assert error.error.code == "not_found"
        assert error.error.msg == "Resource not found"
        assert error.error.details == {"resource_id": 42}

        # Test serialization
        data = error.model_dump()
        assert "error" in data
        assert data["error"]["code"] == "not_found"
        assert data["error"]["msg"] == "Resource not found"

    def test_websocket_error_response(self):
        """Test WebSocketErrorResponse structure."""
        req_id = uuid4()
        error = WebSocketErrorResponse(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            status_code=RSPCode.INVALID_DATA,
            data={
                "code": "validation_error",
                "msg": "Invalid data",
                "details": {"field": "name"},
            },
        )

        assert error.pkg_id == PkgID.TEST_HANDLER
        assert error.req_id == req_id
        assert error.status_code == RSPCode.INVALID_DATA
        assert error.data["code"] == "validation_error"
        assert error.data["msg"] == "Invalid data"

        # Test serialization
        data = error.model_dump(mode="json")
        assert data["pkg_id"] == PkgID.TEST_HANDLER
        assert data["status_code"] == RSPCode.INVALID_DATA
        assert data["data"]["code"] == "validation_error"


class TestErrorFormatters:
    """Test error formatting utility functions."""

    def test_create_error_envelope(self):
        """Test create_error_envelope helper."""
        envelope = create_error_envelope(
            code=ErrorCode.NOT_FOUND,
            msg="Resource not found",
            details={"resource_id": 42},
        )

        assert isinstance(envelope, ErrorEnvelope)
        assert envelope.code == ErrorCode.NOT_FOUND
        assert envelope.msg == "Resource not found"
        assert envelope.details == {"resource_id": 42}

    def test_http_error_response_formatter(self):
        """Test http_error_response formatter."""
        error = http_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            msg="Invalid name",
            details={"field": "name", "constraint": "min_length"},
        )

        assert isinstance(error, HTTPErrorResponse)
        assert error.error.code == ErrorCode.VALIDATION_ERROR
        assert error.error.msg == "Invalid name"
        assert error.error.details == {"field": "name", "constraint": "min_length"}

    def test_ws_error_response_formatter(self):
        """Test ws_error_response formatter."""
        req_id = uuid4()
        error = ws_error_response(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            code=ErrorCode.PERMISSION_DENIED,
            msg="User lacks required role",
            status_code=RSPCode.PERMISSION_DENIED,
            details={"required_roles": ["test-role"]},
        )

        assert isinstance(error, WebSocketErrorResponse)
        assert error.pkg_id == PkgID.TEST_HANDLER
        assert error.req_id == req_id
        assert error.status_code == RSPCode.PERMISSION_DENIED
        assert error.data["code"] == ErrorCode.PERMISSION_DENIED
        assert error.data["msg"] == "User lacks required role"
        assert error.data["details"] == {"required_roles": ["test-role"]}


class TestExceptionMapping:
    """Test exception-to-error-code mapping."""

    @pytest.mark.parametrize(
        "exception_class,expected_code",
        [
            (ValidationError, ErrorCode.VALIDATION_ERROR),
            (NotFoundError, ErrorCode.NOT_FOUND),
            (DatabaseError, ErrorCode.DATABASE_ERROR),
            (AuthenticationError, ErrorCode.AUTHENTICATION_FAILED),
            (AuthorizationError, ErrorCode.PERMISSION_DENIED),
            (RateLimitError, ErrorCode.RATE_LIMIT_EXCEEDED),
            (ConflictError, ErrorCode.CONFLICT),
        ],
    )
    def test_exception_to_error_code_mapping(
        self, exception_class, expected_code
    ):
        """Test that each exception maps to correct error code."""
        exception = exception_class("Test error message")
        code = exception_to_error_code(exception)
        assert code == expected_code

    def test_http_error_from_exception(self):
        """Test http_error_from_exception conversion."""
        exception = ValidationError("Invalid name")
        error = http_error_from_exception(
            exception, details={"field": "name"}
        )

        assert isinstance(error, HTTPErrorResponse)
        assert error.error.code == ErrorCode.VALIDATION_ERROR
        assert error.error.msg == "Invalid name"
        assert error.error.details == {"field": "name"}

    def test_ws_error_from_exception(self):
        """Test ws_error_from_exception conversion."""
        exception = AuthorizationError("User lacks role")
        req_id = uuid4()
        error = ws_error_from_exception(
            exception,
            PkgID.TEST_HANDLER,
            req_id,
            details={"required_roles": ["test-role"]},
        )

        assert isinstance(error, WebSocketErrorResponse)
        assert error.pkg_id == PkgID.TEST_HANDLER
        assert error.req_id == req_id
        assert error.status_code == RSPCode.PERMISSION_DENIED
        assert error.data["code"] == ErrorCode.PERMISSION_DENIED
        assert error.data["msg"] == "User lacks role"
        assert error.data["details"] == {"required_roles": ["test-role"]}


class TestErrorEnvelopeConsistency:
    """Test that HTTP and WS error envelopes maintain consistent shapes."""

    def test_http_and_ws_envelope_shape_consistency(self):
        """Test HTTP and WS errors have same inner envelope shape."""
        # Create HTTP error
        http_error = http_error_response(
            code=ErrorCode.NOT_FOUND,
            msg="Resource not found",
            details={"resource_id": 42},
        )

        # Create WS error with same content
        ws_error = ws_error_response(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=uuid4(),
            code=ErrorCode.NOT_FOUND,
            msg="Resource not found",
            status_code=RSPCode.ERROR,
            details={"resource_id": 42},
        )

        # HTTP error envelope
        http_envelope = http_error.error.model_dump()

        # WS error envelope (embedded in data field)
        ws_envelope = ws_error.data

        # Both should have same structure and content
        assert http_envelope["code"] == ws_envelope["code"]
        assert http_envelope["msg"] == ws_envelope["msg"]
        assert http_envelope["details"] == ws_envelope["details"]

    def test_exception_produces_consistent_envelopes(self):
        """Test same exception produces consistent HTTP and WS envelopes."""
        exception = NotFoundError("Resource not found")
        req_id = uuid4()

        # Convert to HTTP error
        http_error = http_error_from_exception(exception)

        # Convert to WS error
        ws_error = ws_error_from_exception(
            exception, PkgID.TEST_HANDLER, req_id
        )

        # Extract envelopes
        http_envelope = http_error.error.model_dump()
        ws_envelope = ws_error.data

        # Should have same code and message
        assert http_envelope["code"] == ws_envelope["code"]
        assert http_envelope["msg"] == ws_envelope["msg"]


class TestErrorCodeConstants:
    """Test error code constant definitions."""

    def test_error_code_constants_exist(self):
        """Test all standard error codes are defined."""
        assert hasattr(ErrorCode, "INVALID_DATA")
        assert hasattr(ErrorCode, "VALIDATION_ERROR")
        assert hasattr(ErrorCode, "NOT_FOUND")
        assert hasattr(ErrorCode, "CONFLICT")
        assert hasattr(ErrorCode, "PERMISSION_DENIED")
        assert hasattr(ErrorCode, "AUTHENTICATION_FAILED")
        assert hasattr(ErrorCode, "DATABASE_ERROR")
        assert hasattr(ErrorCode, "REDIS_ERROR")
        assert hasattr(ErrorCode, "INTERNAL_ERROR")
        assert hasattr(ErrorCode, "RATE_LIMIT_EXCEEDED")

    def test_error_codes_are_snake_case_strings(self):
        """Test error codes follow snake_case convention."""
        codes = [
            ErrorCode.INVALID_DATA,
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.NOT_FOUND,
            ErrorCode.CONFLICT,
            ErrorCode.PERMISSION_DENIED,
            ErrorCode.AUTHENTICATION_FAILED,
            ErrorCode.DATABASE_ERROR,
            ErrorCode.REDIS_ERROR,
            ErrorCode.INTERNAL_ERROR,
            ErrorCode.RATE_LIMIT_EXCEEDED,
        ]

        for code in codes:
            assert isinstance(code, str)
            assert code.islower()
            assert "_" in code or code == code.lower()
