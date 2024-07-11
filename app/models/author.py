from typing import Optional, TypedDict, Unpack

from sqlmodel import Field, SQLModel, select


class AuthorFilters(TypedDict):
    id: int
    name: str


class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    @classmethod
    async def get_list(
        cls, session, **filters: Unpack[AuthorFilters]
    ) -> list["Author"]:
        """
        Get a list of authors based on the provided filters.

        Args:
            session: The SQLModel session to use for the database query.
            **filters: Keyword arguments that match the fields of the `AuthorFilters` TypedDict. These filters will be used to narrow down the list of authors returned.

        Returns:
            A list of `Author` instances that match the provided filters.
        """
        stmt = select(cls).where(
            *[getattr(cls, k) == v for k, v in filters.items()]
        )
        result = await session.exec(stmt)
        authors = result.all()
        return authors
