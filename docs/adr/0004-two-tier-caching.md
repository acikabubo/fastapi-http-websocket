# 4. Use Two-Tier Memory + Redis Caching for Hot Keys

Date: 2025-01-29

## Status

Accepted

## Context

The application needed caching to reduce database load and improve response times. The system had several caching requirements:

1. **Hot keys**: Frequently accessed data (user sessions, config, feature flags)
2. **Shared state**: Cache shared across application instances
3. **Fast access**: Sub-millisecond latency for hot keys
4. **Consistency**: Reasonable balance between performance and data freshness

Redis-only caching (L2) provides shared state but has network latency (1-5ms). For hot keys accessed 100+ times per second, this latency compounds.

In-memory caching (L1) is faster (<1ms) but not shared across instances, risking stale data in horizontally scaled deployments.

## Decision

Implement **two-tier caching (CacheManager)** with in-memory (L1) + Redis (L2):

1. **Architecture**:
   - **L1 Cache (Memory)**: Fastest access, LRU eviction, per-instance
   - **L2 Cache (Redis)**: Shared state, persistent, cross-instance

2. **Cache Flow**:
   ```
   get(key) → Check Memory → Check Redis → Return None
                 ↓ Hit          ↓ Hit
              Return value   Store in Memory
                             Return value

   set(key, value) → Store in Memory → Store in Redis
   ```

3. **CacheManager** (`app/managers/cache_manager.py`):
   - Singleton pattern for consistent configuration
   - LRU eviction when memory cache full
   - TTL expiration for both tiers
   - Pattern-based invalidation (clears both tiers)
   - Graceful degradation (Redis unavailable → memory only)

4. **Configuration**:
   - `max_memory_entries`: LRU size limit (default: 1000)
   - `default_ttl`: Default TTL in seconds (default: 300)

**Implementation:**

```python
from app.managers.cache_manager import get_cache_manager

# Get singleton cache manager
cache = get_cache_manager(
    max_memory_entries=1000,  # LRU eviction after 1000 entries
    default_ttl=300,          # 5 minutes default TTL
)

# Cache-aside pattern
async def get_user_profile(user_id: int):
    cache_key = f"user:profile:{user_id}"

    # Try cache first (L1 → L2)
    profile = await cache.get(cache_key)
    if profile is not None:
        return profile

    # Cache miss - query database
    profile = await db.query_user_profile(user_id)

    # Cache result (L1 + L2)
    await cache.set(cache_key, profile, ttl=900)

    return profile

# CRITICAL: Invalidate after updates
async def update_user_profile(user_id: int, data: dict):
    await db.update_user_profile(user_id, data)

    # Invalidate both tiers
    await cache.invalidate(f"user:profile:{user_id}")
```

**When to Use**:

✅ Use CacheManager when:
- Hot keys accessed very frequently (>100 requests/sec)
- Data changes infrequently (<1 update/minute)
- Single-instance deployment
- Small objects (<100KB)
- Redis latency is bottleneck (>5ms p95)

⚠️ Use with caution when:
- Horizontally scaled deployment (cache coherence issues)
- Data changes frequently (>10 updates/sec)
- Large objects (>1MB)

**Alternative for shared state**: Use Redis-only caching (`pagination_cache.py`, `token_cache.py`)

## Consequences

### Positive Consequences

- **80-95% Latency Reduction**: Memory hits <1ms vs Redis 1-5ms
- **Reduced Redis Load**: 70-90% reduction in Redis queries (memory hit rate)
- **Better User Experience**: Sub-millisecond response times for hot keys
- **Graceful Degradation**: Works memory-only if Redis unavailable
- **Automatic LRU Eviction**: Memory doesn't grow unbounded
- **Prometheus Metrics**: Track cache hit rates and evictions

### Negative Consequences

- **Memory Usage**: Each instance uses memory for L1 cache (~10-50MB typical)
- **Cache Coherence**: Memory cache not shared across instances (stale data risk)
- **Invalidation Complexity**: Must invalidate both tiers
- **Multi-Instance Issues**: Stale data window in horizontally scaled deployments

### Neutral Consequences

- **Singleton Pattern**: One cache manager per application instance
- **Async Only**: All methods are async (matches FastAPI)

## Alternatives Considered

### Alternative 1: Redis-Only Caching

**Description**: Use only Redis (L2) for all caching, skip memory layer

**Pros**:
- Shared across all instances (no stale data)
- Simpler architecture (one tier)
- No memory usage on application instances
- Better for horizontally scaled deployments

