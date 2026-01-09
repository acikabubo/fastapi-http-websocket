# User Action Logging and Audit Trail

This guide explains how to use and maintain the user action logging (audit logging) system in this FastAPI application.

## Overview

The audit logging system tracks user activities for security, compliance, debugging, and analytics purposes. It captures comprehensive information about user actions across both HTTP and WebSocket endpoints.

## Architecture

The system uses a **database-first approach** with the following components:

- **UserAction Model** (`app/models/user_action.py`): SQLModel storing audit records
- **AuditLogger** (`app/utils/audit_logger.py`): Utility functions for logging actions
- **AuditMiddleware** (`app/middlewares/audit_middleware.py`): HTTP request logging
- **WebSocket Integration**: Manual logging in WebSocket handlers

## What Gets Logged

### Essential Information

Every action log captures:

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | When the action occurred (UTC) | `2025-11-27T14:32:15.123456Z` |
| `user_id` | Keycloak user ID | `sub` field from JWT |
| `username` | Human-readable username | `preferred_username` |
| `user_roles` | Roles at time of action | `["admin", "user"]` |
| `action_type` | HTTP method or WebSocket PkgID | `POST`, `GET`, `PkgID.GET_AUTHORS` |
| `resource` | Resource accessed/modified | `/api/authors/123`, `Author:123` |
| `outcome` | Result of the action | `success`, `error`, `permission_denied` |
| `ip_address` | Client IP (proxy-aware) | `192.168.1.100` |
| `user_agent` | Browser/client info | `Mozilla/5.0 ...` |

### Optional Contextual Data

- `request_id`: Correlation ID for distributed tracing
- `request_data`: Sanitized request payload
- `response_status`: HTTP status code
- `error_message`: Error details for failures
- `duration_ms`: Request processing time

## Using the Audit Logger

### In HTTP Endpoints

HTTP requests are **automatically logged** by `AuditMiddleware`. No manual logging required for standard endpoints.

```python
from fastapi import APIRouter
from app.dependencies import AuthorRepoDep

router = APIRouter()

@router.post("/authors")
async def create_author(author: AuthorCreate, repo: AuthorRepoDep):
    # Middleware automatically logs this action
    return await repo.create(author)
```

### In WebSocket Handlers

WebSocket actions require **manual logging**:

```python
from app.utils.audit_logger import log_user_action
from app.api.ws.models import RequestModel, ResponseModel
from app.storage.db import async_session
from app.repositories.author_repository import AuthorRepository

@pkg_router.register(PkgID.CREATE_AUTHOR, json_schema=CreateAuthorSchema)
async def create_author_handler(request: RequestModel) -> ResponseModel:
    try:
        # Perform action using Repository pattern
        async with async_session() as session:
            repo = AuthorRepository(session)
            author = await repo.create(Author(**request.data))

        # Log successful action
        await log_user_action(
            user_id=request.user.id,
            username=request.user.username,
            user_roles=request.user.roles,
            action_type=f"WS:{request.pkg_id.name}",
            resource=f"Author:{author.id}",
            outcome="success",
            ip_address=request.ip_address,
            request_id=request.req_id,
            request_data=request.data,
            duration_ms=request.duration_ms
        )

        return ResponseModel.success(...)
    except Exception as e:
        # Log failed action
        await log_user_action(
            user_id=request.user.id,
            username=request.user.username,
            user_roles=request.user.roles,
            action_type=f"WS:{request.pkg_id.name}",
            resource="Author",
            outcome="error",
            error_message=str(e),
            ip_address=request.ip_address,
            request_id=request.req_id
        )
        raise
```

### Logging Permission Denials

RBAC permission denials are **automatically logged** by the middleware and WebSocket permission checks.

## Sensitive Data Handling

### Never Log

⚠️ **DO NOT log these fields**:
- Passwords or password hashes
- Full credit card numbers
- Personal health information (PHI)
- Full access tokens or API keys
- Social security numbers or national IDs
- Private encryption keys

### Data Sanitization

The `sanitize_data()` function automatically redacts sensitive fields:

```python
from app.utils.audit_logger import sanitize_data

data = {
    "username": "john",
    "password": "secret123",
    "email": "john@example.com",
    "token": "Bearer xyz..."
}

sanitized = sanitize_data(data)
# Result: {
#     "username": "john",
#     "password": "[REDACTED]",
#     "email": "john@example.com",
#     "token": "[REDACTED]"
# }
```

**Default redacted fields**:
- `password`, `passwd`, `pwd`
- `token`, `access_token`, `refresh_token`
- `secret`, `api_key`, `private_key`
- `ssn`, `social_security_number`
- `credit_card`, `card_number`, `cvv`

## Querying Audit Logs

### Using the API (Admin Only)

```bash
# Get audit logs with filters
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit-logs?page=1&per_page=20&user_id=abc123&outcome=error"

# Filter by date range
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit-logs?start_date=2025-01-01&end_date=2025-01-31"

# Filter by action type
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit-logs?action_type=POST"
```

### Direct Database Queries

