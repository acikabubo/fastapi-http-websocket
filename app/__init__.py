# Uvicorn application factory <https://www.uvicorn.org/#application-factories>
from asyncio import create_task, gather
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.auth import AuthBackend
from app.logging import logger
from app.middlewares.pipeline import MiddlewarePipeline
from app.routing import collect_subrouters
from app.settings import app_settings
from app.storage.db import wait_and_init_db
from app.tasks.kc_user_session import kc_user_session_task
from app.tasks.redis_pool_metrics_task import redis_pool_metrics_task


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager for startup and shutdown.

    Handles:
    - Startup validation (environment variables and service connections)
    - Database initialization with retries
    - Background task startup (user session sync, audit log worker, pool metrics)
    - Prometheus metrics initialization
    - Graceful shutdown with audit log flushing and task cancellation

    Startup operations:
    - Validates required settings and service connections (fail-fast)
    - Sets up the database and tables
    - Creates user session background task
    - Starts audit log background worker
    - Starts Redis pool metrics collection task
    - Starts database pool metrics collection task
    - Initializes Prometheus metrics

    Shutdown operations:
    - Flushes remaining audit logs
    - Closes Redis connection pools
    - Cancels and waits for background tasks
    """
    # Startup
    logger.info("Application startup: initializing resources")

    # Run startup validations (fail-fast if configuration is invalid)
    from app.startup_validation import run_all_validations

    await run_all_validations()

    # Create the database and tables
    await wait_and_init_db()
    logger.info("Initialized database and tables")

    # Start background tasks
    background_tasks = []

    background_tasks.append(
        create_task(kc_user_session_task(), name="kc_session_sync")
    )
    logger.info("Created task for user session")

    # Start audit log background worker
    from app.utils.audit_logger import audit_log_worker

    background_tasks.append(
        create_task(audit_log_worker(), name="audit_worker")
    )
    logger.info("Started audit log background worker")

    # Start Redis pool metrics collection task
    background_tasks.append(
        create_task(redis_pool_metrics_task(), name="redis_pool_metrics")
    )
    logger.info("Started Redis pool metrics collection task")

    # Start database pool metrics collection task
    from app.tasks.db_pool_metrics_task import db_pool_metrics_task

    background_tasks.append(
        create_task(db_pool_metrics_task(), name="db_pool_metrics")
    )
    logger.info("Started database pool metrics collection task")

    # Initialize app info metric
    import sys

    from app.utils.metrics import app_info

    app_info.labels(
        version="1.0.0",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        environment="production",
    ).set(1)
    logger.info("Initialized Prometheus metrics")

    logger.info(f"Started {len(background_tasks)} background tasks")

    yield  # Application runs here

    # Shutdown
    logger.info("Application shutdown: cleaning up resources")

    # Flush remaining audit logs
    try:
        from app.utils.audit_logger import flush_audit_queue

        flushed_count = await flush_audit_queue()
        if flushed_count > 0:
            logger.info(f"Flushed {flushed_count} audit logs during shutdown")
    except (ImportError, RuntimeError, OSError) as ex:
        # ImportError: Module not available
        # RuntimeError: Async context issues
        # OSError: Database connection/write errors
        logger.error(f"Error flushing audit logs: {ex}")

    # Close Redis connection pools
    try:
        from app.storage.redis import RedisPool

        await RedisPool.close_all()
        logger.info("Closed Redis connection pools")
    except (ImportError, RuntimeError, ConnectionError) as ex:
        # ImportError: Module not available
        # RuntimeError: Async context issues
        # ConnectionError: Redis connection errors
        logger.error(f"Error closing Redis connection pools: {ex}")

    # Cancel background tasks
    if background_tasks:
        logger.info(f"Cancelling {len(background_tasks)} background tasks")
        for task in background_tasks:
            if not task.done():
                task.cancel()
        logger.info("Waiting for background tasks to complete cleanup")
        await gather(*background_tasks, return_exceptions=True)
        logger.info("All background tasks completed")

    logger.info("Application shutdown complete")


def application() -> FastAPI:
    """
    Initializes and configures the FastAPI application.

    This function sets up the FastAPI application with the following configurations:
    - Title: "HTTP & WebSocket handlers"
    - Description: "HTTP & WebSocket handlers"
    - Version: "1.0.0"
    - Lifespan: Modern context manager for startup/shutdown (replaces deprecated event handlers)

    The lifespan context manager handles:
    - Database initialization and background task startup
    - Graceful shutdown with audit log flushing and task cancellation

    The function then includes the routers collected from the `app.routing.collect_subrouters()` function, and adds the following middleware:
    - `AuthenticationMiddleware`: Middleware for authentication, using the `AuthBackend` authentication backend.
    - `RateLimitMiddleware`: Middleware for rate limiting HTTP requests.
    - `PrometheusMiddleware`: Middleware for collecting Prometheus metrics.
    - `CorrelationIDMiddleware`: Middleware for request correlation IDs.

    Role-based permissions are now enforced via FastAPI dependencies using `require_roles()`.

    Finally, the function returns the configured FastAPI application.
    """
    # Initialize application with lifespan context manager
    app = FastAPI(
        title="HTTP & WebSocket handlers",
        description="HTTP & WebSocket handlers",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Collect routers
    app.include_router(collect_subrouters())

    # Customize OpenAPI schema to add HTTPBearer security for Swagger UI
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Add HTTPBearer security scheme
        openapi_schema.setdefault("components", {})
        openapi_schema["components"].setdefault("securitySchemes", {})
        openapi_schema["components"]["securitySchemes"]["HTTPBearer"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token from `python scripts/get_token.py <username> <password>`",
        }

        # Apply security globally to all endpoints (except excluded paths)
        openapi_schema.setdefault("security", [])
        openapi_schema["security"].append({"HTTPBearer": []})

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # Apply middleware pipeline with explicit ordering and dependency validation
    # Note: RBAC is now handled via FastAPI dependencies (require_roles) instead of middleware
    pipeline = MiddlewarePipeline(
        allowed_hosts=app_settings.ALLOWED_HOSTS,
        auth_backend=AuthBackend(),
    )
    pipeline.validate_dependencies()
    pipeline.apply_to_app(app)

    return app


app = application()  # Need for fastapi cli
