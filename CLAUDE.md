# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Git Workflow and Worktree Syncing

### GitHub Issue Workflow

When working on GitHub issues, follow this workflow:

1. **Fix the issue** - Make the necessary code changes
2. **Sync to worktree** - If changes affect `app/` or `tests/`, replicate to `.worktree/` template
3. **Commit to develop** - Commit changes to the `develop` branch with descriptive message including "Fixes #<issue_number>"
4. **Push to develop** - Push the commit to `origin/develop`
5. **Commit to worktree** - If worktree files were modified, commit them to the `project-template-develop` branch
6. **Push worktree** - Push worktree changes to `origin/project-template-develop`
7. **Close the issue** - Use `gh issue close <number>` with a descriptive comment

**CRITICAL**: Before committing and pushing changes to `.worktree/` folder, you MUST ask the user for confirmation first.

### Syncing Changes with Worktree Template

**CRITICAL RULE**: When making changes to code files in the main project (`app/`, `tests/`, etc.), you MUST replicate those changes to the corresponding files in the `.worktree/` cookiecutter template.

- Main project files in `app/` → `.worktree/{{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/`
- Main project files in `tests/` → `.worktree/{{cookiecutter.project_slug}}/tests/` (if applicable)
- **Exception**: Do NOT sync `CLAUDE.md` between main project and worktree (they have different purposes)

This ensures new projects generated from the cookiecutter template include all bug fixes and improvements.

### Git Commit Guidelines

When committing changes:
- Use conventional commit format: `fix:`, `feat:`, `refactor:`, etc.
- Include `Fixes #<issue_number>` in the commit message if closing an issue
- Always include the Claude Code footer:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- For worktree commits, clearly indicate it's syncing changes from the main project

## Project Overview

This is a FastAPI application implementing both HTTP and WebSocket handlers with role-based access control (RBAC), Keycloak authentication, and PostgreSQL database integration. The architecture is designed around a package-based routing system where requests are routed through a custom `PackageRouter` that handles validation, permission checking, and handler dispatch.

## Development Commands

### Running the Application
```bash
# Start the server with hot-reload
make serve

# Or using uvicorn directly
uvicorn app:application --host 0.0.0.0 --reload
```

### Docker Development
```bash
# Build containers
make build

# Start services (PostgreSQL, Redis, Keycloak, etc.)
make start

# Stop services
make stop

# Enter development shell
make shell
```

### Testing
```bash
# Run tests (uses pytest with asyncio support)
uv run pytest

# Run a single test
uv run pytest tests/test_check.py::test_function_name
```

### Code Quality & Linting
```bash
# Run ruff linter
make ruff-check

# Or directly with uvx
uvx ruff check --config=pyproject.toml

# Format code
uvx ruff format

# Type checking with mypy (configured with --strict)
uvx mypy app/

# Check docstring coverage (must be ≥80%)
uvx interrogate app/

# Find dead code
make dead-code-scan
# Or: uvx vulture app/

# Spell checking
uvx typos
```

### Security Scanning
```bash
# SAST scanning with Bandit
make bandit-scan

# Dependency vulnerability scanning
make skjold-scan

# Check for outdated packages
make outdated-pkgs-scan
```

### WebSocket Handler Management
```bash
# Show table of PkgIDs and their handlers
make ws-handlers

# Generate a new WebSocket handler from template
make new-ws-handlers
```

## Architecture

### Request Flow

**HTTP Requests:**
1. Request hits FastAPI endpoint
2. `AuthenticationMiddleware` (Starlette) authenticates user via `AuthBackend` using Keycloak token
3. `PermAuthHTTPMiddleware` checks RBAC permissions against `actions.json`
4. Request reaches endpoint handler in `app/api/http/`

**WebSocket Requests:**
1. Client connects to `/web` WebSocket endpoint
2. `PackageAuthWebSocketEndpoint` authenticates via Keycloak token in query params
3. Client sends JSON with `{"pkg_id": <int>, "req_id": "<uuid>", "data": {...}}`
4. `Web.on_receive()` validates request → `pkg_router.handle_request()`
5. `PackageRouter` checks permissions, validates data, dispatches to registered handler
6. Handler returns `ResponseModel` sent back to client

### Core Components

