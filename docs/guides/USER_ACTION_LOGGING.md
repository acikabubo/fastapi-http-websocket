# User Action Logging

## Overview

User action logging (also known as audit logging) captures detailed records of user activities within the application. This is essential for:

- **Security & Compliance**: Track who did what and when for regulatory requirements (GDPR, HIPAA, SOX, etc.)
- **Debugging & Support**: Reproduce user issues and understand behavior patterns
- **Analytics**: Gain insights into feature usage and user workflows
- **Accountability**: Maintain a tamper-proof audit trail for sensitive operations

This guide provides recommendations for implementing user action logging in this FastAPI application with both HTTP and WebSocket handlers.

---

## What to Log

### Essential Information

Every action log should capture:

| Field | Description | Example |
|-------|-------------|---------|
| **Timestamp** | When the action occurred (UTC) | `2025-11-27T14:32:15.123456Z` |
| **User ID** | Unique identifier from Keycloak | `sub` field from JWT |
| **Username** | Human-readable username | `preferred_username` field |
| **Action Type** | HTTP method or WebSocket PkgID | `POST`, `GET`, `PkgID.GET_AUTHORS` |
| **Resource** | What was accessed/modified | `/api/authors/123`, `Author:123` |
| **Outcome** | Success or failure | `success`, `permission_denied`, `error` |
| **IP Address** | Client IP (with proxy awareness) | `192.168.1.100` |
| **User Agent** | Browser/client information | `Mozilla/5.0 ...` |

### Optional Contextual Data

Depending on compliance and debugging needs:

- **Request ID**: Correlation ID for tracing (`req_id` for WebSocket, generated for HTTP)
- **Request Payload**: Sanitized input data (remove passwords, tokens, PII)
- **Response Status**: HTTP status code or WebSocket `RSPCode`
- **Session ID**: Keycloak session identifier
- **User Roles**: Roles at time of action
- **Changes**: Before/after values for updates (careful with PII)
- **Duration**: Request processing time
- **Error Details**: Stack trace or error message for failures

### Sensitive Data Handling

⚠️ **Never log**:
- Passwords or password hashes
- Full credit card numbers
- Personal health information (unless required and encrypted)
- Full access tokens or API keys
- Social security numbers or national IDs

✅ **Sanitize before logging**:
- Mask email addresses: `u***r@example.com`
- Hash sensitive IDs: `sha256(user_id)[:16]`
- Redact fields: `{"password": "[REDACTED]"}`
- Truncate large payloads: `data[:1000] + "..."`

---

## Architecture Integration

### 1. Database Model (Recommended)

Create a dedicated `UserAction` model to persist logs in PostgreSQL.

**Advantages**:
- Queryable with SQL/SQLAlchemy
- ACID guarantees and transactional integrity
- Built-in PostgreSQL JSON support for flexible payloads
- Easy integration with existing database backup/restore

**app/models/user_action.py**:
```python
from datetime import datetime
from typing import Any

from sqlmodel import Column, DateTime, Field, JSON, SQLModel, Text


class UserAction(SQLModel, table=True):
    """
    Audit log for user actions across HTTP and WebSocket endpoints.

    Tracks who performed what action, when, and the outcome for security,
    compliance, and debugging purposes.
    """

    __tablename__ = "user_actions"

    id: int | None = Field(default=None, primary_key=True)

    # Temporal information
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="When the action occurred (UTC)"
    )

    # User identification (from Keycloak JWT)
    user_id: str = Field(index=True, description="Keycloak user ID (sub)")
    username: str = Field(
        index=True,
        description="Username (preferred_username)"
    )
    user_roles: list[str] = Field(
        default=[],
        sa_column=Column(JSON),
        description="User roles at time of action"
    )

    # Action details
    action_type: str = Field(
        index=True,
        description="HTTP method or WebSocket PkgID enum name"
    )
    resource: str = Field(
        index=True,
        description="Resource path or identifier"
    )
    endpoint: str = Field(
        description="Full endpoint path or WebSocket route"
    )

    # Request context
    request_id: str | None = Field(
        default=None,
        index=True,
        description="UUID for request correlation (WebSocket req_id)"
    )
    ip_address: str | None = Field(default=None, description="Client IP")
    user_agent: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Client user agent string"
    )

    # Request/Response data (sanitized)
    request_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Sanitized request data"
    )
    response_status: str = Field(
        index=True,
        description="HTTP status or RSPCode enum name"
    )

    # Outcome and errors
    outcome: str = Field(
        index=True,
        description="success, permission_denied, error, validation_error"
    )
    error_message: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Error details if outcome != success"
    )

    # Performance
    duration_ms: float | None = Field(
        default=None,
        description="Request processing time in milliseconds"
    )

    # Additional metadata
    metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional context (session_id, etc.)"
    )
```

