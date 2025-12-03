# HTTP API Documentation

## Overview

This FastAPI application provides RESTful HTTP endpoints with OpenAPI/Swagger documentation. All endpoints support JSON request/response format and include automatic validation via Pydantic models.

## Base URL

```
http://localhost:8000
https://localhost:8000 (production with TLS)
```

## Authentication

Most endpoints require authentication via Keycloak access token passed in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Obtaining Access Token

**Endpoint:** `POST /login`

**Request:**
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "scope": "profile email"
}
```

**Token Expiration:**
- Access tokens: 300 seconds (5 minutes)
- Refresh tokens: 1800 seconds (30 minutes)

## Rate Limiting

HTTP endpoints are rate-limited to prevent abuse:

**Default Limits:**
- 60 requests per minute per user/IP
- Burst allowance: 10 additional requests

**Rate Limit Headers:**

All responses include rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705320000
```

**Rate Limit Exceeded Response:**

Status Code: `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

## Endpoints

### Health Check

#### GET /health

Check the health status of the application and its dependencies.

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy"
}
```

**Unhealthy Response:** `503 Service Unavailable`

```json
{
  "status": "unhealthy",
  "database": "unhealthy",
  "redis": "healthy"
}
```

**Example:**

```bash
curl http://localhost:8000/health
```

---

### Authors Endpoints

#### POST /authors

Create a new author.

**Authentication:** Required (Role: `user`)

**Request Body:**

```json
{
  "name": "John Doe"
}
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "name": "John Doe"
}
```

**Error Responses:**

| Status Code | Reason | Response |
|-------------|--------|----------|
| 401 | Unauthorized | `{"detail": "Not authenticated"}` |
| 403 | Permission denied | `{"detail": "Forbidden"}` |
| 422 | Validation error | `{"detail": [...validation errors...]}` |
| 500 | Database error | `{"detail": "Internal server error"}` |

**Example:**

```bash
curl -X POST http://localhost:8000/authors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}'
```

**Python Example:**

```python
import requests

response = requests.post(
    'http://localhost:8000/authors',
    headers={'Authorization': f'Bearer {token}'},
    json={'name': 'John Doe'}
)

if response.status_code == 200:
    author = response.json()
    print(f"Created author with ID: {author['id']}")
```

---

#### GET /authors

Retrieve a list of authors with optional filtering.

**Authentication:** Required (Role: `user`)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | No | Filter by author ID |
| `name` | string | No | Filter by author name (case-insensitive, partial match) |

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "John Doe"
  },
  {
    "id": 2,
    "name": "Jane Smith"
  }
]
```

**Empty Result:**

```json
[]
```

**Example:**

```bash
# Get all authors
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/authors

# Filter by name
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/authors?name=John"

# Filter by ID
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/authors?id=1"
```

**Python Example:**

```python
import requests

response = requests.get(
    'http://localhost:8000/authors',
    headers={'Authorization': f'Bearer {token}'},
    params={'name': 'John'}
)

authors = response.json()
for author in authors:
    print(f"{author['id']}: {author['name']}")
```

---

#### GET /authors_paginated

Retrieve a paginated list of authors with optional filtering.

**Authentication:** Required (Role: `user`)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number (>=1) |
| `per_page` | integer | No | 20 | Items per page (>=1) |
| `id` | integer | No | - | Filter by author ID |
| `name` | string | No | - | Filter by author name |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "name": "John Doe"
    },
    {
      "id": 2,
      "name": "Jane Smith"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 42,
    "pages": 3
  }
}
```

**Metadata Fields:**

| Field | Description |
|-------|-------------|
| `page` | Current page number |
| `per_page` | Number of items per page |
| `total` | Total number of items matching filters |
| `pages` | Total number of pages |

**Example:**

```bash
# Get first page (default 20 items)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/authors_paginated

# Get specific page with custom page size
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/authors_paginated?page=2&per_page=10"

# Paginate with filters
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/authors_paginated?page=1&per_page=10&name=Smith"
```

