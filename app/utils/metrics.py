"""
Prometheus metrics definitions and utilities.

This module defines all Prometheus metrics used throughout the application
for monitoring HTTP requests, WebSocket connections, database operations,
and other application behavior.
"""

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


def _get_or_create_counter(name: str, doc: str, labels: list[str] | None = None):
    """
    Get existing counter or create new one.

    Prevents duplicate registration errors during development with --reload.
    """
    try:
        return Counter(name, doc, labels or [])
    except ValueError:
        # Metric already exists, retrieve it from registry
        return REGISTRY._names_to_collectors[name]


def _get_or_create_gauge(name: str, doc: str, labels: list[str] | None = None):
    """
    Get existing gauge or create new one.

    Prevents duplicate registration errors during development with --reload.
    """
    try:
        return Gauge(name, doc, labels or [])
    except ValueError:
        # Metric already exists, retrieve it from registry
        return REGISTRY._names_to_collectors[name]


def _get_or_create_histogram(name: str, doc: str, labels: list[str] | None = None, buckets=None):
    """
    Get existing histogram or create new one.

    Prevents duplicate registration errors during development with --reload.
    """
    try:
        if buckets:
            return Histogram(name, doc, labels or [], buckets=buckets)
        return Histogram(name, doc, labels or [])
    except ValueError:
        # Metric already exists, retrieve it from registry
        return REGISTRY._names_to_collectors[name]

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

# WebSocket Connection Metrics
ws_connections_active = _get_or_create_gauge(
    "ws_connections_active", "Number of active WebSocket connections"
)

ws_connections_total = _get_or_create_counter(
    "ws_connections_total",
    "Total WebSocket connections",
    ["status"],  # accepted, rejected_auth, rejected_limit
)

ws_messages_received_total = _get_or_create_counter(
    "ws_messages_received_total", "Total WebSocket messages received"
)

ws_messages_sent_total = _get_or_create_counter(
    "ws_messages_sent_total", "Total WebSocket messages sent"
)

ws_message_processing_duration_seconds = _get_or_create_histogram(
    "ws_message_processing_duration_seconds",
    "WebSocket message processing duration in seconds",
    ["pkg_id"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
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

# Redis Metrics
redis_operations_total = _get_or_create_counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],  # operation: get, set, delete, etc; status: success, error
)

redis_operation_duration_seconds = _get_or_create_histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# Rate Limiting Metrics
rate_limit_hits_total = _get_or_create_counter(
    "rate_limit_hits_total",
    "Total rate limit hits (requests that exceeded limits)",
    ["limit_type"],  # http, ws_connection, ws_message
)

# Authentication Metrics
auth_attempts_total = _get_or_create_counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["status"],  # success, failure, expired
)

auth_token_validations_total = _get_or_create_counter(
    "auth_token_validations_total",
    "Total token validation attempts",
    ["status"],  # valid, invalid, expired
)

# Application Metrics
app_errors_total = _get_or_create_counter(
    "app_errors_total",
    "Total application errors",
    ["error_type", "handler"],  # error_type: validation, database, auth, etc
)

app_info = _get_or_create_gauge(
    "app_info",
    "Application information",
    ["version", "python_version", "environment"],
)

# Audit Logging Metrics
audit_logs_total = _get_or_create_counter(
    "audit_logs_total",
    "Total audit log entries created",
    ["outcome"],  # success, error, permission_denied
)

audit_log_creation_duration_seconds = _get_or_create_histogram(
    "audit_log_creation_duration_seconds",
    "Audit log creation duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

audit_log_errors_total = _get_or_create_counter(
    "audit_log_errors_total",
    "Total audit log creation errors",
    ["error_type"],
)
