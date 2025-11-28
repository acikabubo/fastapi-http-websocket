from typing import Optional, Unpack

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.logging import logger
from app.schemas.author import AuthorFilters


class Author(SQLModel, table=True):
    """
    SQLModel representing an author entity in the database.

    Attributes:
        id: Primary key identifier for the author
        name: Name of the author
    """

    __table_args__ = {"extend_existing": True}  # for pydoc

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    @classmethod
    async def create(
        cls, session: AsyncSession, author: "Author"
    ) -> "Author":
        """
        Creates a new `Author` instance in the database.

        Args:
            session: Database session to use for the operation.
            author: The `Author` instance to create.

        Returns:
            The created `Author` instance.

        Raises:
            IntegrityError: If the author violates database constraints.
            SQLAlchemyError: For other database-related errors.
        """
        try:
            session.add(author)
            await session.flush()
            await session.refresh(author)
            return author
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Integrity error creating author: {e}")
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error creating author: {e}")
            raise

    @classmethod
    async def get_list(
        cls, session: AsyncSession, **filters: Unpack[AuthorFilters]
    ) -> list["Author"]:
        """
        Retrieves a list of `Author` objects based on the provided filters.

        Args:
            session: Database session to use for the operation.
            **filters: A dictionary of filters to apply to the query.
                Keys should match field names of the Author model.

        Returns:
            A list of `Author` objects that match the provided filters.

        Raises:
            SQLAlchemyError: For database-related errors.
        """
        try:
            stmt = select(cls).where(
                *[getattr(cls, k) == v for k, v in filters.items()]
            )
            return (await session.exec(stmt)).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving authors: {e}")
            raise
