# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Cookiecutter template** for generating FastAPI applications with both HTTP and WebSocket handlers, featuring role-based access control (RBAC), Keycloak authentication, Redis integration, and PostgreSQL database support. The architecture centers around a custom `PackageRouter` that handles validation, permission checking, and handler dispatch for WebSocket requests.

**Required Services:** Redis and Keycloak are required components. This simplified architecture ensures consistency and reduces complexity.

## Additional Documentation

- **[Development Patterns & Best Practices](docs/DEVELOPMENT_PATTERNS.md)** - Recommended patterns for database session management, error handling, testing, and security
- Add more documentation files in the `docs/` folder as needed

## Template Variables

When working with this template, be aware of these Cookiecutter variables:
- `{{cookiecutter.project_name}}` - Project display name
- `{{cookiecutter.project_slug}}` - Directory name (lowercase with underscores)
- `{{cookiecutter.module_name}}` - Python module name (default: "src")

## Development Commands

### Generating Projects from Template
```bash
# Generate new project from this template
cookiecutter --overwrite-if-exists <path-to-this-template>
```

### Running Generated Applications
```bash
# Start server with hot-reload (in generated project)
make serve

# Or using uvicorn directly
uvicorn {{cookiecutter.module_name}}:application --host 0.0.0.0 --reload
```

### Docker Development (in generated project)
```bash
make build    # Build containers
make start    # Start services (PostgreSQL, Redis, Keycloak)
make stop     # Stop services
make shell    # Enter development shell
```

### Testing (in generated project)
```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_file.py::test_function_name
```

### Code Quality & Linting (in generated project)
```bash
# Linting
make ruff-check
# Or: uvx ruff check --config=pyproject.toml

# Type checking (strict mode)
uvx mypy {{cookiecutter.module_name}}/

# Docstring coverage (≥80% required)
uvx interrogate {{cookiecutter.module_name}}/

# Dead code scanning
make dead-code-scan
# Or: uvx vulture {{cookiecutter.module_name}}/

# Spell checking
uvx typos
```

### Security Scanning (in generated project)
```bash
make bandit-scan         # SAST scanning
make skjold-scan         # Dependency vulnerabilities
make outdated-pkgs-scan  # Check outdated packages
```

### WebSocket Handler Management (in generated project)
```bash
# List all PkgIDs and handlers
make ws-handlers

# Generate new WebSocket handler from template
make new-ws-handlers
```

## Architecture

### Core Request Flow

**HTTP Requests:**
1. Request → `AuthenticationMiddleware` (Starlette) → `AuthBackend` validates Keycloak JWT token
2. `PermAuthHTTPMiddleware` checks RBAC permissions against `actions.json`
3. Request reaches endpoint handler in `{{cookiecutter.module_name}}/api/http/`

**WebSocket Requests:**
1. Client connects to `/web` WebSocket endpoint
2. `PackageAuthWebSocketEndpoint` authenticates via Keycloak token (query params)
3. Client sends JSON: `{"pkg_id": <int>, "req_id": "<uuid>", "data": {...}}`
4. `Web.on_receive()` validates → `pkg_router.handle_request()`
5. `PackageRouter` validates, checks permissions, dispatches to handler
6. Handler returns `ResponseModel` sent to client

### Key Components

**PackageRouter ([routing.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/routing.py)):**
- Central routing system for WebSocket requests
- Handlers register via `@pkg_router.register(PkgID.*, json_schema=...)`
- Provides validation, permission checking, and dispatch
- See `PkgID` enum in [constants.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/api/ws/constants.py)

**Authentication ([auth.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/auth.py)):**
- `AuthBackend`: Decodes Keycloak JWT from Authorization header (HTTP) or query string (WebSocket)
- User data extracted into `UserModel` with roles
- Excluded paths configured via `EXCLUDED_PATHS` regex in settings
- Supports `DEBUG_AUTH` mode for development (never use in production!)

**RBAC Manager ([managers/rbac_manager.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/managers/rbac_manager.py)):**
- Singleton loading role definitions from `actions.json`
- `check_ws_permission(pkg_id, user)`: WebSocket permission validation
- `check_http_permission(request)`: HTTP permission validation
- Permission map: `{"roles": [...], "ws": {<pkg_id>: <role>}, "http": {<path>: {<method>: <role>}}}`

