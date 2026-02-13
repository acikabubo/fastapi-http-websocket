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
    def record_keycloak_login_success(duration: float) -> None:
        """Record successful Keycloak login."""
        from app.utils.metrics import (
            keycloak_auth_attempts_total,
            keycloak_operation_duration_seconds,
        )

        keycloak_auth_attempts_total.labels(
            status="success", method="password"
        ).inc()
        keycloak_operation_duration_seconds.labels(operation="login").observe(
            duration
        )

    @staticmethod
    def record_keycloak_login_failure(duration: float) -> None:
        """Record failed Keycloak login."""
        from app.utils.metrics import (
            keycloak_auth_attempts_total,
            keycloak_operation_duration_seconds,
        )

        keycloak_auth_attempts_total.labels(
            status="failure", method="password"
        ).inc()
        keycloak_operation_duration_seconds.labels(operation="login").observe(
            duration
        )

    @staticmethod
    def record_keycloak_login_error(duration: float) -> None:
        """Record Keycloak login error (service unavailable)."""
        from app.utils.metrics import (
            keycloak_auth_attempts_total,
            keycloak_operation_duration_seconds,
        )

        keycloak_auth_attempts_total.labels(
            status="error", method="password"
        ).inc()
        keycloak_operation_duration_seconds.labels(operation="login").observe(
            duration
        )

    @staticmethod
    def record_token_validation_success(duration: float) -> None:
        """Record successful token validation."""
        from app.utils.metrics import (
            keycloak_operation_duration_seconds,
            keycloak_token_validation_total,
        )

        keycloak_token_validation_total.labels(
            status="valid", reason="success"
        ).inc()
        keycloak_operation_duration_seconds.labels(
            operation="validate_token"
        ).observe(duration)

    @staticmethod
    def record_token_validation_expired(duration: float) -> None:
        """Record expired token validation."""
        from app.utils.metrics import (
            keycloak_operation_duration_seconds,
            keycloak_token_validation_total,
        )

        keycloak_token_validation_total.labels(
            status="expired", reason="token_expired"
        ).inc()
        keycloak_operation_duration_seconds.labels(
            operation="validate_token"
        ).observe(duration)

    @staticmethod
    def record_token_validation_invalid(reason: str, duration: float) -> None:
        """
        Record invalid token validation.

        Args:
            reason: Reason for validation failure (e.g., 'invalid_credentials', 'invalid_signature')
            duration: Validation duration in seconds
        """
        from app.utils.metrics import (
            keycloak_operation_duration_seconds,
            keycloak_token_validation_total,
        )

        keycloak_token_validation_total.labels(
            status="invalid", reason=reason
        ).inc()
        keycloak_operation_duration_seconds.labels(
            operation="validate_token"
        ).observe(duration)

    @staticmethod
    def record_token_validation_error(duration: float) -> None:
        """Record token validation error (service unavailable)."""
        from app.utils.metrics import (
            keycloak_operation_duration_seconds,
            keycloak_token_validation_total,
        )

        keycloak_token_validation_total.labels(
            status="error", reason="service_error"
        ).inc()
        keycloak_operation_duration_seconds.labels(
            operation="validate_token"
        ).observe(duration)

    @staticmethod
    def record_auth_backend_request(request_type: str, outcome: str) -> None:
        """
        Record authentication backend request.

        Args:
            request_type: 'http' or 'websocket'
            outcome: 'success', 'denied', or 'error'
        """
        from app.utils.metrics import auth_backend_requests_total

        auth_backend_requests_total.labels(
            type=request_type, outcome=outcome
        ).inc()

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

    @staticmethod
    def record_db_pool_metrics(
        pool_name: str,
        max_connections: int,
        in_use: int,
        available: int,
        overflow_count: int,
        pool_size: int,
        max_overflow: int,
        timeout: int,
    ) -> None:
        """
        Record database connection pool metrics.

        Args:
            pool_name: Name of the connection pool (e.g., 'main')
            max_connections: Maximum number of connections
            in_use: Number of connections currently checked out
            available: Number of available connections
            overflow_count: Number of overflow connections
            pool_size: Configured pool size
            max_overflow: Configured max overflow
            timeout: Connection timeout in seconds
        """
        from app.utils.metrics.database import (
            db_pool_connections_available,
            db_pool_connections_in_use,
            db_pool_info,
            db_pool_max_connections,
            db_pool_overflow_count,
        )

        db_pool_max_connections.labels(pool_name=pool_name).set(
            max_connections
        )
        db_pool_connections_in_use.labels(pool_name=pool_name).set(in_use)
        db_pool_connections_available.labels(pool_name=pool_name).set(
            available
        )
        db_pool_overflow_count.labels(pool_name=pool_name).set(overflow_count)
        db_pool_info.labels(
            pool_name=pool_name,
            pool_size=str(pool_size),
            max_overflow=str(max_overflow),
            timeout=str(timeout),
        ).set(1)

    # ========== Redis Metrics ==========

    @staticmethod
    def record_redis_pool_info(
        db: int,
        host: str,
        port: int,
        max_connections: int,
        socket_timeout: float,
        connect_timeout: float,
        health_check_interval: int,
    ) -> None:
        """Record Redis pool configuration info."""
        from app.utils.metrics.redis import (
            redis_pool_info,
            redis_pool_max_connections,
        )

        db_label = str(db)
        redis_pool_max_connections.labels(db=db_label).set(max_connections)
        redis_pool_info.labels(
            db=db_label,
            host=host,
            port=str(port),
            socket_timeout=str(socket_timeout),
            connect_timeout=str(connect_timeout),
            health_check_interval=str(health_check_interval),
        ).set(1)

    @staticmethod
    def record_redis_pool_metrics(
        db: int, in_use: int, available: int, created: int
    ) -> None:
        """
        Record Redis connection pool metrics.

        Args:
            db: Redis database number
            in_use: Number of connections in use
            available: Number of available connections
            created: Total connections created
        """
        from app.utils.metrics.redis import (
            redis_pool_connections_available,
            redis_pool_connections_created_total,
            redis_pool_connections_in_use,
        )

        db_label = str(db)
        redis_pool_connections_in_use.labels(db=db_label).set(in_use)
        redis_pool_connections_available.labels(db=db_label).set(available)
        redis_pool_connections_created_total.labels(db=db_label).set(created)

    @staticmethod
    def record_rate_limit_hit(limit_type: str) -> None:
        """
        Record rate limit hit.

        Args:
            limit_type: Type of rate limit ('global', 'per_user', 'per_ip')
        """
        from app.utils.metrics import rate_limit_hits_total

        rate_limit_hits_total.labels(limit_type=limit_type).inc()

    # ========== Circuit Breaker Metrics ==========

    @staticmethod
    def record_circuit_breaker_failure(service: str) -> None:
        """
        Record circuit breaker failure.

        Args:
            service: Service name ('keycloak', 'redis')
        """
        from app.utils.metrics import circuit_breaker_failures_total

        circuit_breaker_failures_total.labels(service=service).inc()

    @staticmethod
    def record_circuit_breaker_state_change(
        service: str, from_state: str, to_state: str
    ) -> None:
        """
        Record circuit breaker state change.

        Args:
            service: Service name ('keycloak', 'redis')
            from_state: Previous state ('closed', 'open', 'half_open')
            to_state: New state ('closed', 'open', 'half_open')
        """
        from app.utils.metrics import (
            circuit_breaker_state,
            circuit_breaker_state_changes_total,
        )

        # Update state gauge (0=closed, 1=open, 2=half_open)
        state_mapping = {"closed": 0, "open": 1, "half_open": 2}
        circuit_breaker_state.labels(service=service).set(
            state_mapping.get(to_state, 0)
        )

        # Track state change
        circuit_breaker_state_changes_total.labels(
            service=service, from_state=from_state, to_state=to_state
        ).inc()

    @staticmethod
    def initialize_circuit_breaker_state(service: str) -> None:
        """
        Initialize circuit breaker to closed state.

        Args:
            service: Service name ('keycloak', 'redis')
        """
        from app.utils.metrics import circuit_breaker_state

        circuit_breaker_state.labels(service=service).set(0)  # 0 = closed

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
    def record_audit_batch_write(batch_size: int, duration: float) -> None:
        """
        Record audit log batch write metrics.

        Args:
            batch_size: Number of logs in batch
            duration: Write duration in seconds
        """
        from app.utils.metrics import (
            audit_batch_size,
            audit_log_creation_duration_seconds,
            audit_logs_written_total,
        )

        audit_batch_size.observe(batch_size)
        audit_logs_written_total.inc(batch_size)
        audit_log_creation_duration_seconds.observe(duration)

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

    @staticmethod
    def set_audit_queue_size(size: int) -> None:
        """
        Set current audit queue size.

        Args:
            size: Number of logs in queue
        """
        from app.utils.metrics import audit_queue_size

        audit_queue_size.set(size)

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

    # ========== Memory Cache Metrics ==========

    @staticmethod
    def record_memory_cache_hit() -> None:
        """Record memory cache hit."""
        from app.utils.metrics.redis import memory_cache_hits_total

        memory_cache_hits_total.inc()

    @staticmethod
    def record_memory_cache_miss() -> None:
        """Record memory cache miss."""
        from app.utils.metrics.redis import memory_cache_misses_total

        memory_cache_misses_total.inc()

    @staticmethod
    def record_memory_cache_eviction() -> None:
        """Record memory cache eviction."""
        from app.utils.metrics.redis import memory_cache_evictions_total

        memory_cache_evictions_total.inc()

    @staticmethod
    def set_memory_cache_size(size: int) -> None:
        """
        Set current memory cache size.

        Args:
            size: Number of entries in cache
        """
        from app.utils.metrics.redis import memory_cache_size

        memory_cache_size.set(size)