### 2. Logging Middleware for HTTP

Implement middleware to automatically log all HTTP requests.

**app/middlewares/audit_log.py**:
```python
import time
from typing import Callable

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging import logger
from app.models.user_action import UserAction
from app.schemas.user import UserModel
from app.storage.db import get_session


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all authenticated HTTP requests to the database.

    Captures user actions including request details, response status,
    and processing time for audit and compliance purposes.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Log the HTTP request and response."""
        start_time = time.time()

        # Call the next middleware/endpoint
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Only log authenticated requests
        if hasattr(request, "user") and isinstance(
            request.user, UserModel
        ):
            try:
                await self._log_action(
                    request, response, duration_ms
                )
            except Exception as ex:
                # Never let logging break the request flow
                logger.error(f"Failed to log user action: {ex}")

        return response

    async def _log_action(
        self,
        request: Request,
        response: Response,
        duration_ms: float
    ):
        """Persist the user action to the database."""
        user: UserModel = request.user

        # Determine outcome from status code
        if response.status_code < 300:
            outcome = "success"
        elif response.status_code == 403:
            outcome = "permission_denied"
        elif response.status_code == 422:
            outcome = "validation_error"
        else:
            outcome = "error"

        # Get client IP (handle proxies)
        ip_address = request.client.host if request.client else None
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            ip_address = forwarded_for.split(",")[0].strip()

        action_log = UserAction(
            user_id=user.id,
            username=user.username,
            user_roles=user.roles,
            action_type=request.method,
            resource=request.url.path,
            endpoint=f"{request.method} {request.url.path}",
            ip_address=ip_address,
            user_agent=request.headers.get("User-Agent"),
            request_payload=await self._sanitize_payload(request),
            response_status=str(response.status_code),
            outcome=outcome,
            duration_ms=duration_ms,
        )

        async with get_session() as session:
            session.add(action_log)
            await session.commit()

    async def _sanitize_payload(
        self, request: Request
    ) -> dict | None:
        """
        Extract and sanitize request payload.

        Removes sensitive fields like passwords and tokens.
        """
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                payload = await request.json()

                # Redact sensitive fields
                sensitive_fields = {
                    "password", "token", "access_token",
                    "refresh_token", "secret", "api_key"
                }

                if isinstance(payload, dict):
                    sanitized = payload.copy()
                    for field in sensitive_fields:
                        if field in sanitized:
                            sanitized[field] = "[REDACTED]"
                    return sanitized

                return payload
        except Exception:
            # If we can't parse JSON, don't log payload
            return None

        return None
```

**Register middleware in `app/__init__.py`**:
```python
from app.middlewares.audit_log import AuditLogMiddleware

# Add after AuthenticationMiddleware but before PermAuthHTTPMiddleware
application.add_middleware(AuditLogMiddleware)
```

### 3. Logging in PackageRouter for WebSocket

Extend `PackageRouter.handle_request()` to log WebSocket actions.

