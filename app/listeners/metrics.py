"""
Circuit breaker metrics listener.

Implements circuit breaker event handling to update Prometheus metrics.
This eliminates circular dependencies by separating metric tracking from
circuit breaker initialization.
"""

from typing import Any, Callable

from pybreaker import (
    CircuitBreaker,
    CircuitBreakerListener,
    CircuitBreakerState,
)

from app.logging import logger
from app.utils.metrics import (
    circuit_breaker_failures_total,
    circuit_breaker_state,
    circuit_breaker_state_changes_total,
)


class CircuitBreakerMetricsListener(CircuitBreakerListener):  # type: ignore[misc]
    """
    Listener for circuit breaker events that updates Prometheus metrics.

    Tracks circuit breaker state changes and failures without creating
    circular dependencies. The listener can be injected into any circuit
    breaker to provide metrics tracking.

    Args:
        service_name: Name of the service (e.g., "redis", "keycloak")

    Example:
        ```python
        from pybreaker import CircuitBreaker
        from app.listeners.metrics import CircuitBreakerMetricsListener


        circuit_breaker = CircuitBreaker(
            name="redis",
            listeners=[CircuitBreakerMetricsListener(service_name="redis")],
        )
        ```
    """

    def __init__(self, service_name: str) -> None:
        """
        Initialize the metrics listener.

        Args:
            service_name: Name of the service for metric labels
        """
        self.service_name = service_name

    def before_call(
        self,
        _cb: CircuitBreaker,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Called before circuit breaker calls the function.

        Args:
            _cb: The circuit breaker instance (unused)
            func: The function being called (unused)
            *args: Positional arguments (unused)
            **kwargs: Keyword arguments (unused)
        """
        pass  # No action needed before call

    def success(self, _cb: CircuitBreaker) -> None:
        """
        Called when circuit breaker call succeeds.

        Args:
            _cb: The circuit breaker instance (unused)
        """
        pass  # No action needed on success

    def failure(self, _cb: CircuitBreaker, exc: BaseException) -> None:
        """
        Called when circuit breaker call fails.

        Logs the failure and increments the failure counter metric.

        Args:
            _cb: The circuit breaker instance (unused)
            exc: The exception that was raised
        """
        logger.error(
            f"{self.service_name.capitalize()} circuit breaker failure: {exc}"
        )
        circuit_breaker_failures_total.labels(service=self.service_name).inc()

    def state_change(
        self,
        _cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        """
        Called when circuit breaker state changes.

        Logs the state transition and updates Prometheus metrics:
        - circuit_breaker_state: Current state as numeric value
        - circuit_breaker_state_changes_total: Total state transitions

        Args:
            _cb: The circuit breaker instance (unused)
            old_state: The previous state (None on initialization)
            new_state: The new state
        """
        old_state_name = old_state.name if old_state else "unknown"
        new_state_name = new_state.name

        logger.warning(
            f"{self.service_name.capitalize()} circuit breaker state changed: "
            f"{old_state_name} → {new_state_name}"
        )

        # Map states to numeric values for Gauge metric
        state_mapping = {"closed": 0, "open": 1, "half_open": 2}

        circuit_breaker_state.labels(service=self.service_name).set(
            state_mapping.get(new_state_name, 0)
        )
        circuit_breaker_state_changes_total.labels(
            service=self.service_name,
            from_state=old_state_name,
            to_state=new_state_name,
        ).inc()
