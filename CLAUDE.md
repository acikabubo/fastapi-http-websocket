# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Git Workflow and Worktree Syncing

### GitHub Issue Workflow

When working on GitHub issues, follow this workflow:

#### Step 0: Review Issue Context (REQUIRED BEFORE STARTING)

**CRITICAL**: Before making any changes, you MUST review the issue against the current codebase:

1. **Read the issue carefully** - Understand what's being requested
2. **Search/explore affected files** - Use Glob/Grep/Read to understand current implementation
3. **Check for recent changes** - Review git history to see if issue was already addressed:
   ```bash
   git log --oneline --all --grep="<issue_keyword>" -10
   git log --oneline -- path/to/relevant/file.py -5
   ```
4. **Verify current architecture** - Patterns may have evolved since issue was created:
   - Check if RBAC uses `actions.json` or decorator-based `roles` parameter
   - Verify error handling approach (unified vs individual)
   - Check middleware stack and configuration
   - Look for refactored or renamed components
5. **Identify dependencies** - Find related functionality that might be affected
6. **Ask clarifying questions** - If issue is outdated or conflicts with current code

**Why this matters:**
- Prevents working on already-fixed issues
- Avoids using outdated patterns or assumptions
- Ensures compatibility with recent architectural changes
- Saves time by understanding context first

#### Steps 1-7: Implementation and Deployment

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

#### Cookiecutter Placeholder Requirements

**CRITICAL**: When syncing files to `.worktree/`, you MUST replace project-specific references with cookiecutter placeholders:

1. **Import statements** - Replace `app.` with `{{cookiecutter.module_name}}.`:
   ```python
   # Main project
   from app.api.ws.websocket import PackageAuthWebSocketEndpoint

   # Worktree template
   from {{cookiecutter.module_name}}.api.ws.websocket import PackageAuthWebSocketEndpoint
   ```

2. **Test patch paths** - Use cookiecutter placeholders in mock paths:
   ```python
   # Main project
   with patch("app.api.ws.consumers.web.rate_limiter") as mock:

   # Worktree template
   with patch("{{cookiecutter.module_name}}.api.ws.consumers.web.rate_limiter") as mock:
   ```

3. **Project-specific code** - Replace with generic template equivalents:
   ```python
   # Main project uses Author model
   PkgID.GET_AUTHORS
   from app.repositories.author_repository import AuthorRepository

   # Worktree template uses generic test handler
   PkgID.TEST_HANDLER
   # No project-specific repository imports
   ```

4. **API method calls** - Template may use different method names:
   ```python
   # Main project (current)
   ResponseModel.success(pkg_id, req_id, data={})

   # Worktree template (if different)
   ResponseModel.ok_msg(pkg_id, req_id, data={})
   ```

5. **Configuration patterns** - Template may have evolved (check before syncing):
   - RBAC: `actions.json` → `roles` parameter in decorator
   - Error handling: Check for unified patterns
   - Middleware: Verify middleware stack matches template

**Verification Steps:**
- Use `sed` or similar to replace all `"app\.` with `"{{cookiecutter.module_name}}.`
- Search for hardcoded project names (e.g., "Author", "Book")
- Verify enum values match template (e.g., `PkgID.TEST_HANDLER`)
- Check that method signatures match template's current implementation
- Test generated project after syncing to ensure it works

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

## Design Patterns and Architecture

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
- 📖 **Full Guide**: [docs/architecture/DESIGN_PATTERNS_GUIDE.md](docs/architecture/DESIGN_PATTERNS_GUIDE.md)
- 🚀 **Quick Reference**: [docs/architecture/PATTERNS_QUICK_REFERENCE.md](docs/architecture/PATTERNS_QUICK_REFERENCE.md)
- 💡 **Example**: [app/api/http/author.py](app/api/http/author.py)
- ✅ **Tests**: [tests/test_author_commands.py](tests/test_author_commands.py)

