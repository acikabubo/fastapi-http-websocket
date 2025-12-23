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
   - Check current RBAC implementation (decorator-based `roles` parameter)
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
   - RBAC: Uses decorator-based `roles` parameter (no external config file)
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

# Generate a new WebSocket handler (uses f-string code generator)
make new-ws-handlers

# Or use the generator directly with options:
python generate_ws_handler.py handler_name PKG_ID_NAME [options]

# With JSON schema validation
python generate_ws_handler.py create_author CREATE_AUTHOR --schema

# With pagination
python generate_ws_handler.py get_authors GET_AUTHORS --paginated

# With RBAC roles
python generate_ws_handler.py delete_author DELETE_AUTHOR --roles admin delete-author

# Overwrite existing file
python generate_ws_handler.py handler_name PKG_ID --overwrite
```

## Architecture

### Request Flow

**HTTP Requests:**
1. Request hits FastAPI endpoint
2. `AuthenticationMiddleware` (Starlette) authenticates user via `AuthBackend` using Keycloak token
3. `require_roles()` FastAPI dependency checks RBAC permissions (defined in endpoint decorators)
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
- Handlers register using `@pkg_router.register(PkgID.*, json_schema=..., roles=[...])`
- Provides validation, permission checking, and dispatch
- RBAC roles defined directly in the decorator's `roles` parameter
- See `PkgID` enum in `app/api/ws/constants.py` for available package IDs

**Authentication (`app/auth.py`):**
- `AuthBackend`: Decodes Keycloak JWT tokens from Authorization header (HTTP) or query string (WebSocket)
- User data extracted into `UserModel` with roles
- Excluded paths configured via `EXCLUDED_PATHS` regex in settings

**RBAC (`app/managers/rbac_manager.py`):**
- Singleton manager for role-based access control
- `check_ws_permission(pkg_id, user)`: Validates WebSocket permissions using roles from `pkg_router.permissions_registry`
- `require_roles(*roles)`: FastAPI dependency for HTTP endpoint permission checking
- Permissions defined in code via decorators (WebSocket: `@pkg_router.register(roles=[...])`, HTTP: `dependencies=[Depends(require_roles(...))]`)
- No external configuration file - all permissions co-located with handler code

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
- `app/middlewares/`: Custom middleware (`RateLimitMiddleware`, `PrometheusMiddleware`)
- `app/models/`: SQLModel database models
- `app/utils/`: Utility modules (`rate_limiter.py`, `metrics.py`)
- `app/schemas/`: Pydantic models for request/response validation
- `app/tasks/`: Background tasks (e.g., `kc_user_session_task`)
- `app/storage/`: Database and Redis utilities

### Creating New WebSocket Handlers

The project uses an **f-string-based code generator** for creating WebSocket handlers with AST validation and automatic formatting.

**Benefits of the new generator:**
- ✅ No template files to maintain
- ✅ Full IDE support with syntax highlighting
- ✅ AST validation catches syntax errors before file creation
- ✅ Auto-formatting with Black (79-char line length)
- ✅ Type-safe with proper type hints
- ✅ Passes all pre-commit hooks automatically

**Steps to create a handler:**

1. Add new `PkgID` to `app/api/ws/constants.py` enum
2. Generate handler using CLI:
   ```bash
   make new-ws-handlers  # Interactive prompts

   # Or use the generator directly:
   python generate_ws_handler.py handler_name PKG_ID_NAME [options]
   ```
3. Implement the TODO sections in the generated file
4. Verify registration: `make ws-handlers`

**Generator options:**
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

**Generated code structure:**
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

**Example with multiple roles:**
```python
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]  # User must have ALL roles
)
async def delete_author_handler(request: RequestModel) -> ResponseModel:
    # Only users with both 'delete-author' AND 'admin' roles can access
    pass
```

**Public endpoint (no authentication required):**
```python
@pkg_router.register(
    PkgID.PUBLIC_DATA,
    json_schema=PublicDataSchema
    # No roles parameter = public access
)
async def public_handler(request: RequestModel) -> ResponseModel:
    pass
