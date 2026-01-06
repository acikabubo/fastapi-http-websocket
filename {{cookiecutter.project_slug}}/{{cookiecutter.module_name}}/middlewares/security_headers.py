"""
Security headers middleware.

Adds security-related HTTP headers to all responses to protect against
common web vulnerabilities.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    Middleware that adds security headers to all HTTP responses.

    Headers added:
    - X-Frame-Options: Prevents clickjacking attacks
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-XSS-Protection: Enables XSS filter in older browsers
    - Strict-Transport-Security: Enforces HTTPS connections
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    - Content-Security-Policy: Prevents XSS and injection attacks
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize the security headers middleware.

        Args:
            app: The ASGI application.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        """
        Add security headers to the response.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            Response with security headers added.
        """
        response = await call_next(request)

        # Prevent clickjacking by disallowing iframe embedding
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS filter in older browsers (modern browsers have this by default)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS for 1 year (31536000 seconds)
        # includeSubDomains applies to all subdomains
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Control referrer information sent to other sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Control which browser features can be used
        # Disable geolocation, microphone, camera by default
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Content Security Policy to prevent XSS and injection attacks
        csp_directives = [
            "default-src 'self'",  # Only allow resources from same origin
            "script-src 'self'",  # No inline scripts
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for API docs
            "img-src 'self' data:",  # Allow images from same origin and data URIs
            "font-src 'self'",  # Only load fonts from same origin
            "connect-src 'self' ws: wss:",  # Allow WebSocket connections
            "frame-ancestors 'none'",  # Equivalent to X-Frame-Options: DENY
            "base-uri 'self'",  # Restrict base tag to same origin
            "form-action 'self'",  # Only submit forms to same origin
            "upgrade-insecure-requests",  # Automatically upgrade HTTP to HTTPS
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response
