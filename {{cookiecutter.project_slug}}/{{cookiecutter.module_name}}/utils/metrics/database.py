"""
Prometheus metrics for database operation monitoring.

This module defines metrics for tracking database query durations,
connection pool status, and database errors.
"""

from {{cookiecutter.module_name}}.utils.metrics._helpers import (
    _get_or_create_counter,
    _get_or_create_gauge,
    _get_or_create_histogram,
)

# Database Metrics
db_query_duration_seconds = _get_or_create_histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

db_connections_active = _get_or_create_gauge(
    "db_connections_active", "Number of active database connections"
)

db_query_errors_total = _get_or_create_counter(
    "db_query_errors_total",
    "Total database query errors",
    ["operation", "error_type"],
)

db_slow_queries_total = _get_or_create_counter(
    "db_slow_queries_total",
    "Total number of slow database queries (exceeding threshold)",
    ["operation"],
)

__all__ = [
    "db_query_duration_seconds",
    "db_connections_active",
    "db_query_errors_total",
    "db_slow_queries_total",
]
