"""
Startup validation functions for environment variables and service connections.

This module implements fail-fast validation to ensure the application does not
start with invalid configuration or unavailable dependencies. All validations
run during application startup, before accepting any requests.
"""

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.settings import app_settings
from {{cookiecutter.module_name}}.storage.db import engine


class StartupValidationError(Exception):
    """
    Exception raised when startup validation fails.

    This exception indicates that the application cannot start due to
    missing or invalid configuration, or unavailable dependencies.
    """

    pass


async def validate_settings() -> None:
    """
    Validate required environment variables and configuration.

    Checks that all critical settings are properly configured before
    starting the application. This prevents the app from starting with
    missing credentials or invalid configuration.

    Raises:
        StartupValidationError: If any required setting is missing or invalid
    """
    logger.info("Validating application settings...")

    # Keycloak settings (required for authentication)
    if not app_settings.KEYCLOAK_REALM:
        raise StartupValidationError(
            "KEYCLOAK_REALM environment variable is required"
        )
    if not app_settings.KEYCLOAK_CLIENT_ID:
        raise StartupValidationError(
            "KEYCLOAK_CLIENT_ID environment variable is required"
        )
    if not app_settings.KEYCLOAK_BASE_URL:
        raise StartupValidationError(
            "KEYCLOAK_BASE_URL environment variable is required"
        )
    if not app_settings.KEYCLOAK_ADMIN_USERNAME:
        raise StartupValidationError(
            "KEYCLOAK_ADMIN_USERNAME environment variable is required"
        )
    if not app_settings.KEYCLOAK_ADMIN_PASSWORD:
        raise StartupValidationError(
            "KEYCLOAK_ADMIN_PASSWORD environment variable is required"
        )

    # Database settings (required for data persistence)
    if not app_settings.DB_USER:
        raise StartupValidationError(
            "DB_USER environment variable is required"
        )
    if not app_settings.DB_PASSWORD.get_secret_value():
        raise StartupValidationError(
            "DB_PASSWORD environment variable is required"
        )

    # Validate DEBUG_AUTH is disabled in production
    if app_settings.is_production and app_settings.DEBUG_AUTH:
        raise StartupValidationError(
            "DEBUG_AUTH cannot be enabled in production environment"
        )

    # Validate DEBUG_AUTH credentials if enabled
    if app_settings.DEBUG_AUTH:
        if not app_settings.DEBUG_AUTH_USERNAME:
            raise StartupValidationError(
                "DEBUG_AUTH_USERNAME is required when DEBUG_AUTH is enabled"
            )
        if not app_settings.DEBUG_AUTH_PASSWORD:
            raise StartupValidationError(
                "DEBUG_AUTH_PASSWORD is required when DEBUG_AUTH is enabled"
            )
        logger.warning(
            "DEBUG_AUTH is enabled - bypass authentication is active. "
            "This should ONLY be used for local development!"
        )

    logger.info("Application settings validation passed")


async def validate_database_connection() -> None:
    """
    Validate database connectivity at startup.

    Attempts to connect to the database and execute a simple query to
    verify the connection is working. This catches database configuration
    errors before the application starts accepting requests.

    Raises:
        StartupValidationError: If database connection fails
    """
    logger.info("Validating database connection...")

    try:
        async with engine.connect() as conn:
            # Execute simple query to verify connection works
            result = await conn.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            if not row or row[0] != 1:
                raise StartupValidationError(
                    "Database health check query returned unexpected result"
                )

        logger.info(
            f"Database connection validated: {app_settings.DB_HOST}:"
            f"{app_settings.DB_PORT}/{app_settings.DB_NAME}"
        )
    except StartupValidationError:
        # Re-raise our own exceptions
        raise
    except OperationalError as ex:
        raise StartupValidationError(
            f"Database connection failed: {ex}. "
            f"Verify DB_HOST, DB_PORT, DB_USER, DB_PASSWORD settings."
        )
    except Exception as ex:
        raise StartupValidationError(
            f"Unexpected database validation error: {ex}"
        )


async def validate_redis_connection() -> None:
    """
    Validate Redis connectivity at startup.

    Attempts to connect to Redis and execute a PING command to verify
    the connection is working. This catches Redis configuration errors
    before the application starts.

    Raises:
        StartupValidationError: If Redis connection fails
    """
    logger.info("Validating Redis connection...")

    redis: Redis | None = None
    try:
        # Test connection to main Redis database
        redis = Redis(
            host=app_settings.REDIS_IP,
            port=app_settings.REDIS_PORT,
            db=app_settings.MAIN_REDIS_DB,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True,
        )

        # Execute PING command to verify connection
        pong = await redis.ping()
        if not pong:
            raise StartupValidationError(
                "Redis PING command returned unexpected result"
            )

        logger.info(
            f"Redis connection validated: {app_settings.REDIS_IP}:"
            f"{app_settings.REDIS_PORT} (db={app_settings.MAIN_REDIS_DB})"
        )

    except (RedisError, ConnectionError, TimeoutError, OSError) as ex:
        # RedisError: Redis operation errors
        # ConnectionError: Network issues
        # TimeoutError: Connection timeout
        # OSError: Network/socket errors
        raise StartupValidationError(
            f"Redis connection failed: {ex}. "
            f"Verify REDIS_IP and REDIS_PORT settings."
        )
    except Exception as ex:
        raise StartupValidationError(
            f"Unexpected Redis validation error: {ex}"
        )
    finally:
        if redis:
            await redis.aclose()


async def run_all_validations() -> None:
    """
    Run all startup validation checks.

    This function orchestrates all validation checks and provides a single
    entry point for startup validation. If any validation fails, the
    application will not start.

    The validations run in order:
    1. Settings validation (environment variables)
    2. Database connection validation
    3. Redis connection validation

    Raises:
        StartupValidationError: If any validation fails
    """
    logger.info("Starting application startup validations...")

    try:
        # Validate settings first (no external dependencies)
        await validate_settings()

        # Validate database connection
        await validate_database_connection()

        # Validate Redis connection
        await validate_redis_connection()

        logger.info("All startup validations passed successfully")

    except StartupValidationError as ex:
        logger.error(f"Startup validation failed: {ex}")
        logger.error(
            "Application will not start. Fix the configuration errors "
            "and try again."
        )
        raise
