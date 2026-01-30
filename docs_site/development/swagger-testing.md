# Testing with Swagger UI (OpenAPI)

This guide explains how to test HTTP API endpoints using FastAPI's built-in Swagger UI.

## Quick Start

### 1. Start the Application

```bash
make serve
# Or: uvicorn app:application --reload
```

### 2. Get an Access Token

```bash
python scripts/get_token.py acika 12345
```

**Output:**
```
=== Access Token ===
eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJxxx...

=== Token Info ===
Expires in: 300 seconds
User: acika
Roles: ['admin', 'get-authors', 'create-author', ...]
```

Copy the access token (the long string starting with `eyJhbGc...`).

### 3. Open Swagger UI

Navigate to: **http://localhost:8000/docs**

### 4. Authorize in Swagger UI

1. Click the **"Authorize"** button (green lock icon in the top-right corner)
2. In the **"Available authorizations"** popup:
   - Find the **"HTTPBearer (http, Bearer)"** section
   - In the **"Value"** field, paste your token:
     ```
     Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJxxx...
     ```
     **Important:** Include the word `Bearer` followed by a space before the token.
3. Click **"Authorize"**
4. The popup will show "Authorized" with a checkmark
5. Click **"Close"**

### 5. Test Any Endpoint

Now all HTTP requests will include your access token automatically:

1. Find an endpoint (e.g., **GET /api/authors**)
2. Click to expand it
3. Click **"Try it out"**
4. Fill in any required parameters
5. Click **"Execute"**

You'll see:
- **Request URL** - The actual URL called
- **Request headers** - Including your `Authorization: Bearer ...` header
- **Response body** - The JSON response
- **Response code** - HTTP status code (200, 401, etc.)

## Token Expiration

Tokens expire after **5 minutes** (300 seconds).

When your token expires, you'll get **401 Unauthorized** errors:

```json
{
  "detail": "Could not validate credentials"
}
```

**Solution:**
1. Get a new token: `python scripts/get_token.py acika 12345`
2. Click **"Authorize"** again
3. Paste the new token
4. Continue testing

## Using Different Users

Test with different user accounts to verify RBAC (role-based access control):

```bash
# Admin user with all permissions
python scripts/get_token.py acika 12345

# Limited user (if you have one configured)
python scripts/get_token.py testuser password
```

Each user has different roles, so some endpoints may return **403 Forbidden** for users without proper permissions.

## Testing Protected Endpoints

### Example: Testing GET /api/authors

This endpoint requires the `get-authors` role.

1. **Get token** for user with `get-authors` role:
   ```bash
   python scripts/get_token.py acika 12345
   ```

2. **Authorize** in Swagger UI (paste `Bearer <token>`)

3. **Execute** the request:
   - Expand **GET /api/authors**
   - Click **"Try it out"**
   - Click **"Execute"**

4. **Expected response** (200 OK):
   ```json
   [
     {
       "id": 1,
       "name": "John Doe",
       "created_at": "2024-01-15T10:30:00"
     }
   ]
   ```

### Example: Testing POST /api/authors

This endpoint requires both `create-author` AND `admin` roles.

1. **Get token** for admin user:
   ```bash
   python scripts/get_token.py acika 12345
   ```

2. **Authorize** in Swagger UI

3. **Execute** the request:
   - Expand **POST /api/authors**
   - Click **"Try it out"**
   - Enter request body:
     ```json
     {
       "name": "Jane Smith"
     }
     ```
   - Click **"Execute"**

4. **Expected response** (201 Created):
   ```json
   {
     "id": 2,
     "name": "Jane Smith",
     "created_at": "2024-01-15T11:00:00"
   }
   ```

## Testing Error Cases

### 401 Unauthorized (No Token)

1. Click **"Authorize"** and then **"Logout"** to clear your token
2. Try to execute a protected endpoint
3. You'll get:
   ```json
   {
     "detail": "Not authenticated"
   }
   ```

### 401 Unauthorized (Expired Token)

