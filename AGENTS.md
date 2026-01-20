# AGENTS.md - Coding Guidelines for AI Agents

This document provides essential information for AI coding agents working with this FastAPI HTTP & WebSocket project.

## Build/Lint/Test Commands

### Development Server
```bash
# Start FastAPI application with hot-reload (local development)
make serve

# Or directly:
uvicorn app:application --host 0.0.0.0 --reload
```

### Testing Commands
```bash
# Run all tests in parallel (default)
make test
# Equivalent to: uv run pytest -n auto tests

# Run a single test file
uv run pytest tests/test_check.py

# Run a specific test function
uv run pytest tests/test_check.py::test_function_name

# Run tests sequentially (without parallelization)
make test-serial
# Equivalent to: uv run pytest tests

# Run tests with coverage report
make test-coverage
# Equivalent to: uv run pytest --cov=app --cov-report=term-missing --cov-report=html tests

# Run only unit tests (exclude integration, load, chaos)
make test-unit
# Equivalent to: uv run pytest -m "not integration and not load and not chaos" tests

# Run integration tests (requires Docker, run OUTSIDE container)
make test-integration
# Equivalent to: uv run pytest -m integration tests/integration/ -v -s

# Run load tests
uv run pytest -m load tests/load/ -v -s

# Run chaos engineering tests
uv run pytest -m chaos tests/chaos/ -v -s
```

### Linting and Code Quality
```bash
# Run ruff linter (check only, no fixes)
make ruff-check
# Equivalent to: uvx ruff check --config=pyproject.toml

# Run ruff formatter
uvx ruff format

# Run mypy static type checker
uvx mypy app/

# Check docstring coverage (must be ≥80%)
uvx interrogate app/

# Spell checking
uvx typos

# Security scanning with Bandit
make bandit-scan

# Dependency vulnerability scanning
make skjold-scan

# Find dead code
make dead-code-scan
# Equivalent to: uvx vulture app/
```

### Pre-commit Hooks
The project uses pre-commit hooks that run automatically on commit:
- ruff (linting and formatting)
- mypy (static type checking)
- interrogate (docstring coverage ≥80%)
- typos (spell checking)
- bandit (security scanning)
- skjold (dependency vulnerability scanning)
- pytest-cov (code coverage ≥80%, runs on push only)

## Code Style Guidelines

### Imports
1. Group imports in order: standard library, third-party, local
2. Use explicit imports: `from module import ClassName` instead of `from module import *`
3. Place imports at the top of the file, after module comments and docstrings
4. Separate import groups with blank lines

### Formatting
1. Line length: 79 characters maximum (enforced by ruff)
2. Indentation: 4 spaces (no tabs)
3. Quote style: Double quotes for strings, single quotes for internal quoting
4. Use trailing commas in multiline constructs

### Type Hints
1. All functions must have type annotations for parameters and return values
2. Use `typing` module for complex types (Union, Optional, List, Dict, etc.)
3. Prefer `list[Type]` over `List[Type]` (Python 3.9+ syntax)
4. Use `| None` instead of `Optional[Type]` for optional parameters

### Naming Conventions
1. Variables: `snake_case`
2. Functions: `snake_case`
3. Classes: `PascalCase`
4. Constants: `UPPER_SNAKE_CASE`
5. Private members: prefixed with underscore `_private_variable`

### Error Handling
1. Use custom exception classes defined in `app/exceptions.py`
2. Handle exceptions at the appropriate level
3. Log errors with sufficient context for debugging
4. Return appropriate HTTP status codes for HTTP endpoints
5. Use ResponseModel with appropriate RSPCode for WebSocket handlers

### Documentation
1. All public functions, classes, and methods must have docstrings
2. Use Google-style docstrings with Args/Returns sections
3. Include examples in docstrings where appropriate
4. Keep docstrings up-to-date with code changes

### Testing
1. Use pytest with asyncio support
2. Follow the existing test structure in the `tests/` directory
3. Use centralized fixtures from `tests/conftest.py`
4. Use mock factories from `tests/mocks/` instead of creating inline mocks
5. Test both positive and negative cases
6. Use appropriate test markers (integration, load, chaos)

### Database and ORM
1. Use Repository pattern for database operations
2. Use SQLModel for ORM operations
3. Always use async sessions with proper context managers
4. Use eager loading for relationships when needed
5. Follow pagination patterns using `get_paginated_results()`

### WebSocket Handlers
1. Register handlers with `@pkg_router.register()`
2. Use appropriate PkgID from `app/api/ws/constants.py`
3. Validate input data with JSON schema when needed
4. Implement RBAC with roles parameter
5. Return ResponseModel with appropriate status codes
6. Handle exceptions and return error responses appropriately

### Security
1. Always validate and sanitize input data
2. Use dependency injection for authentication and authorization
3. Follow RBAC patterns with `require_roles()` dependency
4. Implement proper error handling without leaking sensitive information
5. Use secure headers middleware
6. Implement rate limiting where appropriate

### Performance
1. Use connection pooling for database and Redis
2. Implement caching where beneficial
3. Use efficient database queries with proper indexing
4. Avoid N+1 query problems with eager loading
5. Use async/await patterns appropriately
6. Monitor and optimize slow queries

These guidelines ensure consistency with the existing codebase and maintain high-quality standards for all contributions.
