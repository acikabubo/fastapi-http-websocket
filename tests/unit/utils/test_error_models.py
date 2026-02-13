"""
Tests for unified error envelope models.

Tests verify that:
- Error envelope models serialize correctly
- HTTP and WebSocket error responses have consistent shapes
- Error code constants are properly defined
"""

from uuid import uuid4

from app.api.ws.constants import PkgID, RSPCode
from app.schemas.errors import (
    ErrorCode,
    ErrorEnvelope,
    HTTPErrorResponse,
    WebSocketErrorResponse,
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
        assert envelope.details == {
            "field": "name",
            "constraint": "min_length",
        }

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
            pkg_id=PkgID.CREATE_AUTHOR,
            req_id=req_id,
            status_code=RSPCode.INVALID_DATA,
            data={
                "code": "validation_error",
                "msg": "Invalid data",
                "details": {"field": "name"},
            },
        )

        assert error.pkg_id == PkgID.CREATE_AUTHOR
        assert error.req_id == req_id
        assert error.status_code == RSPCode.INVALID_DATA
        assert error.data["code"] == "validation_error"
        assert error.data["msg"] == "Invalid data"

        # Test serialization
        data = error.model_dump(mode="json")
        assert data["pkg_id"] == PkgID.CREATE_AUTHOR
        assert data["status_code"] == RSPCode.INVALID_DATA
        assert data["data"]["code"] == "validation_error"


class TestErrorEnvelopeConsistency:
    """Test that HTTP and WS error envelopes maintain consistent shapes."""

    def test_http_and_ws_envelope_shape_consistency(self):
        """Test HTTP and WS errors have same inner envelope shape."""
        # Create HTTP error
        http_error = HTTPErrorResponse(
            error=ErrorEnvelope(
                code=ErrorCode.NOT_FOUND,
                msg="Resource not found",
                details={"resource_id": 42},
            )
        )

        # Create WS error with same content
        ws_error = WebSocketErrorResponse(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=uuid4(),
            status_code=RSPCode.ERROR,
            data=ErrorEnvelope(
                code=ErrorCode.NOT_FOUND,
                msg="Resource not found",
                details={"resource_id": 42},
            ).model_dump(),
        )

        # HTTP error envelope
        http_envelope = http_error.error.model_dump()

        # WS error envelope (embedded in data field)
        ws_envelope = ws_error.data

        # Both should have same structure and content
        assert http_envelope["code"] == ws_envelope["code"]
        assert http_envelope["msg"] == ws_envelope["msg"]
        assert http_envelope["details"] == ws_envelope["details"]


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