**Modify `app/routing.py`**:
```python
async def handle_request(
    self, user: UserModel, request: RequestModel
) -> ResponseModel[dict[str, Any]]:
    """Handle incoming WebSocket request with audit logging."""
    import time
    from app.models.user_action import UserAction
    from app.storage.db import get_session

    start_time = time.time()
    response = None

    try:
        # Existing validation logic
        if not self._has_handler(request.pkg_id):
            response = ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"No handler found for pkg_id {request.pkg_id}",
                status_code=RSPCode.ERROR,
            )
            return response

        if not self._check_permission(request.pkg_id, user):
            response = ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"No permission for pkg_id {request.pkg_id}",
                status_code=RSPCode.PERMISSION_DENIED,
            )
            return response

        if validation_error := self._validate_request(request):
            response = validation_error
            return response

        handler = self.__get_handler(request.pkg_id)
        response = await handler(request)
        return response

    finally:
        # Log the action regardless of outcome
        duration_ms = (time.time() - start_time) * 1000

        try:
            await self._log_ws_action(
                user, request, response, duration_ms
            )
        except Exception as ex:
            logger.error(f"Failed to log WebSocket action: {ex}")

async def _log_ws_action(
    self,
    user: UserModel,
    request: RequestModel,
    response: ResponseModel | None,
    duration_ms: float
):
    """Log WebSocket action to database."""
    from app.models.user_action import UserAction
    from app.storage.db import get_session

    # Determine outcome
    if response is None:
        outcome = "error"
        response_status = "UNKNOWN"
    elif response.status_code == RSPCode.OK:
        outcome = "success"
        response_status = "OK"
    elif response.status_code == RSPCode.PERMISSION_DENIED:
        outcome = "permission_denied"
        response_status = "PERMISSION_DENIED"
    else:
        outcome = "error"
        response_status = response.status_code.name

    action_log = UserAction(
        user_id=user.id,
        username=user.username,
        user_roles=user.roles,
        action_type=request.pkg_id.name,  # e.g., "GET_AUTHORS"
        resource=f"PkgID.{request.pkg_id.name}",
        endpoint=f"WebSocket:/web/{request.pkg_id.name}",
        request_id=request.req_id,
        request_payload=self._sanitize_ws_payload(request.data),
        response_status=response_status,
        outcome=outcome,
        duration_ms=duration_ms,
    )

    async with get_session() as session:
        session.add(action_log)
        await session.commit()

def _sanitize_ws_payload(self, data: dict | None) -> dict | None:
    """Sanitize WebSocket request payload."""
    if not data:
        return None

    sanitized = data.copy()
    sensitive_fields = {
        "password", "token", "access_token", "secret"
    }

    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "[REDACTED]"

    return sanitized
```

### 4. Alternative: Decorator-Based Logging

For selective logging of specific handlers, use a decorator:

**app/decorators/audit.py**:
```python
from functools import wraps
from typing import Callable

from app.logging import logger
from app.models.user_action import UserAction
from app.storage.db import get_session


def audit_log(resource_name: str):
    """
    Decorator to log WebSocket handler execution.

    Usage:
        @audit_log(resource_name="authors")
        @pkg_router.register(PkgID.GET_AUTHORS)
        async def get_authors_handler(request: RequestModel):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            import time
            start_time = time.time()
            response = None

            try:
                response = await func(request, *args, **kwargs)
                return response
            finally:
                duration_ms = (time.time() - start_time) * 1000

                # Extract user from request state (if available)
                user = getattr(request, "user", None)
                if user:
                    try:
                        await _log_action(
                            user, request, response,
                            resource_name, duration_ms
                        )
                    except Exception as ex:
                        logger.error(f"Audit log failed: {ex}")

        return wrapper
    return decorator


async def _log_action(user, request, response, resource, duration):
    """Helper to persist audit log."""
    # Implementation similar to above
    pass
```

---

## Storage Options

### 1. PostgreSQL (Recommended)

**Pros**:
- ACID compliance for tamper-proof logs
- Rich querying with SQL and indexes
- Built-in JSON support for flexible metadata
- Integrated with existing database backup strategy
- Supports partitioning for large datasets

