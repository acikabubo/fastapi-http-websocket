"""
HTTP rate limiting middleware.

Provides request rate limiting for HTTP endpoints based on user ID or IP address.
"""

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging import logger
from app.schemas.user import UserModel
from app.settings import app_settings
from app.utils.ip_utils import get_client_ip
from app.utils.rate_limiter import rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on HTTP requests.

    Uses Redis-based sliding window algorithm to track requests per user/IP
    and enforces configurable rate limits.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize the rate limit middleware.

        Args:
            app: The ASGI application.
        """
        super().__init__(app)
        self.enabled = app_settings.RATE_LIMIT_ENABLED
        self.rate_limit = app_settings.RATE_LIMIT_PER_MINUTE
        self.burst_limit = app_settings.RATE_LIMIT_BURST

    async def dispatch(
        self, request: Request, call_next: ASGIApp
    ) -> Response:
        """
        Process the request and enforce rate limits.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            HTTP response, either from the endpoint or a 429 Too Many Requests.
        """
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if app_settings.EXCLUDED_PATHS.match(request.url.path):
            return await call_next(request)

        # Get rate limit key (prefer user_id, fallback to IP)
        rate_limit_key = self._get_rate_limit_key(request)

        # Check rate limit
        is_allowed, remaining = await rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=self.rate_limit,
            window_seconds=60,
            burst=self.burst_limit,
        )

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {rate_limit_key} "
                f"on {request.method} {request.url.path}"
            )
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(self.rate_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "60",
                    "Retry-After": "60",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = "60"

        return response

    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Get the rate limit key from the request.

        Prefers user ID from authentication, falls back to safely extracted
        client IP address (with protection against IP spoofing).

        Args:
            request: The HTTP request.

        Returns:
            Rate limit key string.
        """
        # Try to get user from request (set by authentication middleware)
        user: UserModel = getattr(request, "user", None)

        if user and user.username:
            return f"user:{user.username}"

        # Fallback to client IP (safely extracted with spoofing protection)
        client_ip = get_client_ip(request)
        return f"ip:{client_ip}"
