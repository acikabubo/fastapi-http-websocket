# ADR-001: Package-Based WebSocket Routing

**Date**: 2024-11-25

**Status**: Accepted

**Deciders**: Development Team

**Technical Story**: Core architectural pattern for WebSocket message routing

## Context and Problem Statement

The application needs to support multiple WebSocket message types and operations. Traditional REST-style routing doesn't fit well with WebSocket's bidirectional, connection-oriented nature. We need a routing mechanism that:

- Supports multiple operations over a single WebSocket connection
- Provides clear request/response correlation
- Enables easy handler registration and discovery
- Supports validation and permission checking
- Scales to many message types without excessive complexity

## Decision Drivers

* Need for multiplexed operations over single WebSocket connection
* Requirement for request/response correlation (async operations)
* RBAC permission checking per operation
* JSON schema validation for type safety
* Handler discoverability and maintainability
* Clear separation between transport and business logic
* Support for concurrent requests on same connection

## Considered Options

1. **Package-Based Routing with PkgID enum**
2. REST-style path routing (e.g., /ws/authors, /ws/messages)
3. JSON-RPC 2.0 protocol
4. Protocol Buffers with service definitions
5. GraphQL over WebSocket subscriptions

## Decision Outcome

**Chosen option**: "Package-Based Routing with PkgID enum", because it provides the best balance of simplicity, flexibility, and type safety while integrating well with Python's tooling.

### Positive Consequences

* Single WebSocket connection handles all operations
* Clear handler registration via decorators
* Strong typing via PkgID enum (IDE autocomplete, type checking)
* Request/response correlation via UUID req_id
* Easy to add new handlers without changing transport layer
* RBAC permissions configured per PkgID via decorator `roles` parameter
* JSON schema validation integrated into routing

### Negative Consequences

* Custom protocol (not industry standard like JSON-RPC)
* PkgID enum must be updated for each new handler
* Less discoverable than REST paths (requires documentation)
* Client libraries need to know PkgID mappings

## Pros and Cons of the Options

### Package-Based Routing with PkgID enum

**Message Format**:
```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "",
  "data": {...}
}
```

**Handler Registration**:
```python
@pkg_router.register(PkgID.GET_AUTHORS, json_schema=GetAuthorsSchema)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    ...
```

**Pros**:
* Simple integer-based routing (fast lookup)
* Strong typing via enum (Python 3.10+)
* Single connection for all operations
* Clear request/response correlation
* Easy RBAC configuration (PkgID → role)
* Integrated validation
* No URL parsing overhead

**Cons**:
* Custom protocol (learning curve)
* Enum must be updated centrally
* Less RESTful/discoverable
* No built-in versioning

### REST-style Path Routing

**Example**: Connect to different WebSocket paths like /ws/authors, /ws/messages

**Pros**:
* Familiar REST patterns
* Self-documenting paths
* Industry standard approach
* Clear resource separation

**Cons**:
* Requires multiple WebSocket connections
* More complex connection management
* Higher overhead (multiple TCP connections)
* Harder to correlate requests across connections
* No clear request/response correlation mechanism

### JSON-RPC 2.0

**Message Format**:
```json
{
  "jsonrpc": "2.0",
  "method": "get_authors",
  "params": {...},
  "id": 1
}
```

**Pros**:
* Industry standard protocol
* Well-defined specification
* Request/response correlation via id
* Support for notifications (no response)
* Many existing client libraries

**Cons**:
* String-based method names (no compile-time safety)
* More verbose protocol overhead
* Requires strict JSON-RPC compliance
* Less flexible than custom protocol
* No built-in permission checking

### Protocol Buffers

**Pros**:
* Binary protocol (smaller messages)
* Strong schema validation
* Efficient serialization
* Code generation for clients

**Cons**:
* Binary format (harder to debug)
* Requires .proto files and code generation
* More complex tooling
* Overkill for current scale
* Less flexible for rapid iteration

### GraphQL Subscriptions

**Pros**:
* Industry standard for real-time updates
* Flexible query language
* Schema-driven
* Strong tooling support

