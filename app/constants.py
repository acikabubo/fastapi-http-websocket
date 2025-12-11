"""
Application-wide constants.

This module defines named constants for magic numbers throughout the
application, improving code readability, maintainability, and configurability.

Constants are organized by category and can be overridden via settings.py
for environment-specific configuration.
"""

# ============================================================================
# Audit Logging
# ============================================================================

# Maximum number of audit log entries that can be queued before dropping
AUDIT_QUEUE_MAX_SIZE = 10000

# Number of audit logs to batch together for database writes
AUDIT_BATCH_SIZE = 100

# Maximum time (seconds) to wait when collecting a batch before flushing
AUDIT_BATCH_TIMEOUT_SECONDS = 1.0


# ============================================================================
# Database
# ============================================================================

# Maximum number of retries when connecting to the database
DB_MAX_RETRIES = 5

# Delay (seconds) between database connection retry attempts
DB_RETRY_DELAY_SECONDS = 2

# Default number of items per page in paginated results
DEFAULT_PAGE_SIZE = 20

# Maximum allowed page size to prevent excessive database loads
MAX_PAGE_SIZE = 1000


# ============================================================================
# Redis
# ============================================================================

# Default Redis port for connections
REDIS_DEFAULT_PORT = 6379

# Socket timeout (seconds) for Redis operations
REDIS_SOCKET_TIMEOUT_SECONDS = 5

# Connection timeout (seconds) when establishing Redis connections
REDIS_CONNECT_TIMEOUT_SECONDS = 5

# Interval (seconds) between Redis connection health checks
REDIS_HEALTH_CHECK_INTERVAL_SECONDS = 30

# Maximum number of connections in Redis connection pool
REDIS_MAX_CONNECTIONS = 50

# Timeout (seconds) when waiting for Redis messages in pub/sub
REDIS_MESSAGE_TIMEOUT_SECONDS = 1


# ============================================================================
# Background Tasks
# ============================================================================

# Sleep interval (seconds) between task iterations when idle
TASK_SLEEP_INTERVAL_SECONDS = 0.5

# Backoff delay (seconds) when task encounters an error
TASK_ERROR_BACKOFF_SECONDS = 1


# ============================================================================
# Rate Limiting
# ============================================================================

# Default maximum requests per minute for HTTP endpoints
DEFAULT_RATE_LIMIT_PER_MINUTE = 60

# Additional burst allowance for short-term traffic spikes
DEFAULT_RATE_LIMIT_BURST = 10

# Maximum concurrent WebSocket connections per user
DEFAULT_WS_MAX_CONNECTIONS_PER_USER = 5

# Maximum WebSocket messages per minute per user
DEFAULT_WS_MESSAGE_RATE_LIMIT = 100


# ============================================================================
# WebSocket
# ============================================================================

# WebSocket close code for policy violations (RFC 6455)
WS_POLICY_VIOLATION_CODE = 1008

# Timeout (seconds) when closing WebSocket connections gracefully
WS_CLOSE_TIMEOUT_SECONDS = 5


# ============================================================================
# Keycloak / Authentication
# ============================================================================

# Extra buffer time (seconds) added to Keycloak session expiry in Redis
# This ensures Redis expiry slightly outlasts the actual token expiry
KC_SESSION_EXPIRY_BUFFER_SECONDS = 10
