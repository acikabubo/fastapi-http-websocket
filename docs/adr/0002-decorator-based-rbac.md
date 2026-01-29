# 2. Use Decorator-Based RBAC with Co-Located Permissions

Date: 2025-01-29

## Status

Accepted

## Context

The application requires role-based access control (RBAC) for both HTTP and WebSocket endpoints with Keycloak authentication. The system needed to:

1. Enforce permissions consistently across HTTP and WebSocket
2. Make permissions visible in code (not hidden in config files)
3. Support multiple roles per endpoint (AND logic)
4. Integrate with FastAPI's dependency injection
5. Provide clear error messages for unauthorized access

Early implementations used external configuration files (YAML/JSON) to map endpoints to required roles, which led to:
- Permissions separated from handler code (hard to discover)
- Risk of permissions config falling out of sync with code
- Extra indirection when reviewing code
- Difficult code reviews (need to check multiple files)

## Decision

Implement **decorator-based RBAC with co-located permissions**:

1. **HTTP Endpoints**: Use `require_roles()` FastAPI dependency
   ```python
   @router.get("/authors", dependencies=[Depends(require_roles("get-authors"))])
   async def get_authors(): ...
   ```

2. **WebSocket Handlers**: Use `roles` parameter in `@pkg_router.register()` decorator
   ```python
   @pkg_router.register(PkgID.GET_AUTHORS, roles=["get-authors"])
   async def get_authors_handler(request: RequestModel): ...
   ```

3. **Permissions Logic**:
   - User must have **ALL** specified roles (AND logic)
   - Roles extracted from Keycloak JWT token (`realm_access.roles`)
   - Enforced at routing layer (before handler execution)
   - Clear error response: 403 Forbidden with `PermissionDeniedError`

4. **Public Endpoints**: Omit `roles` parameter or `require_roles()` dependency
   ```python
   @router.get("/public")  # No dependencies = public access
   async def public_endpoint(): ...
   ```

**Implementation:**

```python
# HTTP endpoint with single role
@router.get(
    "/authors",
    dependencies=[Depends(require_roles("get-authors"))]
)
async def get_authors(): ...

# HTTP endpoint with multiple roles (ALL required)
@router.post(
    "/authors",
    dependencies=[Depends(require_roles("create-author", "admin"))]
)
async def create_author(): ...

# WebSocket handler with RBAC
@pkg_router.register(
    PkgID.DELETE_AUTHOR,
    roles=["delete-author", "admin"]  # Both roles required
)
async def delete_author_handler(request: RequestModel): ...

# Public endpoint (no authentication)
@router.get("/health")
async def health_check(): ...
```

## Consequences

### Positive Consequences

- **Visibility**: Permissions visible in handler definition (no hunting in config files)
- **Type Safety**: IDE autocomplete for role strings (string literals)
- **Code Reviews**: Reviewers see permissions immediately
- **Consistency**: Same pattern for HTTP and WebSocket
- **Fail-Safe**: Missing role check makes endpoint public (explicit opt-in)
- **Maintainability**: Permissions co-located with code they protect
- **Refactoring**: Moving/renaming handlers keeps permissions attached

### Negative Consequences

- **String Literals**: Role names are strings (no compile-time checking)
- **Duplication**: Same role string in multiple decorators
- **No Central View**: Can't see all permissions in one place
- **Hard to Audit**: Must grep codebase to find all roles

### Neutral Consequences

- **AND Logic Only**: Multiple roles use AND (not OR). OR logic requires separate endpoints.
- **Token Claims**: Roles must be in Keycloak JWT token (not database)

## Alternatives Considered

### Alternative 1: External Configuration File (YAML/JSON)

**Description**: Store role mappings in external config file:
```yaml
permissions:
  GET /authors: ["get-authors"]
  POST /authors: ["create-author", "admin"]
  WS PkgID.GET_AUTHORS: ["get-authors"]
```

