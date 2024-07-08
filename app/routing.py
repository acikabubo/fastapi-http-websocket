import os
import pkgutil
from importlib import import_module

from fastapi import APIRouter

from app.logging import logger


def collect_subrouters():
    # Initialize main router
    main_router = APIRouter()

    # Get project dir
    app_dir = os.path.dirname(__file__)
    app_name = os.path.basename(app_dir)

    # Get API routers
    for _, module, _ in pkgutil.iter_modules([f"{app_dir}/routers/api"]):
        # Get api module
        api = import_module(f".{module}", package=f"{app_name}.routers.api")

        # Add api router to main router
        main_router.include_router(api.router)

        logger.info(f'Register "{module}" api')

    # Get WS routers
    for _, module, _ in pkgutil.iter_modules(
        [f"{app_dir}/routers/ws/consumers"]
    ):
        # Get ws module
        ws_consumer = import_module(
            f".{module}", package=f"{app_name}.routers.ws.consumers"
        )

        # Add ws router to main router
        main_router.include_router(ws_consumer.router)

        logger.info(f'Register "{module}" websocket consumer')

    return main_router
