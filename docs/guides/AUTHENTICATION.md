# Authentication Guide

Complete guide to authentication in the FastAPI HTTP/WebSocket application.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Keycloak Setup](#keycloak-setup)
4. [Getting Tokens](#getting-tokens)
5. [Using Tokens](#using-tokens)
6. [Development Workflow](#development-workflow)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This application uses **Keycloak** for authentication with **JWT (JSON Web Tokens)**. All endpoints except those in `EXCLUDED_PATHS` require authentication.

### Authentication Flow

```
1. User authenticates with Keycloak (username/password)
2. Keycloak returns JWT access token
3. Client includes token in every request
4. Server validates token and extracts user info + roles
5. RBAC checks if user has required role for endpoint
6. Request proceeds or returns 403 Forbidden
```

### Key Components

- **Keycloak**: OpenID Connect / OAuth 2.0 provider
- **JWT Tokens**: Contain user identity and roles
- **RBAC**: Role-based access control for endpoints
- **Middleware**: Validates tokens on every request

---

## Quick Start

### Get a Token

```bash
# Using the helper script
python scripts/get_token.py <username> <password>

# Example:
python scripts/get_token.py acika 12345
```

Copy the access token from the output.

### Use the Token

**HTTP Request** (with curl):
```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8000/authors
```

**WebSocket Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/web?Authorization=Bearer YOUR_TOKEN_HERE');
```

---

## Keycloak Setup

### Configuration

Set these environment variables (or use defaults from `app/settings.py`):

```bash
# Keycloak server
KEYCLOAK_BASE_URL=http://hw-keycloak:8080/

# Realm and client
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=your-client-id

# Admin credentials (for token generation scripts)
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin-password
```

### Docker Setup

Start Keycloak with docker-compose:

```bash
make start  # Starts all services including Keycloak
```

### Manual Setup

1. Access Keycloak Admin Console: http://localhost:8080/
2. Create a realm (e.g., "my-app")
3. Create a client:
   - Client ID: "fastapi-client"
   - Access Type: "confidential" or "public"
   - Valid Redirect URIs: "*" (for development)
4. Create users and assign roles
5. Update `.env` with your configuration

---

## Getting Tokens

### Option 1: Helper Script (Recommended)

```bash
python scripts/get_token.py USERNAME PASSWORD

# Options:
python scripts/get_token.py USERNAME PASSWORD --json    # Full JSON response
python scripts/get_token.py USERNAME PASSWORD --refresh # Include refresh token
```

**Output:**
```
Access Token:
eyJhbGciOiJSUzI1NiIsInR5cC...

Expires in: 300 seconds
```

### Option 2: Direct API Call

```bash
curl -X POST "http://localhost:8080/realms/YOUR_REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "username=USERNAME" \
  -d "password=PASSWORD" \
  -d "grant_type=password"
```

### Option 3: Python Code

```python
from app.managers.keycloak_manager import KeycloakManager

kc = KeycloakManager()
token_response = kc.login("username", "password")
access_token = token_response["access_token"]
```

---

## Using Tokens

### HTTP Requests

#### With curl

```bash
TOKEN="your-access-token-here"

# GET request
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/authors

# POST request
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Author"}' \
  http://localhost:8000/authors
```

#### With Python requests

```python
import requests

token = "your-access-token"
headers = {"Authorization": f"Bearer {token}"}

# GET
response = requests.get("http://localhost:8000/authors", headers=headers)

# POST
response = requests.post(
    "http://localhost:8000/authors",
    headers=headers,
    json={"name": "New Author"}
)
```

#### With httpie

```bash
http GET localhost:8000/authors \
  Authorization:"Bearer YOUR_TOKEN"
```

### WebSocket Connections

#### JavaScript

```javascript
// Token in query parameter
const token = "your-access-token";
const ws = new WebSocket(`ws://localhost:8000/web?Authorization=Bearer ${token}`);

ws.onopen = () => {
    console.log('Connected');

    // Send request
    ws.send(JSON.stringify({
        pkg_id: 1,
        req_id: crypto.randomUUID(),
        data: {}
    }));
};

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    console.log('Response:', response);
};
```

#### Python

```python
import asyncio
import json
import uuid
import websockets

async def test_websocket():
    token = "your-access-token"
    uri = f"ws://localhost:8000/web?Authorization=Bearer {token}"

    async with websockets.connect(uri) as websocket:
        # Send request
        request = {
            "pkg_id": 1,
            "req_id": str(uuid.uuid4()),
            "data": {}
        }
        await websocket.send(json.dumps(request))

        # Receive response
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(test_websocket())
```

---

## Development Workflow

### 1. Start Services

```bash
make start  # Start PostgreSQL, Redis, Keycloak
make serve  # Start FastAPI app
```

### 2. Get Token

```bash
python scripts/get_token.py acika 12345
```

### 3. Test Endpoints

**Option A: VS Code REST Client** (`api-testing/api.http`):
```http
### Get Authors
GET http://localhost:8000/authors
Authorization: Bearer YOUR_TOKEN_HERE
```

**Option B: curl**:
```bash
TOKEN="your-token"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/authors
```

**Option C: Python script**:
```python
# test_auth.py
import requests

token = "your-token"
response = requests.get(
    "http://localhost:8000/authors",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())
```

### 4. Automated Tests

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_auth_example.py::TestMockAuthentication::test_valid_user_has_permission
```

---

## Token Management

### Token Expiration

Tokens expire after a configured time (default: 300 seconds / 5 minutes).

**Handling Expiration**:
1. **HTTP**: Re-authenticate and get new token
2. **WebSocket**: Connection closes, client must reconnect with new token

**Check Token Validity**:
```python
import jwt
from datetime import datetime

token = "your-token"
decoded = jwt.decode(token, options={"verify_signature": False})
exp_timestamp = decoded["exp"]
exp_time = datetime.fromtimestamp(exp_timestamp)

print(f"Token expires at: {exp_time}")
print(f"Is expired: {datetime.now() > exp_time}")
```

### Refresh Tokens

```bash
# Get refresh token
python scripts/get_token.py USERNAME PASSWORD --refresh

# Use refresh token to get new access token
curl -X POST "http://localhost:8080/realms/YOUR_REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

---

## Roles and Permissions

### Understanding Roles

Roles determine what endpoints a user can access. Roles are:
1. Defined in Keycloak
2. Included in JWT token
3. Checked by RBAC on each request

### Current Roles

See `actions.json` for current role mappings:
- `get-authors` - View author list
- `create-author` - Create new authors
- `admin` - Administrative access

### Checking User Roles

Roles are in the JWT token:
```python
import jwt

token = "your-token"
decoded = jwt.decode(token, options={"verify_signature": False})

# Realm roles
realm_roles = decoded["realm_access"]["roles"]

# Client roles
client_roles = decoded["resource_access"]["your-client"]["roles"]
```

### Adding Roles in Keycloak

1. Go to Keycloak Admin Console
2. Select your realm
3. Go to "Roles" → "Add Role"
4. Create role (e.g., "get-authors")
5. Go to "Users" → Select user → "Role Mappings"
6. Assign role to user

---

## Troubleshooting

### "401 Unauthorized"

**Cause**: Missing or invalid token

**Solutions**:
1. Check token is included in request
2. Verify token hasn't expired
3. Get fresh token
4. Check Authorization header format: `Bearer YOUR_TOKEN`

### "403 Forbidden"

**Cause**: Valid token but insufficient permissions

**Solutions**:
1. Check user has required role in Keycloak
2. Verify role mapping in `actions.json`
3. Check RBAC logs: `logger.info("Permission denied...")`

### "Token Expired"

**Cause**: Token validity period elapsed

**Solutions**:
1. Get new token: `python scripts/get_token.py USERNAME PASSWORD`
2. Use refresh token to get new access token
3. For development, increase token lifetime in Keycloak

### WebSocket Connection Fails

**Cause**: Token in wrong format or expired

**Solutions**:
1. Ensure query param format: `?Authorization=Bearer TOKEN`
2. Verify token is valid (not expired)
3. Check server logs for authentication errors

### "Connection Closed"

**Cause**: Token expired during connection

**Solutions**:
1. WebSocket closes when token expires
2. Client must reconnect with fresh token
3. Implement automatic reconnection logic

### Keycloak Not Available

**Cause**: Keycloak service not running

**Solutions**:
```bash
# Check Keycloak status
docker ps | grep keycloak

# Start Keycloak
make start

# Check Keycloak logs
docker logs hw-keycloak
```

---

## Testing Authentication

### Unit Tests with Mocks

```python
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_keycloak_token():
    """Mock Keycloak token response."""
    return {
        "access_token": "mock-token-12345",
        "expires_in": 300,
        "refresh_token": "mock-refresh",
        "token_type": "Bearer"
    }

def test_endpoint_with_auth(client, mock_keycloak_token):
    """Test endpoint with mocked authentication."""
    with patch('app.auth.AuthBackend.authenticate'):
        response = client.get(
            "/authors",
            headers={"Authorization": f"Bearer {mock_keycloak_token['access_token']}"}
        )
        assert response.status_code == 200
```

### Integration Tests with Real Keycloak

```python
import pytest

@pytest.mark.integration
def test_real_authentication():
    """Test with real Keycloak instance."""
    from app.managers.keycloak_manager import KeycloakManager

    kc = KeycloakManager()
    token = kc.login("testuser", "testpass")

    # Use token in request
    response = requests.get(
        "http://localhost:8000/authors",
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert response.status_code == 200
```

See [Testing Guide](TESTING.md) for more details.

---

## Security Best Practices

### Production Checklist

- [ ] Use HTTPS for all connections
- [ ] Set short token expiration times
- [ ] Rotate client secrets regularly
- [ ] Use strong passwords in Keycloak
- [ ] Disable debug authentication bypass
- [ ] Configure proper CORS policies
- [ ] Enable Keycloak audit logging
- [ ] Use refresh tokens for long sessions
- [ ] Implement rate limiting
- [ ] Monitor for suspicious activity

### Token Storage

**Browser**:
- Store in memory (JavaScript variable)
- Or use httpOnly cookies
- Never localStorage (XSS risk)

**Mobile**:
- Use secure keychain/keystore
- Encrypt if in local storage

**Server-to-Server**:
- Environment variables
- Secret management system
- Never commit to git

---

## Related Documentation

- [Testing Guide](TESTING.md) - How to test with authentication
- [Quick Start](QUICKSTART_AUTH.md) - Quick authentication reference
- [Architecture Overview](../architecture/OVERVIEW.md) - System architecture
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines

---

## Additional Resources

### Keycloak Documentation
- [Getting Started](https://www.keycloak.org/getting-started)
- [Securing Applications](https://www.keycloak.org/docs/latest/securing_apps/)
- [Server Administration](https://www.keycloak.org/docs/latest/server_admin/)

### JWT Resources
- [JWT.io](https://jwt.io/) - Decode and verify tokens
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

### OAuth 2.0 / OpenID Connect
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Spec](https://openid.net/connect/)
