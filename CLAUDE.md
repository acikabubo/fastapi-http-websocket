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

### Documentation Requirements for GitHub Issues

**CRITICAL**: When creating GitHub issues, ALWAYS include documentation update requirements in the acceptance criteria.

#### Required Documentation Checks

For EVERY new GitHub issue, the acceptance criteria MUST include:

1. **Documentation Impact Assessment**:
   - [ ] Check if CLAUDE.md needs updates
   - [ ] Check if docs_site/ needs updates
   - [ ] Check if README.md needs updates
   - [ ] Check if inline code comments need updates

2. **Specific Documentation Tasks**:
   - List specific files that need documentation updates
   - Specify what sections need to be added/modified
   - Include examples of correct vs incorrect documentation

3. **Documentation Verification**:
   - [ ] All code examples in documentation reflect actual implementation
   - [ ] No outdated patterns or deprecated methods in docs
   - [ ] Architecture diagrams updated if structural changes made

#### Documentation Update Checklist by Change Type

**For API Changes** (new endpoints, modified signatures):
- [ ] Update `docs_site/api-reference/http-api.md` or `websocket-api.md`
- [ ] Update CLAUDE.md examples if pattern is reusable
- [ ] Add/update docstrings with examples

**For Architecture Changes** (new patterns, refactored components):
- [ ] Update `docs_site/architecture/overview.md`
- [ ] Update CLAUDE.md architecture section
- [ ] Update relevant design pattern guides
- [ ] Update Mermaid diagrams if flow changes

**For New Features** (handlers, middleware, utilities):
- [ ] Add guide to `docs_site/guides/`
- [ ] Update CLAUDE.md with usage examples
- [ ] Update quickstart if feature is core functionality
- [ ] Add configuration docs if feature is configurable

**For Bug Fixes** (especially for common issues):
- [ ] Update `docs_site/deployment/troubleshooting.md`
- [ ] Add warning/note to relevant guide sections
- [ ] Update FAQ if applicable

**For Testing Changes** (new patterns, centralized mocks):
- [ ] Update `docs_site/development/testing.md`
- [ ] Update CLAUDE.md testing section
- [ ] Document new test helpers/fixtures

**For Configuration Changes** (new settings, changed defaults):
- [ ] Update `docs_site/getting-started/configuration.md`
- [ ] Update `.env.*.example` files
- [ ] Add migration notes if breaking change

#### Issue Template Example

When creating issues, include this section in acceptance criteria:

```markdown
## Documentation Updates Required

- [ ] Update CLAUDE.md section: [specify section and what to change]
- [ ] Update docs_site file: [specify file path and changes]
- [ ] Add code examples showing correct usage
- [ ] Update architecture diagram: [if applicable]
- [ ] Add troubleshooting entry: [if common issue]

**Files to update**:
1. `CLAUDE.md` lines XXX-YYY: [description]
2. `docs_site/guides/feature-name.md`: [description]
3. `app/path/to/file.py`: [update docstrings with examples]
```

#### Common Documentation Mistakes to Avoid

❌ **Don't**:
- Create issues without documentation requirements
- Assume documentation is up-to-date after code changes
- Use outdated patterns in examples (e.g., Active Record vs Repository)
- Reference deleted files or deprecated methods
- Skip updating examples when refactoring

✅ **Do**:
- Always check if code examples match actual implementation
- Update documentation in the same commit/PR as code changes
- Verify all file paths and method signatures are current
- Include "before/after" examples for refactoring
- Cross-reference related documentation sections

#### Documentation Consistency Review

Before closing ANY issue:
1. Run grep to find all mentions of changed components in docs
2. Verify code examples actually work (copy-paste test)
3. Check that terminology is consistent across all docs
4. Ensure architecture diagrams reflect current structure

**Example verification commands**:
```bash
# Find all documentation references to changed component
grep -r "MyChangedClass" CLAUDE.md docs_site/

# Find potentially outdated CRUD patterns
grep -r "Model\.create\|Model\.get_list" docs_site/ CLAUDE.md

# Find references to deleted files
grep -r "connection_registry\|ws_clients" docs_site/ CLAUDE.md
```

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
# Run tests in parallel (default, uses pytest-xdist)
make test
# Or: uv run pytest -n auto tests

# Run tests sequentially (without parallelization)
make test-serial
# Or: uv run pytest tests

# Run a single test
uv run pytest tests/test_check.py::test_function_name

# Run tests with coverage
make test-coverage
# Or: uv run pytest --cov=app --cov-report=term-missing --cov-report=html tests

# Run tests in parallel with coverage
make test-coverage-parallel
# Or: uv run pytest -n auto --cov=app --cov-report=term-missing --cov-report=html tests

# Run load tests (high resource usage, marked with @pytest.mark.load)
uv run pytest -m load tests/load/ -v -s

# Run chaos engineering tests (failure scenarios, marked with @pytest.mark.chaos)
uv run pytest -m chaos tests/chaos/ -v -s

# Skip slow tests
uv run pytest -m "not load and not chaos"
```

#### Testing Infrastructure

**Parallel Test Execution (pytest-xdist):**
- Tests run in parallel by default using all available CPU cores (`-n auto`)
- 3-5x faster test execution compared to sequential runs
- Automatically distributes tests across workers
- Use `make test-serial` for debugging or when parallel execution causes issues

**Centralized Fixtures and Mocks:**
- Common fixtures defined in `tests/conftest.py`
- Fixture factories for creating test data: `create_author_fixture()`, `create_request_model_fixture()`, `create_response_model_fixture()`
- Reusable mock factories in `tests/mocks/`:
  - `repository_mocks.py` - Repository and CRUD operation mocks
  - `auth_mocks.py` - Keycloak, AuthBackend, UserModel, RBAC mocks
  - `redis_mocks.py` - Redis connection and rate limiter mocks
  - `keycloak_mocks.py` - KeycloakOpenID and KeycloakAdmin mocks
  - `websocket_mocks.py` - WebSocket connection, consumer, and manager mocks

**Load Testing:**
- WebSocket load tests in `tests/load/test_websocket_load.py`
- Test scenarios:
  - 100 concurrent connections (< 1s connection time, < 2s broadcast time)
  - 1000 concurrent connections (< 5s connection time, < 10s broadcast time)
  - Connection churn (500 rapid connect/disconnect cycles < 5s)
  - High-frequency broadcasts (> 500 messages/sec throughput)
  - Large message broadcasting (~100KB payloads)
  - Partial connection failures (20% failure rate resilience)
  - Concurrent broadcasts (10 simultaneous broadcasts)
- Run with: `pytest -m load tests/load/ -v -s`

**Chaos Engineering Tests:**
- Failure scenario testing in `tests/chaos/`
- Redis failure tests (`test_redis_failures.py`):
  - Redis unavailable (fail-open behavior)
  - Connection timeouts and errors
  - Partial operation failures (INCR succeeds, EXPIRE fails)
  - Intermittent failures and recovery
- Database failure tests (`test_database_failures.py`):
  - Database connection loss
  - Query timeouts
  - Transaction rollbacks
  - Connection pool exhaustion
  - Network partition scenarios
- Keycloak failure tests (`test_keycloak_failures.py`):
  - Keycloak server unavailable
  - Authentication errors
  - Token validation failures
  - Service degradation (partial failures)
  - Configuration errors
- Run with: `pytest -m chaos tests/chaos/ -v -s`

**Test Markers:**
- `@pytest.mark.integration` - Integration tests requiring external services (Keycloak, PostgreSQL, Redis)
- `@pytest.mark.load` - Load tests with high resource usage (skip by default)
- `@pytest.mark.chaos` - Chaos engineering tests simulating failures (skip by default)

**Example Usage:**
```python
# Using centralized fixtures
from tests.conftest import create_author_fixture, create_request_model_fixture

def test_my_feature():
    author = create_author_fixture(id=1, name="Test")
    request = create_request_model_fixture(pkg_id=1, data={"filter": "active"})

# Using centralized mocks
from tests.mocks.repository_mocks import create_mock_author_repository
from tests.mocks.redis_mocks import create_mock_redis_connection

async def test_with_mocks():
    mock_repo = create_mock_author_repository()
    mock_redis = create_mock_redis_connection()
    # Configure mock behavior as needed
    mock_repo.get_by_id.return_value = create_author_fixture(id=1)
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

# Find dead code (uses min_confidence from pyproject.toml)
make dead-code-scan
# Or: uvx vulture app/

# Fix dead code (remove unused imports and re-scan)
make dead-code-fix

# Spell checking
uvx typos

# Run all pre-commit hooks manually (recommended)
prek run --all-files

# Run specific hook
prek run ruff --all-files

# Run pre-push hooks (includes pytest-cov)
prek run --hook-stage pre-push --all-files
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

**WebSocket Protocol Documentation:**

For client developers implementing WebSocket clients, see the comprehensive protocol specification at `docs_site/guides/websocket-protocol.md`:

- Connection URL format and authentication
- Message format (JSON and Protobuf)
- Status codes (RSPCode) and error handling
- Available Package IDs (PkgID) with schemas
- Connection lifecycle and sequence diagrams
- Rate limiting and best practices
- Troubleshooting guide

This documentation is also available online at: https://acikabubo.github.io/fastapi-http-websocket/guides/websocket-protocol/

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
- Raises `AuthenticationError` (from `app/exceptions`) for authentication failures:
  - `token_expired`: JWT token has expired
  - `invalid_credentials`: Invalid Keycloak credentials
  - `token_decode_error`: Token decoding/validation failed

**WebSocket Authentication Security:**

⚠️ **IMPORTANT**: WebSocket connections authenticate using JWT tokens in query parameters due to browser WebSocket API limitations (cannot send custom headers during handshake). This has security implications:

**Security Risks:**
- Tokens appear in server access logs
- Tokens stored in browser history
- Potential proxy caching of URLs with tokens
- Risk of accidental token sharing via URLs

**Required Mitigations (Already Implemented):**
- ✅ Always use WSS (WebSocket over TLS) in production
- ✅ Tokens are short-lived (Keycloak default: 5 minutes)
- ✅ Referrer-Policy header prevents token leakage
- ✅ Security headers middleware (Content-Security-Policy allows `ws:` and `wss:`)
- ✅ Origin validation for CSRF protection (see below)

**WebSocket CSRF Protection:**

Cross-Site WebSocket Hijacking (CSWSH) is prevented by validating the `Origin` header before accepting connections.

**Configuration** (`app/settings.py`):
```python
# Allow all origins (development only)
ALLOWED_WS_ORIGINS: list[str] = ["*"]

# Production - specify exact allowed origins
ALLOWED_WS_ORIGINS: list[str] = [
    "https://app.example.com",
    "https://admin.example.com"
]
```

**How It Works** (`app/api/ws/websocket.py`):
1. Before accepting connection, `_is_origin_allowed()` checks the `Origin` header
2. If wildcard `*` is in allowed list → all origins permitted (dev mode)
3. If no `Origin` header → same-origin request, allowed
4. If origin matches allowed list → permitted
5. Otherwise → connection closed with `WS_1008_POLICY_VIOLATION`

**Attack Scenario Prevented:**
```
1. Attacker hosts malicious site: evil.com
2. User visits evil.com while authenticated to your app
3. evil.com attempts WebSocket to your server
4. Server checks Origin header: "https://evil.com"
5. Origin not in allowed list → connection rejected ✅
```

**Environment Configuration:**
```bash
# .env.dev.example - Allow all (development)
# ALLOWED_WS_ORIGINS=["*"]

# .env.production.example - Strict (production)
ALLOWED_WS_ORIGINS=["https://app.example.com", "https://admin.example.com"]
```

**Client-Side Best Practices:**

1. **Always Use WSS in Production:**
   ```javascript
   // ❌ Development only
   const ws = new WebSocket('ws://localhost:8000/web?Authorization=Bearer%20token');

   // ✅ Production - always use wss://
   const ws = new WebSocket('wss://api.example.com/web?Authorization=Bearer%20token');
   ```

