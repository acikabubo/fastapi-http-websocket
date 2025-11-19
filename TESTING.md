# Testing Guide

This guide explains how to debug and test the application after removing the hardcoded authentication bypass.

## Table of Contents

1. [Getting Valid Tokens](#getting-valid-tokens)
2. [Debug Mode (Development Only)](#debug-mode-development-only)
3. [Manual Testing](#manual-testing)
4. [Automated Testing with Pytest](#automated-testing-with-pytest)
5. [Testing WebSocket Endpoints](#testing-websocket-endpoints)

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

## Debug Mode (Development Only)

For quick local testing, you can enable debug mode to bypass token validation.

**⚠️ WARNING: NEVER enable DEBUG_AUTH in production!**

### Enable Debug Mode

**Option 1: Environment Variable**
```bash
export DEBUG_AUTH=true
uvicorn app:application --reload
```

**Option 2: In docker/.srv_env**
```bash
# Add to docker/.srv_env
DEBUG_AUTH=true
```

**Option 3: Override defaults**
```bash
# Custom debug user
export DEBUG_AUTH=true
export DEBUG_AUTH_USERNAME=testuser
export DEBUG_AUTH_PASSWORD=testpass
```

When DEBUG_AUTH is enabled, you'll see a warning in logs:
```
WARNING - DEBUG_AUTH is enabled - using debug credentials. NEVER enable this in production!
```

### Disable Debug Mode

```bash
unset DEBUG_AUTH
# or
export DEBUG_AUTH=false
```

---

## Manual Testing

### HTTP Endpoints

**Using cURL:**
```bash
# 1. Get token
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)

# 2. Make authenticated request
curl -X GET "http://localhost:8001/authors" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Using VS Code REST Client (api-testing/api.http):**
```http
@baseUrl = localhost:8001

### GET Request Example
GET http://{{baseUrl}}/authors
Content-Type: application/json
Authorization: Bearer eyJhbGci...YOUR_TOKEN_HERE...
```

**Using HTTPie:**
```bash
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)
http GET localhost:8001/authors "Authorization: Bearer $TOKEN"
```

### WebSocket Endpoints

**Using wscat:**
```bash
# Install wscat
npm install -g wscat

# Get token
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)

# Connect
wscat -c "ws://localhost:8001/web?Authorization=Bearer $TOKEN"

# Send message
{"pkg_id": 1, "req_id": "test-123", "data": {}}
```

**Using VS Code REST Client (api-testing/ws.http):**
```http
WS ws://localhost:8001/web?Authorization=Bearer YOUR_TOKEN_HERE

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

# Start server in debug mode
make serve-debug
```

Add to Makefile:
```makefile
get-token:
	@python scripts/get_token.py $(USER) $(PASS)

test-with-coverage:
	@uv run pytest --cov=app --cov-report=html

serve-debug:
	@export DEBUG_AUTH=true && uvicorn app:application --reload
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

**Solution:** Check user roles in `actions.json` and ensure user has required role:
```bash
# See your roles
python scripts/get_token.py acika 12345
# Output shows: Roles: ['admin', 'get-authors', ...]
```

---

## Best Practices

1. **Use Mock Authentication for Unit Tests**: Fast and reliable
2. **Use Real Tokens for Integration Tests**: Catch real-world issues
3. **Never commit tokens**: Tokens in git history are security risks
4. **Rotate tokens regularly**: Even in development
5. **Disable DEBUG_AUTH in CI/CD**: Force proper authentication in pipelines
6. **Test with different user roles**: Verify RBAC properly

---

## Example Test File

See `tests/test_auth_example.py` for a complete example of testing with authentication.
