from app.logging import logger
from app.schemas.roles import ROLE_CONFIG_SCHEMA
from app.schemas.user import UserModel
from app.settings import ACTIONS_FILE_PATH
from app.utils import read_json_file


class RBACManager:
    __instance = None

    def __init__(self):
        """
        Initializes the RBAC (Role-Based Access Control) manager by reading the role configuration from a JSON file and storing it in the `ws` and `http` attributes.

        The `ws` attribute is a dictionary that maps package IDs to the required role for accessing the corresponding WebSocket endpoint.

        The `http` attribute is a dictionary that maps HTTP request paths and methods to the required role for accessing the corresponding HTTP endpoint.
        """

        __roles = read_json_file(ACTIONS_FILE_PATH, ROLE_CONFIG_SCHEMA)

        self.ws: dict[str, str] = __roles["ws"]
        self.http: dict[str, dict[str, str]] = __roles["http"]

    def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """
        Checks if the user has the required role to access the requested WebSocket endpoint.

        Args:
            pkg_id (int): The ID of the package being accessed.
            user (UserModel): The user making the request.

        Returns:
            bool: True if the user has the required role, False otherwise.
                required_role: str | None = self.ws.get(str(pkg_id))
        """
        required_role = self.ws.get(str(pkg_id))

        has_permission: bool = required_role in user.roles

        if has_permission is False:
            logger.info(f"Permission denied for user {user.username}")

        return has_permission

    def check_http_permission(
        self,
        request,
    ) -> bool:
        """
        Checks if the user has the required role to access the requested HTTP endpoint.

        Args:
            request (fastapi.Request): The incoming HTTP request.

        Returns:
            bool: True if the user has the required role, False otherwise.
        """
        has_permission = True

        # Get required role using request path and method
        required_role: str | None = self.http.get(request.url.path, {}).get(
            request.method
        )

        # If a role is specified for this endpoint and method
        if required_role and required_role not in request.user.obj.roles:
            logger.debug(
                f"The user {request.user.obj.username} made a request to "
                f"{request.method} {request.url.path} but has "
                "insufficient permissions. "
                f"The {required_role} role is required."
            )
            has_permission = False

        return has_permission

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