2. **Encode Token Properly:**
   ```javascript
   const token = 'Bearer eyJhbGc...';
   const wsUrl = `wss://api.example.com/web?Authorization=${encodeURIComponent(token)}`;
   const ws = new WebSocket(wsUrl);
   ```

3. **Get Fresh Token Before Connecting:**
   ```javascript
   // Get fresh token immediately before WebSocket connection
   const token = await getAccessToken();
   const ws = new WebSocket(`wss://api.example.com/web?Authorization=${encodeURIComponent(token)}`);

   // Clear token from memory after connection
   token = null;
   ```

4. **Never Log Tokens:**
   ```javascript
   // ❌ Bad - logs token in URL
   console.log('Connecting to:', wsUrl);

   // ✅ Good - logs without token
   console.log('WebSocket connecting...');
   ```

5. **Implement Token Refresh for Long Connections:**
   ```javascript
   // Reconnect with new token before expiration
   setInterval(async () => {
       ws.close();
       const newToken = await refreshAccessToken();
       ws = new WebSocket(`wss://api.example.com/web?Authorization=${encodeURIComponent(newToken)}`);
   }, 4 * 60 * 1000); // Reconnect every 4 minutes (before 5-minute expiry)
   ```

**Server-Side Best Practices:**

1. **Sanitize Access Logs:**
   ```nginx
   # Nginx example - log without query parameters
   log_format websocket_safe '$remote_addr [$time_local] "$request_method $uri" $status';

   location /web {
       access_log /var/log/nginx/websocket.log websocket_safe;
   }
   ```

2. **Use Short Token TTL:**
   - Configure Keycloak access token lifespan to 5-15 minutes
   - Balance between security and user experience
   - Implement automatic reconnection logic in clients

**Why Query Parameters?**

WebSocket connections from JavaScript cannot send custom HTTP headers during the upgrade request:

```javascript
// ❌ Not supported by WebSocket API
const ws = new WebSocket('ws://localhost:8000/web', {
  headers: { 'Authorization': 'Bearer token' }
});

// ✅ Only option: query parameters
const ws = new WebSocket('ws://localhost:8000/web?Authorization=Bearer%20token');
```

**Alternative Approaches (Future Consideration):**

1. **WebSocket Subprotocols** (limited proxy support):
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/web', ['bearer', token]);
   ```

2. **Immediate Token Exchange** (send token in first message after connection):
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/web');
   ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }));
   ```

3. **Cookie-Based Authentication** (requires CORS configuration):
   ```javascript
   // Token in httpOnly cookie, no query params
   const ws = new WebSocket('ws://localhost:8000/web'); // Credentials sent automatically
   ```

**Exception Handling (`app/exceptions.py`):**
- Unified exception hierarchy extending `AppException` base class
- `AuthenticationError`: Authentication failures (HTTP 401, WebSocket RSPCode.PERMISSION_DENIED)
  - Used in `AuthBackend.authenticate()` for token validation failures
  - Automatically formatted as error envelopes by error handlers
  - Example usage:
    ```python
    from app.exceptions import AuthenticationError

    # In authentication code
    raise AuthenticationError(f"token_expired: {ex}")

    # In error handlers (automatic)
    # HTTP: Returns 401 with {"error": "authentication_failed", "message": "..."}
    # WebSocket: Returns ResponseModel with status_code=RSPCode.PERMISSION_DENIED
    ```
- Other exceptions: `ValidationError`, `PermissionDeniedError`, `NotFoundError`, `DatabaseError`, etc.
- See `app/utils/error_formatter.py` for error envelope mapping

**RBAC (`app/managers/rbac_manager.py`):**
- Singleton manager for role-based access control
- `check_ws_permission(pkg_id, user)`: Validates WebSocket permissions using roles from `pkg_router.permissions_registry`
- `require_roles(*roles)`: FastAPI dependency for HTTP endpoint permission checking
- Permissions defined in code via decorators (WebSocket: `@pkg_router.register(roles=[...])`, HTTP: `dependencies=[Depends(require_roles(...))]`)
- No external configuration file - all permissions co-located with handler code

**Keycloak Integration (`app/managers/keycloak_manager.py`):**
- Singleton managing `KeycloakAdmin` and `KeycloakOpenID` clients
- Configuration via environment variables (see `app/settings.py`)
- `login_async(username, password)` returns access token using native async methods
- Protected by circuit breaker pattern to prevent cascading failures

**Circuit Breaker Pattern (`app/managers/keycloak_manager.py`, `app/storage/redis.py`):**
- Resilience pattern that prevents cascading failures when external services (Keycloak, Redis) are unavailable
- Uses pybreaker library to implement fail-fast behavior during outages
- Configuration via `app/settings.py`:
  - `CIRCUIT_BREAKER_ENABLED`: Enable/disable circuit breakers globally (default: True)
  - `KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX`: Open Keycloak circuit after N failures (default: 5)
  - `KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT`: Keep circuit open for N seconds (default: 60)
  - `REDIS_CIRCUIT_BREAKER_FAIL_MAX`: Open Redis circuit after N failures (default: 3)
  - `REDIS_CIRCUIT_BREAKER_TIMEOUT`: Keep circuit open for N seconds (default: 30)
- Circuit breaker states:
  - `closed`: Normal operation, requests pass through
  - `open`: Service is failing, requests fail immediately (CircuitBreakerError)
  - `half_open`: Testing if service has recovered
- Protected operations:
  - Keycloak authentication: `KeycloakManager.login_async()`
  - Redis connections: `get_redis_connection(db)`
- Prometheus metrics tracked:
  - `circuit_breaker_state{service}`: Current state (0=closed, 1=open, 2=half_open)
  - `circuit_breaker_state_changes_total{service, from_state, to_state}`: State transition counts
  - `circuit_breaker_failures_total{service}`: Total failures detected
- Listener classes log state changes and update metrics:
  - `KeycloakCircuitBreakerListener`: Tracks Keycloak circuit breaker events
  - `RedisCircuitBreakerListener`: Tracks Redis circuit breaker events
- Benefits:
  - Prevents resource exhaustion during outages (don't wait for timeouts)
  - Allows services to recover without continued load
  - Provides clear visibility into service health via metrics

**JWT Token Claim Caching (`app/utils/token_cache.py`):**
- Redis-based caching of decoded JWT token claims to reduce CPU overhead
- Automatically caches tokens after successful decode with TTL matching token expiration
- Uses SHA-256 hash of token as cache key (full token never stored in Redis)
- Cache expires 30 seconds before token expiration to prevent stale data
- Fail-open behavior: falls back to token decode if Redis unavailable
- Performance impact:
  - 90% reduction in token decode CPU time (typical workload)
  - 85-95% cache hit rate for repeated requests with same token
  - Reduces Keycloak validation load by 85-95%
- Functions:
  - `get_cached_token_claims(token)`: Returns cached claims or None
  - `cache_token_claims(token, claims, ttl=None)`: Stores claims with auto-calculated TTL
  - `invalidate_token_cache(token)`: Explicitly removes token from cache
- Security considerations:
  - Token hash (SHA-256) used as cache key, not full token
  - Short TTL limits exposure window (expires with token)
  - No PII stored in cache keys
  - Fail-open ensures availability over cache consistency
- Prometheus metrics:
  - `token_cache_hits_total`: Total cache hits
  - `token_cache_misses_total`: Total cache misses
  - Cache hit rate dashboard panel available in Grafana
- Integrated into `AuthBackend.authenticate()` for all HTTP and WebSocket requests

**Audit Logger (`app/utils/audit_logger.py`):**
- Async queue-based audit log writer for non-blocking audit logging
- Processes audit log entries in background without blocking HTTP requests
- Queue-based architecture:
  - `asyncio.Queue` with configurable max size (`AUDIT_QUEUE_MAX_SIZE`)
  - Batch processing: writes multiple logs per database transaction
  - Backpressure mechanism for queue overflow handling
- Batch writer functionality:
  - Groups audit logs into batches (`AUDIT_BATCH_SIZE`)
  - Timeout-based flushing (`AUDIT_BATCH_TIMEOUT`) for partial batches
  - Single database transaction per batch (efficient bulk insert)
- Backpressure mechanism:
  - When queue is full, waits up to `AUDIT_QUEUE_TIMEOUT` seconds for space
  - If timeout=0, drops immediately (original behavior, no backpressure)
  - If timeout>0, applies backpressure before dropping
  - Logs are only dropped after timeout expires (compliance-friendly)
  - Dropped logs tracked via `audit_logs_dropped_total` metric
- Key functions:
  - `log_user_action()`: Async function to queue audit log entry with backpressure
  - `audit_log_worker()`: Background worker that processes queue in batches
  - `flush_audit_queue()`: Gracefully flushes remaining logs on shutdown
- Prometheus metrics:
  - `audit_logs_total`: Total audit logs queued
  - `audit_logs_written_total`: Successfully written to database
  - `audit_logs_dropped_total`: Dropped due to queue overflow (after backpressure timeout)
  - `audit_queue_size`: Current queue size
  - `audit_batch_size`: Logs per batch
- Prometheus alerts (in `docker/prometheus/alerts.yml`):
  - `AuditLogDropping`: Logs being dropped at >1/s rate (critical)
  - `HighAuditLogDropRate`: Drop rate >1% of total logs (warning)
  - `SustainedAuditQueueOverflow`: Drop rate >1% for 5+ minutes (critical, compliance risk)
  - `AuditQueueNearCapacity`: Queue usage >80% (warning)
- Configuration (`app/settings.py`):
  - `AUDIT_QUEUE_MAX_SIZE`: Maximum queue size (default: 10000)
  - `AUDIT_BATCH_SIZE`: Logs per batch write (default: 100)
  - `AUDIT_BATCH_TIMEOUT`: Seconds to wait for batch fill (default: 1.0)
  - `AUDIT_QUEUE_TIMEOUT`: Backpressure timeout in seconds (default: 1.0, set to 0 to disable)
- Prevents request latency from database writes
- Critical for high-throughput APIs with compliance requirements

**Error Handler (`app/utils/error_handler.py`):**
- Centralized error handling utilities for HTTP and WebSocket endpoints
- `handle_http_errors` decorator: Unified error handling for HTTP endpoints
  - Catches common exceptions (ValueError, KeyError, NotFoundError)
  - Converts to appropriate HTTP status codes (400, 404, 500)
  - Returns consistent error response format
  - Logs errors with full stack trace
  - Example usage:
    ```python
    @router.get("/authors")
    @handle_http_errors
    async def get_authors():
        # Exceptions automatically handled
        pass
    ```
- Error response formatting:
  - Standardized error structure for client consumption
  - Includes error type, message, and optional details
  - Integrates with FastAPI exception handlers
- Used across all HTTP endpoints for consistent error handling
- Reduces boilerplate try/except blocks in endpoint code
- See also: `app/utils/error_formatter.py` for error envelope mapping

**File I/O Utilities (`app/utils/file_io.py`):**
- JSON schema loading from files for WebSocket handler validation
- `load_json_schema(file_path)`: Loads and validates JSON schema files
- Used by WebSocket handlers for request data validation
- Caches loaded schemas for performance
- Validates schema format on load (catches schema errors early)
- Internal utility primarily for WebSocket handler registration:
  ```python
  from app.utils.file_io import load_json_schema

  schema = load_json_schema("schemas/author.json")

  @pkg_router.register(
      PkgID.CREATE_AUTHOR,
      json_schema=schema  # Loaded from file
  )
  async def create_author_handler(request: RequestModel):
      ...
  ```

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
  - Fail mode configurable via `RATE_LIMIT_FAIL_MODE` setting:
    - "open" (default): Allows requests when Redis is unavailable
    - "closed": Denies requests when Redis is unavailable
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
  - `RATE_LIMIT_FAIL_MODE`: Fail mode when Redis unavailable - "open" or "closed" (default: "open")
  - `WS_MAX_CONNECTIONS_PER_USER`: Max concurrent WebSocket connections (default: 5)
  - `WS_MESSAGE_RATE_LIMIT`: WebSocket messages per minute (default: 100)

**Redis Connection Pool Monitoring (`app/storage/redis.py`, `app/tasks/redis_pool_metrics_task.py`):**
- Real-time monitoring of Redis connection pool health and usage
- Background task collects pool metrics every 15 seconds for all database pools
- Prometheus metrics tracked:
  - `redis_pool_max_connections`: Maximum connections allowed per pool
  - `redis_pool_connections_in_use`: Current active connections (checked out)
  - `redis_pool_connections_available`: Idle connections ready for use
  - `redis_pool_connections_created_total`: Total connections created (cumulative)
  - `redis_pool_info`: Pool configuration metadata (host, port, timeouts)
- Enables detection of:
  - Pool exhaustion (all connections in use)
  - Connection leaks (connections not returned to pool)
  - Under-provisioned pools (frequent exhaustion)
  - Over-provisioned pools (many idle connections)
- Prometheus alerts configured in `docker/prometheus/alerts.yml`:
  - `RedisPoolNearExhaustion`: Pool usage > 80% for 3 minutes (warning)
  - `RedisPoolExhausted`: Pool usage ≥ 95% for 1 minute (critical)
  - `RedisPoolNoAvailableConnections`: Zero available connections for 1 minute (critical)
- Grafana dashboard panels (IDs 25-27):
  - Panel 25: Connections in use vs max connections (timeseries with thresholds)
  - Panel 26: Available connections over time (timeseries)
  - Panel 27: Pool usage percentage gauge (0-100% with color thresholds)
- Pool configuration via `app/settings.py`:
  - `REDIS_MAX_CONNECTIONS`: Max connections per pool (default: 50)
  - `REDIS_SOCKET_TIMEOUT`: Socket operation timeout (default: 5s)
  - `REDIS_CONNECT_TIMEOUT`: Connection establishment timeout (default: 5s)
  - `REDIS_HEALTH_CHECK_INTERVAL`: Health check frequency (default: 30s)
  - `MAIN_REDIS_DB`: Primary database index (default: 1)
  - `AUTH_REDIS_DB`: Authentication database index (default: 10)
- Use cases:
  - Capacity planning: Determine optimal `REDIS_MAX_CONNECTIONS` setting
  - Incident response: Identify pool exhaustion during outages
  - Performance tuning: Detect connection bottlenecks
  - Leak detection: Spot connections not being properly released

**Database Connection Pool Monitoring (`app/storage/db.py`, `app/tasks/db_pool_metrics_task.py`):**
- Real-time monitoring of PostgreSQL connection pool health and usage
- Background task collects pool metrics every 15 seconds
- Prometheus metrics tracked:
  - `db_pool_max_connections`: Maximum connections allowed (pool_size + max_overflow)
  - `db_pool_connections_in_use`: Current active connections (checked out)
  - `db_pool_connections_available`: Idle connections ready for use
  - `db_pool_connections_created_total`: Total connections created (cumulative)
  - `db_pool_overflow_count`: Overflow connections beyond pool_size
  - `db_pool_info`: Pool configuration metadata (pool_size, max_overflow, timeout)
- Enables detection of:
  - Pool exhaustion (all connections in use)
  - Connection leaks (connections not returned to pool)
  - Under-provisioned pools (frequent overflow usage)
  - Over-provisioned pools (many idle connections)
- Prometheus alerts configured in `docker/prometheus/alerts.yml`:
  - `DatabasePoolNearExhaustion`: Pool usage > 80% for 3 minutes (warning)
  - `DatabasePoolExhausted`: Pool usage ≥ 95% for 1 minute (critical)
  - `DatabasePoolNoAvailableConnections`: Zero available connections for 1 minute (critical)
- Grafana dashboard panels (IDs 31-33):
  - Panel 31: Connections in use vs max connections (timeseries with thresholds)
  - Panel 32: Available connections over time (timeseries)
  - Panel 33: Pool usage percentage gauge (0-100% with color thresholds)
- Pool configuration via SQLAlchemy engine settings:
  - Pool size: Configured in `app/storage/db.py` via engine creation
  - Max overflow: Additional connections beyond pool size
  - Pool timeout: Wait time before raising exception when pool exhausted
- Use cases:
  - Capacity planning: Determine optimal pool_size and max_overflow settings
  - Incident response: Identify pool exhaustion during high traffic
  - Performance tuning: Detect connection bottlenecks
  - Leak detection: Spot connections not being properly closed

**Prometheus Metrics (`app/utils/metrics/`, `app/middlewares/prometheus.py`):**
- Comprehensive metrics collection for monitoring and observability organized by subsystem
- Metrics are split into logical modules for better maintainability:
  - `app/utils/metrics/http.py`: HTTP request metrics
  - `app/utils/metrics/websocket.py`: WebSocket connection and message metrics
  - `app/utils/metrics/database.py`: Database query and connection metrics
  - `app/utils/metrics/redis.py`: Redis operations and pool metrics
  - `app/utils/metrics/auth.py`: Authentication and Keycloak metrics
  - `app/utils/metrics/audit.py`: Audit logging metrics
  - `app/utils/metrics/__init__.py`: Re-exports all metrics for backward compatibility
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

**Security Middlewares (`app/middlewares/security_headers.py`, `app/middlewares/request_size_limit.py`):**
- `SecurityHeadersMiddleware`: Adds security headers to all HTTP responses
  - `X-Frame-Options: DENY` - Prevents clickjacking attacks
  - `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
  - `X-XSS-Protection: 1; mode=block` - Enables XSS filter in older browsers
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` - Enforces HTTPS
  - `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()` - Disables browser features
  - `Content-Security-Policy` - Prevents XSS and injection attacks
    - `default-src 'self'` - Only allow resources from same origin
    - `script-src 'self'` - Block inline scripts and eval()
    - `style-src 'self' 'unsafe-inline'` - Allow inline styles for API docs
    - `img-src 'self' data:` - Allow images from same origin and data URIs
    - `font-src 'self'` - Only load fonts from same origin
    - `connect-src 'self' ws: wss:` - Allow WebSocket connections (critical for /web endpoint)
    - `frame-ancestors 'none'` - Prevent clickjacking (reinforces X-Frame-Options)
    - `base-uri 'self'` - Restrict base tag to same origin
    - `form-action 'self'` - Only submit forms to same origin
    - `upgrade-insecure-requests` - Automatically upgrade HTTP to HTTPS
- `RequestSizeLimitMiddleware`: Protects against large payload attacks
  - Checks `Content-Length` header before processing request
  - Returns 413 Payload Too Large if size exceeds limit
  - Default limit: 1MB (configurable via `MAX_REQUEST_BODY_SIZE`)
- `TrustedHostMiddleware`: Validates Host header against allowed hosts
  - Prevents Host header injection attacks
  - Configured via `ALLOWED_HOSTS` setting (default: `["*"]` for development)
  - Set to specific domains in production: `["example.com", "*.example.com"]`
- Configuration in `app/settings.py`:
  - `ALLOWED_HOSTS`: List of allowed host values (default: `["*"]`)
  - `MAX_REQUEST_BODY_SIZE`: Maximum request body size in bytes (default: 1MB)
  - `TRUSTED_PROXIES`: List of trusted proxy IP addresses/networks for X-Forwarded-For validation

**IP Address Spoofing Protection (`app/utils/ip_utils.py`):**
- `get_client_ip(request)`: Safely extracts client IP with spoofing protection
  - Validates X-Forwarded-For header against trusted proxy list
  - Only trusts X-Forwarded-For from configured `TRUSTED_PROXIES`
  - Supports IP addresses and CIDR notation (`10.0.0.0/8`)
  - Logs warnings for untrusted X-Forwarded-For attempts
- `is_trusted_proxy(ip)`: Checks if IP belongs to trusted proxy
- Used by:
  - Rate limiting middleware (for IP-based rate limits)
  - Audit logging (for accurate IP tracking in audit logs)
- Default trusted proxies: Docker networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)

**Audit Middleware (`app/middlewares/audit_middleware.py`):**
- Intercepts HTTP requests and responses for comprehensive audit logging
- Captures request data, response status, duration, and user context
- Sends audit log entries to async queue for non-blocking processing
- Extracts user information from authenticated requests (user ID, username, roles)
- Tracks IP addresses using IP spoofing protection (`get_client_ip()`)
- Records request/response metadata:
  - Action type (HTTP method)
  - Resource (request path)
  - Outcome (success/error/permission_denied)
  - Duration in milliseconds
  - Error messages for failed requests
- Integrated with correlation ID for request tracing
- Queue-based processing via `audit_logger.py` prevents blocking request handling
- Used for compliance, security monitoring, and troubleshooting

**Correlation ID Middleware (`app/middlewares/correlation_id.py`):**
- Adds X-Correlation-ID header to all requests and responses for distributed tracing
- Generates UUID v4 if client doesn't provide correlation ID
- Propagates correlation ID through entire request lifecycle:
  - HTTP requests
  - WebSocket messages
  - Database queries
  - Audit logs
  - Application logs
- Enables tracing requests across services and log aggregation systems
- Essential for debugging and root cause analysis in distributed systems
- Correlation ID automatically included in structured logs via `logging_context.py`

**Logging Context Middleware (`app/middlewares/logging_context.py`):**
- Sets logging context from request data for structured logging
- Enriches all logs within request scope with contextual fields:
  - `request_id`: Correlation ID from X-Correlation-ID header
  - `user_id`: Authenticated user ID (if available)
  - `endpoint`: HTTP endpoint path
  - `method`: HTTP method (GET, POST, etc.)
  - `ip_address`: Client IP (with spoofing protection)
- Uses contextvars for thread-safe context propagation
- Automatically applied by `set_log_context()` function in `app/logging.py`
- Integrates with Grafana Loki for log querying by correlation ID, user, endpoint
- Example log output:
  ```json
  {
    "timestamp": "2025-01-12T14:30:00Z",
    "level": "INFO",
    "message": "Processing request",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "abc-123-def",
    "endpoint": "/api/authors",
    "method": "POST"
  }
  ```

### Directory Structure

- `app/__init__.py`: Application factory with startup/shutdown handlers
- `app/api/http/`: HTTP endpoint routers (auto-discovered by `collect_subrouters()`)
- `app/api/ws/handlers/`: WebSocket handlers registered with `@pkg_router.register()`
- `app/api/ws/consumers/`: WebSocket endpoint classes (e.g., `Web`)
- `app/api/ws/constants.py`: `PkgID` and `RSPCode` enums
- `app/managers/`: Singleton managers (RBAC, Keycloak, WebSocket connections)
- `app/middlewares/`: Custom middleware (`RateLimitMiddleware`, `PrometheusMiddleware`)
- `app/models/`: SQLModel database models
- `app/utils/`: Utility modules (`rate_limiter.py`, `metrics/`)
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

**Settings (`app/settings/`)**

Settings are organized into a modular package structure with nested configuration groups. The settings support **two access patterns**:

1. **Flat access** (original, backward compatible): `app_settings.DB_HOST`
2. **Nested access** (new, recommended): `app_settings.database.HOST`

**Settings Structure:**
- `app/settings/__init__.py` - Main Settings class with flat env vars
- `app/settings/models.py` - Nested BaseModel classes for grouping

**Nested Configuration Groups:**
```python
from app.settings import app_settings

