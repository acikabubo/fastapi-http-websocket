"""
Decorator for consistent Redis error handling.

Wraps async methods / functions that perform Redis operations so that
Redis-related exceptions are caught, logged uniformly, and a safe
fallback value is returned — without cluttering call sites with
boilerplate try/except blocks.

Usage::

    from app.utils.redis_safe import redis_safe


    class MyService:
        @redis_safe(fail_value=None, operation_name="fetch_item")
        async def fetch(self, key: str) -> dict | None:
            redis = await self._get_redis()
            raw = await redis.get(key)
            return json.loads(raw) if raw else None


    @redis_safe(
        fail_value=0, log_level="warning", operation_name="count_items"
    )
    async def count_items(model: str) -> int:
        redis = await get_redis_connection()
        return int(await redis.get(f"count:{model}") or 0)
"""

import functools
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from redis.asyncio import RedisError as AsyncRedisError
from redis.exceptions import RedisError as SyncRedisError

from app.logging import logger
from app.utils.metrics.redis import redis_operations_total

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])

_LOG_METHODS: dict[str, Callable[..., None]] = {
    "debug": logger.debug,
    "info": logger.info,
    "warning": logger.warning,
    "error": logger.error,
}

_REDIS_ERRORS = (
    AsyncRedisError,
    SyncRedisError,
    ConnectionError,
    TimeoutError,
)


def redis_safe(
    *,
    fail_value: Any = None,
    log_level: str = "error",
    operation_name: str | None = None,
) -> Callable[[F], F]:
    """
    Decorator that catches Redis errors and returns a safe fallback value.

    Args:
        fail_value: Value returned when a Redis error occurs. Defaults to ``None``.
        log_level: Logging level for error messages (``"debug"``, ``"info"``,
            ``"warning"``, or ``"error"``). Defaults to ``"error"``.
        operation_name: Label used in log messages and the
            ``redis_operations_total`` Prometheus metric. Defaults to the
            decorated function's name.

    Returns:
        Decorator that wraps an async function with Redis error handling.
    """
    log_fn = _LOG_METHODS.get(log_level, logger.error)

    def decorator(func: F) -> F:
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except _REDIS_ERRORS as exc:
                log_fn(f"Redis error in {op_name}: {exc}")
                redis_operations_total.labels(
                    operation=op_name, status="error"
                ).inc()
                return fail_value
            except Exception as exc:  # noqa: BLE001
                log_fn(f"Unexpected error in {op_name}: {exc}")
                redis_operations_total.labels(
                    operation=op_name, status="error"
                ).inc()
                return fail_value

        return wrapper  # type: ignore[return-value]

    return decorator


def redis_safe_logging(level: str = "warning") -> Callable[[F], F]:
    """Shorthand: ``redis_safe`` with ``log_level`` pre-set and ``fail_value=None``."""
    return redis_safe(fail_value=None, log_level=level)
