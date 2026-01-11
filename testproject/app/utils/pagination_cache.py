"""
Pagination count caching for improved performance.

Provides Redis-based caching of expensive COUNT queries used in pagination.
Cache keys are based on model name and filter parameters.
"""

import hashlib
import json
from typing import Any

from redis.exceptions import RedisError

from app.logging import logger
from app.storage.redis import RedisPool


# Default TTL for count caches (5 minutes)
DEFAULT_COUNT_CACHE_TTL = 300


async def get_cached_count(
    model_name: str, filters: dict[str, Any] | None = None
) -> int | None:
    """
    Get cached count for a model query.

    Args:
        model_name: Name of the SQLModel class.
        filters: Query filters (must be JSON-serializable).

    Returns:
        Cached count if available, None otherwise.
    """
    cache_key = _generate_count_cache_key(model_name, filters)

    try:
        redis = await RedisPool.get_instance()
        if redis is None:
            logger.warning("Redis unavailable, skipping count cache lookup")
            return None

        cached = await redis.get(cache_key)
        if cached is not None:
            count = int(cached)
            logger.debug(
                f"Count cache hit for {model_name} (filters: {filters}): {count}"
            )
            return count

        logger.debug(f"Count cache miss for {model_name} (filters: {filters})")
        return None

    except (RedisError, ConnectionError) as ex:
        # RedisError: Redis operation failed
        # ConnectionError: Redis connection issues
        logger.error(f"Error reading count cache: {ex}")
        return None
    except (ValueError, TypeError) as ex:
        # ValueError/TypeError: Invalid cached data format
        logger.error(f"Invalid count cache data format: {ex}")
        return None


async def set_cached_count(
    model_name: str,
    count: int,
    filters: dict[str, Any] | None = None,
    ttl: int = DEFAULT_COUNT_CACHE_TTL,
) -> None:
    """
    Cache a count result for a model query.

    Args:
        model_name: Name of the SQLModel class.
        count: The count value to cache.
        filters: Query filters (must be JSON-serializable).
        ttl: Time-to-live in seconds (default: 5 minutes).
    """
    cache_key = _generate_count_cache_key(model_name, filters)

    try:
        redis = await RedisPool.get_instance()
        if redis is None:
            logger.warning("Redis unavailable, skipping count cache storage")
            return

        await redis.setex(cache_key, ttl, str(count))
        logger.debug(
            f"Cached count for {model_name} (filters: {filters}): {count} (TTL: {ttl}s)"
        )

    except (RedisError, ConnectionError) as ex:
        # RedisError: Redis operation failed
        # ConnectionError: Redis connection issues
        logger.error(f"Error writing count cache: {ex}")


async def invalidate_count_cache(
    model_name: str, filters: dict[str, Any] | None = None
) -> None:
    """
    Invalidate cached count for a model query.

    Useful when data changes (INSERT, UPDATE, DELETE operations).

    Args:
        model_name: Name of the SQLModel class.
        filters: Query filters to invalidate (None = invalidate all for model).
    """
    try:
        redis = await RedisPool.get_instance()
        if redis is None:
            logger.warning(
                "Redis unavailable, skipping count cache invalidation"
            )
            return

        if filters is None:
            # Invalidate all counts for this model
            pattern = f"pagination:count:{model_name}:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await redis.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    deleted_count += await redis.delete(*keys)

                if cursor == 0:
                    break

            logger.info(
                f"Invalidated {deleted_count} count cache entries for {model_name}"
            )
        else:
            # Invalidate specific filter combination
            cache_key = _generate_count_cache_key(model_name, filters)
            deleted = await redis.delete(cache_key)
            if deleted:
                logger.debug(
                    f"Invalidated count cache for {model_name} (filters: {filters})"
                )

    except (RedisError, ConnectionError) as ex:
        # RedisError: Redis operation failed
        # ConnectionError: Redis connection issues
        logger.error(f"Error invalidating count cache: {ex}")


def _generate_count_cache_key(
    model_name: str, filters: dict[str, Any] | None
) -> str:
    """
    Generate a cache key for a count query.

    Uses model name and filter hash to create a unique, deterministic key.

    Args:
        model_name: Name of the SQLModel class.
        filters: Query filters (must be JSON-serializable).

    Returns:
        Redis cache key string.
    """
    if filters:
        # Sort filters for consistent hashing
        sorted_filters = json.dumps(filters, sort_keys=True)
        filter_hash = hashlib.md5(
            sorted_filters.encode(), usedforsecurity=False
        ).hexdigest()[:8]
        return f"pagination:count:{model_name}:{filter_hash}"
    else:
        return f"pagination:count:{model_name}:all"
