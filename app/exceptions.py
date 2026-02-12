"""
Custom exception classes for the application.

This module defines unified exceptions that work across both HTTP and WebSocket
protocols. Each exception has both http_status and ws_status attributes for
consistent error handling.

All exceptions are self-converting - they know how to convert themselves to
HTTP or WebSocket error responses via to_http_response() and to_ws_response()
methods.
"""

from typing import Any

from app.api.ws.constants import RSPCode
from app.schemas.errors import (
    ErrorCode,
    ErrorEnvelope,
    HTTPErrorResponse,
    WebSocketErrorResponse,
)


class AppException(Exception):
    """
    Base exception class for all application exceptions.

    Provides unified error handling across HTTP and WebSocket protocols by
    including both HTTP status codes and WebSocket RSPCode values.

    All exceptions are self-converting - they can convert themselves to
    HTTP or WebSocket error responses.

    Attributes:
        message: Human-readable error message.
        http_status: HTTP status code for REST API responses.
        ws_status: RSPCode enum value for WebSocket responses.
        error_code: Machine-readable error code string.
    """

    http_status: int = 500
    ws_status: RSPCode = RSPCode.ERROR
    error_code: str = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str):
        """
        Initialize the exception with a message.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)

    def to_http_response(self, details: dict[str, Any] | None = None) -> HTTPErrorResponse:
        """
        Convert exception to HTTP error response.

        Args:
            details: Optional additional context to include.

        Returns:
            HTTPErrorResponse with error envelope.

        Example:
            ```python
            ex = ValidationError("Invalid name")
            response = ex.to_http_response(details={"field": "name"})
            return JSONResponse(
                status_code=ex.http_status,
                content=response.model_dump()
            )
            ```
        """
        return HTTPErrorResponse(
            error=ErrorEnvelope(
                code=self.error_code,
                msg=self.message,
                details=details,
            )
        )

    def to_ws_response(
        self,
        pkg_id: int,
        req_id: str,
        details: dict[str, Any] | None = None,
    ) -> WebSocketErrorResponse:
        """
        Convert exception to WebSocket error response.

        Args:
            pkg_id: Package identifier from request.
            req_id: Request identifier from request.
            details: Optional additional context to include.

        Returns:
            WebSocketErrorResponse with error envelope.

        Example:
            ```python
            ex = NotFoundError("Author not found")
            response = ex.to_ws_response(request.pkg_id, request.req_id)
            return ResponseModel(
                pkg_id=response.pkg_id,
                req_id=response.req_id,
                status_code=response.status_code,
                data=response.data,
            )
            ```
        """
        return WebSocketErrorResponse(
            pkg_id=pkg_id,
            req_id=req_id,
            status_code=self.ws_status,
            data=ErrorEnvelope(
                code=self.error_code,
                msg=self.message,
                details=details,
            ).model_dump(),
        )


class ValidationError(AppException):
    """
    Data validation failed.

    Raised when input data fails validation checks before processing.

    HTTP Status: 400 Bad Request
    WS Status: RSPCode.INVALID_DATA
    Error Code: validation_error
    """

    http_status = 400
    ws_status = RSPCode.INVALID_DATA
    error_code = ErrorCode.VALIDATION_ERROR


class NotFoundError(AppException):
    """
    Resource not found.

    Raised when a requested resource does not exist.

    HTTP Status: 404 Not Found
    WS Status: RSPCode.ERROR
    Error Code: not_found
    """

    http_status = 404
    ws_status = RSPCode.ERROR
    error_code = ErrorCode.NOT_FOUND


class DatabaseError(AppException):
    """
    Database operation failed.

    Raised when a database operation encounters an error that should be
    handled at the application level.

    HTTP Status: 500 Internal Server Error
    WS Status: RSPCode.ERROR
    Error Code: database_error
    """

    http_status = 500
    ws_status = RSPCode.ERROR
    error_code = ErrorCode.DATABASE_ERROR


class AuthenticationError(AppException):
    """
    Authentication failed.

    Raised when user authentication fails (invalid credentials, expired token, etc.).

    HTTP Status: 401 Unauthorized
    WS Status: RSPCode.PERMISSION_DENIED
    Error Code: authentication_failed
    """

    http_status = 401
    ws_status = RSPCode.PERMISSION_DENIED
    error_code = ErrorCode.AUTHENTICATION_FAILED


class AuthorizationError(AppException):
    """
    Authorization failed.

    Raised when a user lacks required permissions for an operation.

    HTTP Status: 403 Forbidden
    WS Status: RSPCode.PERMISSION_DENIED
    Error Code: permission_denied
    """

    http_status = 403
    ws_status = RSPCode.PERMISSION_DENIED
    error_code = ErrorCode.PERMISSION_DENIED


class RateLimitError(AppException):
    """
    Rate limit exceeded.

    Raised when a user or IP exceeds the configured rate limits.

    HTTP Status: 429 Too Many Requests
    WS Status: RSPCode.ERROR
    Error Code: rate_limit_exceeded
    """

    http_status = 429
    ws_status = RSPCode.ERROR
    error_code = ErrorCode.RATE_LIMIT_EXCEEDED


class RedisError(AppException):
    """
    Redis operation failed.

    Raised when a Redis operation fails and cannot be recovered.

    HTTP Status: 500 Internal Server Error
    WS Status: RSPCode.ERROR
    Error Code: redis_error
    """

    http_status = 500
    ws_status = RSPCode.ERROR
    error_code = ErrorCode.REDIS_ERROR


class ConflictError(AppException):
    """
    Resource conflict.

    Raised when an operation conflicts with existing state (e.g., duplicate entry).

    HTTP Status: 409 Conflict
    WS Status: RSPCode.INVALID_DATA
    Error Code: conflict
    """

    http_status = 409
    ws_status = RSPCode.INVALID_DATA
    error_code = ErrorCode.CONFLICT
