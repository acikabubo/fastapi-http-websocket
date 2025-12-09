"""Health check endpoint for monitoring service status."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis.asyncio import RedisError as AsyncRedisError
from redis.exceptions import RedisError as SyncRedisError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.logging import logger
from app.settings import app_settings
from app.storage.db import engine
from app.storage.redis import get_redis_connection

router = APIRouter()


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
    database: str
    redis: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    tags=["health"],
)
async def health_check(response: Response) -> HealthResponse:
    """
    Check health status of the application and its dependencies.

    This endpoint verifies:
    - Database connectivity (PostgreSQL)
    - Redis connectivity

    Returns:
        HealthResponse: Health status of the service and dependencies.
        Returns 503 Service Unavailable if any service is unhealthy.

    Raises:
        HTTPException: If any critical service is unavailable.
    """
    db_status = "healthy"
    redis_status = "healthy"

    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except (OperationalError, SQLAlchemyError, TimeoutError) as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    except Exception as e:
        # Catch-all for health checks to prevent endpoint failure
        logger.error(f"Unexpected database health check error: {e}")
        db_status = "unhealthy"

    # Check Redis connection
    try:
        r = await get_redis_connection(db=app_settings.MAIN_REDIS_DB)
        await r.ping()
    except (AsyncRedisError, SyncRedisError, ConnectionError, TimeoutError) as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    except Exception as e:
        # Catch-all for health checks to prevent endpoint failure
        logger.error(f"Unexpected Redis health check error: {e}")
        redis_status = "unhealthy"

    overall_status = (
        "healthy"
        if db_status == "healthy" and redis_status == "healthy"
        else "unhealthy"
    )

    if overall_status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status, database=db_status, redis=redis_status
    )
