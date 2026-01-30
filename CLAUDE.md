# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📚 Documentation Index

This project has comprehensive documentation split into focused guides for better maintainability:

### Core Documentation (docs/claude/)

- **[Git Workflow Guide](docs/claude/git-workflow.md)** - GitHub issues, commits, worktree syncing, documentation requirements
- **[Architecture Guide](docs/claude/architecture-guide.md)** - Project overview, design patterns, core components, directory structure
- **[Development Guide](docs/claude/development-guide.md)** - Running the application, Docker commands, WebSocket handler management
- **[Testing Guide](docs/claude/testing-guide.md)** - Test infrastructure, parallel execution, mocks, load testing, chaos engineering
- **[Code Quality Guide](docs/claude/code-quality-guide.md)** - Linting, security scanning, pre-commit hooks, dead code detection, type safety
- **[Configuration Guide](docs/claude/configuration-guide.md)** - Constants, settings structure, environment variables, startup validation
- **[Database Guide](docs/claude/database-guide.md)** - Session management, async relationships, migrations, pagination
- **[Monitoring Guide](docs/claude/monitoring-guide.md)** - Prometheus metrics, alerting, Loki logging, audit dashboards

### User Documentation (docs_site/)

Complete user-facing documentation available at https://acikabubo.github.io/fastapi-http-websocket/

## 🚀 Quick Start Commands

```bash
# Development
make serve              # Start development server with hot-reload
make test               # Run tests in parallel
make test-serial        # Run tests sequentially (for debugging)

# Docker
make build              # Build containers
make start              # Start services (PostgreSQL, Redis, Keycloak)
make shell              # Enter development shell

# Code Quality
prek run --all-files    # Run all pre-commit hooks
make ruff-check         # Lint with ruff
uvx mypy app/           # Type checking

# WebSocket Handlers
make ws-handlers        # Show handler table
make new-ws-handlers    # Generate new handler

# Database
make migrate            # Apply migrations
make migration msg="description"  # Create migration
```

## ⚠️ CRITICAL: Most Important Rules

### 1. Review Issue Context BEFORE Starting

**REQUIRED BEFORE ANY CHANGES:**

```bash
# Read the issue carefully
gh issue view <number>

# Check for recent changes
git log --oneline --all --grep="<issue_keyword>" -10
git log --oneline -- path/to/relevant/file.py -5

# Search affected files
# Use Glob/Grep/Read to understand current implementation

# Verify current architecture
# Check for refactored patterns, renamed components
```

**Why this matters:**
- Prevents working on already-fixed issues
- Avoids using outdated patterns or assumptions
- Ensures compatibility with recent architectural changes

### 2. Use Repository + Command + Dependency Injection Pattern

**ALWAYS use these patterns for new features:**

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
        ...

# 3. HTTP Handler (uses dependency injection)
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
        return ResponseModel.success(...)
```

### 3. Sync Changes to Worktree Template

**CRITICAL:** When modifying `app/` or `tests/`, replicate to `.worktree/` template:

```bash
# Main project files
app/ → .worktree/{{cookiecutter.project_slug}}/{{cookiecutter.module_name}}/
tests/ → .worktree/{{cookiecutter.project_slug}}/tests/

# Replace project-specific references with placeholders:
# app. → {{cookiecutter.module_name}}.
# PkgID.GET_AUTHORS → PkgID.TEST_HANDLER
```

**Exception:** Do NOT sync `CLAUDE.md` between main project and worktree.

**CRITICAL:** Before committing and pushing changes to `.worktree/` folder, you MUST ask the user for confirmation first.

### 4. Update Documentation with Code Changes

**ALWAYS update docs in the same commit/PR as code changes:**

- API changes → Update `docs_site/api-reference/`
- Architecture changes → Update `docs/claude/architecture-guide.md`
- New features → Add guide to `docs_site/guides/`
- Bug fixes → Update `docs_site/deployment/troubleshooting.md`
- Testing changes → Update `docs/claude/testing-guide.md`
- Configuration changes → Update `docs/claude/configuration-guide.md`

**Before closing ANY issue:**
```bash
# Find all documentation references to changed component
grep -r "MyChangedClass" CLAUDE.md docs_site/ docs/claude/

# Verify code examples actually work
# Check that terminology is consistent across all docs
```

## 📋 Common Tasks

### Working on GitHub Issues

```bash
# Step 0: Review issue context (REQUIRED!)
gh issue view <number>
git log --oneline --all --grep="<keyword>" -10