```

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

### Performance Profiling with Scalene

**Overview:**
The application includes optional integration with Scalene, a high-performance CPU, GPU, and memory profiler specifically designed for async Python applications. Scalene provides line-level profiling without significant performance impact, making it ideal for identifying bottlenecks in WebSocket handlers, connection managers, and broadcast operations.

**Why Scalene?**
- Zero-overhead profiling for async/await code
- Line-level visibility into CPU, memory, and GPU usage
- Identifies inefficient list comprehensions, Pydantic serialization, and async bottlenecks
- Ideal for real-time workloads with 1000+ WebSocket connections
- HTML reports with interactive visualizations

**Installation:**

```bash
# Install profiling dependencies (recommended)
make profile-install

# Or manually
uv sync --group profiling
pip install scalene
```

**Makefile Commands (Scalene 2.0+):**

```bash
# Run application with profiling
make profile

# View profiling report in browser (after stopping profiler)
make profile-view

# View profiling report in terminal
make profile-view-cli

# Clean profiling data
make profile-clean
```

**Running with Scalene:**

Scalene 2.0+ uses a new command structure with `run` and `view` subcommands:

```bash
# Basic profiling - saves to scalene-profile.json
scalene run -- uvicorn app:application --host 0.0.0.0

# View report in browser
scalene view

# View report in terminal
scalene view --cli

# Profile in Docker container
docker exec -it hw-server-shell \
  scalene run -- uvicorn app:application --host 0.0.0.0
```

**Note**: Scalene 2.0 generates profiles in JSON format (`scalene-profile.json`) instead of HTML. Use `scalene view` to open an interactive browser-based viewer, or `scalene view --cli` for terminal output.

**Scalene CLI Options:**

```bash
--html                      # Generate HTML report instead of terminal output
--outfile <path>            # Specify output file path
--cpu-percent-threshold N   # Only show lines using >N% CPU (default: 1)
--reduced-profile           # Lower overhead profiling mode
--profile-only <path>       # Only profile files matching path
--profile-exclude <path>    # Exclude files matching path
--cpu-only                  # Profile CPU usage only (skip memory)
--memory-only               # Profile memory usage only (skip CPU)
--use-virtual-time          # Use virtual time for more accurate async profiling
```

**Profiling API Endpoints:**

The application provides HTTP endpoints for managing profiling reports:

```bash
# Check profiling status and configuration
GET /api/profiling/status

Response:
{
  "enabled": true,
  "scalene_installed": true,
  "output_directory": "profiling_reports",
  "interval_seconds": 30,
  "python_version": "3.13.0",
  "command": "scalene --html --outfile report.html -- uvicorn ..."
}

# List all available profiling reports
GET /api/profiling/reports

Response:
{
  "reports": [
    {
      "filename": "websocket_profile_20250123_143000.html",
      "path": "profiling_reports/websocket_profile_20250123_143000.html",
      "size_bytes": 125000,
      "created_at": 1706019000
    }
  ],
  "total_count": 1
}

# Download specific profiling report
GET /api/profiling/reports/websocket_profile_20250123_143000.html

# Delete profiling report
DELETE /api/profiling/reports/websocket_profile_20250123_143000.html
```

**Profiling Context Manager:**

Use the `profile_context` helper for lightweight profiling of specific operations:

```python
from app.utils.profiling import profile_context

async def my_handler(request: RequestModel) -> ResponseModel:
    async with profile_context("my_handler_operation"):
        # Your code here
        result = await expensive_operation()

    return ResponseModel.success(...)
```

**What to Profile:**

1. **WebSocket Connection Lifecycle:**
   - Connection setup and authentication overhead
   - Message receive/send performance
   - Disconnect cleanup time

2. **Broadcast Operations:**
   - Time spent iterating over connections
   - JSON serialization overhead
   - Network I/O bottlenecks

3. **Handler Performance:**
   - Database query execution time
   - Pydantic model validation overhead
   - RBAC permission checking

4. **Memory Leaks:**
   - Unclosed WebSocket connections
   - Growing connection registries
   - Cached data accumulation

**Reading Scalene Reports:**

Scalene HTML reports show:
- **CPU %**: Percentage of time spent on each line (Python + native code)
- **Memory**: Memory allocated/freed per line
- **Copy Volume**: Data copying overhead
- **Timeline**: Interactive timeline of resource usage

Key metrics to watch:
- Lines with >5% CPU usage
- Memory allocations in loops
- High copy volumes (inefficient data handling)
- Async/await overhead

**Example Workflow:**

```bash
# 1. Enable profiling
export PROFILING_ENABLED=true

# 2. Start application with Scalene
scalene --html --outfile profiling_reports/ws_profile.html \
  --cpu-percent-threshold 1 \
  -- uvicorn app:application --host 0.0.0.0

