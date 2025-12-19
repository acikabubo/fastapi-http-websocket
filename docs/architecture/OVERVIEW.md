# Architecture Overview

**Last Updated**: 2025-11-25

## System Architecture

This FastAPI application implements a dual-protocol API server supporting both HTTP REST and WebSocket connections with centralized authentication and authorization.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  HTTP Clients              │           WebSocket Clients        │
│  (REST API calls)          │           (Real-time bidirectional)│
└────────────┬───────────────┴──────────────────┬─────────────────┘
             │                                  │
             v                                  v
┌────────────────────────────┐    ┌────────────────────────────────┐
│  HTTP Endpoints            │    │  WebSocket Endpoint (/web)     │
│  - /authors                │    │  - Connection auth             │
│  - /health                 │    │  - Message routing             │
│  - FastAPI routers         │    │  - PackageRouter dispatch      │
└────────────┬───────────────┘    └───────────┬────────────────────┘
             │                                 │
             v                                 v
┌─────────────────────────────────────────────────────────────────┐
│                    Middleware Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  1. AuthenticationMiddleware (Keycloak JWT validation)         │
│  2. require_roles() dependency (RBAC permission checking)       │
└────────────┬────────────────────────────────────────────────────┘
             │
             v
┌─────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  HTTP Handlers             │           WebSocket Handlers       │
│  - app/api/http/           │           - app/api/ws/handlers/   │
│                            │           - Registered with        │
│                            │             @pkg_router.register() │
└────────────┬───────────────┴──────────────────┬─────────────────┘
             │                                  │
             v                                  v
┌─────────────────────────────────────────────────────────────────┐
│                    Managers & Services                          │
├─────────────────────────────────────────────────────────────────┤
│  - RBACManager (permission checking)                            │
│  - KeycloakManager (authentication)                             │
│  - ConnectionManager (WebSocket connections)                    │
│  - PackageRouter (WebSocket request routing)                    │
└────────────┬────────────────────────────────────────────────────┘
             │
             v
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                   │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL Database       │           Redis Cache              │
│  - SQLModel/SQLAlchemy     │           - Session management     │
│  - Async operations        │           - Pub/Sub                │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Request Flow

#### HTTP Request Flow
```
Client Request
    ↓
AuthenticationMiddleware (validates JWT)
    ↓
require_roles() FastAPI dependency (checks RBAC permissions)
    ↓
HTTP Handler (app/api/http/)
    ↓
Database/Redis operations
    ↓
Response to Client
```

#### WebSocket Request Flow
```
Client Connection
    ↓
PackageAuthWebSocketEndpoint (validates JWT from query params)
    ↓
Connection established
    ↓
Client sends JSON message: {"pkg_id": 1, "req_id": "uuid", "data": {...}}
    ↓
PackageRouter.handle_request()
    ↓
1. Validate request format
2. Check RBAC permissions (RBACManager)
3. Validate data against JSON schema
4. Dispatch to registered handler
    ↓
Handler processes request
    ↓
Response: {"pkg_id": 1, "req_id": "uuid", "status_code": 0, "data": {...}}
    ↓
Send to client via WebSocket
```

### 2. Authentication System

**Provider**: Keycloak (OpenID Connect / OAuth 2.0)

**Components**:
- `app/auth.py` - Authentication backend for Starlette
- `app/managers/keycloak_manager.py` - Keycloak client wrapper
- `app/schemas/user.py` - User model with roles

**Token Flow**:
1. User authenticates with Keycloak (username/password or SSO)
2. Keycloak returns JWT access token
3. Client includes token in requests:
   - HTTP: `Authorization: Bearer <token>` header
   - WebSocket: `?Authorization=Bearer <token>` query parameter
4. `AuthBackend.authenticate()` validates and decodes JWT
5. User object with roles attached to request context

**Configuration** (see `app/settings.py`):
- `KEYCLOAK_REALM` - Keycloak realm name
- `KEYCLOAK_CLIENT_ID` - OAuth client ID
- `KEYCLOAK_BASE_URL` - Keycloak server URL
- `EXCLUDED_PATHS` - Paths that bypass authentication (e.g., /health)

### 3. Authorization (RBAC)

**Current Implementation**: Decorator-based roles defined in code

**Components**:
- `app/managers/rbac_manager.py` - Permission checking logic
- `app/dependencies/permissions.py` - FastAPI dependency for HTTP endpoints
- `app/routing.py` - PackageRouter with permissions registry

**Permission Definition**:

**WebSocket Handlers**:
```python
@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    roles=["get-authors"]  # Permissions defined here
)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    ...
```

**HTTP Endpoints**:
```python
from app.dependencies.permissions import require_roles

@router.get(
    "/authors",
    dependencies=[Depends(require_roles("get-authors"))]
)
async def get_authors():
    ...
```

**Permission Checking**:
- WebSocket: `RBACManager.check_ws_permission(pkg_id, user)` - reads from `pkg_router.permissions_registry`
- HTTP: `require_roles(*roles)` FastAPI dependency
- Default policy: If no roles specified = public access

### 4. WebSocket Package Router

**Purpose**: Route WebSocket messages to appropriate handlers based on package ID (PkgID).

**Key Files**:
- `app/routing.py` - PackageRouter class
- `app/api/ws/constants.py` - PkgID enum definitions
- `app/api/ws/handlers/` - Handler implementations

**Handler Registration**:
```python
@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    validator_callback=validator,
    roles=["get-authors"]  # Permission specification
)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    # Handler implementation
    pass
```

**Request/Response Format**:
- Request: `{"pkg_id": 1, "req_id": "uuid", "data": {...}}`
- Response: `{"pkg_id": 1, "req_id": "uuid", "status_code": 0, "data": {...}, "meta": null}`

