# Middleware Guide

This guide documents the middleware pipeline architecture, execution order, dependencies, and how to add new middleware safely.

## Table of Contents

- [Overview](#overview)
- [Middleware Pipeline](#middleware-pipeline)
- [Execution Order](#execution-order)
- [Middleware Dependencies](#middleware-dependencies)
- [Adding New Middleware](#adding-new-middleware)
- [Troubleshooting](#troubleshooting)

## Overview

The application uses an explicit middleware pipeline (`MiddlewarePipeline`) that manages middleware registration, dependency validation, and provides visualization of the execution order.

**Key Features:**
- **Explicit Ordering**: Middleware are defined in logical execution order (not reversed)
- **Dependency Validation**: Automatic checking that dependencies are satisfied
- **Visualization**: Clear display of middleware execution flow
- **Type Safety**: Centralized configuration prevents ordering mistakes

**Location**: [`app/middlewares/pipeline.py`](../../app/middlewares/pipeline.py)

## Middleware Pipeline

### Architecture

The `MiddlewarePipeline` class handles the complexity of FastAPI/Starlette's reverse middleware registration:

```python
from app.middlewares.pipeline import MiddlewarePipeline
from app.auth import AuthBackend

# Create pipeline with configuration
pipeline = MiddlewarePipeline(
    allowed_hosts=["example.com", "api.example.com"],
    auth_backend=AuthBackend(),
)

# Validate dependencies before applying
pipeline.validate_dependencies()

# Apply to FastAPI app
pipeline.apply_to_app(app)

# Log execution order
logger.info(f"Middleware order: {pipeline.visualize()}")
```

### Why a Pipeline?

**Without Pipeline** (Old Approach):
```python
# Confusing: Registration order is REVERSED from execution order
app.add_middleware(PrometheusMiddleware)         # Executes LAST
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)
...
app.add_middleware(TrustedHostMiddleware, ...)   # Executes FIRST
```

**With Pipeline** (New Approach):
```python
# Clear: Define in logical execution order
self.middleware = [
    (TrustedHostMiddleware, ...),      # Executes FIRST
    (CorrelationIDMiddleware, ...),
    ...
    (PrometheusMiddleware, ...),       # Executes LAST
]
```

The pipeline handles the reversal internally when registering with FastAPI.

## Execution Order

Middleware execute in the following order for each request:

```
Request Flow (Incoming):
  1. TrustedHostMiddleware         ← Validates host headers
  2. CorrelationIDMiddleware       ← Generates correlation ID
  3. LoggingContextMiddleware      ← Sets logging context
  4. AuthenticationMiddleware      ← Identifies user
  5. RateLimitMiddleware           ← Checks rate limits
  6. RequestSizeLimitMiddleware    ← Validates request size
  7. AuditMiddleware               ← Logs request
  8. SecurityHeadersMiddleware     ← Adds security headers
  9. PrometheusMiddleware          ← Collects metrics
        ↓
    [Your Endpoint Handler]
        ↓
Response Flow (Outgoing):
  9. PrometheusMiddleware          ← Finalizes metrics
  8. SecurityHeadersMiddleware     ← Adds response headers
  7. AuditMiddleware               ← Logs response
  6. RequestSizeLimitMiddleware
  5. RateLimitMiddleware
  4. AuthenticationMiddleware
  3. LoggingContextMiddleware
  2. CorrelationIDMiddleware
  1. TrustedHostMiddleware
```

### Visualization

Get the current execution order programmatically:

```python
pipeline = MiddlewarePipeline()
print(pipeline.visualize())
# Output: TrustedHostMiddleware → CorrelationIDMiddleware → ... → PrometheusMiddleware
```

## Middleware Dependencies

Some middleware depend on others executing before them:

### Dependency Graph

```
TrustedHostMiddleware
    ↓
CorrelationIDMiddleware
    ↓
LoggingContextMiddleware (requires CorrelationIDMiddleware)
    ↓
AuthenticationMiddleware
    ↓
RateLimitMiddleware (requires AuthenticationMiddleware)
    ↓
RequestSizeLimitMiddleware
    ↓
AuditMiddleware (requires AuthenticationMiddleware)
    ↓
SecurityHeadersMiddleware
    ↓
PrometheusMiddleware
```

### Defined Dependencies

The pipeline validates these dependencies at startup:

| Middleware | Depends On | Reason |
|------------|------------|--------|
| `LoggingContextMiddleware` | `CorrelationIDMiddleware` | Needs correlation ID for log context |
| `RateLimitMiddleware` | `AuthenticationMiddleware` | Needs user context for per-user limits |
| `AuditMiddleware` | `AuthenticationMiddleware` | Needs user identity for audit logs |

### Validation

Dependencies are automatically validated when you call `validate_dependencies()`:

```python
pipeline = MiddlewarePipeline()
pipeline.validate_dependencies()  # Raises ValueError if invalid
```

**Example Error:**
```
ValueError: Middleware dependency violation:
RateLimitMiddleware requires AuthenticationMiddleware to execute before it,
but AuthenticationMiddleware is at position 5 and RateLimitMiddleware is at position 3
```

## Adding New Middleware

### Step 1: Create Middleware Class

```python
# app/middlewares/my_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class MyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        print("Before request")

        response = await call_next(request)

        # Post-processing
        print("After request")
        return response
```

### Step 2: Add to Pipeline

Edit [`app/middlewares/pipeline.py`](../../app/middlewares/pipeline.py):

```python
from app.middlewares.my_middleware import MyMiddleware

class MiddlewarePipeline:
    def __init__(self, ...):
        self.middleware = [
            (TrustedHostMiddleware, ...),
            (CorrelationIDMiddleware, ...),
            (MyMiddleware, {}),  # ← Add here in logical order
            ...
        ]
```

**Important**: Insert at the correct position based on:
1. What data does your middleware need? (depends on)
2. What data does your middleware provide? (depended on by)

### Step 3: Define Dependencies (if any)

If your middleware depends on others:

```python
self.dependencies = {
    MyMiddleware: [AuthenticationMiddleware, CorrelationIDMiddleware],
    ...
}
```

### Step 4: Test

```python
# tests/unit/middlewares/test_my_middleware.py
def test_my_middleware_in_pipeline():
    pipeline = MiddlewarePipeline()
    middleware_classes = [mw[0] for mw in pipeline.get_middleware_list()]

    assert MyMiddleware in middleware_classes

def test_my_middleware_dependencies():
    pipeline = MiddlewarePipeline()
    pipeline.validate_dependencies()  # Should pass
```

### Example: Adding Caching Middleware

```python
# Want to cache responses based on authenticated user
# Needs: AuthenticationMiddleware (for user context)
# Provides: Cached responses

self.middleware = [
    (TrustedHostMiddleware, ...),
    (CorrelationIDMiddleware, ...),
    (LoggingContextMiddleware, ...),
    (AuthenticationMiddleware, ...),    # ← CacheMiddleware depends on this
    (CacheMiddleware, {}),              # ← Insert after AuthenticationMiddleware
    (RateLimitMiddleware, ...),
    ...
]

self.dependencies = {
    CacheMiddleware: [AuthenticationMiddleware],  # ← Define dependency
    ...
}
```

## Troubleshooting

### Middleware Not Executing

**Symptom**: Your middleware's code doesn't run.

**Causes**:
1. Not added to pipeline
2. Added but not applied to app
3. Middleware class not imported

**Solution**:
```python
# 1. Check it's in the pipeline
pipeline = MiddlewarePipeline()
print(pipeline.visualize())  # Should see your middleware

# 2. Check it's applied
pipeline.apply_to_app(app)

# 3. Check import
from app.middlewares.my_middleware import MyMiddleware  # Must be imported
```

### Dependency Violation Error

**Symptom**: `ValueError: Middleware dependency violation`

**Cause**: A middleware that depends on another is executing before it.

**Solution**:
1. Check the error message for which middleware are out of order
2. Move the dependent middleware AFTER its dependency in the pipeline list
3. Run `validate_dependencies()` to verify

**Example Fix:**
```python
# Before (WRONG):
self.middleware = [
    ...
    (RateLimitMiddleware, {}),          # Needs auth!
    (AuthenticationMiddleware, ...),    # Comes after!
    ...
]

# After (CORRECT):
self.middleware = [
    ...
    (AuthenticationMiddleware, ...),    # Comes first
    (RateLimitMiddleware, {}),          # Uses auth context
    ...
]
```

### Middleware Executing in Wrong Order

**Symptom**: Middleware A should run before B, but B runs first.

**Cause**: FastAPI registers middleware in reverse order.

**Solution**: The pipeline handles this automatically. Just ensure your logical order in `self.middleware` is correct.

```python
# Logical order (what you define):
[A, B, C]

# Execution order (automatic):
A → B → C  ✓

# FastAPI registration order (handled internally):
[C, B, A]  (reversed)
```

### Missing User Context

**Symptom**: `request.user` is not available in your middleware.

**Cause**: Your middleware executes before `AuthenticationMiddleware`.

**Solution**:
1. Move your middleware AFTER `AuthenticationMiddleware` in the pipeline
2. Add dependency: `self.dependencies[YourMiddleware] = [AuthenticationMiddleware]`

### Rate Limiting Not Working

**Symptom**: Rate limits aren't enforced correctly.

**Cause**: `RateLimitMiddleware` is executing before `AuthenticationMiddleware`.

**Solution**: Verify the order:
```python
pipeline = MiddlewarePipeline()
print(pipeline.visualize())
# Should show: ... → AuthenticationMiddleware → RateLimitMiddleware → ...
```

### Correlation ID Missing

**Symptom**: Logs don't have correlation IDs.

**Cause**: `LoggingContextMiddleware` is executing before `CorrelationIDMiddleware`.

**Solution**: This is a defined dependency and should be caught by `validate_dependencies()`. If not, check that both middleware are in the pipeline and in the correct order.

## Best Practices

### 1. Always Validate Dependencies

```python
pipeline = MiddlewarePipeline()
pipeline.validate_dependencies()  # Catches ordering issues early
pipeline.apply_to_app(app)
```

### 2. Use Visualization for Debugging

```python
logger.info(f"Middleware pipeline: {pipeline.visualize()}")
# Logs: TrustedHostMiddleware → CorrelationIDMiddleware → ...
```

### 3. Document New Middleware Dependencies

When adding middleware with dependencies, document them:

```python
self.dependencies = {
    MyMiddleware: [RequiredMiddleware],  # MyMiddleware needs X from RequiredMiddleware
}
```

### 4. Test Middleware Integration

Always write tests that verify:
- Middleware is in the pipeline
- Dependencies are satisfied
- Execution order is correct

```python
def test_my_middleware_integration():
    pipeline = MiddlewarePipeline()

    # Verify it's in the pipeline
    middleware_classes = [mw[0] for mw in pipeline.get_middleware_list()]
    assert MyMiddleware in middleware_classes

    # Verify dependencies are satisfied
    pipeline.validate_dependencies()

    # Verify order
    visualization = pipeline.visualize()
    assert "RequiredMiddleware" in visualization
    assert visualization.index("RequiredMiddleware") < visualization.index("MyMiddleware")
```

### 5. Keep Middleware Focused

Each middleware should have a single responsibility:
- ✅ `AuthenticationMiddleware` - Only identifies the user
- ✅ `RateLimitMiddleware` - Only enforces rate limits
- ❌ `AuthAndRateLimitMiddleware` - Too much responsibility

## Reference

### MiddlewarePipeline API

```python
class MiddlewarePipeline:
    def __init__(
        self,
        allowed_hosts: list[str] | None = None,
        auth_backend: Any | None = None,
    ):
        """Initialize pipeline with configuration."""

    def validate_dependencies(self) -> None:
        """Validate middleware dependencies. Raises ValueError if invalid."""

    def apply_to_app(self, app: FastAPI) -> None:
        """Register middleware to FastAPI app."""

    def visualize(self) -> str:
        """Return visualization of execution order."""

    def get_middleware_list(self) -> list[tuple[type, dict[str, Any]]]:
        """Get middleware list as (MiddlewareClass, kwargs) tuples."""

    def get_middleware_count(self) -> int:
        """Get number of middleware in pipeline."""
```

### Current Middleware

| Middleware | Purpose | Dependencies | Position |
|------------|---------|--------------|----------|
| `TrustedHostMiddleware` | Validates host headers | None | 1 (First) |
| `CorrelationIDMiddleware` | Generates correlation ID | None | 2 |
| `LoggingContextMiddleware` | Sets logging context | `CorrelationIDMiddleware` | 3 |
| `AuthenticationMiddleware` | Identifies user | None | 4 |
| `RateLimitMiddleware` | Enforces rate limits | `AuthenticationMiddleware` | 5 |
| `RequestSizeLimitMiddleware` | Validates request size | None | 6 |
| `AuditMiddleware` | Logs requests/responses | `AuthenticationMiddleware` | 7 |
| `SecurityHeadersMiddleware` | Adds security headers | None | 8 |
| `PrometheusMiddleware` | Collects metrics | None | 9 (Last) |

## See Also

- [Architecture Guide](./architecture-guide.md) - Overall application architecture
- [Development Guide](./development-guide.md) - Development workflows
- [Testing Guide](./testing-guide.md) - Testing strategies
