from fastapi import Request

from app.logging import logger
from app.schemas.roles import ROLE_CONFIG_SCHEMA
from app.schemas.user import UserModel
from app.settings import app_settings
from app.utils import read_json_file
from app.utils.singleton import SingletonMeta


class RBACManager(metaclass=SingletonMeta):
    """
    Singleton manager for Role-Based Access Control (RBAC).

    Manages permission checking for WebSocket and HTTP endpoints based on
    decorator-based roles (for WS) and actions config file (for HTTP).
    """

    def __init__(self):
        """
        Initializes the RBAC manager.

        HTTP permissions are loaded from actions.json.
        WebSocket permissions are retrieved from the pkg_router decorator registry.
        """
        __roles = read_json_file(
            app_settings.ACTIONS_FILE_PATH, ROLE_CONFIG_SCHEMA
        )

        self.http: dict[str, dict[str, str]] = __roles["http"]

    def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """
        Checks if the user has the required roles to access the WebSocket endpoint.

        Uses decorator-based permissions from pkg_router. If no roles are required,
        endpoint is public and access is granted.

        Args:
            pkg_id (int): The ID of the package being accessed.
            user (UserModel): The user making the request.

        Returns:
            bool: True if the user has all required roles or no roles required, False otherwise.
        """
        # Import here to avoid circular dependency
        from app.routing import pkg_router

        required_roles = pkg_router.get_permissions(pkg_id)

        # If no roles are configured for this pkg_id, allow access (public endpoint)
        if not required_roles:
            return True

        # User must have ALL required roles
        has_permission = all(role in user.roles for role in required_roles)

        if not has_permission:
            logger.info(
                f"Permission denied for user {user.username} on pkg_id {pkg_id}. "
                f"Required roles: {required_roles}, User roles: {user.roles}"
            )

        return has_permission

    def check_http_permission(
        self,
        request: Request,
    ) -> bool:
        """
        Checks if the user has the required role to access the requested HTTP endpoint.

        If no role is configured for the endpoint path and method, access is granted by default.

        Args:
            request (fastapi.Request): The incoming HTTP request.

        Returns:
            bool: True if the user has the required role or no role is required, False otherwise.
        """
        has_permission = True

        # Get required role using request path and method
        required_role: str | None = self.http.get(request.url.path, {}).get(
            request.method
        )

        # If a role is specified for this endpoint and method
        if required_role and required_role not in request.auth.scopes:
            logger.debug(
                f"The user {request.user.username} made a request to "
                f"{request.method} {request.url.path} but has "
                "insufficient permissions. "
                f"The {required_role} role is required."
            )
            has_permission = False

        return has_permission
