"""
Facade for centralized metrics emission.

Provides high-level methods for recording metrics without exposing
Prometheus implementation details to the rest of the codebase.
"""


class MetricsCollector:
    """
    Centralized facade for all Prometheus metrics.

    All methods are static for easy use without instantiation.
    Organizes metrics by domain (auth, websocket, database, etc).
    """

    # ========== WebSocket Metrics ==========

    @staticmethod
    def record_ws_connection_accepted() -> None:
        """Record successful WebSocket connection."""
        from app.utils.metrics import (
            ws_connections_active,
            ws_connections_total,
        )

        ws_connections_total.labels(status="accepted").inc()
        ws_connections_active.inc()

    @staticmethod
    def record_ws_connection_rejected(reason: str) -> None:
        """
        Record rejected WebSocket connection.

        Args:
            reason: One of 'auth', 'origin', 'limit'
        """
        from app.utils.metrics import ws_connections_total

        ws_connections_total.labels(status=f"rejected_{reason}").inc()

    @staticmethod
    def record_ws_disconnection() -> None:
        """Record WebSocket disconnection."""
        from app.utils.metrics import ws_connections_active

        ws_connections_active.dec()

    @staticmethod
    def record_ws_message_received() -> None:
        """Record WebSocket message received."""
        from app.utils.metrics import ws_messages_received_total

        ws_messages_received_total.inc()

    @staticmethod
    def record_ws_message_sent() -> None:
        """Record WebSocket message sent."""
        from app.utils.metrics import ws_messages_sent_total

        ws_messages_sent_total.inc()

    @staticmethod
    def record_ws_message_processing(pkg_id: int, duration: float) -> None:
        """
        Record WebSocket message processing duration.

        Args:
            pkg_id: Package ID of the message handler
            duration: Processing duration in seconds
        """
        from app.utils.metrics import ws_message_processing_duration_seconds

        ws_message_processing_duration_seconds.labels(
            pkg_id=str(pkg_id)
        ).observe(duration)

    # ========== Authentication Metrics ==========

    @staticmethod
    def record_token_cache_hit() -> None:
        """Record token cache hit."""
        from app.utils.metrics import token_cache_hits_total

        token_cache_hits_total.inc()

    @staticmethod
    def record_token_cache_miss() -> None:
        """Record token cache miss."""
        from app.utils.metrics import token_cache_misses_total

        token_cache_misses_total.inc()

    # ========== Database Metrics ==========

    @staticmethod
    def record_db_query(
        operation: str, duration: float, slow_threshold: float = 1.0
    ) -> None:
        """
        Record database query duration and track slow queries.

        Args:
            operation: Query operation type ('select', 'insert', 'update', 'delete')
            duration: Query duration in seconds
            slow_threshold: Threshold for slow query detection (default: 1.0s)
        """
        from app.utils.metrics import (
            db_query_duration_seconds,
            db_slow_queries_total,
        )

        db_query_duration_seconds.labels(operation=operation).observe(duration)
        if duration > slow_threshold:
            db_slow_queries_total.labels(operation=operation).inc()

    # ========== Redis Metrics ==========

    @staticmethod
    def record_rate_limit_hit(limit_type: str) -> None:
        """
        Record rate limit hit.

        Args:
            limit_type: Type of rate limit ('per_user', 'per_ip', 'websocket')
        """
        from app.utils.metrics import rate_limit_hits_total

        rate_limit_hits_total.labels(limit_type=limit_type).inc()

    # ========== Audit Metrics ==========

    @staticmethod
    def record_audit_log(outcome: str) -> None:
        """
        Record individual audit log entry.

        Args:
            outcome: Audit log outcome ('success', 'error', 'permission_denied')
        """
        from app.utils.metrics import audit_logs_total

        audit_logs_total.labels(outcome=outcome).inc()

    @staticmethod
    def record_audit_log_error(error_type: str) -> None:
        """
        Record audit log error.

        Args:
            error_type: Python exception type name
        """
        from app.utils.metrics import audit_log_errors_total

        audit_log_errors_total.labels(error_type=error_type).inc()

    @staticmethod
    def record_audit_log_dropped() -> None:
        """Record dropped audit log (queue full)."""
        from app.utils.metrics import audit_logs_dropped_total

        audit_logs_dropped_total.inc()

    # ========== HTTP Metrics ==========

    @staticmethod
    def record_http_request_start(method: str, endpoint: str) -> None:
        """Record HTTP request start."""
        from app.utils.metrics import http_requests_in_progress

        http_requests_in_progress.labels(
            method=method, endpoint=endpoint
        ).inc()

    @staticmethod
    def record_http_request_end(
        method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """
        Record HTTP request completion.

        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: Request path
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        from app.utils.metrics import (
            http_request_duration_seconds,
            http_requests_in_progress,
            http_requests_total,
        )

        http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        http_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)
        http_requests_in_progress.labels(
            method=method, endpoint=endpoint
        ).dec()

    # ========== Application Error Metrics ==========

    @staticmethod
    def record_app_error(error_type: str, handler: str) -> None:
        """
        Record unhandled application error.

        Args:
            error_type: Exception class name (e.g. 'ValueError', 'RuntimeError')
            handler: Name of the handler/endpoint where the error occurred
        """
        from app.utils.metrics import app_errors_total

        app_errors_total.labels(error_type=error_type, handler=handler).inc()
