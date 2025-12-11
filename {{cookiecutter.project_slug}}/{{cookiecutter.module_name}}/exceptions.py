"""
Custom exception classes for the application.

This module defines unified exceptions that work across both HTTP and WebSocket
protocols. Each exception has both http_status and ws_status attributes for
consistent error handling.
"""

from {{cookiecutter.module_name}}.api.ws.constants import RSPCode


class AppException(Exception):
    """
    Base exception class for all application exceptions.

    Provides unified error handling across HTTP and WebSocket protocols by
    including both HTTP status codes and WebSocket RSPCode values.

    Attributes:
        message: Human-readable error message.
        http_status: HTTP status code for REST API responses.
        ws_status: RSPCode enum value for WebSocket responses.
    """

    http_status: int = 500
    ws_status: RSPCode = RSPCode.ERROR

    def __init__(self, message: str):
        """
        Initialize the exception with a message.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)


class ValidationError(AppException):
    """
    Data validation failed.

    Raised when input data fails validation checks before processing.

    HTTP Status: 400 Bad Request
    WS Status: RSPCode.INVALID_DATA
    """

    http_status = 400
    ws_status = RSPCode.INVALID_DATA


class NotFoundError(AppException):
    """
    Resource not found.

    Raised when a requested resource does not exist.

    HTTP Status: 404 Not Found
    WS Status: RSPCode.ERROR
    """

    http_status = 404
    ws_status = RSPCode.ERROR


class DatabaseError(AppException):
    """
    Database operation failed.

    Raised when a database operation encounters an error that should be
    handled at the application level.

    HTTP Status: 500 Internal Server Error
    WS Status: RSPCode.ERROR
    """

    http_status = 500
    ws_status = RSPCode.ERROR


class AuthenticationError(AppException):
    """
    Authentication failed.

    Raised when user authentication fails (invalid credentials, expired token, etc.).

    HTTP Status: 401 Unauthorized
    WS Status: RSPCode.PERMISSION_DENIED
    """

    http_status = 401
    ws_status = RSPCode.PERMISSION_DENIED


class AuthorizationError(AppException):
    """
    Authorization failed.

    Raised when a user lacks required permissions for an operation.

    HTTP Status: 403 Forbidden
    WS Status: RSPCode.PERMISSION_DENIED
    """

    http_status = 403
    ws_status = RSPCode.PERMISSION_DENIED


class RateLimitError(AppException):
    """
    Rate limit exceeded.

    Raised when a user or IP exceeds the configured rate limits.

    HTTP Status: 429 Too Many Requests
    WS Status: RSPCode.ERROR
    """

    http_status = 429
    ws_status = RSPCode.ERROR


class RedisError(AppException):
    """
    Redis operation failed.

    Raised when a Redis operation fails and cannot be recovered.

    HTTP Status: 500 Internal Server Error
    WS Status: RSPCode.ERROR
    """

    http_status = 500
    ws_status = RSPCode.ERROR


class ConflictError(AppException):
    """
    Resource conflict.

    Raised when an operation conflicts with existing state (e.g., duplicate entry).

    HTTP Status: 409 Conflict
    WS Status: RSPCode.INVALID_DATA
    """

    http_status = 409
    ws_status = RSPCode.INVALID_DATA
