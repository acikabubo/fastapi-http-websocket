"""
Request body size limit middleware.

Protects against large payload attacks by enforcing a maximum request body size.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.logging import logger
from app.settings import app_settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces maximum request body size.

    Rejects requests with Content-Length header exceeding the configured
    maximum size to prevent denial-of-service attacks via large payloads.
    """

    def __init__(self, app: ASGIApp, max_size: int | None = None):
        """
        Initialize the request size limit middleware.

        Args:
            app: The ASGI application.
            max_size: Maximum request body size in bytes.
                     If None, uses app_settings.MAX_REQUEST_BODY_SIZE.
        """
        super().__init__(app)
        self.max_size = max_size or app_settings.MAX_REQUEST_BODY_SIZE

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        """
        Check request size and reject if too large.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            Response (413 if request too large, otherwise normal response).
        """
        # Get Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                content_length_int = int(content_length)

                if content_length_int > self.max_size:
                    logger.warning(
                        f"Request rejected: body size {content_length_int} bytes "
                        f"exceeds limit of {self.max_size} bytes"
                    )
                    return Response(
                        content=(
                            f"Request body too large. "
                            f"Maximum allowed: {self.max_size} bytes"
                        ),
                        status_code=413,  # Payload Too Large
                        media_type="text/plain",
                    )
            except ValueError:
                # Invalid Content-Length header - let it through,
                # FastAPI will handle invalid requests
                logger.warning(
                    f"Invalid Content-Length header: {content_length}"
                )

        return await call_next(request)
