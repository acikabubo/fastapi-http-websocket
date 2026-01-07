"""
Redis connection pool metrics collection task.

This task periodically collects and updates Prometheus metrics for Redis
connection pool usage. This enables monitoring of pool health, detecting
pool exhaustion, and identifying connection leaks.

The task runs every 15 seconds by default to provide real-time visibility
into pool metrics without excessive overhead.
"""

import asyncio

from app.constants import TASK_ERROR_BACKOFF_SECONDS
from app.logging import logger
from app.storage.redis import RedisPool

# Update pool metrics every 15 seconds
REDIS_POOL_METRICS_INTERVAL_SECONDS = 15


async def redis_pool_metrics_task() -> None:
    """
    Periodically update Redis connection pool metrics for Prometheus.

    This background task collects current pool statistics (connections in use,
    available, created) and updates Prometheus gauges every 15 seconds.

    Metrics collected:
    - redis_pool_connections_in_use: Active connections
    - redis_pool_connections_available: Idle connections
    - redis_pool_connections_created_total: Total created

    The task runs continuously and handles errors gracefully to prevent
    disrupting other background tasks.
    """
    logger.info("Starting Redis pool metrics collection task")

    while True:
        try:
            # Update pool metrics for all databases
            RedisPool.update_pool_metrics()

            # Wait before next collection
            await asyncio.sleep(REDIS_POOL_METRICS_INTERVAL_SECONDS)

        except Exception as ex:
            logger.error(
                f"Error in redis_pool_metrics_task: {ex}", exc_info=True
            )
            # Back off on errors to avoid log spam
            await asyncio.sleep(TASK_ERROR_BACKOFF_SECONDS)