# Steps 1-7: Implementation
# 1. Fix the issue
# 2. Sync to worktree (if needed)
# 3. Commit to develop with "Fixes #<number>"
# 4. Push to develop
# 5. Commit to worktree (if modified, ASK USER FIRST)
# 6. Push worktree
# 7. Close the issue
gh issue close <number> -c "Completed: description"
```

### Creating WebSocket Handlers

```bash
# Generate handler with options
python generate_ws_handler.py handler_name PKG_ID_NAME [options]

# Examples:
python generate_ws_handler.py get_status GET_STATUS
python generate_ws_handler.py create_author CREATE_AUTHOR --schema
python generate_ws_handler.py get_authors GET_AUTHORS --paginated
python generate_ws_handler.py delete_author DELETE_AUTHOR --roles admin delete-author
```

### Database Operations

```bash
# Modify model
# Generate migration
make migration msg="Add email field to Author"

# ALWAYS review generated migration!
# Apply migration
make migrate

# Rollback if issues
make rollback
```

### Testing

```bash
# Run tests
make test                    # Parallel (fast)
make test-serial             # Sequential (debugging)
uv run pytest tests/test_file.py::test_name  # Single test

# Coverage
make test-coverage
make test-coverage-parallel

# Load/chaos tests
uv run pytest -m load tests/load/ -v -s
uv run pytest -m chaos tests/chaos/ -v -s
```

## 🔧 Git Commit Format

```bash
git commit -m "$(cat <<'EOF'
<type>: <description>

Fixes #<issue_number>

Detailed explanation if needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Types:** `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

## 📁 Project Structure

```
app/
├── api/
│   ├── http/           # HTTP endpoints (auto-discovered)
│   └── ws/
│       ├── handlers/   # WebSocket handlers
│       ├── consumers/  # WebSocket endpoint classes
│       └── constants.py  # PkgID, RSPCode enums
├── managers/           # Singleton managers (RBAC, Keycloak, WebSocket)
├── middlewares/        # Custom middleware
├── models/             # SQLModel database models
├── repositories/       # Data access layer
├── commands/           # Business logic layer
├── schemas/            # Pydantic request/response models
├── utils/              # Utilities (rate_limiter, metrics/, etc.)
├── storage/            # Database and Redis utilities
└── tasks/              # Background tasks

tests/
├── unit/               # Fast unit tests (no external deps)
├── integration/        # Integration tests (require services)
├── load/               # Performance tests (@pytest.mark.load)
├── chaos/              # Failure tests (@pytest.mark.chaos)
└── mocks/              # Centralized mock factories

docs/
├── claude/             # Developer documentation (this guide structure)
└── architecture/       # Architecture diagrams and design docs

docs_site/              # User-facing documentation (MkDocs)
```

## 🛠️ Development Environment

**Prerequisites:**
- Python 3.13+
- Docker and Docker Compose
- uv (Python package manager)

**First-time setup:**
```bash
# Clone repository
git clone <repo_url>
cd fastapi-http-websocket

# Install dependencies
uv sync

# Install pre-commit hooks
uv tool install prek
prek install -f
prek install --hook-type pre-push -f

# Start services
make build
make start

# Run migrations
make migrate

# Start development server
make serve
```

**Key Environment Variables:**
```bash
# Database
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_IP=localhost
REDIS_PORT=6379

# Keycloak
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=your-client
KEYCLOAK_BASE_URL=http://localhost:8080

# Application
ENV=dev  # dev, staging, production
LOG_LEVEL=DEBUG
LOG_CONSOLE_FORMAT=human  # human or json
RATE_LIMIT_ENABLED=true
```

## 🎯 Quick Reference

**When to use each pattern:**
- New feature → Repository + Command + DI
- HTTP endpoint → FastAPI router with `require_roles()`
- WebSocket handler → `@pkg_router.register()` with roles
- Database query → Repository method
- Business logic → Command class
- Reusable logic → Command (use in both HTTP and WebSocket)

**Testing patterns:**
- Unit tests → `tests/unit/`
- Integration tests → `tests/integration/` with `@pytest.mark.integration`
- Edge cases → Dedicated `test_*_edge_cases.py` files
- Load tests → `tests/load/` with `@pytest.mark.load`
- Use centralized mocks from `tests/mocks/`

**Documentation flow:**
1. Make code changes
2. Update relevant docs in `docs/claude/` or `docs_site/`
3. Verify examples work
4. Commit docs with code in same PR

**Need more details?** See the focused guides in `docs/claude/` listed at the top of this file.
