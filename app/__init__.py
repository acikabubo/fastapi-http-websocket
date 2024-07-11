# Uvicorn application factory <https://www.uvicorn.org/#application-factories>
from fastapi import FastAPI

from app.db import init_db
from app.logging import logger
from app.middlewares.middleware import ActionMiddleware
from app.routing import collect_subrouters

# Define your action map here
action_map = {1: "create_author", 2: "create_genre"}


def startup():
    """
    Application startup handler
    """

    async def wrapper():
        # Create the database and tables
        await init_db()
        logger.info("Initialized database and tables")

    return wrapper


def shutdown():
    """
    Application shutdown handler
    """

    async def wrapper():
        print("SHUTDOWN")

    return wrapper


def application() -> FastAPI:
    # Initialize application
    app = FastAPI(
        title="HTTP & WebSocket handlers",
        description="HTTP & WebSocket handlers",
        version="1.0.0",
    )

    # Add event handlers
    app.add_event_handler("startup", startup())  # FIXME: Is it necessary?
    app.add_event_handler("shutdown", shutdown())  # FIXME: Is it necessary?

    # Routers
    app.include_router(collect_subrouters())

    # Middlewares
    # app.add_middleware(ActionMiddleware, action_map=action_map)  # FIXME:

    return app


app = application()  # Need for fastapi cli