**Cons**:
- Network latency (1-5ms per request)
- Higher Redis load (100% of cache queries)
- Slower for hot keys
- No fallback if Redis unavailable

**Why not chosen**: Hot keys benefit significantly from memory caching. For shared state, use Redis-only caching (`pagination_cache.py`, `token_cache.py`) instead of CacheManager.

### Alternative 2: Memory-Only Caching

**Description**: Use only in-memory caching (L1), skip Redis

**Pros**:
- Fastest possible (<1ms)
- No Redis dependency
- No network latency
- Simplest implementation

**Cons**:
- Not shared across instances (stale data)
- Lost on application restart
- Cannot share cache between processes
- No persistence

**Why not chosen**: Shared state is important for multi-process deployments (even single-server). Redis provides persistence and shared cache.

### Alternative 3: Write-Through Caching

**Description**: Write to cache and database simultaneously

**Pros**:
- Cache always up-to-date
- No cache invalidation needed
- Simpler logic

**Cons**:
- Higher write latency (cache + DB)
- More complex error handling
- Cache failures block writes
- Not suitable for read-heavy workloads

**Why not chosen**: Read-heavy workloads benefit more from cache-aside pattern. Write-through adds latency without equivalent benefit.

### Alternative 4: Memcached

**Description**: Use Memcached instead of Redis for L2 cache

**Pros**:
- Simpler protocol (faster)
- Lower memory overhead
- Purpose-built for caching

**Cons**:
- No persistence (lost on restart)
- No pattern-based invalidation (SCAN)
- No Redis Pub/Sub for cache invalidation
- Less feature-rich than Redis

**Why not chosen**: Already using Redis for other features (rate limiting, session storage). Adding Memcached increases infrastructure complexity without significant benefit.

## References

- [Caching Strategies](https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-patterns.html) - AWS best practices
- [LRU Cache Implementation](https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU) - Wikipedia
- [app/managers/cache_manager.py](../../app/managers/cache_manager.py) - Implementation
- [examples/layered_cache_usage.py](../../examples/layered_cache_usage.py) - Usage examples
- [docs_site/guides/performance-tuning.md](../../docs_site/guides/performance-tuning.md) - Performance guide
- [tests/unit/utils/test_cache_manager.py](../../tests/unit/utils/test_cache_manager.py) - Comprehensive tests

## Notes

**Performance Benchmarks** (single-instance deployment):

| Tier | Latency | Use Case | Cache Hit Rate |
|------|---------|----------|----------------|
| Memory (L1) | <1ms | Hot keys | 85-95% |
| Redis (L2) | 1-5ms | Warm keys | 10-15% |
| Database | 10-100ms | Cold keys | 0-5% |

**Hot Key Examples**:
- Application configuration (rarely changes, frequently accessed)
- Feature flags (changes hourly, accessed every request)
- User sessions (active for hours, accessed per request)
- Rate limit counters (changes per request, accessed per request)

**Cache Invalidation Patterns**:

```python
# Invalidate single key (both tiers)
await cache.invalidate("user:profile:123")

# Invalidate pattern (clears entire memory cache + Redis SCAN)
await cache.invalidate_pattern("user:profile:*")

# Clear entire memory cache (keeps Redis)
await cache.clear()
```

**Multi-Instance Deployment Strategies**:

1. **Short TTL** (<1 minute): Reduces stale data window
2. **Accept Eventual Consistency**: Stale data acceptable for some use cases
3. **Redis-Only**: Skip memory layer for critical shared state
4. **Redis Pub/Sub**: Broadcast invalidations across instances (future enhancement)

**Monitoring**:

```promql
# Memory cache hit rate
rate(memory_cache_hits_total[5m]) /
(rate(memory_cache_hits_total[5m]) + rate(memory_cache_misses_total[5m]))

# Memory cache size
memory_cache_size

# LRU evictions
rate(memory_cache_evictions_total[5m])
```

**Target Metrics**:
- Memory cache hit rate: >85%
- Memory cache size: <1000 entries (configurable)
- LRU evictions: <10/minute (indicates good cache sizing)

**Future Enhancements**:
1. Redis Pub/Sub for cache invalidation coordination across instances
2. Configurable per-key TTL overrides
3. Cache warming on application startup
4. Adaptive TTL based on access patterns
5. Cache compression for large values

**Testing Strategy**:
- Unit tests: Mock Redis, test memory cache logic
- Integration tests: Real Redis, test full two-tier flow
- Load tests: Verify cache hit rates under load
- Chaos tests: Redis failures, graceful degradation
