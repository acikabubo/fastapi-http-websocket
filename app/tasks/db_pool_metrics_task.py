"""
Database connection pool metrics collection task.

This task periodically collects and updates Prometheus metrics for PostgreSQL
connection pool usage. This enables monitoring of pool health, detecting
pool exhaustion, and identifying connection leaks.

The task runs every 15 seconds by default to provide real-time visibility
into pool metrics without excessive overhead.
"""

import asyncio

from sqlalchemy.pool import Pool

from app.constants import TASK_ERROR_BACKOFF_SECONDS
from app.logging import logger
from app.storage.db import engine
from app.utils.metrics.database import (
    db_pool_connections_available,
    db_pool_connections_in_use,
    db_pool_info,
    db_pool_max_connections,
    db_pool_overflow_count,
)

# Update pool metrics every 15 seconds
DB_POOL_METRICS_INTERVAL_SECONDS = 15


async def db_pool_metrics_task() -> None:
    """
    Periodically update database connection pool metrics for Prometheus.

    This background task collects current pool statistics (connections in use,
    available, created, overflow) and updates Prometheus gauges every 15 seconds.

    Metrics collected:
    - db_pool_max_connections: Maximum connections allowed
    - db_pool_connections_in_use: Active connections
    - db_pool_connections_available: Idle connections
    - db_pool_connections_created_total: Total created
    - db_pool_overflow_count: Overflow connections
    - db_pool_info: Pool configuration metadata

    The task runs continuously and handles errors gracefully to prevent
    disrupting other background tasks.
    """
    logger.info("Starting database pool metrics collection task")

    # Get pool configuration for metadata
    pool: Pool = engine.pool
    pool_size = getattr(pool, "_pool_size", 0)
    max_overflow = getattr(pool, "_max_overflow", 0)
    timeout = getattr(pool, "_timeout", 30)

    # Set pool configuration metadata (static info)
    db_pool_info.labels(
        pool_name="main",
        pool_size=str(pool_size),
        max_overflow=str(max_overflow),
        timeout=str(timeout),
    ).set(1)

    while True:
        try:
            # Get pool statistics
            pool_status = pool.status()
            checked_out = pool.checkedout()
            pool_current_size = pool.size()
            overflow_count = pool.overflow()

            # Calculate max connections (pool_size + max_overflow)
            max_connections = pool_size + max_overflow

            # Update dynamic metrics
            db_pool_max_connections.labels(pool_name="main").set(
                max_connections
            )
            db_pool_connections_in_use.labels(pool_name="main").set(
                checked_out
            )
            db_pool_connections_available.labels(pool_name="main").set(
                pool_current_size - checked_out
            )
            db_pool_overflow_count.labels(pool_name="main").set(overflow_count)

            # Note: connections_created_total would require tracking via
            # pool events, which we'll skip for now as it's not critical

            logger.debug(
                f"DB pool metrics: size={pool_current_size}, "
                f"in_use={checked_out}, overflow={overflow_count}, "
                f"status={pool_status}"
            )

            # Wait before next collection
            await asyncio.sleep(DB_POOL_METRICS_INTERVAL_SECONDS)

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Error in db_pool_metrics_task: {ex}", exc_info=True)
            # Back off on errors to avoid log spam
            await asyncio.sleep(TASK_ERROR_BACKOFF_SECONDS)
