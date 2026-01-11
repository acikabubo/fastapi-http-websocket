"""
Prometheus metrics for HTTP request monitoring.

This module defines metrics for tracking HTTP request rates, durations,
and in-progress requests.
"""

from {{cookiecutter.module_name}}.utils.metrics._helpers import (
    _get_or_create_counter,
    _get_or_create_gauge,
    _get_or_create_histogram,
)

# HTTP Request Metrics
http_requests_total = _get_or_create_counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = _get_or_create_histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

http_requests_in_progress = _get_or_create_gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

__all__ = [
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
]
