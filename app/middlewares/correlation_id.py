"""
Middleware for request correlation ID tracking.

This middleware adds correlation IDs to requests for distributed tracing
and cross-service request tracking.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for storing correlation ID per request
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests for distributed tracing.

    This middleware:
    - Extracts correlation ID from X-Correlation-ID header or generates new 8-char UUID
    - Limits all correlation IDs to 8 characters for consistency
    - Stores correlation ID in request.state.request_id for other middleware
    - Stores correlation ID in context variable for access in handlers/logging
    - Adds correlation ID to response headers for client tracking

    The correlation ID can be accessed anywhere in the request context using:
        from app.middlewares.correlation_id import get_correlation_id
        cid = get_correlation_id()
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and add correlation ID.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            Response with X-Correlation-ID header added.
        """
        # Get correlation ID from header or generate new one (8 chars)
        cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])

        # Ensure correlation ID is limited to 8 characters
        cid = cid[:8]

        # Store in request.state for access by other middleware (e.g., audit)
        request.state.request_id = cid

        # Store in context variable for logging
        correlation_id.set(cid)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers for client tracking
        response.headers["X-Correlation-ID"] = cid

        return response


def get_correlation_id() -> str:
    """
    Get the correlation ID for the current request context.

    Returns:
        The correlation ID string, or empty string if not set.

    Example:
        >>> from app.middlewares.correlation_id import get_correlation_id
        >>> cid = get_correlation_id()
        >>> logger.info(f"Processing request {cid}")
    """
    return correlation_id.get()
