import math
from typing import Any, Callable, Dict, Optional, Type

from sqlalchemy import Select, inspect
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.generic_typing import GenericSQLModelType
from app.schemas.response import MetadataModel

DB_URL = "postgresql+asyncpg://postgres:postgres@db:5432/app_db"

engine: AsyncEngine = create_async_engine(
    DB_URL, echo=False, poolclass=NullPool
)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_paginated_results(
    session: AsyncSession,
    model: Type[GenericSQLModelType],
    page: int = 1,
    per_page: int = 20,
    filters: Dict[str, Any] | None = None,
    apply_filters: Optional[
        Callable[[Select, Type[GenericSQLModelType], Dict[str, Any]], Select]
    ] = None,
) -> tuple[list[GenericSQLModelType], MetadataModel]:
    """
    Get a paginated set of results from the database with optional filtering.
    Args:
        session (AsyncSession): The database session to use.
        model (Type[GenericSQLModelType]): The SQLModel class to query.
        page (int): The page number to retrieve.
        per_page (int): The number of results to return per page.
        filters (Dict[str, Any]): Optional dictionary of filters to apply.
        apply_filters (Callable): Optional function to apply custom filters.
    Returns:
        Tuple[List[GenericSQLModelType], MetadataModel]: The paginated results and metadata about the pagination.
    """
    query = select(model)

    if filters:
        if apply_filters:
            query = apply_filters(query, model, filters)
        else:
            query = default_apply_filters(query, model, filters)

    # Calculate total
    total_result = await session.exec(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.one()

    # Collect/format meta data
    meta_data = MetadataModel(
        page=page,
        per_page=per_page,
        total=total,
        pages=math.ceil(total / per_page),
    )

    # Get items
    query = query.offset((page - 1) * per_page).limit(per_page)
    results = await session.exec(query)

    return results.all(), meta_data


def default_apply_filters(
    query: Select, model: Type[GenericSQLModelType], filters: Dict[str, Any]
) -> Select:
    """
    Apply default filters to a SQLModel query.

    Args:
        query (Select): The SQLModel query to apply filters to.
        model (Type[GenericSQLModelType]): The SQLModel class being queried.
        filters (Dict[str, Any]): A dictionary of filters to apply to the query.

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
            else:
                query = query.filter(attr == value)
        else:
            raise ValueError(
                f"Invalid filter: {key} is not an attribute of {model.__name__}"
            )
    return query
