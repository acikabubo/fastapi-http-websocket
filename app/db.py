from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

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