# 3. Generate load (e.g., connect 1000 WebSocket clients)
# Use tools like locust, websocket-bench, or custom scripts

# 4. Stop application (Ctrl+C)
# Scalene generates report automatically

# 5. View report
open profiling_reports/ws_profile.html

# Or access via API
curl http://localhost:8000/api/profiling/reports/ws_profile.html > report.html
```

**Best Practices:**

1. **Profile Under Load**: Scalene is most useful under realistic load conditions
2. **Use Reduced Profile Mode**: Enable `--reduced-profile` for lower overhead
3. **Filter Output**: Use `--cpu-percent-threshold` to focus on hot spots
4. **Profile Specific Modules**: Use `--profile-only app/api/ws/` to focus on WebSocket code
5. **Combine with Metrics**: Cross-reference Scalene reports with Prometheus metrics
6. **Regular Profiling**: Run profiling sessions after major changes
7. **Save Reports**: Keep historical reports to track performance over time

**Common Bottlenecks Identified:**

- **Pydantic Validation**: Use `model_validate()` instead of manual dict conversion
- **JSON Serialization**: Consider `orjson` for faster JSON encoding
- **List Comprehensions in Broadcast**: Use async generators for large connection lists
- **Database Queries**: Missing indexes, N+1 queries
- **Sync Code in Async**: Blocking calls in async functions (use `run_in_executor`)

**Integration with Existing Monitoring:**

Scalene profiling complements existing monitoring tools:
- **Prometheus Metrics**: High-level trends (request rates, error rates)
- **Grafana Dashboards**: Real-time monitoring
- **Application Logs**: Error tracking and debugging
- **Scalene Reports**: Deep dive into performance bottlenecks

Use Prometheus to identify when performance degrades, then use Scalene to pinpoint the exact lines causing the issue.

**Troubleshooting:**

**Q: Scalene not found**
A: Install with `uv sync --group profiling` or `pip install scalene`

**Q: Permission denied on report file**
A: Ensure `PROFILING_OUTPUT_DIR` has write permissions

**Q: High overhead during profiling**
A: Use `--reduced-profile` mode or `--cpu-only` flag

**Q: Report shows no data**
A: Ensure application runs long enough to collect samples (at least 10-30 seconds)

**Q: Can't access /api/profiling endpoints**
A: Ensure profiling router is registered in `app/__init__.py`

**Configuration Files:**
- Profiling settings: `app/settings.py` (lines 112-115)
- Profiling utilities: `app/utils/profiling.py`
- Profiling API endpoints: `app/api/http/profiling.py`

### Common Patterns

**Adding HTTP endpoint:**
- Create router in `app/api/http/<module>.py`
- Define `router = APIRouter()` and endpoints
- Use `require_roles()` dependency for RBAC protection
- Will be auto-discovered by `collect_subrouters()`

**Example HTTP endpoint with RBAC:**
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
    """Create author - requires BOTH 'create-author' AND 'admin' roles."""
    pass

@router.get("/public")
async def public_endpoint():
    """Public endpoint - no require_roles() = no authentication required."""
    pass
```

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

**Available Keycloak Metrics:**

Keycloak provides primarily JVM and HTTP server metrics out of the box:

```
# HTTP Server Metrics (Available Now)
http_server_requests_seconds_count - Total HTTP requests
http_server_requests_seconds_sum - Total request duration
http_server_active_requests - Current active requests
http_server_connections_seconds_duration_sum - Connection duration

# JVM Metrics (Available Now)
jvm_memory_used_bytes{area="heap"} - JVM heap memory usage
jvm_memory_max_bytes{area="heap"} - Maximum heap memory
jvm_gc_pause_seconds_sum - Garbage collection pause time
jvm_gc_pause_seconds_count - GC pause count
jvm_threads_current - Current thread count
jvm_threads_peak - Peak thread count
jvm_threads_daemon - Daemon thread count

# Cache/Session Metrics (Available Now - via vendor metrics)
vendor_statistics_hits - Cache hit count by cache type
vendor_statistics_misses - Cache miss count
vendor_statistics_entries - Number of entries in cache
```