# Database settings
app_settings.database.USER          # or app_settings.DB_USER
app_settings.database.PASSWORD      # or app_settings.DB_PASSWORD
app_settings.database.HOST          # or app_settings.DB_HOST
app_settings.database.url           # Computed property (DATABASE_URL)

# Redis settings
app_settings.redis.IP               # or app_settings.REDIS_IP
app_settings.redis.PORT             # or app_settings.REDIS_PORT
app_settings.redis.MAIN_DB          # or app_settings.MAIN_REDIS_DB

# Keycloak settings
app_settings.keycloak.REALM         # or app_settings.KEYCLOAK_REALM
app_settings.keycloak.CLIENT_ID     # or app_settings.KEYCLOAK_CLIENT_ID

# Security settings (with nested rate_limit)
app_settings.security.ALLOWED_HOSTS
app_settings.security.rate_limit.ENABLED     # or app_settings.RATE_LIMIT_ENABLED
app_settings.security.rate_limit.PER_MINUTE  # or app_settings.RATE_LIMIT_PER_MINUTE

# WebSocket settings
app_settings.websocket.MAX_CONNECTIONS_PER_USER  # or app_settings.WS_MAX_CONNECTIONS_PER_USER
app_settings.websocket.ALLOWED_ORIGINS           # or app_settings.ALLOWED_WS_ORIGINS

# Logging settings (with nested audit)
app_settings.logging.LEVEL                     # or app_settings.LOG_LEVEL
app_settings.logging.CONSOLE_FORMAT            # or app_settings.LOG_CONSOLE_FORMAT
app_settings.logging.audit.ENABLED             # or app_settings.AUDIT_LOG_ENABLED
app_settings.logging.audit.QUEUE_MAX_SIZE      # or app_settings.AUDIT_QUEUE_MAX_SIZE

# Circuit breaker settings (with nested keycloak/redis)
app_settings.circuit_breaker.ENABLED
app_settings.circuit_breaker.keycloak.FAIL_MAX  # or app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX
app_settings.circuit_breaker.redis.TIMEOUT      # or app_settings.REDIS_CIRCUIT_BREAKER_TIMEOUT

