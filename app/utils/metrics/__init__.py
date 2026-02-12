"""
Prometheus metrics definitions and utilities.

This module provides a centralized export of all Prometheus metrics used
throughout the application. Metrics are organized into logical submodules
by subsystem (HTTP, WebSocket, database, Redis, auth, audit).

For backward compatibility, all metrics are re-exported here so existing
imports continue to work:

    from app.utils.metrics import http_requests_total
    from app.utils.metrics import ws_connections_active
    from app.utils.metrics import db_query_duration_seconds

New code should use the MetricsCollector facade for better maintainability:

    from app.utils.metrics import MetricsCollector
    MetricsCollector.record_ws_message_received()
"""

from app.utils.metrics._helpers import (
    _get_or_create_counter,
    _get_or_create_gauge,
)
from app.utils.metrics.collector import MetricsCollector

# Import all metrics from submodules
from app.utils.metrics.audit import (
    audit_batch_size,
    audit_log_creation_duration_seconds,
    audit_log_errors_total,
    audit_logs_dropped_total,
    audit_logs_total,
    audit_logs_written_total,
    audit_queue_size,
)
from app.utils.metrics.circuit_breaker import (
    circuit_breaker_failures_total,
    circuit_breaker_state,
    circuit_breaker_state_changes_total,
)
from app.utils.metrics.auth import (
    auth_attempts_total,
    auth_backend_requests_total,
    auth_token_validations_total,
    keycloak_auth_attempts_total,
    keycloak_operation_duration_seconds,
    keycloak_token_validation_total,
    token_cache_hits_total,
    token_cache_misses_total,
)
from app.utils.metrics.database import (
    db_connections_active,
    db_query_duration_seconds,
    db_query_errors_total,
    db_slow_queries_total,
)
from app.utils.metrics.http import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)
from app.utils.metrics.redis import (
    rate_limit_hits_total,
    redis_operation_duration_seconds,
    redis_operations_total,
    redis_pool_connections_available,
    redis_pool_connections_created_total,
    redis_pool_connections_in_use,
    redis_pool_info,
    redis_pool_max_connections,
)
from app.utils.metrics.websocket import (
    get_active_websocket_connections,
    get_websocket_health_info,
    ws_connections_active,
    ws_connections_total,
    ws_message_processing_duration_seconds,
    ws_messages_received_total,
    ws_messages_sent_total,
)

# Application-level metrics (defined here since they don't fit into a specific category)
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

# Export all metrics for backward compatibility
__all__ = [
    # Metrics Collector Facade (NEW - recommended for new code)
    "MetricsCollector",
    # HTTP metrics
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
    # WebSocket metrics
    "ws_connections_active",
    "ws_connections_total",
    "ws_messages_received_total",
    "ws_messages_sent_total",
    "ws_message_processing_duration_seconds",
    "get_active_websocket_connections",
    "get_websocket_health_info",
    # Database metrics
    "db_query_duration_seconds",
    "db_connections_active",
    "db_query_errors_total",
    "db_slow_queries_total",
    # Redis metrics
    "redis_operations_total",
    "redis_operation_duration_seconds",
    "redis_pool_max_connections",
    "redis_pool_info",
    "redis_pool_connections_created_total",
    "redis_pool_connections_in_use",
    "redis_pool_connections_available",
    "rate_limit_hits_total",
    # Authentication metrics
    "auth_attempts_total",
    "auth_token_validations_total",
    "keycloak_auth_attempts_total",
    "keycloak_token_validation_total",
    "keycloak_operation_duration_seconds",
    "auth_backend_requests_total",
    "token_cache_hits_total",
    "token_cache_misses_total",
    # Audit metrics
    "audit_logs_total",
    "audit_log_creation_duration_seconds",
    "audit_log_errors_total",
    "audit_queue_size",
    "audit_logs_written_total",
    "audit_logs_dropped_total",
    "audit_batch_size",
    # Application metrics
    "app_errors_total",
    "app_info",
    # Circuit breaker metrics
    "circuit_breaker_state",
    "circuit_breaker_state_changes_total",
    "circuit_breaker_failures_total",
]
