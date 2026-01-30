# Security Best Practices

Comprehensive guide to security features, configuration, and deployment best practices for this FastAPI + WebSocket application.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication](#authentication)
3. [Authorization (RBAC)](#authorization-rbac)
4. [Security Headers](#security-headers)
5. [Input Validation](#input-validation)
6. [Rate Limiting](#rate-limiting)
7. [WebSocket Security](#websocket-security)
8. [Audit Logging](#audit-logging)
9. [IP Spoofing Protection](#ip-spoofing-protection)
10. [Circuit Breakers](#circuit-breakers)
11. [Security Deployment Checklist](#security-deployment-checklist)
12. [Common Security Pitfalls](#common-security-pitfalls)
13. [Security Testing](#security-testing)
14. [Troubleshooting](#troubleshooting)

---

## Security Overview

This application implements **defense-in-depth** security with multiple layers:

```mermaid
graph TD
    A[Client Request] --> B[TLS/HTTPS]
    B --> C[Security Headers]
    C --> D[Request Size Limit]
    D --> E[Rate Limiting]
    E --> F[Authentication]
    F --> G[Authorization RBAC]
    G --> H[Input Validation]
    H --> I[Handler Logic]
    I --> J[Audit Logging]
    J --> K[Response]
```

**All security features are already implemented** - this guide explains how to configure and use them properly.

### Security Features Matrix

| Feature | HTTP | WebSocket | Configuration | Status |
|---------|------|-----------|---------------|--------|
| Authentication (JWT) | ✅ | ✅ | Keycloak | Implemented |
| Authorization (RBAC) | ✅ | ✅ | Code-based | Implemented |
| Rate Limiting | ✅ | ✅ | Settings | Implemented |
| CSRF Protection | ✅ (Framework) | ✅ (Origin) | Settings | Implemented |
| Input Validation | ✅ | ✅ | Pydantic/Schema | Implemented |
| Security Headers | ✅ | N/A | Middleware | Implemented |
| Audit Logging | ✅ | ✅ | Settings | Implemented |
| Request Size Limit | ✅ | N/A | Settings | Implemented |
| IP Spoofing Protection | ✅ | ✅ | Settings | Implemented |
| Circuit Breakers | ✅ | ✅ | Settings | Implemented |

---

## Authentication

### Overview

Authentication uses **Keycloak with JWT tokens**:
- HTTP requests: Token in `Authorization` header
- WebSocket connections: Token in query parameter (browser limitation)
- Token validation with Redis caching (85-95% cache hit rate)
- Circuit breaker protection for Keycloak outages

### Token Flow Diagram

```mermaid
sequenceDiagram
    participant Client
    participant App
    participant Redis
    participant Keycloak

    Client->>App: Request with JWT token
    App->>Redis: Check token cache
    alt Cache Hit (85-95%)
        Redis-->>App: Cached user claims
        App->>App: Create UserModel
    else Cache Miss
        App->>Keycloak: Validate token
        Keycloak-->>App: Token claims
        App->>Redis: Cache claims (TTL = token exp - 30s)
        App->>App: Create UserModel
    end
    App->>Client: Authenticated response
```

### HTTP Authentication

HTTP authentication is **automatic** via middleware:

```python
from fastapi import APIRouter, Depends
from app.schemas.user import UserModel
from app.dependencies import get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(user: UserModel = Depends(get_current_user)):
    """
    Protected endpoint - requires valid JWT token.

    User is automatically extracted from Authorization header.
    """
    return {
        "user_id": user.user_id,
        "username": user.username,
        "roles": user.roles
    }

# Client request example:
# GET /profile
# Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...
```

### WebSocket Authentication

WebSocket connections authenticate via query parameter (browser WebSocket API limitation):

```python
# Client-side JavaScript
const token = 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6...';
const wsUrl = `wss://api.example.com/web?Authorization=${encodeURIComponent(token)}`;
const ws = new WebSocket(wsUrl);
```

**Security Considerations:**

⚠️ **Query parameters have security implications:**
- Tokens appear in server access logs
- Tokens stored in browser history
- Risk of accidental token sharing via URLs

✅ **Required mitigations (already implemented):**
- Always use WSS (WebSocket over TLS) in production
- Short-lived tokens (Keycloak default: 5 minutes)
- Referrer-Policy header prevents token leakage
- Origin validation for CSRF protection

**Client Best Practices:**

```javascript
// ✅ GOOD - Get fresh token before connecting
const token = await getAccessToken();
const ws = new WebSocket(`wss://api.example.com/web?Authorization=${encodeURIComponent(token)}`);
token = null;  // Clear from memory

// ✅ GOOD - Reconnect with new token before expiration
setInterval(async () => {
    ws.close();
    const newToken = await refreshAccessToken();
    ws = new WebSocket(`wss://api.example.com/web?Authorization=${encodeURIComponent(newToken)}`);
}, 4 * 60 * 1000);  // Every 4 minutes (before 5-minute expiry)

// ❌ BAD - Log token in URL
console.log('Connecting to:', wsUrl);  // Exposes token!

// ❌ BAD - Reuse same token for hours
const ws = new WebSocket(wsUrl);  // Token will expire!
```

### Token Caching

Token validation is cached in Redis for performance:

**How It Works:**
1. SHA-256 hash of token used as cache key (full token never stored)
2. Cache stores decoded claims with TTL = token expiration - 30 seconds
3. 85-95% cache hit rate reduces Keycloak load by 85-95%
4. Fail-open behavior (falls back to token decode if Redis unavailable)

**Metrics:**
```promql
# Cache hit rate
rate(token_cache_hits_total[5m]) /
(rate(token_cache_hits_total[5m]) + rate(token_cache_misses_total[5m]))

# Should be 85-95% for typical workloads
```

**Configuration:**

```python
# app/utils/token_cache.py
TOKEN_CACHE_BUFFER_SECONDS = 30  # Cache expires 30s before token expiration
```

### Excluded Paths

Public endpoints (no authentication required):

```python
# app/settings.py
EXCLUDED_PATHS = re.compile(
    r"^/(health|metrics|docs|openapi\.json|redoc)"
)

# Example: Add custom public endpoint
EXCLUDED_PATHS = re.compile(
    r"^/(health|metrics|docs|openapi\.json|redoc|public-api)"
)
```

### Circuit Breaker Protection

Keycloak operations are protected by circuit breaker to prevent cascading failures:

**Configuration:**

```python
# app/settings.py
CIRCUIT_BREAKER_ENABLED = True
KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX = 5  # Open after 5 failures
KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT = 60  # Keep open for 60 seconds
```

**States:**
- **Closed** (normal): All requests pass through
- **Open** (failing): Requests fail immediately with `CircuitBreakerError`
- **Half-Open** (testing): One request allowed to test recovery

**Prometheus Metrics:**

```promql
# Circuit breaker state (0=closed, 1=open, 2=half_open)
circuit_breaker_state{service="keycloak"}

# State transitions
circuit_breaker_state_changes_total{service="keycloak", from_state="closed", to_state="open"}
```

### Token Expiration Handling

**Client-Side:**

```python
# Python client example
import requests
from datetime import datetime, timedelta

class APIClient:
    def __init__(self, keycloak_url, client_id, username, password):
        self.keycloak_url = keycloak_url
        self.client_id = client_id
        self.username = username
        self.password = password
        self.token = None
        self.token_expires_at = None

    def _refresh_token_if_needed(self):
        if not self.token or datetime.now() >= self.token_expires_at:
            # Get new token from Keycloak
            response = requests.post(
                f"{self.keycloak_url}/realms/your-realm/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "username": self.username,
                    "password": self.password
                }
            )
            data = response.json()
            self.token = data["access_token"]
            # Refresh 1 minute before expiration
            self.token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 60)

    def make_request(self, endpoint):
        self._refresh_token_if_needed()
        headers = {"Authorization": f"Bearer {self.token}"}
        return requests.get(f"https://api.example.com{endpoint}", headers=headers)
```

**Server-Side:**

The server automatically handles expired tokens:

```python
# app/auth.py (AuthBackend.authenticate)
try:
    user_data = keycloak_manager.openid.a_decode_token(access_token)
except JWTExpired:
    raise AuthenticationError("token_expired: Token has expired")
    # Client receives HTTP 401 or WebSocket close with PERMISSION_DENIED
```

---

## Authorization (RBAC)

### Overview

Role-Based Access Control (RBAC) uses **Keycloak roles** with decorator-based configuration:
- Roles defined in Keycloak (not in code)
- HTTP: `require_roles()` dependency
- WebSocket: `roles` parameter in `@pkg_router.register()`
- AND logic: User must have **ALL** required roles

### Keycloak Role Setup

**1. Create Realm Roles in Keycloak:**

Navigate to: Keycloak Admin Console → Your Realm → Roles → Create Role

```
Role Name: create-author
Description: Permission to create new authors
```

**2. Assign Roles to Users:**

Navigate to: Users → Select User → Role Mappings → Assign Role

**3. Include Roles in Token:**

Keycloak automatically includes realm roles in JWT `realm_access.roles` claim.

### HTTP Endpoint Protection

Use `require_roles()` dependency for HTTP endpoints:

```python
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_roles
from app.schemas.author import Author

router = APIRouter(prefix="/api", tags=["authors"])

# Single role required
@router.post(
    "/authors",
    dependencies=[Depends(require_roles("create-author"))]
)
async def create_author(author: Author) -> Author:
    """Create author - requires 'create-author' role."""
    # Implementation
    pass

# Multiple roles required (AND logic - user must have ALL)
@router.delete(
    "/authors/{author_id}",
    dependencies=[Depends(require_roles("delete-author", "admin"))]
)
async def delete_author(author_id: int) -> None:
    """Delete author - requires BOTH 'delete-author' AND 'admin' roles."""
    # Implementation
    pass

# Public endpoint - no authentication required
@router.get("/public-stats")
async def get_public_stats():
    """Public endpoint - no require_roles() = no authentication."""
    return {"total_authors": 1234}
```

**Response Codes:**
- `401 Unauthorized`: No token or invalid token
- `403 Forbidden`: Valid token but insufficient roles

### WebSocket Handler Protection

Use `roles` parameter in `@pkg_router.register()`:

```python
from app.routing import pkg_router
from app.api.ws.constants import PkgID
from app.schemas.ws import RequestModel, ResponseModel

# Single role required
@pkg_router.register(
    PkgID.CREATE_AUTHOR,
    json_schema=CreateAuthorSchema,
    roles=["create-author"]
)
async def create_author_handler(request: RequestModel) -> ResponseModel:
    """Create author - requires 'create-author' role."""
    # Implementation
    return ResponseModel.success(request.pkg_id, request.req_id, data={...})

# Multiple roles required (AND logic)
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]
)
async def delete_author_handler(request: RequestModel) -> ResponseModel:
    """Delete author - requires BOTH 'delete-author' AND 'admin' roles."""
    # Implementation
    return ResponseModel.success(...)

# Public handler - no authentication required
@pkg_router.register(PkgID.PUBLIC_DATA)
async def public_handler(request: RequestModel) -> ResponseModel:
    """Public handler - no roles = no authentication."""
    return ResponseModel.success(...)
```

**Response:**
```json
{
    "pkg_id": 101,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_code": 403,  // RSPCode.PERMISSION_DENIED
    "data": null,
    "meta": null
}
```

### Custom Permission Checking

For complex permission logic:

```python
from app.managers.rbac_manager import rbac_manager
from app.dependencies import get_current_user

@router.get("/sensitive-data")
async def get_sensitive_data(user: UserModel = Depends(get_current_user)):
    """Custom permission logic."""
    # Check if user has required role
    has_permission, missing_roles = rbac_manager.check_user_has_roles(
        user,
        ["view-sensitive-data"]
    )

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Missing roles: {', '.join(missing_roles)}"
        )

    # Additional business logic checks
    if user.user_id not in allowed_users:
        raise HTTPException(status_code=403, detail="Access denied")

    return {"sensitive": "data"}
```

### Role Composition Patterns

**AND Logic (all roles required):**

```python
# User must have BOTH roles
@router.delete("/critical", dependencies=[Depends(require_roles("delete", "admin"))])
```

**OR Logic (any role sufficient):**

```python
# User needs either role (implement custom dependency)
from app.dependencies import require_any_role

@router.get("/stats", dependencies=[Depends(require_any_role("viewer", "admin"))])
```

**Hierarchical Roles:**

Use Keycloak's composite roles feature:
1. Create composite role: `admin`
2. Add child roles: `create-author`, `delete-author`, `view-stats`
3. Users with `admin` role automatically get all child roles

---

## Security Headers

### Overview

Security headers protect against common web vulnerabilities and are added automatically to all HTTP responses.

**Implementation:** [`app/middlewares/security_headers.py`](../../app/middlewares/security_headers.py)

### Headers Explained

#### 1. X-Frame-Options: DENY

**Protects Against:** Clickjacking attacks

```http
X-Frame-Options: DENY
```

**What It Does:**
- Prevents your site from being embedded in `<iframe>`, `<frame>`, or `<object>` tags
- Stops attackers from overlaying transparent iframes to trick users into clicking malicious content

**When to Customize:**
```python
# If you need to allow framing (not recommended):
response.headers["X-Frame-Options"] = "SAMEORIGIN"  # Same domain only
# Or
response.headers["X-Frame-Options"] = "ALLOW-FROM https://trusted-site.com"
```

#### 2. X-Content-Type-Options: nosniff

**Protects Against:** MIME type sniffing attacks

```http
X-Content-Type-Options: nosniff
```

**What It Does:**
- Forces browsers to respect declared `Content-Type`
- Prevents browser from interpreting files as different type (e.g., image as script)
- Blocks execution of incorrectly labeled content

#### 3. X-XSS-Protection: 1; mode=block

**Protects Against:** Cross-Site Scripting (XSS) in legacy browsers

```http
X-XSS-Protection: 1; mode=block
```

**What It Does:**
- Enables XSS filter in older browsers (IE, Chrome <79)
- Modern browsers rely on CSP instead
- `mode=block` stops rendering page if XSS detected

#### 4. Strict-Transport-Security (HSTS)

**Protects Against:** Man-in-the-middle attacks, SSL stripping

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**What It Does:**
- Forces HTTPS for 1 year (31536000 seconds)
- Applies to all subdomains
- Prevents downgrade attacks to HTTP

**⚠️ Important:** Only enable HSTS after confirming HTTPS works everywhere!

```python
# For development (HTTP), comment out HSTS:
# response.headers["Strict-Transport-Security"] = ...

# For production with HTTPS:
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
```

#### 5. Referrer-Policy: strict-origin-when-cross-origin

**Protects Against:** Referrer leakage

```http
Referrer-Policy: strict-origin-when-cross-origin
```

**What It Does:**
- Same-origin requests: Full URL in Referer header
- Cross-origin HTTPS→HTTPS: Origin only (no path)
- HTTPS→HTTP: No referrer sent (prevents token leakage!)

**Critical for WebSocket security:** Prevents token in query parameter from leaking via Referer.

#### 6. Permissions-Policy

**Protects Against:** Unauthorized use of browser features

```http
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

**What It Does:**
- Disables geolocation, microphone, camera access
- Prevents malicious code from accessing sensitive hardware

**Customize for your needs:**
```python
# Allow geolocation from same origin:
response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
```

#### 7. Content-Security-Policy (CSP)

**Protects Against:** XSS, injection attacks, data exfiltration

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ws: wss:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests
```

**Directives Explained:**

| Directive | Value | Purpose |
|-----------|-------|---------|
| `default-src` | `'self'` | Default policy: only same-origin resources |
| `script-src` | `'self'` | Block inline scripts and eval() |
| `style-src` | `'self' 'unsafe-inline'` | Allow inline styles (needed for API docs) |
| `img-src` | `'self' data:` | Same-origin images + data URIs |
| `font-src` | `'self'` | Same-origin fonts only |
| `connect-src` | `'self' ws: wss:` | **Critical:** Allow WebSocket connections |
| `frame-ancestors` | `'none'` | Prevent clickjacking (reinforces X-Frame-Options) |
| `base-uri` | `'self'` | Restrict `<base>` tag to same origin |
| `form-action` | `'self'` | Only submit forms to same origin |
| `upgrade-insecure-requests` | - | Auto-upgrade HTTP to HTTPS |

**⚠️ Critical for WebSocket:** `connect-src 'self' ws: wss:'` is **required** for WebSocket connections!

**Testing CSP:**

```bash
# Check CSP header
curl -I https://your-api.com | grep -i content-security

# Test CSP violations (browser console)
# Attempt to load external script - should be blocked by CSP
```

**Reporting CSP Violations:**

```python
# Add report-uri directive to log violations:
csp_directives.append("report-uri /csp-report")

# Create endpoint to receive reports:
@router.post("/csp-report")
async def csp_report(request: Request):
    report = await request.json()
    logger.warning(f"CSP violation: {report}")
    return {}
```

### Testing Security Headers

**1. Manual Testing:**

```bash
curl -I https://your-api.com
```

**2. Security Header Scanners:**

- [https://securityheaders.com/](https://securityheaders.com/)
- [https://observatory.mozilla.org/](https://observatory.mozilla.org/)

**3. Expected Output:**

```
HTTP/2 200
x-frame-options: DENY
x-content-type-options: nosniff
x-xss-protection: 1; mode=block
strict-transport-security: max-age=31536000; includeSubDomains
referrer-policy: strict-origin-when-cross-origin
permissions-policy: geolocation=(), microphone=(), camera=()
content-security-policy: default-src 'self'; script-src 'self'; ...
```

### Common Issues

**Problem:** API requests failing with CSP errors

**Solution:** Check `connect-src` directive includes your API domain:

```python
# If API is on different subdomain:
"connect-src 'self' api.example.com ws: wss:"
```

**Problem:** WebSocket connections blocked by CSP

**Solution:** Ensure `connect-src` includes `ws:` and `wss:`:

```python
"connect-src 'self' ws: wss:"  # Required for WebSocket
```

**Problem:** Third-party fonts/CDN resources blocked

**Solution:** Add specific domains to CSP:

```python
"font-src 'self' fonts.gstatic.com",
"style-src 'self' 'unsafe-inline' fonts.googleapis.com"
```

---

## Input Validation

### Overview

All input is validated before processing:
- **HTTP**: Pydantic models (automatic FastAPI validation)
- **WebSocket**: Pydantic + optional JSON Schema + Protobuf
- **Database**: SQLModel field constraints
- **Automatic sanitization** of sensitive fields in audit logs

### Pydantic Validation Patterns

#### Basic Field Validation

```python
from pydantic import BaseModel, Field, EmailStr, field_validator

class CreateUserInput(BaseModel):
    """Input validation for user creation."""

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_]+$',  # Alphanumeric + underscore only
        description="Unique username"
    )

    email: EmailStr  # Built-in email validation

    age: int = Field(ge=13, le=120)  # Greater than or equal, less than or equal

    bio: str | None = Field(None, max_length=500)

    website: str | None = Field(None, pattern=r'^https?://')  # HTTP(S) URLs only

# FastAPI automatically validates and returns 422 Unprocessable Entity for invalid data
```

#### Custom Validators

```python
class CreateAuthorInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    country_code: str = Field(pattern=r'^[A-Z]{2}$')  # ISO 3166-1 alpha-2

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name doesn't contain reserved words."""
        reserved = ['admin', 'root', 'system', 'anonymous']
        if v.lower() in reserved:
            raise ValueError(f'Reserved name: {v}')
        return v.strip()  # Remove leading/trailing whitespace

    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Block disposable email domains."""
        disposable_domains = ['tempmail.com', '10minutemail.com']
        domain = v.split('@')[1]
        if domain in disposable_domains:
            raise ValueError(f'Disposable email addresses not allowed')
        return v.lower()  # Normalize to lowercase
```

#### Model Validators (Multiple Fields)

```python
from pydantic import model_validator

class CreateBookInput(BaseModel):
    title: str
    author_id: int
    isbn: str | None = None
    asin: str | None = None

    @model_validator(mode='after')
    def validate_identifiers(self) -> 'CreateBookInput':
        """At least one identifier (ISBN or ASIN) required."""
        if not self.isbn and not self.asin:
            raise ValueError('Either ISBN or ASIN must be provided')
        return self
```

#### Validation Error Handling

```python
from fastapi import HTTPException
from pydantic import ValidationError

@router.post("/authors")
async def create_author(data: CreateAuthorInput):
    try:
        # Validation happens automatically
        # If we get here, data is valid
        author = await create_author_logic(data)
        return author
    except ValidationError as e:
        # FastAPI handles this automatically, but you can customize:
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )
```

### WebSocket JSON Schema Validation

For WebSocket handlers, add JSON Schema validation:

```python
# Define schema (schemas/create_author.json)
{
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "email"],
    "additionalProperties": false
}

# Register handler with schema
from app.utils.file_io import load_json_schema

create_author_schema = load_json_schema("schemas/create_author.json")

@pkg_router.register(
    PkgID.CREATE_AUTHOR,
    json_schema=create_author_schema,
    roles=["create-author"]
)
async def create_author_handler(request: RequestModel) -> ResponseModel:
    # request.data is already validated against JSON schema
    author = Author(**request.data)
    # ...
```

### Protobuf Validation

For binary message validation:

```protobuf
// proto/websocket.proto
message CreateAuthorRequest {
    string name = 1;
    string email = 2;
    optional string bio = 3;
}
```

```python
# Client sends binary message
from app.schemas.proto import CreateAuthorRequest

request = CreateAuthorRequest()
request.name = "John Doe"
request.email = "john@example.com"
binary_data = request.SerializeToString()

await websocket.send(binary_data)
```

### String Length Limits

**Always set maximum lengths** to prevent DoS attacks:

```python
# ❌ BAD - No length limit (DoS vulnerability)
class UserInput(BaseModel):
    bio: str

# ✅ GOOD - Reasonable length limit
class UserInput(BaseModel):
    bio: str = Field(max_length=500)
```

### SQL Injection Prevention

**SQLModel/SQLAlchemy uses parameterized queries automatically:**

```python
# ✅ SAFE - Parameterized query
stmt = select(Author).where(Author.name == user_input)
result = await session.execute(stmt)

# ❌ DANGEROUS - Never use string formatting!
# stmt = text(f"SELECT * FROM authors WHERE name = '{user_input}'")
```

### Path Traversal Prevention

```python
from pathlib import Path

@router.get("/files/{filename}")
async def get_file(filename: str):
    # ❌ VULNERABLE to path traversal
    # file_path = f"/files/{filename}"  # filename could be "../../../etc/passwd"

    # ✅ SAFE - Validate filename
    safe_filename = Path(filename).name  # Removes directory components
    if not safe_filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")

    file_path = Path("/files") / safe_filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path)
```

### Sensitive Data Sanitization

Audit logs automatically sanitize sensitive fields:

```python
# app/utils/audit_logger.py
SENSITIVE_FIELDS = [
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token",
    "secret", "api_key", "private_key",
    "ssn", "social_security_number",
    "credit_card", "card_number", "cvv",
    "authorization"
]

# Before logging:
request_data = {
    "username": "john",
    "password": "secret123",
    "email": "john@example.com"
}

# After sanitization:
sanitized_data = {
    "username": "john",
    "password": "[REDACTED]",
    "email": "john@example.com"
}
```

---

## Rate Limiting

### Overview

Rate limiting prevents abuse and ensures fair resource usage:
- **HTTP**: Per-user or IP-based, sliding window algorithm
- **WebSocket**: Connection limits + message rate limits
- **Redis-based**: Distributed rate limiting across instances
- **Fail modes**: Configurable fail-open (allow) or fail-closed (deny)

### HTTP Rate Limiting

**Configuration:**

```python
# app/settings.py
RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_MINUTE = 60  # Requests per minute
RATE_LIMIT_BURST = 10  # Additional burst allowance
RATE_LIMIT_FAIL_MODE = "open"  # or "closed"
```

**How It Works:**

```python
# Middleware: app/middlewares/rate_limit.py
# Automatically applied to all HTTP endpoints

# Rate limit key:
# - Authenticated: "rate_limit:user:{username}"
# - Unauthenticated: "rate_limit:ip:{ip_address}"

# Response headers:
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200

# When limit exceeded:
HTTP/1.1 429 Too Many Requests
Retry-After: 60
{
    "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

**Excluded Paths:**

```python
# Excluded from rate limiting (health checks, metrics)
EXCLUDED_PATHS = re.compile(r"^/(health|metrics|docs|openapi\.json)")
```

**Burst Allowance:**

Burst allows temporary traffic spikes:

```python
RATE_LIMIT_PER_MINUTE = 60  # Base limit
RATE_LIMIT_BURST = 20  # Burst allowance

# Total allowed: 80 requests per minute (60 + 20)
# After burst consumed, limited to 60/minute
```

**Sliding Window Algorithm:**

```python
# Redis sorted set implementation
# Key: rate_limit:user:john
# Score: timestamp
# Member: request_id

# Check rate limit:
1. Remove expired entries (outside window)
2. Count requests in current window
3. If count < limit: Allow
4. If count >= limit: Deny with 429
```

**Fail Modes:**

```python
# Fail-open (default): Allow requests if Redis unavailable
RATE_LIMIT_FAIL_MODE = "open"
# Use for: High availability over strict rate limiting

# Fail-closed: Deny requests if Redis unavailable
RATE_LIMIT_FAIL_MODE = "closed"
# Use for: Strict rate limiting over availability (production)
```

### WebSocket Rate Limiting

**Two-Level Protection:**

#### 1. Connection Limit

Prevents users from opening excessive connections:

```python
# app/settings.py
WS_MAX_CONNECTIONS_PER_USER = 5  # Max concurrent connections per user
```

**Enforcement:**

```python
# In PackageAuthWebSocketEndpoint.on_connect()
connection_limiter = ConnectionLimiter()
success = await connection_limiter.add_connection(user.user_id, connection_id)

if not success:
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION,
        reason=f"Connection limit exceeded: {WS_MAX_CONNECTIONS_PER_USER}"
    )
```

**Redis Storage:**

```
Redis Key: ws_connections:{user_id}
Type: SET
Members: [connection_id1, connection_id2, ...]
TTL: Auto-cleanup on disconnect
```

#### 2. Message Rate Limit

Prevents message flooding:

```python
# app/settings.py
WS_MESSAGE_RATE_LIMIT = 100  # Messages per minute
```

**Enforcement:**

```python
# In Web.on_receive()
rate_limiter = RateLimiter()
is_allowed, remaining = await rate_limiter.check_rate_limit(
    key=f"ws_msg:{user.user_id}",
    limit=WS_MESSAGE_RATE_LIMIT,
    window_seconds=60
)

if not is_allowed:
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION,
        reason="Message rate limit exceeded"
    )
```

### Custom Rate Limits

For specific endpoints:

```python
from app.utils.rate_limiter import RateLimiter

@router.post("/expensive-operation")
async def expensive_operation(user: UserModel = Depends(get_current_user)):
    """Custom rate limit for expensive operation."""
    rate_limiter = RateLimiter()

    # 10 requests per hour
    is_allowed, remaining = await rate_limiter.check_rate_limit(
        key=f"expensive_op:{user.user_id}",
        limit=10,
        window_seconds=3600
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Remaining: {remaining}"
        )

    # Expensive operation
    result = await perform_expensive_operation()
    return result
```

### Rate Limit Monitoring

**Prometheus Metrics:**

```promql
# Rate limit hits (429 responses)
rate(rate_limit_hits_total{limit_type="http"}[5m])

# WebSocket connection rejections
rate(ws_connections_total{status="rejected_limit"}[5m])

# WebSocket message rate limit violations
rate(ws_messages_rejected_total{reason="rate_limit"}[5m])
```

**Grafana Alerts:**

```yaml
# docker/prometheus/alerts.yml
- alert: HighRateLimitHits
  expr: rate(rate_limit_hits_total[5m]) > 10
  for: 5m
  labels:
    severity: info
  annotations:
    summary: "High rate limit hit rate"
    description: "Rate limit being hit frequently ({{ $value }}/s)"
```

### Rate Limit Best Practices

**1. Choose appropriate limits:**

```python
# Public API: Strict limits
RATE_LIMIT_PER_MINUTE = 10

# Authenticated users: Generous limits
RATE_LIMIT_PER_MINUTE = 100

# Internal services: Very high limits or disabled
RATE_LIMIT_PER_MINUTE = 1000
```

**2. Different limits for different endpoints:**

```python
# General endpoints: 100/minute
# Auth endpoints: 10/minute (prevent brute force)
# File uploads: 5/hour
```

**3. Communicate limits to clients:**

```python
# Document in API docs
# Include X-RateLimit-* headers in responses
# Return clear error messages with Retry-After header
```

**4. Monitor and adjust:**

```python
# Track rate limit hits
# Adjust based on legitimate vs abusive traffic
# Whitelist trusted IPs if needed
```

---

## WebSocket Security

### Overview

WebSocket connections have unique security considerations:
- CSRF protection via Origin header validation
- Per-user connection limits
- Message rate limiting
- Token refresh strategies for long-lived connections

### CSRF Protection

**Attack Scenario:**

```html
<!-- Malicious site: evil.com -->
<script>
// Attempt WebSocket connection to your API
const ws = new WebSocket('wss://your-api.com/web?token=stolen_token');
// Origin header: https://evil.com
</script>
```

**Protection:**

```python
# app/api/ws/websocket.py (PackageAuthWebSocketEndpoint._is_origin_allowed)

# Configuration
ALLOWED_WS_ORIGINS = [
    "https://app.example.com",
    "https://admin.example.com"
]

# Validation Flow:
1. Extract Origin header from WebSocket request
2. If wildcard "*" in ALLOWED_WS_ORIGINS → Allow all (dev only!)
3. If no Origin header → Same-origin request, allow
4. If Origin in ALLOWED_WS_ORIGINS → Allow
5. Otherwise → Reject with WS_1008_POLICY_VIOLATION
```

**Configuration:**

```python
# Development - allow all origins
ALLOWED_WS_ORIGINS = ["*"]

# Production - restrict to specific origins
ALLOWED_WS_ORIGINS = [
    "https://app.example.com",
    "https://admin.example.com",
    "https://*.example.com"  # Wildcard subdomain (if supported)
]
```

**How It Works:**

```python
# Browser automatically sends Origin header
Origin: https://app.example.com

# Server validates:
if origin not in ALLOWED_WS_ORIGINS:
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION,
        reason="Origin not allowed"
    )
```

### Connection Lifecycle Security

**1. Connection Establishment:**

```python
async def on_connect(websocket: WebSocket):
    # Step 1: Origin validation (CSRF protection)
    if not _is_origin_allowed(websocket):
        await websocket.close(WS_1008_POLICY_VIOLATION, "Origin not allowed")
        return

    # Step 2: Authentication (JWT token from query param)
    user = websocket.scope["user"]
    if not user or not user.is_authenticated:
        await websocket.close(WS_1008_POLICY_VIOLATION, "Authentication required")
        return

    # Step 3: Connection limit enforcement
    if await connection_limiter.is_limit_exceeded(user.user_id):
        await websocket.close(WS_1008_POLICY_VIOLATION, "Connection limit exceeded")
        return

    # Step 4: Accept connection
    await websocket.accept()

    # Step 5: Register in connection manager
    await connection_manager.connect(websocket, user)
```

**2. Message Handling:**

```python
async def on_receive(websocket: WebSocket, data):
    # Step 1: Rate limit check
    if not await check_message_rate_limit(user):
        await websocket.close(WS_1008_POLICY_VIOLATION, "Rate limit exceeded")
        return

    # Step 2: Input validation (Pydantic/JSON Schema/Protobuf)
    try:
        request = RequestModel(**data)
    except ValidationError:
        await websocket.close(WS_1003_UNSUPPORTED_DATA, "Invalid data")
        return

    # Step 3: Permission check
    if not rbac_manager.check_ws_permission(request.pkg_id, user):
        response = ResponseModel.error(request.pkg_id, request.req_id, "Permission denied")
        await websocket.send_response(response)
        return

    # Step 4: Handler dispatch
    response = await pkg_router.handle_request(user, request)
    await websocket.send_response(response)
```

**3. Disconnection:**

```python
async def on_disconnect(websocket: WebSocket, close_code: int):
    # Step 1: Remove from connection manager
    await connection_manager.disconnect(websocket)

    # Step 2: Remove from connection limiter
    await connection_limiter.remove_connection(user.user_id, connection_id)

    # Step 3: Clean up user session in Redis
    await redis.delete(f"ws_session:{connection_id}")

    # Step 4: Log disconnect
    logger.info(f"WebSocket disconnected: {user.user_id}, code={close_code}")
```

### Token Refresh Strategies

WebSocket connections can last hours - tokens expire in minutes.

**Strategy 1: Reconnect Before Expiration**

```javascript
// Client-side
let ws;
const TOKEN_LIFETIME = 5 * 60 * 1000;  // 5 minutes
const REFRESH_BUFFER = 60 * 1000;  // Reconnect 1 minute before expiration

function connect() {
    const token = getAccessToken();
    ws = new WebSocket(`wss://api.example.com/web?Authorization=${encodeURIComponent(token)}`);

    // Reconnect before token expires
    setTimeout(() => {
        ws.close();
        connect();
    }, TOKEN_LIFETIME - REFRESH_BUFFER);
}

connect();
```

**Strategy 2: Server-Initiated Reconnection**

```python
# Server sends reconnection message before token expires
if token_expires_in < 60:  # Less than 1 minute remaining
    response = ResponseModel(
        pkg_id=PkgID.SYSTEM_MESSAGE,
        req_id=generate_uuid(),
        status_code=RSPCode.TOKEN_EXPIRING,
        data={"message": "Token expiring soon, please reconnect"}
    )
    await websocket.send_response(response)
```

**Strategy 3: Token Refresh via WebSocket**

```python
@pkg_router.register(PkgID.REFRESH_TOKEN)
async def refresh_token_handler(request: RequestModel) -> ResponseModel:
    """
    Refresh access token via WebSocket.

    Client sends refresh_token, receives new access_token.
    """
    refresh_token = request.data.get("refresh_token")

    try:
        new_token = await keycloak_manager.refresh_token(refresh_token)
        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data={"access_token": new_token}
        )
    except Exception as e:
        return ResponseModel.error(request.pkg_id, request.req_id, str(e))
```

### Message Format Negotiation

Clients can choose JSON or Protobuf:

```javascript
// JSON format (default)
const ws = new WebSocket('wss://api.example.com/web?Authorization=...&format=json');

// Protobuf format (smaller, faster)
const ws = new WebSocket('wss://api.example.com/web?Authorization=...&format=protobuf');
```

**Security:** Both formats are validated, but Protobuf has stronger type safety.

### Broadcast Security

**Problem:** Sending sensitive data to all connected users

**Solution:** Filter broadcasts by user permissions

```python
async def broadcast_sensitive_data(data: dict):
    """Broadcast only to users with permission."""
    for connection in connection_manager.active_connections:
        user = connection.user

        # Check if user has permission to receive this data
        if rbac_manager.check_user_has_roles(user, ["view-sensitive-data"]):
            await connection.websocket.send_json(data)
```

### Connection Monitoring

**Metrics:**

```promql
# Active connections
ws_connections_active

# Connection rejections
rate(ws_connections_total{status="rejected_auth"}[5m])
rate(ws_connections_total{status="rejected_limit"}[5m])

# Message rate
rate(ws_messages_received_total[5m])
rate(ws_messages_sent_total[5m])
```

**Alerts:**

```yaml
- alert: HighWebSocketRejections
  expr: rate(ws_connections_total{status=~"rejected_.*"}[5m]) > 5
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "High WebSocket rejection rate"
    description: "{{ $value }} connections/s being rejected"
```

### WebSocket Security Checklist

- [ ] Origin validation enabled and configured for production
- [ ] ALLOWED_WS_ORIGINS does not contain wildcard "*" in production
- [ ] Connection limits per user configured appropriately
- [ ] Message rate limits prevent flooding
- [ ] Token expiration handled gracefully (reconnection strategy)
- [ ] Input validation on all message types
- [ ] RBAC permissions checked before handling messages
- [ ] Sensitive data not broadcast to unauthorized users
- [ ] WSS (WebSocket over TLS) used in production
- [ ] Audit logging enabled for WebSocket connections and messages

---

## Audit Logging

### Overview

Comprehensive audit logging for compliance and security monitoring:
- Non-blocking async queue-based logging
- Automatic sanitization of sensitive data
- Batch processing for performance
- Backpressure mechanism prevents data loss

**Implementation:** [`app/utils/audit_logger.py`](../../app/utils/audit_logger.py)

### What Gets Logged

Every user action is logged with:

```python
# User context
user_id: str  # Keycloak user ID
username: str  # Keycloak username
user_roles: list[str]  # Roles at time of action

# Action details
action_type: str  # HTTP method or WS:PKG_ID
resource: str  # Endpoint path or resource identifier
outcome: str  # "success", "error", "permission_denied"

# Request context
ip_address: str  # Client IP (with spoofing protection)
user_agent: str  # Client user agent
request_id: str  # Correlation ID for tracing
request_data: dict  # Request payload (sanitized)

# Response context
response_status: int  # HTTP status code or RSPCode
error_message: str | None  # Error details if failed
duration_ms: int  # Request processing time

# Metadata
timestamp: datetime  # UTC timestamp
```

### Async Queue Architecture

```mermaid
graph LR
    A[HTTP/WS Request] --> B[log_user_action]
    B --> C[Async Queue]
    C --> D[Batch Worker]
    D --> E[Bulk DB Insert]
    E --> F[PostgreSQL]

    style C fill:#f9f,stroke:#333
    style D fill:#bbf,stroke:#333
```

**Benefits:**
- Non-blocking: Returns immediately, no impact on request latency
- Batch processing: Efficient bulk inserts (100 logs per batch)
- Backpressure: Waits for queue space instead of dropping logs
- Resilient: Graceful degradation on database issues

### Configuration

```python
# app/settings.py
AUDIT_LOG_ENABLED = True
AUDIT_QUEUE_MAX_SIZE = 10000  # Max queued logs before backpressure
AUDIT_BATCH_SIZE = 100  # Logs per database transaction
AUDIT_BATCH_TIMEOUT = 1.0  # Seconds to wait for full batch
AUDIT_QUEUE_TIMEOUT = 1.0  # Seconds to wait for queue space (backpressure)
```

### Backpressure Mechanism

**Queue Full Scenario:**

```python
# Default behavior (AUDIT_QUEUE_TIMEOUT = 1.0):
1. Queue is full (10,000 logs)
2. New log arrival → Wait up to 1 second for space
3. If space available within 1s → Log enqueued
4. If timeout expires → Log dropped with warning

# Legacy behavior (AUDIT_QUEUE_TIMEOUT = 0):
1. Queue is full
2. New log arrival → Drop immediately
```

**Why Backpressure?**
- Compliance: Reduces log loss during traffic spikes
- Transparency: Logs wait time vs immediate drops
- Metrics: `audit_logs_dropped_total` tracks actual data loss

### Sensitive Data Sanitization

**Automatically redacted fields:**

```python
SENSITIVE_FIELDS = [
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token",
    "secret", "api_key", "private_key",
    "ssn", "social_security_number",
    "credit_card", "card_number", "cvv",
    "authorization"
]
```

**Example:**

```python
# Original request data
request_data = {
    "username": "john",
    "password": "SuperSecret123!",
    "email": "john@example.com",
    "api_key": "sk_live_1234567890"
}

# Stored in audit log
sanitized_data = {
    "username": "john",
    "password": "[REDACTED]",
    "email": "john@example.com",
    "api_key": "[REDACTED]"
}
```

### Usage in Endpoints

**HTTP Endpoints (Automatic):**

```python
# Middleware: app/middlewares/audit_middleware.py
# Automatically logs all HTTP requests

# No code needed - middleware intercepts all requests
```

**WebSocket Handlers (Manual):**

```python
from app.utils.audit_logger import log_user_action

@pkg_router.register(PkgID.DELETE_AUTHOR, roles=["delete-author"])
async def delete_author_handler(request: RequestModel) -> ResponseModel:
    user = request.user  # From context

    try:
        # Business logic
        await author_repository.delete(request.data["author_id"])

        # Log success
        await log_user_action(
            user_id=user.user_id,
            username=user.username,
            user_roles=user.roles,
            action_type=f"WS:{PkgID.DELETE_AUTHOR.name}",
            resource=f"author:{request.data['author_id']}",
            outcome="success",
            ip_address=get_client_ip(request),
            request_data=request.data,
            response_status=RSPCode.OK,
            duration_ms=45
        )

        return ResponseModel.success(...)

    except Exception as e:
        # Log error
        await log_user_action(
            user_id=user.user_id,
            username=user.username,
            user_roles=user.roles,
            action_type=f"WS:{PkgID.DELETE_AUTHOR.name}",
            resource=f"author:{request.data.get('author_id', 'unknown')}",
            outcome="error",
            error_message=str(e),
            ip_address=get_client_ip(request),
            request_data=request.data,
            response_status=RSPCode.ERROR,
            duration_ms=12
        )
        raise
```

### Querying Audit Logs

**Grafana Dashboard:**

The Audit Logs Dashboard (`audit-logs`) provides:
- Time series of events by outcome
- Top users by activity
- Recent audit events table
- Failed/denied actions table

Access at: http://localhost:3000/d/audit-logs

**SQL Queries:**

```sql
-- Find all actions by specific user
SELECT timestamp, action_type, resource, outcome, error_message
FROM user_actions
WHERE username = 'john.doe'
ORDER BY timestamp DESC
LIMIT 100;

-- Find all failed login attempts
SELECT timestamp, username, ip_address, error_message
FROM user_actions
WHERE action_type = 'POST' AND resource = '/auth/login' AND outcome = 'error'
AND timestamp > NOW() - INTERVAL '24 hours';

-- Find all permission denied events
SELECT timestamp, username, action_type, resource, user_roles
FROM user_actions
WHERE outcome = 'permission_denied'
ORDER BY timestamp DESC;

-- Track user activity patterns
SELECT
    DATE_TRUNC('hour', timestamp) AS hour,
    username,
    COUNT(*) AS action_count,
    SUM(CASE WHEN outcome = 'error' THEN 1 ELSE 0 END) AS errors
FROM user_actions
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY hour, username
ORDER BY hour, action_count DESC;
```

### Compliance Considerations

**GDPR Compliance:**

```python
# Data retention policy
DELETE FROM user_actions
WHERE timestamp < NOW() - INTERVAL '2 years';

# User data deletion (right to be forgotten)
DELETE FROM user_actions
WHERE user_id = '<user_id_to_delete>';

# Pseudonymization for analytics
UPDATE user_actions
SET username = 'user_' || MD5(username)
WHERE timestamp < NOW() - INTERVAL '90 days';
```

**SOX/HIPAA Compliance:**

```python
# Immutability - audit logs should never be modified
# Implement as database trigger:
CREATE TRIGGER prevent_audit_log_modification
BEFORE UPDATE ON user_actions
FOR EACH ROW
EXECUTE FUNCTION prevent_modification();

# Separate audit log database with restricted access
# Only audit service can write, only auditors can read
```

### Monitoring Audit Logs

**Prometheus Metrics:**

```promql
# Total audit logs created
rate(audit_logs_total{outcome="success"}[5m])

# Audit logs dropped due to queue overflow
rate(audit_logs_dropped_total[5m])

# Queue depth
audit_queue_size

# Batch processing efficiency
audit_batch_size
```

**Alerts:**

```yaml
- alert: AuditLogDropping
  expr: rate(audit_logs_dropped_total[2m]) > 1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Audit logs being dropped"
    description: "{{ $value }} logs/s dropped (compliance risk!)"

- alert: HighAuditLogDropRate
  expr: |
    (rate(audit_logs_dropped_total[2m]) /
     rate(audit_logs_total[2m])) > 0.01
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High audit log drop rate"
    description: "{{ $value | humanizePercentage }} of logs being dropped"
```

### Troubleshooting

**Problem:** Audit logs being dropped

```bash
# Check queue size
curl http://localhost:9090/api/v1/query?query=audit_queue_size

# Check drop rate
curl http://localhost:9090/api/v1/query?query=rate(audit_logs_dropped_total[5m])
```

**Solutions:**
1. Increase queue size: `AUDIT_QUEUE_MAX_SIZE = 20000`
2. Increase batch size for faster processing: `AUDIT_BATCH_SIZE = 200`
3. Optimize database write performance (indexes, connection pool)
4. Scale horizontally (add more application instances)

**Problem:** Slow database writes

```bash
# Check batch write duration
curl http://localhost:9090/api/v1/query?query=audit_log_creation_duration_seconds
```

**Solutions:**
1. Add database index on `timestamp`, `username`, `user_id`
2. Increase database connection pool size
3. Consider partitioning `user_actions` table by time

---

## IP Spoofing Protection

### Overview

Prevents attackers from forging IP addresses via `X-Forwarded-For` header:
- Validates proxy authenticity
- Supports CIDR notation for trusted proxy ranges
- Logs warnings for untrusted sources

**Implementation:** [`app/utils/ip_utils.py`](../../app/utils/ip_utils.py)

### How IP Spoofing Works

**Attack Scenario:**

```http
# Attacker sends request with forged X-Forwarded-For header
GET /api/sensitive HTTP/1.1
Host: api.example.com
X-Forwarded-For: 192.168.1.1  # Forged internal IP

# Without validation:
# - Rate limiting bypassed (new IP each request)
# - Audit logs show wrong IP
# - IP-based access controls bypassed
```

### Trusted Proxy Validation

**Configuration:**

```python
# app/settings.py
TRUSTED_PROXIES = [
    "10.0.0.0/8",      # Private network
    "172.16.0.0/12",   # Private network
    "192.168.0.0/16",  # Private network
    "203.0.113.0/24"   # Your CDN/load balancer IPs
]
```

**How It Works:**

```python
def get_client_ip(request: Request) -> str:
    """
    Safely extract client IP with spoofing protection.

    Priority:
    1. X-Forwarded-For header (if from trusted proxy)
    2. Direct client.host (fallback)
    """
    # Check if request came through trusted proxy
    direct_ip = request.client.host

    if is_trusted_proxy(direct_ip):
        # Trust X-Forwarded-For from trusted proxy
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            # First IP in comma-separated list is the client
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip

    # Not from trusted proxy - use direct IP
    # Log warning if X-Forwarded-For present (potential spoof attempt)
    if "X-Forwarded-For" in request.headers:
        logger.warning(
            f"Untrusted X-Forwarded-For header from {direct_ip}: "
            f"{request.headers['X-Forwarded-For']}"
        )

    return direct_ip
```

### Production Deployment

**AWS/ELB:**

```python
# Trust ALB/ELB IP ranges
TRUSTED_PROXIES = [
    "10.0.0.0/8",  # VPC private IPs
    # Add AWS ALB IP ranges for your region
]
```

**Nginx Reverse Proxy:**

```python
# Trust Nginx server IP
TRUSTED_PROXIES = [
    "172.17.0.2",  # Docker nginx container
    "10.0.1.0/24"  # Nginx server subnet
]

# Nginx configuration (set real IP from X-Forwarded-For)
# /etc/nginx/nginx.conf
set_real_ip_from 10.0.0.0/8;
real_ip_header X-Forwarded-For;
```

**Cloudflare:**

```python
# Trust Cloudflare IP ranges
# https://www.cloudflare.com/ips/
TRUSTED_PROXIES = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    # ... add all Cloudflare ranges
]
```

### Testing

```bash
# Test with trusted proxy
curl -H "X-Forwarded-For: 1.2.3.4" http://localhost:8000/api/test
# Result: IP logged as 1.2.3.4 (trusted)

# Test with untrusted source (direct connection)
curl -H "X-Forwarded-For: 1.2.3.4" http://your-api.com/api/test
# Result: IP logged as your actual IP (untrusted header ignored)
# Warning logged: "Untrusted X-Forwarded-For header from <your_ip>"
```

### CIDR Notation Support

```python
def is_trusted_proxy(ip_address: str) -> bool:
    """Check if IP belongs to trusted proxy (supports CIDR)."""
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_address)

        for trusted in TRUSTED_PROXIES:
            # Single IP
            if "/" not in trusted:
                if str(ip) == trusted:
                    return True
            # CIDR notation (e.g., "10.0.0.0/8")
            else:
                network = ipaddress.ip_network(trusted, strict=False)
                if ip in network:
                    return True

        return False
    except ValueError:
        logger.error(f"Invalid IP address: {ip_address}")
        return False
```

### Usage in Application

**Audit Logging:**

```python
# app/middlewares/audit_middleware.py
ip_address = get_client_ip(request)  # Safe IP extraction

await log_user_action(
    ...
    ip_address=ip_address,  # Accurate IP in audit logs
    ...
)
```

**Rate Limiting:**

```python
# app/middlewares/rate_limit.py
if user:
    rate_limit_key = f"rate_limit:user:{user.username}"
else:
    # Fall back to IP-based rate limit
    ip_address = get_client_ip(request)  # Protected from spoofing
    rate_limit_key = f"rate_limit:ip:{ip_address}"
```

---

## Circuit Breakers

### Overview

Circuit breakers prevent cascading failures when external services (Keycloak, Redis) are unavailable:
- Fail-fast instead of waiting for timeouts
- Automatic recovery testing
- Prometheus metrics for monitoring

**Implementation:**
- Keycloak: [`app/managers/keycloak_manager.py`](../../app/managers/keycloak_manager.py)
- Redis: [`app/storage/redis.py`](../../app/storage/redis.py)

### How Circuit Breakers Work

```mermaid
stateDiagram-v2
    [*] --> Closed: Normal Operation
    Closed --> Open: N Failures
    Open --> HalfOpen: Timeout Expires
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure

    note right of Closed
        All requests pass through
        Failures counted
    end note

    note right of Open
        Requests fail immediately
        No calls to service
    end note

    note right of HalfOpen
        One request allowed
        Test if service recovered
    end note
```

### Keycloak Circuit Breaker

**Configuration:**

```python
# app/settings.py
CIRCUIT_BREAKER_ENABLED = True
KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX = 5  # Open after 5 failures
KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT = 60  # Keep open for 60 seconds
```

**Protected Operations:**

```python
# app/managers/keycloak_manager.py
@CircuitBreaker(fail_max=KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX,
                 timeout_seconds=KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT)
async def login_async(username: str, password: str) -> dict:
    """
    Login to Keycloak.

    Protected by circuit breaker - fails fast if Keycloak is down.
    """
    return await self.openid.a_token(username, password)
```

**Behavior:**

```python
# Closed (normal):
result = await keycloak_manager.login_async(username, password)
# Calls Keycloak, returns token

# Open (after 5 failures):
result = await keycloak_manager.login_async(username, password)
# Raises CircuitBreakerError immediately (no call to Keycloak)

# Half-Open (after 60 seconds):
result = await keycloak_manager.login_async(username, password)
# Allows ONE test request
# If successful → Closed
# If failed → Open for another 60 seconds
```

### Redis Circuit Breaker

**Configuration:**

```python
# app/settings.py
REDIS_CIRCUIT_BREAKER_FAIL_MAX = 3  # Open after 3 failures
REDIS_CIRCUIT_BREAKER_TIMEOUT = 30  # Keep open for 30 seconds
```

**Protected Operations:**

```python
# app/storage/redis.py
@CircuitBreaker(fail_max=REDIS_CIRCUIT_BREAKER_FAIL_MAX,
                 timeout_seconds=REDIS_CIRCUIT_BREAKER_TIMEOUT)
async def get_redis_connection(db: int = 1) -> Redis | None:
    """
    Get Redis connection.

    Protected by circuit breaker for resilience.
    """
    return await RedisPool.get_instance(db)
```

**Fail-Open Behavior:**

```python
# Rate limiter with fail-open
async def check_rate_limit(key, limit):
    try:
        redis = await get_redis_connection()
        # Use Redis for rate limiting
    except CircuitBreakerError:
        # Redis circuit is open - fail-open
        logger.warning("Redis circuit breaker open, allowing request")
        return (True, limit)  # Allow request
```

### Monitoring Circuit Breakers

**Prometheus Metrics:**

```promql
# Circuit breaker state (0=closed, 1=open, 2=half_open)
circuit_breaker_state{service="keycloak"}
circuit_breaker_state{service="redis"}

# State transitions
circuit_breaker_state_changes_total{service="keycloak", from_state="closed", to_state="open"}

# Total failures detected
circuit_breaker_failures_total{service="keycloak"}
```

**Grafana Visualization:**

```promql
# Circuit breaker state over time
circuit_breaker_state{service="keycloak"}

# Alert when circuit is open
circuit_breaker_state{service="keycloak"} == 1
```

**Alerts:**

```yaml
- alert: KeycloakCircuitBreakerOpen
  expr: circuit_breaker_state{service="keycloak"} == 1
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Keycloak circuit breaker is OPEN"
    description: "Authentication will fail until Keycloak recovers"

- alert: RedisCircuitBreakerOpen
  expr: circuit_breaker_state{service="redis"} == 1
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Redis circuit breaker is OPEN"
    description: "Rate limiting and caching degraded"
```

### Benefits

**1. Fail-Fast:**
```python
# Without circuit breaker:
# - Keycloak down
# - Every auth attempt waits for 30s timeout
# - Request latency: 30+ seconds
# - Resource exhaustion from waiting threads

# With circuit breaker:
# - Keycloak down
# - Circuit opens after 5 failures (~150s)
# - Future requests fail immediately (< 1ms)
# - Resources freed for other tasks
```

**2. Automatic Recovery:**
```python
# Circuit automatically tests service recovery
# No manual intervention needed
# Half-open state allows safe testing
```

**3. Clear Visibility:**
```python
# Metrics show service health
# Alerts notify when services degraded
# Dashboard shows circuit breaker state
```

### Tuning Circuit Breakers

**Aggressive (Fail-fast):**

```python
# Open quickly, short timeout
KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX = 3  # 3 failures
KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT = 30  # 30 seconds

# Use for: Critical path, strict SLA requirements
```

**Conservative (Tolerant):**

```python
# Open slowly, long timeout
KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX = 10  # 10 failures
KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT = 120  # 2 minutes

# Use for: Non-critical path, intermittent issues
```

**Disable for Development:**

```python
# Disable circuit breakers in development
CIRCUIT_BREAKER_ENABLED = False
```

---

## Security Deployment Checklist

Use this checklist before deploying to production:

### Environment Configuration

- [ ] `ENV=production` in environment variables
- [ ] All `CHANGE_ME` values replaced in `.env.production`
- [ ] Strong secret keys generated (not default values)
- [ ] Database credentials not in code (environment variables only)
- [ ] Redis password set (if exposed outside Docker network)

### HTTPS / TLS

- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Valid SSL/TLS certificate installed (not self-signed)
- [ ] HSTS header enabled (`Strict-Transport-Security`)
- [ ] TLS 1.2+ only (disable TLS 1.0, 1.1)
- [ ] Strong cipher suites configured

### Authentication & Authorization

- [ ] Keycloak token TTL configured (5-15 minutes recommended)
- [ ] Token refresh mechanism implemented for long sessions
- [ ] RBAC permissions configured for all sensitive endpoints
- [ ] Public endpoints intentionally marked (no accidental public access)
- [ ] Excluded paths reviewed (only health checks, metrics should bypass auth)

### Rate Limiting

- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Appropriate limits configured for API usage patterns
- [ ] Fail mode set to `closed` for strict enforcement
- [ ] Burst allowances configured for traffic spikes
- [ ] WebSocket connection limits per user configured
- [ ] WebSocket message rate limits configured

### WebSocket Security

- [ ] `ALLOWED_WS_ORIGINS` set to specific domains (no wildcard "*")
- [ ] Origin validation enabled in production
- [ ] WSS (WebSocket over TLS) used (not WS)
- [ ] Connection limits prevent resource exhaustion
- [ ] Token refresh strategy implemented for long-lived connections

### Network Security

- [ ] `ALLOWED_HOSTS` configured (no wildcard "*")
- [ ] Trusted proxies configured for `X-Forwarded-For` validation
- [ ] IP spoofing protection verified
- [ ] Firewall rules restrict database/Redis access
- [ ] Prometheus `/metrics` endpoint secured (network policy or auth)

### Audit Logging

- [ ] Audit logging enabled (`AUDIT_LOG_ENABLED=true`)
- [ ] Log retention policy configured (GDPR/compliance)
- [ ] Audit log backups scheduled
- [ ] Alerts configured for dropped audit logs
- [ ] Log aggregation configured (Loki/ELK)

### Security Headers

- [ ] Security headers verified with scanner
- [ ] CSP configured appropriately for your app
- [ ] HSTS preload considered (if public site)
- [ ] Referrer-Policy prevents token leakage

### Input Validation

- [ ] Pydantic models used for all input validation
- [ ] String length limits on all user input
- [ ] JSON Schema validation for WebSocket messages
- [ ] SQL injection prevention verified (parameterized queries)
- [ ] Path traversal prevention in file operations

### Monitoring & Alerting

- [ ] Prometheus alerts configured for security events
- [ ] High authentication failure rate alert
- [ ] Rate limit violation alerts
- [ ] Circuit breaker open alerts
- [ ] Audit log dropping alerts
- [ ] Grafana dashboards configured

### Dependency Security

- [ ] All dependencies up to date
- [ ] `skjold` vulnerability scan passing
- [ ] `bandit` security scan passing
- [ ] Dependabot enabled for automatic updates
- [ ] Regular security update schedule established

### Incident Response

- [ ] Security incident response plan documented
- [ ] Contact information for security team
- [ ] Log aggregation for forensic analysis
- [ ] Backup and recovery procedures tested
- [ ] Rollback procedures documented

### Documentation

- [ ] Security documentation accessible to team
- [ ] API documentation includes auth requirements
- [ ] Deployment guide includes security setup
- [ ] Security best practices communicated to developers

---

## Common Security Pitfalls

### 1. Mass Assignment

**Problem:**

```python
# ❌ VULNERABLE - Accepts any field from user input
@router.post("/users")
async def create_user(data: dict):
    user = User(**data)  # Attacker can set is_admin=True!
    await session.add(user)
```

**Solution:**

```python
# ✅ SAFE - Pydantic model whitelists allowed fields
class CreateUserInput(BaseModel):
    username: str
    email: EmailStr
    # is_admin NOT included - cannot be set by user

@router.post("/users")
async def create_user(data: CreateUserInput):
    user = User(**data.model_dump())  # Only whitelisted fields
    await session.add(user)
```

### 2. SQL Injection

**Problem:**

```python
# ❌ VULNERABLE - String formatting in query
@router.get("/users")
async def search_users(name: str):
    query = f"SELECT * FROM users WHERE name = '{name}'"
    result = await session.execute(text(query))
    # Attacker: name = "'; DROP TABLE users; --"
```

**Solution:**

```python
# ✅ SAFE - Parameterized query
@router.get("/users")
async def search_users(name: str):
    stmt = select(User).where(User.name == name)
    result = await session.execute(stmt)
    # SQLAlchemy automatically parameterizes
```

### 3. Broken Authentication

**Problem:**

```python
# ❌ VULNERABLE - No token validation
@router.get("/profile")
async def get_profile(user_id: str):
    # Attacker can access any user's profile!
    user = await get_user(user_id)
    return user
```

**Solution:**

```python
# ✅ SAFE - Token validation + user context
@router.get("/profile")
async def get_profile(user: UserModel = Depends(get_current_user)):
    # User is authenticated via JWT token
    # Can only access their own profile
    return user
```

### 4. Sensitive Data Exposure

**Problem:**

```python
# ❌ VULNERABLE - Logging sensitive data
logger.info(f"User login: {username}, password: {password}")

# ❌ VULNERABLE - Returning sensitive data
@router.get("/users/{id}")
async def get_user(id: int):
    user = await get_user(id)
    return user  # Includes password_hash, api_keys, etc.!
```

**Solution:**

```python
# ✅ SAFE - Don't log sensitive data
logger.info(f"User login: {username}")

# ✅ SAFE - Response model excludes sensitive fields
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    # password_hash excluded

@router.get("/users/{id}")
async def get_user(id: int) -> UserResponse:
    user = await get_user(id)
    return UserResponse(**user.model_dump())
```

### 5. Broken Access Control

**Problem:**

```python
# ❌ VULNERABLE - No permission check
@router.delete("/users/{id}")
async def delete_user(id: int, user: UserModel = Depends(get_current_user)):
    # Any authenticated user can delete any user!
    await delete_user_logic(id)
```

**Solution:**

```python
# ✅ SAFE - Permission check
@router.delete(
    "/users/{id}",
    dependencies=[Depends(require_roles("delete-user", "admin"))]
)
async def delete_user(id: int, user: UserModel = Depends(get_current_user)):
    # Only users with required roles can delete
    await delete_user_logic(id)
```

### 6. Security Misconfiguration

**Problem:**

```python
# ❌ VULNERABLE - Production settings
ENV = "development"  # Debug mode in production!
ALLOWED_HOSTS = ["*"]  # Any host accepted
ALLOWED_WS_ORIGINS = ["*"]  # No CSRF protection
RATE_LIMIT_ENABLED = False  # No rate limiting
```

**Solution:**

```python
# ✅ SAFE - Production settings
ENV = "production"
ALLOWED_HOSTS = ["api.example.com"]
ALLOWED_WS_ORIGINS = ["https://app.example.com"]
RATE_LIMIT_ENABLED = True
```

### 7. Injection Attacks

**Problem:**

```python
# ❌ VULNERABLE - Command injection
import os

@router.get("/ping")
async def ping(host: str):
    result = os.system(f"ping -c 1 {host}")
    # Attacker: host = "example.com; rm -rf /"
```

**Solution:**

```python
# ✅ SAFE - Input validation + whitelist
import subprocess

@router.get("/ping")
async def ping(host: str = Field(pattern=r'^[a-zA-Z0-9.-]+$')):
    # Validate hostname format
    if not is_valid_hostname(host):
        raise HTTPException(400, "Invalid hostname")

    # Use subprocess with argument list (not shell)
    result = subprocess.run(
        ["ping", "-c", "1", host],
        capture_output=True,
        timeout=5
    )
    return {"output": result.stdout.decode()}
```

### 8. Insecure Deserialization

**Problem:**

```python
# ❌ VULNERABLE - pickle deserialization
import pickle

@router.post("/data")
async def process_data(data: bytes):
    obj = pickle.loads(data)  # Attacker can execute arbitrary code!
```

**Solution:**

```python
# ✅ SAFE - Pydantic validation
@router.post("/data")
async def process_data(data: MyDataModel):
    # Pydantic validates and deserializes safely
    return process_logic(data)
```

### 9. Insufficient Logging

**Problem:**

```python
# ❌ BAD - No logging
@router.post("/admin/delete-all")
async def delete_all_data():
    await delete_everything()
    # No audit trail! Who did this?
```

**Solution:**

```python
# ✅ GOOD - Comprehensive logging
@router.post("/admin/delete-all")
async def delete_all_data(user: UserModel = Depends(get_current_user)):
    logger.warning(
        f"Delete all data requested by {user.username} ({user.user_id})"
    )
    await log_user_action(
        user_id=user.user_id,
        username=user.username,
        action_type="DELETE_ALL",
        outcome="success"
    )
    await delete_everything()
```

### 10. Using Components with Known Vulnerabilities

**Problem:**

```python
# ❌ BAD - Outdated dependencies
fastapi==0.68.0  # Contains known CVE
requests==2.25.0  # Vulnerable version
```

**Solution:**

```bash
# ✅ GOOD - Regular updates
uv sync  # Update dependencies
make skjold-scan  # Check for vulnerabilities
make outdated-pkgs-scan  # Check for outdated packages

# Enable Dependabot for automatic PRs
```

---

## Security Testing

### Automated Security Scanning

**1. Static Application Security Testing (SAST):**

```bash
# Bandit - Python security scanner
make bandit-scan
# Or: uvx bandit -r app/ -ll -confidence-level=low

# Scans for:
# - SQL injection vulnerabilities
# - Command injection
# - Hardcoded passwords
# - Insecure cryptography
# - Path traversal
```

**2. Dependency Vulnerability Scanning:**

```bash
# Skjold - Dependency vulnerability scanner
make skjold-scan
# Or: uvx skjold audit

# Checks against:
# - GitHub Advisory Database
# - PyPA Advisory Database
# - Known CVEs
```

**3. Outdated Package Detection:**

```bash
# Check for outdated packages
make outdated-pkgs-scan
# Or: uv pip list --outdated
```

### Manual Security Testing

**1. Test Authentication:**

```bash
# Test missing token
curl -X GET http://localhost:8000/api/protected
# Expected: 401 Unauthorized

# Test invalid token
curl -H "Authorization: Bearer invalid_token" \
    http://localhost:8000/api/protected
# Expected: 401 Unauthorized

# Test expired token
curl -H "Authorization: Bearer <expired_token>" \
    http://localhost:8000/api/protected
# Expected: 401 Unauthorized
```

**2. Test Authorization (RBAC):**

```bash
# Test insufficient permissions
curl -H "Authorization: Bearer <user_token>" \
    -X DELETE http://localhost:8000/api/authors/1
# Expected: 403 Forbidden (if user lacks delete-author role)

# Test with admin role
curl -H "Authorization: Bearer <admin_token>" \
    -X DELETE http://localhost:8000/api/authors/1
# Expected: 200 OK
```

**3. Test Rate Limiting:**

```bash
# Rapid requests
for i in {1..100}; do
    curl http://localhost:8000/api/endpoint
done
# Expected: 429 Too Many Requests after limit exceeded
```

**4. Test Input Validation:**

```bash
# SQL injection attempt
curl -X POST http://localhost:8000/api/users \
    -H "Content-Type: application/json" \
    -d '{"username": "admin; DROP TABLE users;--"}'
# Expected: 422 Unprocessable Entity (validation error)

# XSS attempt
curl -X POST http://localhost:8000/api/comments \
    -H "Content-Type: application/json" \
    -d '{"text": "<script>alert(1)</script>"}'
# Expected: 422 (if pattern validation) or sanitized on output
```

**5. Test Security Headers:**

```bash
# Check security headers
curl -I http://localhost:8000/

# Verify presence of:
# - X-Frame-Options: DENY
# - X-Content-Type-Options: nosniff
# - Content-Security-Policy: ...
# - Strict-Transport-Security: ...
```

**6. Test WebSocket Security:**

```bash
# Test origin validation (requires custom script)
# Connect with Origin: https://evil.com
# Expected: Connection closed with WS_1008_POLICY_VIOLATION
```

### Security Header Scanners

```bash
# Online scanners
https://securityheaders.com/?q=https://your-api.com
https://observatory.mozilla.org/analyze/your-api.com

# Expected Grade: A or A+
```

### Penetration Testing

**Recommended Tools:**

1. **OWASP ZAP** - Automated web app scanner
2. **Burp Suite** - Manual penetration testing
3. **sqlmap** - SQL injection testing
4. **Nmap** - Port scanning and service detection

**Penetration Testing Checklist:**

- [ ] Authentication bypass attempts
- [ ] Authorization bypass (access other users' data)
- [ ] SQL injection in all input fields
- [ ] XSS in user-generated content
- [ ] CSRF token validation
- [ ] File upload vulnerabilities
- [ ] Directory traversal
- [ ] API rate limiting enforcement
- [ ] Session fixation/hijacking
- [ ] Brute force protection

**Example with OWASP ZAP:**

```bash
# Docker container
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t http://your-api.com

# Full scan
docker run -t owasp/zap2docker-stable zap-full-scan.py \
    -t http://your-api.com
```

---

## Troubleshooting

### Authentication Issues

**Problem:** Token validation failing

```
AuthenticationError: token_decode_error
```

**Diagnosis:**

```bash
# Check Keycloak is reachable
curl http://keycloak:8080/health

# Check circuit breaker state
curl http://localhost:9090/api/v1/query?query=circuit_breaker_state{service="keycloak"}

# Check token cache
redis-cli
> KEYS token:claims:*
> TTL token:claims:<hash>
```

**Solutions:**

1. Verify Keycloak is running and healthy
2. Check token hasn't expired (decode JWT at jwt.io)
3. Verify Keycloak client settings match configuration
4. Check Redis is available (token cache)
5. Review circuit breaker configuration

**Problem:** CORS errors in browser

```
Access to fetch at 'http://api.example.com' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solution:**

```python
# app/__init__.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting Issues

**Problem:** Legitimate users being rate limited

**Diagnosis:**

```promql
# Check rate limit hit rate
rate(rate_limit_hits_total[5m])

# Check per-user rate limits
# (requires custom logging)
```

**Solutions:**

1. Increase rate limits: `RATE_LIMIT_PER_MINUTE = 120`
2. Add burst allowance: `RATE_LIMIT_BURST = 30`
3. Whitelist specific IPs/users (custom implementation)
4. Implement tiered rate limits based on user roles

**Problem:** Rate limiting not working (Redis down)

**Diagnosis:**

```bash
# Check Redis connection
redis-cli PING

# Check circuit breaker
curl http://localhost:9090/api/v1/query?query=circuit_breaker_state{service="redis"}
```

**Solutions:**

1. Fix Redis connection
2. Check circuit breaker timeout
3. Verify `RATE_LIMIT_FAIL_MODE` setting (fail-open vs fail-closed)

### WebSocket Issues

**Problem:** WebSocket connections being rejected

```
WebSocket close code: 1008 (Policy Violation)
```

**Diagnosis:**

```bash
# Check connection rejections by reason
curl http://localhost:9090/api/v1/query?query=ws_connections_total{status="rejected_auth"}
curl http://localhost:9090/api/v1/query?query=ws_connections_total{status="rejected_limit"}
```

**Solutions:**

1. **Authentication:** Verify token is valid and not expired
2. **Origin:** Check Origin header matches `ALLOWED_WS_ORIGINS`
3. **Connection limit:** Increase `WS_MAX_CONNECTIONS_PER_USER`
4. **Message rate limit:** Increase `WS_MESSAGE_RATE_LIMIT`

**Problem:** CSP blocking WebSocket connections

```
Refused to connect to 'ws://localhost:8000/web' because it violates the following Content Security Policy directive: "connect-src 'self'"
```

**Solution:**

```python
# app/middlewares/security_headers.py
# Ensure connect-src includes ws: and wss:
"connect-src 'self' ws: wss:",
```

### Audit Log Issues

**Problem:** Audit logs being dropped

**Diagnosis:**

```promql
# Check drop rate
rate(audit_logs_dropped_total[5m])

# Check queue size
audit_queue_size
```

**Solutions:**

1. Increase queue size: `AUDIT_QUEUE_MAX_SIZE = 20000`
2. Increase batch size: `AUDIT_BATCH_SIZE = 200`
3. Optimize database (indexes, connection pool)
4. Scale horizontally (more app instances)

**Problem:** Slow audit log writes

**Diagnosis:**

```promql
# Check write duration
audit_log_creation_duration_seconds

# Check batch size
audit_batch_size
```

**Solutions:**

```sql
-- Add database indexes
CREATE INDEX idx_user_actions_timestamp ON user_actions(timestamp);
CREATE INDEX idx_user_actions_username ON user_actions(username);
CREATE INDEX idx_user_actions_user_id ON user_actions(user_id);

-- Partition table by time (for very large tables)
-- (requires migration script)
```

---

## Related Documentation

- [Authentication Guide](authentication.md) - Keycloak setup and configuration
- [WebSocket Protocol](websocket-protocol.md) - WebSocket message format and usage
- [Monitoring Guide](../../../docs/claude/monitoring-guide.md) - Prometheus, Grafana, alerts
- [Testing Guide](../../../docs/claude/testing-guide.md) - Security testing patterns

---

## Additional Resources

**OWASP Resources:**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)

**Security Tools:**
- [Bandit](https://bandit.readthedocs.io/) - Python security scanner
- [Skjold](https://github.com/twu/skjold) - Dependency vulnerability scanner
- [OWASP ZAP](https://www.zaproxy.org/) - Web application scanner

**FastAPI Security:**
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)

**Compliance:**
- [GDPR Compliance Checklist](https://gdpr.eu/checklist/)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [SOX IT Controls](https://www.soxlaw.com/)