**Note on Authentication Metrics**: The dashboard includes panels for authentication-specific metrics (sessions, login success/failure). These metrics require additional setup:
- **Option 1**: Install [Keycloak Metrics SPI](https://github.com/aerogear/keycloak-metrics-spi) for detailed auth metrics
- **Option 2**: Enable Keycloak event listeners and export to Prometheus
- **Option 3**: Track authentication via FastAPI app's own metrics (already available in `fastapi-metrics` dashboard)

**Currently working panels**: JVM Heap Memory (panel 6), GC Pause Time (panel 7), Thread Count (panel 8). Panels 1-5 and 9 will show "No data" until authentication metrics are configured.

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

### Centralized Logging with Loki

**Overview:**
The application uses structured JSON logging with Grafana Loki for centralized log aggregation. All logs include contextual fields for correlation and debugging.

**Logging Stack:**
- **Structured Logging**: JSON format with contextual fields (`app/logging.py`)
- **Grafana Alloy**: Modern observability collector (replaced deprecated Promtail)
- **Loki**: Centralized log aggregation and storage
- **Grafana**: Log visualization and querying with LogQL

**Architecture:**
Logs flow: Application → stdout (JSON or human-readable) → Grafana Alloy → Loki → Grafana

We use **only Grafana Alloy** to send logs to Loki (no LokiHandler). This is the modern, recommended approach that avoids duplicate logs and complexity.

**Why Grafana Alloy?**
- Promtail was deprecated in February 2025 (EOL March 2026)
- Alloy is the unified observability agent supporting logs, metrics, and traces
- Uses modern "River" configuration language
- Better performance and more features than Promtail
- Alloy UI available at http://localhost:12345 for debugging

**Console Log Format:**
You can choose between JSON and human-readable console output:
- **JSON format**: Required for Grafana Alloy to parse logs correctly. Use in production.
- **Human-readable format** (default): Easier to read during development. Use locally.

Set via environment variable in `docker/.srv_env`:
```bash
# For development (human-readable) - DEFAULT
LOG_CONSOLE_FORMAT=human

# For production (JSON for Grafana Alloy)
LOG_CONSOLE_FORMAT=json
```

**Important Notes:**
- When `LOG_CONSOLE_FORMAT=human`, Alloy will fail to parse JSON fields from logs (acceptable for local dev without Grafana)
- When `LOG_CONSOLE_FORMAT=json`, all logs are properly parsed and indexed in Loki for Grafana dashboards
- Error log files (`logs/logging_errors.log`) are always in JSON format regardless of this setting
- For production deployments with Grafana monitoring, always use `LOG_CONSOLE_FORMAT=json`

**Available Log Fields:**
Structured logs automatically include:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `logger`: Python logger name (e.g., `app.auth`, `app.api.ws.consumers`)
- `message`: Log message
- `request_id`: Correlation ID from `X-Correlation-ID` header
- `user_id`: Authenticated user ID (if available)
- `endpoint`: HTTP endpoint path
- `method`: HTTP method (GET, POST, etc.)
- `status_code`: HTTP response status code
- `environment`: Deployment environment (dev, staging, production)
- `module`, `function`, `line`: Code location
- `exception`: Stack trace (for ERROR logs)

**Setting Log Context:**
Use `set_log_context()` to add custom fields to all logs in the current request:

```python
from app.logging import logger, set_log_context

# Add custom contextual fields
set_log_context(
    user_id="user123",
    operation="create_author",
    duration_ms=45
)

logger.info("Operation completed")  # Will include user_id, operation, duration_ms
```

**Grafana Dashboards:**
1. **Application Logs Dashboard** (`application-logs`):
   - Access at: http://localhost:3000/d/application-logs
   - Panels: Log volume, error logs, HTTP requests, WebSocket logs, rate limits, auth failures
   - Variables: service, level, user_id, endpoint, method, status_code

2. **FastAPI Metrics Dashboard** (`fastapi-metrics`):
   - Includes log panels for correlating logs with metrics
   - Recent errors, HTTP request logs, rate limit events

**Common LogQL Queries:**

```logql
# Recent error logs
{service="shell"} | json | level="ERROR"

# Logs for specific user
{service="shell"} | json | user_id="user123"

# HTTP requests to specific endpoint
{service="shell"} | json | endpoint=~"/api/authors.*"

# Failed authentication attempts
{service="shell"} | json | logger=~"app.auth.*" |~ "(?i)(error|failed|invalid)"

# Rate limit violations
{service="shell"} | json |~ "(?i)(rate limit|too many requests)"

# WebSocket logs
{service="shell"} | json | logger=~"app.api.ws.*"

# Logs by HTTP status code
{service="shell"} | json | status_code=~"5.."  # 5xx errors
{service="shell"} | json | status_code="429"   # Rate limit hits

# Slow operations (requires duration_ms field)
{service="shell"} | json | duration_ms > 100

# Permission denied events
{service="shell"} | json |~ "(?i)(permission denied|unauthorized|forbidden)"

# Correlate logs by request ID
{service="shell"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"
```

**Log Filtering Variables:**
Dashboards support filtering by:
- **service**: Docker service name (shell, hw-db, hw-keycloak)
- **level**: Log level (INFO, WARNING, ERROR)
- **user_id**: Filter by authenticated user (regex)
- **endpoint**: Filter by HTTP endpoint (regex)
- **method**: HTTP method (GET, POST, PUT, PATCH, DELETE)
- **status_code**: HTTP status code (regex)

**Correlation Between Logs and Metrics:**
Use `request_id` (correlation ID) to trace requests across:
1. HTTP/WebSocket logs
2. Database query logs
3. Authentication logs
4. Error logs
5. Prometheus metrics (via exemplars)

**Best Practices:**
1. **Always include context**: Use `set_log_context()` for request-specific fields
2. **Use structured fields**: Add fields as keyword arguments, not in message strings
3. **Log at appropriate levels**:
   - `DEBUG`: Detailed diagnostic info
   - `INFO`: Normal operations, request handling
   - `WARNING`: Unexpected but recoverable issues
   - `ERROR`: Errors requiring attention
4. **Include duration for performance tracking**: Add `duration_ms` field for slow operations
5. **Correlate with request_id**: Every log includes correlation ID for tracing

**Example Logging Pattern:**

```python
from app.logging import logger, set_log_context
import time

async def process_request(request: RequestModel, user_id: str) -> ResponseModel:
    # Set context for all logs in this request
    set_log_context(
        user_id=user_id,
        pkg_id=request.pkg_id,
        operation="process_request"
    )

    start_time = time.time()

    try:
        logger.info("Processing request")

        # Your logic here
        result = await do_work()

        duration_ms = (time.time() - start_time) * 1000
        logger.info("Request completed", extra={"duration_ms": duration_ms})

        return ResponseModel.success(...)

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed: {e}",
            exc_info=True,
            extra={"duration_ms": duration_ms}
        )
        raise
```

**Troubleshooting with Logs:**
1. Check application logs dashboard for recent errors
2. Filter by user_id or endpoint to narrow down issues
3. Use request_id to trace the full request lifecycle
4. Correlate error spikes in logs with metrics anomalies
5. Check authentication failures for security issues
6. Monitor rate limit violations for abuse patterns

**Configuration:**
- Logging config: `app/logging.py`
- Log level: Set via `LOG_LEVEL` environment variable
- Loki config: `docker/loki/loki-config.yml`
- Promtail config: `docker/promtail/promtail-config.yml`
- Loki URL: `LOKI_URL` in `app/settings.py` (default: http://loki:3100)

### Audit Logs Dashboard

**Overview:**
The Audit Logs Dashboard provides comprehensive visibility into user activities and security events by querying the `user_actions` table directly from PostgreSQL. This dashboard surfaces Keycloak usernames alongside detailed audit information.

**Accessing the Dashboard:**
- Dashboard location: `docker/grafana/provisioning/dashboards/audit-logs.json`
- Auto-provisioned on Grafana startup
- Access at: http://localhost:3000/d/audit-logs
- Datasource: PostgreSQL (configured in `docker/grafana/provisioning/datasources/prometheus.yml`)

**Dashboard Panels:**

1. **Audit Events Over Time** (Time Series)
   - Shows event volume grouped by outcome (success, error, permission_denied)
   - Color-coded: green (success), red (error), orange (permission_denied)
   - Stacked visualization with sum totals in legend
   - Query: Aggregates events by minute with outcome grouping

2. **Actions by Type** (Bar Chart)
   - Horizontal bar chart showing top 20 action types
   - Helps identify most common operations (GET, POST, WS:*, etc.)
   - Sorted by event count descending
   - Query: Groups by action_type with count

3. **Top Users by Activity** (Bar Chart)
   - Shows top 15 most active users by event count
   - Displays Keycloak usernames (from JWT `preferred_username` claim)
   - Useful for identifying power users or suspicious activity
   - Query: Groups by username with count

4. **Recent Audit Events** (Table)
   - Paginated table of last 100 events
   - Columns: timestamp, username, action_type, resource, outcome, response_status, duration_ms, ip_address
   - Color-coded cells:
     - outcome: green (success), red (error), orange (permission_denied)
     - response_status: green (<300), yellow (300-399), red (≥400)
     - duration_ms: green (<500ms), yellow (500-999ms), red (≥1000ms)
   - Sorted by timestamp descending

5. **Failed/Denied Actions** (Table)
   - Filtered view showing only errors and permission denials
   - Columns: timestamp, username, action_type, resource, outcome, error_message, ip_address
   - Critical for security monitoring and debugging
   - Limited to last 50 events
   - Query: WHERE outcome IN ('error', 'permission_denied')

6. **Average Response Time by Action** (Time Series)
   - Line chart showing avg duration_ms per action type over time
   - Only includes successful operations
   - Multiple series for different action types
   - Legend shows mean and max values
   - Helps identify performance regressions

**Dashboard Variables (Filters):**

All panels support dynamic filtering via these variables:

- **Username**: Multi-select dropdown of all usernames in audit log
  - Allows filtering by specific user(s)
  - "All" option to show all users

- **Action Type**: Multi-select filter for action types
  - Filter by GET, POST, WS:GET_AUTHORS, etc.
  - "All" option to show all action types

- **Outcome**: Multi-select filter for operation outcomes
  - Filter by success, error, or permission_denied
  - "All" option to show all outcomes

**Time Range:**
- Default: Last 6 hours
- Configurable via Grafana time picker (top-right)
- All queries use `$__timeFilter(timestamp)` for proper time filtering

**Database Schema:**

The dashboard queries the `user_actions` table with this structure:

```sql
Table: user_actions
- id (PRIMARY KEY)
- timestamp (indexed)
- user_id (indexed) - Keycloak user ID (sub claim)
- username (indexed) - Keycloak username (preferred_username claim)
- user_roles (JSON) - User roles at time of action
- action_type (indexed) - Type of action (GET, POST, WS:*, etc.)
- resource - Resource being accessed
- outcome (indexed) - success, error, permission_denied
- ip_address - Client IP address
- user_agent - Client user agent
- request_id (indexed) - Correlation ID for tracing
- request_data (JSON) - Request payload
- response_status - HTTP status code
- error_message - Error details (if applicable)
- duration_ms - Request duration in milliseconds
```

**Use Cases:**

1. **Security Monitoring:**
   - Identify unauthorized access attempts (permission_denied panel)
   - Track failed operations by user
   - Monitor IP addresses for suspicious patterns
   - Detect brute force attempts

2. **Compliance and Auditing:**
   - Export audit trails for compliance reports
   - Track who performed what actions and when
   - Correlate actions with outcomes
   - Maintain immutable audit log

3. **Performance Analysis:**
   - Identify slow operations by action type
   - Track response time trends
   - Find performance bottlenecks per user or action

4. **Troubleshooting:**
   - Filter by username to debug user-specific issues
   - Use request_id to trace requests across services
   - Correlate errors with specific actions and timestamps
   - Analyze error messages for root cause

**Example Queries:**

```sql
-- Find all failed logins for specific user
SELECT timestamp, action_type, outcome, error_message, ip_address
FROM user_actions
WHERE username = 'acika'
  AND outcome IN ('error', 'permission_denied')
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Identify most common errors
SELECT error_message, COUNT(*) as count
FROM user_actions
WHERE outcome = 'error'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY error_message
ORDER BY count DESC
LIMIT 10;

-- Track user activity patterns
SELECT
  DATE_TRUNC('hour', timestamp) AS hour,
  username,
  COUNT(*) AS events
FROM user_actions
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour, username
ORDER BY hour, events DESC;
```

**Integration with Other Dashboards:**

- **Application Logs**: Cross-reference request_id between audit logs and application logs
- **FastAPI Metrics**: Correlate audit events with HTTP request metrics
- **Keycloak Metrics**: Compare authentication events with user actions

**Best Practices:**

1. **Regular Review**: Monitor failed/denied actions panel daily for security anomalies
2. **Set Alerts**: Configure Grafana alerts for:
   - High rate of permission_denied events
   - Unusual user activity patterns
   - Error rate spikes
3. **Export Reports**: Use Grafana's export features for compliance reports
4. **Retention Policy**: Configure PostgreSQL retention for audit_logs table based on compliance needs
5. **Correlate with Logs**: Use request_id to trace between audit logs and application logs
