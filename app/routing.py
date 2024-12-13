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
from app.schemas.roles import ROLE_CONFIG_SCHEMA
from app.schemas.user import UserModel
from app.settings import ACTIONS_FILE_PATH
from app.utils import read_json_file


class PackageRouter:
    def __init__(self):
        """
        Initializes the `PackageRouter` class with empty dictionaries to store registered handlers and validators for different package IDs (PkgID).

        The `handlers_registry` dictionary maps package IDs to their corresponding handler functions (HandlerCallableType).
        The `validators_registry` dictionary maps package IDs to a tuple containing the JSON schema (JsonSchemaType) and a validator callback function (ValidatorType) for that package ID.
        """
        self.handlers_registry: dict[PkgID, HandlerCallableType] = {}
        self.validators_registry: dict[
            PkgID, tuple[JsonSchemaType, ValidatorType]
        ] = {}
        self.rbac: RBACManager = RBACManager()

    def register(
        self,
        *pkg_ids: PkgID,
        json_schema: JsonSchemaType | None = None,
        validator_callback: ValidatorType | None = None,
    ):
        """
        Decorator function to register a handler and validator for a specific package ID (PkgID).

        This decorator is used to register a handler function and an optional JSON schema validator for a specific package ID. The registered handler function will be used to handle requests with the corresponding package ID, and the validator will be used to validate the request data against the provided JSON schema.

        Args:
            *pkg_ids (PkgID): One or more package IDs to register the handler and validator for.
            json_schema (JsonSchemaType | None): An optional JSON schema to validate the request data against.
            validator_callback (ValidatorType | None): An optional callback function to validate the request data against the provided JSON schema.

        Returns:
            A decorator function that can be used to register a handler function.
        """

        def decorator(func: HandlerCallableType):
            for pkg_id in pkg_ids:
                if pkg_id in self.handlers_registry:
                    raise ValueError(
                        f"Handler already registered for pkg_id {pkg_id}"
                    )

                self.handlers_registry[pkg_id] = func
                self.validators_registry[pkg_id] = (
                    json_schema,
                    validator_callback,
                )

                logger.info(
                    f"Register {func.__module__}.{func.__name__} for PkgID: {pkg_id}"
                )

            return func

        return decorator

    def __get_handler(self, pkg_id: PkgID) -> HandlerCallableType:
        return self.handlers_registry[pkg_id]

    async def handle_request(
        self, user: UserModel, request: RequestModel
    ) -> ResponseModel[dict[str, Any]]:
        """
        This code acts like a traffic controller for incoming requests. It checks if the request is valid, if the user has permission to make the request, and then directs the request to the right handler function to process it.
        Handles a request by finding the appropriate handler and validator for the request's package ID (pkg_id), validating the request data if a validator is registered, and then calling the registered handler function.

        Args:
            user (UserModel): The user making the request.
            request (RequestModel): The request object containing the package ID and other request data.

        Returns:
            ResponseModel[dict[str, Any]]: The response object containing the result of the request handling.
        """
        if request.pkg_id not in self.handlers_registry:
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"No handler found for pkg_id {request.pkg_id}",
                status_code=RSPCode.ERROR,
            )

        has_permission = self.rbac.check_ws_permission(request.pkg_id, user)

        if not has_permission:
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"No permission for pkg_id {request.pkg_id}",
                status_code=RSPCode.PERMISSION_DENIED,
            )

        json_schema, validator_func = self.validators_registry[request.pkg_id]

        if json_schema is not None and validator_func is not None:
            if validation_result := validator_func(request, json_schema):
                return validation_result

        handler = self.__get_handler(request.pkg_id)

        # return await handler(request, session)
        return await handler(request)


pkg_router = PackageRouter()


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

        logger.info(f'Register "{module}" api')

    # Get WS routers
    for _, module, _ in pkgutil.iter_modules([f"{app_dir}/api/ws/consumers"]):
        # Get ws module
        ws_consumer = import_module(
            f".{module}", package=f"{app_name}.api.ws.consumers"
        )

        # Add ws router to main router
        main_router.include_router(ws_consumer.router)

        logger.info(f'Register "{module}" websocket consumer')

    return main_router
