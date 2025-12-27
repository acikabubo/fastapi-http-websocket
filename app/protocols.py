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

from typing import Any, Protocol, TypeVar, runtime_checkable

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
