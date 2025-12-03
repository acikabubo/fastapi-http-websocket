from app.logging import logger
from app.schemas.user import UserModel
from app.utils.singleton import SingletonMeta


class RBACManager(metaclass=SingletonMeta):
    """
    Singleton manager for Role-Based Access Control (RBAC).

    Manages permission checking for WebSocket endpoints based on
    decorator-based roles defined in pkg_router.register().
    HTTP permissions are now handled via FastAPI dependencies (require_roles).
    """

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
