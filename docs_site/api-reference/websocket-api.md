# WebSocket API Documentation

## Overview

This FastAPI application provides a WebSocket API for real-time bidirectional communication. The WebSocket endpoint uses a package-based routing system where requests are dispatched to handlers based on Package IDs (PkgID).

## Connection

### Endpoint

```
ws://localhost:8000/web
wss://localhost:8000/web (for production with TLS)
```

### Authentication

Authentication is required via Keycloak access token passed as a query parameter:

```
ws://localhost:8000/web?token=<your_access_token>
```

**Connection Limits:**
- Maximum concurrent connections per user: 5 (configurable via `WS_MAX_CONNECTIONS_PER_USER`)
- Exceeding this limit results in connection rejection with code `1008` (Policy Violation)

### Rate Limiting

**Message Rate Limits:**
- Default: 100 messages per minute per user (configurable via `WS_MESSAGE_RATE_LIMIT`)
- Exceeding rate limit returns error response with `RSPCode.ERROR`

## Message Format

### Request Message

All client requests must follow this JSON structure:

```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "",
  "data": {}
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pkg_id` | integer | Yes | Package identifier routing request to specific handler (see PkgID Reference) |
| `req_id` | string (UUID) | Yes | Unique request identifier for tracking responses |
| `method` | string | No | Optional method name (handler-specific, defaults to empty string) |
| `data` | object | No | Request payload containing handler-specific parameters (defaults to `{}`) |

### Response Message

All server responses follow this JSON structure:

```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 0,
  "meta": null,
  "data": []
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `pkg_id` | integer | Same as request pkg_id, identifies the handler that processed the request |
| `req_id` | string (UUID) | Same as request req_id, for request/response correlation |
| `status_code` | integer | Response code indicating operation result (see RSPCode Reference) |
| `meta` | object/null | Optional metadata (e.g., pagination info) |
| `data` | object/array/null | Response payload containing results or error details |

## Package ID Reference (PkgID)

| PkgID | Name | Description | Required Role |
|-------|------|-------------|---------------|
| 1 | `GET_AUTHORS` | Retrieve list of authors with optional filters | `user` |
| 2 | `GET_PAGINATED_AUTHORS` | Retrieve paginated list of authors | `user` |
| 3 | `THIRD` | Reserved for future use | TBD |

### Handler Details

#### 1. GET_AUTHORS (PkgID: 1)

Retrieves a list of authors with optional filtering.

**Request Data Schema:**

```json
{
  "filters": {
    "id": 123,        // optional: filter by author ID
    "name": "John"    // optional: filter by author name (case-insensitive, partial match)
  }
}
```

**Success Response:**

```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 0,
  "meta": null,
  "data": [
    {
      "id": 1,
      "name": "John Doe"
    },
    {
      "id": 2,
      "name": "Jane Smith"
    }
  ]
}
```

**Example Request:**

```javascript
const ws = new WebSocket('ws://localhost:8000/web?token=YOUR_TOKEN');