**Features**:
- Automatic JSON schema validation
- RBAC permission checking
- Request/response correlation via req_id
- Error handling with status codes

### 5. Database Layer

**Technology**: PostgreSQL with async SQLModel/SQLAlchemy

**Configuration** (see `app/storage/db.py`):
- Connection pooling (configurable pool size)
- Async operations (asyncpg driver)
- Automatic retry on connection failure

**Models**: `app/models/`
- Inherit from SQLModel with `table=True`
- Support async operations
- Class methods for common operations

**Pagination Helper**:
```python
results, meta = await get_paginated_results(
    Author,
    page=1,
    per_page=20,
    filters={"status": "active"}
)
```

### 6. Connection Management

**WebSocket Connections**: `app/managers/websocket_connection_manager.py`
- Track active connections
- Broadcast to all connected clients
- Automatic cleanup on disconnect

**Redis Sessions**: `app/storage/redis.py`
- Session storage
- Pub/sub for cross-instance communication
- Connection pooling

### 7. Background Tasks

**Location**: `app/tasks/`

**Current Tasks**:
- `kc_user_session_task` - Monitor Keycloak session expiration via Redis pub/sub

**Management**:
- Started in app startup handler
- Graceful shutdown on app termination
- Tracked in global tasks list

## Design Patterns

### Singleton Pattern
Used for managers that should have single instance:
- `RBACManager`
- `KeycloakManager`
- Implemented via `SingletonMeta` metaclass

### Decorator Pattern
Used for handler registration and enhancement:
- `@pkg_router.register()` - WebSocket handler registration
- `@router.get/post()` - HTTP endpoint registration
- Proposed: `@require_roles()` for inline permission declarations

### Repository Pattern
Models encapsulate data access:
- Class methods for CRUD operations
- Async session management
- Filter support

## Configuration Management

**File**: `app/settings.py`

**Technology**: Pydantic Settings (loads from environment variables)

**Key Settings**:
- Database connection parameters
- Keycloak configuration
- Redis connection
- Pool sizes and timeouts
- Debug flags (development only)

## Security Considerations

### Current Security Measures
- ✅ JWT-based authentication via Keycloak
- ✅ RBAC for endpoint authorization
- ✅ Middleware authentication ordering
- ✅ Excluded paths for public endpoints
- ✅ WebSocket authentication on connection

### Known Issues (see [Codebase Improvements](../improvements/CODEBASE_IMPROVEMENTS.md))
- ⚠️ Middleware order issue (#5)
- ⚠️ Hardcoded credentials in settings (#6)
- ⚠️ No rate limiting
- ⚠️ No request correlation IDs

## Performance Considerations

### Current Optimizations
- Async I/O throughout
- Database connection pooling
- Redis for caching and sessions
- Singleton managers

### Potential Improvements
- Database query optimization (pagination)
- WebSocket broadcast concurrency
- Redis connection pool tuning
- Response caching

## Scalability

### Current Limitations
- Single-instance architecture (WebSocket state)
- No load balancing strategy
- File-based RBAC configuration

### Future Enhancements
- Multi-instance with Redis pub/sub
- Database-backed RBAC for runtime updates
- Distributed session management
- Horizontal scaling with load balancer

## Testing Strategy

**Test Files**: `tests/`

**Current Coverage**: ~57% (4 of 7 API files)

**Test Types**:
- Unit tests (handlers, managers)
- Integration tests (marked with `@pytest.mark.integration`)
- Mock-based authentication tests
- Real Keycloak authentication tests

**See**: [Testing Guide](../guides/TESTING.md)

## Deployment

### Dependencies
- Python 3.13+
- PostgreSQL 12+
- Redis 6+
- Keycloak 20+

### Environment
- Docker Compose for local development
- Environment variables for configuration
- Health check endpoint for monitoring

### Startup Process
1. Load settings from environment
2. Initialize database connection
3. Wait for database availability
4. Register WebSocket handlers
5. Register HTTP routers
6. Start background tasks
7. Start server

## Related Documentation

- [RBAC Alternatives](RBAC_ALTERNATIVES.md) - Proposed RBAC improvements
- [Codebase Improvements](../improvements/CODEBASE_IMPROVEMENTS.md) - Comprehensive improvement report
- [Testing Guide](../guides/TESTING.md) - How to test the application
- [Authentication Guide](../guides/AUTHENTICATION.md) - Working with Keycloak
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines for AI assistant

## Diagrams

### Component Interaction
```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Client     │─────▶│   FastAPI    │─────▶│  Keycloak    │
│              │      │  Application │      │    (Auth)    │
└──────────────┘      └──────┬───────┘      └──────────────┘
                             │
                    ┌────────┼────────┐
                    │        │        │
              ┌─────▼────┐ ┌▼─────┐ ┌▼──────┐
              │PostgreSQL│ │Redis │ │Mgrs   │
              │   (DB)   │ │(Cache│ │(RBAC, │
              │          │ │)     │ │Keycloak│
              └──────────┘ └──────┘ └───────┘
```

## Maintenance

**Code Organization**:
- Follow existing package structure
- Keep handlers thin (business logic in services/managers)
- Use type hints throughout
- Maintain 80%+ docstring coverage

**Adding New Features**:
1. Define models in `app/models/`
2. Create schemas in `app/schemas/`
3. Implement handlers in `app/api/http/` or `app/api/ws/handlers/`
4. Specify required roles in handler decorators (WebSocket: `roles=[]`, HTTP: `require_roles()`)
5. Write tests in `tests/`
6. Update documentation

**See**: [CLAUDE.md](../../CLAUDE.md) for detailed development guidelines