**Python Example:**

```python
import requests

def get_all_authors(token):
    """Fetch all authors using pagination."""
    all_authors = []
    page = 1

    while True:
        response = requests.get(
            'http://localhost:8000/authors_paginated',
            headers={'Authorization': f'Bearer {token}'},
            params={'page': page, 'per_page': 100}
        )

        data = response.json()
        all_authors.extend(data['items'])

        if page >= data['meta']['pages']:
            break

        page += 1

    return all_authors
```

---

### Metrics Endpoint

#### GET /metrics

Retrieve Prometheus metrics for monitoring.

**Authentication:** Not required

**Content-Type:** `text/plain; version=0.0.4`

**Response:** `200 OK`

```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/authors",status_code="200"} 1234.0

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/authors",le="0.005"} 100.0

# HELP ws_connections_active Active WebSocket connections
# TYPE ws_connections_active gauge
ws_connections_active 5.0
```

**Example:**

```bash
curl http://localhost:8000/metrics
```

## Error Handling

### Standard Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request successful |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | User lacks required permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error in request data |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error occurred |
| 503 | Service Unavailable | Service or dependency unhealthy |

### Validation Errors (422)

Pydantic validation errors include detailed field-level information:

```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "name"],
      "msg": "Input should be a valid string",
      "input": 123
    }
  ]
}
```

**Fields:**
- `type`: Type of validation error
- `loc`: Location of error (path to field)
- `msg`: Human-readable error message
- `input`: The invalid input value

## Role-Based Access Control (RBAC)

Endpoints are protected by role-based access control defined in `actions.json`.

**Common Roles:**

| Role | Description | Endpoints Access |
|------|-------------|------------------|
| `user` | Basic authenticated user | All author endpoints, health |
| `admin` | Administrative privileges | All endpoints + admin operations |
| `developer` | Development access | All endpoints + debug features |

**Permission Denied Response:** `403 Forbidden`

```json
{
  "detail": "Forbidden"
}
```

## OpenAPI/Swagger Documentation

Interactive API documentation is available at:

**Swagger UI:** http://localhost:8000/docs

**ReDoc:** http://localhost:8000/redoc

**OpenAPI JSON:** http://localhost:8000/openapi.json

These provide:
- Interactive request testing
- Request/response schema documentation
- Example values
- Authentication configuration

## Best Practices

### 1. Token Management

```python
import requests
from datetime import datetime, timedelta

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.token_expiry = None

    def login(self, username, password):
        response = requests.post(
            f'{self.base_url}/login',
            json={'username': username, 'password': password}
        )
        data = response.json()

        self.token = data['access_token']
        self.token_expiry = datetime.now() + timedelta(seconds=data['expires_in'])

    def _ensure_authenticated(self):
        if not self.token or datetime.now() >= self.token_expiry:
            raise Exception('Token expired or missing')

    def get_authors(self, **filters):
        self._ensure_authenticated()
        response = requests.get(
            f'{self.base_url}/authors',
            headers={'Authorization': f'Bearer {self.token}'},
            params=filters
        )
        response.raise_for_status()
        return response.json()
```

### 2. Error Handling

```python
import requests
from requests.exceptions import RequestException

def safe_api_call(func):
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Authentication failed")
            elif e.response.status_code == 403:
                print("Permission denied")
            elif e.response.status_code == 429:
                print("Rate limit exceeded")
            else:
                print(f"HTTP error: {e}")
        except RequestException as e:
            print(f"Request failed: {e}")
        return None

    return wrapper

@safe_api_call
def get_authors(token):
    return requests.get(
        'http://localhost:8000/authors',
        headers={'Authorization': f'Bearer {token}'}
    )
```

### 3. Pagination Handling