```python
from sqlmodel import select
from app.models.user_action import UserAction
from app.storage.db import async_session

# Get all actions by a user in date range
async with async_session() as session:
    stmt = (
        select(UserAction)
        .where(UserAction.user_id == "user123")
        .where(UserAction.timestamp >= start_date)
        .where(UserAction.timestamp <= end_date)
        .order_by(UserAction.timestamp.desc())
    )
    actions = (await session.exec(stmt)).all()

# Get failed login attempts
async with async_session() as session:
    stmt = (
        select(UserAction)
        .where(UserAction.action_type == "POST")
        .where(UserAction.resource.like("%/auth/login%"))
        .where(UserAction.outcome == "error")
        .order_by(UserAction.timestamp.desc())
        .limit(100)
    )
    failed_logins = (await session.exec(stmt)).all()

# Get permission denied events
async with async_session() as session:
    stmt = (
        select(UserAction)
        .where(UserAction.outcome == "permission_denied")
        .order_by(UserAction.timestamp.desc())
    )
    denied = (await session.exec(stmt)).all()

# Get actions on a specific resource
async with async_session() as session:
    stmt = (
        select(UserAction)
        .where(UserAction.resource == "Author:123")
        .order_by(UserAction.timestamp.desc())
    )
    author_actions = (await session.exec(stmt)).all()
```

## Common Use Cases

### 1. Security Incident Investigation

Track what a compromised user did:

```python
actions = await session.exec(
    select(UserAction)
    .where(UserAction.user_id == compromised_user_id)
    .where(UserAction.timestamp >= incident_start)
    .where(UserAction.timestamp <= incident_end)
    .order_by(UserAction.timestamp.asc())
)
```

### 2. Failed Authentication Monitoring

Detect brute force attempts:

```python
failed_logins = await session.exec(
    select(UserAction)
    .where(UserAction.resource.like("%/auth/login%"))
    .where(UserAction.outcome == "error")
    .where(UserAction.timestamp >= datetime.utcnow() - timedelta(hours=1))
    .order_by(UserAction.timestamp.desc())
)
```

### 3. User Activity Timeline

Generate activity report for a user:

```python
timeline = await session.exec(
    select(UserAction)
    .where(UserAction.user_id == user_id)
    .order_by(UserAction.timestamp.desc())
    .limit(100)
)
```

### 4. Resource Access Audit

See who accessed a sensitive resource:

```python
access_log = await session.exec(
    select(UserAction)
    .where(UserAction.resource.like("Author:sensitive_id%"))
    .order_by(UserAction.timestamp.desc())
)
```

## Performance Considerations

### Database Indexes

The following indexes are created automatically:

- `user_id` - Fast user-specific queries
- `timestamp` - Date range filtering
- `action_type` - Action type filtering
- `outcome` - Error/success filtering
- `request_id` - Request correlation
- Composite index on `(user_id, timestamp)` - Optimized user timeline queries

### Best Practices

1. **Asynchronous logging**: All logging is async to avoid blocking requests
2. **Pagination**: Always use pagination when querying large result sets
3. **Date range limits**: Limit queries to reasonable time windows (e.g., 30 days)
4. **Archival**: Implement log archival for records older than retention period
5. **Partitioning**: Consider table partitioning by date for very large deployments

## Compliance Features

### GDPR

**Right to be Forgotten**:
```python
# Delete all logs for a user
await session.exec(delete(UserAction).where(UserAction.user_id == user_id))
```

**Data Export**:
```python
# Export user's activity history
actions = await session.exec(
    select(UserAction).where(UserAction.user_id == user_id)
)
export_data = [action.model_dump() for action in actions]
```

### HIPAA

- All logs containing PHI are encrypted at rest (PostgreSQL encryption)
- 6-year retention requirement enforced by archival policy
- Access to audit logs restricted to admin role

### SOX

- Immutable logs (no UPDATE capability in the model)
- Financial transaction logs retained indefinitely
- Audit trail for all data modifications

### PCI-DSS

- Cardholder data access logged (if applicable)
- 1-year minimum retention enforced

## Configuration

Environment variables in `app/settings.py`:

```python
# Audit logging settings
AUDIT_LOG_ENABLED: bool = True  # Enable/disable audit logging
AUDIT_LOG_RETENTION_DAYS: int = 365  # Log retention period
AUDIT_LOG_EXCLUDED_PATHS: list[str] = [
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json"
]
```

## Excluded Paths

The following paths are **not logged** to reduce noise:

- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics
- `/docs` - API documentation
- `/openapi.json` - OpenAPI schema
- `/static/*` - Static files

## Monitoring

Prometheus metrics track audit logging performance:

```
# Total audit logs created
audit_logs_total{outcome}

# Audit log creation duration
audit_log_duration_seconds

# Audit log errors
audit_log_errors_total{error_type}
```

## Troubleshooting

### Logs not appearing

1. Check `AUDIT_LOG_ENABLED` setting
2. Verify user is authenticated (unauthenticated requests not logged)
3. Check if path is in `AUDIT_LOG_EXCLUDED_PATHS`
4. Review application logs for errors

### Performance issues

1. Verify database indexes exist
2. Check query date ranges (avoid unbounded queries)
3. Use pagination for large result sets
4. Consider archiving old logs

### Storage growth

1. Implement log archival (move old logs to cold storage)
2. Adjust retention policy
3. Enable log compression
4. Consider external logging service for high-volume scenarios

## Future Enhancements

Potential improvements to consider:

- **Log streaming**: Real-time log streaming to SIEM tools
- **Anomaly detection**: ML-based detection of unusual patterns
- **Log encryption**: Per-record encryption for sensitive actions
- **Export formats**: CSV/JSON export functionality
- **Compliance reports**: Automated compliance report generation
- **Log integrity**: Cryptographic checksums to detect tampering

## Related Documentation

- [Authentication Guide](AUTHENTICATION.md)
- [Testing Guide](TESTING.md)
- [Database Migrations](../DATABASE_MIGRATIONS.md)
