"""
Offset-based pagination strategy (traditional page numbers).

Implements traditional offset/limit pagination using page numbers. Best for
user-facing interfaces where users expect "Page 1, 2, 3..." navigation.
"""

import math
from typing import Any, Callable, Type

from sqlalchemy import Select
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.generic_typing import GenericSQLModelType
from app.schemas.response import MetadataModel
from app.storage.db import default_apply_filters
from app.utils.pagination_cache import get_cached_count, set_cached_count


class OffsetPaginationStrategy:
    """
    Traditional offset-based pagination (page 1, 2, 3...).

    Pros:
    - User-friendly (page numbers)
    - Shows total pages
    - Allows jumping to any page
    - Count queries cached in Redis

    Cons:
    - O(n) performance for large offsets (database must scan all rows)
    - Inconsistent results with concurrent inserts/deletes (duplicates/gaps)
    - High memory usage for large datasets

    Example:
        ```python
        from app.storage.pagination import OffsetPaginationStrategy
        from sqlmodel import select
        from app.models.author import Author

        async with async_session() as session:
            strategy = OffsetPaginationStrategy(session, page=2)
            query = select(Author).where(Author.name.ilike("%John%"))
            items, meta = await strategy.paginate(query, Author, 20)

            print(f"Page {meta.page} of {meta.pages}")
            print(f"Total items: {meta.total}")
        ```
    """

    def __init__(
        self,
        session: AsyncSession,
        page: int = 1,
        skip_count: bool = False,
        filter_dict: dict[str, Any] | None = None,
        apply_filters_func: Callable[
            [Select[Any], Type[GenericSQLModelType], dict[str, Any]],
            Select[Any],
        ]
        | None = None,
    ):
        """
        Initialize offset pagination strategy.

        Args:
            session: SQLModel async session for database queries.
            page: Page number (1-indexed). Defaults to 1.
            skip_count: If True, skip COUNT query and set total=0.
                       Useful for real-time data where count is expensive.
            filter_dict: Filter dictionary for count cache key generation.
                        Pass the same filters used in query building.
            apply_filters_func: Custom filter function for count query.
                               If None, uses default_apply_filters.
        """
        self.session = session
        self.page = page
        self.skip_count = skip_count
        self.filter_dict = filter_dict
        self.apply_filters_func = apply_filters_func or default_apply_filters

    async def paginate(
        self,
        query: Select[Any],
        model: Type[GenericSQLModelType],
        page_size: int,
    ) -> tuple[list[GenericSQLModelType], MetadataModel]:
        """
        Execute offset-based pagination on the query.

        Args:
            query: SQLAlchemy Select query with filters and eager loading
                  already applied.
            model: The SQLModel class being queried.
            page_size: Number of items per page.

        Returns:
            Tuple of (items, metadata) where metadata includes:
            - page: Current page number
            - per_page: Items per page
            - total: Total item count (0 if skip_count=True)
            - pages: Total page count
            - has_more: Whether more results exist
            - next_cursor: None (not used in offset pagination)

        Raises:
            SQLAlchemyError: If database query fails.
        """
        # Count logic with caching
        total = 0
        if not self.skip_count:
            # Try cache first
            model_name = model.__name__
            cached_total = await get_cached_count(model_name, self.filter_dict)

            if cached_total is not None:
                total = cached_total
            else:
                # Execute count query - build count query
                count_query = select(func.count(model.id))

                # Apply same filters as data query
                if self.filter_dict:
                    count_query = self.apply_filters_func(
                        count_query, model, self.filter_dict
                    )

                total_result = await self.session.exec(count_query)
                total = total_result.one()

                # Cache the count for future requests
                await set_cached_count(model_name, total, self.filter_dict)

        # Apply offset
        offset = (self.page - 1) * page_size
        data_query = query.offset(offset).limit(page_size + 1)

        # Execute query
        results = await self.session.exec(data_query)
        items = results.all()

        # Check for more results (fetched page_size + 1 to detect)
        has_more = len(items) > page_size
        if has_more:
            items = items[:page_size]  # Remove extra item

        # Calculate total pages
        pages = math.ceil(total / page_size) if total > 0 else 0

        # Build metadata
        meta = MetadataModel(
            page=self.page,
            per_page=page_size,
            total=total,
            pages=pages,
            has_more=has_more,
            next_cursor=None,  # Not used in offset pagination
        )

        return items, meta
