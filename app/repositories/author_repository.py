"""
Repository for Author entity with specialized query methods.

This repository extends BaseRepository with Author-specific operations
like searching by name pattern.

Example:
    ```python
    from app.repositories.author_repository import AuthorRepository
    from app.storage.db import async_session

    async with async_session() as session:
        repo = AuthorRepository(session)
        authors = await repo.get_all()
        specific = await repo.get_by_name("John Doe")
        search_results = await repo.search_by_name("John")
    ```
"""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.author import Author
from app.repositories.base import BaseRepository


class AuthorRepository(BaseRepository[Author]):
    """
    Repository for Author entity operations.

    Provides CRUD operations inherited from BaseRepository plus
    Author-specific query methods.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Author repository.

        Args:
            session: Database session for executing queries.
        """
        super().__init__(session, Author)

    async def get_by_name(self, name: str) -> Author | None:
        """
        Get author by exact name match.

        Args:
            name: Exact author name to search for.

        Returns:
            Author if found, None otherwise.
        """
        stmt = select(Author).where(Author.name == name)
        result = await self.session.exec(stmt)
        return result.first()

    async def search_by_name(self, name_pattern: str) -> list[Author]:
        """
        Search authors by name pattern (case-insensitive).

        Args:
            name_pattern: Pattern to search for in author names.
                Performs case-insensitive LIKE search.

        Returns:
            List of authors matching the pattern.

        Example:
            ```python
            # Find all authors with "John" in their name
            results = await repo.search_by_name("John")
            ```
        """
        stmt = select(Author).where(Author.name.ilike(f"%{name_pattern}%"))  # type: ignore[attr-defined]
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_active_authors(self) -> list[Author]:
        """
        Get all active authors.

        This is a placeholder for potential future filtering.
        Currently returns all authors since there's no 'active' field.

        Returns:
            List of all authors.
        """
        return await self.get_all()
