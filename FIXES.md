# Codebase Issues and Fixes

This document outlines the identified issues in the FastAPI HTTP & WebSocket codebase and provides solutions to resolve them.

## 1. Type Issues

### Issue 1: JsonSchemaType Type Mismatch
**File:** `app/routing.py:159`
**Error:** Type "JsonSchemaType" is not assignable to declared type "dict[str, Any]"

**Problem:** The `JsonSchemaType` is defined as a union of `dict[str, Any]` and `type[PydanticModel]`, but the code expects only `dict[str, Any]`.

**Solution:**
```python
# In app/routing.py, update the validation function
def _validate_request(self, request: RequestModel) -> ResponseModel[dict[str, Any]] | None:
    """
    Validate request data against registered schema.

    Returns:
        ResponseModel with error if validation fails, None if valid.
    """
    # Skip validation if no validator is registered for this pkg_id
    if request.pkg_id not in self.validators_registry:
        return None

    json_schema, validator_func = self.validators_registry[request.pkg_id]

    if validator_func is None or json_schema is None:
        return None

    # Convert Pydantic model class to JSON schema if needed
    schema_dict: dict[str, Any]
    if hasattr(json_schema, "model_json_schema"):
        # It's a Pydantic model class (classmethod call)
        schema_dict = json_schema.model_json_schema()  # type: ignore[call-arg]
    else:
        # It's already a dict
        schema_dict = json_schema  # type: ignore[assignment]

    return validator_func(request, schema_dict)  # Pass schema_dict instead of json_schema
```

### Issue 2: ResponseModel Generic Type Mismatch
**Files:** `app/api/ws/handlers/author_handlers.py:97, 164, 224`
**Error:** Type "ResponseModel[dict[str, Any]]" is not assignable to return type "ResponseModel[Author]"

**Problem:** The handlers are returning `ResponseModel` with `dict[str, Any]` data but the function signature expects `ResponseModel[Author]`.

**Solution:**
```python
# In app/api/ws/handlers/author_handlers.py
# Update the return type annotations and response creation

@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=get_authors_schema,
    validator_callback=validator,
    roles=["get-authors"],
)
@handle_ws_errors
async def get_authors_handler(request: RequestModel) -> ResponseModel[dict[str, Any]]:  # Change return type
    """
    WebSocket handler to get authors using Repository + Command pattern.
    """
    async with async_session() as session:
        # ... existing code ...

        # Return with correct type
        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[author.model_dump() for author in authors],
        )

# Similar changes for other handlers
```

## 2. WebSocket Implementation Issues

### Issue 3: WebSocket Extension Method Not Found
**File:** `app/api/ws/consumers/web.py:127`
**Error:** Cannot access attribute "send_response" for class "WebSocket"

**Problem:** The `send_response` method is defined in `PackagedWebSocket` but the type system doesn't recognize it when used in the consumer.

**Solution:**
```python
# In app/api/ws/consumers/web.py
# Import the extended WebSocket class and use proper typing
from app.api.ws.websocket import PackagedWebSocket

# In the Web class, update the on_receive method
async def on_receive(
    self, websocket: PackagedWebSocket, data: dict[str, Any] | bytes  # Proper typing
) -> None:
    # ... existing code ...

    # For protobuf responses, ensure proper handling
    if message_format == "protobuf":
        response_data = serialize_response(response, "protobuf")
        if isinstance(response_data, bytes):
            await websocket.send_bytes(response_data)
        else:
            await websocket.send_text(response_data)  # Fallback for text data
    else:
        await websocket.send_response(response)  # This should now work with proper typing
```

### Issue 4: JSON Encoder Parameter Name Mismatch
**File:** `app/api/ws/websocket.py:25`
**Error:** Parameter 2 name mismatch: base parameter is named "o", override parameter is named "obj"

**Solution:**
```python
# In app/api/ws/websocket.py
class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""

    def default(self, o: Any) -> Any:  # Change parameter name from 'obj' to 'o'
        """
        Convert UUID objects to strings for JSON serialization.
        """
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)
```

## 3. Database Session Issues

### Issue 5: Async Session Context Manager Problems
**File:** `app/api/ws/handlers/author_handlers.py:84, 210`
**Error:** Object of type "Session" cannot be used with "async with" because it does not correctly implement __aenter__

**Problem:** The session is not being used correctly in async context managers.

**Solution:**
```python
# In app/api/ws/handlers/author_handlers.py
# Update the handler functions to properly use async sessions

@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=get_authors_schema,
    validator_callback=validator,
    roles=["get-authors"],
)
@handle_ws_errors
async def get_authors_handler(request: RequestModel) -> ResponseModel[dict[str, Any]]:
    """
    WebSocket handler to get authors using Repository + Command pattern.
    """
    from app.storage.db import get_session  # Import the session getter

    async with get_session() as session:  # Use proper async session
        # Create repository with session
        repo = AuthorRepository(session)

        # Create command with repository
        command = GetAuthorsCommand(repo)

        # Parse input from request data
        input_data = GetAuthorsInput(**(request.data or {}))

        # Execute command (same business logic as HTTP handler!)
        authors = await command.execute(input_data)

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[author.model_dump() for author in authors],
        )
```

## 4. WebSocket Message Decoding Issues

### Issue 6: Message Type Mismatch
**File:** `app/api/ws/websocket.py:162`
**Error:** Parameter 3 type mismatch: base parameter is type "Message", override parameter is type "dict[str, Any]"

**Solution:**
```python
# In app/api/ws/websocket.py
# Update the decode method signature to match the base class
async def decode(
    self, websocket: WebSocket, message: Message  # Use Message type from starlette
) -> dict[str, Any] | bytes:
    """
    Decode incoming WebSocket message.
    """
    if "text" in message:
        # JSON format - parse as JSON
        text = message["text"]
        return json.loads(text)
    elif "bytes" in message:
        # Protobuf format - return raw bytes
        return message["bytes"]
    else:
        # Fallback for other message types
        return message.get("text", message.get("bytes", b""))
```

## 5. Additional Improvements

### WebSocket Consumer Type Safety
**Issue:** Mixed return types causing confusion

**Solution:**
```python
# In app/api/ws/consumers/web.py
# Add proper type hints and imports
from starlette.websockets import WebSocketState
from app.api.ws.websocket import PackagedWebSocket

class Web(PackageAuthWebSocketEndpoint):
    """
    WebSocket endpoint for handling package-related requests.
    """

    websocket_class: Type[PackagedWebSocket] = PackagedWebSocket

    async def on_receive(
        self,
        websocket: PackagedWebSocket,
        data: dict[str, Any] | bytes
    ) -> None:
        # ... implementation with proper typing
```

## Summary of Required Changes

1. **Type Definitions**: Update JsonSchemaType handling to properly convert Pydantic models to dicts
2. **Response Types**: Align ResponseModel generic types with actual return data
3. **WebSocket Extensions**: Properly type and implement extended WebSocket classes
4. **Database Sessions**: Use proper async session management patterns
5. **Message Handling**: Align message type signatures with base class expectations

These fixes will resolve the LSP errors and improve the type safety and reliability of the codebase.
