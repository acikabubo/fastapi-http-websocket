"""
Application-level constants for hardcoded business logic.

These values represent core application behavior and should NEVER be changed
via environment variables or configuration. They are compile-time constants
that define protocol specifications, safety limits, and internal timing.

For configurable values (connection pools, timeouts, rate limits, etc.),
see app/settings.py where values can be overridden via environment variables.
"""

# ============================================================================
# WebSocket Protocol Constants
# ============================================================================

# WebSocket close code for policy violations (RFC 6455 standard)
# Used when rejecting connections due to authentication or rate limiting
WS_POLICY_VIOLATION_CODE = 1008

# Timeout (seconds) when closing WebSocket connections gracefully
# Ensures connections don't hang indefinitely during shutdown
WS_CLOSE_TIMEOUT_SECONDS = 5


# ============================================================================
# Background Task Behavior
# ============================================================================

# Sleep interval (seconds) between task iterations when idle
# Prevents busy-waiting while allowing responsive task loops
TASK_SLEEP_INTERVAL_SECONDS = 0.5

# Backoff delay (seconds) when task encounters an error
# Prevents error loops from overwhelming system resources
TASK_ERROR_BACKOFF_SECONDS = 1


# ============================================================================
# Redis Pub/Sub Behavior
# ============================================================================

# Timeout (seconds) when waiting for Redis messages in pub/sub
# Prevents indefinite blocking while allowing efficient message processing
REDIS_MESSAGE_TIMEOUT_SECONDS = 1


# ============================================================================
# Keycloak / Authentication
# ============================================================================

# Extra buffer time (seconds) added to Keycloak session expiry in Redis
# Ensures Redis expiry slightly outlasts actual token expiry to avoid
# race conditions where token is valid but Redis entry is gone
KC_SESSION_EXPIRY_BUFFER_SECONDS = 10


# ============================================================================
# Pagination Safety Limits
# ============================================================================

# Maximum allowed page size to prevent excessive database loads
# Hard safety limit regardless of what client requests
# For default page size, see app/settings.py (DEFAULT_PAGE_SIZE)
MAX_PAGE_SIZE = 1000
