"""
Base repository with common CRUD operations.

The Repository pattern separates data access logic from business logic,
making it easier to test and maintain. Repositories encapsulate all
database operations for a specific entity.

Example:
    ```python
    from app.repositories.base import BaseRepository
    from app.models.author import Author


    class AuthorRepository(BaseRepository[Author]):
        def __init__(self, session: AsyncSession):
            super().__init__(session, Author)

        async def get_by_name(self, name: str) -> Author | None:
            stmt = select(Author).where(Author.name == name)
            result = await self.session.exec(stmt)
            return result.first()
    ```
"""

from typing import Any, Generic, Type, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.logging import logger

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.

    This class provides generic CRUD operations that can be inherited
    by specific repository implementations. Each repository operates
    on a single model type.

    Type Parameters:
        T: The SQLModel type this repository manages.

    Attributes:
        session: The database session for executing queries.
        model: The SQLModel class this repository manages.
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        Initialize repository with session and model.

        Args:
            session: Database session for executing queries.
            model: The SQLModel class to manage.
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        """
        Get entity by primary key ID.

        Args:
            id: Primary key value.

        Returns:
            Entity if found, None otherwise.
        """
        return await self.session.get(self.model, id)

    async def get_all(self, **filters: Any) -> list[T]:
        """
        Get all entities matching the provided filters.

        Args:
            **filters: Field name and value pairs to filter by.
                Example: get_all(name="John", age=25)

        Returns:
            List of entities matching all filters.

        Raises:
            SQLAlchemyError: If database query fails.
        """
        try:
            stmt = select(self.model)
            for key, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await self.session.exec(stmt)
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving {self.model.__name__}: {e}")
            raise

    async def create(self, entity: T) -> T:
        """
        Create new entity in database.

        Args:
            entity: The entity instance to create.

        Returns:
            The created entity with generated fields populated.

        Raises:
            SQLAlchemyError: If database operation fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            await self.session.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(self, entity: T) -> T:
        """
        Update existing entity in database.

        Args:
            entity: The entity instance with updated values.

        Returns:
            The updated entity.

        Raises:
            SQLAlchemyError: If database operation fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            await self.session.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise

    async def delete(self, entity: T) -> None:
        """
        Delete entity from database.

        Args:
            entity: The entity instance to delete.

        Raises:
            SQLAlchemyError: If database operation fails.
        """
        try:
            await self.session.delete(entity)
            await self.session.flush()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise

    async def exists(self, **filters: Any) -> bool:
        """
        Check if entity exists matching the provided filters.

        Args:
            **filters: Field name and value pairs to filter by.

        Returns:
            True if at least one entity matches, False otherwise.

        Raises:
            SQLAlchemyError: If database query fails.
        """
        try:
            stmt = select(self.model)
            for key, value in filters.items():
                if value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await self.session.exec(stmt)
            return result.first() is not None
        except SQLAlchemyError as e:
            logger.error(
                f"Error checking existence of {self.model.__name__}: {e}"
            )
            raise
