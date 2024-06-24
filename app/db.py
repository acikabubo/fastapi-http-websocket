from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel, create_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/app_db"
engine = create_engine(DATABASE_URL, echo=True, future=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())