**Database ([storage/db.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/storage.db.py)):**
- PostgreSQL via SQLModel (async SQLAlchemy)
- `get_paginated_results(model, page, per_page, filters=...)` for pagination
- Custom filter functions via `apply_filters` parameter
- Database initialization with retry logic: `wait_and_init_db()`

**Response Models ([schemas/response.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/schemas/response.py)):**
All WebSocket handlers return `ResponseModel`:
- `pkg_id`: Same as request
- `req_id`: Same as request UUID
- `status_code`: `RSPCode` enum (0 = OK, 1 = ERROR, 2 = INVALID_DATA, 3 = PERMISSION_DENIED)
- `data`: Response payload (dict or list)
- `meta`: Optional pagination metadata (`MetadataModel`)

Helper methods:
- `ResponseModel.ok_msg(pkg_id, req_id, data, msg=...)`
- `ResponseModel.err_msg(pkg_id, req_id, msg, status_code)`

### Directory Structure (in generated projects)

```
{{cookiecutter.module_name}}/
├── __init__.py              # Application factory with startup/shutdown
├── auth.py                  # Authentication backend (Keycloak JWT)
├── routing.py               # PackageRouter and subrouter collection
├── settings.py              # Pydantic settings (env vars)
├── api/
│   ├── http/                # HTTP endpoint routers (auto-discovered)
│   └── ws/
│       ├── constants.py     # PkgID and RSPCode enums
│       ├── handlers/        # WebSocket handlers (@pkg_router.register)
│       ├── consumers/       # WebSocket endpoint classes (e.g., Web)
│       ├── validation.py    # JSON schema validation utilities
│       └── websocket.py     # PackageAuthWebSocketEndpoint base class
├── managers/                # Singleton managers
│   ├── rbac_manager.py      # RBAC permission checking
│   ├── websocket_connection_manager.py  # Active connection tracking
│   └── keycloak_manager.py  # Keycloak client management
├── middlewares/             # Custom middleware
│   └── action.py            # PermAuthHTTPMiddleware (HTTP RBAC)
├── models/                  # SQLModel database models
├── schemas/                 # Pydantic request/response models
├── storage/                 # Database and Redis utilities
├── tasks/                   # Background tasks
└── utils/                   # Utility functions
```

## Creating New WebSocket Handlers

1. **Add new PkgID** to [constants.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/api/ws/constants.py) enum:
```python
class PkgID(IntEnum):
    MY_NEW_HANDLER = 10
```

2. **Create handler** in `{{cookiecutter.module_name}}/api/ws/handlers/`:
```bash
make new-ws-handlers  # Interactive CLI generator
```

Or manually:
```python
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.api.ws.constants import PkgID, RSPCode
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import ResponseModel

@pkg_router.register(PkgID.MY_NEW_HANDLER, json_schema=MySchema)
async def my_handler(request: RequestModel) -> ResponseModel:
    return ResponseModel.ok_msg(
        request.pkg_id,
        request.req_id,
        data={"result": "success"}
    )
```

3. **Update `actions.json`** with required role:
```json
{
  "ws": {
    "10": "admin"
  }
}
```

4. **Verify registration**: `make ws-handlers`

## Database Pagination Pattern

Use `get_paginated_results()` for all list endpoints:

```python
from {{cookiecutter.module_name}}.storage.db import get_paginated_results

results, meta = await get_paginated_results(
    MyModel,
    page=request.data.get("page", 1),
    per_page=request.data.get("per_page", 20),
    filters={"status": "active"}  # Optional dict filters
)

return ResponseModel.ok_msg(
    request.pkg_id,
    request.req_id,
    data=[r.model_dump() for r in results],
    meta=meta
)
```

## Async Relationships with AsyncAttrs

**All database models should inherit from `BaseModel`** to enable proper async relationship handling.

### BaseModel Pattern

```python
from {{cookiecutter.module_name}}.models.base import BaseModel
from sqlmodel import Field, Relationship

class Author(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    books: list["Book"] = Relationship(back_populates="author")

class Book(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author_id: int = Field(foreign_key="author.id")
    author: Author = Relationship(back_populates="books")
```

### Eager Loading (Preferred)

**Best practice for better performance** - Load relationships upfront:

```python
from sqlalchemy.orm import selectinload, joinedload

# One-to-many (use selectinload)
async with async_session() as session:
    stmt = select(Author).options(selectinload(Author.books))
    result = await session.execute(stmt)
    author = result.scalar_one()
    books = author.books  # Already loaded, no await needed!

# Many-to-one (use joinedload)
async with async_session() as session:
    stmt = select(Book).options(joinedload(Book.author))
    result = await session.execute(stmt)
    book = result.scalar_one()
    author = book.author  # Already loaded
```