# Profiling settings
app_settings.profiling.ENABLED          # or app_settings.PROFILING_ENABLED
app_settings.profiling.OUTPUT_DIR       # or app_settings.PROFILING_OUTPUT_DIR
```

**Environment Variables:**

All settings are loaded from environment variables with their original flat names:
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `REDIS_IP`, `REDIS_PORT`, `MAIN_REDIS_DB`, `AUTH_REDIS_DB`
- `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE`
- `WS_MAX_CONNECTIONS_PER_USER`, `WS_MESSAGE_RATE_LIMIT`
- `LOG_LEVEL`, `LOG_CONSOLE_FORMAT`
- `AUDIT_LOG_ENABLED`, `AUDIT_QUEUE_MAX_SIZE`
- `PROFILING_ENABLED`, `PROFILING_OUTPUT_DIR`

**No breaking changes** - all existing env var names are preserved!

**Benefits of Nested Access:**
- Better IDE autocomplete (`app_settings.database.` shows all database settings)
- Logical grouping (related settings together)
- Type hints for nested models
- Backward compatible (flat access still works)

**Adding New Settings:**
1. Add env var to `Settings` class in `app/settings/__init__.py` (flat field)
2. Add field to appropriate nested model in `app/settings/models.py`
3. Add mapping in corresponding `@property` method
4. Both access patterns will work automatically

**Environment-Specific Configuration**

The application supports multiple deployment environments with automatic configuration defaults. The `ENV` setting (from `app.settings.Environment` enum) determines environment-specific behavior:

**Supported Environments:**
- `dev` - Development environment (default)
- `staging` - Staging/testing environment
- `production` - Production environment

**Environment Configuration Files:**
- `.env.dev.example` - Development environment template
- `.env.staging.example` - Staging environment template
- `.env.production.example` - Production environment template

**Environment-Specific Defaults:**

| Setting | DEV | STAGING | PRODUCTION |
|---------|-----|---------|------------|
| `DEBUG_AUTH` | Allowed | Disallowed | Disallowed (enforced) |
| `LOG_LEVEL` | DEBUG | INFO | WARNING |
| `LOG_CONSOLE_FORMAT` | human | json | json |
| `RATE_LIMIT_FAIL_MODE` | open | open | closed |
| `PROFILING_ENABLED` | true | true | false |

**Setting the Environment:**

```bash
# Development (default)
ENV=dev

# Staging
ENV=staging

# Production
ENV=production
```

**Environment-Specific Behavior:**

1. **Production Environment** (`ENV=production`):
   - `DEBUG_AUTH` is automatically disabled (cannot be enabled)
   - Rate limiting fails closed (denies requests when Redis unavailable)
   - JSON logging for Grafana Alloy/Loki integration
   - WARNING log level (minimal logging)
   - Profiling disabled by default

2. **Staging Environment** (`ENV=staging`):
   - Production-like settings with some debugging enabled
   - INFO log level for moderate logging
   - JSON logging for log aggregation
   - Profiling enabled for performance testing

3. **Development Environment** (`ENV=dev`):
   - Permissive settings for local development
   - DEBUG log level for verbose logging
   - Human-readable console logging
   - Profiling enabled for local testing

**Helper Properties:**

The `Settings` class provides helper properties for environment checks:

```python
from app.settings import app_settings

if app_settings.is_production:
    # Production-only logic
    pass

if app_settings.is_staging:
    # Staging-only logic
    pass

if app_settings.is_development:
    # Development-only logic
    pass
```

**Configuration Priority:**

Environment-specific defaults are applied **only if** the setting is not explicitly provided via environment variables. This allows overriding defaults when needed:

```bash
# Override production default (WARNING) with INFO
ENV=production
LOG_LEVEL=INFO  # Explicitly set, overrides production default
```

**Example Usage:**

```bash
# Development
cp .env.dev.example .env
# Edit .env with your local Keycloak credentials
ENV=dev

# Staging deployment
cp .env.staging.example .env
# Update all CHANGE_ME values
ENV=staging

# Production deployment
cp .env.production.example .env
# CRITICAL: Review and update ALL settings
ENV=production
```

**Startup Validation (`app/startup_validation.py`)**

The application implements **fail-fast validation** to ensure it does not start with invalid configuration or unavailable dependencies. All validations run during application startup, before accepting any requests.

**Validation Functions:**

1. **`validate_settings()`** - Validates required environment variables:
   - Keycloak settings: `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`, `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
   - Database settings: `DB_USER`, `DB_PASSWORD`
   - Validates `DEBUG_AUTH` is disabled in production
   - Validates `DEBUG_AUTH` credentials if enabled

2. **`validate_database_connection()`** - Tests database connectivity:
   - Attempts connection to PostgreSQL
   - Executes simple health check query (`SELECT 1`)
   - Raises `StartupValidationError` if connection fails

3. **`validate_redis_connection()`** - Tests Redis connectivity:
   - Attempts connection to Redis
   - Executes PING command to verify connection
   - Raises `StartupValidationError` if connection fails

4. **`run_all_validations()`** - Orchestrates all validation checks:
   - Runs settings validation first (no external dependencies)
   - Then validates database connection
   - Finally validates Redis connection
   - Application will not start if any validation fails

**Integration with Lifespan:**

Startup validation runs automatically in the `lifespan()` context manager before any other initialization:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Run startup validations (fail-fast if configuration is invalid)
    from app.startup_validation import run_all_validations
    await run_all_validations()

    # Continue with normal startup (database, background tasks, etc.)
    ...
```

**Error Messages:**

When validation fails, the application logs a clear error message and raises `StartupValidationError`:

```
ERROR - Startup validation failed: KEYCLOAK_REALM environment variable is required
ERROR - Application will not start. Fix the configuration errors and try again.
```

**Benefits:**

- ✅ **Fail-fast principle**: Application won't start with invalid configuration
- ✅ **Clear error messages**: Actionable feedback for missing/invalid settings
- ✅ **Early detection**: Catch configuration errors before accepting requests
- ✅ **Service availability checks**: Verify database and Redis are reachable
- ✅ **Production safety**: Prevents DEBUG_AUTH from being enabled in production

**Testing:**

Comprehensive tests in [tests/test_startup_validation.py](tests/test_startup_validation.py) cover:
- Missing environment variables
- Invalid configuration (e.g., DEBUG_AUTH in production)
- Database connection failures
- Redis connection failures
- Validation orchestration

### Pre-commit Hooks

**Hook Manager**: We use **prek** (Rust-based, 3-10x faster than pre-commit) for running pre-commit hooks.

All commits must pass:
- **ruff**: Linting and formatting with auto-fix (79 char line length, removes unused imports)
- **mypy**: Strict type checking
- **interrogate**: ≥80% docstring coverage
- **typos**: Spell checking
- **bandit**: Security scanning (low severity threshold `-lll`)
- **skjold**: Dependency vulnerability checks
- **vulture**: Dead code detection (100% confidence, runs on `git push` only)
- **pytest-cov**: Code coverage checker (≥80% coverage, runs on `git push` only)

**Installing Hooks:**

```bash
# Install prek (recommended - 3-10x faster)
uv tool install prek
prek install -f
prek install --hook-type pre-push -f

# Alternative: Use pre-commit (slower but more mature)
uvx pre-commit install
uvx pre-commit install --hook-type pre-push
```

**Rollback to pre-commit (if needed):**

```bash
prek uninstall
prek uninstall --hook-type pre-push
uvx pre-commit install
uvx pre-commit install --hook-type pre-push
```

**Why prek?**
- 3-10x faster hook execution (typical: 2s vs 10-20s)
- 50% less disk space usage
- Drop-in replacement (uses same `.pre-commit-config.yaml`)
- Automatic stashing of unstaged changes
- Used by CPython, Apache Airflow, FastAPI, Home Assistant

**Note**: Both prek and pre-commit use the same `.pre-commit-config.yaml` file, so switching between them is seamless.

**Running Tests with Coverage:**

```bash
# Run tests with coverage report
uv run pytest --cov=app --cov-report=term-missing

# Run tests with HTML coverage report
uv run pytest --cov=app --cov-report=html

# View HTML coverage report
open htmlcov/index.html
```

**Coverage Configuration:**

Coverage settings are in `pyproject.toml`:
- Minimum coverage threshold: 80%
- Omitted files: `__init__.py`, `__main__.py`, tests, logging, routing, settings
- Excluded lines: `pragma: no cover`, imports, pass statements

**Note**: The coverage hook only runs on `git push` (not on every commit) to avoid slowing down the development workflow. This allows you to commit work-in-progress code while ensuring coverage is checked before pushing to remote.

### Dead Code Detection

The project uses **vulture** (dead code detector) and **ruff** (with auto-fix) to keep the codebase clean and maintainable.

**Pre-commit Hooks:**
- **ruff**: Automatically fixes lint violations including unused imports (F401) and unused variables (F841) on every commit
- **vulture**: Detects unused functions, classes, and variables on `git push` (100% confidence)

**Manual Commands:**

```bash
# Scan for dead code (uses min_confidence from pyproject.toml)
make dead-code-scan
# Or: uvx vulture app/

# Fix dead code (remove unused imports + re-scan)
make dead-code-fix
```

**Configuration (`pyproject.toml`):**

```toml
[tool.vulture]
min_confidence = 100  # Only report absolutely certain dead code
paths = ["app"]
exclude = [
    "app/storage/migrations/*",
    "app/schemas/proto/*",  # Generated protobuf code
]
ignore_names = [
    "lifespan",  # FastAPI lifespan context manager
    "on_connect",  # WebSocket lifecycle methods
    "on_disconnect",
    "on_receive",
    "dispatch",  # Middleware dispatch methods
    "*Model",  # SQLModel classes (may appear unused)
]
ignore_decorators = [
    "@router.*",  # FastAPI route decorators
    "@pkg_router.register",  # WebSocket handler decorators
]
```

**Vulture Confidence Levels:**
- **100%**: Definitely dead (unused imports, unreachable code) - ruff auto-fixes unused imports (F401), vulture detects other dead code
- **80-99%**: Very likely dead (unused functions) - not reported with 100% threshold
- **60-79%**: Probably dead (may be false positive) - not reported with 100% threshold
- **<60%**: Uncertain (many false positives) - not reported with 100% threshold

**Note**: With `min_confidence = 100`, vulture only reports absolutely certain dead code. Ruff's auto-fix handles unused imports, so vulture primarily catches unreachable code and unused function definitions.

**Handling False Positives:**

```python
# Option 1: Add to vulture whitelist in pyproject.toml
# See ignore_names, ignore_decorators above

# Option 2: Add # noqa: vulture comment
def used_in_tests_only():  # noqa: vulture
    pass

# Option 3: Reference in __all__ or import in __init__.py
__all__ = ["may_be_used_dynamically"]
```

**Workflow:**
1. Developer commits code → ruff auto-fixes lint violations (including unused imports)
2. Developer pushes code → vulture checks for unused functions/classes (100% confidence)
3. If dead code found → fix and commit → push succeeds

**Benefits:**
- ✅ Cleaner codebase with less noise
- ✅ Easier navigation and code reviews
- ✅ Faster imports and smaller bundles
- ✅ Safe refactoring (unused code caught early)
- ✅ Automated enforcement via pre-commit hooks

### Code Style Requirements

- **Line length**: 79 characters (enforced by ruff)
- **Type hints**: Required on all functions (mypy --strict)
- **Docstrings**: Required on all public functions, classes, and methods (80% coverage minimum)
- **Formatting**: Double quotes, 4-space indentation
- **Unused code**: Will be caught by vulture (see `pyproject.toml` for ignored names)

### Docstring Style Guide

All public functions, classes, and methods must have comprehensive docstrings following **Google-style** format:

**Required Sections:**
1. **One-line summary** - Imperative mood, ends with period
2. **Extended description** - Optional, for complex functions
3. **Args** - All parameters with types and descriptions
4. **Returns** - Return type and description
5. **Raises** - Expected exceptions (optional)
6. **Examples** - 2-3 realistic usage examples (required for complex functions)

**Example Docstring:**
```python
async def check_rate_limit(
    self,
    key: str,
    limit: int,
    window_seconds: int = 60,
    burst: int | None = None,
) -> tuple[bool, int]:
    """
    Check if a request is within rate limits using sliding window.

    This function uses Redis sorted sets to implement a sliding window
    rate limiter that accurately counts requests over time.

    Args:
        key: Unique identifier for the rate limit (e.g., user_id, IP).
        limit: Maximum number of requests allowed in the window.
        window_seconds: Time window in seconds (default: 60).
        burst: Optional burst limit for short-term spikes.

    Returns:
        Tuple of (is_allowed, remaining_requests).

    Raises:
        Exception: If Redis connection fails.

    Examples:
        >>> # Basic rate limiting (60 requests per minute)
        >>> limiter = RateLimiter()
        >>> is_allowed, remaining = await limiter.check_rate_limit(
        ...     key="user:123",
        ...     limit=60,
        ...     window_seconds=60
        ... )
        >>> if not is_allowed:
        ...     raise HTTPException(429, "Rate limit exceeded")

        >>> # With burst allowance for traffic spikes
        >>> is_allowed, remaining = await limiter.check_rate_limit(
        ...     key="ip:192.168.1.1",
        ...     limit=100,
        ...     window_seconds=60,
        ...     burst=20  # Allow 120 total (100 + 20 burst)
        ... )
    """
    # Implementation...
