"""
Prometheus metrics middleware for HTTP requests.

This middleware automatically tracks HTTP request metrics including
request counts, duration, and in-progress requests.
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
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

        # Increment in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        # Track request duration
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Track successful request
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method, endpoint=path
            ).observe(duration)

            http_requests_total.labels(
                method=method, endpoint=path, status_code=response.status_code
            ).inc()

            return response

        except Exception as exc:
            # Track failed request
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method, endpoint=path
            ).observe(duration)

            # Track as 500 error
            http_requests_total.labels(
                method=method, endpoint=path, status_code=500
            ).inc()

            raise exc

        finally:
            # Decrement in-progress requests
            http_requests_in_progress.labels(
                method=method, endpoint=path
            ).dec()