**When Creating New Features:**
1. Define repository in `app/repositories/<feature>_repository.py`
2. Define commands in `app/commands/<feature>_commands.py`
3. Add repository dependency to `app/dependencies.py`
4. Create HTTP endpoints using injected repository
5. Create WebSocket handlers reusing same commands
6. Write unit tests for repository and commands

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

**Constants Module (`app/constants.py`)**

Application-wide constants are defined in `app/constants.py` to eliminate magic numbers and improve code clarity. Constants are organized by category:

- **Audit Logging**: `AUDIT_QUEUE_MAX_SIZE`, `AUDIT_BATCH_SIZE`, `AUDIT_BATCH_TIMEOUT_SECONDS`
- **Database**: `DB_MAX_RETRIES`, `DB_RETRY_DELAY_SECONDS`, `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`
- **Redis**: `REDIS_DEFAULT_PORT`, `REDIS_SOCKET_TIMEOUT_SECONDS`, `REDIS_CONNECT_TIMEOUT_SECONDS`, `REDIS_HEALTH_CHECK_INTERVAL_SECONDS`, `REDIS_MAX_CONNECTIONS`, `REDIS_MESSAGE_TIMEOUT_SECONDS`
- **Background Tasks**: `TASK_SLEEP_INTERVAL_SECONDS`, `TASK_ERROR_BACKOFF_SECONDS`
- **Rate Limiting**: `DEFAULT_RATE_LIMIT_PER_MINUTE`, `DEFAULT_RATE_LIMIT_BURST`, `DEFAULT_WS_MAX_CONNECTIONS_PER_USER`, `DEFAULT_WS_MESSAGE_RATE_LIMIT`
- **WebSocket**: `WS_POLICY_VIOLATION_CODE`, `WS_CLOSE_TIMEOUT_SECONDS`
- **Keycloak/Auth**: `KC_SESSION_EXPIRY_BUFFER_SECONDS`

**Settings (`app/settings.py`)**

Environment variables in `app/settings.py` (loaded via pydantic-settings) use constants as defaults:
- `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`
- `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
- `REDIS_IP`, `REDIS_PORT` (default: `REDIS_DEFAULT_PORT`)
- `REDIS_MAX_CONNECTIONS` (default: `REDIS_MAX_CONNECTIONS`)
- `MAIN_REDIS_DB`, `AUTH_REDIS_DB`
- `RATE_LIMIT_PER_MINUTE` (default: `DEFAULT_RATE_LIMIT_PER_MINUTE`)
- `WS_MAX_CONNECTIONS_PER_USER` (default: `DEFAULT_WS_MAX_CONNECTIONS_PER_USER`)
- `AUDIT_QUEUE_MAX_SIZE` (default: `AUDIT_QUEUE_MAX_SIZE`)
- `ACTIONS_FILE_PATH` (default: `actions.json`)

**Adding New Constants:**
1. Add to appropriate category in `app/constants.py`
2. Use descriptive name indicating purpose and units (e.g., `_SECONDS`, `_SIZE`)
3. Add docstring comment explaining the constant's purpose
4. If configurable, add to Settings with constant as default value

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

### Type Safety

This project uses advanced typing features for improved type safety and IDE support:

#### Protocol Classes (`app/protocols.py`)

Protocols define interfaces without requiring inheritance:

```python
from app.protocols import Repository
from app.models.author import Author

def process_data(repo: Repository[Author]) -> None:
    # Works with any repository implementation
    author = await repo.get_by_id(1)
```

#### Domain-Specific Types (`app/types.py`)

NewType prevents mixing different ID types:

```python
from app.types import UserId, Username, RequestId

def get_user(user_id: UserId) -> User:  # Type-safe IDs
    ...

def log_action(username: Username, request_id: RequestId):
    ...  # Can't accidentally swap these
```

Literal types for string constants:

```python
from app.types import AuditOutcome, ActionType

def log_audit(outcome: AuditOutcome):  # Only "success", "error", "permission_denied"
    ...
