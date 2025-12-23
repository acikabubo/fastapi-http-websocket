# Exception Handling

## Overview

This document describes the exception handling patterns used in the application.

## HTTP Exceptions

### FastAPI HTTPException

Used for HTTP endpoints:

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Author not found")
```

### Common HTTP Exceptions

**401 Unauthorized:**
```python
raise HTTPException(status_code=401, detail="Not authenticated")
```

**403 Forbidden:**
```python
raise HTTPException(status_code=403, detail="Forbidden")
```

**404 Not Found:**
```python
raise HTTPException(status_code=404, detail="Resource not found")
```

**422 Validation Error:**

Automatically raised by Pydantic for invalid data.

**500 Internal Server Error:**

Unhandled exceptions are caught and returned as 500 errors.

## WebSocket Exceptions

### Error Response Pattern

WebSocket handlers return error responses instead of raising exceptions:

```python
try:
    # Handler logic
    return ResponseModel.success(...)
except ValueError as e:
    return ResponseModel.err_msg(
        pkg_id=request.pkg_id,
        req_id=request.req_id,
        msg=str(e),
        status_code=RSPCode.INVALID_DATA
    )
except Exception as e:
    logger.error(f"Handler error: {e}", exc_info=True)
    return ResponseModel.err_msg(
        pkg_id=request.pkg_id,
        req_id=request.req_id,
        msg="Internal error",
        status_code=RSPCode.ERROR
    )
```

### Connection Exceptions

**WebSocketDisconnect:**

Raised when client disconnects:

```python
from starlette.websockets import WebSocketDisconnect

try:
    data = await websocket.receive_text()
except WebSocketDisconnect:
    # Clean up connection
    await on_disconnect(websocket, 1000)
```

## Custom Exceptions

### Database Exceptions

```python
from sqlalchemy.exc import IntegrityError

try:
    await session.commit()
except IntegrityError as e:
    await session.rollback()
    logger.error(f"Database constraint violation: {e}")
    raise HTTPException(status_code=400, detail="Duplicate entry")
```

### Validation Exceptions

```python
from pydantic import ValidationError

try:
    data = InputModel(**request.data)
except ValidationError as e:
    return ResponseModel.err_msg(
        pkg_id=request.pkg_id,
        req_id=request.req_id,
        msg=str(e),
        status_code=RSPCode.INVALID_DATA
    )
```

## Error Logging

All exceptions are logged with full context:

```python
import logging

logger = logging.getLogger(__name__)

try:
    # Operation
    pass
except Exception as e:
    logger.error(
        f"Operation failed: {e}",
        exc_info=True,
        extra={"user_id": user.sub, "pkg_id": request.pkg_id}
    )
```

## Best Practices

1. **Use specific exceptions** - Catch specific exception types
2. **Log with context** - Include user_id, request_id, etc.
3. **Return user-friendly messages** - Don't expose internal details
4. **Clean up resources** - Use try-finally or context managers
5. **Handle async exceptions** - Use proper async exception handling

## Related

- [HTTP API Error Handling](http-api.md#error-handling)
- [WebSocket API Error Handling](websocket-api.md#error-handling)
