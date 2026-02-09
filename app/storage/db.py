import asyncio
import base64
from typing import Any, Callable, Type

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import selectinload, sessionmaker
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.constants import MAX_PAGE_SIZE
from app.logging import logger
from app.schemas.generic_typing import GenericSQLModelType
from app.schemas.response import MetadataModel
from app.settings import app_settings
from app.utils.query_monitor import enable_query_monitoring

# Enable database query performance monitoring
enable_query_monitoring()

engine: AsyncEngine = create_async_engine(
    app_settings.DATABASE_URL,
    echo=False,
    pool_size=app_settings.DB_POOL_SIZE,
    max_overflow=app_settings.DB_MAX_OVERFLOW,
    pool_recycle=app_settings.DB_POOL_RECYCLE,
    pool_pre_ping=app_settings.DB_POOL_PRE_PING,
)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def wait_and_init_db(
    retry_interval: int | None = None,
    max_retries: int | None = None,
) -> None:
    """
    Wait until the database is available.

    Note: Database schema is now managed by Alembic migrations.
    Run 'make migrate' to apply migrations after the database is ready.

    Args:
        retry_interval: Time in seconds between retries.
            Defaults to app_settings.DB_INIT_RETRY_INTERVAL
        max_retries: Maximum number of retries before giving up.
            Defaults to app_settings.DB_INIT_MAX_RETRIES
    """
    if retry_interval is None:
        retry_interval = app_settings.DB_INIT_RETRY_INTERVAL
    if max_retries is None:
        max_retries = app_settings.DB_INIT_MAX_RETRIES
    for attempt in range(max_retries):
        try:
            # Test a lightweight connection to check if the DB is ready
            async with engine.connect() as conn:
                # Simple query to verify connection
                await conn.exec_driver_sql("SELECT 1")
            logger.info("Database is now ready.")
            return  # Database is ready, continue
        except OperationalError:
            logger.warning(
                f"Database not ready, retrying in {retry_interval} seconds... (Attempt {attempt + 1}/{max_retries})"
            )
            await asyncio.sleep(retry_interval)

    logger.error("Failed to connect to the database after multiple attempts.")
    raise RuntimeError("Database connection could not be established.")


