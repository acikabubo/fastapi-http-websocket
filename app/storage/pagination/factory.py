"""
Strategy factory for selecting the appropriate pagination strategy.

Encapsulates the logic for choosing between offset and cursor pagination
based on request parameters.
"""

from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.storage.pagination.cursor import CursorPaginationStrategy
from app.storage.pagination.offset import OffsetPaginationStrategy
from app.storage.pagination.protocol import PaginationStrategy


def select_strategy(
    session: AsyncSession,
    cursor: str | None,
    page: int,
    skip_count: bool,
    filter_dict: dict[str, Any] | None,
    apply_filters_func=None,
) -> PaginationStrategy:
    """
    Select appropriate pagination strategy based on parameters.

    Decision logic:
    - If cursor is provided → CursorPaginationStrategy
    - Otherwise → OffsetPaginationStrategy

    Args:
        session: SQLModel async session for database queries.
        cursor: Base64-encoded cursor for cursor pagination. If provided,
               cursor pagination is used.
        page: Page number for offset pagination (ignored if cursor provided).
        skip_count: Whether to skip count query in offset pagination.
        filter_dict: Filter dictionary for count cache key generation.
        apply_filters_func: Custom filter function for count queries.

    Returns:
        Appropriate pagination strategy instance.

    Example:
        ```python
        from app.storage.pagination import select_strategy

        # Cursor pagination (cursor provided)
        strategy = select_strategy(
            session=session,
            cursor="MTA=",
            page=1,
            skip_count=False,
            filter_dict=None,
        )
        # Returns CursorPaginationStrategy

        # Offset pagination (no cursor)
        strategy = select_strategy(
            session=session,
            cursor=None,
            page=2,
            skip_count=False,
            filter_dict={"name": "John"},
        )
        # Returns OffsetPaginationStrategy
        ```
    """
    if cursor is not None:
        # Use cursor pagination for stable, high-performance pagination
        return CursorPaginationStrategy(session, cursor)
    else:
        # Use offset pagination for traditional page-based navigation
        return OffsetPaginationStrategy(
            session,
            page=page,
            skip_count=skip_count,
            filter_dict=filter_dict,
            apply_filters_func=apply_filters_func,
        )
