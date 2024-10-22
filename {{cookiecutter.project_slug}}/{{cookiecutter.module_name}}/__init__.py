# Uvicorn application factory <https://www.uvicorn.org/#application-factories>
from asyncio import (
    CancelledError,
    TimeoutError,
    create_task,
    ensure_future,
    gather,
    sleep,
)

from fastapi import FastAPI
from starlette.middleware.authentication import AuthenticationMiddleware

from {{cookiecutter.module_name}}.auth import AuthBackend
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.middlewares.action import PermAuthHTTPMiddleware
from {{cookiecutter.module_name}}.routing import collect_subrouters
from {{cookiecutter.module_name}}.settings import ACTIONS_FILE_PATH, USER_SESSION_REDIS_KEY_PREFIX
from {{cookiecutter.module_name}}.storage.db import init_db
from {{cookiecutter.module_name}}.storage.redis import get_auth_redis_connection
from {{cookiecutter.module_name}}.utils import read_json_file

# Define your action map here
action_map = {1: "create_author", 2: "create_genre"}

tasks = []
ws_clients = {}


async def kc_user_session_task():
    """
    Runs a task that monitors the expiration of user sessions stored in Redis.

    This task subscribes to the Redis `__keyevent@*__:expired` channel to listen for expired keys.
    When an expired key is detected that matches the `USER_SESSION_REDIS_KEY_PREFIX`,
    the task closes the associated WebSocket connection (if it exists) and removes the user from the `ws_clients` dictionary.

    This ensures that when a user's session expires, their WebSocket connection is properly closed and cleaned up.
    """
    # Get auth redis instance
    r = await get_auth_redis_connection()

    rch = None

    while True:
        try:
            if not rch:
                rch = r.pubsub()
                await rch.psubscribe("__keyevent@*__:expired")

            event = await rch.get_message(
                ignore_subscribe_messages=True, timeout=1
            )

            if not event:
                await sleep(0.5)
                continue

            evt_key = event["data"]

            if not evt_key.startswith(USER_SESSION_REDIS_KEY_PREFIX):
                await sleep(1)
                continue

            # Close websocket connection and delete user
            # relation with websocket connection
            if ws_conn := ws_clients.get(evt_key):
                await ws_conn.close()
                del ws_clients[evt_key]

            logger.info(f'Session for user "{evt_key}" has been expired')

            await sleep(1)

        except CancelledError:
            logger.info("Task for keycloak user session cancelled!")
            break

        except TimeoutError:
            await sleep(0.1)

        except Exception as ex:
            logger.error(
                f"Keycloak user session task error occurred with: {ex}"
            )
            rch = None
            await sleep(0.5)


def startup():
    """
    Application startup handler
    """

    async def wrapper():
        # Create the database and tables
        await init_db()
        logger.info("Initialized database and tables")

        print("STARTUP")
        # tasks.append(create_task(kc_user_session_task()))
        logger.info("Created task for user session")

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
    {{cookiecutter.module_name}}.add_event_handler("startup", startup())  # FIXME: Is it necessary?
    {{cookiecutter.module_name}}.add_event_handler("shutdown", shutdown())  # FIXME: Is it necessary?

    # Collect routers
    {{cookiecutter.module_name}}.include_router(collect_subrouters())

    # Middlewares
    {{cookiecutter.module_name}}.add_middleware(
        PermAuthHTTPMiddleware,
        actions=read_json_file(ACTIONS_FILE_PATH),
    )  # FIXME:
    {{cookiecutter.module_name}}.add_middleware(AuthenticationMiddleware, backend=AuthBackend())

    return app


app = application()  # Need for fastapi cli