```

**When to Add Examples:**
- ✅ Complex functions with 3+ parameters
- ✅ Functions with non-obvious usage patterns
- ✅ Public API functions used by other developers
- ✅ Functions with conditional behavior or edge cases
- ❌ Simple getters/setters
- ❌ Private utility functions (unless complex)

**Example Guidelines:**
- Use `>>>` for doctest-style examples
- Show 2-3 realistic use cases
- Include error handling examples
- Demonstrate optional parameters
- Keep examples concise but complete

**Functions with Examples:**
- `get_paginated_results()` - app/storage/db.py
- `log_user_action()` - app/utils/audit_logger.py
- `check_rate_limit()` - app/utils/rate_limiter.py
- `PackageRouter.register()` - app/routing.py
- `require_roles()` - app/dependencies/permissions.py
- BaseRepository methods - app/repositories/base.py

**Verification:**
Run `uvx interrogate app/` to check docstring coverage (must be ≥80%).

### Automated Dependency Updates

**Dependabot Configuration:**

The project uses GitHub Dependabot for automated dependency updates. Configuration is in `.github/dependabot.yml`.

**Update Schedule:**
- **Python dependencies** (pip): Weekly on Mondays at 09:00 Europe/Skopje time
- **GitHub Actions**: Weekly on Mondays at 09:00 Europe/Skopje time
- **Docker images**: Weekly on Mondays at 09:00 Europe/Skopje time

**Grouping Strategy:**
- Minor and patch updates are grouped together to reduce PR noise
- Major version updates create separate PRs for careful review

**Pull Request Management:**
- Maximum 10 open PRs for Python dependencies
- Maximum 5 open PRs for GitHub Actions and Docker
- PRs are labeled with `dependencies` and ecosystem-specific labels
- Automatic reviewer assignment to `@acikabubo`

**Commit Message Format:**
- Python dependencies: `deps: Update package-name from X to Y`
- Development dependencies: `deps(dev): Update package-name from X to Y`
- GitHub Actions: `deps(actions): Update action-name from X to Y`
- Docker: `deps(docker): Update image-name from X to Y`

**Reviewing Dependabot PRs:**

1. **Check CI Status**: Ensure all tests pass
2. **Review Changelog**: Check breaking changes in package release notes
3. **Test Locally**: For major updates, test locally before merging
4. **Merge Strategy**:
   - Patch updates: Can be auto-merged if tests pass
   - Minor updates: Review changelog, merge if no breaking changes
   - Major updates: Careful review, test locally, update code if needed

**Dependabot Commands:**

You can interact with Dependabot via PR comments:
- `@dependabot rebase` - Rebase the PR
- `@dependabot recreate` - Recreate the PR (ignore local edits)
- `@dependabot merge` - Merge the PR (after approvals)
- `@dependabot squash and merge` - Squash and merge
- `@dependabot cancel merge` - Cancel a merge request
- `@dependabot close` - Close the PR and don't create updates
- `@dependabot ignore this dependency` - Close and ignore future updates
- `@dependabot ignore this major version` - Ignore major version updates
- `@dependabot ignore this minor version` - Ignore minor version updates

**Security Updates:**

Dependabot also creates PRs for security vulnerabilities automatically (not on schedule). These should be reviewed and merged with high priority.

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

**Return Type Guidelines:**

1. **Functions that return nothing** - Use `-> None`:
   ```python
   async def send_notification(user_id: str, message: str) -> None:
       await notification_service.send(user_id, message)
       # No return statement

   async def audit_log_worker() -> None:
       """Background worker that processes audit logs."""
       while True:
           batch = await get_batch()
           await process_batch(batch)
   ```

2. **Functions that never return** (infinite loops, always raise) - Use `-> NoReturn`:
   ```python
   from typing import NoReturn

   async def background_task() -> NoReturn:
       """Task that runs forever."""
       while True:
           await asyncio.sleep(10)
           await do_work()
           # Never exits normally

   def raise_error() -> NoReturn:
       """Always raises an exception."""
       raise ValueError("This always fails")
   ```

3. **Functions with optional returns** - Use `-> ReturnType | None`:
   ```python
   async def get_user(user_id: int) -> User | None:
       """Returns User or None if not found."""
       user = await db.query(User).filter(User.id == user_id).first()
       return user

   async def get_redis_connection(db: int = 1) -> Redis | None:
       """Returns Redis connection or None if unavailable."""
       try:
           return await RedisPool.get_instance(db)
       except ConnectionError:
           return None
   ```

4. **Generic collections** - Use specific type parameters:
   ```python
   # ✅ Good - specific types
   def get_authors() -> list[Author]:
       return [Author(id=1, name="John")]

   def get_config() -> dict[str, Any]:
       return {"key": "value", "count": 42}

   # ❌ Bad - bare collections
   def get_authors() -> list:  # ❌ What's in the list?
       return [Author(id=1, name="John")]

   def get_config() -> dict:  # ❌ What are the keys/values?
       return {"key": "value"}
   ```

5. **Async context managers** - Use `-> AsyncGenerator`:
   ```python
   from collections.abc import AsyncGenerator

   async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
       """FastAPI lifespan context manager."""
       # Startup
       await initialize_services()
       yield
       # Shutdown
       await cleanup_services()
   ```

6. **Middleware dispatch methods** - Use `-> Response`:
   ```python
   from starlette.types import ASGIApp

   async def dispatch(
       self, request: Request, call_next: ASGIApp
   ) -> Response:
       # Process request
       response = await call_next(request)
       # Modify response
       return response
   ```

**Examples:**
```python
# Good
async def get_connection(db: int = 1) -> Redis | None:
    ...

def process_data(filters: dict[str, Any]) -> list[Author]:
    ...

async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
    ...

async def background_worker() -> None:
    while True:
        await process()

async def infinite_task() -> NoReturn:
    while True:
        await asyncio.sleep(1)

# Bad
async def get_connection(db=1):  # ❌ No return type
    ...

def process_data(filters: dict):  # ❌ Generic dict
    ...

async def dispatch(self, request: Request, call_next):  # ❌ Missing type
    ...
```

**mypy Configuration:**

The project enforces strict type checking via `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
disallow_untyped_defs = true  # Requires return types
```

Run `uvx mypy app/` to verify type correctness before committing.

### Database Session Management

**IMPORTANT**: Use the Repository pattern for all database operations. This enables:
- Separation of concerns (models are pure data classes)
- Easier testing with mocked repositories
- Better transaction control
- Reusable business logic via Commands

**Repository Pattern:**
```python
from app.repositories.base import BaseRepository

class MyModelRepository(BaseRepository[MyModel]):
    async def get_by_name(self, name: str) -> MyModel | None:
        """Get model by name."""
        stmt = select(MyModel).where(MyModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str) -> list[MyModel]:
        """Search models by query."""
        stmt = select(MyModel).where(MyModel.name.contains(query))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

**Usage in HTTP endpoints:**
```python
from app.storage.db import async_session
from app.dependencies import MyModelRepoDep  # Dependency injection

@router.post("/my-models")
async def create_model(
    instance: MyModel,
    repo: MyModelRepoDep  # Injected by FastAPI
) -> MyModel:
    return await repo.create(instance)

@router.get("/my-models")
async def get_models(repo: MyModelRepoDep) -> list[MyModel]:
    return await repo.get_all()

@router.get("/my-models/{id}")
async def get_model(id: int, repo: MyModelRepoDep) -> MyModel:
    model = await repo.get_by_id(id)
    if not model:
        raise HTTPException(status_code=404, detail="Not found")
    return model
```

**Usage in WebSocket handlers:**
```python
from app.storage.db import async_session

async def my_handler(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        repo = MyModelRepository(session)
        items = await repo.get_all()
        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[item.model_dump() for item in items]
        )
```

**Why Repository Pattern?**
- **Testability**: Easy to mock repositories without database
- **Reusability**: Same repository used in HTTP and WebSocket handlers
- **Maintainability**: Business logic separated from data access
- **Type Safety**: Full type hints with FastAPI's `Depends()`

See [Design Patterns Guide](docs/architecture/DESIGN_PATTERNS_GUIDE.md) for complete examples.

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

**The N+1 Query Problem:**

Without eager loading, accessing relationships in loops triggers the N+1 query problem:

```python
# ❌ BAD - N+1 queries
async with async_session() as session:
    authors = await session.exec(select(Author))  # 1 query

    for author in authors:  # Loop through N authors
        books = await author.awaitable_attrs.books  # N additional queries!
        print(f"{author.name}: {len(books)} books")

# Total: 1 + N queries (if you have 100 authors, that's 101 queries!)
```

**Accessing Relationships with Eager Loading:**

1. **selectinload() - For One-to-Many and Many-to-Many (Recommended)**
   ```python
   from sqlalchemy.orm import selectinload

   # ✅ GOOD - Only 2 queries total
   async with async_session() as session:
       # Load authors with all books in 2 optimized queries
       stmt = select(Author).options(selectinload(Author.books))
       result = await session.execute(stmt)
       authors = result.scalars().all()

       # Relationships already loaded, no await needed
       for author in authors:
           books = author.books  # ✅ Already loaded, no additional query!
           print(f"{author.name}: {len(books)} books")

   # Total: 2 queries (1 for authors, 1 for all books in bulk)
   ```

2. **joinedload() - For Many-to-One Relationships**
   ```python
   from sqlalchemy.orm import joinedload

   # ✅ GOOD - Only 1 query with JOIN
   async with async_session() as session:
       stmt = select(Book).options(joinedload(Book.author))
       result = await session.execute(stmt)
       books = result.scalars().unique().all()  # unique() required with joins!

       # Author already loaded for each book
       for book in books:
           author = book.author  # ✅ Already loaded!
           print(f"{book.title} by {author.name}")

   # Total: 1 query (single JOIN)
   ```

3. **Nested Eager Loading - For Deep Relationships**
   ```python
   # Load authors → books → reviews (3 levels deep)
   stmt = select(Author).options(
       selectinload(Author.books).selectinload(Book.reviews)
   )
   result = await session.execute(stmt)
   authors = result.scalars().all()

   for author in authors:
       for book in author.books:
           reviews = book.reviews  # All loaded!

   # Total: 3 queries (authors, books, reviews)
   ```

4. **Lazy Loading with awaitable_attrs (Use Sparingly)**
   ```python
   async with async_session() as session:
       author = await session.get(Author, 1)

       # Access lazy-loaded relationship asynchronously
       books = await author.awaitable_attrs.books  # ✅ Awaitable
       for book in books:
           print(book.title)
   ```

**Performance Comparison:**

| Strategy | Query Count | Best For | Example Use Case |
|----------|-------------|----------|------------------|
| Lazy Loading (`awaitable_attrs`) | 1 + N | Single relationship access | Loading one author's books |
| `selectinload()` | 2 | One-to-many, many-to-many | Authors → books, users → roles |
| `joinedload()` | 1 (with JOIN) | Many-to-one | Books → author, orders → customer |
| Nested eager loading | 1 per level | Deep relationships | Authors → books → reviews |

**When to Use Each Strategy:**

✅ **Use Eager Loading When:**
- Accessing relationships in loops (list views, reports)
- Loading multiple related objects at once
- Building API responses with nested data
- Displaying paginated lists with related entities
- You know you'll need the relationship data

⚠️ **Use Lazy Loading When:**
- Relationship might not be accessed (conditional logic)
- Loading single object with specific relationship
- Relationship access is rare or dynamic
- Eager loading would load too much unnecessary data

**Important Notes:**
- Models without relationships (e.g., `UserAction` audit logs) don't need to inherit from `BaseModel` and can use `SQLModel` directly
- `AsyncAttrs` has no performance penalty if relationships are not used
- Avoid accessing relationships directly without eager loading or `awaitable_attrs` - it will raise `MissingGreenlet` errors in async contexts
- Always use `.unique()` when using `joinedload()` to remove duplicate rows from JOIN results
- For repositories, prefer eager loading in `get_all()` methods to avoid N+1 queries in list endpoints

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

The application supports both **offset-based** (traditional) and **cursor-based** pagination, with optional eager loading to prevent N+1 queries.

#### Offset-based Pagination (Traditional)

