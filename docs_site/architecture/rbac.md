# RBAC System

Role-Based Access Control (RBAC) in this application uses a decorator-based approach where permissions are defined directly in handler code.

## Overview

The RBAC system provides:

- **Decorator-based permissions** - Roles defined directly with handlers
- **Type-safe** - All permissions in Python code, not external files
- **Co-located** - Permissions live next to the code they protect
- **Two protocols** - Works for both HTTP and WebSocket

## Components

### RBACManager

Singleton manager for permission checking:

- `check_ws_permission(pkg_id, user)` - Validates WebSocket permissions
- `require_roles(*roles)` - FastAPI dependency for HTTP endpoints
- Reads from `pkg_router.permissions_registry` for WebSocket
- No external configuration files needed

**Location**: `app/managers/rbac_manager.py`

### Permissions Registry

The `PackageRouter` maintains a registry of required roles for each WebSocket handler:

```python
# Internal registry structure
permissions_registry: dict[PkgID, list[str]] = {
    PkgID.GET_AUTHORS: ["get-authors"],
    PkgID.CREATE_AUTHOR: ["create-author", "admin"],
    PkgID.DELETE_AUTHOR: ["delete-author", "admin"]
}
```

## WebSocket RBAC

### Defining Permissions

Use the `roles` parameter in the `@pkg_router.register()` decorator:

```python
from app.routing import pkg_router
from app.api.ws.constants import PkgID
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel

@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    roles=["get-authors"]  # Required roles
)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    """Get all authors - requires 'get-authors' role."""
    # Handler implementation
    ...
```

### Multiple Roles

User must have **ALL** specified roles:

```python
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]  # Requires BOTH roles
)
async def delete_author_handler(request: RequestModel) -> ResponseModel:
    """Delete author - requires both 'delete-author' AND 'admin' roles."""
    ...
```

### Public Endpoints

Omit the `roles` parameter for public access (no authentication required):

```python
@pkg_router.register(
    PkgID.PUBLIC_DATA,
    json_schema=PublicDataSchema
    # No roles parameter = public access
)
async def public_handler(request: RequestModel) -> ResponseModel:
    """Public endpoint - no authentication required."""
    ...
```

## HTTP RBAC

### Defining Permissions

Use the `require_roles()` FastAPI dependency:

```python
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_roles
from app.schemas.author import Author

router = APIRouter(prefix="/api", tags=["authors"])

@router.get(
    "/authors",
    dependencies=[Depends(require_roles("get-authors"))]
)
async def get_authors() -> list[Author]:
    """Get all authors - requires 'get-authors' role."""
    ...
```

### Multiple Roles

User must have **ALL** specified roles:

```python
@router.delete(
    "/authors/{author_id}",
    dependencies=[Depends(require_roles("delete-author", "admin"))]
)
async def delete_author(author_id: int):
    """Delete author - requires BOTH 'delete-author' AND 'admin' roles."""
    ...
```

### Public Endpoints

Omit the `dependencies` parameter for public access:

```python
@router.get("/health")
async def health_check():
    """Public endpoint - no authentication required."""
    return {"status": "healthy"}
```

## Permission Flow

### HTTP Request Flow

```
1. Client sends request with JWT token
   ↓
2. AuthenticationMiddleware validates token
   ↓
3. require_roles() dependency checks user roles
   ↓
   ├─ User has required roles → Continue to handler
   └─ User missing roles → Return 403 Forbidden
```

### WebSocket Request Flow

```
1. Client connects with JWT token in query params
   ↓
2. PackageAuthWebSocketEndpoint validates token
   ↓
3. Client sends message with pkg_id
   ↓
4. PackageRouter.handle_request() checks permissions
   ↓
5. RBACManager.check_ws_permission(pkg_id, user)
   ↓
   ├─ User has required roles → Dispatch to handler
   └─ User missing roles → Return error response
```

## Role Management

### Defining Roles in Keycloak

Roles are managed in Keycloak:

1. Log into Keycloak Admin Console
2. Select your realm
3. Navigate to **Roles** → **Realm roles**
4. Click **Create role**
5. Define role name (e.g., `get-authors`, `create-author`)

### Assigning Roles to Users

1. Navigate to **Users** in Keycloak Admin
2. Select the user
3. Go to **Role mapping** tab
4. Click **Assign role**
5. Select the roles to assign

### Role Naming Convention

Follow these conventions for consistency:

- Use kebab-case: `get-authors`, `create-author`
- Use descriptive names: `delete-author` not `del-auth`
- Resource-action format: `{action}-{resource}`
- Examples:
  - `get-authors` - View authors
  - `create-author` - Create new authors
  - `update-author` - Modify authors
  - `delete-author` - Remove authors
  - `admin` - Administrative privileges

## Common Patterns

### Read-Only Access

