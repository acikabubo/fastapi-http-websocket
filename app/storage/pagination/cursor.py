"""
Cursor-based pagination strategy (stable, high-performance).

Implements cursor-based pagination using item IDs as cursors. Best for
APIs, infinite scroll, and real-time feeds where performance and stability
matter more than showing total pages.
"""

from typing import Type

from sqlalchemy import Select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.generic_typing import GenericSQLModelType
from app.schemas.response import MetadataModel
from app.storage.db import decode_cursor, encode_cursor


class CursorPaginationStrategy:
    """
    Cursor-based pagination using last item ID.

    Pros:
    - O(1) performance (always fast, regardless of dataset size)
    - Stable results (no duplicates/skips with concurrent changes)
    - Efficient for real-time feeds
    - Low memory usage

    Cons:
    - Cannot jump to arbitrary pages (only next/previous)
    - No total count (expensive to compute for large datasets)
    - Requires unique, sortable ID field

    Example:
        ```python
        from app.storage.pagination import CursorPaginationStrategy
        from sqlmodel import select
        from app.models.author import Author

        async with async_session() as session:
            # First page
            strategy = CursorPaginationStrategy(session, cursor=None)
            query = select(Author).order_by(Author.id)
            items, meta = await strategy.paginate(query, Author, 20)

            # Next page using cursor from first page
            if meta.next_cursor:
                strategy2 = CursorPaginationStrategy(session, cursor=meta.next_cursor)
                items2, meta2 = await strategy2.paginate(query, Author, 20)
        ```
    """

    def __init__(
        self,
        session: AsyncSession,
        cursor: str | None = None,
    ):
        """
        Initialize cursor pagination strategy.

        Args:
            session: SQLModel async session for database queries.
            cursor: Base64-encoded cursor from previous page (item ID).
                   If None, starts from the beginning.

        Raises:
            ValueError: If cursor is invalid or cannot be decoded.
        """
        self.session = session
        self.cursor = cursor
        self.last_id = decode_cursor(cursor) if cursor else None

    async def paginate(
        self,
        query: Select,
        model: Type[GenericSQLModelType],
        page_size: int,
    ) -> tuple[list[GenericSQLModelType], MetadataModel]:
        """
        Execute cursor-based pagination on the query.

        Args:
            query: SQLAlchemy Select query with filters and eager loading
                  already applied. Must be ordered by ID (ascending).
            model: The SQLModel class being queried.
            page_size: Number of items per page.

        Returns:
            Tuple of (items, metadata) where metadata includes:
            - page: Always 1 (not meaningful for cursor pagination)
            - per_page: Items per page
            - total: Always 0 (count skipped for performance)
            - pages: Always 0 (not applicable)
            - has_more: Whether more results exist
            - next_cursor: Base64-encoded cursor for next page, or None

        Raises:
            ValueError: If cursor is invalid.
            SQLAlchemyError: If database query fails.
        """
        # Apply cursor filter (WHERE id > last_id)
        if self.last_id is not None:
            query = query.where(model.id > self.last_id)

        # Fetch page_size + 1 to detect if there are more results
        data_query = query.limit(page_size + 1)
        results = await self.session.exec(data_query)
        items = results.all()

        # Check for more results
        has_more = len(items) > page_size
        if has_more:
            items = items[:page_size]  # Remove extra item

        # Generate next cursor
        next_cursor = None
        if has_more and items:
            next_cursor = encode_cursor(items[-1].id)

        # Build metadata
        meta = MetadataModel(
            page=1,  # Not meaningful for cursor pagination
            per_page=page_size,
            total=0,  # Skip count for cursor pagination (performance)
            pages=0,  # Not applicable
            has_more=has_more,
            next_cursor=next_cursor,
        )

        return items, meta
