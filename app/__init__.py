# Uvicorn application factory <https://www.uvicorn.org/#application-factories>
from asyncio import create_task, ensure_future, gather

from fastapi import FastAPI
from starlette.middleware.authentication import AuthenticationMiddleware

from app.auth import AuthBackend
from app.logging import logger
from app.managers.rbac_manager import RBACManager
from app.middlewares.action import PermAuthHTTPMiddleware
from app.routing import collect_subrouters
from app.schemas.roles import ROLE_CONFIG_SCHEMA
from app.settings import ACTIONS_FILE_PATH
from app.storage.db import wait_and_init_db
from app.storage.redis import RRedis
from app.tasks.kc_user_session import kc_user_session_task
from app.utils import read_json_file

tasks = []
ws_clients = {}


async def proba(_, content):
    print()
    print("tuka si")
    print()


def startup():
    """
    Application startup handler
    """

    async def wrapper():
        # Create the database and tables
        await wait_and_init_db()
        logger.info("Initialized database and tables")

        print("STARTUP")
        tasks.append(create_task(kc_user_session_task()))
        logger.info("Created task for user session")

        # Subscribe to Redis channels
        r = await RRedis()
        await r.subscribe("proba", proba)

    return wrapper


def shutdown():
    """
    Application shutdown handler
    """

    async def wrapper():
        print("SHUTDOWN")
        # Run loop until tasks done
        ensure_future(gather(*tasks, return_exceptions=True))

    return wrapper


def application() -> FastAPI:
    """
    Initializes and configures the FastAPI application.

    This function sets up the FastAPI application with the following configurations:
    - Title: "HTTP & WebSocket handlers"
    - Description: "HTTP & WebSocket handlers"
    - Version: "1.0.0"

    It also adds the following event handlers:
    - Startup handler: Initializes the database and tables.
    - Shutdown handler: Prints "SHUTDOWN" when the application is shutting down.

    The function then includes the routers collected from the `app.routing.collect_subrouters()` function, and adds the following middleware:
    - `PermAuthHTTPMiddleware`: Middleware for permission-based authentication, using actions defined in the "/project/actions1123.json" file.
    - `AuthenticationMiddleware`: Middleware for authentication, using the `AuthBackend` authentication backend.

    Finally, the function returns the configured FastAPI application.
    """
    # Initialize application
    app = FastAPI(
        title="HTTP & WebSocket handlers",
        description="HTTP & WebSocket handlers",
        version="1.0.0",
    )

    # Add event handlers
    app.add_event_handler("startup", startup())
    app.add_event_handler("shutdown", shutdown())

    # Collect routers
    app.include_router(collect_subrouters())

    # Middlewares
    app.add_middleware(PermAuthHTTPMiddleware, rbac=RBACManager())
    app.add_middleware(AuthenticationMiddleware, backend=AuthBackend())

    return app


app = application()  # Need for fastapi cli
