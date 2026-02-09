"""
Pagination strategies for database queries.

This package implements the Strategy pattern for pagination, separating different
pagination algorithms (offset-based, cursor-based) into distinct, testable classes.

Example:
    Using the facade function (backward compatible):
    ```python
    from app.storage.db import get_paginated_results
    from app.models.author import Author

    # Offset pagination
    items, meta = await get_paginated_results(Author, page=1, per_page=20)

    # Cursor pagination
    items, meta = await get_paginated_results(
        Author, cursor="MTA=", per_page=20
    )
    ```

    Using strategies directly (new code):
    ```python
    from app.storage.pagination import OffsetPaginationStrategy
    from sqlmodel import select

    strategy = OffsetPaginationStrategy(session, page=1)
    query = select(Author)
    items, meta = await strategy.paginate(query, Author, 20)
    ```
"""

from app.storage.pagination.cursor import CursorPaginationStrategy
from app.storage.pagination.factory import select_strategy
from app.storage.pagination.offset import OffsetPaginationStrategy
from app.storage.pagination.protocol import PaginationStrategy

__all__ = [
    "PaginationStrategy",
    "OffsetPaginationStrategy",
    "CursorPaginationStrategy",
    "select_strategy",
]
