"""
Prometheus metrics definitions and utilities.

This module defines all Prometheus metrics used throughout the application
for monitoring HTTP requests, WebSocket connections, database operations,
and other application behavior.
"""

from prometheus_client import Counter, Gauge, Histogram

# HTTP Request Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
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

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

# WebSocket Connection Metrics
ws_connections_active = Gauge(
    "ws_connections_active", "Number of active WebSocket connections"
)

ws_connections_total = Counter(
    "ws_connections_total",
    "Total WebSocket connections",
    ["status"],  # accepted, rejected_auth, rejected_limit
)

ws_messages_received_total = Counter(
    "ws_messages_received_total", "Total WebSocket messages received"
)

ws_messages_sent_total = Counter(
    "ws_messages_sent_total", "Total WebSocket messages sent"
)

ws_message_processing_duration_seconds = Histogram(
    "ws_message_processing_duration_seconds",
    "WebSocket message processing duration in seconds",
    ["pkg_id"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Database Metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

db_connections_active = Gauge(
    "db_connections_active", "Number of active database connections"
)

db_query_errors_total = Counter(
    "db_query_errors_total",
    "Total database query errors",
    ["operation", "error_type"],
)

# Redis Metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],  # operation: get, set, delete, etc; status: success, error
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

redis_pool_max_connections = Gauge(
    "redis_pool_max_connections",
    "Maximum number of connections allowed in Redis pool",
    ["db"],
)

redis_pool_info = Gauge(
    "redis_pool_info",
    "Redis connection pool configuration info",
    ["db", "host", "port", "socket_timeout", "connect_timeout", "health_check_interval"],
)

# Rate Limiting Metrics
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits (requests that exceeded limits)",
    ["limit_type"],  # http, ws_connection, ws_message
)

# Authentication Metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["status"],  # success, failure, expired
)

auth_token_validations_total = Counter(
    "auth_token_validations_total",
    "Total token validation attempts",
    ["status"],  # valid, invalid, expired
)

# Application Metrics
app_errors_total = Counter(
    "app_errors_total",
    "Total application errors",
    ["error_type", "handler"],  # error_type: validation, database, auth, etc
)

app_info = Gauge(
    "app_info",
    "Application information",
    ["version", "python_version", "environment"],
)
{% if cookiecutter.enable_audit_logging == "yes" %}
# Audit Logging Metrics
audit_logs_total = Counter(
    "audit_logs_total",
    "Total audit log entries created",
    ["outcome"],  # success, error, permission_denied
)

audit_log_creation_duration_seconds = Histogram(
    "audit_log_creation_duration_seconds",
    "Audit log creation duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

audit_log_errors_total = Counter(
    "audit_log_errors_total",
    "Total audit log creation errors",
    ["error_type"],
)
{% endif %}
