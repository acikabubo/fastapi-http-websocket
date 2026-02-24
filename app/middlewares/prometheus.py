"""
Prometheus metrics middleware for HTTP requests.

This middleware automatically tracks HTTP request metrics including
request counts, duration, and in-progress requests.
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.metrics import MetricsCollector


class PrometheusMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    Middleware to track Prometheus metrics for HTTP requests.

    Tracks the following metrics:
    - http_requests_total: Counter of total requests by method, endpoint, and status
    - http_request_duration_seconds: Histogram of request durations
    - http_requests_in_progress: Gauge of in-progress requests
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize the Prometheus middleware.

        Args:
            app: The ASGI application.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        """
        Process the request and track metrics.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or endpoint handler.

        Returns:
            HTTP response from the endpoint.
        """
        # Get method and path
        method = request.method
        path = request.url.path

        # Track request start
        MetricsCollector.record_http_request_start(method, path)

        # Track request duration
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Track successful request completion
            duration = time.time() - start_time
            MetricsCollector.record_http_request_end(
                method, path, response.status_code, duration
            )

            return response

        except Exception as exc:
            # Track failed request
            duration = time.time() - start_time
            MetricsCollector.record_http_request_end(
                method, path, 500, duration
            )
            MetricsCollector.record_app_error(
                error_type=type(exc).__name__, handler=path
            )

            raise exc
