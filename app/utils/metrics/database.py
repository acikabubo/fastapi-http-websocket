"""
Prometheus metrics for database operation monitoring.

This module defines metrics for tracking database query durations,
connection pool status, and database errors.
"""

from app.utils.metrics._helpers import (
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

# Database Connection Pool Metrics
db_pool_max_connections = _get_or_create_gauge(
    "db_pool_max_connections",
    "Maximum connections allowed in database pool",
    ["pool_name"],
)

db_pool_connections_in_use = _get_or_create_gauge(
    "db_pool_connections_in_use",
    "Current number of connections checked out from pool",
    ["pool_name"],
)

db_pool_connections_available = _get_or_create_gauge(
    "db_pool_connections_available",
    "Current number of idle connections in pool",
    ["pool_name"],
)

db_pool_connections_created_total = _get_or_create_counter(
    "db_pool_connections_created_total",
    "Total connections created since pool startup",
    ["pool_name"],
)

db_pool_overflow_count = _get_or_create_gauge(
    "db_pool_overflow_count",
    "Current number of overflow connections (beyond pool_size)",
    ["pool_name"],
)

db_pool_info = _get_or_create_gauge(
    "db_pool_info",
    "Database pool configuration metadata",
    ["pool_name", "pool_size", "max_overflow", "timeout"],
)

__all__ = [
    "db_query_duration_seconds",
    "db_connections_active",
    "db_query_errors_total",
    "db_slow_queries_total",
    "db_pool_max_connections",
    "db_pool_connections_in_use",
    "db_pool_connections_available",
    "db_pool_connections_created_total",
    "db_pool_overflow_count",
    "db_pool_info",
]
