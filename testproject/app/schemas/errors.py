"""
Unified error envelope models for HTTP and WebSocket protocols.

This module defines standardized error response structures that provide
consistent error formatting across both HTTP and WebSocket protocols.

The error envelopes follow a common shape:
- code: Machine-readable error code (string)
- msg: Human-readable error description
- details: Optional additional context (request_id, field errors, etc.)

Example HTTP error response:
    {
        "code": "validation_error",
        "message": "Invalid author name",
        "details": {
            "field": "name",
            "constraint": "min_length"
        }
    }

Example WebSocket error response:
    {
        "pkg_id": 1,
        "req_id": "123e4567-e89b-12d3-a456-426614174000",
        "status_code": 2,
        "data": {
            "code": "validation_error",
            "message": "Invalid author name",
            "details": {
                "field": "name",
                "constraint": "min_length"
            }
        }
    }
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.ws.constants import PkgID, RSPCode


class ErrorEnvelope(BaseModel):
    """
    Unified error envelope structure used across protocols.

    This model provides a consistent error shape that can be embedded
    in both HTTP and WebSocket responses.

    Attributes:
        code: Machine-readable error code for client-side error handling.
        msg: Human-readable error description for display.
        details: Optional additional context (field errors, stack traces, etc.).

    Example:
        ```python
        error = ErrorEnvelope(
            code="author_not_found",
            msg="Author with ID 42 not found",
            details={"author_id": 42, "available_ids": [1, 2, 3]}
        )
        ```
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'validation_error', 'not_found')",
    )
    msg: str = Field(
        ..., description="Human-readable error message"
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional error context and metadata",
    )


class HTTPErrorResponse(BaseModel):
    """
    HTTP error response envelope.

    Used as the JSON body for HTTP error responses. Provides a consistent
    structure for API clients to parse and handle errors.

    This replaces FastAPI's default HTTPException detail structure with
    a more structured error format.

    Attributes:
        error: Embedded error envelope with code, msg, and details.

    Example:
        ```python
        # FastAPI will serialize this to JSON:
        {
            "error": {
                "code": "permission_denied",
                "message": "User lacks create-author role",
                "details": {"required_roles": ["create-author"]}
            }
        }
        ```
    """

    error: ErrorEnvelope = Field(
        ..., description="Error details envelope"
    )


class WebSocketErrorResponse(BaseModel):
    """
    WebSocket error response with embedded error envelope.

    Extends the standard ResponseModel structure to include a structured
    error envelope in the data field.

    The error envelope is embedded in the 'data' field to maintain
    compatibility with existing WebSocket protocol structure.

    Attributes:
        pkg_id: Package identifier from request.
        req_id: Request identifier from request.
        status_code: RSPCode indicating error type.
        data: Error envelope with code, msg, and details.

    Example:
        ```python
        error = WebSocketErrorResponse(
            pkg_id=PkgID.CREATE_AUTHOR,
            req_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            status_code=RSPCode.PERMISSION_DENIED,
            data=ErrorEnvelope(
                code="permission_denied",
                msg="User lacks create-author role",
                details={"required_roles": ["create-author"]}
            ).model_dump()
        )
        ```
    """

    pkg_id: PkgID = Field(frozen=True)
    req_id: UUID = Field(frozen=True)
    status_code: RSPCode = Field(default=RSPCode.ERROR)
    data: dict[str, Any] = Field(
        ...,
        description="Error envelope (code, msg, details)",
    )


# Standard error codes for common scenarios
class ErrorCode:
    """
    Standard error codes for consistent error reporting.

    These codes provide a taxonomy of errors that clients can handle
    programmatically. Use these constants instead of hardcoded strings.

    Categories:
    - Validation errors: INVALID_DATA, VALIDATION_ERROR
    - Resource errors: NOT_FOUND, CONFLICT
    - Permission errors: PERMISSION_DENIED, AUTHENTICATION_FAILED
    - System errors: DATABASE_ERROR, REDIS_ERROR, INTERNAL_ERROR
    - Rate limiting: RATE_LIMIT_EXCEEDED
    """

    # Validation errors
    INVALID_DATA = "invalid_data"
    VALIDATION_ERROR = "validation_error"

    # Resource errors
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"

    # Permission errors
    PERMISSION_DENIED = "permission_denied"
    AUTHENTICATION_FAILED = "authentication_failed"

    # System errors
    DATABASE_ERROR = "database_error"
    REDIS_ERROR = "redis_error"
    INTERNAL_ERROR = "internal_error"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
