"""
Error response formatting utilities for unified error envelopes.

This module provides helper functions to create standardized error responses
for both HTTP and WebSocket protocols using the unified error envelope structure.

The formatters handle conversion from AppException instances to appropriately
formatted error responses while maintaining consistent error shapes.
"""

from typing import Any
from uuid import UUID

from app.api.ws.constants import PkgID, RSPCode
from app.exceptions import AppException
from app.schemas.errors import (
    ErrorCode,
    ErrorEnvelope,
    HTTPErrorResponse,
    WebSocketErrorResponse,
)


def create_error_envelope(
    code: str,
    msg: str,
    details: dict[str, Any] | None = None,
) -> ErrorEnvelope:
    """
    Create a standardized error envelope.

    Args:
        code: Machine-readable error code (use ErrorCode constants).
        msg: Human-readable error message.
        details: Optional additional context.

    Returns:
        ErrorEnvelope with specified fields.

    Example:
        ```python
        envelope = create_error_envelope(
            code=ErrorCode.NOT_FOUND,
            msg="Author not found",
            details={"author_id": 42}
        )
        ```
    """
    return ErrorEnvelope(code=code, msg=msg, details=details)


def http_error_response(
    code: str,
    msg: str,
    details: dict[str, Any] | None = None,
) -> HTTPErrorResponse:
    """
    Create HTTP error response with unified envelope.

    Args:
        code: Machine-readable error code (use ErrorCode constants).
        msg: Human-readable error message.
        details: Optional additional context.

    Returns:
        HTTPErrorResponse suitable for FastAPI response_model.

    Example:
        ```python
        error = http_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            msg="Invalid author name",
            details={"field": "name", "constraint": "min_length"}
        )
        return JSONResponse(
            status_code=400,
            content=error.model_dump()
        )
        ```
    """
    envelope = create_error_envelope(code, msg, details)
    return HTTPErrorResponse(error=envelope)


def ws_error_response(
    pkg_id: PkgID,
    req_id: UUID,
    code: str,
    msg: str,
    status_code: RSPCode = RSPCode.ERROR,
    details: dict[str, Any] | None = None,
) -> WebSocketErrorResponse:
    """
    Create WebSocket error response with unified envelope.

    Args:
        pkg_id: Package identifier from request.
        req_id: Request identifier from request.
        code: Machine-readable error code (use ErrorCode constants).
        msg: Human-readable error message.
        status_code: RSPCode indicating error type.
        details: Optional additional context.

    Returns:
        WebSocketErrorResponse ready to send to client.

    Example:
        ```python
        error = ws_error_response(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            code=ErrorCode.PERMISSION_DENIED,
            msg="User lacks required role",
            status_code=RSPCode.PERMISSION_DENIED,
            details={"required_roles": ["create-author"]}
        )
        await websocket.send_json(error.model_dump(mode="json"))
        ```
    """
    envelope = create_error_envelope(code, msg, details)
    return WebSocketErrorResponse(
        pkg_id=pkg_id,
        req_id=req_id,
        status_code=status_code,
        data=envelope.model_dump(),
    )


def exception_to_error_code(exception: AppException) -> str:
    """
    Map AppException types to error codes.

    Args:
        exception: AppException instance.

    Returns:
        Corresponding error code string.

    Example:
        ```python
        try:
            ...
        except ValidationError as ex:
            code = exception_to_error_code(ex)  # Returns "validation_error"
        ```
    """
    from app.exceptions import (
        AuthenticationError,
        AuthorizationError,
        ConflictError,
        DatabaseError,
        NotFoundError,
        RateLimitError,
        RedisError,
        ValidationError,
    )

    # Map exception types to error codes
    exception_map = {
        ValidationError: ErrorCode.VALIDATION_ERROR,
        NotFoundError: ErrorCode.NOT_FOUND,
        DatabaseError: ErrorCode.DATABASE_ERROR,
        AuthenticationError: ErrorCode.AUTHENTICATION_FAILED,
        AuthorizationError: ErrorCode.PERMISSION_DENIED,
        RateLimitError: ErrorCode.RATE_LIMIT_EXCEEDED,
        RedisError: ErrorCode.REDIS_ERROR,
        ConflictError: ErrorCode.CONFLICT,
    }

    # Return mapped code or default to internal_error
    return exception_map.get(type(exception), ErrorCode.INTERNAL_ERROR)


def http_error_from_exception(
    exception: AppException,
    details: dict[str, Any] | None = None,
) -> HTTPErrorResponse:
    """
    Convert AppException to HTTP error response.

    Args:
        exception: AppException instance.
        details: Optional additional context to include.

    Returns:
        HTTPErrorResponse with error envelope.

    Example:
        ```python
        try:
            await command.execute(data)
        except AppException as ex:
            error = http_error_from_exception(ex)
            return JSONResponse(
                status_code=ex.http_status,
                content=error.model_dump()
            )
        ```
    """
    code = exception_to_error_code(exception)
    return http_error_response(code, exception.message, details)


def ws_error_from_exception(
    exception: AppException,
    pkg_id: PkgID,
    req_id: UUID,
    details: dict[str, Any] | None = None,
) -> WebSocketErrorResponse:
    """
    Convert AppException to WebSocket error response.

    Args:
        exception: AppException instance.
        pkg_id: Package identifier from request.
        req_id: Request identifier from request.
        details: Optional additional context to include.

    Returns:
        WebSocketErrorResponse with error envelope.

    Example:
        ```python
        try:
            await command.execute(data)
        except AppException as ex:
            return ws_error_from_exception(
                ex,
                request.pkg_id,
                request.req_id
            )
        ```
    """
    code = exception_to_error_code(exception)
    return ws_error_response(
        pkg_id,
        req_id,
        code,
        exception.message,
        exception.ws_status,
        details,
    )
