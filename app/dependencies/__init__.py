"""
Dependency injection configuration for FastAPI.

This module provides dependency injection setup for managers, repositories,
and database sessions. Using FastAPI's Depends() system with @lru_cache
provides singleton-like behavior while maintaining testability.

Example:
    ```python
    from fastapi import APIRouter
    from app.dependencies import SessionDep, RBACDep, AuthorRepoDep

    router = APIRouter()


    @router.get("/authors")
    async def get_authors(
        repo: AuthorRepoDep,
        rbac: RBACDep,
    ) -> list[Author]:
        return await repo.get_all()
    ```
"""

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.managers.keycloak_manager import KeycloakManager, keycloak_manager
from app.managers.rbac_manager import RBACManager, rbac_manager
from app.storage.db import get_session

# ============================================================================
# Database Session Dependencies
# ============================================================================

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ============================================================================
# Manager Dependencies
# ============================================================================


@lru_cache
def get_rbac_manager() -> RBACManager:
    """
    Get RBAC manager instance.

    Returns the module-level singleton rbac_manager instance.
    Can be overridden in tests using app.dependency_overrides.

    Returns:
        RBACManager singleton instance.
    """
    return rbac_manager


@lru_cache
def get_keycloak_manager() -> KeycloakManager:
    """
    Get Keycloak manager instance.

    Returns the module-level singleton keycloak_manager instance.
    Can be overridden in tests using app.dependency_overrides.

    Returns:
        KeycloakManager singleton instance.
    """
    return keycloak_manager


RBACDep = Annotated[RBACManager, Depends(get_rbac_manager)]
KeycloakDep = Annotated[KeycloakManager, Depends(get_keycloak_manager)]


# ============================================================================
# Repository Dependencies
# ============================================================================


def get_author_repository(session: SessionDep) -> Any:
    """
    Get author repository with injected database session.

    Args:
        session: Database session injected by FastAPI.

    Returns:
        AuthorRepository instance with session.
    """
    from app.repositories.author_repository import AuthorRepository

    return AuthorRepository(session)


AuthorRepoDep = Annotated[Any, Depends(get_author_repository)]