**PackageRouter (`app/routing.py`):**
- Central routing system for WebSocket requests
- Handlers register using `@pkg_router.register(PkgID.*, json_schema=...)`
- Provides validation, permission checking, and dispatch
- See `PkgID` enum in `app/api/ws/constants.py` for available package IDs

**Authentication (`app/auth.py`):**
- `AuthBackend`: Decodes Keycloak JWT tokens from Authorization header (HTTP) or query string (WebSocket)
- User data extracted into `UserModel` with roles
- Excluded paths configured via `EXCLUDED_PATHS` regex in settings

**RBAC (`app/managers/rbac_manager.py`):**
- Singleton manager loading role definitions from `actions.json`
- `check_ws_permission(pkg_id, user)`: Validates WebSocket request permissions
- `check_http_permission(request)`: Validates HTTP request permissions
- Permission map structure: `{"roles": [...], "ws": {<pkg_id>: <role>}, "http": {<path>: {<method>: <role>}}}`

**Keycloak Integration (`app/managers/keycloak_manager.py`):**
- Singleton managing `KeycloakAdmin` and `KeycloakOpenID` clients
- Configuration via environment variables (see `app/settings.py`)
- `login(username, password)` returns access token

**WebSocket Connection Manager (`app/managers/websocket_connection_manager.py`):**
- Manages active WebSocket connections
- `broadcast(message)` sends to all connected clients
- Connection tracking with logging

**Database (`app/storage/db.py`):**
- PostgreSQL via SQLModel (async SQLAlchemy)
- `get_paginated_results(model, page, per_page, filters=...)` for pagination
- Custom filter functions can be passed via `apply_filters` parameter
- Database initialization with retry logic in `wait_and_init_db()`

**Rate Limiting (`app/utils/rate_limiter.py`, `app/middlewares/rate_limit.py`):**
- Redis-based sliding window algorithm for HTTP and WebSocket rate limiting
- `RateLimiter`: Tracks request counts per user/IP within configurable time windows
  - `check_rate_limit(key, limit, window_seconds, burst)` returns (is_allowed, remaining)
  - Supports burst limits for short-term traffic spikes
  - Fails open on Redis errors (allows requests)
- `ConnectionLimiter`: Manages WebSocket connection limits per user
  - `add_connection(user_id, connection_id)` enforces max connections
  - `remove_connection(user_id, connection_id)` cleanup on disconnect
  - Tracks active connections in Redis sets
- `RateLimitMiddleware`: HTTP middleware adding rate limits to endpoints
  - Returns 429 Too Many Requests when limits exceeded
  - Adds X-RateLimit-* headers to all responses
  - Uses user ID (authenticated) or IP address (unauthenticated) as key
  - Respects EXCLUDED_PATHS for health checks and docs
- WebSocket rate limiting in `PackageAuthWebSocketEndpoint`:
  - Connection limiting in `on_connect()` (closes with WS_1008_POLICY_VIOLATION)
  - Message rate limiting in `Web.on_receive()` per user
- Configuration in `app/settings.py`:
  - `RATE_LIMIT_ENABLED`: Enable/disable rate limiting (default: True)
  - `RATE_LIMIT_PER_MINUTE`: HTTP request limit per minute (default: 60)
  - `RATE_LIMIT_BURST`: Burst allowance for traffic spikes (default: 10)
  - `WS_MAX_CONNECTIONS_PER_USER`: Max concurrent WebSocket connections (default: 5)
  - `WS_MESSAGE_RATE_LIMIT`: WebSocket messages per minute (default: 100)

**Prometheus Metrics (`app/utils/metrics.py`, `app/middlewares/prometheus.py`):**
- Comprehensive metrics collection for monitoring and observability
- `PrometheusMiddleware`: Automatically tracks HTTP request metrics
  - Request counts by method, endpoint, and status code
  - Request duration histograms with configurable buckets
  - In-progress request gauges
- WebSocket metrics tracking in `websocket.py` and `web.py`:
  - Active connections gauge
  - Connection totals by status (accepted, rejected_auth, rejected_limit)
  - Message counts (received/sent)
  - Message processing duration histograms by pkg_id
- Database and Redis metrics defined for future instrumentation:
  - Query duration histograms by operation type
  - Active connections gauge
  - Error counters by operation and error type
