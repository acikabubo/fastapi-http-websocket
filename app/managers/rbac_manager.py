from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.authentication import UnauthenticatedUser

from app.logging import logger
from app.schemas.user import UserModel
from app.utils.singleton import SingletonMeta


class RBACManager(metaclass=SingletonMeta):
    """
    Singleton manager for Role-Based Access Control (RBAC).

    Provides unified role-based permission checking for both WebSocket and HTTP endpoints.
    Uses decorator-based roles defined in pkg_router.register() for WebSocket and
    require_roles() method for HTTP FastAPI dependencies.
    """

    @staticmethod
    def check_user_has_roles(
        user: UserModel, required_roles: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Core role-checking logic: checks if user has ALL required roles.

        Args:
            user: The user to check permissions for.
            required_roles: List of role names that the user must have.

        Returns:
            Tuple of (has_permission, missing_roles):
            - has_permission: True if user has all required roles
            - missing_roles: List of roles the user is missing
        """
        if not required_roles:
            return True, []

        missing_roles = [
            role for role in required_roles if role not in user.roles
        ]
        has_permission = len(missing_roles) == 0

        return has_permission, missing_roles

    def check_ws_permission(
        self,
        pkg_id: int,
        user: UserModel,
        permissions_registry: dict[Any, list[str]],
    ) -> bool:
        """
        Checks if the user has the required roles to access the WebSocket endpoint.

        Uses decorator-based permissions from permissions_registry. If no roles are required,
        endpoint is public and access is granted.

        Args:
            pkg_id: The ID of the package being accessed.
            user: The user making the request.
            permissions_registry: Dictionary mapping package IDs to required roles.

        Returns:
            True if the user has all required roles or no roles required, False otherwise.
        """
        required_roles = permissions_registry.get(pkg_id, [])
        has_permission, missing_roles = self.check_user_has_roles(
            user, required_roles
        )

        if not has_permission:
            logger.info(
                f"Permission denied for user {user.username} on pkg_id {pkg_id}",
                extra={
                    "required_roles": required_roles,
                    "user_roles": user.roles,
                    "missing_roles": list(missing_roles),
                    "pkg_id": pkg_id,
                },
            )

        return has_permission

    def require_roles(
        self, *roles: str
    ) -> Callable[[Request], Awaitable[None]]:
        """
        Create a FastAPI dependency that requires the user to have ALL specified roles.

        This method returns a dependency function that can be used with FastAPI's Depends()
        to enforce role-based access control on HTTP endpoints.

        Args:
            *roles: Variable number of role names that the user must have.

        Returns:
            A dependency function that checks if the user has all required roles.

        Example:
            ```python
            from fastapi import APIRouter, Depends
            from app.managers.rbac_manager import RBACManager

            router = APIRouter()
            rbac = RBACManager()


            @router.get(
                "/authors",
                dependencies=[Depends(rbac.require_roles("get-authors"))],
            )
            async def get_authors():
                return {"authors": []}
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
            if (
                isinstance(request.user, UnauthenticatedUser)
                or not request.user
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user: UserModel = request.user
            has_permission, missing_roles = self.check_user_has_roles(
                user, list(roles)
            )

            if not has_permission:
                logger.info(
                    f"HTTP permission denied for user {user.username} on {request.method} {request.url.path}",
                    extra={
                        "required_roles": list(roles),
                        "user_roles": user.roles,
                        "missing_roles": list(missing_roles),
                        "http_method": request.method,
                        "endpoint": str(request.url.path),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required roles: {', '.join(missing_roles)}",
                )

        return check_roles