Standard page-based pagination using `OFFSET` and `LIMIT`:

```python
from app.storage.db import get_paginated_results

# Traditional offset pagination
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

**Metadata returned:**
```python
{
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "next_cursor": None,
    "has_more": False
}
```

**Pros:**
- Familiar page-based navigation
- Shows total count and page numbers
- Easy to jump to specific pages

**Cons:**
- O(n) performance - slower for large offsets (e.g., page 1000)
- Inconsistent results if data changes between page loads
- Expensive `COUNT(*)` query for total count

#### Cursor-based Pagination (Recommended)

Cursor-based pagination provides consistent O(1) performance and stable results using the last item's ID as a cursor:

```python
from app.storage.db import get_paginated_results

# First page - no cursor
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor=""  # Empty string or None for first page
)

# Subsequent pages - use next_cursor from previous response
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor=meta.next_cursor  # Base64-encoded last item ID
)
```

**Metadata returned:**
```python
{
    "page": 1,
    "per_page": 20,
    "total": 0,  # COUNT skipped for performance
    "pages": 0,
    "next_cursor": "MjA=",  # Base64-encoded cursor for next page
    "has_more": True  # Whether more results exist
}
```

**Cursor encoding:**
- Cursor is base64-encoded last item ID: `encode_cursor(20)` → `"MjA="`
- Decode with `decode_cursor("MjA=")` → `20`
- Empty cursor or `None` starts from first item

**Pros:**
- O(1) performance - consistent speed regardless of position
- Stable results - no duplicates or skipped items if data changes
- No expensive `COUNT(*)` query
- Better for infinite scroll and real-time feeds

**Cons:**
- Cannot jump to arbitrary pages
- No total count or page numbers
- Requires sequential traversal

#### Eager Loading (Prevent N+1 Queries)

Both pagination types support eager loading to prevent N+1 query problems:

```python
# Eager load relationships to prevent N+1 queries
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor="",
    eager_load=["books"]  # Load books relationship in 2 queries (not N+1)
)

# Without eager loading (N+1 problem):
# - 1 query for authors
# - N queries for each author's books (if accessed)
# Total: 1 + N queries

# With eager loading:
# - 1 query for authors
# - 1 optimized query for all books
# Total: 2 queries
```

**Multiple relationships:**
```python
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    eager_load=["books", "reviews"]  # Load multiple relationships
)
```

**Invalid relationship handling:**
- If relationship doesn't exist, logs warning but continues
- Example: `eager_load=["nonexistent"]` logs warning, returns results

#### Combined Example: Cursor + Eager Loading + Filters

```python
# Optimal pagination with cursor, eager loading, and filters
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor=request.data.get("cursor", ""),
    filters={"status": "active", "verified": True},
    eager_load=["books", "reviews"]
)

# Check if more results exist
if meta.has_more:
    next_cursor = meta.next_cursor
    # Client can request next page with cursor=next_cursor
```

#### WebSocket Handler Example

```python
@pkg_router.register(PkgID.GET_AUTHORS, json_schema=schema)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    """
    Get paginated authors with cursor and eager loading support.

    Request Data:
        {
            "per_page": 20,
            "cursor": "MjA=",  # Optional - for subsequent pages
            "eager_load": ["books"],  # Optional - prevent N+1 queries
            "filters": {"status": "active"}  # Optional
        }

    Response:
        {
            "data": [...],
            "meta": {
                "has_more": true,
                "next_cursor": "NDA=",
                "total": 0,  # COUNT skipped for cursor pagination
                "pages": 0
            }
        }
    """
    async with async_session() as session:
        repo = AuthorRepository(session)

        # Get pagination parameters
        per_page = request.data.get("per_page", 20)
        cursor = request.data.get("cursor", "")
        eager_load = request.data.get("eager_load", [])
        filters = request.data.get("filters", {})

        # Use cursor pagination with eager loading
        results, meta = await get_paginated_results(
            Author,
            per_page=per_page,
            cursor=cursor,
            eager_load=eager_load,
            filters=filters
        )

        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[r.model_dump() for r in results],
            meta=meta.model_dump()
        )
```

#### Type-Safe Filters with Pydantic Schemas

For better type safety and IDE autocomplete, use Pydantic filter schemas instead of raw dictionaries:

**Filter Schema Definition:**
```python
# app/schemas/filters.py
from pydantic import BaseModel, Field
from app.schemas.filters import BaseFilter

class AuthorFilters(BaseFilter):
    """Type-safe filters for Author model queries."""

    id: int | None = Field(
        default=None,
        description="Filter by exact author ID",
    )
    name: str | None = Field(
        default=None,
        description="Filter by author name (case-insensitive partial match)",
    )

# BaseFilter provides to_dict() method and extra="forbid" config
```

**Usage in WebSocket Handlers:**
```python
from pydantic import ValidationError
from app.schemas.filters import AuthorFilters

@pkg_router.register(PkgID.GET_PAGINATED_AUTHORS)
@handle_ws_errors
async def get_paginated_authors_handler(request: RequestModel) -> ResponseModel:
    # Extract request parameters
    data = request.data or {}
    page = data.get("page", 1)
    per_page = data.get("per_page")

    # Parse filters with type-safe Pydantic schema
    filters = None
    if "filters" in data:
        try:
            filters = AuthorFilters(**data["filters"])
        except ValidationError as e:
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                f"Invalid filter parameters: {str(e)}",
            )

    # Get paginated results with type-safe filters
    authors, meta = await get_paginated_results(
        Author,
        page=page,
        per_page=per_page,
        filters=filters,  # Pydantic model, not dict!
    )

    return ResponseModel(
        pkg_id=request.pkg_id,
        req_id=request.req_id,
        data=[author.model_dump() for author in authors],
        meta=meta,
    )
```

**Benefits of Type-Safe Filters:**
- ✅ **Compile-time safety**: IDE autocomplete for filter fields
- ✅ **Runtime validation**: Pydantic catches invalid fields before query execution
- ✅ **Self-documenting**: Filter schemas document available filter options
- ✅ **Security**: Whitelist of allowed filter fields prevents injection attacks
- ✅ **Backward compatible**: Legacy dict filters still work via `get_paginated_results()`

**Creating Filter Schemas:**

When adding a new model, create a corresponding filter schema in `app/schemas/filters.py`:

```python
class MyModelFilters(BaseFilter):
    """Type-safe filters for MyModel queries."""

    id: int | None = None
    name: str | None = None
    created_after: datetime | None = Field(
        None,
        description="Filter by creation date"
    )

    # All fields are optional (None default)
    # String filters use case-insensitive ILIKE pattern matching
    # to_dict() method excludes None values automatically
```

**Filter Validation:**

The `get_paginated_results()` function validates filter keys against model columns in `default_apply_filters()`:

```python
def default_apply_filters(query, model, filters):
    for key, value in filters.items():
        if hasattr(model, key):
            # Apply filter
            attr = getattr(model, key)
            query = query.filter(attr == value)
        else:
            # Invalid filter key
            raise ValueError(
                f"Invalid filter: {key} is not an attribute of {model.__name__}"
            )
    return query
```

**Error Handling:**
```python
# Invalid filter field (extra="forbid")
filters = AuthorFilters(invalid_field="value")  # ValidationError!

# Invalid field type
filters = AuthorFilters(id="not_an_int")  # ValidationError!

# Valid filter
filters = AuthorFilters(name="John")  # ✅ Type-safe
```

#### Choosing Between Offset and Cursor Pagination

**Use Cursor Pagination When:**
- ✅ Performance is critical (large datasets, high traffic)
- ✅ Real-time data (frequent inserts/updates)
- ✅ Infinite scroll UI pattern
- ✅ Mobile apps (bandwidth-sensitive)
- ✅ No need for page numbers or jumping to specific pages

**Use Offset Pagination When:**
- ✅ Need total count and page numbers
- ✅ Users need to jump to arbitrary pages
- ✅ Small datasets (< 1000 items)
- ✅ Data rarely changes
- ✅ Admin dashboards with page selectors

**Best Practice: Support Both**

The current implementation supports both simultaneously - clients can choose via request parameters:

```python
# Offset pagination (traditional)
{"page": 2, "per_page": 20}

# Cursor pagination (recommended)
{"cursor": "MjA=", "per_page": 20}
```

#### Performance Comparison

| Feature | Offset Pagination | Cursor Pagination |
|---------|-------------------|-------------------|
| Speed (page 1) | Fast | Fast |
| Speed (page 1000) | Slow (O(n)) | Fast (O(1)) |
| Total count | Yes (expensive) | No (skipped) |
| Jump to page | Yes | No (sequential only) |
| Stable results | No (data changes) | Yes (cursor-based) |
| N+1 queries | Possible | Possible (use eager_load) |
| Best for | Small datasets | Large datasets, real-time |

### Performance Optimizations

The application includes several performance optimizations for database queries and pagination:

#### Slow Query Detection

**SQLAlchemy Event Listeners** ([app/utils/query_monitor.py](app/utils/query_monitor.py)):
- Automatically tracks all database query execution times
- Logs queries exceeding 100ms threshold (configurable `SLOW_QUERY_THRESHOLD`)
- Records metrics for Prometheus monitoring
- Enabled automatically on application startup

**Implementation:**
```python
from app.utils.query_monitor import enable_query_monitoring

# Called automatically in app/storage/db.py
enable_query_monitoring()
```

**Slow Query Logging:**
```
WARNING - Slow query detected: 0.245s [SELECT] Statement: SELECT * FROM authors WHERE ...
```

**Metrics Available:**
- `db_query_duration_seconds{operation="select|insert|update|delete"}` - Histogram of query durations
- `db_slow_queries_total{operation="select|insert|update|delete"}` - Counter of slow queries

**Best Practices:**
1. Monitor slow query logs regularly
2. Add database indexes for frequently filtered columns
3. Use query profiling to optimize N+1 query patterns
4. Consider query result caching for expensive operations

#### Pagination Count Caching

**Redis-Based Count Caching** ([app/utils/pagination_cache.py](app/utils/pagination_cache.py)):
- Caches expensive `COUNT(*)` queries used in pagination
- Default TTL: 5 minutes (configurable)
- Cache keys based on model name and filter hash
- Automatic cache invalidation support

**How It Works:**
```python
# Automatically used in get_paginated_results()
# 1. Check cache first
cached_total = await get_cached_count(model_name, filters)

# 2. If cache miss, execute COUNT query
if cached_total is None:
    total = await s.exec(count_query)
    # 3. Cache the result
    await set_cached_count(model_name, total, filters)
```

**Cache Invalidation:**

Invalidate the count cache after any CREATE, UPDATE, or DELETE operation that affects the model:

```python
from app.utils.pagination_cache import invalidate_count_cache

# After creating a new record
async def create_author(author: Author, repo: AuthorRepository) -> Author:
    result = await repo.create(author)
    await invalidate_count_cache("Author")  # Invalidate all Author counts
    return result

# After deleting a record
async def delete_author(author_id: int, repo: AuthorRepository) -> None:
    await repo.delete(author_id)
    await invalidate_count_cache("Author")

# After updating (if it might affect filters)
async def update_author_status(author_id: int, status: str, repo: AuthorRepository) -> Author:
    author = await repo.get_by_id(author_id)
    old_status = author.status
    author.status = status
    result = await repo.update(author)

    # Invalidate counts for both old and new status
    await invalidate_count_cache("Author", filters={"status": old_status})
    await invalidate_count_cache("Author", filters={"status": status})
    return result
```

**When to invalidate:**
- ✅ **Always**: After INSERT or DELETE operations
- ✅ **Conditional**: After UPDATE if updated field is in common filters
- ❌ **Never**: After SELECT/GET operations
- ⚠️ **Skip caching**: For models with very frequent writes (use `skip_count=True` instead)

**Granular invalidation:**
```python
# Invalidate all counts for a model
await invalidate_count_cache("Author")

# Invalidate only specific filter combination
await invalidate_count_cache("Author", filters={"status": "active"})

# Invalidate multiple filter combinations after batch operations
for status in ["active", "inactive", "pending"]:
    await invalidate_count_cache("Author", filters={"status": status})
```

**Batch operations:**
```python
# Batch insert - invalidate once at the end
async def batch_create_authors(authors: list[Author], repo: AuthorRepository) -> None:
    for author in authors:
        await repo.create(author)

    # Invalidate once after batch (not per record!)
    await invalidate_count_cache("Author")