**Cons**:
* Complex protocol overhead
* Requires GraphQL server setup
* Overkill for simple request/response
* Harder to implement permissions
* Higher learning curve

## Implementation Details

### PackageRouter Class

Located in `app/routing.py`:

```python
class PackageRouter:
    def __init__(self):
        self._handlers: dict[PkgID, HandlerInfo] = {}

    def register(
        self,
        pkg_id: PkgID,
        json_schema: JsonSchemaType | Type[BaseModel],
        validator_callback: Callable = None,
    ):
        def decorator(handler: Callable):
            self._handlers[pkg_id] = HandlerInfo(
                pkg_id=pkg_id,
                handler=handler,
                json_schema=json_schema,
                validator_callback=validator_callback,
            )
            return handler
        return decorator

    async def handle_request(
        self, request: RequestModel, user: UserModel
    ) -> ResponseModel:
        # 1. Check RBAC permissions
        # 2. Validate against JSON schema
        # 3. Dispatch to handler
        # 4. Return response or error
```

### Request/Response Models

Located in `app/schemas/request.py` and `app/schemas/response.py`:

```python
class RequestModel(BaseModel):
    pkg_id: PkgID
    req_id: UUID
    method: str | None = ""
    data: dict[str, Any] | None = {}

class ResponseModel(BaseModel):
    pkg_id: PkgID
    req_id: UUID
    status_code: RSPCode | None = RSPCode.OK
    meta: MetadataModel | dict | None = None
    data: dict[str, Any] | list | None = None
```

### Handler Example

Located in `app/api/ws/handlers/author_handler.py`:

```python
@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    validator_callback=validator,
)
async def get_authors_handler(request: RequestModel) -> ResponseModel:
    filters = request.data.get("filters", {})
    async with async_session() as session:
        authors = await Author.get_list(session, **filters)

    return ResponseModel(
        pkg_id=request.pkg_id,
        req_id=request.req_id,
        data=[author.model_dump() for author in authors],
    )
```

### PkgID Enum

Located in `app/api/ws/constants.py`:

```python
class PkgID(IntEnum):
    GET_AUTHORS = 1
    GET_PAGINATED_AUTHORS = 2
    THIRD = 3
```

## Links

* [PackageRouter Implementation](../../app/routing.py)
* [PkgID Constants](../../app/api/ws/constants.py)
* [WebSocket Endpoint](../../app/api/ws/websocket.py)
* [WebSocket API Documentation](../WEBSOCKET_API.md)
* [Handler Examples](../../app/api/ws/handlers/)

## Migration Strategy

This is the initial implementation, so no migration needed. For future changes:

1. **Adding new handlers**: Add new PkgID enum value, implement handler with decorator
2. **Deprecating handlers**: Mark PkgID as deprecated in docstring, log warnings, remove after grace period
3. **Versioning**: If breaking changes needed, consider adding version field to protocol or creating new PkgID values

## Rollback Plan

If this approach proves problematic:

1. Implement JSON-RPC 2.0 adapter layer over existing handlers
2. Maintain PkgID routing internally but expose JSON-RPC externally
3. Gradually migrate handlers to pure JSON-RPC if needed

## Validation

**Success Criteria**:
* ✅ Multiple handlers registered and working
* ✅ Request/response correlation via req_id working
* ✅ RBAC permissions enforced per PkgID
* ✅ JSON schema validation working
* ✅ Easy to add new handlers (< 50 lines of code)
* ✅ Type safety via mypy passing

**Metrics to Track**:
* Number of WebSocket handlers
* Average message processing time
* Error rate per PkgID
* Client adoption and feedback

**Review Date**: 2025-06-01

## Notes

The package-based routing provides a good balance for our current needs. If we grow to 50+ handlers or need public API, we should reconsider JSON-RPC 2.0 or GraphQL for better standardization and client library support.

The tight coupling with Python enums (PkgID) is acceptable given we control both client and server implementations. For public APIs, string-based method names (JSON-RPC style) would be more flexible.
