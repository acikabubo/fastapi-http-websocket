# Uvicorn application factory <https://www.uvicorn.org/#application-factories>
from asyncio import (
    create_task,
    ensure_future,
    gather,
)

from fastapi import FastAPI
from starlette.middleware.authentication import AuthenticationMiddleware

from {{cookiecutter.module_name}}.auth import AuthBackend
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.middlewares.action import PermAuthHTTPMiddleware
from {{cookiecutter.module_name}}.routing import collect_subrouters
from {{cookiecutter.module_name}}.schemas.roles import ROLE_CONFIG_SCHEMA
from {{cookiecutter.module_name}}.settings import ACTIONS_FILE_PATH
from {{cookiecutter.module_name}}.storage.db import wait_and_init_db
from {{cookiecutter.module_name}}.utils import read_json_file
{% if cookiecutter.use_redis == "y" and cookiecutter.use_keycloak == "y" %}
from {{cookiecutter.module_name}}.tasks.kc_user_session import kc_user_session_task
{% endif %}

# Define your action map here
action_map = {1: "create_author", 2: "create_genre"}

tasks = []
ws_clients = {}


def startup():
    """
    Application startup handler
    """

    async def wrapper():
        # Create the database and tables
        await wait_and_init_db()
        logger.info("Initialized database and tables")

        print("STARTUP")
        {% if cookiecutter.use_redis == "y" and cookiecutter.use_keycloak == "y" %}
        tasks.append(create_task(kc_user_session_task()))
        logger.info("Created task for user session")
        {% endif %}

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

    The function then includes the routers collected from the `{{cookiecutter.module_name}}.routing.collect_subrouters()` function, and adds the following middleware:
    - `PermAuthHTTPMiddleware`: Middleware for permission-based authentication, using actions defined in the "/project/actions1123.json" file.
    - `AuthenticationMiddleware`: Middleware for authentication, using the `AuthBackend` authentication backend.

    Finally, the function returns the configured FastAPI application.
    """
    # Initialize application
    app = FastAPI(
        title="{{cookiecutter.project_name}}",
        description="{{cookiecutter.project_description}}",
        version="1.0.0",
    )

    # Add event handlers
    app.add_event_handler("startup", startup())  # FIXME: Is it necessary?
    app.add_event_handler("shutdown", shutdown())  # FIXME: Is it necessary?

    # Collect routers
    app.include_router(collect_subrouters())

    # Middlewares
    app.add_middleware(
        PermAuthHTTPMiddleware,
        actions=read_json_file(ACTIONS_FILE_PATH, ROLE_CONFIG_SCHEMA),
    )  # FIXME:
    app.add_middleware(AuthenticationMiddleware, backend=AuthBackend())

    return app


app = application()  # Need for fastapi cli
