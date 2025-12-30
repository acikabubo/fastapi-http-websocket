"""
Mock factory functions for Redis testing.

Provides pre-configured Redis mocks with common operations.
"""

from unittest.mock import AsyncMock, MagicMock


def create_mock_redis_connection():
    """
    Creates a mock Redis connection with common methods.

    Returns:
        AsyncMock: Mocked Redis connection
    """
    redis_mock = AsyncMock()

    # Key-value operations
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.ttl = AsyncMock(return_value=-1)

    # Increment/decrement operations
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.decr = AsyncMock(return_value=0)
    redis_mock.incrby = AsyncMock(return_value=10)

    # Set operations
    redis_mock.sadd = AsyncMock(return_value=1)
    redis_mock.srem = AsyncMock(return_value=1)
    redis_mock.sismember = AsyncMock(return_value=False)
    redis_mock.smembers = AsyncMock(return_value=set())
    redis_mock.scard = AsyncMock(return_value=0)

    # Sorted set operations (for rate limiting)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zremrangebyscore = AsyncMock(return_value=0)
    redis_mock.zrange = AsyncMock(return_value=[])
    redis_mock.zrem = AsyncMock(return_value=1)

    # Hash operations
    redis_mock.hset = AsyncMock(return_value=1)
    redis_mock.hget = AsyncMock(return_value=None)
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.hdel = AsyncMock(return_value=1)

    # Pub/sub operations
    redis_mock.publish = AsyncMock(return_value=0)
    redis_mock.subscribe = AsyncMock()
    redis_mock.unsubscribe = AsyncMock()

    # Pipeline operations
    pipeline_mock = MagicMock()
    pipeline_mock.execute = AsyncMock(return_value=[])
    redis_mock.pipeline = MagicMock(return_value=pipeline_mock)

    # Connection management
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()

    return redis_mock


def create_mock_rate_limiter():
    """
    Creates a mock RateLimiter instance.

    Returns:
        MagicMock: Mocked RateLimiter instance
    """
    from app.utils.rate_limiter import RateLimiter

    limiter_mock = MagicMock(spec=RateLimiter)
    limiter_mock.check_rate_limit = AsyncMock(return_value=(True, 10))
    return limiter_mock


def create_mock_connection_limiter():
    """
    Creates a mock ConnectionLimiter instance.

    Returns:
        MagicMock: Mocked ConnectionLimiter instance
    """
    from app.utils.rate_limiter import ConnectionLimiter

    limiter_mock = MagicMock(spec=ConnectionLimiter)
    limiter_mock.add_connection = AsyncMock(return_value=True)
    limiter_mock.remove_connection = AsyncMock()
    return limiter_mock
