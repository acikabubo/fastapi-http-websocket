"""
Custom exception classes for the application.

This module defines custom exceptions for better error handling and
more specific error reporting throughout the application.
"""


class DatabaseError(Exception):
    """
    Database operation failed.

    Raised when a database operation encounters an error that should be
    handled at the application level.
    """

    pass


class ValidationError(Exception):
    """
    Data validation failed.

    Raised when input data fails validation checks before processing.
    """

    pass


class RateLimitError(Exception):
    """
    Rate limit exceeded.

    Raised when a user or IP exceeds the configured rate limits.
    """

    pass


class RedisError(Exception):
    """
    Redis operation failed.

    Raised when a Redis operation fails and cannot be recovered.
    """

    pass


class AuthenticationError(Exception):
    """
    Authentication failed.

    Raised when user authentication fails (invalid credentials, expired token, etc.).
    """

    pass


class AuthorizationError(Exception):
    """
    Authorization failed.

    Raised when a user lacks required permissions for an operation.
    """

    pass
