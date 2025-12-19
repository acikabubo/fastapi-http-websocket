# Authentication Quick Start

Quick reference for working with authentication after debug bypass removal.

## 🚀 Quick Commands

```bash
# Get a token (copy the token from output)
python scripts/get_token.py acika 12345

# Use with cURL
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/authors

# Enable debug mode (local dev only)
export DEBUG_AUTH=true
make serve
```

## 📋 Three Ways to Test

### 1. Debug Mode (Quickest - Local Only)
```bash
export DEBUG_AUTH=true
make serve
# Now all requests work without real tokens
```

### 2. Get Real Token (Recommended)
```bash
# Get token
python scripts/get_token.py acika 12345

# Copy token and use in your HTTP client
# Authorization: Bearer <paste-token-here>
```

### 3. Mock in Tests (Unit Tests)
```python
def test_something(mock_keycloak_manager, mock_user):
    # Authentication is automatically mocked
    response = await my_handler(request)
```

## 🔑 Token Lifecycle

```
Get Token → Use for 5min → Token Expires → Get New Token
```

Tokens expire after 5 minutes. Just run `get_token.py` again.

## 🛠️ Integration with Tools

### VS Code REST Client
```http
# api-testing/api.http
GET http://localhost:8000/authors
Authorization: Bearer eyJhbGci...

# Get fresh token: python scripts/get_token.py acika 12345
```

### cURL
```bash
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/authors
```

### HTTPie
```bash
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)
http GET localhost:8000/authors "Authorization: Bearer $TOKEN"
```

### Postman
1. Run: `python scripts/get_token.py acika 12345`
2. Copy the access token
3. In Postman: Authorization → Bearer Token → Paste

### WebSocket (wscat)
```bash
TOKEN=$(python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1 | xargs)
wscat -c "ws://localhost:8000/web?Authorization=Bearer $TOKEN"
```

## ⚠️ Common Issues

**401 Unauthorized**
- Token expired (get new one)
- Token not in header
- Wrong format (should be: `Bearer <token>`)

**403 Forbidden**
- User lacks required role
- Check roles: `python scripts/get_token.py acika 12345`
- Check handler decorator for required roles (e.g., `@pkg_router.register(roles=["get-authors"])`)

**Connection Refused**
- Keycloak not running: `make start`
- Wrong URL: check `docker/.srv_env`

## 🧪 Testing

```bash
# Unit tests (with mocks - fast)
uv run pytest tests/

# Integration tests (with real Keycloak - slow)
uv run pytest tests/ -m integration

# Specific test
uv run pytest tests/test_auth_example.py::test_handler_with_mock_user
```

## 📚 Full Documentation

See [TESTING.md](TESTING.md) for complete documentation.

## 🔐 Security

- ✅ DEBUG_AUTH=false in production
- ✅ Never commit tokens to git
- ✅ Use environment variables for credentials
- ✅ Tokens expire after 5 minutes
- ❌ Never push DEBUG_AUTH=true to production
