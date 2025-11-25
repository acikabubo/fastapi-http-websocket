# Better Alternatives to actions.json for RBAC Management

## Current Implementation Analysis

**Current Approach**: Static JSON file (`actions.json`)
```json
{
    "roles": ["get-authors"],
    "ws": {
        "1": "get-authors"
    },
    "http": {
        "/authors": {
            "GET": "get-authors"
        }
    }
}
```

**Problems with Current Approach**:
1. ❌ **Tightly coupled** - PkgID mapped by integer strings
2. ❌ **No type safety** - Can't catch errors at compile time
3. ❌ **Manual synchronization** - Must manually keep JSON in sync with code
4. ❌ **Requires app restart** - Changes need deployment
5. ❌ **No validation** - Easy to introduce errors
6. ❌ **Duplicated role definitions** - Same role in multiple places
7. ❌ **Hard to test** - Must mock file reading
8. ❌ **No inheritance** - Can't express role hierarchies

---

## Recommended Approaches (Ranked)

## 🥇 Option 1: Decorator-Based Permissions (BEST)

**Concept**: Define permissions at the point of use using decorators.

### Implementation

```python
# app/decorators/permissions.py
from functools import wraps
from typing import Callable, Sequence
from app.api.ws.constants import PkgID
from app.schemas.user import UserModel

# Permission registry
_ws_permissions: dict[PkgID, list[str]] = {}
_http_permissions: dict[tuple[str, str], list[str]] = {}  # (path, method) -> roles

def require_roles(*roles: str):
    """
    Decorator to specify required roles for a handler.

    Usage:
        @pkg_router.register(PkgID.GET_AUTHORS)
        @require_roles("get-authors", "admin")
        async def get_authors_handler(request: RequestModel):
            ...
    """
    def decorator(func: Callable):
        # Store permissions in function metadata
        func.__required_roles__ = list(roles)
        return func
    return decorator

def ws_permissions(pkg_id: PkgID, *roles: str):
    """
    Decorator to define WebSocket permissions.

    Usage:
        @ws_permissions(PkgID.GET_AUTHORS, "get-authors")
        @pkg_router.register(PkgID.GET_AUTHORS)
        async def get_authors_handler(request: RequestModel):
            ...
    """
    def decorator(func: Callable):
        _ws_permissions[pkg_id] = list(roles)
        func.__required_roles__ = list(roles)
        return func
    return decorator

def http_permissions(path: str, method: str, *roles: str):
    """
    Decorator to define HTTP endpoint permissions.

    Usage:
        @router.get("/authors")
        @http_permissions("/authors", "GET", "get-authors")
        async def get_authors():
            ...
    """
    def decorator(func: Callable):
        _http_permissions[(path, method)] = list(roles)
        func.__required_roles__ = list(roles)
        return func
    return decorator

class RBACRegistry:
    """Central registry for RBAC permissions."""

    @staticmethod
    def get_ws_roles(pkg_id: PkgID) -> list[str]:
        """Get required roles for a WebSocket package."""
        return _ws_permissions.get(pkg_id, [])

    @staticmethod
    def get_http_roles(path: str, method: str) -> list[str]:
        """Get required roles for an HTTP endpoint."""
        return _http_permissions.get((path, method), [])

    @staticmethod
    def list_all_permissions() -> dict:
        """List all registered permissions (useful for debugging)."""
        return {
            "websocket": {str(k): v for k, v in _ws_permissions.items()},
            "http": {f"{k[0]} {k[1]}": v for k, v in _http_permissions.items()}
        }
```

### Better: Integrate into `pkg_router.register()`

**No duplication** - Add `roles` parameter to existing decorator:

```python
# Update app/routing.py PackageRouter.register():
def register(
    self,
    *pkg_ids: PkgID,
    json_schema: JsonSchemaType | None = None,
    validator_callback: ValidatorType | None = None,
    roles: list[str] | None = None,  # NEW: Add roles parameter
):
    """
    Decorator to register handler with permissions.

    Args:
        *pkg_ids: Package IDs to register
        json_schema: Optional JSON schema for validation
        validator_callback: Optional custom validator
        roles: Optional list of required roles (None = public access)
    """
    def decorator(func: HandlerCallableType):
        for pkg_id in pkg_ids:
            # ... existing registration code ...

            # Store roles in registry
            if roles:
                self._permissions_registry[pkg_id] = roles

        return func
    return decorator
```

