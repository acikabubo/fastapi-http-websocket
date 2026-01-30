# Testing Guide

This guide covers test infrastructure, centralized fixtures and mocks, load testing, chaos engineering, and test organization.

## Table of Contents

- [Running Tests](#running-tests)
- [Testing Infrastructure](#testing-infrastructure)
- [Test Organization](#test-organization)
- [Centralized Test Mocks](#centralized-test-mocks)
- [Edge Case Testing](#edge-case-testing)
- [Property-Based Testing](#property-based-testing)
- [Test Coverage](#test-coverage)
- [Related Documentation](#related-documentation)

## Running Tests

### Basic Test Commands

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

## Testing Infrastructure

### Parallel Test Execution (pytest-xdist)

- Tests run in parallel by default using all available CPU cores (`-n auto`)
- 3-5x faster test execution compared to sequential runs
- Automatically distributes tests across workers
- Use `make test-serial` for debugging or when parallel execution causes issues

### Centralized Fixtures and Mocks

- Common fixtures defined in `tests/conftest.py`
- Fixture factories for creating test data:
  - `create_author_fixture()`
  - `create_request_model_fixture()`
  - `create_response_model_fixture()`
- Reusable mock factories in `tests/mocks/`:
  - `repository_mocks.py` - Repository and CRUD operation mocks
  - `auth_mocks.py` - Keycloak, AuthBackend, UserModel, RBAC mocks
  - `redis_mocks.py` - Redis connection and rate limiter mocks
  - `keycloak_mocks.py` - KeycloakOpenID and KeycloakAdmin mocks
  - `websocket_mocks.py` - WebSocket connection, consumer, and manager mocks

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

### Load Testing

WebSocket load tests in `tests/load/test_websocket_load.py`:

**Test scenarios:**
- 100 concurrent connections (< 1s connection time, < 2s broadcast time)
- 1000 concurrent connections (< 5s connection time, < 10s broadcast time)
- Connection churn (500 rapid connect/disconnect cycles < 5s)
- High-frequency broadcasts (> 500 messages/sec throughput)
- Large message broadcasting (~100KB payloads)
- Partial connection failures (20% failure rate resilience)
- Concurrent broadcasts (10 simultaneous broadcasts)

Run with: `pytest -m load tests/load/ -v -s`

### Chaos Engineering Tests

Failure scenario testing in `tests/chaos/`:

**Redis failure tests** (`test_redis_failures.py`):
- Redis unavailable (fail-open behavior)
- Connection timeouts and errors
- Partial operation failures (INCR succeeds, EXPIRE fails)
- Intermittent failures and recovery

**Database failure tests** (`test_database_failures.py`):
- Database connection loss
- Query timeouts
- Transaction rollbacks
- Connection pool exhaustion
- Network partition scenarios

**Keycloak failure tests** (`test_keycloak_failures.py`):
- Keycloak server unavailable
- Authentication errors
- Token validation failures
- Service degradation (partial failures)
- Configuration errors

Run with: `pytest -m chaos tests/chaos/ -v -s`

### Test Markers

- `@pytest.mark.integration` - Integration tests requiring external services (Keycloak, PostgreSQL, Redis)
- `@pytest.mark.load` - Load tests with high resource usage (skip by default)
- `@pytest.mark.chaos` - Chaos engineering tests simulating failures (skip by default)

## Test Organization

Tests are organized into subdirectories by test type for better maintainability and clarity:

```
tests/
├── unit/              # Fast unit tests (no external dependencies)
│   ├── commands/      # Command pattern tests
│   ├── repositories/  # Repository pattern tests
│   ├── pagination/    # Pagination logic tests
│   ├── schemas/       # Schema validation tests
│   ├── middleware/    # Middleware tests
│   ├── rbac/          # RBAC and permissions tests
│   ├── websocket/     # WebSocket utility tests
│   ├── utils/         # Utility function tests
│   ├── edge_cases/    # Cross-cutting edge case tests
│   └── test_check.py  # Smoke test
├── integration/       # Integration tests (require external services)
│   ├── test_database.py
│   ├── test_redis.py
│   └── test_keycloak.py
├── load/              # Performance and load tests (@pytest.mark.load)
│   └── test_websocket_load.py
├── chaos/             # Chaos engineering tests (@pytest.mark.chaos)
│   ├── test_redis_failures.py
│   ├── test_database_failures.py
│   └── test_keycloak_failures.py
├── mocks/             # Centralized mock factories
│   ├── redis_mocks.py
│   ├── websocket_mocks.py
│   └── auth_mocks.py
└── conftest.py        # Shared fixtures and configuration
```

### Directory Guidelines

**Unit Tests** (`tests/unit/`):
- Test individual functions/classes in isolation
- Use mocks for all external dependencies
- Fast execution (< 1 second per test)
- No database, Redis, or Keycloak required
- Examples: pagination logic, data validation, encoding/decoding

**Integration Tests** (`tests/integration/`):
- Test interaction between components
- May use real external services (Docker containers)
- Slower execution (1-10 seconds per test)
- Marked with `@pytest.mark.integration`
- Examples: database queries, Redis operations, Keycloak auth

**Load Tests** (`tests/load/`):
- Test performance under high load
- Measure throughput, latency, resource usage
- Very slow execution (10+ seconds)
- Marked with `@pytest.mark.load`
- Examples: 1000 concurrent WebSocket connections, high-frequency broadcasts

**Chaos Tests** (`tests/chaos/`):
- Test resilience when dependencies fail
- Simulate failures, timeouts, network issues
- Marked with `@pytest.mark.chaos`
- Examples: Redis unavailable, database connection loss, Keycloak errors

### When Creating New Tests

1. **Determine test type**: Is it unit, integration, load, or chaos?
2. **Place in correct directory**: Use the directory structure above
3. **Use appropriate markers**: `@pytest.mark.integration`, `@pytest.mark.load`, `@pytest.mark.chaos`
4. **Follow naming convention**: `test_<component>_<scenario>.py`
5. **Use centralized mocks**: Import from `tests/mocks/` instead of creating inline

### Running Tests by Category

```bash
# Run all unit tests (fast)
pytest tests/unit/ -v

# Run integration tests (requires Docker services)
pytest tests/integration/ -v -m integration

# Run all tests except slow ones
pytest -m "not load and not chaos"

# Run specific category
pytest tests/chaos/ -v -m chaos

# Run all tests in parallel
pytest -n auto
```

## Centralized Test Mocks

**CRITICAL:** Always use centralized mock factories from `tests/mocks/` instead of creating inline mocks.

### Available Mock Factories

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

### Benefits

- ✅ **Consistency:** Same mock behavior across all tests
- ✅ **Maintainability:** Update once in `tests/mocks/`, benefits all tests
- ✅ **Less Code:** ~80 lines eliminated in just 4 refactored files
- ✅ **Discoverability:** Easy to find and reuse existing mocks
- ✅ **Type Safety:** Mocks use `spec` parameter for better IDE support

### When Creating New Tests

1. Check `tests/mocks/` first - the mock you need probably exists
2. If creating a new mock, add it to the appropriate `tests/mocks/*.py` file
3. Never create inline mocks - always use or extend centralized factories

## Edge Case Testing

**IMPORTANT**: Always write edge case tests for critical components.

### What Are Edge Cases?

- Invalid input (malformed data, wrong types, missing fields)
- Boundary conditions (zero, negative, maximum values)
- Resource failures (database down, Redis unavailable, connection drops)
- Concurrent operations (race conditions, deadlocks)
- Unusual state combinations (empty results, overflow, underflow)

### Dedicated Edge Case Test Files

- `tests/test_websocket_edge_cases.py` - WebSocket consumer edge cases (14 tests)
- `tests/test_rate_limiter_edge_cases.py` - Rate limiter edge cases (19 tests)
- `tests/test_audit_edge_cases.py` - Audit logger edge cases (15 tests)
- `tests/test_pagination_edge_cases.py` - Pagination edge cases (16 tests)

### When to Write Edge Case Tests

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

## Property-Based Testing

Property-based testing uses automated test case generation (via Hypothesis) to verify that code properties hold for a wide range of inputs.

### Benefits

- ✅ **Comprehensive Coverage**: Tests thousands of edge cases automatically
- ✅ **Bug Discovery**: Finds edge cases you wouldn't think to test manually
- ✅ **Less Maintenance**: One property test replaces dozens of example tests
- ✅ **Better Documentation**: Properties clearly express code invariants

### Example: Pagination Properties

```python
from hypothesis import given, strategies as st
import pytest

class TestPaginationProperties:
    """Property-based tests for pagination logic."""

    @given(
        page=st.integers(min_value=1, max_value=100),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_page_calculation_properties(self, page: int, per_page: int) -> None:
        """
        Test mathematical properties of pagination calculations.

        Properties tested:
        1. offset = (page - 1) * per_page
        2. offset is always >= 0
        3. offset + per_page represents the end index
        """
        offset = (page - 1) * per_page

        # Property 1: Offset calculation is correct
        assert offset == (page - 1) * per_page

        # Property 2: Offset is always non-negative
        assert offset >= 0

        # Property 3: End index is offset + per_page
        end_index = offset + per_page
        assert end_index == page * per_page
```

### Running Property-Based Tests

```bash
# Run property-based tests
pytest tests/test_pagination_property_based.py -v

# Hypothesis will generate hundreds of test cases automatically
```

See `tests/test_pagination_property_based.py` for more examples.

## Test Coverage

### Coverage Configuration

Coverage settings are in `pyproject.toml`:
- Minimum coverage threshold: 80%
- Omitted files: `__init__.py`, `__main__.py`, tests, logging, routing, settings
- Excluded lines: `pragma: no cover`, imports, pass statements

### Running Coverage Reports

```bash
# Run tests with coverage report
uv run pytest --cov=app --cov-report=term-missing

# Run tests with HTML coverage report
uv run pytest --cov=app --cov-report=html

# View HTML coverage report
open htmlcov/index.html
```

**Note**: The coverage hook only runs on `git push` (not on every commit) to avoid slowing down development.

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Architecture Guide](architecture-guide.md) - Design patterns, components, request flow
- [Development Guide](development-guide.md) - Running the app, Docker, WebSocket handlers
- [Code Quality Guide](code-quality-guide.md) - Linting, type checking, pre-commit hooks
- [Configuration Guide](configuration-guide.md) - Settings, environment variables, validation
- [Database Guide](database-guide.md) - Sessions, migrations, pagination, relationships
- [Monitoring Guide](monitoring-guide.md) - Prometheus, alerts, logging, dashboards
