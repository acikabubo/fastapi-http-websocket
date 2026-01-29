"""
Prometheus metrics for Redis operation monitoring.

This module defines metrics for tracking Redis operations, connection pool
status, and Redis performance.
"""

from app.utils.metrics._helpers import (
    _get_or_create_counter,
    _get_or_create_gauge,
    _get_or_create_histogram,
)

# Redis Metrics
redis_operations_total = _get_or_create_counter(
    "redis_operations_total",
    "Total Redis operations",
    [
        "operation",
        "status",
    ],  # operation: get, set, delete, etc; status: success, error
)

redis_operation_duration_seconds = _get_or_create_histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

redis_pool_max_connections = _get_or_create_gauge(
    "redis_pool_max_connections",
    "Maximum number of connections allowed in Redis pool",
    ["db"],
)

redis_pool_info = _get_or_create_gauge(
    "redis_pool_info",
    "Redis connection pool configuration info",
    [
        "db",
        "host",
        "port",
        "socket_timeout",
        "connect_timeout",
        "health_check_interval",
    ],
)

redis_pool_connections_created_total = _get_or_create_gauge(
    "redis_pool_connections_created_total",
    "Total connections created in Redis pool",
    ["db"],
)

redis_pool_connections_in_use = _get_or_create_gauge(
    "redis_pool_connections_in_use",
    "Current number of connections in use from Redis pool",
    ["db"],
)

redis_pool_connections_available = _get_or_create_gauge(
    "redis_pool_connections_available",
    "Current number of available connections in Redis pool",
    ["db"],
)

# Rate Limiting Metrics (Redis-backed)
rate_limit_hits_total = _get_or_create_counter(
    "rate_limit_hits_total",
    "Total rate limit hits (requests that exceeded limits)",
    ["limit_type"],  # http, ws_connection, ws_message
)

# Memory Cache Metrics (L1 cache in CacheManager)
memory_cache_hits_total = _get_or_create_counter(
    "memory_cache_hits_total",
    "Total memory cache hits (L1 cache)",
)

memory_cache_misses_total = _get_or_create_counter(
    "memory_cache_misses_total",
    "Total memory cache misses (L1 cache)",
)

memory_cache_evictions_total = _get_or_create_counter(
    "memory_cache_evictions_total",
    "Total memory cache evictions (LRU policy)",
)

memory_cache_size = _get_or_create_gauge(
    "memory_cache_size",
    "Current number of entries in memory cache",
)

__all__ = [
    "redis_operations_total",
    "redis_operation_duration_seconds",
    "redis_pool_max_connections",
    "redis_pool_info",
    "redis_pool_connections_created_total",
    "redis_pool_connections_in_use",
    "redis_pool_connections_available",
    "rate_limit_hits_total",
    "memory_cache_hits_total",
    "memory_cache_misses_total",
    "memory_cache_evictions_total",
    "memory_cache_size",
]
