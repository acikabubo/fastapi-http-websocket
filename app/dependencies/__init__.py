"""
Dependency injection configuration for FastAPI.

This module provides dependency injection setup for repositories
and database sessions. Using FastAPI's Depends() system provides
singleton-like behavior while maintaining testability.

Example:
    ```python
    from fastapi import APIRouter
    from app.dependencies import SessionDep, AuthorRepoDep

    router = APIRouter()


    @router.get("/authors")
    async def get_authors(
        repo: AuthorRepoDep,
    ) -> list[Author]:
        return await repo.get_all()
    ```
"""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.repositories.author_repository import AuthorRepository
from app.storage.db import get_session

# ============================================================================
# Database Session Dependencies
# ============================================================================

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ============================================================================
# Repository Dependencies
# ============================================================================


def get_author_repository(session: SessionDep) -> AuthorRepository:
    """
    Get author repository with injected database session.

    Args:
        session: Database session injected by FastAPI.

    Returns:
        AuthorRepository instance with session.
    """
    return AuthorRepository(session)


AuthorRepoDep = Annotated[AuthorRepository, Depends(get_author_repository)]