async def get_session() -> AsyncSession:
    """
    Get an asynchronous session from the SQLAlchemy session factory.

    Yields:
        AsyncSession: An asynchronous SQLAlchemy session.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except IntegrityError as ex:
            await session.rollback()
            logger.error(f"Database integrity error: {ex}")
            raise
        except SQLAlchemyError as ex:
            await session.rollback()
            logger.error(f"Database error: {ex}")
            raise


def encode_cursor(last_id: int) -> str:
    """
    Encode a cursor from the last item ID for cursor-based pagination.

    Args:
        last_id: The ID of the last item on the current page.

    Returns:
        Base64-encoded cursor string.
    """
    return base64.b64encode(str(last_id).encode()).decode()


def decode_cursor(cursor: str) -> int:
    """
    Decode a cursor to get the last item ID for cursor-based pagination.

    Args:
        cursor: Base64-encoded cursor string.

    Returns:
        The ID of the last item from the previous page.

    Raises:
        ValueError: If cursor is invalid or cannot be decoded.
    """
    try:
        return int(base64.b64decode(cursor).decode())
    except (ValueError, TypeError) as ex:
        raise ValueError(f"Invalid cursor format: {ex}") from ex


async def get_paginated_results(
    model: Type[GenericSQLModelType],
    page: int = 1,
    per_page: int | None = None,
    *,
    filters: dict[str, Any] | PydanticBaseModel | None = None,
    apply_filters: (
        Callable[[Select, Type[GenericSQLModelType], dict[str, Any]], Select]
        | None
    ) = None,
    skip_count: bool = False,
    cursor: str | None = None,
    eager_load: list[str] | None = None,
) -> tuple[list[GenericSQLModelType], MetadataModel]:
    """
    Get paginated results from a SQLModel query with cursor and eager loading support.

    BACKWARD COMPATIBLE FACADE - This function now delegates to strategy classes
    internally while maintaining the same API for existing callers.

    This function supports both offset-based (traditional) and cursor-based pagination.
    Cursor-based pagination provides consistent performance for any page and stable
    results unaffected by concurrent inserts/deletes.

    For new code, consider using strategies directly:
        >>> from app.storage.pagination import OffsetPaginationStrategy
        >>> strategy = OffsetPaginationStrategy(session, page=1)
        >>> items, meta = await strategy.paginate(query, Author, 20)

    Args:
        model (Type[GenericSQLModelType]): The SQLModel class to query.
        page (int, optional): The page number to retrieve (offset pagination). Defaults to 1.
        per_page (int | None, optional): The number of results to return per page. Defaults to app_settings.DEFAULT_PAGE_SIZE. Capped at MAX_PAGE_SIZE.
        filters (dict[str, Any] | PydanticBaseModel | None, optional): Filters to apply to the query. Can be a dict (legacy) or Pydantic BaseModel (type-safe). Pydantic models should inherit from app.schemas.filters.BaseFilter.
        apply_filters (Callable[[Select, Type[GenericSQLModelType], dict[str, Any]], Select] | None, optional): A custom function to apply filters to the query. If not provided, the `default_apply_filters` function will be used.
        skip_count (bool, optional): Skip the count query for performance. When True, total will be 0. Defaults to False.
        cursor (str | None, optional): Base64-encoded cursor for cursor-based pagination. When provided, page parameter is ignored.
        eager_load (list[str] | None, optional): List of relationship names to eager load to prevent N+1 queries.

    Returns:
        tuple[list[GenericSQLModelType], MetadataModel]: A tuple containing the list of results and a `MetadataModel` instance with pagination metadata. When using cursor pagination, next_cursor and has_more fields will be populated.

    Example:
        >>> # Offset-based pagination (traditional)
        >>> authors, meta = await get_paginated_results(
        ...     Author, page=1, per_page=20
        ... )

        >>> # Type-safe filters with Pydantic schema
        >>> from app.schemas.filters import AuthorFilters
        >>> filters = AuthorFilters(name="John")
        >>> authors, meta = await get_paginated_results(
        ...     Author, page=1, per_page=20, filters=filters
        ... )

        >>> # Cursor-based pagination with eager loading (prevents N+1 queries)
        >>> authors, meta = await get_paginated_results(
        ...     Author,
        ...     per_page=20,
        ...     cursor=request.data.get("cursor"),
        ...     eager_load=["books"],  # Load books relationship
        ... )
        >>> # Use meta.next_cursor for next page
    """
    from app.storage.pagination.factory import select_strategy
    from app.storage.pagination.query_builder import (
        build_query,
        convert_filters,
    )

    # Use settings default if not specified, cap at MAX_PAGE_SIZE
    if per_page is None:
        per_page = app_settings.DEFAULT_PAGE_SIZE
    per_page = min(per_page, MAX_PAGE_SIZE)

    # Validate per_page is positive (prevents division by zero)
    if per_page < 1:
        raise ValueError("per_page must be >= 1")

    # Convert filters to dict
    filter_dict = convert_filters(filters)

    # Build query with filters and eager loading
    query = build_query(model, filter_dict, apply_filters, eager_load)

    # Select and execute pagination strategy
    async with async_session() as session:
        strategy = select_strategy(
            session=session,
            cursor=cursor,
            page=page,
            skip_count=skip_count,
            filter_dict=filter_dict,
            apply_filters_func=apply_filters,
        )

        print()
        print(f"STRATEGY: {strategy}")
        print()

        return await strategy.paginate(query, model, per_page)


def default_apply_filters(
    query: Select, model: Type[GenericSQLModelType], filters: dict[str, Any]
) -> Select:
    """
    Apply default filters to a SQLModel query.

    String filters use case-insensitive ILIKE pattern matching with wildcards.
    Other types use exact equality matching or IN clauses for lists/tuples.

    Args:
        query (Select): The SQLModel query to apply filters to.
        model (Type[GenericSQLModelType]): The SQLModel class being queried.
        filters (dict[str, Any]): A dictionary of filters to apply to the query.

    Returns:
        Select: The updated query with the filters applied.

    Raises:
        ValueError: If a filter key is not an attribute of the SQLModel class.
    """
    for key, value in filters.items():
        if hasattr(model, key):
            attr = getattr(model, key)
            if isinstance(value, (list, tuple)):
                query = query.filter(attr.in_(value))
            elif isinstance(value, str):
                # Use case-insensitive ILIKE for string filters
                query = query.filter(attr.ilike(f"%{value}%"))
            else:
                query = query.filter(attr == value)
        else:
            raise ValueError(
                f"Invalid filter: {key} is not an attribute of {model.__name__}"
            )
    return query
