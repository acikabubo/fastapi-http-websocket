"""
Protocol definition for pagination strategies.

Uses Python's structural subtyping (Protocol) to define the interface for pagination
strategies without requiring explicit inheritance. This follows the same pattern as
app.protocols.Repository.
"""

from typing import Protocol, Type, TypeVar

from sqlalchemy import Select

from app.schemas.generic_typing import GenericSQLModelType
from app.schemas.response import MetadataModel

T = TypeVar("T", bound=GenericSQLModelType)


class PaginationStrategy(Protocol[T]):
    """
    Protocol for pagination strategies.

    Defines the interface that all pagination implementations must follow.
    Any class implementing the paginate() method is considered compatible,
    enabling flexible design while maintaining type safety.

    Type Parameters:
        T: The SQLModel type being paginated.

    Example:
        ```python
        class CustomPaginationStrategy:
            async def paginate(
                self,
                query: Select,
                model: Type[Author],
                page_size: int,
            ) -> tuple[list[Author], MetadataModel]:
                # Custom pagination logic
                ...


        # Type-checks as PaginationStrategy[Author]
        strategy: PaginationStrategy[Author] = CustomPaginationStrategy()
        ```
    """

    async def paginate(
        self,
        query: Select,
        model: Type[T],
        page_size: int,
    ) -> tuple[list[T], MetadataModel]:
        """
        Execute pagination on the provided query.

        Args:
            query: SQLAlchemy Select query with filters and eager loading
                  already applied. The strategy only applies pagination logic.
            model: The SQLModel class being queried (used for count queries
                  and metadata).
            page_size: Number of items per page.

        Returns:
            Tuple of (items, metadata) where:
            - items: List of model instances for this page
            - metadata: Pagination metadata (page, total, next_cursor, etc.)

        Raises:
            ValueError: If pagination parameters are invalid
            SQLAlchemyError: If database query fails
        """
        ...
