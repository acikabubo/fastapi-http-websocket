import asyncio
import math
from typing import Any, Callable, Type

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from {{cookiecutter.module_name}}.constants import MAX_PAGE_SIZE
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.generic_typing import GenericSQLModelType
from {{cookiecutter.module_name}}.schemas.response import MetadataModel
from {{cookiecutter.module_name}}.settings import app_settings
from {{cookiecutter.module_name}}.utils.pagination_cache import get_cached_count, set_cached_count
from {{cookiecutter.module_name}}.utils.query_monitor import enable_query_monitoring

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
) -> tuple[list[GenericSQLModelType], MetadataModel]:
    """
    Get paginated results from a SQLModel query with optional count optimization.

    This function executes a SQLModel query, applies any provided filters, and returns the paginated results along with metadata about the query.

    Args:
        model (Type[GenericSQLModelType]): The SQLModel class to query.
        page (int, optional): The page number to retrieve. Defaults to 1.
        per_page (int | None, optional): The number of results to return per page. Defaults to app_settings.DEFAULT_PAGE_SIZE. Capped at MAX_PAGE_SIZE.
        filters (dict[str, Any] | PydanticBaseModel | None, optional): Filters to apply to the query. Can be a dict (legacy) or Pydantic BaseModel (type-safe). Pydantic models should inherit from {{cookiecutter.module_name}}.schemas.filters.BaseFilter.
        apply_filters (Callable[[Select, Type[GenericSQLModelType], dict[str, Any]], Select] | None, optional): A custom function to apply filters to the query. If not provided, the `default_apply_filters` function will be used.
        skip_count (bool, optional): Skip the count query for performance. When True, total will be 0. Defaults to False.

    Returns:
        tuple[list[GenericSQLModelType], MetadataModel]: A tuple containing the list of results and a `MetadataModel` instance with pagination metadata. When skip_count is True, total will be 0 and pages will be 0.
    """
    # Use settings default if not specified, cap at MAX_PAGE_SIZE
    if per_page is None:
        per_page = app_settings.DEFAULT_PAGE_SIZE
    per_page = min(per_page, MAX_PAGE_SIZE)

    # Convert Pydantic filters to dict (backward compatibility)
    filter_dict: dict[str, Any] | None = None
    if filters is not None:
        if isinstance(filters, PydanticBaseModel):
            # Type-safe Pydantic filter schema
            # Use to_dict() method if available (BaseFilter), else model_dump()
            if hasattr(filters, "to_dict"):
                filter_dict = filters.to_dict()  # type: ignore[attr-defined]
            else:
                # Fallback for custom Pydantic models without to_dict()
                filter_dict = {
                    k: v
                    for k, v in filters.model_dump().items()
                    if v is not None
                }
        else:
            # Legacy dict filters
            filter_dict = filters

    query: Select = select(model)

    if filter_dict:
        if apply_filters:
            query = apply_filters(query, model, filter_dict)
        else:
            query = default_apply_filters(query, model, filter_dict)

    async with async_session() as s:
        # Calculate total
        if skip_count:
            total = 0  # Skip count query for performance
        else:
            # Try to get count from cache first
            model_name = model.__name__
            cached_total = await get_cached_count(model_name, filter_dict)

            if cached_total is not None:
                total = cached_total
            else:
                # More efficient count on primary key instead of subquery
                count_query = select(func.count(model.id))
                if filter_dict:
                    if apply_filters:
                        count_query = apply_filters(
                            count_query, model, filter_dict
                        )
                    else:
                        count_query = default_apply_filters(
                            count_query, model, filter_dict
                        )
                total_result = await s.exec(count_query)
                total = total_result.one()

                # Cache the count result for future requests
                await set_cached_count(model_name, total, filter_dict)

        # Collect/format meta data
        meta_data = MetadataModel(
            page=page,
            per_page=per_page,
            total=total,
            pages=math.ceil(total / per_page) if total > 0 else 0,
        )

        # Get items
        query = query.offset((page - 1) * per_page).limit(per_page)
        results = await s.exec(query)

        return results.all(), meta_data


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