ws.onopen = () => {
  ws.send(JSON.stringify({
    pkg_id: 1,
    req_id: crypto.randomUUID(),
    method: "",
    data: {
      filters: {
        name: "John"
      }
    }
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('Authors:', response.data);
};
```

**Error Responses:**

| status_code | Reason | data.msg |
|-------------|--------|----------|
| 1 | Database error | "Database error occurred" |
| 2 | Invalid filter parameters | "Invalid filter parameters" |
| 3 | Permission denied | "Permission denied" |

---

#### 2. GET_PAGINATED_AUTHORS (PkgID: 2)

Retrieves a paginated list of authors with optional filtering.

**Request Data Schema:**

```json
{
  "page": 1,           // required: page number (>=1)
  "per_page": 20,      // required: items per page (>=1)
  "filters": {
    "id": 123,         // optional: filter by author ID
    "name": "John"     // optional: filter by author name
  }
}
```

**Success Response:**

```json
{
  "pkg_id": 2,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 0,
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 42,
    "pages": 3
  },
  "data": [
    {
      "id": 1,
      "name": "John Doe"
    },
    {
      "id": 2,
      "name": "Jane Smith"
    }
  ]
}
```

**Example Request:**

```javascript
ws.send(JSON.stringify({
  pkg_id: 2,
  req_id: crypto.randomUUID(),
  method: "",
  data: {
    page: 1,
    per_page: 20,
    filters: {
      name: "Smith"
    }
  }
}));
```

**Error Responses:**

| status_code | Reason | data.msg |
|-------------|--------|----------|
| 1 | Database error | "Database error occurred" |
| 2 | Invalid pagination parameters | "Invalid pagination parameters" |
| 3 | Permission denied | "Permission denied" |

## Response Code Reference (RSPCode)

| Code | Name | Description |
|------|------|-------------|
| 0 | `OK` | Operation completed successfully |
| 1 | `ERROR` | General error occurred |
| 2 | `INVALID_DATA` | Provided data is invalid or malformed |
| 3 | `PERMISSION_DENIED` | User lacks required permissions for the operation |

## Error Handling

### Client-Side Error Handling

```javascript
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);

  if (response.status_code !== 0) {
    // Handle error
    switch (response.status_code) {
      case 1:
        console.error('Server error:', response.data.msg);
        break;
      case 2:
        console.error('Invalid data:', response.data.msg);
        // Validate and retry with corrected data
        break;
      case 3:
        console.error('Permission denied:', response.data.msg);
        // User needs different role or authentication
        break;
      default:
        console.error('Unknown error:', response);
    }
    return;
  }

  // Success - process data
  console.log('Success:', response.data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  if (event.code === 1008) {
    console.error('Connection rejected: Maximum concurrent connections exceeded');
  } else if (event.code === 1003) {
    console.error('Connection closed: Invalid message format');
  } else {
    console.log('Connection closed:', event.code, event.reason);
  }
};
```

### Common Connection Close Codes

| Code | Reason | Description |
|------|--------|-------------|
| 1000 | Normal Closure | Connection closed normally |
| 1003 | Unsupported Data | Invalid message format |
| 1008 | Policy Violation | Connection limit exceeded or rate limit violation |
| 4001 | Unauthorized | Invalid or expired authentication token |

## Broadcast Messages

The server may send unsolicited broadcast messages to all connected clients:

```json
{
  "pkg_id": 1,
  "req_id": "00000000-0000-0000-0000-000000000000",
  "data": {
    "event": "update",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Identifying Broadcasts:**
- `req_id` will be `00000000-0000-0000-0000-000000000000` (UUID with int=0)
- Not correlated to any client request

## Authentication

### Obtaining Access Token

Use the HTTP `/login` endpoint or Keycloak direct grant flow:

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### Token Expiration

- Access tokens expire after 5 minutes (300 seconds) by default
- Client must handle reconnection with refreshed token
- Monitor `exp` claim in JWT payload

## CSRF Protection

WebSocket connections are protected against Cross-Site WebSocket Hijacking (CSWSH) attacks through Origin header validation.

### How It Works

Before accepting a WebSocket connection, the server validates the `Origin` header:

1. If `ALLOWED_WS_ORIGINS` contains `"*"` → all origins permitted (development only)
2. If no `Origin` header → same-origin request, allowed
3. If origin matches an entry in `ALLOWED_WS_ORIGINS` → permitted
4. Otherwise → connection rejected with code `1008` (Policy Violation)

### Configuration

Configure allowed origins in your environment:

```bash
# Development (.env.dev) - Allow all origins
ALLOWED_WS_ORIGINS=["*"]

# Production (.env.production) - Restrict to your domains
ALLOWED_WS_ORIGINS=["https://app.example.com", "https://admin.example.com"]
```

### Attack Scenario Prevented

```
1. Attacker hosts malicious site: evil.com
2. User visits evil.com while authenticated to your app
3. evil.com attempts WebSocket connection to your server
4. Server checks Origin header: "https://evil.com"
5. Origin not in allowed list → connection rejected with code 1008
```

### Client-Side Handling

Handle CSRF rejection in your WebSocket `onclose` handler:

```javascript
ws.onclose = (event) => {
  if (event.code === 1008) {
    console.error('Connection rejected: Origin not allowed (CSRF protection)');
    // This typically means you're connecting from an unauthorized domain
  }
};
```

### Security Recommendations

1. **Never use `["*"]` in production** - Always specify exact allowed origins
2. **Use HTTPS origins** - Match the protocol used by your frontend
3. **Include all frontend domains** - Add each domain that needs WebSocket access
4. **Update on domain changes** - Keep `ALLOWED_WS_ORIGINS` in sync with your deployments

## Role-Based Access Control (RBAC)

Each handler requires specific roles defined in its `@pkg_router.register()` decorator. Users must have the required role in their Keycloak token to access handlers.

**Implementation:**
```python
@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    roles=["get-authors"]  # Required roles
)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    ...
```

**Common Roles:**
- `get-authors`: View author list
- `create-author`: Create new authors
- `admin`: Administrative privileges

**Finding Role Requirements:**
Check the handler code in `app/api/ws/handlers/` to see which roles are required for each `PkgID`.

## Best Practices

### 1. Request ID Management

Always generate unique UUIDs for each request to correlate responses:

```javascript
function generateRequestId() {
  return crypto.randomUUID();
}

const requestMap = new Map();

function sendRequest(pkgId, data) {
  const reqId = generateRequestId();
  requestMap.set(reqId, { pkgId, timestamp: Date.now() });

  ws.send(JSON.stringify({
    pkg_id: pkgId,
    req_id: reqId,
    data: data
  }));

  return reqId;
}

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  const request = requestMap.get(response.req_id);

  if (request) {
    requestMap.delete(response.req_id);
    // Process response with context
  }
};
```

### 2. Connection Management

Implement reconnection logic with exponential backoff:

```javascript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connect() {
  const ws = new WebSocket(`ws://localhost:8000/web?token=${token}`);

  ws.onclose = (event) => {
    if (reconnectAttempts < maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
      setTimeout(() => {
        reconnectAttempts++;
        connect();
      }, delay);
    }
  };

  ws.onopen = () => {
    reconnectAttempts = 0;
  };
}
```

### 3. Token Refresh

Proactively refresh tokens before expiration:

```javascript
function scheduleTokenRefresh(expiresIn) {
  // Refresh 30 seconds before expiration
  const refreshDelay = (expiresIn - 30) * 1000;

  setTimeout(async () => {
    const newToken = await refreshAccessToken();
    // Reconnect with new token
    ws.close(1000, 'Token refresh');
    connect(newToken);
  }, refreshDelay);
}
```

### 4. Message Validation

Always validate responses before processing:

```javascript
function isValidResponse(response) {
  return (
    response &&
    typeof response.pkg_id === 'number' &&
    typeof response.req_id === 'string' &&
    typeof response.status_code === 'number'
  );
}

ws.onmessage = (event) => {
  try {
    const response = JSON.parse(event.data);
    if (!isValidResponse(response)) {
      console.error('Invalid response format:', response);
      return;
    }
    // Process valid response
  } catch (error) {
    console.error('Failed to parse response:', error);
  }
};
```

## Performance Considerations

### Rate Limiting

To avoid hitting rate limits:
- Batch requests when possible
- Implement client-side throttling
- Cache frequently requested data
- Use pagination for large datasets

### Connection Pooling

For multi-user applications:
- Reuse connections across requests
- Implement connection pooling
- Monitor connection count per user
- Close idle connections

### Pagination

For large result sets:
- Always use paginated endpoints (`GET_PAGINATED_AUTHORS`)
- Request reasonable page sizes (20-100 items)
- Implement infinite scroll or pagination UI
- Cache previous pages on client

## Troubleshooting

### Connection Refused

**Problem:** WebSocket connection fails with 403 Forbidden

**Solutions:**
- Verify token is valid and not expired
- Check token is passed in query parameter: `?token=...`
- Ensure user has required roles in Keycloak

### Rate Limit Exceeded

**Problem:** Receiving `RSPCode.ERROR` frequently

**Solutions:**
- Implement client-side rate limiting
- Reduce message frequency
- Check `WS_MESSAGE_RATE_LIMIT` server configuration

### Invalid Data Errors

**Problem:** Receiving `RSPCode.INVALID_DATA`

**Solutions:**
- Validate data schema before sending
- Check required fields are present
- Ensure data types match schema
- Review handler-specific documentation

### Connection Drops

**Problem:** WebSocket disconnects frequently

**Solutions:**
- Implement reconnection logic
- Check network stability
- Monitor server logs for errors
- Verify token hasn't expired

## Support

For issues or questions:
- Check application logs for detailed error messages
- Review Keycloak configuration for authentication issues
- Check handler decorator for RBAC requirements (e.g., `@pkg_router.register(roles=[...])`)
- Enable debug logging: Set `LOG_LEVEL=DEBUG` in environment