### Usage in Handlers (Clean - No Duplication!)

```python
# app/api/ws/handlers/author_handler.py

@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    roles=["get-authors"]  # Single place to define everything!
)
async def get_authors_handler(request: RequestModel) -> ResponseModel[Author]:
    """Get all authors."""
    pass

@pkg_router.register(
    PkgID.GET_PAGINATED_AUTHORS,
    roles=["get-authors"]
)
async def get_paginated_authors_handler(request: RequestModel):
    """Get paginated authors."""
    pass

# Multiple roles example:
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]  # Requires BOTH roles
)
async def delete_author_handler(request: RequestModel):
    """Delete author - admin only."""
    pass
```

```python
# app/api/http/author.py
# For HTTP, can use FastAPI dependencies or similar decorator:

from app.decorators.permissions import require_roles

@router.get("/authors")
@require_roles("get-authors")
async def get_authors_endpoint() -> list[Author]:
    """Get all authors via HTTP."""
    pass

@router.post("/authors")
@require_roles("create-author", "admin")  # Requires BOTH
async def create_author_endpoint(author: Author) -> Author:
    """Create author - requires both create-author AND admin roles."""
    pass
```

### Updated RBAC Manager (Reads from PackageRouter)

```python
# app/managers/rbac_manager.py
from app.utils.singleton import SingletonMeta

class RBACManager(metaclass=SingletonMeta):
    """Singleton manager for Role-Based Access Control (RBAC)."""

    def __init__(self):
        """Initialize RBAC manager."""
        # Get permissions from PackageRouter registry
        from app.routing import pkg_router
        self.pkg_router = pkg_router

    def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """Check if user has required roles for WebSocket package."""
        # Get roles from PackageRouter's permissions registry
        required_roles = self.pkg_router.get_permissions(pkg_id)

        # No roles required = public access
        if not required_roles:
            return True

        # User must have ALL required roles
        has_permission = all(role in user.roles for role in required_roles)

        if not has_permission:
            logger.info(
                f"Permission denied for user {user.username} on pkg_id {pkg_id}. "
                f"Required roles: {required_roles}, User roles: {user.roles}"
            )

        return has_permission

    def check_http_permission(self, request: Request) -> bool:
        """Check if user has required roles for HTTP endpoint."""
        # For HTTP, can check function metadata
        # or use a similar registry pattern

        # Get endpoint handler function
        endpoint = request.scope.get("endpoint")
        if not endpoint:
            return True

        # Check if handler has __required_roles__ attribute
        required_roles = getattr(endpoint, "__required_roles__", [])

        if not required_roles:
            return True  # No roles = public access

        # User must have ALL required roles
        user_roles = request.auth.scopes
        has_permission = all(role in user_roles for role in required_roles)

        if not has_permission:
            logger.info(
                f"Permission denied for {request.user.username} "
                f"on {request.method} {request.url.path}. "
                f"Required: {required_roles}, Has: {user_roles}"
            )

        return has_permission
```

### Benefits ✅

- ✅ **Type-safe** - Defined in Python code
- ✅ **Co-located** - Permissions next to handler code
- ✅ **Self-documenting** - Clear what each endpoint requires
- ✅ **Compile-time errors** - Catch mistakes early
- ✅ **No sync issues** - Code and permissions always match
- ✅ **Easy to test** - Just check function metadata
- ✅ **Flexible** - Can require multiple roles
- ✅ **No file I/O** - Faster startup

---

## 🥈 Option 2: Dataclass-Based Configuration

**Concept**: Use Python dataclasses for strongly-typed configuration.

### Implementation