```python
# WebSocket
@pkg_router.register(PkgID.GET_AUTHORS, roles=["viewer"])

# HTTP
@router.get("/authors", dependencies=[Depends(require_roles("viewer"))])
```

### Write Access

```python
# WebSocket
@pkg_router.register(PkgID.CREATE_AUTHOR, roles=["editor"])

# HTTP
@router.post("/authors", dependencies=[Depends(require_roles("editor"))])
```

### Admin-Only Access

```python
# WebSocket
@pkg_router.register(PkgID.DELETE_AUTHOR, roles=["admin"])

# HTTP
@router.delete("/authors/{id}", dependencies=[Depends(require_roles("admin"))])
```

### Combined Permissions

Require both a specific permission AND admin role:

```python
# WebSocket
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]
)

# HTTP
@router.delete(
    "/authors/{id}",
    dependencies=[Depends(require_roles("delete-author", "admin"))]
)
```

## Troubleshooting

### Permission Denied (403)

**Symptom**: Users get 403 Forbidden errors

**Diagnosis**:
```bash
# Check user roles in Keycloak
# Admin Console → Users → <user> → Role Mappings

# Check handler code for required roles
# WebSocket: @pkg_router.register(PkgID.*, roles=["role-name"])
# HTTP: dependencies=[Depends(require_roles("role-name"))]

# Check application logs
docker logs hw-server | grep -i "permission\|rbac"
```

**Solution**:

1. Verify user has the required role(s) in Keycloak
2. Check handler decorator to see what roles are required
3. Ensure JWT token includes the roles (check token claims)

### Finding Required Roles

To find what roles are required for an endpoint:

**WebSocket**:
```bash
# Search handler code
grep -r "@pkg_router.register" app/api/ws/handlers/ | grep "PkgID.YOUR_HANDLER"
```

**HTTP**:
```bash
# Search endpoint code
grep -r "require_roles" app/api/http/
```

### Testing RBAC

```python
# tests/test_rbac.py
import pytest
from app.managers.rbac_manager import RBACManager
from app.schemas.user import UserModel

def test_user_with_correct_role():
    """Test user with correct role can access endpoint."""
    user = UserModel(
        sub="user123",
        username="testuser",
        roles=["get-authors"]
    )
    rbac = RBACManager()

    # Should allow access
    assert rbac.check_ws_permission(PkgID.GET_AUTHORS, user) is True

def test_user_without_role():
    """Test user without role is denied access."""
    user = UserModel(
        sub="user123",
        username="testuser",
        roles=["viewer"]  # Missing 'get-authors'
    )
    rbac = RBACManager()

    # Should deny access
    assert rbac.check_ws_permission(PkgID.GET_AUTHORS, user) is False
```

## Best Practices

### 1. Principle of Least Privilege

Only grant the minimum roles needed:

```python
# Good - specific permission
@pkg_router.register(PkgID.GET_AUTHORS, roles=["get-authors"])

# Avoid - overly broad
@pkg_router.register(PkgID.GET_AUTHORS, roles=["admin"])
```

### 2. Descriptive Role Names

Use clear, descriptive role names:

```python
# Good
roles=["create-author", "update-author"]

# Avoid
roles=["writer", "modifier"]
```

### 3. Co-locate Permissions

Define permissions next to the code they protect:

```python
# Good - roles defined with handler
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]
)
async def delete_author_handler(request: RequestModel):
    ...

# This makes it obvious what roles are required
```

### 4. Document Role Requirements

Add docstrings explaining what roles are required:

```python
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]
)
async def delete_author_handler(request: RequestModel) -> ResponseModel:
    """
    Delete an author.

    Requires BOTH 'delete-author' AND 'admin' roles.
    User must have all specified roles to access this endpoint.
    """
    ...
```

### 5. Test RBAC Logic

Always write tests for permission checks:

```python
# Test both allowed and denied scenarios
def test_authorized_access():
    """Test user with correct roles can access."""
    ...

def test_unauthorized_access():
    """Test user without roles is denied."""
    ...
```

## Security Considerations

### Token Validation

- JWT tokens are validated on every request
- Expired tokens are automatically rejected
- Token signature is verified against Keycloak public key

### Role Extraction

- Roles are extracted from `realm_access.roles` in JWT
- Only roles from the configured Keycloak realm are used
- Invalid or missing role claims result in empty role list

### Permission Checking

- User must have **ALL** required roles (AND logic)
- No roles specified = public access (use cautiously)
- Permission denied returns 403 Forbidden (not 401)

## Related Documentation

- [Authentication Guide](../guides/authentication.md) - Setting up Keycloak and users
- [HTTP API Reference](../api-reference/http-api.md) - HTTP endpoint documentation
- [WebSocket API Reference](../api-reference/websocket-api.md) - WebSocket handler documentation
- [Testing Guide](../development/testing.md) - Testing RBAC logic
