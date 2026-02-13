"""
Circuit breaker event listeners.

This module provides listener implementations for circuit breaker events,
eliminating circular dependencies by moving metric-tracking logic out of
the manager modules.

The listener pattern allows:
- Separation of concerns (managers handle operations, listeners handle metrics)
- Dependency injection without circular imports
- Static analysis of module dependencies
- Easier testing and mocking

Example:
    ```python
    from pybreaker import CircuitBreaker
    from app.listeners.metrics import CircuitBreakerMetricsListener


    circuit_breaker = CircuitBreaker(
        name="my_service",
        listeners=[CircuitBreakerMetricsListener(service_name="my_service")],
    )
    ```
"""

from app.listeners.metrics import CircuitBreakerMetricsListener

__all__ = ["CircuitBreakerMetricsListener"]
