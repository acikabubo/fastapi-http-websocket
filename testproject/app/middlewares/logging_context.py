"""
Middleware for injecting contextual fields into structured logs.

This middleware adds request-specific information to the log context
that will be included in all log messages during request processing.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.logging import clear_log_context, set_log_context


class LoggingContextMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    Middleware to inject contextual fields into structured logs.

    This middleware:
    - Adds endpoint, method, and status_code to log context
    - Adds user_id if user is authenticated
    - Clears log context after request completes
    - Measures request duration for logging
    """

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        """
        Process request and inject logging context.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            Response from the endpoint.
        """
        # Set initial context
        set_log_context(
            endpoint=request.url.path,
            method=request.method,
        )

        # Add user_id if authenticated
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            if hasattr(user, "user_id"):
                set_log_context(user_id=str(user.user_id))
            elif hasattr(user, "sub"):
                set_log_context(user_id=user.sub)

        # Process request
        response = await call_next(request)

        # Add status code to context
        set_log_context(status_code=response.status_code)

        # Clear context after request
        clear_log_context()

        return response