- Authentication and rate limiting metrics:
  - Auth attempt counters by status
  - Token validation counters
  - Rate limit hit counters by limit type
- Application-level metrics:
  - Error counters by type and handler
  - App info gauge with version and environment
- Metrics endpoint at `/metrics` (excluded from auth and rate limiting)
- Compatible with Prometheus scraping

### Directory Structure

- `app/__init__.py`: Application factory with startup/shutdown handlers
- `app/api/http/`: HTTP endpoint routers (auto-discovered by `collect_subrouters()`)
- `app/api/ws/handlers/`: WebSocket handlers registered with `@pkg_router.register()`
- `app/api/ws/consumers/`: WebSocket endpoint classes (e.g., `Web`)
- `app/api/ws/constants.py`: `PkgID` and `RSPCode` enums
- `app/managers/`: Singleton managers (RBAC, Keycloak, WebSocket connections)
- `app/middlewares/`: Custom middleware (`PermAuthHTTPMiddleware`, `RateLimitMiddleware`, `PrometheusMiddleware`)
- `app/models/`: SQLModel database models
- `app/utils/`: Utility modules (`rate_limiter.py`, `metrics.py`)
- `app/schemas/`: Pydantic models for request/response validation
- `app/tasks/`: Background tasks (e.g., `kc_user_session_task`)
- `app/storage/`: Database and Redis utilities

### Creating New WebSocket Handlers

1. Add new `PkgID` to `app/api/ws/constants.py` enum
2. Create handler in `app/api/ws/handlers/` or use CLI:
   ```bash
   make new-ws-handlers  # Uses Jinja2 template
   ```
3. Register handler with decorator:
   ```python
   @pkg_router.register(PkgID.MY_NEW_HANDLER, json_schema=MySchema)
   async def my_handler(request: RequestModel) -> ResponseModel:
       # Handler logic
       return ResponseModel.success(request.pkg_id, request.req_id, data={...})
   ```
4. Update `actions.json` with required role for the PkgID
5. Verify registration: `make ws-handlers`

### Response Models

All WebSocket handlers return `ResponseModel` with:
- `pkg_id`: Same as request
- `req_id`: Same as request UUID
- `status_code`: `RSPCode` enum value (0 = OK)
- `data`: Response payload (dict or list)
- `meta`: Optional pagination metadata (`MetadataModel`)

Helper methods:
- `ResponseModel.success(pkg_id, req_id, data, meta=...)`
- `ResponseModel.err_msg(pkg_id, req_id, msg, status_code)`

### Configuration

Environment variables in `app/settings.py` (loaded via pydantic-settings):
- `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`
- `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
- `REDIS_IP`, `MAIN_REDIS_DB`, `AUTH_REDIS_DB`
- `ACTIONS_FILE_PATH` (default: `actions.json`)

### Pre-commit Hooks

All commits must pass:
- **ruff**: Linting and formatting (79 char line length)
- **mypy**: Strict type checking
- **interrogate**: ≥80% docstring coverage
- **typos**: Spell checking
- **bandit**: Security scanning (low severity threshold `-lll`)
- **skjold**: Dependency vulnerability checks

### Code Style Requirements

- **Line length**: 79 characters (enforced by ruff)
- **Type hints**: Required on all functions (mypy --strict)
- **Docstrings**: Required on all public functions, classes, and methods (80% coverage minimum)
- **Formatting**: Double quotes, 4-space indentation
- **Unused code**: Will be caught by vulture (see `pyproject.toml` for ignored names)

### Database Session Management

**IMPORTANT**: Model methods should accept database sessions as parameters rather than creating their own sessions. This enables:
- Multiple operations in a single transaction
- Easier testing with mocked sessions
- Better transaction control

**Pattern for model methods:**
```python
from sqlmodel.ext.asyncio.session import AsyncSession

class MyModel(SQLModel, table=True):
    @classmethod
    async def create(
        cls, session: AsyncSession, instance: "MyModel"
    ) -> "MyModel":
        """
        Creates a new instance in the database.

        Args:
            session: Database session to use for the operation.
            instance: The instance to create.

        Returns:
            The created instance.
        """
        try:
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            return instance
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Integrity error: {e}")
            raise

    @classmethod
    async def get_list(
        cls, session: AsyncSession, **filters
    ) -> list["MyModel"]:
        """Retrieves a list of instances based on filters."""
        stmt = select(cls).where(
            *[getattr(cls, k) == v for k, v in filters.items()]
        )
        return (await session.exec(stmt)).all()