**Cons**:
- Can impact database performance under high load
- Requires careful index management

**Optimization Strategies**:
- Use async batch inserts for high-volume logging
- Partition table by month: `user_actions_2025_11`, `user_actions_2025_12`
- Create indexes on commonly queried fields: `user_id`, `timestamp`, `action_type`
- Archive old logs to separate tables or cold storage

### 2. Time-Series Database (ClickHouse, TimescaleDB)

**Pros**:
- Optimized for high-volume append-only logs
- Excellent query performance for time-range queries
- Built-in data retention policies

**Cons**:
- Additional infrastructure to manage
- Eventual consistency trade-offs

**Use When**: Logging >10k actions/minute

### 3. Structured Log Files (JSON Lines)

**Pros**:
- No database overhead
- Easy to ship to external systems (ELK, Splunk, Datadog)
- Good for compliance archiving

**Cons**:
- Difficult to query without external tools
- No transactional guarantees

**app/utils/file_logger.py**:
```python
import json
from datetime import datetime
from pathlib import Path

AUDIT_LOG_PATH = Path("logs/audit.jsonl")


async def log_to_file(action_data: dict):
    """Append action log to JSON Lines file."""
    action_data["timestamp"] = datetime.utcnow().isoformat()

    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with AUDIT_LOG_PATH.open("a") as f:
        f.write(json.dumps(action_data) + "\n")
```

### 4. External Services (Datadog, Splunk, CloudWatch)

**Pros**:
- Offloads infrastructure burden
- Rich analytics and alerting
- Compliance-ready retention policies

**Cons**:
- Cost scales with volume
- Network dependency
- Data leaves your infrastructure

**Integration**: Use async HTTP client to send logs to external API

---

## Privacy & Compliance

### GDPR Considerations

1. **Right to Access**: Users can request all their logged actions
   ```python
   # Example query
   actions = await session.exec(
       select(UserAction).where(UserAction.user_id == user_id)
   )
   ```

2. **Right to Erasure**: Pseudonymize or delete logs after retention period
   ```python
   # Pseudonymize after 90 days
   await session.exec(
       update(UserAction)
       .where(UserAction.timestamp < thirty_days_ago)
       .values(
           username="[DELETED]",
           ip_address="0.0.0.0",
           user_agent="[DELETED]"
       )
   )
   ```

3. **Purpose Limitation**: Document why each field is logged
4. **Data Minimization**: Only log what's necessary

### Retention Policies

Define clear retention based on compliance needs:

| Log Type | Retention | Rationale |
|----------|-----------|-----------|
| Authentication | 90 days | Security incident investigation |
| Financial transactions | 7 years | Tax compliance (SOX) |
| Health data access | 6 years | HIPAA requirements |
| General actions | 1 year | Operational debugging |

**Automated cleanup (scheduled task)**:
```python
from datetime import datetime, timedelta
from sqlmodel import delete, select

async def cleanup_old_logs():
    """Delete user actions older than retention period."""
    cutoff_date = datetime.utcnow() - timedelta(days=365)

    async with get_session() as session:
        await session.exec(
            delete(UserAction).where(
                UserAction.timestamp < cutoff_date
            )
        )
        await session.commit()
```

---

## Querying & Analysis

### Common Queries

**1. User activity timeline**:
```python
from sqlmodel import select

actions = await session.exec(
    select(UserAction)
    .where(UserAction.user_id == user_id)
    .order_by(UserAction.timestamp.desc())
    .limit(100)
)
```

**2. Failed authentication attempts**:
```python
failed_auths = await session.exec(
    select(UserAction)
    .where(
        UserAction.action_type == "POST",
        UserAction.endpoint.like("%/login%"),
        UserAction.outcome == "error"
    )
    .where(UserAction.timestamp > last_hour)
)
```

