from typing import Optional, Unpack

from sqlmodel import Field, SQLModel, select

from app.db import async_session
from app.schemas.author import AuthorFilters


class Author(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}  # for pydoc

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    @classmethod
    async def create(cls, author: "Author"):
        """
        Creates a new `Author` instance in the database.

        Args:
            author: The `Author` instance to create.

        Returns:
            The created `Author` instance.
        """
        async with async_session() as session:
            async with session.begin():
                session.add(author)

            await session.refresh(author)

            return author

    @classmethod
    async def get_list(
        cls, **filters: Unpack[AuthorFilters]
    ) -> list["Author"]:
        """
        Retrieves a list of `Author` objects based on the provided filters.

        Args:
            **filters: A dictionary of filters to apply to the query. The keys should match the field names of the `Author` model, and the values should be the desired filter values.

        Returns:
            A list of `Author` objects that match the provided filters.
        """
        async with async_session() as s:
            stmt = select(cls).where(
                *[getattr(cls, k) == v for k, v in filters.items()]
            )
            result = await s.exec(stmt)
            authors = result.all()
            return authors