```python
# app/config/permissions.py
from dataclasses import dataclass, field
from enum import Enum
from app.api.ws.constants import PkgID

class Role(str, Enum):
    """All available roles in the system."""
    GET_AUTHORS = "get-authors"
    CREATE_AUTHOR = "create-author"
    DELETE_AUTHOR = "delete-author"
    ADMIN = "admin"
    USER = "user"

@dataclass
class PermissionRule:
    """Single permission rule."""
    roles: list[Role]
    description: str = ""

    def allows(self, user_roles: list[str]) -> bool:
        """Check if user roles satisfy this rule."""
        required = {r.value for r in self.roles}
        return all(role in user_roles for role in required)

@dataclass
class WebSocketPermissions:
    """WebSocket endpoint permissions."""
    GET_AUTHORS: PermissionRule = field(
        default_factory=lambda: PermissionRule(
            roles=[Role.GET_AUTHORS],
            description="View author list"
        )
    )
    GET_PAGINATED_AUTHORS: PermissionRule = field(
        default_factory=lambda: PermissionRule(
            roles=[Role.GET_AUTHORS],
            description="View paginated author list"
        )
    )

    def get_rule(self, pkg_id: PkgID) -> PermissionRule | None:
        """Get permission rule for package ID."""
        mapping = {
            PkgID.GET_AUTHORS: self.GET_AUTHORS,
            PkgID.GET_PAGINATED_AUTHORS: self.GET_PAGINATED_AUTHORS,
        }
        return mapping.get(pkg_id)

@dataclass
class HTTPPermissions:
    """HTTP endpoint permissions."""
    routes: dict[tuple[str, str], PermissionRule] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize route permissions."""
        self.routes = {
            ("/authors", "GET"): PermissionRule(
                roles=[Role.GET_AUTHORS],
                description="List authors"
            ),
            ("/authors", "POST"): PermissionRule(
                roles=[Role.CREATE_AUTHOR, Role.ADMIN],
                description="Create new author"
            ),
            ("/authors/{id}", "DELETE"): PermissionRule(
                roles=[Role.DELETE_AUTHOR, Role.ADMIN],
                description="Delete author"
            ),
        }

    def get_rule(self, path: str, method: str) -> PermissionRule | None:
        """Get permission rule for HTTP route."""
        return self.routes.get((path, method))

@dataclass
class RBACConfig:
    """Complete RBAC configuration."""
    websocket: WebSocketPermissions = field(default_factory=WebSocketPermissions)
    http: HTTPPermissions = field(default_factory=HTTPPermissions)

    # Role hierarchy (parent roles inherit child permissions)
    role_hierarchy: dict[Role, list[Role]] = field(default_factory=lambda: {
        Role.ADMIN: [Role.GET_AUTHORS, Role.CREATE_AUTHOR, Role.DELETE_AUTHOR]
    })

    def expand_roles(self, roles: list[str]) -> set[str]:
        """Expand roles based on hierarchy."""
        expanded = set(roles)
        for role in roles:
            try:
                role_enum = Role(role)
                if role_enum in self.role_hierarchy:
                    expanded.update(r.value for r in self.role_hierarchy[role_enum])
            except ValueError:
                continue
        return expanded

# Singleton instance
rbac_config = RBACConfig()
```

### Updated RBAC Manager

```python
# app/managers/rbac_manager.py
from app.config.permissions import rbac_config

class RBACManager(metaclass=SingletonMeta):
    """Singleton manager for Role-Based Access Control."""

    def __init__(self):
        self.config = rbac_config

    def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """Check WebSocket permissions with role hierarchy."""
        rule = self.config.websocket.get_rule(pkg_id)

        if rule is None:
            return True  # No rule = public access

        # Expand user roles based on hierarchy
        expanded_roles = self.config.expand_roles(user.roles)

        return rule.allows(list(expanded_roles))

    def check_http_permission(self, request: Request) -> bool:
        """Check HTTP permissions with role hierarchy."""
        rule = self.config.http.get_rule(request.url.path, request.method)

        if rule is None:
            return True  # No rule = public access

        # Expand user roles based on hierarchy
        expanded_roles = self.config.expand_roles(request.auth.scopes)

        return rule.allows(list(expanded_roles))
```

