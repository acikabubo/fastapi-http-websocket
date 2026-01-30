# Architecture Guide

This guide covers the architectural patterns, design principles, and core components of the FastAPI HTTP/WebSocket application.

## Table of Contents

- [Project Overview](#project-overview)
- [Design Patterns](#design-patterns)
- [Request Flow](#request-flow)
- [Core Components](#core-components)
- [Directory Structure](#directory-structure)
- [Creating New WebSocket Handlers](#creating-new-websocket-handlers)
- [Response Models](#response-models)
- [Common Patterns](#common-patterns)
- [Related Documentation](#related-documentation)

## Project Overview

This is a FastAPI application implementing both HTTP and WebSocket handlers with role-based access control (RBAC), Keycloak authentication, and PostgreSQL database integration. The architecture is designed around a package-based routing system where requests are routed through a custom `PackageRouter` that handles validation, permission checking, and handler dispatch.

## Design Patterns

This project uses modern design patterns for better maintainability, testability, and code reuse:

### **Repository + Command + Dependency Injection** (Preferred)

**Use these patterns for all new features**. They provide:
- ✅ **Testability** - Easy to mock dependencies without database
- ✅ **Reusability** - Same business logic in HTTP and WebSocket handlers
- ✅ **Maintainability** - Clear separation: Repository (data) → Command (logic) → Handler (protocol)
- ✅ **Type Safety** - Full type hints with FastAPI's `Depends()`

**Quick Example:**
```python
# 1. Repository (data access)
class AuthorRepository(BaseRepository[Author]):
    async def get_by_name(self, name: str) -> Author | None:
        ...

# 2. Command (business logic)
class CreateAuthorCommand(BaseCommand[CreateAuthorInput, Author]):
    def __init__(self, repository: AuthorRepository):
        self.repository = repository

    async def execute(self, input_data: CreateAuthorInput) -> Author:
        # Check duplicates
        if await self.repository.exists(name=input_data.name):
            raise ValueError("Author already exists")
        return await self.repository.create(Author(**input_data.model_dump()))

# 3. HTTP Handler (uses command)
@router.post("/authors")
async def create_author(data: CreateAuthorInput, repo: AuthorRepoDep) -> Author:
    command = CreateAuthorCommand(repo)
    return await command.execute(data)

# 4. WebSocket Handler (reuses same command!)
@pkg_router.register(PkgID.CREATE_AUTHOR)
async def create_author_ws(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        repo = AuthorRepository(session)
        command = CreateAuthorCommand(repo)  # Same logic!
        author = await command.execute(CreateAuthorInput(**request.data))
        return ResponseModel(..., data=author.model_dump())
```

**Documentation:**
- 📖 **Full Guide**: [docs/architecture/DESIGN_PATTERNS_GUIDE.md](../architecture/DESIGN_PATTERNS_GUIDE.md)
- 🚀 **Quick Reference**: [docs/architecture/PATTERNS_QUICK_REFERENCE.md](../architecture/PATTERNS_QUICK_REFERENCE.md)
- 💡 **Example**: [app/api/http/author.py](../../app/api/http/author.py)
- ✅ **Tests**: [tests/test_author_commands.py](../../tests/test_author_commands.py)

**When Creating New Features:**
1. Define repository in `app/repositories/<feature>_repository.py`
2. Define commands in `app/commands/<feature>_commands.py`
3. Add repository dependency to `app/dependencies.py`
4. Create HTTP endpoints using injected repository
5. Create WebSocket handlers reusing same commands
6. Write unit tests for repository and commands

## Request Flow

### HTTP Requests

1. Request hits FastAPI endpoint
2. `AuthenticationMiddleware` (Starlette) authenticates user via `AuthBackend` using Keycloak token
3. `require_roles()` FastAPI dependency checks RBAC permissions (defined in endpoint decorators)
4. Request reaches endpoint handler in `app/api/http/`

### WebSocket Requests

1. Client connects to `/web` WebSocket endpoint
2. `PackageAuthWebSocketEndpoint` authenticates via Keycloak token in query params
3. Client sends JSON with `{"pkg_id": <int>, "req_id": "<uuid>", "data": {...}}`
4. `Web.on_receive()` validates request → `pkg_router.handle_request()`
5. `PackageRouter` checks permissions, validates data, dispatches to registered handler
6. Handler returns `ResponseModel` sent back to client

## Core Components

### PackageRouter

**Location**: `app/routing.py`

- Central routing system for WebSocket requests
- Handlers register using `@pkg_router.register(PkgID.*, json_schema=..., roles=[...])`
- Provides validation, permission checking, and dispatch
- RBAC roles defined directly in the decorator's `roles` parameter
- See `PkgID` enum in `app/api/ws/constants.py` for available package IDs

### Authentication

**Location**: `app/auth.py`

- `AuthBackend`: Decodes Keycloak JWT tokens from Authorization header (HTTP) or query string (WebSocket)
- User data extracted into `UserModel` with roles
- Excluded paths configured via `EXCLUDED_PATHS` regex in settings
- Raises `AuthenticationError` (from `app/exceptions`) for authentication failures:
  - `token_expired`: JWT token has expired
  - `invalid_credentials`: Invalid Keycloak credentials
  - `token_decode_error`: Token decoding/validation failed

### RBAC Manager

**Location**: `app/managers/rbac_manager.py`

- Singleton manager for role-based access control
- `check_ws_permission(pkg_id, user)`: Validates WebSocket permissions using roles from `pkg_router.permissions_registry`
- `require_roles(*roles)`: FastAPI dependency for HTTP endpoint permission checking
- Permissions defined in code via decorators:
  - WebSocket: `@pkg_router.register(roles=[...])`
  - HTTP: `dependencies=[Depends(require_roles(...))]`
- No external configuration file - all permissions co-located with handler code

### Keycloak Integration

**Location**: `app/managers/keycloak_manager.py`

- Singleton managing `KeycloakAdmin` and `KeycloakOpenID` clients
- Configuration via environment variables (see `app/settings.py`)
- `login_async(username, password)` returns access token using native async methods
- Protected by circuit breaker pattern to prevent cascading failures

### WebSocket Connection Manager

**Location**: `app/managers/websocket_connection_manager.py`

- Manages active WebSocket connections
- `broadcast(message)` sends to all connected clients
- Connection tracking with logging

### Database

**Location**: `app/storage/db.py`

- PostgreSQL via SQLModel (async SQLAlchemy)
- `get_paginated_results(model, page, per_page, filters=...)` for pagination
- Custom filter functions can be passed via `apply_filters` parameter
- Database initialization with retry logic in `wait_and_init_db()`

### Rate Limiting

**Locations**: `app/utils/rate_limiter.py`, `app/middlewares/rate_limit.py`

- Redis-based sliding window algorithm for HTTP and WebSocket rate limiting
- `RateLimiter`: Tracks request counts per user/IP within configurable time windows
  - `check_rate_limit(key, limit, window_seconds, burst)` returns (is_allowed, remaining)
  - Supports burst limits for short-term traffic spikes
  - Fail mode configurable via `RATE_LIMIT_FAIL_MODE` setting
- `ConnectionLimiter`: Manages WebSocket connection limits per user
- `RateLimitMiddleware`: HTTP middleware adding rate limits to endpoints
- WebSocket rate limiting in `PackageAuthWebSocketEndpoint`

### Security Middlewares

**Locations**: `app/middlewares/security_headers.py`, `app/middlewares/request_size_limit.py`

- `SecurityHeadersMiddleware`: Adds security headers to all HTTP responses
  - Prevents clickjacking, MIME sniffing, XSS attacks
  - Enforces HTTPS with HSTS
  - Content Security Policy with WebSocket support
- `RequestSizeLimitMiddleware`: Protects against large payload attacks (default 1MB)
- `TrustedHostMiddleware`: Validates Host header against allowed hosts

### Audit Logger

**Location**: `app/utils/audit_logger.py`

- Async queue-based audit log writer for non-blocking audit logging
- Processes audit log entries in background without blocking HTTP requests
- Batch processing with backpressure mechanism
- Tracks metrics: `audit_logs_total`, `audit_logs_written_total`, `audit_logs_dropped_total`

### Error Handler

**Location**: `app/utils/error_handler.py`

- Centralized error handling utilities for HTTP and WebSocket endpoints
- `handle_http_errors` decorator: Unified error handling for HTTP endpoints
- Standardized error response format
- Reduces boilerplate try/except blocks

## Directory Structure

```
app/
├── __init__.py                    # Application factory with startup/shutdown handlers
├── api/
│   ├── http/                      # HTTP endpoint routers (auto-discovered)
│   └── ws/
│       ├── handlers/              # WebSocket handlers (@pkg_router.register)
│       ├── consumers/             # WebSocket endpoint classes (e.g., Web)
│       └── constants.py           # PkgID and RSPCode enums
├── managers/                      # Singleton managers (RBAC, Keycloak, WebSocket)
├── middlewares/                   # Custom middleware
├── models/                        # SQLModel database models
├── schemas/                       # Pydantic models for validation
├── repositories/                  # Data access layer
├── commands/                      # Business logic layer
├── tasks/                         # Background tasks
├── storage/                       # Database and Redis utilities
└── utils/                         # Utility modules
```

## Creating New WebSocket Handlers

The project uses an **f-string-based code generator** for creating WebSocket handlers with AST validation and automatic formatting.

### Benefits

- ✅ No template files to maintain
- ✅ Full IDE support with syntax highlighting
- ✅ AST validation catches syntax errors before file creation
- ✅ Auto-formatting with Black (79-char line length)
- ✅ Type-safe with proper type hints
- ✅ Passes all pre-commit hooks automatically

### Steps

1. Add new `PkgID` to `app/api/ws/constants.py` enum
2. Generate handler using CLI:
   ```bash
   make new-ws-handlers  # Interactive prompts

   # Or use the generator directly:
   python generate_ws_handler.py handler_name PKG_ID_NAME [options]
   ```
3. Implement the TODO sections in the generated file
4. Verify registration: `make ws-handlers`

### Generator Options

```bash
# Simple handler
python generate_ws_handler.py get_status GET_STATUS

# With JSON schema validation
python generate_ws_handler.py create_author CREATE_AUTHOR --schema

# With pagination
python generate_ws_handler.py get_authors GET_AUTHORS --paginated

# With RBAC roles
python generate_ws_handler.py delete_author DELETE_AUTHOR --roles admin delete-author

# Combine options
python generate_ws_handler.py get_users GET_USERS --schema --paginated --roles view-users

# Overwrite existing file
python generate_ws_handler.py handler_name PKG_ID --overwrite
```

### Generated Code Structure

```python
@pkg_router.register(
    PkgID.MY_NEW_HANDLER,
    json_schema=MySchema,  # If --schema flag used
    roles=["required-role"]  # If --roles flag used
)
async def my_handler(request: RequestModel) -> ResponseModel:
    """
    Comprehensive docstring with examples automatically generated.
    """
    try:
        # TODO: Implement your handler logic here
        return ResponseModel.success(request.pkg_id, request.req_id, data={...})
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return ResponseModel.err_msg(...)
    except Exception as e:
        logger.error(f"Error in my_handler: {e}", exc_info=True)
        return ResponseModel.err_msg(...)
```

### RBAC Examples

**Multiple roles** (user must have ALL):
```python
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]
)
async def delete_author_handler(request: RequestModel) -> ResponseModel:
    # Only users with both roles can access
    pass
```

**Public endpoint** (no authentication):
```python
@pkg_router.register(
    PkgID.PUBLIC_DATA,
    json_schema=PublicDataSchema
    # No roles parameter = public access
)
async def public_handler(request: RequestModel) -> ResponseModel:
    pass
```

## Response Models

All WebSocket handlers return `ResponseModel` with:
- `pkg_id`: Same as request
- `req_id`: Same as request UUID
- `status_code`: `RSPCode` enum value (0 = OK)
- `data`: Response payload (dict or list)
- `meta`: Optional pagination metadata (`MetadataModel`)

Helper methods:
- `ResponseModel.success(pkg_id, req_id, data, meta=...)`
- `ResponseModel.err_msg(pkg_id, req_id, msg, status_code)`

## Common Patterns

### Adding HTTP Endpoint

1. Create router in `app/api/http/<module>.py`
2. Define `router = APIRouter()` and endpoints
3. Use `require_roles()` dependency for RBAC protection
4. Router will be auto-discovered by `collect_subrouters()`

**Example:**
```python
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_roles
from app.schemas.author import Author

router = APIRouter(prefix="/api", tags=["authors"])

@router.get(
    "/authors",
    dependencies=[Depends(require_roles("get-authors"))]
)
async def get_authors() -> list[Author]:
    """Get all authors - requires 'get-authors' role."""
    pass

@router.post(
    "/authors",
    dependencies=[Depends(require_roles("create-author", "admin"))]
)
async def create_author(author: Author) -> Author:
    """Create author - requires BOTH roles."""
    pass

@router.get("/public")
async def public_endpoint():
    """Public endpoint - no authentication required."""
    pass
```

### Adding Background Tasks

1. Add task functions to `app/tasks/`
2. Register in `app/__init__.py` startup handler
3. Append to global `tasks` list for graceful shutdown

### Redis Pub/Sub

- Use `RRedis()` singleton from `app/storage/redis.py`
- Subscribe in startup handler: `await r.subscribe("channel", callback)`

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Development Guide](development-guide.md) - Running the app, Docker, WebSocket handlers
- [Testing Guide](testing-guide.md) - Test infrastructure, fixtures, load/chaos tests
- [Code Quality Guide](code-quality-guide.md) - Linting, type checking, pre-commit hooks
- [Configuration Guide](configuration-guide.md) - Settings, environment variables, validation
- [Database Guide](database-guide.md) - Sessions, migrations, pagination, relationships
- [Monitoring Guide](monitoring-guide.md) - Prometheus, alerts, logging, dashboards
