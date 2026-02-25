"""
Prometheus metrics for database operation monitoring.

This module defines metrics for tracking database query durations,
connection pool status, and database errors.
"""

from fastapi_telemetry import (
    get_or_create_counter,
    get_or_create_gauge,
    get_or_create_histogram,
)

# Database Metrics
db_query_duration_seconds = get_or_create_histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

db_connections_active = get_or_create_gauge(
    "db_connections_active", "Number of active database connections"
)

db_query_errors_total = get_or_create_counter(
    "db_query_errors_total",
    "Total database query errors",
    ["operation", "error_type"],
)

db_slow_queries_total = get_or_create_counter(
    "db_slow_queries_total",
    "Total number of slow database queries (exceeding threshold)",
    ["operation"],
)

# Database Connection Pool Metrics
db_pool_max_connections = get_or_create_gauge(
    "db_pool_max_connections",
    "Maximum connections allowed in database pool",
    ["pool_name"],
)

db_pool_connections_in_use = get_or_create_gauge(
    "db_pool_connections_in_use",
    "Current number of connections checked out from pool",
    ["pool_name"],
)

db_pool_connections_available = get_or_create_gauge(
    "db_pool_connections_available",
    "Current number of idle connections in pool",
    ["pool_name"],
)

db_pool_connections_created_total = get_or_create_counter(
    "db_pool_connections_created_total",
    "Total connections created since pool startup",
    ["pool_name"],
)

db_pool_overflow_count = get_or_create_gauge(
    "db_pool_overflow_count",
    "Current number of overflow connections (beyond pool_size)",
    ["pool_name"],
)

db_pool_info = get_or_create_gauge(
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
