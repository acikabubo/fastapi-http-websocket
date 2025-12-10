"""
HTTP audit logging middleware.

Automatically logs all HTTP requests for authenticated users to the audit log.
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.schemas.user import UserModel
from app.settings import app_settings
from app.utils.audit_logger import extract_ip_address, log_user_action


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests to the audit log.

    Captures request details, user information, and response status for
    authenticated users. Excluded paths (health checks, metrics, docs) are
    not logged to reduce noise.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize the audit middleware.

        Args:
            app: The ASGI application.
        """
        super().__init__(app)
        self.enabled = app_settings.AUDIT_LOG_ENABLED

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and log it to the audit log.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            HTTP response from the endpoint.
        """
        if not self.enabled:
            return await call_next(request)

        # Skip audit logging for excluded paths
        if app_settings.EXCLUDED_PATHS.match(request.url.path):
            return await call_next(request)

        # Get user from request (set by AuthBackend)
        user: UserModel | None = getattr(request, "user", None)

        # Only log authenticated requests
        if user is None:
            return await call_next(request)

        # Track request duration
        start_time = time.time()

        # Get request context
        ip_address = extract_ip_address(request)
        user_agent = request.headers.get("user-agent")
        # Get correlation ID set by CorrelationIDMiddleware
        request_id = getattr(request.state, "request_id", None)

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful request
            await log_user_action(
                user_id=user.id,
                username=user.username,
                user_roles=user.roles,
                action_type=request.method,
                resource=request.url.path,
                outcome="success",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                response_status=response.status_code,
                duration_ms=duration_ms,
            )

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log failed request
            await log_user_action(
                user_id=user.id,
                username=user.username,
                user_roles=user.roles,
                action_type=request.method,
                resource=request.url.path,
                outcome="error",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                error_message=str(e),
                duration_ms=duration_ms,
            )

            # Re-raise the exception
            raise