```

#### TypedDict for Structured Dicts (`app/schemas/types.py`)

Use TypedDict instead of bare `dict`:

```python
from app.schemas.types import PaginationParams, FilterDict

def get_paginated(params: PaginationParams) -> list[Model]:
    page = params["page"]  # Type-safe dictionary access
    filters = params.get("filters", {})
    ...
```

#### Type Annotation Best Practices

**Required:**
- ✅ All functions must have return type annotations
- ✅ Use `dict[str, Any]` instead of bare `dict`
- ✅ Use `list[Model]` instead of bare `list`
- ✅ Middleware `dispatch` methods must type `call_next: ASGIApp`
- ✅ Redis connection functions return `Redis | None`

**Examples:**
```python
# Good
async def get_connection(db: int = 1) -> Redis | None:
    ...

def process_data(filters: dict[str, Any]) -> list[Author]:
    ...

async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
    ...

# Bad
async def get_connection(db=1):  # ❌ No return type
    ...

def process_data(filters: dict):  # ❌ Generic dict
    ...

async def dispatch(self, request: Request, call_next):  # ❌ Missing type
    ...
```

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

### Async Relationships with AsyncAttrs

When SQLModel models have relationships (foreign keys, one-to-many, many-to-many), use the `BaseModel` class which includes SQLAlchemy's `AsyncAttrs` mixin for proper async relationship handling.

**Base Model Pattern:**

All table models that may have relationships should inherit from `BaseModel`:

```python
# app/models/base.py
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlmodel import SQLModel

class BaseModel(SQLModel, AsyncAttrs):
    """Base model with async relationship support."""
    pass
```

**Model Definition:**

```python
# app/models/author.py
from sqlmodel import Field, Relationship
from app.models.base import BaseModel

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

**Accessing Relationships:**

1. **Preferred: Eager Loading (Better Performance)**
   ```python
   from sqlalchemy.orm import selectinload

   async with async_session() as session:
       # Load author with all books in optimized queries
       stmt = select(Author).options(selectinload(Author.books))
       result = await session.execute(stmt)
       author = result.scalar_one()

       # Relationship already loaded, no await needed
       books = author.books  # ✅ Already loaded!
       for book in books:
           print(book.title)
   ```

2. **Alternative: Lazy Loading with awaitable_attrs**
   ```python
   async with async_session() as session:
       author = await session.get(Author, 1)

       # Access lazy-loaded relationship asynchronously
       books = await author.awaitable_attrs.books  # ✅ Awaitable
       for book in books:
           print(book.title)
   ```

3. **Single Query with JOIN (joinedload)**
   ```python
   from sqlalchemy.orm import joinedload

   async with async_session() as session:
       stmt = select(Author).options(joinedload(Author.books))
       result = await session.execute(stmt)
       author = result.scalar_one()

       # Single query with JOIN, already loaded
       books = author.books  # ✅ Already loaded!
   ```

**Rule of Thumb:**
- ✅ **Use eager loading** (`selectinload`, `joinedload`) for better performance
- ✅ Use `selectinload` for one-to-many and many-to-many relationships
- ✅ Use `joinedload` for many-to-one relationships
- ⚠️ Use `awaitable_attrs` only for dynamic relationship access or when eager loading would load unnecessary data

**Important Notes:**
- Models without relationships (e.g., `UserAction` audit logs) don't need to inherit from `BaseModel` and can use `SQLModel` directly
- `AsyncAttrs` has no performance penalty if relationships are not used
- Avoid accessing relationships directly without eager loading or `awaitable_attrs` - it will raise `MissingGreenlet` errors in async contexts

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

#### Migration Testing

This project includes automated migration testing to ensure migrations can be applied and rolled back cleanly.

**Running migration tests:**
```bash
# Test migrations manually (upgrade/downgrade cycle)
make test-migrations

# Run pytest-based structure tests
uv run pytest tests/test_migrations.py -v
```

**Pre-commit hook:**
Migration tests automatically run before commits when migration files are modified. The hook:
- Tests upgrade to head and downgrade by one revision
- Validates migration structure (unique IDs, docstrings, no conflicts)
- Prevents commits if migrations fail

