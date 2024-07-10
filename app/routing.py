import os
import pkgutil
from importlib import import_module
from typing import Any, Callable

from fastapi import APIRouter
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.routers.ws.constants import PkgID
from app.core.logging import logger
from app.schemas.generic import (
    HandlerCallableType,
    JsonSchemaType,
    ValidatorType,
)
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel


class PackageRouter:
    def __init__(self):
        self.handlers_registry: dict[PkgID, HandlerCallableType] = {}
        self.validators_registry: dict[
            PkgID, tuple[JsonSchemaType, ValidatorType]
        ] = {}

    def register(
        self,
        *pkg_ids: PkgID,
        json_schema: JsonSchemaType | None = None,
        validator_callback: ValidatorType | None = None,
    ):
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
                    f"FROM ROUTER Registered {func.__module__}.{func.__name__} for PkgID: {pkg_id}"
                )

            return func

        return decorator

    def __get_handler(self, pkg_id: PkgID) -> Callable:
        return self.handlers_registry[pkg_id]

    async def handle_request(
        self, request: RequestModel, session: AsyncSession
    ) -> ResponseModel[dict[str, Any]]:
        if request.pkg_id not in self.handlers_registry:
            raise ValueError(f"No handler found for pkg_id {request.pkg_id}")

        json_schema, validator_func = self.validators_registry[request.pkg_id]

        if json_schema is not None and validator_func is not None:
            if validation_result := validator_func(request, json_schema):
                return validation_result

        handler = self.__get_handler(request.pkg_id)

        return await handler(request, session)


pkg_router = PackageRouter()


def collect_subrouters():
    # Initialize main router
    main_router = APIRouter()

    # Get project dir
    app_dir = os.path.dirname(__file__)
    app_name = os.path.basename(app_dir)

    # Get API routers
    for _, module, _ in pkgutil.iter_modules([f"{app_dir}/api/routers/http"]):
        # Get api module
        api = import_module(
            f".{module}", package=f"{app_name}.api.routers.http"
        )

        # Add api router to main router
        main_router.include_router(api.router)

        logger.info(f'Register "{module}" api')

    # Get WS routers
    for _, module, _ in pkgutil.iter_modules(
        [f"{app_dir}/api/routers/ws/consumers"]
    ):
        # Get ws module
        ws_consumer = import_module(
            f".{module}", package=f"{app_name}.api.routers.ws.consumers"
        )

        # Add ws router to main router
        main_router.include_router(ws_consumer.router)

        logger.info(f'Register "{module}" websocket consumer')

    return main_router