**3. Permission violations**:
```python
violations = await session.exec(
    select(UserAction)
    .where(UserAction.outcome == "permission_denied")
    .order_by(UserAction.timestamp.desc())
)
```

**4. Most accessed resources**:
```python
from sqlalchemy import func

popular_resources = await session.exec(
    select(
        UserAction.resource,
        func.count(UserAction.id).label("access_count")
    )
    .group_by(UserAction.resource)
    .order_by(func.count(UserAction.id).desc())
    .limit(10)
)
```

### Analytics Dashboard

Consider building endpoints for:
- User activity heatmaps
- Permission denial trends
- Slow endpoint detection (high `duration_ms`)
- Anomaly detection (unusual access patterns)

---

## Performance Considerations

### 1. Async Background Logging

Avoid blocking request handlers:

```python
import asyncio
from typing import Any

# Global queue for async logging
log_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


async def log_worker():
    """Background worker to process log queue."""
    while True:
        action_data = await log_queue.get()

        try:
            async with get_session() as session:
                action = UserAction(**action_data)
                session.add(action)
                await session.commit()
        except Exception as ex:
            logger.error(f"Failed to persist log: {ex}")
        finally:
            log_queue.task_done()


# In app startup
async def start_log_worker():
    """Start background log worker."""
    asyncio.create_task(log_worker())


# In middleware/router
await log_queue.put(action_data)
```

### 2. Batch Inserts

For high-volume scenarios:

```python
# Collect logs in batches of 100 or every 5 seconds
batch = []

async def flush_batch():
    if batch:
        async with get_session() as session:
            session.add_all([UserAction(**log) for log in batch])
            await session.commit()
        batch.clear()
```

### 3. Database Partitioning

Partition the `user_actions` table by month:

```sql
CREATE TABLE user_actions_2025_11 PARTITION OF user_actions
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE user_actions_2025_12 PARTITION OF user_actions
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

### 4. Sampling for High-Volume Endpoints

For non-critical actions, log only a percentage:

```python
import random

# Log only 10% of GET requests
if request.method == "GET" and random.random() > 0.1:
    return  # Skip logging
```

---

## Migration Guide

### Step 1: Create Database Model

Add `app/models/user_action.py` with the `UserAction` model.

### Step 2: Generate Migration

```bash
# Using Alembic (if configured)
alembic revision --autogenerate -m "Add user_actions table"
alembic upgrade head
```

### Step 3: Add Middleware

Create `app/middlewares/audit_log.py` and register in `app/__init__.py`.

### Step 4: Update PackageRouter

Add `_log_ws_action()` method to `app/routing.py`.

### Step 5: Configure Settings

Add to `app/settings.py`:
```python
class Settings(BaseSettings):
    # Audit logging
    ENABLE_AUDIT_LOGGING: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_LOG_SAMPLE_RATE: float = 1.0  # 1.0 = log everything
```

### Step 6: Test

Write tests to verify logging:
```python
async def test_audit_log_created(client, db_session):
    """Test that user actions are logged."""
    response = await client.get("/api/authors")

    logs = await db_session.exec(
        select(UserAction).where(
            UserAction.endpoint == "GET /api/authors"
        )
    )

    assert len(logs) == 1
    assert logs[0].outcome == "success"
```

---

## Summary

**Recommended Implementation**:

1. **Database Model**: Use `UserAction` SQLModel for structured, queryable logs
2. **HTTP Logging**: Implement `AuditLogMiddleware` for automatic logging
3. **WebSocket Logging**: Extend `PackageRouter.handle_request()` with `_log_ws_action()`
4. **Sanitization**: Always redact sensitive fields before logging
5. **Performance**: Use async background workers for high-volume scenarios
6. **Compliance**: Implement retention policies and pseudonymization

**Next Steps**:
- Define your retention policy based on compliance needs
- Determine which fields are mandatory vs. optional for your use case
- Set up monitoring/alerts for permission violations and errors
- Consider integrating with external log aggregation services

For questions or implementation assistance, refer to the code examples above or consult the team.
