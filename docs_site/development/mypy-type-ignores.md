# MyPy Type Ignore Comments - Reference Document

This document tracks all `# type: ignore` comments added during the mypy strict mode migration. These represent cases where mypy's type checker has limitations or where proper typing would require significant refactoring.

## Summary Statistics

- **Starting errors**: 211 errors across 84+ files
- **Final non-import errors**: 0
- **Total type: ignore comments**: 47

## Categories of Type Ignores

### 1. Third-Party Library Subclassing (misc) - 20 occurrences

These are cases where we subclass from third-party libraries (Pydantic, SQLModel, Starlette) that mypy doesn't fully understand in strict mode.

**Files affected:**
- `app/models/base.py:13` - BaseModel (SQLModel + AsyncAttrs)
- `app/models/author.py:6` - Author model (table=True argument)
- `app/models/user_action.py:11` - UserAction model (SQLModel with table=True)
- `app/schemas/*.py` - All Pydantic BaseModel subclasses (7 files)
- `app/middlewares/*.py` - All BaseHTTPMiddleware subclasses (7 files)
- `app/api/ws/websocket.py` - WebSocket-related classes (2 occurrences)
- `app/auth.py:45` - AuthBackend
- `app/fields/unix_timestamp.py:22` - TypeDecorator

**Reason**: These libraries use metaclasses and dynamic behavior that mypy's type system cannot fully represent.

**Future fix**: These may resolve with updated type stubs from the libraries or when mypy improves metaclass handling.

### 2. SQLAlchemy Column Attributes (attr-defined) - 1 occurrence

**File**: `app/repositories/author_repository.py:75`
```python
stmt = select(Author).where(Author.name.ilike(f"%{name_pattern}%"))  # type: ignore[attr-defined]
```

**Reason**: SQLModel fields appear as `str` in the class definition but become SQLAlchemy Column objects at runtime with methods like `ilike()`.

**Future fix**: This is a known limitation of SQLModel's typing. May improve with future SQLModel versions.

### 3. Untyped Decorators (untyped-decorator) - 2 occurrences

**Files**:
- `app/settings.py:79` - Pydantic's `@field_validator`
- `app/api/http/metrics.py:9` - FastAPI's `@router.get`

**Reason**: Some decorators from third-party libraries don't have complete type annotations.

**Future fix**: Will resolve when FastAPI and Pydantic provide fully typed decorators.

### 4. Union Type Narrowing (union-attr) - 3 occurrences

**Files**:
- `app/tasks/kc_user_session.py:31` - Redis pubsub (returns Any | None)
- `app/api/http/health.py:76` - Redis ping (returns Any | None)

**Reason**: Functions like `get_redis_connection()` return `Redis | None`, but we check for None before calling methods. Mypy doesn't track these runtime checks perfectly.

**Future fix**: Could add explicit None checks or use TypeGuard functions for better type narrowing.

### 5. Assignment Type Mismatches (assignment) - 5 occurrences

**Files**:
- `app/middlewares/rate_limit.py:108` - getattr returns Any
- `app/utils/audit_logger.py:198,201` - Recursive dict sanitization
- `app/routing.py:152` - JsonSchemaType union handling

**Reason**: Complex type unions or dynamic attribute access that mypy cannot fully infer.

**Future fix**: Could use more specific type guards or restructure code to avoid dynamic typing.

### 6. Function Return Values (func-returns-value) - 1 occurrence

**File**: `app/auth.py:152`
```python
token = kc_manager.login(credentials.username, credentials.password)  # type: ignore[func-returns-value]
```

**Reason**: KeycloakManager.login() has incorrect type hints in the keycloak library.

**Future fix**: Report to python-keycloak library or override with more specific type stub.

### 7. Callable Argument Types (arg-type) - 4 occurrences

**Files**:
- `app/api/http/profiling.py:89` - Lambda key function for sort
- `app/api/http/audit_logs.py:97,178` - apply_filters callable signature

**Reason**: Complex callable signatures that mypy cannot fully infer from generic types.

**Future fix**: Could define more specific Protocol types for these callables.

### 8. Union Attribute Access (call-arg, no-untyped-def) - 6 occurrences

**Files**:
- `app/routing.py:149` - Pydantic model_json_schema classmethod
- `app/schemas/user.py:14` - Dynamic **kwargs in __init__
- `app/dependencies/permissions.py:15` - Variable args in require_roles
- `app/api/ws/handlers/__init__.py:5` - Dynamic handler loading
- `app/fields/unix_timestamp.py:87` - SQLAlchemy column defaults

**Reason**: Dynamic behavior with **kwargs, classmethods, or variable arguments.

**Future fix**: Could add overload signatures or more specific type hints.

### 9. Dict Key Type Mismatches (misc) - 2 occurrences

**Files**:
- `app/storage/redis.py:146` - Dict comprehension with int keys expected to be str
- `app/schemas/response.py` - Generic type parameters

**Reason**: Type system expects str keys in dict but runtime uses int.

**Future fix**: Could use explicit type cast or restructure data to use str keys.

## Recommendations for Future Cleanup

### High Priority (Easy to Fix)
1. **Union narrowing** - Add explicit `if x is None: return` checks before using optional values
2. **Dict key types** - Convert int keys to str or use explicit type casts
3. **getattr usage** - Use hasattr checks or default values with specific types

### Medium Priority (Moderate Effort)
1. **Callable signatures** - Define Protocol types for complex callables
2. **Dynamic **kwargs** - Use TypedDict for structured kwargs
3. **KeycloakManager types** - Create local type stub file

### Low Priority (Library-Dependent)
1. **Third-party subclassing** - Wait for library type stub improvements
2. **Untyped decorators** - Will resolve with FastAPI/Pydantic updates
3. **SQLAlchemy column attributes** - SQLModel typing limitation

## Best Practices Going Forward

1. **Avoid adding new type: ignore comments** without documenting the reason
2. **Prefer explicit type narrowing** over type: ignore when possible
3. **Review this file periodically** as libraries improve their type hints
4. **Test that ignored code paths work correctly** since mypy won't catch errors there

## Monitoring

To check for unused type: ignore comments:
```bash
uvx mypy app/ --warn-unused-ignores
```

To find all type: ignore comments:
```bash
grep -rn "# type: ignore" app/ | grep -v ".pyc" | wc -l
```

---
**Last updated**: 2025-12-28
**MyPy version**: 1.19.1
**Python version**: 3.13