### Lazy Loading (When Needed)

Use `awaitable_attrs` for dynamic relationship access:

```python
async with async_session() as session:
    author = await session.get(Author, 1)
    # Access lazy-loaded relationship asynchronously
    books = await author.awaitable_attrs.books
```

**Important notes:**
- ✅ **Prefer eager loading** (selectinload/joinedload) for better performance
- ✅ Use `awaitable_attrs` only when you can't predict which relationships you'll need
- ✅ `BaseModel` adds no overhead if relationships aren't used
- ❌ **Never access relationships directly without eager loading** - causes MissingGreenlet errors

## Configuration

Environment variables in [settings.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/settings.py):

**Keycloak (Required):**
- `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`
- `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
- `DEBUG_AUTH`, `DEBUG_AUTH_USERNAME`, `DEBUG_AUTH_PASSWORD`

**Redis (Required):**
- `REDIS_IP`, `REDIS_PORT`
- `MAIN_REDIS_DB`, `AUTH_REDIS_DB`
- `USER_SESSION_REDIS_KEY_PREFIX`

**Database:**
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`, `DB_POOL_PRE_PING`
- `DB_INIT_RETRY_INTERVAL`, `DB_INIT_MAX_RETRIES`

**General:**
- `ACTIONS_FILE_PATH` (default: `actions.json`)
- `EXCLUDED_PATHS` (regex for auth bypass)
- `DEFAULT_PAGE_SIZE` (pagination default)

## Pre-commit Hooks

All commits in generated projects must pass:
- **ruff**: Linting and formatting (79 char line length)
- **mypy**: Strict type checking
- **interrogate**: ≥80% docstring coverage
- **typos**: Spell checking
- **bandit**: Security scanning (low severity `-lll`)
- **skjold**: Dependency vulnerability checks

## Code Style Requirements (in generated projects)

- **Line length**: 79 characters (ruff enforced)
- **Type hints**: Required on all functions (mypy --strict)
- **Docstrings**: Required on all public functions/classes/methods (80% minimum)
- **Formatting**: Double quotes, 4-space indentation
- **Unused code**: Caught by vulture (see [pyproject.toml]({{cookiecutter.project_slug}}/pyproject.toml) for ignored names)

## Testing Notes (in generated projects)

- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Mock Keycloak interactions where appropriate (`pytest-mock`)
- Database tests should use isolated test fixtures

## Common Patterns (in generated projects)

**Adding HTTP endpoint:**
- Create router in `{{cookiecutter.module_name}}/api/http/<module>.py`
- Define `router = APIRouter()` and endpoints
- Auto-discovered by `collect_subrouters()`

**Background tasks:**
- Add task functions to `{{cookiecutter.module_name}}/tasks/`
- Register in `{{cookiecutter.module_name}}/__init__.py` startup handler
- Append to global `tasks` list for graceful shutdown

**Router auto-discovery:**
HTTP and WebSocket routers are automatically discovered from:
- `{{cookiecutter.module_name}}/api/http/` - All Python modules with `router = APIRouter()`
- `{{cookiecutter.module_name}}/api/ws/consumers/` - WebSocket consumer classes

**WebSocket handler loading:**
All handlers in `{{cookiecutter.module_name}}/api/ws/handlers/` are auto-loaded via `load_handlers()` in [handlers/__init__.py]({{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/api/ws/handlers/__init__.py), triggering decorator registration.

## WebSocket Request/Response Format

**Request:**
```json
{
    "pkg_id": 1,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "data": {
        "page": 1,
        "per_page": 20
    }
}
```

**Response (paginated):**
```json
{
    "pkg_id": 1,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_code": 0,
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "pages": 5
    },
    "data": [...]
}
```

**Response (error):**
```json
{
    "pkg_id": 1,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_code": 3,
    "data": {
        "msg": "Permission denied"
    }
}
```

## Architecture Philosophy

**Simplicity Over Flexibility:**
This template requires Redis and Keycloak to maintain a clean, maintainable codebase. Optional features were removed to:
- Reduce complexity and conditional logic
- Ensure consistent behavior across all generated projects
- Simplify testing and maintenance
- Provide production-ready security by default

Both services are lightweight and commonly used in production environments, making this a reasonable requirement for most use cases.