```python
def fetch_all_pages(token, endpoint, per_page=100):
    """
    Fetch all pages from a paginated endpoint.

    Args:
        token: Authentication token
        endpoint: API endpoint URL
        per_page: Items per page

    Yields:
        Individual items from all pages
    """
    page = 1

    while True:
        response = requests.get(
            endpoint,
            headers={'Authorization': f'Bearer {token}'},
            params={'page': page, 'per_page': per_page}
        )
        response.raise_for_status()

        data = response.json()

        for item in data['items']:
            yield item

        if page >= data['meta']['pages']:
            break

        page += 1

# Usage
for author in fetch_all_pages(token, 'http://localhost:8000/authors_paginated'):
    print(f"{author['id']}: {author['name']}")
```

### 4. Rate Limiting

```python
import time
from functools import wraps

def rate_limit_handler(func):
    """Decorator to handle rate limiting with automatic retry."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = func(*args, **kwargs)

                # Check rate limit headers
                remaining = int(response.headers.get('X-RateLimit-Remaining', 0))

                if remaining < 5:
                    # Approaching limit, slow down
                    time.sleep(1)

                return response

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    retry_count += 1
                else:
                    raise

        raise Exception("Max retries exceeded for rate limiting")

    return wrapper

@rate_limit_handler
def get_authors_safe(token):
    return requests.get(
        'http://localhost:8000/authors',
        headers={'Authorization': f'Bearer {token}'}
    )
```

## Performance Considerations

### 1. Use Pagination

For large datasets, always use paginated endpoints:

```python
# Good: Paginated request
response = requests.get(
    'http://localhost:8000/authors_paginated',
    params={'page': 1, 'per_page': 50}
)

# Avoid: Non-paginated request for large datasets
response = requests.get('http://localhost:8000/authors')  # May return thousands
```

### 2. Filter Early

Apply filters to reduce data transfer:

```python
# Good: Filter on server
response = requests.get(
    'http://localhost:8000/authors',
    params={'name': 'Smith'}
)

# Avoid: Fetch all and filter on client
response = requests.get('http://localhost:8000/authors')
authors = [a for a in response.json() if 'Smith' in a['name']]
```

### 3. Reuse Connections

Use session objects for multiple requests:

```python
session = requests.Session()
session.headers.update({'Authorization': f'Bearer {token}'})

# Reuses underlying TCP connection
for i in range(10):
    response = session.get('http://localhost:8000/authors')
```

## Monitoring

### Health Checks

Implement periodic health checks for service monitoring:

```python
import requests
import time

def monitor_service(url, interval=30):
    """Monitor service health."""
    while True:
        try:
            response = requests.get(f'{url}/health', timeout=5)
            health = response.json()

            if health['status'] != 'healthy':
                alert(f"Service unhealthy: {health}")

        except Exception as e:
            alert(f"Health check failed: {e}")

        time.sleep(interval)
```

### Metrics Integration

Scrape Prometheus metrics for monitoring:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Troubleshooting

### Authentication Issues

**Problem:** 401 Unauthorized

**Solutions:**
1. Verify token hasn't expired (check `exp` claim)
2. Ensure token is in Authorization header: `Bearer <token>`
3. Check Keycloak server is accessible
4. Verify username/password are correct

### Rate Limiting

**Problem:** 429 Too Many Requests

**Solutions:**
1. Implement exponential backoff
2. Check `X-RateLimit-Reset` header for retry time
3. Reduce request frequency
4. Cache responses when possible

### Validation Errors

**Problem:** 422 Unprocessable Entity

**Solutions:**
1. Review validation error details in response
2. Check field types match schema
3. Ensure required fields are present
4. Validate data before sending

### Database Errors

**Problem:** 500 Internal Server Error

**Solutions:**
1. Check `/health` endpoint for database status
2. Review server logs for detailed errors
3. Verify database connection configuration
4. Contact system administrator if persistent

## Support

For additional help:
- Interactive documentation: http://localhost:8000/docs
- Health status: http://localhost:8000/health
- Enable debug logging: `LOG_LEVEL=DEBUG`
- Check application logs for detailed error traces
