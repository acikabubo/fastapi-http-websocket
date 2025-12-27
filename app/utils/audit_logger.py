"""
Audit logging utilities for tracking user actions.

This module provides utilities for logging user actions to the database
for security, compliance, debugging, and analytics purposes.

Uses an async queue and background worker for non-blocking audit log writes.
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from starlette.requests import Request

from app.logging import logger
from app.models.user_action import UserAction
from app.settings import app_settings
from app.storage.db import async_session
from app.utils.metrics import (
    audit_batch_size,
    audit_log_creation_duration_seconds,
    audit_log_errors_total,
    audit_logs_dropped_total,
    audit_logs_total,
    audit_logs_written_total,
    audit_queue_size,
)

# Sensitive field names that should be redacted from logs
SENSITIVE_FIELDS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "private_key",
    "ssn",
    "social_security_number",
    "credit_card",
    "card_number",
    "cvv",
    "authorization",
}

# Global queue for audit logs (initialized lazily)
_audit_queue: asyncio.Queue[UserAction] | None = None


def get_audit_queue() -> asyncio.Queue[UserAction]:
    """
    Get or create the global audit log queue.

    Returns:
        Async queue for audit log entries.
    """
    global _audit_queue
    if _audit_queue is None:
        _audit_queue = asyncio.Queue(maxsize=app_settings.AUDIT_QUEUE_MAX_SIZE)
    return _audit_queue


async def audit_log_worker():
    """
    Background worker that processes audit logs from queue in batches.

    Collects audit log entries from the queue and writes them to the database
    in batches to improve performance. Runs continuously until application
    shutdown.
    """
    queue = get_audit_queue()
    logger.info("Audit log background worker started")

    while True:
        try:
            batch: list[UserAction] = []

            # Collect batch of logs (up to AUDIT_BATCH_SIZE or timeout)
            try:
                for _ in range(app_settings.AUDIT_BATCH_SIZE):
                    log_entry = await asyncio.wait_for(
                        queue.get(),
                        timeout=app_settings.AUDIT_BATCH_TIMEOUT,
                    )
                    batch.append(log_entry)
            except asyncio.TimeoutError:
                # Batch timeout reached, process what we have
                pass

            # Write batch to database if we have any logs
            if batch:
                start_time = time.time()

                try:
                    async with async_session() as session:
                        async with session.begin():
                            session.add_all(batch)
                            await session.flush()

                    # Update metrics
                    duration = time.time() - start_time
                    audit_batch_size.observe(len(batch))
                    audit_logs_written_total.inc(len(batch))
                    audit_log_creation_duration_seconds.observe(duration)

                    # Update outcome counts
                    for log_entry in batch:
                        audit_logs_total.labels(outcome=log_entry.outcome).inc()

                    logger.debug(f"Wrote {len(batch)} audit logs to database in {duration:.3f}s")

                except Exception as e:
                    # Record batch write error
                    audit_log_errors_total.labels(error_type=type(e).__name__).inc()
                    logger.error(f"Failed to write audit log batch: {e}")

            # Update queue size metric
            audit_queue_size.set(queue.qsize())

        except Exception as e:
            logger.error(f"Audit log worker error: {e}")
            await asyncio.sleep(1)  # Backoff on errors


async def flush_audit_queue() -> int:
    """
    Flush all remaining audit logs from the queue to the database.

    This should be called during application shutdown to ensure no logs are lost.

    Returns:
        Number of logs flushed.
    """
    queue = get_audit_queue()
    remaining_logs: list[UserAction] = []

    logger.info(f"Flushing {queue.qsize()} remaining audit logs")

    # Collect all remaining logs from queue
    while not queue.empty():
        try:
            log_entry = queue.get_nowait()
            remaining_logs.append(log_entry)
        except asyncio.QueueEmpty:
            break

    # Write to database
    if remaining_logs:
        try:
            async with async_session() as session:
                async with session.begin():
                    session.add_all(remaining_logs)
                    await session.flush()

            logger.info(f"Flushed {len(remaining_logs)} audit logs to database")
            return len(remaining_logs)

        except Exception as e:
            logger.error(f"Failed to flush audit logs: {e}")
            return 0

    return 0


def sanitize_data(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Remove sensitive fields from data before logging.

    Args:
        data: Dictionary potentially containing sensitive information.

    Returns:
        Sanitized dictionary with sensitive fields redacted, or None if
        input was None.
    """
    if data is None:
        return None

    sanitized = {}
    for key, value in data.items():
        # Check if key matches any sensitive field name (case-insensitive)
        if key.lower() in SENSITIVE_FIELDS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_data(value)
        elif isinstance(value, list):
            # Sanitize list items if they are dictionaries
            sanitized[key] = [
                sanitize_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def extract_ip_address(request: Request) -> str | None:
    """
    Extract client IP address from request with spoofing protection.

    Uses the secure get_client_ip() function which validates X-Forwarded-For
    headers against trusted proxy list to prevent IP spoofing.

    Args:
        request: Starlette request object.

    Returns:
        Client IP address, or None if not available.
    """
    from app.utils.ip_utils import get_client_ip

    return get_client_ip(request)


async def log_user_action(
    user_id: str,
    username: str,
    user_roles: list[str],
    action_type: str,
    resource: str,
    outcome: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    request_data: dict[str, Any] | None = None,
    response_status: int | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> UserAction | None:
    """
    Queue a user action for asynchronous logging to the database.

    This function is non-blocking - it adds the log entry to a queue for
    background processing, allowing the request to complete immediately.

    Args:
        user_id: Keycloak user ID (sub claim).
        username: Username (preferred_username claim).
        user_roles: List of user roles at time of action.
        action_type: Type of action (HTTP method or WebSocket PkgID).
        resource: Resource accessed (URL path or entity identifier).
        outcome: Result of the action (success, error, permission_denied).
        ip_address: Client IP address.
        user_agent: Browser/client user agent string.
        request_id: Request UUID for correlation.
        request_data: Request payload (will be sanitized).
        response_status: HTTP status code or WebSocket response code.
        error_message: Error details if action failed.
        duration_ms: Request processing duration in milliseconds.

    Returns:
        The created UserAction instance (not yet persisted), or None if queueing failed.
    """
    try:
        # Sanitize request data to remove sensitive information
        sanitized_data = sanitize_data(request_data)

        # Create audit log entry
        action = UserAction(
            timestamp=datetime.now(UTC),
            user_id=user_id,
            username=username,
            user_roles=user_roles,
            action_type=action_type,
            resource=resource,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=str(request_id) if request_id else None,
            request_data=sanitized_data,
            response_status=response_status,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        # Queue for background processing (non-blocking)
        queue = get_audit_queue()
        try:
            queue.put_nowait(action)
            # Update queue size metric
            audit_queue_size.set(queue.qsize())
            return action

        except asyncio.QueueFull:
            # Queue is full, drop the log entry
            audit_logs_dropped_total.inc()
            logger.warning(
                f"Audit queue full ({app_settings.AUDIT_QUEUE_MAX_SIZE}), "
                f"dropping log entry for {username}"
            )
            return None

    except Exception as e:
        # Record audit log error
        audit_log_errors_total.labels(error_type=type(e).__name__).inc()

        # Log the error but don't fail the request
        logger.error(f"Failed to queue user action: {e}")
        return None
