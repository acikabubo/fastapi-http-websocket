import os
import pkgutil
from importlib import import_module
from typing import Any

from fastapi import APIRouter

from app.api.ws.constants import PkgID, RSPCode
from app.logging import logger
from app.managers.rbac_manager import RBACManager
from app.schemas.generic_typing import (
    HandlerCallableType,
    JsonSchemaType,
    ValidatorType,
)
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.schemas.user import UserModel


class PackageRouter:
    """
    Router for WebSocket package-based requests.

    Manages registration and dispatching of WebSocket handlers based on package IDs,
    including validation and permission checking for each request.
    """

    def __init__(self):
        """
        Initializes the `PackageRouter` class with empty dictionaries to store registered handlers and validators for different package IDs (PkgID).

        The `handlers_registry` dictionary maps package IDs to their corresponding handler functions (HandlerCallableType).
        The `validators_registry` dictionary maps package IDs to a tuple containing the JSON schema (JsonSchemaType) and a validator callback function (ValidatorType) for that package ID.
        The `permissions_registry` dictionary maps package IDs to their required roles for access control.
        """
        self.handlers_registry: dict[PkgID, HandlerCallableType] = {}
        self.validators_registry: dict[
            PkgID, tuple[JsonSchemaType, ValidatorType]
        ] = {}
        self.permissions_registry: dict[PkgID, list[str]] = {}
        self.rbac: RBACManager = RBACManager()

    def register(
        self,
        *pkg_ids: PkgID,
        json_schema: JsonSchemaType | None = None,
        validator_callback: ValidatorType | None = None,
        roles: list[str] | None = None,
    ):
        """
        Decorator function to register a handler and validator for a specific package ID (PkgID).

        This decorator is used to register a handler function and an optional JSON schema validator for a specific package ID. The registered handler function will be used to handle requests with the corresponding package ID, and the validator will be used to validate the request data against the provided JSON schema.

        Args:
            *pkg_ids (PkgID): One or more package IDs to register the handler and validator for.
            json_schema (JsonSchemaType | None): An optional JSON schema to validate the request data against.
            validator_callback (ValidatorType | None): An optional callback function to validate the request data against the provided JSON schema.
            roles (list[str] | None): Optional list of roles required to access this endpoint. If None, endpoint is public.

        Returns:
            A decorator function that can be used to register a handler function.
        """

        def decorator(func: HandlerCallableType):
            for pkg_id in pkg_ids:
                # Check if handler is already registered (idempotent for reload)
                if pkg_id in self.handlers_registry:
                    # Skip if same handler, raise if different
                    if self.handlers_registry[pkg_id] != func:
                        raise ValueError(
                            f"Different handler already registered for pkg_id {pkg_id}"
                        )
                    continue

                self.handlers_registry[pkg_id] = func
                self.validators_registry[pkg_id] = (
                    json_schema,
                    validator_callback,
                )

                # Store permissions if roles are specified
                if roles:
                    self.permissions_registry[pkg_id] = roles

                logger.info(
                    f"Register {func.__module__}.{func.__name__} for PkgID: {pkg_id}"
                    + (f" with roles: {roles}" if roles else "")
                )

            return func

        return decorator

    def __get_handler(self, pkg_id: PkgID) -> HandlerCallableType:
        """
        Retrieves the handler function registered for the given package ID from the `handlers_registry` dictionary.

        Args:
            pkg_id (PkgID): The package ID to retrieve the handler function for.

        Returns:
            HandlerCallableType: The handler function registered for the given package ID.
        """
        return self.handlers_registry[pkg_id]

    def _has_handler(self, pkg_id: int) -> bool:
        """Check if a handler is registered for the given package ID."""
        return pkg_id in self.handlers_registry

    def get_permissions(self, pkg_id: int) -> list[str]:
        """
        Get required roles for a package ID.

        Args:
            pkg_id: The package ID to get permissions for.

        Returns:
            List of role names required for access. Empty list means public access.
        """
        return self.permissions_registry.get(pkg_id, [])

    def _check_permission(self, pkg_id: int, user: UserModel) -> bool:
        """Check if user has permission for the package ID."""
        return self.rbac.check_ws_permission(pkg_id, user)

    def _validate_request(
        self, request: RequestModel
    ) -> ResponseModel[dict[str, Any]] | None:
        """
        Validate request data against registered schema.

        Returns:
            ResponseModel with error if validation fails, None if valid.
        """
        json_schema, validator_func = self.validators_registry[request.pkg_id]

        if validator_func is None or json_schema is None:
            return None

        # Convert Pydantic model to JSON schema if needed
        if hasattr(json_schema, "model_json_schema"):
            json_schema = json_schema.model_json_schema()

        return validator_func(request, json_schema)

    async def handle_request(
        self, user: UserModel, request: RequestModel
    ) -> ResponseModel[dict[str, Any]]:
        """
        Handle incoming WebSocket request with validation and permission checks.

        This method acts as a router, checking if the request is valid,
        if the user has permission, and directing to the appropriate handler.

        Args:
            user: The user making the request.
            request: The request object containing pkg_id and data.

        Returns:
            ResponseModel with the result of request handling.
        """
        if not self._has_handler(request.pkg_id):
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"No handler found for pkg_id {request.pkg_id}",
                status_code=RSPCode.ERROR,
            )

        if not self._check_permission(request.pkg_id, user):
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"No permission for pkg_id {request.pkg_id}",
                status_code=RSPCode.PERMISSION_DENIED,
            )

        if validation_error := self._validate_request(request):
            return validation_error

        handler = self.__get_handler(request.pkg_id)
        return await handler(request)


pkg_router = PackageRouter()


# Track registered modules to prevent duplicate logging
_registered_http_modules: set[str] = set()
_registered_ws_modules: set[str] = set()


def collect_subrouters() -> APIRouter:
    """
    Collects and registers all API and WebSocket routers for the application.

    This function is responsible for discovering and registering all API and WebSocket routers in the application.
    It iterates through the `api/routers/http` and `api/routers/ws/consumers` directories,
    imports the corresponding modules, and adds their routers to the main `APIRouter` instance.

    The main `APIRouter` instance is then returned, allowing it to be used as the entry point for the application's API.
    """
    # Initialize main router
    main_router: APIRouter = APIRouter()

    # Get project dir
    app_dir = os.path.dirname(__file__)
    app_name = os.path.basename(app_dir)

    # Get API routers
    for _, module, _ in pkgutil.iter_modules([f"{app_dir}/api/http"]):
        # Get api module
        api = import_module(f".{module}", package=f"{app_name}.api.http")

        # Add api router to main router
        main_router.include_router(api.router)

        # Only log on first registration
        if module not in _registered_http_modules:
            logger.info(f'Register "{module}" api')
            _registered_http_modules.add(module)

    # Get WS routers
    for _, module, _ in pkgutil.iter_modules([f"{app_dir}/api/ws/consumers"]):
        # Get ws module
        ws_consumer = import_module(
            f".{module}", package=f"{app_name}.api.ws.consumers"
        )

        # Add ws router to main router
        main_router.include_router(ws_consumer.router)

        # Only log on first registration
        if module not in _registered_ws_modules:
            logger.info(f'Register "{module}" websocket consumer')
            _registered_ws_modules.add(module)

    return main_router
