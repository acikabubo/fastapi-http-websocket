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

from app.schemas import GenericSQLModelType

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
    page: int,
    per_page: int,
) -> list[GenericSQLModelType]:
    """
    Get a paginated list of results from the database for the given model.

    Args:
        session (AsyncSession): The database session to use.
        model (Type[GenericSQLModelType]): The SQLModel class to query.
        page (int): The page number to retrieve (starting from 1).
        per_page (int): The number of results to return per page.

    Returns:
        list[GenericSQLModelType]: A list of the requested page of results.
    """
    # TODO: Add filter
    query = select(model).offset((page - 1) * per_page).limit(per_page)
    results = await session.exec(query)
    return results.all()


async def get_total_count(session: AsyncSession, model: SQLModel) -> int:
    """
    Get the total count of records for the given SQLModel class.

    Args:
        session (AsyncSession): The database session to use.
        model (SQLModel): The SQLModel class to get the total count for.

    Returns:
        int: The total count of records for the given model.
    """
    query = select(func.count()).select_from(model)
    result = await session.exec(query)
    return result.one()