1. Wait more than 5 minutes after getting a token
2. Try to execute an endpoint
3. You'll get:
   ```json
   {
     "detail": "Could not validate credentials"
   }
   ```

### 403 Forbidden (Missing Role)

1. Use a token from a user without required roles
2. Try to execute a protected endpoint
3. You'll get:
   ```json
   {
     "error": "permission_denied",
     "message": "User does not have required roles: ['admin', 'create-author']"
   }
   ```

## Tips and Tricks

### 1. Keep a Token Ready

Open a terminal and keep this command ready:

```bash
python scripts/get_token.py acika 12345
```

When your token expires (every 5 minutes), just run it again and copy the new token.

### 2. Use JSON Output for Scripting

Get just the token for easy copying:

```bash
python scripts/get_token.py acika 12345 --json | jq -r '.access_token'
```

Or get the full token with Bearer prefix:

```bash
TOKEN=$(python scripts/get_token.py acika 12345 --json | jq -r '.access_token')
echo "Bearer $TOKEN"
```

### 3. Check Token Roles

See what roles your user has:

```bash
python scripts/get_token.py acika 12345
```

Look at the **Roles** line in the output:
```
Roles: ['admin', 'get-authors', 'create-author', ...]
```

### 4. Test Multiple Users

Create multiple terminal tabs with tokens for different users:

**Tab 1 - Admin:**
```bash
python scripts/get_token.py acika 12345
```

**Tab 2 - Regular User:**
```bash
python scripts/get_token.py testuser password
```

Switch between tokens in Swagger UI to test different permission levels.

### 5. Copy Token Faster

Use your terminal's selection to copy:

```bash
python scripts/get_token.py acika 12345 | grep -A1 "Access Token" | tail -1
```

This outputs just the token (no "=== Access Token ===" header).

### 6. Monitor Token Expiry

Set a 4-minute timer after getting a token to remind you to refresh:

```bash
python scripts/get_token.py acika 12345 && sleep 240 && echo "⏰ Token expires in 1 minute!"
```

---

## Troubleshooting

### Problem: "Not authenticated" error

**Cause:** No token provided or token not in correct format.

**Solution:**
1. Check you clicked "Authorize" in Swagger UI
2. Ensure token starts with `Bearer ` (with space)
3. Check token was copied completely (very long string)

### Problem: "Could not validate credentials"

**Cause:** Token expired (older than 5 minutes).

**Solution:**
1. Get a new token: `python scripts/get_token.py acika 12345`
2. Click "Authorize" again
3. Paste new token

### Problem: "Permission denied" error

**Cause:** User doesn't have required roles for this endpoint.

**Solution:**
1. Check required roles in error message
2. Verify your user has these roles:
   ```bash
   python scripts/get_token.py acika 12345
   # Look at Roles: line
   ```
3. Use an admin user or add roles to your user in Keycloak

### Problem: Keycloak connection error

**Cause:** Keycloak is not running.

**Solution:**
```bash
# Start all services including Keycloak
make start

# Check Keycloak is running
docker ps | grep keycloak

# Access Keycloak admin console
open http://localhost:8080
# Login: admin/admin
```

### Problem: "Invalid credentials" when getting token

**Cause:** Wrong username or password for Keycloak user.

**Solution:**
1. Verify user exists in Keycloak admin console
2. Check username and password are correct
3. Create test user if needed (see Keycloak admin console)

## Alternative: ReDoc UI

FastAPI also provides ReDoc at **http://localhost:8000/redoc**.

ReDoc is read-only (no "Try it out" button) but provides:
- Better documentation layout
- Easier to browse API structure
- Printable API reference

Use Swagger UI for testing, ReDoc for documentation.

## Next Steps

- See [testing.md](testing.md) for automated testing with pytest
- See [websocket-testing.md](websocket-testing.md) for WebSocket testing with tokens
- See [../deployment/troubleshooting.md](../deployment/troubleshooting.md) for common issues
