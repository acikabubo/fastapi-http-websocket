# {{cookiecutter.project_name}}

FastAPI application with HTTP and WebSocket handlers, featuring role-based access control (RBAC), Keycloak authentication, Redis integration, and PostgreSQL database support.

## Quick Start

### Development Setup

```bash
# Start server with hot-reload
make serve

# Or using uvicorn directly
uvicorn {{cookiecutter.module_name}}:application --host 0.0.0.0 --reload
```

### Docker Development

```bash
make build    # Build containers
make start    # Start services (PostgreSQL, Redis, Keycloak)
make stop     # Stop services
make shell    # Enter development shell
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_file.py::test_function_name
```

## Architecture

### Request Flow

**HTTP Requests:**
1. `AuthenticationMiddleware` validates Keycloak JWT token via `AuthBackend`
2. `PermAuthHTTPMiddleware` checks RBAC permissions against `actions.json`
3. Request reaches endpoint handler in `{{cookiecutter.module_name}}/api/http/`

**WebSocket Requests:**
1. Client connects to `/web` WebSocket endpoint
2. `PackageAuthWebSocketEndpoint` authenticates via Keycloak token (query params)
3. Client sends JSON: `{"pkg_id": <int>, "req_id": "<uuid>", "data": {...}}`
4. `Web.on_receive()` validates → `pkg_router.handle_request()`
5. `PackageRouter` validates, checks permissions, dispatches to handler
6. Handler returns `ResponseModel` sent to client

### Key Components

- **PackageRouter** ([routing.py]({{cookiecutter.module_name}}/routing.py)): Central routing system for WebSocket requests with validation and permission checking
- **AuthBackend** ([auth.py]({{cookiecutter.module_name}}/auth.py)): Keycloak JWT authentication for HTTP and WebSocket
- **RBAC Manager** ([managers/rbac_manager.py]({{cookiecutter.module_name}}/managers/rbac_manager.py)): Singleton managing role-based permissions from `actions.json`
- **Database** ([storage/db.py]({{cookiecutter.module_name}}/storage/db.py)): PostgreSQL via SQLModel with pagination support

## WebSocket API

### Request Format

```json
{
    "pkg_id": 1,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "data": {
        "page": 1,
        "per_page": 20
    }
}
```

### Response Format (Success with Pagination)

```json
{
    "pkg_id": 1,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_code": 0,
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "pages": 5
    },
    "data": [...]
}
```

### Response Format (Error)

```json
{
    "pkg_id": 1,
    "req_id": "550e8400-e29b-41d4-a716-446655440000",
    "status_code": 3,
    "data": {
        "msg": "Permission denied"
    }
}
```

Status codes: `0 = OK`, `1 = ERROR`, `2 = INVALID_DATA`, `3 = PERMISSION_DENIED`

## Creating WebSocket Handlers

1. **Add PkgID** to [constants.py]({{cookiecutter.module_name}}/api/ws/constants.py):
```python
class PkgID(IntEnum):
    MY_NEW_HANDLER = 10
```

2. **Generate handler**:
```bash
make new-ws-handlers  # Interactive CLI
```

Or manually create in `{{cookiecutter.module_name}}/api/ws/handlers/`:
```python
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.api.ws.constants import PkgID
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import ResponseModel

@pkg_router.register(PkgID.MY_NEW_HANDLER, json_schema=MySchema)
async def my_handler(request: RequestModel) -> ResponseModel:
    return ResponseModel.ok_msg(
        request.pkg_id,
        request.req_id,
        data={"result": "success"}
    )
```

3. **Update `actions.json`**:
```json
{
  "ws": {
    "10": "admin"
  }
}
```

4. **Verify**: `make ws-handlers`

## Configuration

Environment variables in [settings.py]({{cookiecutter.module_name}}/settings.py):

**Keycloak (Required):**
- `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_BASE_URL`
- `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`

**Redis (Required):**
- `REDIS_IP`, `REDIS_PORT`
- `MAIN_REDIS_DB`, `AUTH_REDIS_DB`

**Database:**
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`

## Documentation

For detailed guides and advanced topics, see:
- **[Advanced Features](docs/guides/ADVANCED_FEATURES.md)** - Protocol Buffers, Performance Profiling
- **[Monitoring & Observability](docs/guides/MONITORING.md)** - Prometheus, Grafana, Loki, Audit Logs
{% if cookiecutter.enable_audit_logging == 'yes' %}- **[User Action Logging](docs/guides/USER_ACTION_LOGGING.md)** - Audit logging setup and usage{% endif %}

## Code Quality

```bash
# Linting
make ruff-check

# Type checking (strict mode)
uvx mypy {{cookiecutter.module_name}}/

# Docstring coverage (≥80% required)
uvx interrogate {{cookiecutter.module_name}}/

# Dead code scanning
make dead-code-scan

# Spell checking
uvx typos
```

## Security Scanning

```bash
make bandit-scan         # SAST scanning
make skjold-scan         # Dependency vulnerabilities
make outdated-pkgs-scan  # Check outdated packages
```

## RBAC Permissions

Permissions are defined in `actions.json`:

```json
{
    "roles": ["admin", "user", "guest"],
    "ws": {
        "1": "admin",
        "2": "user"
    },
    "http": {
        "/api/users": {
            "GET": "user",
            "POST": "admin"
        }
    }
}
```

## Database Pagination

Use `get_paginated_results()` for all list endpoints:

```python
from {{cookiecutter.module_name}}.storage.db import get_paginated_results

results, meta = await get_paginated_results(
    MyModel,
    page=request.data.get("page", 1),
    per_page=request.data.get("per_page", 20),
    filters={"status": "active"}
)

return ResponseModel.ok_msg(
    request.pkg_id,
    request.req_id,
    data=[r.model_dump() for r in results],
    meta=meta
)
```

## Project Structure

```
{{cookiecutter.module_name}}/
├── __init__.py              # Application factory
├── auth.py                  # Keycloak JWT authentication
├── routing.py               # PackageRouter
├── settings.py              # Environment configuration
├── api/
│   ├── http/                # HTTP endpoints (auto-discovered)
│   └── ws/                  # WebSocket handlers and consumers
├── managers/                # Singleton managers (RBAC, Keycloak, WebSocket)
├── middlewares/             # Custom middleware (RBAC for HTTP)
├── models/                  # SQLModel database models
├── schemas/                 # Pydantic request/response models
├── storage/                 # Database and Redis utilities
└── tasks/                   # Background tasks
```

## Pre-commit Hooks

All commits must pass:
- **ruff**: Linting (79 char line length)
- **mypy**: Strict type checking
- **interrogate**: ≥80% docstring coverage
- **typos**: Spell checking
- **bandit**: Security scanning
- **skjold**: Dependency vulnerability checks
