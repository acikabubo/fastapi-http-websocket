# Testing Guide

This guide explains how to test the application with proper authentication.

## Quick Links

- **Testing HTTP API with Swagger UI**: See [swagger-testing.md](swagger-testing.md) - Complete guide for testing with FastAPI's OpenAPI interface
- **Automated Testing**: See sections below for pytest and mock usage
- **WebSocket Testing**: See [Testing WebSocket Endpoints](#testing-websocket-endpoints) section

## Table of Contents

1. [Test Organization](#test-organization)
2. [Getting Valid Tokens](#getting-valid-tokens)
3. [Debug Mode (Development Only)](#debug-mode-development-only)
4. [Manual Testing](#manual-testing)
5. [Automated Testing with Pytest](#automated-testing-with-pytest)
6. [Using Centralized Test Mocks](#using-centralized-test-mocks)
7. [Testing WebSocket Endpoints](#testing-websocket-endpoints)

---

## Test Organization

Tests are organized into subdirectories by test type for better maintainability and scalability.

### Directory Structure

```
tests/
├── unit/              # Fast unit tests (no external dependencies)
│   ├── commands/      # Command pattern tests
│   │   └── test_author_commands.py
│   ├── repositories/  # Repository pattern tests
│   │   └── test_author_repository.py
│   ├── pagination/    # Pagination logic tests (4 files)
│   ├── schemas/       # Schema validation tests (3 files)
│   ├── middleware/    # Middleware tests (3 files)
│   ├── rbac/          # RBAC tests (3 files)
│   ├── websocket/     # WebSocket utility tests (2 files)
│   ├── utils/         # Utility tests (8 files)
│   ├── edge_cases/    # Edge case tests (2 files)
│   └── test_check.py  # Smoke test
├── integration/       # Integration tests (require external services)
│   ├── test_database.py
│   ├── test_redis.py
│   └── test_keycloak.py
├── load/              # Performance and load tests
│   └── test_websocket_load.py
├── chaos/             # Chaos engineering tests (failure scenarios)
│   ├── test_redis_failures.py
│   ├── test_database_failures.py
│   └── test_keycloak_failures.py
├── mocks/             # Centralized mock factories
│   ├── redis_mocks.py
│   ├── websocket_mocks.py
│   └── auth_mocks.py
└── conftest.py        # Shared fixtures and configuration
```

### Test Categories

**Unit Tests** (`tests/unit/`):
- Test individual functions/classes in isolation
- Use mocks for all external dependencies
- Fast execution (< 1 second per test)
- No database, Redis, or Keycloak required
- Examples: pagination logic, data validation, encoding/decoding

**Integration Tests** (`tests/integration/`):
- Test interaction between components
- Use real external services (Docker containers)
- Slower execution (1-10 seconds per test)
- Marked with `@pytest.mark.integration`
- Examples: database queries, Redis operations, Keycloak authentication

**Load Tests** (`tests/load/`):
- Test performance under high load
- Measure throughput, latency, resource usage
- Very slow execution (10+ seconds)
- Marked with `@pytest.mark.load`
- Examples: 1000 concurrent WebSocket connections, broadcast performance

**Chaos Tests** (`tests/chaos/`):
- Test resilience when dependencies fail
- Simulate failures, timeouts, network partitions
- Marked with `@pytest.mark.chaos`
- Examples: Redis down, database connection loss, Keycloak unavailable

### Running Tests by Category

```bash
# Run unit tests only (fast)
pytest tests/unit/ -v

# Run integration tests (requires Docker)
pytest tests/integration/ -v -m integration

# Run all tests except slow ones
pytest -m "not load and not chaos"

# Run load tests
pytest tests/load/ -v -m load

# Run chaos tests
pytest tests/chaos/ -v -m chaos

# Run all tests in parallel
pytest -n auto
```

### Naming Conventions

**Test Files:**
- `test_<component>_<scenario>.py`
- Examples: `test_pagination_edge_cases.py`, `test_websocket_load.py`

**Test Functions:**
- `test_<what>_<condition>_<expected_result>()`
- Examples: `test_pagination_with_invalid_page_raises_error()`

**Test Classes:**
- `Test<ComponentName><Category>`
- Examples: `TestPaginationProperties`, `TestAuthenticationFailures`

### When Creating New Tests

1. **Determine test type**: Unit, integration, load, or chaos?
2. **Place in correct directory**: Use structure above
3. **Add appropriate markers**: `@pytest.mark.integration`, `@pytest.mark.load`, etc.
4. **Use centralized mocks**: Import from `tests/mocks/` directory
5. **Follow naming conventions**: Clear, descriptive names

**Example:**

```python
# tests/unit/test_pagination_properties.py
import pytest
from hypothesis import given, strategies as st

class TestPaginationProperties:
    """Property-based tests for pagination logic."""

    @given(
        page=st.integers(min_value=1, max_value=100),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_offset_calculation_always_valid(self, page: int, per_page: int):
        """Test that offset calculation is always correct."""
        offset = (page - 1) * per_page
        assert offset >= 0
        assert offset == (page - 1) * per_page
```

---

## Getting Valid Tokens

### Method 1: Using the Token Helper Script (Recommended)

The easiest way to get a valid access token:

```bash
# Get token for user 'acika'
python scripts/get_token.py acika 12345

# Output will show:
# === Access Token ===
# eyJhbGci...
#
# === Token Info ===
# Expires in: 300 seconds
# User: acika
# Roles: ['admin', 'get-authors', ...]
```

**For JSON output:**
```bash
python scripts/get_token.py acika 12345 --json
```

**Include refresh token:**
```bash
python scripts/get_token.py acika 12345 --refresh
```

### Method 2: Direct API Call to Keycloak

```bash
curl -X POST "http://localhost:8080/realms/HW-App/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=acika" \
  -d "password=12345" \
  -d "grant_type=password" \
  -d "client_id=auth-hw-frontend"
```

### Method 3: Use Keycloak Admin Console

1. Navigate to http://localhost:8080
2. Login with admin credentials (admin/admin)
3. Go to your realm → Users
4. Select a user → Credentials → Generate token

---

## Manual Testing

### HTTP Endpoints

**Using cURL:**
```bash
# 1. Get token
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)

# 2. Make authenticated request
curl -X GET "http://localhost:8000/authors" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Using VS Code REST Client (api-testing/api.http):**
```http
@baseUrl = localhost:8000

### GET Request Example
GET http://{{baseUrl}}/authors
Content-Type: application/json
Authorization: Bearer eyJhbGci...YOUR_TOKEN_HERE...
```

**Using HTTPie:**
```bash
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)
http GET localhost:8000/authors "Authorization: Bearer $TOKEN"
```

### WebSocket Endpoints

**Using wscat:**
```bash
# Install wscat
npm install -g wscat

# Get token
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)

# Connect
wscat -c "ws://localhost:8000/web?Authorization=Bearer $TOKEN"

# Send message
{"pkg_id": 1, "req_id": "test-123", "data": {}}
```

**Using VS Code REST Client (api-testing/ws.http):**
```http
WS ws://localhost:8000/web?Authorization=Bearer YOUR_TOKEN_HERE

{"pkg_id": 1, "req_id": "123qweasd"}
```

---

## Automated Testing with Pytest

### Using Mock Authentication (Unit Tests)

The `tests/conftest.py` provides fixtures that mock Keycloak:

```python
import pytest
from app.schemas.request import RequestModel
from app.api.ws.handlers.author_handler import get_authors_handler


@pytest.mark.asyncio
async def test_get_authors_with_mock_auth(
    mock_keycloak_manager, mock_user
):
    """Test handler with mocked authentication."""
    request = RequestModel(
        pkg_id=1,
        req_id="test-123",
        data={"filters": {"name": "Test"}}
    )

    response = await get_authors_handler(request)

    assert response.status_code == 0
    assert isinstance(response.data, list)
```

### Available Fixtures

- `mock_keycloak_token`: Mock token response
- `mock_user_data`: Mock decoded user data
- `mock_user`: UserModel instance
- `mock_keycloak_manager`: Mocked KeycloakManager
- `auth_headers`: Headers with Bearer token
- `admin_user_data`: Admin user with full permissions
- `limited_user_data`: User with limited permissions

### Testing RBAC Permissions

```python
@pytest.mark.asyncio
async def test_permission_denied_for_limited_user(limited_user_data):
    """Test that users without proper roles are denied."""
    user = UserModel(**limited_user_data)
    request = RequestModel(pkg_id=1, req_id="test-123", data={})

    response = await pkg_router.handle_request(user, request)

    assert response.status_code == RSPCode.PERMISSION_DENIED
```

### Integration Tests with Real Keycloak

For integration tests that actually connect to Keycloak:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_keycloak_auth():
    """Integration test with real Keycloak instance."""
    from app.managers.keycloak_manager import KeycloakManager

    kc = KeycloakManager()
    token = kc.login("acika", "12345")

    assert "access_token" in token

    user_data = kc.openid.decode_token(token["access_token"])
    assert user_data["preferred_username"] == "acika"
```

Run integration tests only:
```bash
uv run pytest -m integration
```

---

## Using Centralized Test Mocks

### Why Centralized Mocks?

The project uses **centralized mock factories** located in `tests/mocks/` to promote consistency and reduce code duplication.

**Benefits:**
- ✅ **Consistency**: Same mock behavior across all tests
- ✅ **Maintainability**: Update once in `tests/mocks/`, benefits all tests
- ✅ **Less Code**: ~80 lines eliminated per test file
- ✅ **Discoverability**: Easy to find and reuse existing mocks
- ✅ **Type Safety**: Mocks use `spec` parameter for better IDE support

### Available Mock Factories

#### Redis Mocks (`tests/mocks/redis_mocks.py`)

```python
from tests.mocks.redis_mocks import (
    create_mock_redis_connection,     # Full Redis connection with all operations
    create_mock_rate_limiter,          # RateLimiter instance
    create_mock_connection_limiter,    # ConnectionLimiter instance
)

# Example usage
@pytest.fixture
def mock_redis():
    return create_mock_redis_connection()

async def test_with_redis(mock_redis):
    # Mock already has all methods configured
    result = await mock_redis.get("key")
```

#### WebSocket Mocks (`tests/mocks/websocket_mocks.py`)

```python
from tests.mocks.websocket_mocks import (
    create_mock_websocket,             # WebSocket connection with send/receive
    create_mock_connection_manager,    # ConnectionManager with broadcast
    create_mock_package_router,        # PackageRouter with handle_request
    create_mock_broadcast_message,     # BroadcastDataModel factory
)

# Example usage
async def test_websocket_handler():
    mock_ws = create_mock_websocket()
    # Already has send_json, send_response, accept, close, client.host, etc.
    await handler.on_connect(mock_ws)
```

#### Auth Mocks (`tests/mocks/auth_mocks.py`)

```python
from tests.mocks.auth_mocks import (
    create_mock_keycloak_manager,      # KeycloakManager with login/decode_token
    create_mock_user_model,             # UserModel factory
    create_mock_auth_backend,           # AuthBackend for middleware tests
    create_mock_rbac_manager,           # RBACManager for permission tests
)

# Example usage
async def test_authentication():
    mock_kc = create_mock_keycloak_manager()
    # Already configured with login and decode_token methods
    with patch("app.auth.keycloak_manager", mock_kc):
        result = await auth_backend.authenticate(request)
```

#### Repository Mocks (`tests/mocks/repository_mocks.py`)

```python
from tests.mocks.repository_mocks import (
    create_mock_author_repository,     # AuthorRepository with CRUD ops
    create_mock_crud_repository,        # Generic BaseRepository
)

# Example usage
async def test_with_repo():
    mock_repo = create_mock_author_repository()
    # Configure mock behavior as needed
    mock_repo.get_by_id.return_value = create_author_fixture(id=1)

    author = await mock_repo.get_by_id(1)
    assert author.id == 1
```

### Inline vs Centralized: Comparison

**❌ BAD - Inline mock (hard to maintain)**

```python
@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zremrangebyscore = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.pipeline = MagicMock()
    redis_mock.pipeline.return_value.__aenter__ = AsyncMock()
    redis_mock.pipeline.return_value.__aexit__ = AsyncMock()
    # ... 10 more lines of setup
    return redis_mock
```

**✅ GOOD - Use centralized mock**

```python
from tests.mocks.redis_mocks import create_mock_redis_connection

@pytest.fixture
def mock_redis():
    return create_mock_redis_connection()
```

### When to Use Centralized vs Custom Mocks

**Use Centralized Mocks When:**
- ✅ Testing standard components (Redis, WebSocket, Auth, Repositories)
- ✅ Mock needs common default behavior
- ✅ Multiple tests need the same mock
- ✅ Mock is reusable across test files

**Create Custom Inline Mocks When:**
- ⚠️ Testing very specific edge case behavior
- ⚠️ Mock is used in only one test
- ⚠️ Centralized mock doesn't exist yet (consider adding it!)

### Adding New Centralized Mocks

If you create a mock that could be reused, add it to `tests/mocks/`:

1. **Choose the right file**: `redis_mocks.py`, `auth_mocks.py`, `websocket_mocks.py`, `repository_mocks.py`
2. **Create factory function**: Use `create_mock_*` naming convention
3. **Use `spec` parameter**: For better type safety
4. **Add docstring**: Explain what the mock provides
5. **Update conftest.py**: If it's a common fixture

**Example:**

```python
# tests/mocks/redis_mocks.py
def create_mock_redis_connection() -> AsyncMock:
    """
    Create a mock Redis connection with common operations configured.

    Returns:
        AsyncMock: Configured Redis connection mock
    """
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.zadd = AsyncMock(return_value=1)
    # ... configure other methods
    return redis_mock
```

### Examples in Action

See these refactored test files for proper usage:
- `tests/test_rate_limiting.py` - Redis mock usage
- `tests/test_websocket.py` - WebSocket mock usage
- `tests/test_auth_basic.py` - Keycloak mock usage
- `tests/test_auth_backend.py` - Comprehensive auth testing

**Reference**: See `CLAUDE.md` lines 1539-1650 for comprehensive mock documentation.

---

## Testing WebSocket Endpoints

### Example WebSocket Test

```python
import pytest
from fastapi.testclient import TestClient
from app import application


@pytest.mark.asyncio
async def test_websocket_connection(mock_keycloak_manager):
    """Test WebSocket connection with authentication."""
    client = TestClient(application())

    with client.websocket_connect(
        "/web?Authorization=Bearer mock_token"
    ) as websocket:
        # Send request
        websocket.send_json({
            "pkg_id": 1,
            "req_id": "ws-test-123",
            "data": {}
        })

        # Receive response
        response = websocket.receive_json()

        assert response["pkg_id"] == 1
        assert response["req_id"] == "ws-test-123"
```

---

## Makefile Integration

Add these helpful commands to your workflow:

```bash
# Get token quickly
make get-token USER=acika PASS=12345

# Run tests with coverage
make test-with-coverage
```

Add to Makefile:
```makefile
get-token:
	@python scripts/get_token.py $(USER) $(PASS)

test-with-coverage:
	@uv run pytest --cov=app --cov-report=html
```

---

## Troubleshooting

### Token Expired
**Error:** `JWT token expired`

**Solution:** Tokens expire after 5 minutes. Get a fresh token:
```bash
python scripts/get_token.py acika 12345
```

### Keycloak Not Running
**Error:** Connection refused to hw-keycloak:8080

**Solution:**
```bash
make start  # Start all services including Keycloak
docker ps   # Verify hw-keycloak is running
```

### Invalid Credentials
**Error:** `Invalid credentials`

**Solution:** Verify user exists in Keycloak and credentials are correct:
```bash
# Access Keycloak admin console
open http://localhost:8080
# Login: admin/admin
# Check Users in HW-App realm
```

### Permission Denied
**Error:** `No permission for pkg_id X`

**Solution:** Check handler's `roles` parameter in `@pkg_router.register()` decorator and ensure user has required role:
```bash
# See your roles
python scripts/get_token.py acika 12345
# Output shows: Roles: ['admin', 'get-authors', ...]

# Check handler code for required roles
# Example: @pkg_router.register(PkgID.GET_AUTHORS, roles=["get-authors"])
```

---

## Best Practices

1. **Use Mock Authentication for Unit Tests**: Fast and reliable
2. **Use Real Tokens for Integration Tests**: Catch real-world issues
3. **Never commit tokens**: Tokens in git history are security risks
4. **Rotate tokens regularly**: Even in development
5. **Test with different user roles**: Verify RBAC properly
6. **Use Property-Based Testing**: Catch edge cases automatically with Hypothesis

---

## Property-Based Testing with Hypothesis

### What is Property-Based Testing?

Property-based testing automatically generates test cases to verify that code properties hold for a wide range of inputs. Instead of writing specific examples, you define properties that should always be true.

**Benefits:**
- Catches edge cases you wouldn't think to test manually
- One property test replaces dozens of example tests
- Automatically finds minimal failing cases
- Tests thousands of input combinations

### Installation

Hypothesis is included in dev dependencies:

```bash
uv sync --group dev
```

### Example: Testing Pagination Properties

```python
from hypothesis import given, strategies as st
import pytest

class TestPaginationProperties:
    @given(
        page=st.integers(min_value=1, max_value=100),
        per_page=st.integers(min_value=1, max_value=100),
    )
    def test_page_calculation_properties(self, page: int, per_page: int) -> None:
        """
        Test mathematical properties of pagination calculations.

        Properties:
        1. offset = (page - 1) * per_page
        2. offset is always >= 0
        """
        offset = (page - 1) * per_page

        assert offset == (page - 1) * per_page
        assert offset >= 0
        assert offset + per_page == page * per_page
```

### Running Property-Based Tests

```bash
# Run property-based tests
pytest tests/test_pagination_property_based.py -v

# Hypothesis runs 100 examples by default
# Example output:
# test_page_calculation_properties PASSED (ran 100 examples)
```

### Common Use Cases

**1. Reversible Operations:**
```python
@given(st.text())
def test_encoding_roundtrip(self, value: str) -> None:
    """Test that decode(encode(x)) == x"""
    encoded = encode_cursor(value)
    decoded = decode_cursor(encoded)
    assert decoded == value
```

**2. Boundary Conditions:**
```python
@given(st.integers(min_value=-100, max_value=0))
def test_invalid_pages_rejected(self, invalid_page: int) -> None:
    """Test that page <= 0 raises ValueError"""
    with pytest.raises(ValueError):
        get_paginated_results(Model, page=invalid_page, per_page=10)
```

**3. Data Validation:**
```python
@given(st.dictionaries(keys=st.text(), values=st.integers()))
def test_filters_json_serializable(self, filters: dict) -> None:
    """Test that filters are always JSON-serializable"""
    import json
    serialized = json.dumps(filters)
    assert json.loads(serialized) == filters
```

### Best Practices

- Start with simple mathematical properties
- Use realistic input bounds
- Combine with example-based tests
- Document what property is being tested
- Let Hypothesis automatically shrink failing cases

### See Also

- Example file: `tests/test_pagination_property_based.py`
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- CLAUDE.md section on Property-Based Testing

---

## Example Test File

See `tests/test_auth_example.py` for a complete example of testing with authentication.