```

**Usage in HTTP endpoints:**
```python
from app.storage.db import async_session

@router.post("/my-models")
async def create_model(instance: MyModel) -> MyModel:
    async with async_session() as session:
        async with session.begin():
            return await MyModel.create(session, instance)

@router.get("/my-models")
async def get_models():
    async with async_session() as session:
        return await MyModel.get_list(session)
```

**Usage in WebSocket handlers:**
```python
async def my_handler(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        items = await MyModel.get_list(session, **request.data.get("filters", {}))
        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[item.model_dump() for item in items]
        )
```

### Database Migrations

This project uses **Alembic** for database schema migrations. The old `SQLModel.metadata.create_all()` approach has been replaced with proper migration management.

**Key commands:**
```bash
# Apply all pending migrations
make migrate

# Generate new migration after model changes
make migration msg="Add email field to Author"

# Rollback last migration
make rollback

# View migration history
make migration-history

# Check current migration version
make migration-current

# Stamp database at specific revision (for existing DBs)
make migration-stamp rev="head"
```

**Important workflow:**
1. Modify your SQLModel (e.g., add field to `Author`)
2. Generate migration: `make migration msg="description"`
3. **ALWAYS review** the generated migration in `app/storage/migrations/versions/`
4. Apply migration: `make migrate`
5. If issues occur, rollback: `make rollback`

**Adding new models:**
When you create a new model, import it in `app/storage/migrations/env.py`:
```python
from app.models.author import Author  # noqa: F401
from app.models.book import Book  # noqa: F401  # ADD NEW IMPORTS
```

**See:** [docs/DATABASE_MIGRATIONS.md](docs/DATABASE_MIGRATIONS.md) for complete guide.

### Database Pagination

Use `get_paginated_results()` for all list endpoints:
```python
from app.storage.db import get_paginated_results

results, meta = await get_paginated_results(
    Author,
    page=request.data.get("page", 1),
    per_page=request.data.get("per_page", 20),
    filters={"status": "active"}  # Optional
)

return ResponseModel.success(
    request.pkg_id,
    request.req_id,
    data=[r.model_dump() for r in results],
    meta=meta
)
```

### Testing Notes

- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Mock Keycloak interactions where appropriate (`pytest-mock`)
- Database tests should use test fixtures with isolated sessions

### Common Patterns

**Adding HTTP endpoint:**
- Create router in `app/api/http/<module>.py`
- Define `router = APIRouter()` and endpoints
- Will be auto-discovered by `collect_subrouters()`

**Background tasks:**
- Add task functions to `app/tasks/`
- Register in `app/__init__.py` startup handler
- Append to global `tasks` list for graceful shutdown

**Redis pub/sub:**
- Use `RRedis()` singleton from `app/storage/redis.py`
- Subscribe in startup handler: `await r.subscribe("channel", callback)`

### Monitoring with Prometheus

**Accessing Metrics:**
- Metrics endpoint: `GET /metrics`
- Excluded from authentication and rate limiting
- Returns Prometheus text format

**Key Metrics Available:**
```
# HTTP Metrics
http_requests_total{method,endpoint,status_code}
http_request_duration_seconds{method,endpoint}
http_requests_in_progress{method,endpoint}

# WebSocket Metrics
ws_connections_active
ws_connections_total{status}  # status: accepted, rejected_auth, rejected_limit
ws_messages_received_total
ws_messages_sent_total
ws_message_processing_duration_seconds{pkg_id}

# Application Metrics
app_info{version,python_version,environment}
rate_limit_hits_total{limit_type}
auth_attempts_total{status}
```

**Setting up Prometheus (Docker):**
```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

**Custom Metrics:**
```python
from app.utils.metrics import http_requests_total

# Increment counter
http_requests_total.labels(
    method="POST",
    endpoint="/api/custom",
    status_code=201
).inc()

# Observe histogram
from app.utils.metrics import db_query_duration_seconds
db_query_duration_seconds.labels(operation="select").observe(0.045)
```
