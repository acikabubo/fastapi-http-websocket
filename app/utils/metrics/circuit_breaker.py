"""
Circuit breaker metrics for monitoring external service health.

This module provides Prometheus metrics for tracking circuit breaker state
and behavior for external service integrations (Keycloak, Redis).
"""

from app.utils.metrics._helpers import (
    _get_or_create_counter,
    _get_or_create_gauge,
)

# Circuit breaker state gauge (0=closed, 1=open, 2=half_open)
circuit_breaker_state = _get_or_create_gauge(
    "circuit_breaker_state",
    "Current circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"],  # service: keycloak, redis
)

# Circuit breaker state changes counter
circuit_breaker_state_changes_total = _get_or_create_counter(
    "circuit_breaker_state_changes_total",
    "Total circuit breaker state changes",
    ["service", "from_state", "to_state"],
)

# Circuit breaker failures counter
circuit_breaker_failures_total = _get_or_create_counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"],
)

__all__ = [
    "circuit_breaker_state",
    "circuit_breaker_state_changes_total",
    "circuit_breaker_failures_total",
]
