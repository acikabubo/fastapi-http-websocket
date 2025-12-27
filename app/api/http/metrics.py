"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get(
    "/metrics",
    response_class=Response,
    summary="Prometheus metrics endpoint",
    tags=["metrics"],
)
async def metrics() -> Response:
    """
    Expose Prometheus metrics for monitoring.

    This endpoint returns all registered Prometheus metrics in the
    text-based exposition format that Prometheus can scrape.

    Returns:
        Response: Metrics in Prometheus text format.

    Example:
        ```
        # HELP http_requests_total Total HTTP requests
        # TYPE http_requests_total counter
        http_requests_total{method="GET",endpoint="/health",status_code="200"} 42.0
        ```
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