```

**Benefits:**
- 50-90% reduction in COUNT query execution for repeated requests
- Significant performance improvement for large tables (10k+ rows)
- Fails gracefully when Redis is unavailable (executes query normally)

**Skip Count Option:**
For endpoints where total count is not needed (e.g., infinite scroll):
```python
results, meta = await get_paginated_results(
    Author,
    page=1,
    per_page=20,
    skip_count=True  # Skip expensive COUNT query
)
# meta.total will be 0, meta.pages will be 0
```

**Performance Comparison:**

| Table Size | Without Cache | With Cache | Improvement |
|------------|---------------|------------|-------------|
| 1,000 rows | 5ms          | 1ms        | 80% faster  |
| 10,000 rows| 45ms         | 1ms        | 98% faster  |
| 100,000 rows| 450ms       | 1ms        | 99.8% faster|

**Configuration:**
```python
# app/utils/pagination_cache.py
DEFAULT_COUNT_CACHE_TTL = 300  # 5 minutes

# Custom TTL when caching
await set_cached_count(model_name, total, filters, ttl=600)  # 10 minutes
```

**Monitoring:**
Track cache hit rates in application logs:
```
DEBUG - Count cache hit for Author (filters: {'status': 'active'}): 42
DEBUG - Count cache miss for Author (filters: {'name': 'John'})
DEBUG - Cached count for Author (filters: None): 1234 (TTL: 300s)
```

**Use Cases:**
- ✅ **Use count caching**: List endpoints with stable data, admin dashboards, reports
- ✅ **Use skip_count**: Infinite scroll, real-time feeds, frequently changing data
- ✅ **Invalidate cache**: After any CREATE, UPDATE, DELETE operations on the model

#### Query Performance Best Practices

1. **Add Database Indexes:**
   ```python
   # In your SQLModel definitions
   class Author(BaseModel, table=True):
       name: str = Field(index=True)  # Frequently filtered
       email: str = Field(unique=True, index=True)
       status: str = Field(index=True)  # Frequently filtered
   ```

2. **Use Eager Loading for Relationships:**
   ```python
   from sqlalchemy.orm import selectinload

   stmt = select(Author).options(selectinload(Author.books))
   authors = await session.exec(stmt)
   # All books loaded in 2 optimized queries (no N+1)
   ```

3. **Monitor Slow Queries:**
   - Check application logs for slow query warnings
   - Review Prometheus metrics for query duration trends
   - Use `EXPLAIN ANALYZE` for query optimization

4. **Combine Optimizations:**
   ```python
   # Skip count for real-time data + use filters
   results, meta = await get_paginated_results(
       Message,
       page=1,
       per_page=50,
       skip_count=True,  # No COUNT query
       filters={"created_at": ">= 2024-01-01"}
   )
   ```

### Testing Notes

- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Tests run in parallel by default using `pytest-xdist` for faster execution
- Mock Keycloak interactions where appropriate (`pytest-mock`)
- Database tests should use test fixtures with isolated sessions
- **IMPORTANT:** Use centralized fixtures from `tests/conftest.py` and mock factories from `tests/mocks/`
- Load tests (marked `@pytest.mark.load`) test performance under high concurrent loads
- Chaos tests (marked `@pytest.mark.chaos`) test resilience when dependencies fail
- Skip slow tests with: `pytest -m "not load and not chaos"`

#### Centralized Test Mocks

**CRITICAL:** Always use centralized mock factories from `tests/mocks/` instead of creating inline mocks. This ensures consistency, reduces code duplication, and makes tests easier to maintain.

**Available Mock Factories:**

```python
# Redis Mocks (tests/mocks/redis_mocks.py)
from tests.mocks.redis_mocks import (
    create_mock_redis_connection,     # Full Redis connection with all operations
    create_mock_rate_limiter,          # RateLimiter instance
    create_mock_connection_limiter,    # ConnectionLimiter instance
)

# WebSocket Mocks (tests/mocks/websocket_mocks.py)
from tests.mocks.websocket_mocks import (
    create_mock_websocket,             # WebSocket connection with send/receive
    create_mock_connection_manager,    # ConnectionManager with broadcast
    create_mock_package_router,        # PackageRouter with handle_request
    create_mock_broadcast_message,     # BroadcastDataModel factory
)

# Auth Mocks (tests/mocks/auth_mocks.py)
from tests.mocks.auth_mocks import (
    create_mock_keycloak_manager,      # KeycloakManager with login/decode_token
    create_mock_user_model,             # UserModel factory
    create_mock_auth_backend,           # AuthBackend for middleware tests
    create_mock_rbac_manager,           # RBACManager for permission tests
)

# Repository Mocks (tests/mocks/repository_mocks.py)
from tests.mocks.repository_mocks import (
    create_mock_author_repository,     # AuthorRepository with CRUD ops
    create_mock_crud_repository,        # Generic BaseRepository
)
```

**Usage Examples:**

```python
# ✅ GOOD - Use centralized mocks
from tests.mocks.redis_mocks import create_mock_redis_connection

@pytest.fixture
def mock_redis():
    return create_mock_redis_connection()

async def test_rate_limiting(mock_redis):
    limiter = RateLimiter()
    # mock_redis already has all methods configured
    ...

# ❌ BAD - Don't create inline mocks
@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.zcard = AsyncMock(return_value=0)
    # ... 10 more lines of setup
    return redis_mock
```

```python
# ✅ GOOD - Use WebSocket mock factory
from tests.mocks.websocket_mocks import create_mock_websocket

async def test_websocket_handler():
    mock_ws = create_mock_websocket()
    # Already has send_json, send_response, accept, close, client.host, etc.
    await handler.on_connect(mock_ws)

# ❌ BAD - Don't create inline WebSocket mocks
async def test_websocket_handler():
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.send_response = AsyncMock()
    # ... many more lines
```

```python
# ✅ GOOD - Use Keycloak mock factory
from tests.mocks.auth_mocks import create_mock_keycloak_manager

async def test_authentication():
    mock_kc = create_mock_keycloak_manager()
    # Already configured with login and decode_token methods
    with patch("app.auth.KeycloakManager", return_value=mock_kc):
        ...

# ❌ BAD - Don't create inline Keycloak mocks
async def test_authentication():
    mock_kc = MagicMock()
    mock_kc.login = Mock(return_value={"access_token": "..."})
    mock_kc.openid.decode_token = Mock(return_value={...})
    # Duplicate setup across many test files
