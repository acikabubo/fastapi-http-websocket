"""
Layered Cache (CacheManager) Usage Examples.

This module demonstrates how to use the two-tier CacheManager for
performance optimization with in-memory (L1) + Redis (L2) caching.

Use cases:
- Frequently accessed data (hot keys)
- Reducing Redis network latency
- Improving cache hit performance

Trade-offs:
- Increased memory usage per instance
- Cache invalidation complexity
- Stale data risk in multi-instance deployments

Related:
- app/managers/cache_manager.py - Implementation
- docs_site/guides/performance-tuning.md - Performance guide
"""

from app.managers.cache_manager import get_cache_manager


# Example 1: Basic caching with CacheManager
async def basic_cache_example() -> dict[str, str]:
    """
    Basic cache usage: get, set, invalidate.

    The cache automatically handles two tiers:
    1. Memory cache (L1) - Fastest, no network latency
    2. Redis cache (L2) - Shared across instances
    """
    cache = get_cache_manager()

    # Set value in cache (both memory and Redis)
    await cache.set(
        key="user:123",
        value={"name": "John", "email": "john@example.com"},
        ttl=300,  # 5 minutes
    )

    # Get value from cache
    # First request: memory cache hit (fastest)
    user = await cache.get("user:123")
    print(f"User: {user}")

    # Invalidate cache
    await cache.invalidate("user:123")

    # After invalidation: cache miss
    user = await cache.get("user:123")
    print(f"After invalidation: {user}")  # None

    return user


# Example 2: Cache with fallback to database
async def cache_with_db_fallback_example(user_id: int):
    """
    Cache-aside pattern: try cache first, fallback to database.

    This is the most common caching pattern:
    1. Check cache (memory → Redis)
    2. If miss, query database
    3. Cache result for future requests
    """
    from app.models.author import Author
    from app.repositories.author_repository import AuthorRepository
    from app.storage.db import async_session

    cache = get_cache_manager()
    cache_key = f"author:{user_id}"

    # Try cache first
    cached_author = await cache.get(cache_key)
    if cached_author is not None:
        print(f"Cache hit: {cache_key}")
        return Author(**cached_author)

    # Cache miss - query database
    print(f"Cache miss: {cache_key}, querying database")
    async with async_session() as session:
        repo = AuthorRepository(session)
        author = await repo.get_by_id(user_id)

        if author is not None:
            # Cache result for future requests
            await cache.set(
                cache_key,
                author.model_dump(),
                ttl=300,  # 5 minutes
            )

        return author


# Example 3: Hot key caching for frequently accessed data
async def hot_key_caching_example():
    """
    Cache hot keys (frequently accessed data) in memory.

    Hot keys benefit most from L1 memory cache:
    - No Redis network latency
    - Sub-millisecond access time
    - Automatic LRU eviction

    Example hot keys:
    - Current user session
    - Application configuration
    - Feature flags
    - Popular product listings
    """
    cache = get_cache_manager()

    # Cache application config (rarely changes, frequently accessed)
    config = {
        "max_upload_size": 10485760,  # 10MB
        "allowed_file_types": ["jpg", "png", "pdf"],
        "feature_flags": {"dark_mode": True, "beta_features": False},
    }

    await cache.set(
        key="app:config",
        value=config,
        ttl=3600,  # 1 hour
    )

    # Subsequent requests hit memory cache (microseconds)
    cached_config = await cache.get("app:config")
    return cached_config


# Example 4: Pattern-based invalidation
async def pattern_invalidation_example():
    """
    Invalidate multiple cache keys matching a pattern.

    Useful for:
    - Invalidating all user sessions on logout
    - Clearing product cache after bulk update
    - Resetting feature flags

    WARNING: This clears entire memory cache and scans Redis.
    """
    cache = get_cache_manager()

    # Cache multiple user sessions
    await cache.set("session:user:123", {"logged_in": True}, ttl=600)
    await cache.set("session:user:456", {"logged_in": True}, ttl=600)
    await cache.set("session:user:789", {"logged_in": True}, ttl=600)

    # Invalidate all sessions (e.g., on security incident)
    deleted_count = await cache.invalidate_pattern("session:*")
    print(f"Invalidated {deleted_count} session keys")


# Example 5: Cache invalidation after CRUD operations
async def crud_with_cache_invalidation_example(author_id: int, new_name: str):
    """
    Always invalidate cache after UPDATE/DELETE operations.

    CRITICAL: Failing to invalidate cache after writes leads to stale data.
    """
    from app.repositories.author_repository import AuthorRepository
    from app.storage.db import async_session

    cache = get_cache_manager()
    cache_key = f"author:{author_id}"

    async with async_session() as session:
        repo = AuthorRepository(session)

        # Update author in database
        author = await repo.get_by_id(author_id)
        if author is None:
            raise ValueError(f"Author {author_id} not found")

        author.name = new_name
        updated_author = await repo.update(author)

        # ✅ CRITICAL: Invalidate cache after update
        await cache.invalidate(cache_key)

        return updated_author


