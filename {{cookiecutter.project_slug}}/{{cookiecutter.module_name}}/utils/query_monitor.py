"""
Database query performance monitoring.

Provides SQLAlchemy event listeners for tracking query execution times,
identifying slow queries, and collecting performance metrics.
"""

import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.utils.metrics import (
    db_query_duration_seconds,
    db_slow_queries_total,
)

# Slow query threshold in seconds (default: 100ms)
SLOW_QUERY_THRESHOLD = 0.1


def _get_query_operation(statement: str) -> str:
    """
    Extract the operation type from a SQL statement.

    Args:
        statement: SQL statement string.

    Returns:
        Operation type (select, insert, update, delete, other).
    """
    statement_lower = statement.strip().lower()

    if statement_lower.startswith("select"):
        return "select"
    elif statement_lower.startswith("insert"):
        return "insert"
    elif statement_lower.startswith("update"):
        return "update"
    elif statement_lower.startswith("delete"):
        return "delete"
    else:
        return "other"


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(  # type: ignore[no-untyped-def]
    conn, cursor, statement, parameters, context, executemany
):
    """
    SQLAlchemy event listener: before query execution.

    Records the start time for query execution timing.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        statement: SQL statement to execute.
        parameters: Query parameters.
        context: Execution context.
        executemany: Whether executing multiple statements.
    """
    # Store start time in context for duration calculation
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(  # type: ignore[no-untyped-def]
    conn, cursor, statement, parameters, context, executemany
):
    """
    SQLAlchemy event listener: after query execution.

    Calculates query duration, logs slow queries, and records metrics.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        statement: SQL statement executed.
        parameters: Query parameters.
        context: Execution context.
        executemany: Whether executing multiple statements.
    """
    # Calculate query duration
    start_time = getattr(context, "_query_start_time", None)
    if start_time is None:
        return

    duration = time.time() - start_time
    operation = _get_query_operation(statement)

    # Record query duration metric
    db_query_duration_seconds.labels(operation=operation).observe(duration)

    # Check for slow queries
    if duration > SLOW_QUERY_THRESHOLD:
        # Increment slow query counter
        db_slow_queries_total.labels(operation=operation).inc()

        # Log slow query details
        # Truncate statement for logging (first 500 chars)
        statement_preview = (
            statement[:500] + "..." if len(statement) > 500 else statement
        )

        logger.warning(
            f"Slow query detected: {duration:.3f}s [{operation.upper()}] "
            f"Statement: {statement_preview}"
        )


def enable_query_monitoring() -> None:
    """
    Enable database query performance monitoring.

    This function is called during application startup to register
    SQLAlchemy event listeners for query timing and slow query detection.

    Note: Event listeners are registered globally via @event.listens_for
    decorators, so this function is primarily for documentation and
    potential future configuration.
    """
    logger.info(
        f"Database query monitoring enabled (slow query threshold: "
        f"{SLOW_QUERY_THRESHOLD * 1000:.0f}ms)"
    )