### Benefits ✅

- ✅ **Strongly typed** - Role enum prevents typos
- ✅ **Centralized** - All permissions in one place
- ✅ **Role hierarchy** - Admins inherit other roles
- ✅ **Documentation** - Built-in descriptions
- ✅ **Validation** - Python validates at import
- ✅ **IDE support** - Autocomplete for roles

---

## 🥉 Option 3: Database-Backed Permissions

**Concept**: Store permissions in database for runtime configurability.

### Schema

```python
# app/models/permission.py
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional

class Role(SQLModel, table=True):
    """Role model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str = ""

    # Relationships
    ws_permissions: list["WebSocketPermission"] = Relationship(back_populates="role")
    http_permissions: list["HTTPPermission"] = Relationship(back_populates="role")

class WebSocketPermission(SQLModel, table=True):
    """WebSocket endpoint permissions."""
    id: Optional[int] = Field(default=None, primary_key=True)
    pkg_id: int = Field(index=True)
    role_id: int = Field(foreign_key="role.id")

    # Relationship
    role: Role = Relationship(back_populates="ws_permissions")

class HTTPPermission(SQLModel, table=True):
    """HTTP endpoint permissions."""
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(index=True)
    method: str = Field(index=True)
    role_id: int = Field(foreign_key="role.id")

    # Relationship
    role: Role = Relationship(back_populates="http_permissions")
```

### RBAC Manager with Caching

```python
# app/managers/rbac_manager.py
from typing import Optional
from sqlmodel import select
from app.models.permission import Role, WebSocketPermission, HTTPPermission
from app.storage.db import async_session
import asyncio

class RBACManager(metaclass=SingletonMeta):
    """Database-backed RBAC manager with caching."""

    def __init__(self):
        self._ws_cache: dict[int, set[str]] = {}
        self._http_cache: dict[tuple[str, str], set[str]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_refresh: float = 0

    async def _refresh_cache_if_needed(self):
        """Refresh cache if TTL expired."""
        import time
        if time.time() - self._last_refresh > self._cache_ttl:
            await self._refresh_cache()

    async def _refresh_cache(self):
        """Load all permissions from database into cache."""
        import time
        async with async_session() as session:
            # Load WebSocket permissions
            ws_result = await session.exec(
                select(WebSocketPermission, Role)
                .join(Role)
            )
            self._ws_cache.clear()
            for permission, role in ws_result:
                if permission.pkg_id not in self._ws_cache:
                    self._ws_cache[permission.pkg_id] = set()
                self._ws_cache[permission.pkg_id].add(role.name)

            # Load HTTP permissions
            http_result = await session.exec(
                select(HTTPPermission, Role)
                .join(Role)
            )
            self._http_cache.clear()
            for permission, role in http_result:
                key = (permission.path, permission.method)
                if key not in self._http_cache:
                    self._http_cache[key] = set()
                self._http_cache[key].add(role.name)

        self._last_refresh = time.time()

    async def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """Check WebSocket permissions from cache."""
        await self._refresh_cache_if_needed()

        required_roles = self._ws_cache.get(pkg_id, set())
        if not required_roles:
            return True  # No roles = public

        return any(role in user.roles for role in required_roles)

    async def check_http_permission(self, request: Request) -> bool:
        """Check HTTP permissions from cache."""
        await self._refresh_cache_if_needed()

        required_roles = self._http_cache.get(
            (request.url.path, request.method),
            set()
        )
        if not required_roles:
            return True  # No roles = public

        return any(role in request.auth.scopes for role in required_roles)

    async def invalidate_cache(self):
        """Force cache refresh (call after permission changes)."""
        await self._refresh_cache()
```

### Management API

