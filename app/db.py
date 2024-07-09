import math
from typing import Type

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.generic import GenericSQLModelType
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
) -> tuple[list[GenericSQLModelType], MetadataModel]:
    """
    Get a paginated set of results from the database.

    Args:
        session (AsyncSession): The database session to use.
        model (Type[GenericSQLModelType]): The SQLModel class to query.
        page (int): The page number to retrieve.
        per_page (int): The number of results to return per page.

    Returns:
        Tuple[List[GenericSQLModelType], MetadataModel]: The paginated results and metadata about the pagination.
    """
    # TODO: Add filter
    # Calculate total
    total_result = await session.exec(select(func.count()).select_from(model))
    total = total_result.one()

    # Collect/format meta data
    meta_data = MetadataModel(
        page=page,
        per_page=per_page,
        total=total,
        pages=math.ceil(total / per_page),
    )

    # Get items
    results = await session.exec(
        select(model).offset((page - 1) * per_page).limit(per_page)
    )

    return results.all(), meta_data
