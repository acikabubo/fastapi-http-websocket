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
from app.storage.db import get_read_session, get_session

# ============================================================================
# Database Session Dependencies
# ============================================================================

SessionDep = Annotated[AsyncSession, Depends(get_session)]
"""Write session — commits on success. Use for handlers that mutate data."""

ReadSessionDep = Annotated[AsyncSession, Depends(get_read_session)]
"""Read-only session — no commit. Use for GET/read handlers to avoid a no-op round-trip."""


# ============================================================================
# Repository Dependencies
# ============================================================================


def get_author_repository(session: SessionDep) -> AuthorRepository:
    """
    Get author repository with injected write database session.

    Args:
        session: Database session injected by FastAPI.

    Returns:
        AuthorRepository instance with session.
    """
    return AuthorRepository(session)


AuthorRepoDep = Annotated[AuthorRepository, Depends(get_author_repository)]


def get_read_author_repository(session: ReadSessionDep) -> AuthorRepository:
    """
    Get author repository with injected read-only database session.

    Use for GET endpoints that do not write to the database.

    Args:
        session: Read-only database session injected by FastAPI.

    Returns:
        AuthorRepository instance with session.
    """
    return AuthorRepository(session)


ReadAuthorRepoDep = Annotated[
    AuthorRepository, Depends(get_read_author_repository)
]