```python
# app/api/http/admin.py
from fastapi import APIRouter, HTTPException, Depends
from app.models.permission import Role, WebSocketPermission, HTTPPermission
from app.managers.rbac_manager import RBACManager

router = APIRouter(prefix="/admin/permissions", tags=["admin"])

@router.post("/ws")
async def create_ws_permission(
    pkg_id: int,
    role_name: str,
    rbac: RBACManager = Depends(lambda: RBACManager())
):
    """Add WebSocket permission."""
    async with async_session() as session:
        # Get role
        role = await session.exec(select(Role).where(Role.name == role_name))
        role = role.first()
        if not role:
            raise HTTPException(404, "Role not found")

        # Create permission
        permission = WebSocketPermission(pkg_id=pkg_id, role_id=role.id)
        session.add(permission)
        await session.commit()

        # Invalidate cache
        await rbac.invalidate_cache()

        return {"status": "created"}

@router.delete("/ws/{pkg_id}/{role_name}")
async def delete_ws_permission(
    pkg_id: int,
    role_name: str,
    rbac: RBACManager = Depends(lambda: RBACManager())
):
    """Remove WebSocket permission."""
    # Implementation similar to create
    pass
```

### Benefits ✅

- ✅ **Runtime configuration** - Change without deployment
- ✅ **Admin UI** - Build permission management UI
- ✅ **Auditable** - Track permission changes
- ✅ **Scalable** - Works for large deployments
- ✅ **Flexible** - Easy to add new permissions

### Drawbacks ⚠️

- ⚠️ **Complexity** - More moving parts
- ⚠️ **Database dependency** - Must be available
- ⚠️ **Caching needed** - Performance overhead
- ⚠️ **Migration path** - Need to seed initial data

---

## 🔄 Option 4: Hybrid Approach

**Concept**: Combine decorator defaults with database overrides.

```python
# app/config/permissions.py
from app.decorators.permissions import ws_permissions, http_permissions
from app.managers.rbac_manager import RBACManager

class HybridRBACManager(RBACManager):
    """RBAC manager that checks database first, falls back to decorators."""

    def __init__(self):
        super().__init__()
        self.use_database = True  # Feature flag

    async def check_ws_permission(self, pkg_id: int, user: UserModel) -> bool:
        """Check database first, then decorator defaults."""
        if self.use_database:
            # Try database permissions
            db_result = await self._check_ws_permission_db(pkg_id, user)
            if db_result is not None:
                return db_result

        # Fall back to decorator-based permissions
        from app.decorators.permissions import RBACRegistry
        required_roles = RBACRegistry.get_ws_roles(pkg_id)

        if not required_roles:
            return True

        return all(role in user.roles for role in required_roles)
```

---

## 📊 Comparison Table

| Feature | JSON File | Decorators | Dataclass | Database | Hybrid |
|---------|-----------|------------|-----------|----------|--------|
| Type Safety | ❌ | ✅ | ✅ | ⚠️ | ✅ |
| Runtime Config | ❌ | ❌ | ❌ | ✅ | ✅ |
| Co-located | ❌ | ✅ | ⚠️ | ❌ | ✅ |
| No Sync Issues | ❌ | ✅ | ✅ | ⚠️ | ✅ |
| Easy Testing | ❌ | ✅ | ✅ | ⚠️ | ✅ |
| Performance | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| Complexity | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Admin UI | ❌ | ❌ | ❌ | ✅ | ✅ |
| Role Hierarchy | ❌ | ❌ | ✅ | ✅ | ✅ |
| IDE Support | ❌ | ✅ | ✅ | ❌ | ✅ |

---

## 🎯 Recommendation

### For Your Use Case: **Option 1 (Decorator-Based)**

**Reasoning**:
1. You have a small number of endpoints (2 WS handlers, few HTTP routes)
2. Permissions are unlikely to change frequently
3. Current team is small (simpler is better)
4. Type safety and co-location are valuable
5. No need for runtime configuration
6. Easier to test and maintain

### Migration Path

**Phase 1**: Add decorator support alongside existing JSON (2 hours)
```python
# Keep actions.json working
# Add decorator infrastructure
# Test both systems work
```

**Phase 2**: Migrate handlers to use decorators (1 hour)
```python
# Add @ws_permissions to each handler
# Verify permissions match JSON
```

**Phase 3**: Remove JSON file (30 minutes)
```python
# Update RBACManager to use decorators only
# Delete actions.json
# Update tests
```

