"""
FastAPI dependencies for role-based access control.

This module provides a convenient standalone function for enforcing
role-based permissions on HTTP endpoints. It delegates to rbac_manager
for unified permission checking across HTTP and WebSocket endpoints.
"""

from app.managers.rbac_manager import rbac_manager


def require_roles(*roles: str):  # type: ignore[no-untyped-def]
    """
    Create a FastAPI dependency that requires the user to have ALL specified roles.

    This is a convenience function that wraps RBACManager.require_roles() to provide
    a cleaner import path for HTTP endpoint decorators. The actual permission checking
    logic is shared with WebSocket handlers through RBACManager.

    Args:
        *roles: Variable number of role names that the user must have.

    Returns:
        A dependency function that checks if the user has all required roles.

    Example:
        ```python
        from fastapi import APIRouter, Depends
        from app.dependencies.permissions import require_roles

        router = APIRouter()


        @router.get(
            "/authors", dependencies=[Depends(require_roles("get-authors"))]
        )
        async def get_authors():
            return {"authors": []}


        @router.post(
            "/admin", dependencies=[Depends(require_roles("admin", "write"))]
        )
        async def admin_action():
            return {"status": "ok"}
        ```

    Raises:
        HTTPException: 401 if user is not authenticated, 403 if user lacks required roles.
    """
    return rbac_manager.require_roles(*roles)
