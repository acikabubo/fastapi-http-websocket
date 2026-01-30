# Code Quality Guide

This guide covers code linting, security scanning, pre-commit hooks, dead code detection, and coding standards.

## Table of Contents

- [Code Quality & Linting](#code-quality--linting)
- [Security Scanning](#security-scanning)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Dead Code Detection](#dead-code-detection)
- [Code Style Requirements](#code-style-requirements)
- [Docstring Style Guide](#docstring-style-guide)
- [Automated Dependency Updates](#automated-dependency-updates)
- [Type Safety](#type-safety)
- [Related Documentation](#related-documentation)

## Code Quality & Linting

### Commands

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

## Security Scanning

```bash
# SAST scanning with Bandit
make bandit-scan

# Dependency vulnerability scanning
make skjold-scan

# Check for outdated packages
make outdated-pkgs-scan
```

## Pre-commit Hooks

**Hook Manager**: We use **prek** (Rust-based, 3-10x faster than pre-commit) for running pre-commit hooks.

### Required Hooks

All commits must pass:
- **ruff**: Linting and formatting with auto-fix (79 char line length, removes unused imports)
- **mypy**: Strict type checking
- **interrogate**: ≥80% docstring coverage
- **typos**: Spell checking
- **bandit**: Security scanning (low severity threshold `-lll`)
- **skjold**: Dependency vulnerability checks
- **vulture**: Dead code detection (100% confidence, runs on `git push` only)
- **pytest-cov**: Code coverage checker (≥80% coverage, runs on `git push` only)

### Installing Hooks

```bash
# Install prek (recommended - 3-10x faster)
uv tool install prek
prek install -f
prek install --hook-type pre-push -f

# Alternative: Use pre-commit (slower but more mature)
uvx pre-commit install
uvx pre-commit install --hook-type pre-push
```

### Rollback to pre-commit

```bash
prek uninstall
prek uninstall --hook-type pre-push
uvx pre-commit install
uvx pre-commit install --hook-type pre-push
```

### Why prek?

- 3-10x faster hook execution (typical: 2s vs 10-20s)
- 50% less disk space usage
- Drop-in replacement (uses same `.pre-commit-config.yaml`)
- Automatic stashing of unstaged changes
- Used by CPython, Apache Airflow, FastAPI, Home Assistant

**Note**: Both prek and pre-commit use the same `.pre-commit-config.yaml` file, so switching between them is seamless.

### Running Tests with Coverage

```bash
# Run tests with coverage report
uv run pytest --cov=app --cov-report=term-missing

# Run tests with HTML coverage report
uv run pytest --cov=app --cov-report=html

# View HTML coverage report
open htmlcov/index.html
```

### Coverage Configuration

Coverage settings are in `pyproject.toml`:
- Minimum coverage threshold: 80%
- Omitted files: `__init__.py`, `__main__.py`, tests, logging, routing, settings
- Excluded lines: `pragma: no cover`, imports, pass statements

**Note**: The coverage hook only runs on `git push` (not on every commit) to avoid slowing down the development workflow.

## Dead Code Detection

The project uses **vulture** (dead code detector) and **ruff** (with auto-fix) to keep the codebase clean.

### Pre-commit Hooks

- **ruff**: Automatically fixes lint violations including unused imports (F401) and unused variables (F841) on every commit
- **vulture**: Detects unused functions, classes, and variables on `git push` (100% confidence)

### Manual Commands

```bash
# Scan for dead code (uses min_confidence from pyproject.toml)
make dead-code-scan
# Or: uvx vulture app/

# Fix dead code (remove unused imports + re-scan)
make dead-code-fix
```

### Configuration

From `pyproject.toml`:

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

### Vulture Confidence Levels

- **100%**: Definitely dead (unused imports, unreachable code) - ruff auto-fixes unused imports (F401), vulture detects other dead code
- **80-99%**: Very likely dead (unused functions) - not reported with 100% threshold
- **60-79%**: Probably dead (may be false positive) - not reported with 100% threshold
- **<60%**: Uncertain (many false positives) - not reported with 100% threshold

**Note**: With `min_confidence = 100`, vulture only reports absolutely certain dead code.

### Handling False Positives

```python
# Option 1: Add to vulture whitelist in pyproject.toml
# See ignore_names, ignore_decorators above

# Option 2: Add # noqa: vulture comment
def used_in_tests_only():  # noqa: vulture
    pass

# Option 3: Reference in __all__ or import in __init__.py
__all__ = ["may_be_used_dynamically"]
```

### Workflow

1. Developer commits code → ruff auto-fixes lint violations (including unused imports)
2. Developer pushes code → vulture checks for unused functions/classes (100% confidence)
3. If dead code found → fix and commit → push succeeds

### Benefits

- ✅ Cleaner codebase with less noise
- ✅ Easier navigation and code reviews
- ✅ Faster imports and smaller bundles
- ✅ Safe refactoring (unused code caught early)
- ✅ Automated enforcement via pre-commit hooks

## Code Style Requirements

- **Line length**: 79 characters (enforced by ruff)
- **Type hints**: Required on all functions (mypy --strict)
- **Docstrings**: Required on all public functions, classes, and methods (80% coverage minimum)
- **Formatting**: Double quotes, 4-space indentation
- **Unused code**: Will be caught by vulture (see `pyproject.toml` for ignored names)

## Docstring Style Guide

All public functions, classes, and methods must have comprehensive docstrings following **Google-style** format.

### Required Sections

1. **One-line summary** - Imperative mood, ends with period
2. **Extended description** - Optional, for complex functions
3. **Args** - All parameters with types and descriptions
4. **Returns** - Return type and description
5. **Raises** - Expected exceptions (optional)
6. **Examples** - 2-3 realistic usage examples (required for complex functions)

### Example Docstring

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

### When to Add Examples

- ✅ Complex functions with 3+ parameters
- ✅ Functions with non-obvious usage patterns
- ✅ Public API functions used by other developers
- ✅ Functions with conditional behavior or edge cases
- ❌ Simple getters/setters
- ❌ Private utility functions (unless complex)

### Example Guidelines

- Use `>>>` for doctest-style examples
- Show 2-3 realistic use cases
- Include error handling examples
- Demonstrate optional parameters
- Keep examples concise but complete

### Verification

Run `uvx interrogate app/` to check docstring coverage (must be ≥80%).

## Automated Dependency Updates

### Dependabot Configuration

The project uses GitHub Dependabot for automated dependency updates. Configuration is in `.github/dependabot.yml`.

### Update Schedule

- **Python dependencies** (pip): Weekly on Mondays at 09:00 Europe/Skopje time
- **GitHub Actions**: Weekly on Mondays at 09:00 Europe/Skopje time
- **Docker images**: Weekly on Mondays at 09:00 Europe/Skopje time

### Grouping Strategy

- Minor and patch updates are grouped together to reduce PR noise
- Major version updates create separate PRs for careful review

### Pull Request Management

- Maximum 10 open PRs for Python dependencies
- Maximum 5 open PRs for GitHub Actions and Docker
- PRs are labeled with `dependencies` and ecosystem-specific labels
- Automatic reviewer assignment

### Commit Message Format

- Python dependencies: `deps: Update package-name from X to Y`
- Development dependencies: `deps(dev): Update package-name from X to Y`
- GitHub Actions: `deps(actions): Update action-name from X to Y`
- Docker: `deps(docker): Update image-name from X to Y`

### Reviewing Dependabot PRs

1. **Check CI Status**: Ensure all tests pass
2. **Review Changelog**: Check breaking changes in package release notes
3. **Test Locally**: For major updates, test locally before merging
4. **Merge Strategy**:
   - Patch updates: Can be auto-merged if tests pass
   - Minor updates: Review changelog, merge if no breaking changes
   - Major updates: Careful review, test locally, update code if needed

### Dependabot Commands

Interact with Dependabot via PR comments:
- `@dependabot rebase` - Rebase the PR
- `@dependabot recreate` - Recreate the PR (ignore local edits)
- `@dependabot merge` - Merge the PR (after approvals)
- `@dependabot squash and merge` - Squash and merge
- `@dependabot cancel merge` - Cancel a merge request
- `@dependabot close` - Close the PR and don't create updates
- `@dependabot ignore this dependency` - Close and ignore future updates
- `@dependabot ignore this major version` - Ignore major version updates
- `@dependabot ignore this minor version` - Ignore minor version updates

### Security Updates

Dependabot also creates PRs for security vulnerabilities automatically (not on schedule). These should be reviewed and merged with high priority.

## Type Safety

This project uses advanced typing features for improved type safety and IDE support.

### Return Type Guidelines

1. **Functions that return nothing** - Use `-> None`:
   ```python
   async def send_notification(user_id: str, message: str) -> None:
       await notification_service.send(user_id, message)
   ```

2. **Functions that never return** (infinite loops, always raise) - Use `-> NoReturn`:
   ```python
   from typing import NoReturn

   async def background_task() -> NoReturn:
       """Task that runs forever."""
       while True:
           await asyncio.sleep(10)
           await do_work()
   ```

3. **Functions with optional returns** - Use `-> ReturnType | None`:
   ```python
   async def get_user(user_id: int) -> User | None:
       """Returns User or None if not found."""
       return await db.query(User).filter(User.id == user_id).first()
   ```

4. **Generic collections** - Use specific type parameters:
   ```python
   # ✅ Good
   def get_authors() -> list[Author]:
       return [Author(id=1, name="John")]

   def get_config() -> dict[str, Any]:
       return {"key": "value", "count": 42}

   # ❌ Bad
   def get_authors() -> list:  # What's in the list?
       return [Author(id=1, name="John")]
   ```

5. **Async context managers** - Use `-> AsyncGenerator`:
   ```python
   from collections.abc import AsyncGenerator

   async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
       """FastAPI lifespan context manager."""
       await initialize_services()
       yield
       await cleanup_services()
   ```

6. **Middleware dispatch methods** - Use `-> Response`:
   ```python
   from starlette.types import ASGIApp

   async def dispatch(
       self, request: Request, call_next: ASGIApp
   ) -> Response:
       response = await call_next(request)
       return response
   ```

### mypy Configuration

The project enforces strict type checking via `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
disallow_untyped_defs = true  # Requires return types
```

Run `uvx mypy app/` to verify type correctness before committing.

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Architecture Guide](architecture-guide.md) - Design patterns, components, request flow
- [Development Guide](development-guide.md) - Running the app, Docker, WebSocket handlers
- [Testing Guide](testing-guide.md) - Test infrastructure, fixtures, load/chaos tests
- [Configuration Guide](configuration-guide.md) - Settings, environment variables, validation
- [Database Guide](database-guide.md) - Sessions, migrations, pagination, relationships
- [Monitoring Guide](monitoring-guide.md) - Prometheus, alerts, logging, dashboards
