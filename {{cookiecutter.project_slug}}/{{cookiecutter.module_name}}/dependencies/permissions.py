"""
FastAPI dependencies for role-based access control.

This module provides dependency functions that can be used to enforce
role-based permissions on HTTP endpoints using FastAPI's dependency injection.
"""

from fastapi import HTTPException, Request, status
from starlette.authentication import UnauthenticatedUser

from {{cookiecutter.module_name}}.schemas.user import UserModel


def require_roles(*roles: str):
    """
    Create a FastAPI dependency that requires the user to have ALL specified roles.

    This function returns a dependency that can be used with FastAPI's Depends()
    to enforce role-based access control on HTTP endpoints. If the user doesn't
    have all required roles, a 403 Forbidden response is returned.

    Args:
        *roles: Variable number of role names that the user must have.

    Returns:
        A dependency function that checks if the user has all required roles.

    Example:
        ```python
        from fastapi import APIRouter, Depends
        from {{cookiecutter.module_name}}.dependencies.permissions import require_roles

        router = APIRouter()

        @router.get("/authors", dependencies=[Depends(require_roles("get-authors"))])
        async def get_authors():
            return {"authors": []}

        @router.post("/admin", dependencies=[Depends(require_roles("admin", "write"))])
        async def admin_action():
            return {"status": "ok"}
        ```

    Raises:
        HTTPException: 401 if user is not authenticated, 403 if user lacks required roles.
    """

    async def check_roles(request: Request) -> None:
        """
        Dependency function that checks if the authenticated user has required roles.

        Args:
            request: The incoming HTTP request containing user information.

        Raises:
            HTTPException: 401 if not authenticated, 403 if insufficient permissions.
        """
        # Check if user is authenticated
        if isinstance(request.user, UnauthenticatedUser) or not request.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user: UserModel = request.user

        # Check if user has all required roles
        missing_roles = [role for role in roles if role not in user.roles]

        if missing_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(missing_roles)}",
            )

    return check_roles
