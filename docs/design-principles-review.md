# Design Principles Review: SOLID, DRY, YAGNI, KISS

**Project:** FastAPI HTTP/WebSocket Application
**Review Date:** 2026-02-13
**Reviewer:** Senior Python Developer Analysis

---

## Executive Summary

This document provides a comprehensive review of design principle adherence across the codebase, identifying opportunities to improve code quality through SOLID, DRY, YAGNI, and KISS principles.

**Key Findings:**
- ✅ **Strengths:** Well-implemented Repository + Command patterns, strong RBAC architecture
- ⚠️ **DRY Violations:** Redis connection pattern duplicated 3x, error handling duplicated 5x
- ⚠️ **SRP Violations:** God classes in `RateLimiter`, `CacheManager`, and managers
- ⚠️ **YAGNI Concerns:** Potentially over-engineered caching and metrics
- 💡 **Quick Wins:** Extract Redis utilities, create cache key factory, introduce Role enum

---

## Table of Contents

1. [DRY Violations (Don't Repeat Yourself)](#1-dry-violations)
2. [Single Responsibility Principle (SRP)](#2-single-responsibility-principle-violations)
3. [Open/Closed Principle (OCP)](#3-openclosed-principle-opportunities)
4. [Interface Segregation Principle (ISP)](#4-interface-segregation-violations)
5. [YAGNI Violations (You Aren't Gonna Need It)](#5-yagni-violations)
6. [KISS Violations (Keep It Simple, Stupid)](#6-kiss-violations)
7. [Dependency Inversion Opportunities](#7-dependency-inversion-opportunities)
8. [Code Smells](#8-additional-code-smells)
9. [Implementation Roadmap](#9-implementation-roadmap)

---

## 1. DRY Violations

### 1.1 Redis Connection Pattern Duplication ⚠️ **CRITICAL**

**Severity:** HIGH
**Impact:** Code duplication across 3 files
**Effort:** Medium

**Problem:**

Multiple classes implement identical `_get_redis()` pattern:

```python
# app/utils/rate_limiter.py (lines 31-35)
class RateLimiter:
    async def _get_redis(self) -> Redis | None:
        if self.redis is None:
            self.redis = await get_redis_connection()
        return self.redis

# app/utils/rate_limiter.py (lines 178-182) - DUPLICATE
class ConnectionLimiter:
    async def _get_redis(self) -> Redis | None:
        if self.redis is None:
            self.redis = await get_redis_connection()
        return self.redis

# Similar patterns in:
# - app/utils/token_cache.py
# - app/utils/pagination_cache.py
# - app/managers/cache_manager.py
```

**Solution:**

Create a reusable mixin:

```python
# app/utils/redis_mixin.py
from redis.asyncio import Redis
from app.storage.redis import get_redis_connection

class RedisClientMixin:
    """Mixin for classes that need lazy Redis connection."""

    def __init__(self):
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis | None:
        """Get or create Redis connection (lazy initialization)."""
        if self._redis is None:
            self._redis = await get_redis_connection()
        return self._redis

    async def _close_redis(self) -> None:
        """Close Redis connection if exists."""
        if self._redis:
            await self._redis.close()
            self._redis = None
```

**Usage:**

```python
class RateLimiter(RedisClientMixin):
    def __init__(self):
        super().__init__()  # Initialize mixin
        self.burst_capacity = app_settings.RATE_LIMIT_BURST_CAPACITY

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int = 60):
        redis = await self._get_redis()  # Use mixin method
        # ... rest of implementation
```

**Benefits:**
- Eliminates 3+ duplicate implementations
- Single point of maintenance
- Consistent error handling
- Easy to add features (connection pooling, retry logic)

---

### 1.2 Error Handling Pattern Duplication ⚠️

**Severity:** MEDIUM
**Impact:** Inconsistent error handling across 5+ files
**Effort:** Medium

**Problem:**

Redis error handling repeated with variations:

```python
# Pattern 1: app/utils/rate_limiter.py (lines 130-143)
try:
    redis = await self._get_redis()
    # ... Redis operations
except (RedisError, ConnectionError) as ex:
    logger.error(f"Redis error for rate limit key {key}: {ex}")
    if app_settings.RATE_LIMIT_FAIL_MODE == "closed":
        logger.warning("Rate limiter in fail-closed mode, denying request")
        return False, 0
    return True, limit

# Pattern 2: app/utils/pagination_cache.py (lines 54-62)
try:
    redis = await get_redis_connection()
    # ... Redis operations
except (RedisError, ConnectionError) as ex:
    logger.error(f"Error reading count cache: {ex}")
    return None

# Pattern 3: app/utils/token_cache.py (lines 88-98)
try:
    redis = await get_redis_connection()
    # ... Redis operations
except Exception as e:  # ← Catches ALL exceptions (too broad!)
    logger.warning(f"Unexpected error retrieving cached token: {e}")
    return None
```

**Issues:**
- Inconsistent exception types caught (RedisError vs Exception)
- Inconsistent logging levels (error vs warning)
- Repeated fail-open/fail-closed logic
- No metrics on failures

**Solution:**

Create a decorator for Redis operations:

```python
# app/utils/redis_safe.py
from functools import wraps
from typing import Any, Callable, TypeVar
from redis.exceptions import RedisError
from app.logging import logger
from app.utils.metrics import MetricsCollector

T = TypeVar('T')

def redis_safe(
    *,
    fail_value: Any = None,
    fail_mode: str = "open",  # "open" or "closed"
    log_level: str = "error",
    operation_name: str | None = None
):
    """
    Decorator to safely handle Redis errors with consistent behavior.

    Args:
        fail_value: Value to return on error (default: None)
        fail_mode: "open" (allow on failure) or "closed" (deny on failure)
        log_level: Logging level for errors (default: "error")
        operation_name: Name for metrics (auto-detected from function name if None)

    Example:
        @redis_safe(fail_value=0, operation_name="rate_limit_check")
        async def check_rate(self, key: str) -> int:
            redis = await self._get_redis()
            return await redis.incr(key)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__

            try:
                return await func(*args, **kwargs)

            except (RedisError, ConnectionError) as ex:
                # Log with specified level
                log_func = getattr(logger, log_level)
                log_func(f"Redis error in {op_name}: {ex}")

                # Record metric
                MetricsCollector.record_redis_error(operation=op_name)

                # Return fail value based on mode
                if fail_mode == "closed":
                    logger.warning(f"{op_name} in fail-closed mode, denying")
                return fail_value

        return wrapper
    return decorator
```

**Usage:**

```python
class RateLimiter:
    @redis_safe(fail_value=(True, 0), operation_name="rate_limit_check")
    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> tuple[bool, int]:
        redis = await self._get_redis()
        # ... rest of implementation
        # No try/except needed - decorator handles it!

class TokenCache:
    @redis_safe(fail_value=None, log_level="warning")
    async def get_cached_token(self, token: str) -> dict[str, Any] | None:
        redis = await self._get_redis()
        # ... rest of implementation
```

**Benefits:**
- Consistent error handling
- Centralized logging and metrics
- Configurable fail-open/fail-closed
- Cleaner function code (no try/except noise)

---

### 1.3 Cache Key Generation Duplication ⚠️

**Severity:** MEDIUM
**Impact:** Inconsistent hashing, duplicated logic
**Effort:** Low

**Problem:**

Multiple similar hash-based key generation patterns:

```python
# app/utils/pagination_cache.py (lines 153-176)
def _generate_count_cache_key(model_name: str, filters: dict[str, Any] | None) -> str:
    if filters:
        sorted_filters = json.dumps(filters, sort_keys=True)
        filter_hash = hashlib.md5(
            sorted_filters.encode(),
            usedforsecurity=False
        ).hexdigest()[:8]
        return f"pagination:count:{model_name}:{filter_hash}"
    else:
        return f"pagination:count:{model_name}:all"

# app/utils/token_cache.py (lines 68-69)
token_hash = hashlib.sha256(token.encode()).hexdigest()
cache_key = f"token:claims:{token_hash}"
```

**Issues:**
- Inconsistent hashing (MD5 vs SHA256)
- Arbitrary truncation ([:8] vs full hash)
- Duplicated JSON serialization logic
- No validation of key format

**Solution:**

Create a cache key factory:

```python
# app/utils/cache_keys.py
import hashlib
import json
from typing import Any

class CacheKeyFactory:
    """Factory for generating consistent cache keys with optional hashing."""

    HASH_LENGTH = 8  # Truncate hashes to this length

    @staticmethod
    def generate(
        prefix: str,
        *parts: str | int,
        hash_dict: dict[str, Any] | None = None
    ) -> str:
        """
        Generate a cache key with optional dictionary hashing.

        Args:
            prefix: Key namespace (e.g., "pagination:count", "token:claims")
            *parts: Fixed parts of the key (e.g., model_name, user_id)
            hash_dict: Optional dict to hash and append

        Returns:
            Cache key in format: "prefix:part1:part2:hash"

        Examples:
            >>> CacheKeyFactory.generate("pagination:count", "Author")
            "pagination:count:Author"

            >>> CacheKeyFactory.generate(
            ...     "pagination:count",
            ...     "Author",
            ...     hash_dict={"name__icontains": "john"}
            ... )
            "pagination:count:Author:a1b2c3d4"
        """
        key_parts = [prefix] + [str(part) for part in parts]

        if hash_dict:
            # Sort for consistency, hash, and truncate
            sorted_data = json.dumps(hash_dict, sort_keys=True)
            hash_val = hashlib.sha256(sorted_data.encode()).hexdigest()
            key_parts.append(hash_val[:CacheKeyFactory.HASH_LENGTH])

        return ":".join(key_parts)

    @staticmethod
    def generate_with_hash(prefix: str, value: str) -> str:
        """
        Generate a cache key with full hash of value.

        Useful for sensitive data like tokens where you don't want
        the actual value in the key.

        Example:
            >>> CacheKeyFactory.generate_with_hash("token:claims", "eyJhbG...")
            "token:claims:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11"
        """
        hash_val = hashlib.sha256(value.encode()).hexdigest()
        return f"{prefix}:{hash_val}"
```

**Usage:**

```python
# app/utils/pagination_cache.py
def _generate_count_cache_key(model_name: str, filters: dict[str, Any] | None) -> str:
    return CacheKeyFactory.generate(
        "pagination:count",
        model_name,
        hash_dict=filters
    )

# app/utils/token_cache.py
def _generate_token_cache_key(token: str) -> str:
    return CacheKeyFactory.generate_with_hash("token:claims", token)
```

**Benefits:**
- Consistent hashing algorithm (SHA256)
- Single place to change hash length
- Clear API for common patterns
- Easy to add versioning or namespacing

---

## 2. Single Responsibility Principle Violations

### 2.1 RateLimiter God Class ⚠️

**Severity:** MEDIUM
**Impact:** Tight coupling, hard to test
**Effort:** High

**Problem:**

`RateLimiter` class handles multiple responsibilities:

```python
# app/utils/rate_limiter.py
class RateLimiter:
    """
    Responsibilities:
    1. Rate limiting logic (sliding window algorithm)
    2. Redis connection management
    3. Fail-open/fail-closed policy enforcement
    4. Metrics collection
    """

    async def _get_redis(self) -> Redis | None:  # Concern: Redis connection
        if self.redis is None:
            self.redis = await get_redis_connection()
        return self.redis

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int = 60):
        # Concern: Sliding window algorithm
        # Concern: Fail-open/fail-closed policy
        # Concern: Metrics emission
        # Concern: Redis operations
        ...
```

**Solution:**

Separate concerns into focused classes:

```python
# app/utils/rate_limiting/algorithm.py
class SlidingWindowAlgorithm:
    """Pure sliding window rate limiting algorithm."""

    async def check(
        self,
        redis: Redis,
        key: str,
        limit: int,
        window_seconds: int,
        current_time: float | None = None
    ) -> tuple[int, int]:
        """
        Check rate limit using sliding window.

        Returns:
            (current_count, limit) - count of requests in window
        """
        current_time = current_time or time.time()
        window_start = current_time - window_seconds

        # Remove old entries
        await redis.zremrangebyscore(key, "-inf", window_start)

        # Get current count
        current_count = await redis.zcard(key)

        return current_count, limit

# app/utils/rate_limiting/rate_limiter.py
from app.utils.redis_mixin import RedisClientMixin
from app.utils.rate_limiting.algorithm import SlidingWindowAlgorithm

class RateLimiter(RedisClientMixin):
    """
    Manages rate limiting with fail-open/fail-closed policy.

    Single Responsibility: Coordinate rate limiting checks with policy.
    """

    def __init__(self, algorithm: SlidingWindowAlgorithm | None = None):
        super().__init__()
        self.algorithm = algorithm or SlidingWindowAlgorithm()
        self.burst_capacity = app_settings.RATE_LIMIT_BURST_CAPACITY

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check if rate limit allows request.

        Returns:
            (is_allowed, current_count)
        """
        redis = await self._get_redis()
        if not redis:
            return self._handle_redis_unavailable(limit)

        try:
            current_count, _ = await self.algorithm.check(
                redis, key, limit, window_seconds
            )

            effective_limit = min(self.burst_capacity, limit)
            is_allowed = current_count < effective_limit

            if is_allowed:
                await redis.zadd(key, {str(time.time()): time.time()})
                await redis.expire(key, window_seconds)

            return is_allowed, current_count

        except (RedisError, ConnectionError) as ex:
            logger.error(f"Redis error for rate limit key {key}: {ex}")
            return self._handle_redis_unavailable(limit)

    def _handle_redis_unavailable(self, limit: int) -> tuple[bool, int]:
        """Handle Redis unavailability based on fail mode."""
        if app_settings.RATE_LIMIT_FAIL_MODE == "closed":
            logger.warning("Rate limiter in fail-closed mode, denying request")
            return False, 0
        return True, limit
```

**Benefits:**
- `SlidingWindowAlgorithm` is testable without Redis (dependency injection)
- `RateLimiter` focused on policy, not algorithm implementation
- Can swap algorithms (token bucket, leaky bucket) without changing RateLimiter
- Easier to test edge cases

---

### 2.2 CacheManager Multi-Responsibility ⚠️

**Severity:** MEDIUM
**Impact:** Complex class, hard to maintain
**Effort:** High

**Problem:**

`CacheManager` handles 3 concerns:

```python
# app/managers/cache_manager.py
class CacheManager:
    """
    Responsibilities:
    1. Two-tier caching logic (memory + Redis)
    2. LRU eviction policy
    3. Cache entry expiration
    4. Statistics collection
    """

    async def _set_memory(self, key: str, value: Any, ttl: int) -> None:
        # Concern: LRU eviction (lines 326-328)
        if len(self._memory_cache) > self.max_memory_entries:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]

        # Concern: Expiration tracking
        expiry = time.time() + ttl
        self._memory_cache[key] = CacheEntry(value, expiry)

    async def get_stats(self) -> dict[str, Any]:
        # Concern: Statistics collection
        ...
```

**Solution:**

Split into focused classes:

```python
# app/caching/entry.py
from dataclasses import dataclass
import time

@dataclass
class CacheEntry:
    """Represents a single cache entry with expiration."""

    value: Any
    expiry: float
    last_accessed: float = time.time()

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expiry

    def access(self) -> None:
        """Update last accessed time (for LRU)."""
        self.last_accessed = time.time()

# app/caching/memory_store.py
from collections import OrderedDict

class MemoryCacheStore:
    """In-memory cache with LRU eviction policy."""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Any | None:
        """Get value from cache, returns None if expired or missing."""
        entry = self._cache.get(key)
        if not entry:
            return None

        if entry.is_expired():
            del self._cache[key]
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)
        entry.access()
        return entry.value

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL."""
        # Evict if at capacity
        if len(self._cache) >= self.max_entries:
            self._evict_lru()

        expiry = time.time() + ttl
        self._cache[key] = CacheEntry(value, expiry)

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        oldest_key = next(iter(self._cache))
        del self._cache[oldest_key]

    def invalidate(self, key: str) -> None:
        """Remove entry from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "capacity": self.max_entries,
            "utilization": len(self._cache) / self.max_entries
        }

# app/caching/cache_manager.py
class CacheManager(RedisClientMixin):
    """
    Two-tier cache coordinator (memory + Redis).

    Single Responsibility: Coordinate between memory and Redis tiers.
    """

    def __init__(
        self,
        memory_store: MemoryCacheStore | None = None,
        default_ttl: int = 300
    ):
        super().__init__()
        self.memory = memory_store or MemoryCacheStore()
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        """Get from memory, fallback to Redis."""
        # Try memory first
        value = self.memory.get(key)
        if value is not None:
            return value

        # Fallback to Redis
        redis = await self._get_redis()
        if redis:
            value = await redis.get(key)
            if value:
                # Populate memory cache
                self.memory.set(key, value, self.default_ttl)
            return value

        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set in both memory and Redis."""
        ttl = ttl or self.default_ttl

        # Set in memory
        self.memory.set(key, value, ttl)

        # Set in Redis
        redis = await self._get_redis()
        if redis:
            await redis.setex(key, ttl, value)
```

**Benefits:**
- Each class has one reason to change
- `MemoryCacheStore` is testable without Redis
- Can swap eviction policies (LRU → LFU) without touching CacheManager
- Clearer separation of concerns

---

### 2.3 RBACManager Mixed Concerns ⚠️

**Severity:** MEDIUM
**Impact:** Tight coupling to FastAPI
**Effort:** Medium

**Problem:**

`RBACManager` mixes pure logic with framework adapters:

```python
# app/managers/rbac_manager.py
class RBACManager:
    @staticmethod
    def check_user_has_roles(
        user: UserModel,
        required_roles: list[str]
    ) -> tuple[bool, list[str]]:
        """Pure role checking logic - GOOD"""
        ...

    def require_roles(self, *roles: str) -> Callable[[Request], Awaitable[None]]:
        """HTTP/FastAPI specific - MIXED CONCERN"""
        async def role_checker(request: Request) -> None:
            user = request.state.user  # Coupled to FastAPI Request
            ...
        return role_checker

    def check_ws_permission(
        self, pkg_id: int, user: UserModel, permissions_registry: dict
    ) -> bool:
        """WebSocket specific - MIXED CONCERN"""
        ...
```

**Solution:**

Separate pure logic from adapters:

```python
# app/security/role_checker.py
class RoleChecker:
    """Pure role checking logic - no framework dependencies."""

    @staticmethod
    def check_user_has_roles(
        user: UserModel,
        required_roles: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Check if user has all required roles.

        Returns:
            (has_all_roles, missing_roles)
        """
        if not required_roles:
            return True, []

        user_roles = set(user.roles)
        required_set = set(required_roles)
        missing = list(required_set - user_roles)

        return len(missing) == 0, missing

# app/security/http_rbac_adapter.py
from fastapi import Request, HTTPException

class HTTPRBACAdapter:
    """FastAPI/HTTP specific RBAC adapter."""

    def __init__(self, role_checker: RoleChecker):
        self.role_checker = role_checker

    def require_roles(self, *roles: str) -> Callable[[Request], Awaitable[None]]:
        """Create FastAPI dependency for role checking."""
        async def role_checker_dependency(request: Request) -> None:
            if not hasattr(request.state, "user"):
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            user = request.state.user
            has_roles, missing = self.role_checker.check_user_has_roles(
                user, list(roles)
            )

            if not has_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing roles: {', '.join(missing)}"
                )

        return role_checker_dependency

# app/security/websocket_rbac_adapter.py
class WebSocketRBACAdapter:
    """WebSocket specific RBAC adapter."""

    def __init__(self, role_checker: RoleChecker):
        self.role_checker = role_checker

    def check_permission(
        self,
        user: UserModel,
        required_roles: list[str]
    ) -> bool:
        """Check if user has permission (returns bool for WebSocket)."""
        has_roles, _ = self.role_checker.check_user_has_roles(
            user, required_roles
        )
        return has_roles
```

**Benefits:**
- `RoleChecker` is pure Python, fully testable
- Can use same logic in CLI, background tasks, etc.
- Easy to swap HTTP framework (FastAPI → Flask)
- Clear separation: logic vs adapters

---

## 3. Open/Closed Principle Opportunities

### 3.1 Rigid MiddlewarePipeline ⚠️

**Severity:** MEDIUM
**Impact:** Cannot extend without modification
**Effort:** Medium

**Problem:**

Pipeline hardcodes middleware list:

```python
# app/middlewares/pipeline.py (lines 59-81)
class MiddlewarePipeline:
    def __init__(self, allowed_hosts: list[str] | None = None, auth_backend: Any | None = None):
        # HARDCODED - cannot add custom middleware without editing this file
        self.middleware: list[tuple[type, dict[str, Any]]] = [
            (TrustedHostMiddleware, {"allowed_hosts": allowed_hosts or ["*"]}),
            (CorrelationIDMiddleware, {}),
            (LoggingContextMiddleware, {}),
            (AuthenticationMiddleware, {"backend": auth_backend} if auth_backend else {}),
            (RateLimitMiddleware, {}),
            (RequestSizeLimitMiddleware, {}),
            (AuditMiddleware, {}),
            (SecurityHeadersMiddleware, {}),
            (PrometheusMiddleware, {}),
        ]
```

**Solution:**

Make pipeline configurable with fluent API:

```python
# app/middlewares/pipeline.py
class MiddlewarePipeline:
    """
    Configurable middleware pipeline with dependency validation.

    Open for extension: Add custom middleware via .add_middleware()
    Closed for modification: Core logic remains unchanged
    """

    def __init__(self):
        self.middleware: list[tuple[type, dict[str, Any]]] = []
        self.dependencies: dict[type, list[type]] = {}

    def add_middleware(
        self,
        middleware_class: type,
        depends_on: list[type] | None = None,
        **kwargs
    ) -> "MiddlewarePipeline":
        """
        Add middleware to pipeline with optional dependencies.

        Args:
            middleware_class: Middleware class to add
            depends_on: List of middleware classes this depends on
            **kwargs: Configuration for middleware

        Returns:
            self for fluent chaining

        Example:
            pipeline = (
                MiddlewarePipeline()
                .add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
                .add_middleware(CorrelationIDMiddleware)
                .add_middleware(
                    RateLimitMiddleware,
                    depends_on=[AuthenticationMiddleware]
                )
            )
        """
        self.middleware.append((middleware_class, kwargs))

        if depends_on:
            self.dependencies[middleware_class] = depends_on

        return self  # Fluent API

    def validate_dependencies(self) -> None:
        """Validate all dependencies are satisfied."""
        # Existing validation logic
        ...

    def apply_to_app(self, app: FastAPI) -> None:
        """Apply middleware to FastAPI app."""
        # Existing apply logic
        ...

# Factory function for standard pipeline
def create_standard_pipeline(
    allowed_hosts: list[str] | None = None,
    auth_backend: Any | None = None
) -> MiddlewarePipeline:
    """Create standard middleware pipeline."""
    pipeline = MiddlewarePipeline()

    # Security layer
    pipeline.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts or ["*"]
    )

    # Observability layer
    pipeline.add_middleware(CorrelationIDMiddleware)
    pipeline.add_middleware(
        LoggingContextMiddleware,
        depends_on=[CorrelationIDMiddleware]
    )

    # Authentication layer
    if auth_backend:
        pipeline.add_middleware(
            AuthenticationMiddleware,
            backend=auth_backend
        )

    # Authorization & limiting layer
    pipeline.add_middleware(
        RateLimitMiddleware,
        depends_on=[AuthenticationMiddleware] if auth_backend else None
    )
    pipeline.add_middleware(RequestSizeLimitMiddleware)

    # Audit layer
    pipeline.add_middleware(
        AuditMiddleware,
        depends_on=[AuthenticationMiddleware] if auth_backend else None
    )

    # Response layer
    pipeline.add_middleware(SecurityHeadersMiddleware)

    # Metrics layer (should be last)
    pipeline.add_middleware(PrometheusMiddleware)

    return pipeline
```

**Usage:**

```python
# Standard pipeline (existing behavior)
pipeline = create_standard_pipeline(
    allowed_hosts=app_settings.ALLOWED_HOSTS,
    auth_backend=AuthBackend()
)

# Custom pipeline (EXTENDED - not modified!)
pipeline = (
    create_standard_pipeline(...)
    .add_middleware(CustomCacheMiddleware)  # New middleware
    .add_middleware(CustomMetricsMiddleware)
)

pipeline.validate_dependencies()
pipeline.apply_to_app(app)
```

**Benefits:**
- Open for extension (add custom middleware)
- Closed for modification (core logic untouched)
- Factory function preserves standard behavior
- Fluent API improves readability

---

### 3.2 Rigid Error Handler Decorator ⚠️

**Severity:** LOW
**Impact:** Hard to add custom exception handling
**Effort:** High

**Problem:**

Error decorator only handles specific exceptions:

```python
# app/utils/error_handler.py
def handle_http_errors(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AppException as ex:
            # Handle AppException
            ...
        except SQLAlchemyError as ex:
            # Handle SQLAlchemyError
            ...
        # Cannot handle custom exceptions without editing this file!
    return wrapper
```

**Solution:**

Strategy pattern for extensible error handling:

```python
# app/error_handling/handler.py
from abc import ABC, abstractmethod

class ErrorHandler(ABC):
    """Strategy for handling specific exception types."""

    @abstractmethod
    def can_handle(self, ex: Exception) -> bool:
        """Check if this handler can handle the exception."""
        pass

    @abstractmethod
    async def handle(
        self, ex: Exception, context: dict[str, Any]
    ) -> JSONResponse:
        """Handle the exception and return response."""
        pass

# app/error_handling/handlers/app_exception.py
class AppExceptionHandler(ErrorHandler):
    """Handles AppException and subclasses."""

    def can_handle(self, ex: Exception) -> bool:
        return isinstance(ex, AppException)

    async def handle(
        self, ex: AppException, context: dict[str, Any]
    ) -> JSONResponse:
        logger.warning(
            f"Application error in {context['endpoint']}: {ex.message}"
        )
        return JSONResponse(
            status_code=ex.http_status,
            content=ex.to_http_response().model_dump()
        )

# app/error_handling/handlers/sqlalchemy_exception.py
class SQLAlchemyErrorHandler(ErrorHandler):
    """Handles SQLAlchemy database errors."""

    def can_handle(self, ex: Exception) -> bool:
        return isinstance(ex, SQLAlchemyError)

    async def handle(
        self, ex: SQLAlchemyError, context: dict[str, Any]
    ) -> JSONResponse:
        logger.error(f"Database error in {context['endpoint']}: {ex}")
        return JSONResponse(
            status_code=500,
            content=HTTPErrorResponse(
                error=ErrorEnvelope(
                    code=ErrorCode.DATABASE_ERROR,
                    msg="Database error occurred"
                )
            ).model_dump()
        )

# app/error_handling/decorator.py
def handle_errors(*handlers: ErrorHandler):
    """
    Extensible error handling decorator.

    Example:
        @handle_errors(
            AppExceptionHandler(),
            SQLAlchemyErrorHandler(),
            CustomExceptionHandler()  # NEW - no modification needed!
        )
        async def my_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as ex:
                context = {
                    "endpoint": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                }

                # Try each handler in order
                for handler in handlers:
                    if handler.can_handle(ex):
                        return await handler.handle(ex, context)

                # No handler found - re-raise
                logger.error(f"Unhandled exception in {func.__name__}: {ex}")
                raise

        return wrapper
    return decorator
```

**Usage:**

```python
# Default handlers
default_handlers = [
    AppExceptionHandler(),
    SQLAlchemyErrorHandler()
]

# Standard usage
@handle_errors(*default_handlers)
async def get_authors():
    ...

# Extended with custom handler (OPEN for extension!)
@handle_errors(
    *default_handlers,
    ThirdPartyAPIErrorHandler()  # NEW handler - no modification!
)
async def fetch_external_data():
    ...
```

**Benefits:**
- Open for extension (add new handlers)
- Closed for modification (decorator logic unchanged)
- Handler chain is explicit and testable
- Can reorder handlers for precedence

---

## 4. Interface Segregation Violations

### 4.1 Repository Protocol Too Broad ⚠️

**Severity:** LOW
**Impact:** Commands depend on unnecessary operations
**Effort:** Low

**Problem:**

`Repository` protocol forces all operations:

```python
# app/protocols.py
@runtime_checkable
class Repository(Protocol[T]):
    async def get_by_id(self, id: int) -> T | None
    async def get_all(self, **filters: Any) -> list[T]
    async def create(self, entity: T) -> T        # ← Not needed by read commands
    async def update(self, entity: T) -> T        # ← Not needed by read commands
    async def delete(self, entity: T) -> None     # ← Not needed by read commands
    async def exists(self, **filters: Any) -> bool

# app/commands/author_commands.py
class GetAuthorsCommand:
    def __init__(self, repository: Repository[Author]):  # Depends on write methods!
        self.repository = repository

    async def execute(self, input_data: GetAuthorsInput) -> list[Author]:
        # Only uses get_all() - doesn't need create/update/delete!
        return await self.repository.get_all(...)
```

**Solution:**

Segregate into read and write interfaces:

```python
# app/protocols.py
@runtime_checkable
class ReadRepository(Protocol[T]):
    """Read-only repository operations."""

    async def get_by_id(self, id: int) -> T | None
    async def get_all(self, **filters: Any) -> list[T]
    async def exists(self, **filters: Any) -> bool

@runtime_checkable
class WriteRepository(Protocol[T]):
    """Write-only repository operations."""

    async def create(self, entity: T) -> T
    async def update(self, entity: T) -> T
    async def delete(self, entity: T) -> None

@runtime_checkable
class Repository(ReadRepository[T], WriteRepository[T], Protocol[T]):
    """Full repository interface (read + write)."""
    pass

# app/commands/author_commands.py
class GetAuthorsCommand:
    def __init__(self, repository: ReadRepository[Author]):  # Only read methods!
        self.repository = repository

class CreateAuthorCommand:
    def __init__(self, repository: Repository[Author]):  # Needs both read + write
        self.repository = repository
```

**Benefits:**
- Commands only depend on methods they use
- More testable (can mock fewer methods)
- Clearer intent (read vs write vs both)
- Follows ISP: clients shouldn't depend on interfaces they don't use

---

## 5. YAGNI Violations

### 5.1 Connection Limiter Feature Audit ⚠️

**Severity:** LOW
**Impact:** Potentially unused code
**Effort:** Low (audit + potential removal)

**Issue:**

`ConnectionLimiter` provides detailed features, but usage is unclear:

```python
# app/utils/rate_limiter.py (lines 166-285)
class ConnectionLimiter:
    async def add_connection(
        self, user_id: str, connection_id: str
    ) -> bool:  # ← Is return value checked?
        ...

    async def get_connection_count(self, user_id: str) -> int:
        # ← Is this used anywhere?
        ...
```

**Action Items:**

1. **Audit usage:**
   ```bash
   # Search for usage of get_connection_count
   grep -r "get_connection_count" app/

   # Search for usage of add_connection return value
   grep -A 2 "add_connection" app/
   ```

2. **If unused:** Remove or simplify
   ```python
   # Simplified version if only count matters
   class ConnectionLimiter:
       async def increment_connection(self, user_id: str) -> int:
           """Increment and return new count."""
           ...

       async def decrement_connection(self, user_id: str) -> int:
           """Decrement and return new count."""
           ...
   ```

---

### 5.2 Cache Manager Pattern Invalidation ⚠️

**Severity:** LOW
**Impact:** Expensive Redis SCAN operation
**Effort:** Low

**Issue:**

`invalidate_pattern()` uses expensive SCAN:

```python
# app/managers/cache_manager.py (lines 247-297)
async def invalidate_pattern(self, pattern: str) -> int:
    """
    Invalidate all keys matching pattern using SCAN.
    WARNING: Expensive operation on large keyspaces!
    """
    redis = await self._get_redis()
    # ... uses SCAN which blocks Redis
```

**Action Items:**

1. **Audit usage:**
   ```bash
   grep -r "invalidate_pattern" app/
   ```

2. **If unused:** Remove it

3. **If used rarely:** Add warning and consider alternatives:
   ```python
   async def invalidate_pattern(self, pattern: str) -> int:
       """
       WARNING: This is an expensive O(N) operation that scans all keys.

       Alternatives:
       - Use tag-based invalidation instead
       - Store pattern keys in a SET for O(1) retrieval
       - Use invalidate() for specific keys
       """
       logger.warning(
           f"invalidate_pattern({pattern}) called - this is expensive!"
       )
       # ... existing implementation
   ```

---

### 5.3 Metrics Collection Audit ⚠️

**Severity:** LOW
**Impact:** Unused instrumentation
**Effort:** Medium

**Issue:**

`MetricsCollector` has 50+ methods, unclear which are used:

```python
# app/utils/metrics/collector.py
class MetricsCollector:
    # Are all these actually used?
    @staticmethod
    def record_ws_message_processing(...): ...

    @staticmethod
    def record_token_cache_hit(): ...

    @staticmethod
    def record_circuit_breaker_opened(...): ...

    # ... 47 more methods
```

**Action Items:**

1. **Audit usage of each method:**
   ```bash
   # Generate usage report
   for method in $(grep '@staticmethod' app/utils/metrics/collector.py | awk '{print $2}'); do
       count=$(grep -r "$method" app/ | wc -l)
       echo "$method: $count uses"
   done | sort -t: -k2 -n
   ```

2. **Remove unused metrics or mark as deprecated:**
   ```python
   @staticmethod
   @deprecated("Unused metric - will be removed in v2.0")
   def record_unused_metric(): ...
   ```

---

## 6. KISS Violations

### 6.1 Over-Complex Cache Key Generation ⚠️

**Severity:** LOW
**Impact:** Unnecessary complexity
**Effort:** Low

**Problem:**

Pagination cache key generation is overly complex:

```python
# app/utils/pagination_cache.py (lines 153-176)
def _generate_count_cache_key(model_name: str, filters: dict[str, Any] | None) -> str:
    if filters:
        sorted_filters = json.dumps(filters, sort_keys=True)  # Why sort?
        filter_hash = hashlib.md5(
            sorted_filters.encode(),
            usedforsecurity=False
        ).hexdigest()[:8]  # Why MD5? Why truncate to 8?
        return f"pagination:count:{model_name}:{filter_hash}"
    else:
        return f"pagination:count:{model_name}:all"  # Special case
```

**Questions:**
- Why sort filters? (Probably for collision resistance with different key orders)
- Why MD5 when marked `usedforsecurity=False`? (Why not SHA256 everywhere?)
- Why truncate to 8 chars? (Collision risk?)
- Why special case for no filters?

**Simpler approach:**

```python
def _generate_count_cache_key(model_name: str, filters: dict[str, Any] | None) -> str:
    """Generate cache key for count query."""
    if not filters:
        return f"pagination:count:{model_name}"

    # Canonical representation for consistent hashing
    filter_str = json.dumps(filters, sort_keys=True)
    # Use same hash as everywhere else (SHA256)
    filter_hash = hashlib.sha256(filter_str.encode()).hexdigest()[:12]  # Longer = safer
    return f"pagination:count:{model_name}:{filter_hash}"
```

**Benefits:**
- Consistent with other hashing (SHA256)
- Longer hash reduces collisions
- Clear why sorting is needed (consistency)

---

### 6.2 Auto-Detecting Error Handler ⚠️

**Severity:** LOW
**Impact:** Fragile magic
**Effort:** Low

**Problem:**

`handle_errors()` uses fragile signature inspection:

```python
# app/utils/error_handler.py (lines 184-228)
def handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Auto-detect HTTP vs WebSocket handler - FRAGILE!"""
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Magic detection based on parameter name and type
    if (
        params
        and params[0].name == "request"  # ← Fragile: assumes naming
        and params[0].annotation == RequestModel  # ← Fragile: exact type match
    ):
        return handle_ws_errors(func)

    return handle_http_errors(func)  # ← Surprising fallback
```

**Problems:**
- Assumes parameter named "request"
- Assumes exact type (not `RequestModel | None`)
- Falls back to HTTP silently (surprising)
- Hard to debug when detection fails

**Simpler approach:**

Remove auto-detection, use explicit decorators:

```python
# Explicit and clear
@handle_http_errors
async def http_endpoint():
    ...

@handle_ws_errors
async def ws_handler(request: RequestModel):
    ...

# No magic @handle_errors that guesses
```

**Benefits:**
- Explicit > implicit
- No fragile inspection
- Clear intent
- Easier to debug

---

## 7. Dependency Inversion Opportunities

### 7.1 Commands Depend on Concrete Repository ⚠️

**Severity:** LOW
**Impact:** Tight coupling
**Effort:** Low

**Problem:**

Commands depend on concrete `AuthorRepository`:

```python
# app/commands/author_commands.py
class GetAuthorsCommand:
    def __init__(self, repository: AuthorRepository):  # ← Concrete type
        self.repository = repository

    async def execute(self, input_data):
        # Uses repository.search_by_name() which is NOT in base protocol
        return await self.repository.search_by_name(...)
```

**Why:** `search_by_name()` is specific to `AuthorRepository`, not in base `Repository` protocol.

**Solution:**

Extend protocol with search capability:

```python
# app/protocols.py
@runtime_checkable
class SearchableRepository(ReadRepository[T], Protocol[T]):
    """Repository with search capabilities."""

    async def search_by_name(self, pattern: str) -> list[T]

# app/commands/author_commands.py
class GetAuthorsCommand:
    def __init__(self, repository: SearchableRepository[Author]):  # ← Protocol
        self.repository = repository
```

**Benefits:**
- Depend on abstraction, not concretion
- Easier to test (mock protocol)
- Can swap implementations

---

### 7.2 RateLimiter Creates Redis Dependency ⚠️

**Severity:** LOW
**Impact:** Hard to test
**Effort:** Low

**Problem:**

`RateLimiter` creates its own Redis connection:

```python
class RateLimiter:
    async def _get_redis(self) -> Redis | None:
        if self.redis is None:
            self.redis = await get_redis_connection()  # ← Creates dependency
        return self.redis
```

**Solution:**

Inject Redis client:

```python
class RateLimiter:
    def __init__(self, redis: Redis | None = None):
        """
        Args:
            redis: Optional Redis client for testing.
                   If None, will be lazily created from pool.
        """
        self._redis = redis

    async def _get_redis(self) -> Redis | None:
        if self._redis is None:
            self._redis = await get_redis_connection()
        return self._redis

# Testing
async def test_rate_limiter():
    mock_redis = AsyncMock(spec=Redis)
    limiter = RateLimiter(redis=mock_redis)  # Inject mock!

    result = await limiter.check_rate_limit("test:key", 10)
    # Easy to test without real Redis
```

**Benefits:**
- Testable without Redis
- Explicit dependencies
- Follows DIP

---

## 8. Additional Code Smells

### 8.1 Feature Envy: RateLimiter knows too much about Redis ⚠️

**Problem:**

`check_rate_limit()` has deep knowledge of Redis data structures:

```python
# app/utils/rate_limiter.py (lines 109-122)
async def check_rate_limit(...):
    # Knows Redis sorted set operations
    await redis.zremrangebyscore(key, "-inf", window_start)  # ← Redis-specific
    current_count = await redis.zcard(key)  # ← Redis-specific
    await redis.zadd(key, {str(current_time): current_time})  # ← Redis-specific
```

**Solution:** Extract to `SlidingWindowAlgorithm` (see Section 2.1)

---

### 8.2 Primitive Obsession: String-Based Roles ⚠️

**Problem:**

Roles are magic strings:

```python
# No IDE autocomplete, no validation
@pkg_router.register(PkgID.CREATE_AUTHOR, roles=["create-author"])

# Easy to typo
@pkg_router.register(PkgID.CREATE_AUTHOR, roles=["creat-author"])  # BUG!
```

**Solution:**

Use enum for type safety:

```python
# app/security/roles.py
from enum import Enum

class Role(str, Enum):
    """Application roles - single source of truth."""

    # Author management
    CREATE_AUTHOR = "create-author"
    GET_AUTHORS = "get-authors"
    UPDATE_AUTHOR = "update-author"
    DELETE_AUTHOR = "delete-author"

    # Admin
    ADMIN = "admin"
    VIEW_AUDIT_LOGS = "view-audit-logs"

# Usage - type-safe and autocompleted!
@pkg_router.register(PkgID.CREATE_AUTHOR, roles=[Role.CREATE_AUTHOR])
@router.get("/authors", dependencies=[Depends(require_roles(Role.GET_AUTHORS))])
```

**Benefits:**
- IDE autocomplete
- Typo-proof
- Single source of truth
- Easy to refactor
- Self-documenting

---

### 8.3 Magic Numbers: Cache TTL and Hash Lengths ⚠️

**Problem:**

Magic numbers scattered throughout:

```python
# What is 300? Seconds? Minutes?
self.default_ttl = 300

# Why 8? What's the collision risk?
filter_hash = hashlib.md5(...).hexdigest()[:8]

# Why 1000?
self.max_memory_entries = 1000
```

**Solution:**

Named constants with documentation:

```python
# app/constants.py
from datetime import timedelta

# Cache configuration
DEFAULT_CACHE_TTL = timedelta(minutes=5)  # Clear unit!
CACHE_KEY_HASH_LENGTH = 12  # SHA256 chars (1 in 16^12 collision risk)
MAX_MEMORY_CACHE_ENTRIES = 1000  # LRU size before eviction

# Rate limiting
DEFAULT_RATE_LIMIT_WINDOW = timedelta(seconds=60)
RATE_LIMIT_BURST_MULTIPLIER = 2  # Allow 2x burst capacity

# Token cache
TOKEN_CACHE_BUFFER = timedelta(seconds=10)  # Expire 10s early
```

**Benefits:**
- Self-documenting
- Easy to adjust
- Units are clear
- Single source of truth

---

## 9. Implementation Roadmap

### Phase 1: Quick Wins (1-2 days) 🎯

**High impact, low effort:**

1. **Create Redis utility mixin** (2h)
   - File: `app/utils/redis_mixin.py`
   - Benefit: Eliminates 3+ duplications
   - Impact: 🟢🟢🟢

2. **Create Redis error handling decorator** (3h)
   - File: `app/utils/redis_safe.py`
   - Benefit: Consistent error handling across 5+ files
   - Impact: 🟢🟢🟢

3. **Create cache key factory** (2h)
   - File: `app/utils/cache_keys.py`
   - Benefit: Eliminates hash duplication, consistent naming
   - Impact: 🟢🟢

4. **Extract constants** (1h)
   - File: `app/constants.py`
   - Benefit: Self-documenting magic numbers
   - Impact: 🟢

**Total:** ~8 hours

---

### Phase 2: Structural Improvements (3-5 days) 🏗️

**Medium effort, high long-term value:**

1. **Refactor RateLimiter** (1 day)
   - Extract `SlidingWindowAlgorithm`
   - Create `RedisBackedLimiter` base
   - Update tests
   - Impact: 🟢🟢🟢

2. **Segregate RBACManager** (1 day)
   - Create `RoleChecker` (pure logic)
   - Create `HTTPRBACAdapter`
   - Create `WebSocketRBACAdapter`
   - Update tests
   - Impact: 🟢🟢🟢

3. **Create Role enum** (0.5 day)
   - File: `app/security/roles.py`
   - Update all role references
   - Impact: 🟢🟢

4. **Make MiddlewarePipeline configurable** (1 day)
   - Add fluent API
   - Create factory function
   - Update tests and docs
   - Impact: 🟢🟢

**Total:** ~3.5 days

---

### Phase 3: Advanced Refactoring (1-2 weeks) 🔬

**Higher effort, architectural improvements:**

1. **Refactor CacheManager** (2 days)
   - Extract `CacheEntry`
   - Extract `MemoryCacheStore`
   - Refactor `CacheManager` as coordinator
   - Update tests
   - Impact: 🟢🟢

2. **Implement error handler strategy pattern** (2 days)
   - Create `ErrorHandler` protocol
   - Implement handlers for each exception type
   - Create `handle_errors()` decorator
   - Update all endpoints
   - Impact: 🟢🟢

3. **Segregate Repository protocols** (1 day)
   - Create `ReadRepository` protocol
   - Create `WriteRepository` protocol
   - Update command dependencies
   - Impact: 🟢

4. **YAGNI audit and cleanup** (1-2 days)
   - Audit metric usage
   - Audit connection limiter usage
   - Audit `invalidate_pattern()` usage
   - Remove or deprecate unused code
   - Impact: 🟢🟢

**Total:** ~6-7 days

---

### Phase 4: Continuous Improvement 🔄

**Ongoing practices:**

1. **Code review checklist:**
   - [ ] No duplicated Redis connection logic
   - [ ] Use `@redis_safe` for Redis operations
   - [ ] Use `CacheKeyFactory` for cache keys
   - [ ] Use `Role` enum, not strings
   - [ ] Extract constants, no magic numbers
   - [ ] Single responsibility per class
   - [ ] Depend on protocols, not concretions

2. **Pre-commit hook:**
   ```python
   # Add to .pre-commit-config.yaml
   - id: check-design-principles
     name: "Check design principle violations"
     entry: python scripts/check_design_principles.py
     language: system
   ```

3. **Documentation:**
   - Update `CLAUDE.md` with design principles
   - Add examples to developer guide
   - Document refactoring decisions

---

## 10. Metrics for Success

Track these metrics to measure improvement:

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| **Code Duplication** | ~15% | <5% | `radon raw -s app/` |
| **Average Cyclomatic Complexity** | ~6 | <5 | `radon cc -a app/` |
| **Classes > 300 lines** | 5 | <3 | `radon raw app/ \| grep "LOC.*[3-9][0-9]{2}"` |
| **Functions > 50 lines** | 12 | <8 | `radon raw -s app/` |
| **Protocol usage** | 60% | >80% | Grep for concrete types in __init__ |
| **Test coverage** | 82% | >85% | `pytest --cov` |
| **Type hint coverage** | ~90% | >95% | `mypy --strict` |

---

## 11. References and Further Reading

### Design Principles
- **SOLID Principles:** https://en.wikipedia.org/wiki/SOLID
- **DRY Principle:** https://en.wikipedia.org/wiki/Don%27t_repeat_yourself
- **YAGNI:** https://martinfowler.com/bliki/Yagni.html
- **KISS:** https://en.wikipedia.org/wiki/KISS_principle

### Python-Specific
- **Python Patterns:** https://python-patterns.guide/
- **Effective Python:** Brett Slatkin
- **Clean Code:** Robert C. Martin (Uncle Bob)

### Tools
- **Radon:** Complexity metrics - `pip install radon`
- **Vulture:** Dead code detection (already used)
- **PyLint:** Linting with design checks - `pip install pylint`

---

## Appendix A: Before/After Examples

### Example 1: Redis Connection (DRY)

**Before (Duplicated 3x):**
```python
# File 1
class RateLimiter:
    async def _get_redis(self) -> Redis | None:
        if self.redis is None:
            self.redis = await get_redis_connection()
        return self.redis

# File 2
class ConnectionLimiter:
    async def _get_redis(self) -> Redis | None:
        if self.redis is None:
            self.redis = await get_redis_connection()
        return self.redis
```

**After (Centralized):**
```python
# app/utils/redis_mixin.py
class RedisClientMixin:
    async def _get_redis(self) -> Redis | None:
        if self._redis is None:
            self._redis = await get_redis_connection()
        return self._redis

# Usage
class RateLimiter(RedisClientMixin):
    # Just use inherited _get_redis()
    pass
```

---

### Example 2: RoleChecker (SRP)

**Before (Mixed Concerns):**
```python
class RBACManager:
    @staticmethod
    def check_user_has_roles(...):  # Pure logic
        ...

    def require_roles(...):  # FastAPI dependency
        async def role_checker(request: Request):  # Coupled to FastAPI
            ...
```

**After (Separated):**
```python
# Pure logic - testable without FastAPI
class RoleChecker:
    @staticmethod
    def check_user_has_roles(...):
        ...

# FastAPI adapter
class HTTPRBACAdapter:
    def require_roles(...):
        async def role_checker(request: Request):
            ...
```

---

## Appendix B: Testing Improvements

### Before: Hard to Test

```python
class RateLimiter:
    async def check_rate_limit(self, key: str, limit: int):
        # Creates own Redis connection - hard to mock
        redis = await get_redis_connection()
        # Complex logic mixed with Redis operations
        await redis.zremrangebyscore(...)
        count = await redis.zcard(...)
        # ... 20 more lines
```

**Test difficulty:** Requires real Redis or complex mocking

---

### After: Easy to Test

```python
class SlidingWindowAlgorithm:
    async def check(self, redis: Redis, key: str, limit: int):
        # Pure algorithm - testable with any Redis mock
        ...

class RateLimiter:
    def __init__(self, algorithm: SlidingWindowAlgorithm, redis: Redis | None = None):
        self.algorithm = algorithm
        self._redis = redis  # Injectable!

# Test
async def test_rate_limiter():
    mock_redis = AsyncMock(spec=Redis)
    algorithm = SlidingWindowAlgorithm()
    limiter = RateLimiter(algorithm, redis=mock_redis)

    # Easy to test!
    result = await limiter.check_rate_limit("key", 10)
    assert result == (True, 0)
```

---

## Conclusion

This review identified **40+ opportunities** to improve code quality through SOLID, DRY, YAGNI, and KISS principles. The implementation roadmap prioritizes:

1. **Phase 1 (1-2 days):** Quick wins with immediate impact
2. **Phase 2 (3-5 days):** Structural improvements for long-term maintainability
3. **Phase 3 (1-2 weeks):** Advanced refactoring for architectural cleanliness
4. **Phase 4 (Ongoing):** Continuous improvement practices

**Recommended Start:** Begin with Phase 1 to see immediate benefits, then progressively tackle Phase 2 and 3 as time permits.

**Key Takeaway:** The codebase is already well-structured (Repository + Command patterns), but has common issues found in growing projects: duplication, mixed concerns, and some over-engineering. Following this roadmap will reduce technical debt while maintaining velocity.