**Pros**:
- Central view of all permissions
- Can generate permission documentation automatically
- Non-developers can update permissions
- Easy to audit (single file)

**Cons**:
- Permissions separated from code (hard to discover)
- Risk of config falling out of sync with code
- Extra file to maintain
- Difficult code reviews (need to check config file)
- Refactoring breaks config (endpoint paths change)

**Why not chosen**: Co-location is more important than central view. Developers need to see permissions when reading code.

### Alternative 2: Database-Driven Permissions

**Description**: Store permissions in database table, check at runtime:
```sql
CREATE TABLE permissions (
    endpoint VARCHAR(255),
    required_roles TEXT[]
);
```

**Pros**:
- Can update permissions without code deployment
- UI for permission management
- Supports dynamic role changes

**Cons**:
- Database dependency for all requests (latency)
- Permissions not visible in code
- Cache invalidation complexity
- Over-engineering for current needs
- Difficult to version control permissions

**Why not chosen**: No requirement for runtime permission updates. Code changes are acceptable.

### Alternative 3: Class-Based Permissions

**Description**: Define permissions as class attributes:
```python
class AuthorEndpoints:
    GET_AUTHORS_ROLES = ["get-authors"]
    CREATE_AUTHOR_ROLES = ["create-author", "admin"]

    @router.get("/authors", dependencies=[Depends(require_roles(*GET_AUTHORS_ROLES))])
    async def get_authors(self): ...
```

**Pros**:
- Constants reduce string duplication
- Easy to find all roles in class
- Type hints possible with TypedDict

**Cons**:
- Extra indirection (class attribute instead of inline)
- Still need to grep to find all permissions
- Class-based views not idiomatic FastAPI
- More boilerplate code

**Why not chosen**: Extra indirection outweighs benefits. String duplication is acceptable.

### Alternative 4: Attribute-Based Access Control (ABAC)

**Description**: Check user attributes beyond roles:
```python
@router.get("/authors", dependencies=[Depends(require_attributes(
    roles=["get-authors"],
    org_id="current_user.org_id",
    subscription="premium"
))])
```

**Pros**:
- More granular permissions
- Supports complex business rules
- Context-aware authorization

**Cons**:
- Significantly more complex
- Slower performance (more checks)
- Harder to understand and debug
- Over-engineering for current needs

**Why not chosen**: RBAC is sufficient for current requirements. Can add ABAC later if needed.

## References

- [Keycloak Roles](https://www.keycloak.org/docs/latest/server_admin/#_roles) - Keycloak documentation
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) - Dependency injection
- [app/dependencies/permissions.py](../../app/dependencies/permissions.py) - `require_roles()` implementation
- [app/managers/rbac_manager.py](../../app/managers/rbac_manager.py) - RBAC manager singleton
- [app/routing.py](../../app/routing.py) - WebSocket RBAC enforcement
- [docs/architecture/rbac.md](../../docs_site/architecture/rbac.md) - RBAC documentation

## Notes

**Role Naming Convention**:
- Use lowercase kebab-case: `get-authors`, `create-author`, `delete-author`
- Matches Keycloak role naming conventions
- Prefix with resource name for clarity

**Keycloak Configuration**:
1. Create client in Keycloak
2. Add client roles (e.g., `get-authors`, `create-author`)
3. Assign roles to users
4. Configure role mapping in JWT token (`realm_access.roles`)

**Testing Strategy**:
- Unit tests: Mock user roles in request context
- Integration tests: Use real Keycloak with test users/roles
- RBAC tests: Verify 403 errors for missing roles

**Future Enhancements**:
1. Generate permission documentation from decorators (grep + parse)
2. Add role constants file to reduce string duplication
3. Consider OR logic support (user has ANY of specified roles)
4. Add permission auditing tool (list all endpoints + required roles)

**Migration from Config File**:
If migrating from external config file:
1. Parse config file to extract role mappings
2. Add decorators to each endpoint/handler
3. Verify all permissions match config
4. Remove config file
5. Update documentation