# Example 6: Monitoring cache performance
async def cache_stats_example():
    """
    Get cache statistics for monitoring and tuning.

    Metrics available:
    - Memory cache size and usage
    - Cache hit/miss rates (Prometheus)
    - Eviction counts (Prometheus)
    """
    cache = get_cache_manager()

    # Get cache statistics
    stats = await cache.get_stats()
    print(f"Cache stats: {stats}")

    # Example output:
    # {
    #     "memory_cache_size": 234,
    #     "memory_cache_max": 1000,
    #     "memory_usage_percent": 23.4,
    #     "default_ttl": 300
    # }

    # Prometheus metrics (available at /metrics endpoint):
    # - memory_cache_hits_total
    # - memory_cache_misses_total
    # - memory_cache_evictions_total
    # - memory_cache_size


# Example 7: Custom TTL per cache entry
async def custom_ttl_example():
    """
    Use different TTL values based on data characteristics.

    Guidelines:
    - Frequently changing data: Short TTL (1-5 minutes)
    - Slowly changing data: Medium TTL (15-60 minutes)
    - Rarely changing data: Long TTL (1-24 hours)
    """
    cache = get_cache_manager()

    # User profile (changes occasionally): 15 minutes
    await cache.set(
        "user:profile:123",
        {"name": "John", "bio": "Developer"},
        ttl=900,  # 15 minutes
    )

    # Application config (rarely changes): 1 hour
    await cache.set(
        "app:config",
        {"version": "1.0.0", "features": []},
        ttl=3600,  # 1 hour
    )

    # Real-time data (changes frequently): 1 minute
    await cache.set(
        "dashboard:stats",
        {"active_users": 142, "requests_per_sec": 45},
        ttl=60,  # 1 minute
    )


# Example 8: Singleton cache manager usage
async def singleton_pattern_example():
    """
    CacheManager uses singleton pattern for consistent configuration.

    All calls to get_cache_manager() return the same instance.
    """
    # First call creates instance with configuration
    cache1 = get_cache_manager(
        max_memory_entries=1000,
        default_ttl=300,
    )

    # Subsequent calls return same instance (config params ignored)
    cache2 = get_cache_manager()

    # Both references point to same instance
    assert cache1 is cache2

    # Shared state across entire application
    await cache1.set("key1", "value1")
    value = await cache2.get("key1")  # Returns "value1"
    print(f"Value: {value}")


# Example 9: Multi-instance deployment considerations
async def multi_instance_warning_example():
    """
    WARNING: Memory cache is NOT shared across application instances.

    In horizontally scaled deployments:
    - Each instance has its own memory cache (L1)
    - Redis cache (L2) is shared
    - Cache invalidation must happen on ALL instances

    Strategies:
    1. Use Redis pub/sub to broadcast invalidations
    2. Accept eventual consistency (stale data window)
    3. Use Redis-only caching (skip memory layer)

    Recommendation:
    - Single instance: CacheManager provides significant benefit
    - Multi-instance: Use with caution or stick to Redis-only caching
    """
    # If running multiple instances, consider:
    # - Short TTL to reduce stale data window
    # - Redis pub/sub for cache invalidation coordination
    # - Monitoring for cache coherence issues

    # Example: Short TTL for multi-instance safety
    cache = get_cache_manager()
    await cache.set(
        "user:session:123",
        {"logged_in": True},
        ttl=60,  # Short TTL (1 minute)
    )


# Example 10: When NOT to use CacheManager
async def when_not_to_cache_example():
    """
    Scenarios where CacheManager should NOT be used.

    ❌ Don't cache:
    - Data that changes very frequently (> 10 updates/sec)
    - User-specific sensitive data (PII, passwords)
    - Large objects (> 1MB)
    - Data with complex invalidation requirements

    ✅ Use instead:
    - Pagination count caching (app/utils/pagination_cache.py)
    - Token caching (app/utils/token_cache.py)
    - Redis-only caching for shared state
    """
    # Bad example: Caching large objects
    # large_data = {"key": "x" * 1000000}  # 1MB+
    # await cache.set("large:data", large_data)  # DON'T DO THIS

    # Good example: Cache small, frequently accessed data
    cache = get_cache_manager()
    await cache.set(
        "feature:flags",
        {"dark_mode": True, "beta": False},
        ttl=3600,
    )


# Best Practices Summary
"""
CacheManager Best Practices:

✅ DO:
1. Use for hot keys (frequently accessed data)
2. Set appropriate TTL based on data change frequency
3. Invalidate cache after UPDATE/DELETE operations
4. Monitor cache hit rates and eviction counts
5. Use for small objects (< 100KB)
6. Consider single-instance deployment benefits

❌ DON'T:
1. Cache frequently changing data (> 10 updates/sec)
2. Cache large objects (> 1MB)
3. Skip cache invalidation after writes
4. Use in multi-instance deployments without coordination
5. Cache sensitive data (use encryption if needed)

Performance Tips:
- Memory cache (L1): Sub-millisecond latency
- Redis cache (L2): 1-5ms latency
- Database query: 10-100ms latency
- Target cache hit rate: > 85%

Deployment Considerations:
- Single instance: CacheManager provides 80-95% latency reduction
- Multi-instance: Use with caution (cache coherence issues)
- Horizontally scaled: Consider Redis-only caching

See also:
- app/managers/cache_manager.py - Implementation
- docs_site/guides/performance-tuning.md - Performance guide
- app/utils/pagination_cache.py - Pagination caching
- app/utils/token_cache.py - Token caching
"""
