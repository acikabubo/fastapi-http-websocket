# Creating WebSocket Handlers

## Overview

This guide shows how to create new WebSocket handlers using the package-based routing system with proper authentication and authorization.

## Quick Start

### 1. Add Package ID

```python
# app/api/ws/constants.py
class PkgID(IntEnum):
    GET_AUTHORS = 1
    GET_PAGINATED_AUTHORS = 2
    CREATE_BOOK = 3  # Add new PkgID
```

### 2. Create Handler

```python
# app/api/ws/handlers/book_handlers.py
from app.api.ws.constants import PkgID, RSPCode
from app.commands.book_commands import CreateBookCommand, CreateBookInput
from app.repositories.book_repository import BookRepository
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.storage.db import async_session

@pkg_router.register(
    PkgID.CREATE_BOOK,
    roles=["create-book"]  # Required role
)
async def create_book_handler(request: RequestModel) -> ResponseModel:
    """Create a new book via WebSocket."""
    try:
        async with async_session() as session:
            async with session.begin():
                repo = BookRepository(session)
                command = CreateBookCommand(repo)
                input_data = CreateBookInput(**request.data)
                book = await command.execute(input_data)

                return ResponseModel.success(
                    pkg_id=request.pkg_id,
                    req_id=request.req_id,
                    data=book.model_dump()
                )
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

### 3. Verify Registration

```bash
make ws-handlers
```

## Handler Registration

### Basic Handler

```python
@pkg_router.register(PkgID.GET_BOOKS)
async def get_books_handler(request: RequestModel) -> ResponseModel:
    """Public handler (no authentication required)."""
    async with async_session() as session:
        repo = BookRepository(session)
        books = await repo.get_all()
        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[b.model_dump() for b in books]
        )
```

### Handler with RBAC

```python
@pkg_router.register(
    PkgID.DELETE_BOOK,
    roles=["delete-book", "admin"]  # Requires BOTH roles
)
async def delete_book_handler(request: RequestModel) -> ResponseModel:
    """Protected handler - requires 'delete-book' AND 'admin' roles."""
    # Handler logic
    pass
```

### Handler with JSON Schema Validation

```python
from pydantic import BaseModel

class CreateBookSchema(BaseModel):
    title: str
    author_id: int

@pkg_router.register(
    PkgID.CREATE_BOOK,
    json_schema=CreateBookSchema,
    roles=["create-book"]
)
async def create_book_handler(request: RequestModel) -> ResponseModel:
    """Handler with automatic schema validation."""
    # request.data is already validated against CreateBookSchema
    pass
```

## Request Handling

### Accessing Request Data

```python
async def handler(request: RequestModel) -> ResponseModel:
    """Access request data."""
    pkg_id = request.pkg_id  # Package ID
    req_id = request.req_id  # Request UUID
    data = request.data     # Request payload (dict)

    # Extract specific fields
    book_id = data.get("id")
    filters = data.get("filters", {})
```

### Using Commands

Reuse business logic from HTTP endpoints:

```python
@pkg_router.register(PkgID.CREATE_BOOK)
async def create_book_handler(request: RequestModel) -> ResponseModel:
    """Handler using command pattern."""
    async with async_session() as session:
        async with session.begin():
            repo = BookRepository(session)
            command = CreateBookCommand(repo)  # Same command as HTTP!
            input_data = CreateBookInput(**request.data)
            book = await command.execute(input_data)

            return ResponseModel.success(
                request.pkg_id,
                request.req_id,
                data=book.model_dump()
            )
```

## Response Handling

### Success Response

```python
return ResponseModel.success(
    pkg_id=request.pkg_id,
    req_id=request.req_id,
    data=[{"id": 1, "title": "Book"}]
)
```

### Error Response

```python
return ResponseModel.err_msg(
    pkg_id=request.pkg_id,
    req_id=request.req_id,
    msg="Book not found",
    status_code=RSPCode.ERROR
)
```

### Paginated Response

```python
from app.storage.db import get_paginated_results

results, meta = await get_paginated_results(
    Book,
    page=request.data.get("page", 1),
    per_page=request.data.get("per_page", 20)
)

return ResponseModel.success(
    request.pkg_id,
    request.req_id,
    data=[r.model_dump() for r in results],
    meta=meta
)
```

## Error Handling

### Database Errors

```python
from sqlalchemy.exc import IntegrityError

try:
    book = await repo.create(book)
except IntegrityError:
    return ResponseModel.err_msg(
        request.pkg_id,
        request.req_id,
        msg="Book already exists",
        status_code=RSPCode.INVALID_DATA
    )
```

### Validation Errors

```python
from pydantic import ValidationError

try:
    input_data = CreateBookInput(**request.data)
except ValidationError as e:
    return ResponseModel.err_msg(
        request.pkg_id,
        request.req_id,
        msg=str(e),
        status_code=RSPCode.INVALID_DATA
    )
```

## Testing

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_book_handler():
    """Test WebSocket handler."""
    # Mock repository
    mock_repo = AsyncMock()
    mock_repo.create.return_value = Book(id=1, title="Test")

    # Create request
    request = RequestModel(
        pkg_id=PkgID.CREATE_BOOK,
        req_id="test-uuid",
        data={"title": "Test", "author_id": 1}
    )

    # Call handler
    response = await create_book_handler(request)

    # Verify response
    assert response.status_code == RSPCode.OK
    assert response.data["title"] == "Test"
```

## Broadcasting

Send messages to all connected clients:

```python
from app.managers.websocket_connection_manager import connection_manager

# In handler
await connection_manager.broadcast({
    "pkg_id": PkgID.BOOK_CREATED,
    "req_id": "00000000-0000-0000-0000-000000000000",
    "data": book.model_dump()
})
```

## Generator Script

Generate new handler from template:

```bash
make new-ws-handlers
```

Follow the prompts to create a new handler file.

## Related

- [WebSocket API](../api-reference/websocket-api.md)
- [Design Patterns Guide](../architecture/design-patterns.md)
- [HTTP Endpoints](http-endpoints.md)
- [Testing Guide](../development/testing.md)