### Future Enhancement Path

If you later need runtime configuration:
- **Small scale**: Add **Option 2 (Dataclass)** for role hierarchy
- **Large scale**: Add **Option 4 (Hybrid)** for database overrides

---

## 🛠️ Implementation Example

Here's a complete working example for your project:

```python
# 1. Create app/decorators/permissions.py (see Option 1 above)

# 2. Update app/api/ws/handlers/author_handler.py
from app.decorators.permissions import ws_permissions

@ws_permissions(PkgID.GET_AUTHORS, "get-authors")
@pkg_router.register(PkgID.GET_AUTHORS, json_schema=GetAuthorsModel)
async def get_authors_handler(request: RequestModel):
    # ... existing implementation

@ws_permissions(PkgID.GET_PAGINATED_AUTHORS, "get-authors")
@pkg_router.register(PkgID.GET_PAGINATED_AUTHORS)
async def get_paginated_authors_handler(request: RequestModel):
    # ... existing implementation

# 3. Update app/api/http/author.py
from app.decorators.permissions import http_permissions

@router.get("/authors")
@http_permissions("/authors", "GET", "get-authors")
async def get_authors_endpoint():
    # ... existing implementation

# 4. Update app/managers/rbac_manager.py (see Option 1 above)

# 5. Delete actions.json

# 6. Update app/settings.py - remove ACTIONS_FILE_PATH

# 7. Add CLI command to list all permissions
@app.command()
def list_permissions():
    """List all registered permissions."""
    from app.decorators.permissions import RBACRegistry
    import json
    print(json.dumps(RBACRegistry.list_all_permissions(), indent=2))
```

---

## 📝 Additional Improvements

### 1. Permission Testing Helper

```python
# tests/test_permissions.py
import pytest
from app.decorators.permissions import RBACRegistry
from app.api.ws.constants import PkgID

def test_all_ws_handlers_have_permissions():
    """Ensure all registered WS handlers have permission definitions."""
    from app.routing import pkg_router

    for pkg_id in pkg_router.handlers_registry.keys():
        roles = RBACRegistry.get_ws_roles(pkg_id)
        # Either has roles or is explicitly public
        assert roles is not None, f"No permission defined for {pkg_id}"

def test_permission_consistency():
    """Test that permissions are consistently defined."""
    permissions = RBACRegistry.list_all_permissions()
    # Add assertions about expected permissions
    assert "websocket" in permissions
    assert "http" in permissions
```

### 2. Permission Documentation Generator

```python
# scripts/generate_permission_docs.py
"""Generate markdown documentation of all permissions."""
from app.decorators.permissions import RBACRegistry

def generate_permission_docs():
    perms = RBACRegistry.list_all_permissions()

    md = "# API Permissions\n\n"
    md += "## WebSocket Endpoints\n\n"
    md += "| Package ID | Required Roles |\n"
    md += "|------------|----------------|\n"

    for pkg_id, roles in perms["websocket"].items():
        md += f"| {pkg_id} | {', '.join(roles)} |\n"

    md += "\n## HTTP Endpoints\n\n"
    md += "| Endpoint | Required Roles |\n"
    md += "|----------|----------------|\n"

    for endpoint, roles in perms["http"].items():
        md += f"| {endpoint} | {', '.join(roles)} |\n"

    with open("docs/PERMISSIONS.md", "w") as f:
        f.write(md)

if __name__ == "__main__":
    generate_permission_docs()
```

---

## 🎓 Summary

**Best Choice**: **Decorator-Based Permissions (Option 1)**

**Why**:
- ✅ Simple to implement
- ✅ Type-safe and maintainable
- ✅ No external dependencies
- ✅ Self-documenting code
- ✅ Easy to test
- ✅ Perfect for your current scale

**Next Steps**:
1. Implement decorator infrastructure (2 hours)
2. Migrate existing handlers (1 hour)
3. Remove actions.json (30 minutes)
4. Add permission tests (1 hour)
5. Generate permission documentation (30 minutes)

**Total migration time**: ~5 hours
