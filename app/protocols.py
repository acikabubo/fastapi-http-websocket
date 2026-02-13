"""
Protocol classes for structural subtyping (duck typing with type safety).

Protocols define interfaces without requiring explicit inheritance. Any class
that implements the required methods is considered compatible, enabling flexible
design while maintaining type safety.

Example:
    ```python
    from app.protocols import Repository
    from app.models.author import Author


    def process_data(repo: Repository[Author]) -> None:
        # Works with any repository implementation
        author = await repo.get_by_id(1)
    ```
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Protocol,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from pybreaker import CircuitBreaker, CircuitBreakerState

T = TypeVar("T")


@runtime_checkable
class Repository(Protocol[T]):
    """
    Protocol for repository pattern.

    Defines the interface for data access objects that manage entities
    of type T. Any class implementing these methods can be used as a
    repository, regardless of inheritance.

    Type Parameters:
        T: The entity type this repository manages.
    """

    async def get_by_id(self, id: int) -> T | None:
        """
        Get entity by primary key ID.

        Args:
            id: Primary key value.

        Returns:
            Entity if found, None otherwise.
        """
        ...

    async def get_all(self, **filters: Any) -> list[T]:
        """
        Get all entities matching the provided filters.

        Args:
            **filters: Field name and value pairs to filter by.

        Returns:
            List of entities matching all filters.
        """
        ...

    async def create(self, entity: T) -> T:
        """
        Create new entity in database.

        Args:
            entity: The entity instance to create.

        Returns:
            The created entity with generated fields populated.
        """
        ...

    async def update(self, entity: T) -> T:
        """
        Update existing entity in database.

        Args:
            entity: The entity instance with updated values.

        Returns:
            The updated entity.
        """
        ...

    async def delete(self, entity: T) -> None:
        """
        Delete entity from database.

        Args:
            entity: The entity instance to delete.
        """
        ...

    async def exists(self, **filters: Any) -> bool:
        """
        Check if entity exists matching the provided filters.

        Args:
            **filters: Field name and value pairs to filter by.

        Returns:
            True if at least one entity matches, False otherwise.
        """
        ...


@runtime_checkable
class CircuitBreakerListenerProtocol(Protocol):
    """
    Protocol for circuit breaker event listeners.

    Defines the interface for handling circuit breaker events without
    requiring inheritance from pybreaker.CircuitBreakerListener. This
    enables dependency injection and eliminates circular dependencies
    with metrics modules.

    Example:
        ```python
        from app.protocols import CircuitBreakerListenerProtocol


        class MyMetricsListener:
            def before_call(self, cb, func, *args, **kwargs):
                # Track operation start
                pass

            def success(self, cb):
                # Track successful operation
                pass

            def failure(self, cb, exc):
                # Track failed operation
                pass

            def state_change(self, cb, old_state, new_state):
                # Track state transitions
                pass
        ```
    """

    def before_call(
        self,
        cb: "CircuitBreaker",  # noqa: ARG002
        func: Callable[..., Any],  # noqa: ARG002
        *args: Any,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """
        Called before circuit breaker invokes the protected function.

        Args:
            cb: The circuit breaker instance.
            func: The function being called.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        ...

    def success(self, cb: "CircuitBreaker") -> None:  # noqa: ARG002
        """
        Called when the protected function succeeds.

        Args:
            cb: The circuit breaker instance.
        """
        ...

    def failure(self, cb: "CircuitBreaker", exc: BaseException) -> None:  # noqa: ARG002
        """
        Called when the protected function fails.

        Args:
            cb: The circuit breaker instance.
            exc: The exception that was raised.
        """
        ...

    def state_change(
        self,
        cb: "CircuitBreaker",  # noqa: ARG002
        old_state: "CircuitBreakerState | None",  # noqa: ARG002
        new_state: "CircuitBreakerState",  # noqa: ARG002
    ) -> None:
        """
        Called when the circuit breaker state changes.

        Args:
            cb: The circuit breaker instance.
            old_state: The previous state (None on initialization).
            new_state: The new state.
        """
        ...
