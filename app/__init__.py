# Uvicorn application factory <https://www.uvicorn.org/#application-factories>
from asyncio import create_task, gather

from fastapi import FastAPI
from starlette.middleware.authentication import AuthenticationMiddleware

from app.auth import AuthBackend
from app.logging import logger
from app.middlewares.audit_middleware import AuditMiddleware
from app.middlewares.correlation_id import CorrelationIDMiddleware
from app.middlewares.logging_context import LoggingContextMiddleware
from app.middlewares.prometheus import PrometheusMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.routing import collect_subrouters
from app.storage.db import wait_and_init_db
from app.tasks.kc_user_session import kc_user_session_task

tasks = []


def startup():
    """
    Application startup handler
    """

    async def wrapper():
        """
        Asynchronous initialization wrapper that:
        - Sets up the database and tables
        - Creates a user session background task
        - Subscribes to Redis channels for real-time messaging
        - Initializes Prometheus metrics

        This wrapper handles all startup operations that require async/await syntax.
        """
        # Create the database and tables
        await wait_and_init_db()
        logger.info("Initialized database and tables")

        logger.info("Application startup initiated")
        tasks.append(create_task(kc_user_session_task()))
        logger.info("Created task for user session")

        # Start audit log background worker
        from app.utils.audit_logger import audit_log_worker

        tasks.append(create_task(audit_log_worker()))
        logger.info("Started audit log background worker")

        # Initialize app info metric
        import sys

        from app.utils.metrics import app_info

        app_info.labels(
            version="1.0.0",
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            environment="production",
        ).set(1)
        logger.info("Initialized Prometheus metrics")

    return wrapper


def shutdown():
    """
    Application shutdown handler
    """

    async def wrapper():
        """
        Asynchronous shutdown wrapper that performs graceful cleanup.

        Cleanup order:
        1. Flush remaining audit logs
        2. Close Redis connection pools
        3. Cancel and wait for background tasks

        Uses gather() with return_exceptions=True to handle CancelledError
        exceptions gracefully during the cancellation process.
        """
        logger.info("Application shutdown initiated")

        # Flush remaining audit logs
        try:
            from app.utils.audit_logger import flush_audit_queue

            flushed_count = await flush_audit_queue()
            if flushed_count > 0:
                logger.info(f"Flushed {flushed_count} audit logs during shutdown")
        except Exception as ex:
            logger.error(f"Error flushing audit logs: {ex}")

        # Close Redis connection pools
        try:
            from app.storage.redis import RedisPool

            await RedisPool.close_all()
        except Exception as ex:
            logger.error(f"Error closing Redis connection pools: {ex}")

        # Cancel background tasks
        if tasks:
            logger.info(f"Cancelling {len(tasks)} background tasks")
            for task in tasks:
                task.cancel()
            logger.info("Waiting for background tasks to complete cleanup")
            await gather(*tasks, return_exceptions=True)
            logger.info("All background tasks completed")

        logger.info("Application shutdown complete")

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
    - `AuthenticationMiddleware`: Middleware for authentication, using the `AuthBackend` authentication backend.
    - `RateLimitMiddleware`: Middleware for rate limiting HTTP requests.
    - `PrometheusMiddleware`: Middleware for collecting Prometheus metrics.
    - `CorrelationIDMiddleware`: Middleware for request correlation IDs.

    Role-based permissions are now enforced via FastAPI dependencies using `require_roles()`.

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

    # Middlewares (execute in REVERSE order of registration)
    # Execution flow: CorrelationIDMiddleware → LoggingContextMiddleware → AuthenticationMiddleware → RateLimitMiddleware → AuditMiddleware → PrometheusMiddleware
    # Note: RBAC is now handled via FastAPI dependencies (require_roles) instead of middleware
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthenticationMiddleware, backend=AuthBackend())
    app.add_middleware(LoggingContextMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    return app


app = application()  # Need for fastapi cli
