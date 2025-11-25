from fastapi import Request

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.roles import ROLE_CONFIG_SCHEMA
from {{cookiecutter.module_name}}.schemas.user import UserModel
from {{cookiecutter.module_name}}.settings import app_settings
from {{cookiecutter.module_name}}.utils import read_json_file
from {{cookiecutter.module_name}}.utils.singleton import SingletonMeta


class RBACManager(metaclass=SingletonMeta):
    """
    Singleton manager for Role-Based Access Control (RBAC).

    Manages permission checking for WebSocket and HTTP endpoints based on
    user roles defined in the actions configuration file.
    """

    def __init__(self):
        """
        Initializes the RBAC (Role-Based Access Control) manager by reading the role configuration from a JSON file and storing it in the `ws` and `http` attributes.

        The `ws` attribute is a dictionary that maps package IDs to the required role for accessing the corresponding WebSocket endpoint.

        The `http` attribute is a dictionary that maps HTTP request paths and methods to the required role for accessing the corresponding HTTP endpoint.
        """

        __roles = read_json_file(
            app_settings.ACTIONS_FILE_PATH, ROLE_CONFIG_SCHEMA
        )

        self.ws: dict[str, str] = __roles["ws"]
        self.http: dict[str, dict[str, str]] = __roles["http"]

    def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """
        Checks if the user has the required role to access the requested WebSocket endpoint.

        If no role is configured for the pkg_id, access is granted by default.

        Args:
            pkg_id (int): The ID of the package being accessed.
            user (UserModel): The user making the request.

        Returns:
            bool: True if the user has the required role or no role is required, False otherwise.
        """
        required_role = self.ws.get(str(pkg_id))

        # If no role is configured for this pkg_id, allow access
        if required_role is None:
            return True

        has_permission: bool = required_role in user.roles

        if has_permission is False:
            logger.info(
                f"Permission denied for user {user.username} on pkg_id {pkg_id}. "
                f"Required role: {required_role}"
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