**What gets tested:**

1. **Upgrade/Downgrade Cycle** (`scripts/test_migrations.py`):
   - Downgrades by one revision
   - Upgrades back to head
   - Verifies database stays in consistent state

2. **Migration Structure** (`tests/test_migrations.py`):
   - All revision IDs are unique
   - All migrations have descriptive docstrings (>10 chars)
   - No conflicting migration branches exist
   - All migrations (except first) have down_revision

**Best practices enforced:**
- ✅ Every migration must have a clear docstring explaining changes
- ✅ Migrations must be reversible (have downgrade logic)
- ✅ No merge conflicts in migration history
- ✅ Migration IDs must be unique

**Troubleshooting:**
If migration tests fail during pre-commit:
1. Check the error message for specific migration issues
2. Review your migration file in `app/storage/migrations/versions/`
3. Ensure downgrade logic correctly reverses upgrade changes
4. Test manually: `make test-migrations`
5. Fix issues and re-commit

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

**IMPORTANT**: When adding new Prometheus metrics to `app/utils/metrics.py`, you must also update the Grafana dashboard at `docker/grafana/provisioning/dashboards/fastapi-metrics.json` to visualize the new metrics. This ensures monitoring dashboards stay in sync with available metrics.

### Monitoring Keycloak with Prometheus

**Keycloak Metrics Endpoint:**
- Metrics endpoint: `http://localhost:9999/metrics` (exposed on port 9000 internally, mapped to 9999 externally)
- Enabled via `KC_METRICS_ENABLED=true` in `docker/.kc_env`
- Scraped by Prometheus every 30 seconds

**Key Keycloak Metrics:**
```
# Authentication & Sessions
keycloak_sessions - Active user sessions count
keycloak_logins_total - Total successful logins
keycloak_login_failures_total - Total failed login attempts

# Performance
keycloak_request_total - Total HTTP requests to Keycloak
keycloak_request_duration_bucket - Request duration histogram

# JVM Metrics
jvm_memory_used_bytes{area="heap"} - JVM heap memory usage
jvm_memory_max_bytes{area="heap"} - Maximum heap memory
jvm_gc_pause_seconds_sum - Garbage collection pause time
jvm_threads_current - Current thread count
jvm_threads_peak - Peak thread count

# Database Connection Pool (HikariCP)
hikaricp_connections_active - Active database connections
hikaricp_connections_idle - Idle database connections
hikaricp_connections_pending - Pending connection requests
```

**Grafana Dashboard:**
- Dashboard location: `docker/grafana/provisioning/dashboards/keycloak-metrics.json`
- Auto-provisioned on Grafana startup
- Access at: http://localhost:3000/d/keycloak-metrics

**Dashboard Panels:**
1. **Active Sessions** (Gauge) - Real-time session count
2. **Login Success/Failure Rate** (Time Series) - Authentication trends
3. **Failed Logins (Last Hour)** (Stat) - Security monitoring
4. **Request Duration (Percentiles)** (Time Series) - Performance p50/p95/p99
5. **Request Rate** (Time Series) - Traffic monitoring
6. **JVM Heap Memory Usage** (Time Series) - Memory consumption
7. **Garbage Collection Pause Time** (Time Series) - GC impact
8. **JVM Thread Count** (Time Series) - Thread pool status
9. **Database Connection Pool** (Time Series) - Connection pool health

**Troubleshooting:**
- If metrics endpoint is not accessible, check `KC_METRICS_ENABLED=true` in `docker/.kc_env`
- Verify Keycloak container exposes port 9000: `docker ps | grep keycloak`
- Check Prometheus targets: http://localhost:9090/targets
- View raw metrics: `curl http://localhost:9999/metrics`

**Security Considerations:**
- Metrics endpoint should be restricted in production (use network policies or firewall rules)
- Monitor failed login attempts for suspicious activity
- Set up alerts for high failure rates or unusual session patterns
