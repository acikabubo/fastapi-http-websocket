"""Health check endpoint for monitoring service status."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis.asyncio import RedisError as AsyncRedisError
from redis.exceptions import RedisError as SyncRedisError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.settings import app_settings
from {{cookiecutter.module_name}}.storage.db import engine
from {{cookiecutter.module_name}}.storage.redis import get_redis_connection
from {{cookiecutter.module_name}}.utils.metrics import get_websocket_health_info

router = APIRouter()


class WebSocketHealthInfo(BaseModel):
    """WebSocket health information."""

    status: str
    active_connections: int


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
    database: str
    redis: str
    websocket: WebSocketHealthInfo


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
    - WebSocket system health (active connections, metrics)

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

    # Get WebSocket health information
    ws_health_data = get_websocket_health_info()
    ws_health = WebSocketHealthInfo(**ws_health_data)

    overall_status = (
        "healthy"
        if db_status == "healthy"
        and redis_status == "healthy"
        and ws_health.status == "healthy"
        else "unhealthy"
    )

    if overall_status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        database=db_status,
        redis=redis_status,
        websocket=ws_health,
    )