```

**Benefits of Centralized Mocks:**
- ✅ **Consistency:** Same mock behavior across all tests
- ✅ **Maintainability:** Update once in `tests/mocks/`, benefits all tests
- ✅ **Less Code:** ~80 lines eliminated in just 4 refactored files
- ✅ **Discoverability:** Easy to find and reuse existing mocks
- ✅ **Type Safety:** Mocks use `spec` parameter for better IDE support

**When Creating New Tests:**
1. Check `tests/mocks/` first - the mock you need probably exists
2. If creating a new mock, add it to the appropriate `tests/mocks/*.py` file
3. Never create inline mocks - always use or extend centralized factories
4. See refactored files for examples: `test_rate_limiting.py`, `test_websocket.py`, `test_auth_basic.py`

#### Edge Case Testing

**IMPORTANT**: Always write edge case tests for critical components. Edge cases reveal bugs that standard tests miss.

**What Are Edge Cases?**
- Invalid input (malformed data, wrong types, missing fields)
- Boundary conditions (zero, negative, maximum values)
- Resource failures (database down, Redis unavailable, connection drops)
- Concurrent operations (race conditions, deadlocks)
- Unusual state combinations (empty results, overflow, underflow)

**Dedicated Edge Case Test Files:**
- `tests/test_websocket_edge_cases.py` - WebSocket consumer edge cases (14 tests)
- `tests/test_rate_limiter_edge_cases.py` - Rate limiter edge cases (19 tests)
- `tests/test_audit_edge_cases.py` - Audit logger edge cases (15 tests)
- `tests/test_pagination_edge_cases.py` - Pagination edge cases (16 tests)

**Edge Case Categories:**

1. **Malformed Input:**
   ```python
   async def test_malformed_json_message(self):
       """Test handling of invalid JSON."""
       invalid_data = {"invalid_field": "value"}  # Missing required fields
       await consumer.on_receive(websocket, invalid_data)
       websocket.close.assert_called_once()  # Should close gracefully
   ```

2. **Resource Failures:**
   ```python
   async def test_redis_connection_error_fail_open(self):
       """Test fail-open when Redis unavailable."""
       mock_redis.zadd.side_effect = RedisConnectionError("Connection refused")
       is_allowed, _ = await rate_limiter.check_rate_limit("user:123", 10, 60)
       assert is_allowed is True  # Should allow request (fail-open)
   ```

3. **Boundary Conditions:**
   ```python
   async def test_page_zero(self):
       """Test that page=0 is rejected."""
       with pytest.raises(ValueError, match="page must be >= 1"):
           await get_paginated_results(Author, page=0, per_page=10)
   ```

4. **Concurrent Operations:**
   ```python
   async def test_concurrent_messages_from_single_connection(self):
       """Test handling of multiple concurrent messages."""
       tasks = [consumer.on_receive(websocket, req) for req in requests]
       await asyncio.gather(*tasks)
       assert websocket.send_response.call_count == len(requests)
   ```

5. **Connection/Network Failures:**
   ```python
   async def test_message_processing_during_disconnect(self):
       """Test when connection drops mid-processing."""
       websocket.send_response.side_effect = RuntimeError("Connection closed")
       # Should handle gracefully without crashing
       await consumer.on_receive(websocket, request_data)
   ```

**When to Write Edge Case Tests:**

✅ **Always write edge case tests for:**
- Critical path code (authentication, authorization, data persistence)
- External service integrations (Redis, PostgreSQL, Keycloak)
- Message handling (WebSocket, HTTP request validation)
- Rate limiting and resource management
- Data pagination and filtering

❌ **Don't need edge case tests for:**
- Simple utility functions with no external dependencies
- Configuration loaders
- Static data transformations

**Discovered Bugs Process:**

When edge case tests reveal bugs:
1. Document bug in test docstring with "BUG DISCOVERED:" prefix
2. Update test to expect current behavior (with `pytest.raises`)
3. Create GitHub issue for fixing the bug
4. Link issue number in test comment
5. After fix, update test to expect correct behavior

**Example:**
```python
async def test_malformed_protobuf_message(self):
    """
    Test handling of invalid Protobuf data.

    BUG DISCOVERED: DecodeError not caught, causing exception.
    GitHub Issue: #130
    Should be caught and handled like ValidationError.
    """
    # Currently raises DecodeError (not caught)
    with pytest.raises(DecodeError):
        await consumer.on_receive(websocket, invalid_protobuf)

    # After fix (issue #130), change to:
    # await consumer.on_receive(websocket, invalid_protobuf)
    # websocket.close.assert_called_once()
```

**Running Edge Case Tests:**
```bash
# Run all edge case tests
pytest tests/test_*_edge_cases.py -v

# Run specific category
pytest tests/test_websocket_edge_cases.py -v

# Run only edge case tests that currently fail (to track bugs)
pytest tests/test_*_edge_cases.py -v --tb=line | grep FAILED
```

**Benefits of Edge Case Testing:**
- ✅ Catches bugs before production (5 critical bugs found in WebSocket consumer)
- ✅ Documents expected behavior for unusual scenarios
- ✅ Prevents regressions when fixing bugs
- ✅ Improves code reliability and robustness
- ✅ Serves as specification for fail-open/fail-closed behavior

**See Also:**
- `BUGS_DISCOVERED_ISSUE_129.md` - Summary of bugs found during edge case testing
- `tests/test_websocket_edge_cases.py` - Comprehensive WebSocket edge case examples

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

### Protocol Buffers (Protobuf) Support

**Overview:**
The application supports Protocol Buffers (protobuf) for WebSocket communication alongside JSON. Protobuf provides better performance, smaller message sizes (30-50% reduction), and faster serialization compared to JSON.

**Why Protobuf?**
- **Smaller Messages**: 30-50% size reduction vs JSON
- **Faster Serialization**: 2-5x faster encoding/decoding
- **Strong Typing**: Schema validation with `.proto` files
- **Language Agnostic**: Easy client implementation in any language
- **Backwards Compatible**: Supports both JSON and protobuf simultaneously

**Installation:**

```bash
# Install protobuf dependencies
make protobuf-install

# Or manually
uv sync --group protobuf

# Generate Python code from .proto files
make protobuf-generate
```

**Schema Files:**

Protocol Buffer definitions are in `proto/websocket.proto`:
- `Request`: WebSocket request message
- `Response`: WebSocket response message
- `Broadcast`: Server-to-client push notifications
- `Metadata`: Pagination metadata
- `PaginatedRequest`: Paginated query parameters

**Format Negotiation:**

Clients specify the message format via query parameter:

```python
# Protobuf format
ws://localhost:8000/web?token=xxx&format=protobuf

# JSON format (default)
ws://localhost:8000/web?token=xxx
ws://localhost:8000/web?token=xxx&format=json
```

**Python Client Example:**

```python
import asyncio
import json
import uuid
import websockets
from app.schemas.proto import Request, Response

async def connect_with_protobuf(token: str):
    url = f"ws://localhost:8000/web?token={token}&format=protobuf"

    async with websockets.connect(url) as websocket:
        # Create protobuf Request
        request = Request()
        request.pkg_id = 1  # PkgID.GET_AUTHORS
        request.req_id = str(uuid.uuid4())
        request.data_json = json.dumps({"filters": {}})

        # Send binary message
        await websocket.send(request.SerializeToString())

        # Receive binary response
        response_bytes = await websocket.recv()

        # Parse protobuf Response
        response = Response()
        response.ParseFromString(response_bytes)

        print(f"Status: {response.status_code}")
        print(f"Data: {json.loads(response.data_json)}")
```

**Server-Side Implementation:**

The WebSocket consumer (`app/api/ws/consumers/web.py`) automatically detects message format:

```python
async def on_receive(self, websocket, data: dict[str, Any] | bytes):
    if isinstance(data, bytes):
        # Protobuf format - deserialize binary message
        proto_request = ProtoRequest()
        proto_request.ParseFromString(data)
        request = proto_to_pydantic_request(proto_request)
    else:
        # JSON format - validate with Pydantic
        request = RequestModel(**data)

    # Process request (format-agnostic)
    response = await pkg_router.handle_request(user, request)

    # Send response in same format as request
    if message_format == "protobuf":
        response_bytes = serialize_response(response, "protobuf")
        await websocket.send_bytes(response_bytes)
    else:
        await websocket.send_response(response)  # JSON
```

**Converter Utilities:**

The `app/utils/protobuf_converter.py` module provides bidirectional conversion:

```python
from app.utils.protobuf_converter import (
    pydantic_to_proto_request,
    proto_to_pydantic_request,
    pydantic_to_proto_response,
    proto_to_pydantic_response,
    detect_message_format,
    serialize_response,
)

# Pydantic → Protobuf
proto_req = pydantic_to_proto_request(pydantic_req)
binary_data = proto_req.SerializeToString()

# Protobuf → Pydantic
proto_req = Request.FromString(binary_data)
pydantic_req = proto_to_pydantic_request(proto_req)

# Auto-detect format
format = detect_message_format(data)  # Returns "json" or "protobuf"

# Serialize response to specific format
protobuf_bytes = serialize_response(response, "protobuf")
json_dict = serialize_response(response, "json")
```

**Makefile Commands:**

```bash
# Install protobuf dependencies
make protobuf-install

# Generate Python code from .proto files
make protobuf-generate

# Clean generated protobuf code
make protobuf-clean
```

**Testing:**

Unit tests for protobuf converters are in `tests/test_protobuf_converter.py`:
- Pydantic → Protobuf conversion
- Protobuf → Pydantic conversion
- Round-trip conversion (preserves data)
- Format detection
- Serialization to both formats

Run tests:
```bash
uv run pytest tests/test_protobuf_converter.py -v
```

**Performance Comparison:**

Protobuf vs JSON for typical WebSocket messages:

| Metric | JSON | Protobuf | Improvement |
|--------|------|----------|-------------|
| Message Size | ~200 bytes | ~120 bytes | 40% smaller |
| Serialization | ~50 µs | ~15 µs | 3.3x faster |
| Deserialization | ~45 µs | ~12 µs | 3.8x faster |

**Use Cases:**

✅ **Use Protobuf when:**
- High message throughput (100+ messages/sec)
- Bandwidth is limited (mobile clients)
- Performance is critical
- Strong typing is required

✅ **Use JSON when:**
- Debugging (human-readable)
- Low message volume
- Simple clients (browsers)
- Flexibility is more important than performance

**Backwards Compatibility:**

The server supports both formats simultaneously:
- Existing JSON clients continue to work without changes
- New clients can opt-in to protobuf with `?format=protobuf`
- Per-connection format negotiation (no global flag needed)
- Handlers are format-agnostic (work with both)

**Schema Evolution:**

When updating `.proto` files:
1. Modify `proto/websocket.proto`
2. Run `make protobuf-generate`
3. Commit both `.proto` and generated `_pb2.py` files
4. Follow protobuf compatibility rules (don't change field numbers)

**Files:**
- Schema: `proto/websocket.proto`
- Generated code: `app/schemas/proto/websocket_pb2.py`
- Converters: `app/utils/protobuf_converter.py`
- Tests: `tests/test_protobuf_converter.py`
- Example client: `examples/clients/websocket_protobuf_client.py`

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

# Keycloak Authentication Metrics
keycloak_auth_attempts_total{status,method}  # status: success/failure/error, method: password/token
keycloak_token_validation_total{status,reason}  # status: valid/invalid/expired/error
keycloak_operation_duration_seconds{operation}  # operation: login/validate_token
auth_backend_requests_total{type,outcome}  # type: http/websocket, outcome: success/denied/error
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

**IMPORTANT**: When adding new Prometheus metrics to `app/utils/metrics/`, you must also update the Grafana dashboard at `docker/grafana/provisioning/dashboards/fastapi-metrics.json` to visualize the new metrics. This ensures monitoring dashboards stay in sync with available metrics. Add metrics to the appropriate submodule based on their category (http.py, websocket.py, database.py, redis.py, auth.py, or audit.py).

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

### Prometheus Alerting

**Overview:**
The application includes comprehensive Prometheus alerting rules for proactive monitoring and incident detection. Alerts are defined in `docker/prometheus/alerts.yml` and automatically loaded by Prometheus.

**Alert Configuration:**
- Alert rules file: `docker/prometheus/alerts.yml`
- Evaluation interval: 30 seconds
- Configured in `docker/prometheus/prometheus.yml` via `rule_files: ['alerts.yml']`
- Access Prometheus alerts UI: http://localhost:9090/alerts

**Alert Categories:**

1. **Application Alerts** (`application_alerts` group):
   - `HighErrorRate`: HTTP 5xx error rate > 5% for 2 minutes (warning)
   - `CriticalErrorRate`: HTTP 5xx error rate > 20% for 1 minute (critical)
   - `HighClientErrorRate`: HTTP 4xx error rate > 30% for 5 minutes (info)
   - `SlowResponseTime`: 95th percentile response time > 1s for 5 minutes (warning)

2. **Database Alerts** (`database_alerts` group):
   - `DatabaseDown`: PostgreSQL unavailable for > 1 minute (critical)
   - `SlowDatabaseQueries`: 95th percentile query duration > 0.5s for 5 minutes (warning)

3. **Redis Alerts** (`redis_alerts` group):
   - `RedisDown`: Redis cache unavailable for > 1 minute (critical)

4. **WebSocket Alerts** (`websocket_alerts` group):
   - `HighWebSocketRejections`: Rejection rate > 5/s for 3 minutes (warning)
   - `HighWebSocketConnections`: Active connections > 1000 for 5 minutes (warning)

5. **Audit Alerts** (`audit_alerts` group):
   - `AuditLogDropping`: Audit logs drop rate > 1/s for 2 minutes (critical)
   - `HighAuditLogDropRate`: Drop rate > 1% for 2 minutes (warning)
   - `SustainedAuditQueueOverflow`: Drop rate > 1% for 5+ minutes (critical - compliance risk)
   - `AuditQueueNearCapacity`: Queue usage > 80% for 2 minutes (warning)

6. **Rate Limit Alerts** (`rate_limit_alerts` group):
   - `HighRateLimitHits`: Rate limit hit rate > 10/s for 5 minutes (info)

7. **Authentication Alerts** (`authentication_alerts` group):
   - `HighAuthFailureRate`: Auth failure rate > 20% for 3 minutes (warning)
   - `CriticalAuthFailureRate`: Auth failure rate > 50% for 1 minute (critical - possible attack)
   - `HighKeycloakAuthFailureRate`: Keycloak auth failure rate > 20% for 3 minutes (warning)
   - `KeycloakAuthErrors`: Keycloak auth errors > 1/s for 2 minutes (critical)
   - `HighTokenExpirationRate`: Token expiration rate > 30% for 5 minutes (info)
   - `HighInvalidTokenRate`: Invalid token rate > 10% for 3 minutes (warning)
   - `SlowKeycloakLogin`: 95th percentile login duration > 2s for 5 minutes (warning)
   - `SlowTokenValidation`: 95th percentile token validation > 0.5s for 5 minutes (warning)
   - `HighAuthBackendErrors`: Auth backend errors > 5/s for 2 minutes (critical)

8. **Keycloak Alerts** (`keycloak_alerts` group):
   - `KeycloakDown`: Keycloak unavailable for > 1 minute (critical)
   - `HighKeycloakMemoryUsage`: JVM heap usage > 85% for 5 minutes (warning)

**Alert Severity Levels:**
- `critical`: Immediate action required (service down, data loss, security incident)
- `warning`: Requires attention (degraded performance, approaching limits)
- `info`: Informational (unusual but not critical activity)

**Alert Annotations:**
Each alert includes:
- `summary`: Brief description of the alert condition
- `description`: Detailed information with metric values and thresholds

**Example Alert Rule:**
```yaml
- alert: HighErrorRate
  expr: |
    (
      rate(http_requests_total{status_code=~"5.."}[5m])
      /
      rate(http_requests_total[5m])
    ) > 0.05
  for: 2m
  labels:
    severity: warning
    component: application
  annotations:
    summary: "High HTTP 5xx error rate detected"
    description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
```

**Configuring Alert Notifications:**

To receive alert notifications, configure Alertmanager:

1. **Add Alertmanager to docker-compose.yml:**
```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  volumes:
    - ./docker/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
  command:
    - '--config.file=/etc/alertmanager/alertmanager.yml'
```

2. **Create `docker/alertmanager/alertmanager.yml`:**
```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-notifications'

receivers:
  - name: 'team-notifications'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'app_password'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

3. **Update Prometheus configuration:**
```yaml
# docker/prometheus/prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

**Viewing Alerts:**
- Prometheus alerts UI: http://localhost:9090/alerts
- Alertmanager UI: http://localhost:9093 (after configuration)
- Grafana dashboards: Alerts are visualized in panels

**Testing Alerts:**

```bash
# Trigger HighErrorRate alert (generate 500 errors)
for i in {1..100}; do curl http://localhost:8000/non-existent-endpoint; done

# Trigger SlowResponseTime alert (if you have slow endpoints)
ab -n 1000 -c 10 http://localhost:8000/slow-endpoint

# Trigger AuditLogDropping alert (requires heavy load on audit logging)
# Simulate high traffic that fills the audit queue
```

**Best Practices:**
1. **Tune thresholds**: Adjust alert thresholds based on your traffic patterns
2. **Reduce alert fatigue**: Set appropriate `for` durations to avoid flapping alerts
3. **Group alerts**: Use Alertmanager grouping to avoid notification storms
4. **Test regularly**: Verify alerts trigger correctly during deployments
5. **Document runbooks**: Create response procedures for each alert type
6. **Review alert history**: Use Grafana to analyze alert trends over time

**Audit Queue Overflow Monitoring:**

The application includes comprehensive monitoring for audit log queue overflow:

- **Metric**: `audit_logs_dropped_total` - Counter incremented when queue is full
- **Metric**: `audit_queue_size` - Current number of logs in queue
- **Alert**: `AuditLogDropping` - Triggers when logs are being dropped (rate > 1/s)
- **Alert**: `HighAuditLogDropRate` - Triggers when drop rate > 1% of total logs
- **Dashboard**: Grafana panel in `fastapi-metrics` dashboard shows dropped log trends
- **Queue size**: Configured via `AUDIT_QUEUE_MAX_SIZE` (default: 10,000)

**What happens when queue is full:**
1. New audit logs are rejected with `asyncio.QueueFull` exception
2. `audit_logs_dropped_total` counter is incremented
3. Warning is logged: `"Audit queue full, dropping log entry for {username}"`
4. Alert triggers if drop rate exceeds threshold
5. No impact on request processing (audit logging is non-blocking)

**Mitigation strategies:**
- Increase `AUDIT_QUEUE_MAX_SIZE` in settings
- Increase `AUDIT_BATCH_SIZE` for faster queue processing
- Optimize database write performance
- Add more database connections
- Scale horizontally (add more application instances)

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
