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

## Complete Example: Book WebSocket Handler

Here's a complete example combining all concepts:

```python
# app/api/ws/handlers/book_handlers.py
from pydantic import BaseModel, Field
from app.api.ws.constants import PkgID, RSPCode
from app.commands.book_commands import (
    CreateBookCommand,
    UpdateBookCommand,
    DeleteBookCommand,
)
from app.logging import logger
from app.managers.websocket_connection_manager import connection_manager
from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.storage.db import async_session, get_paginated_results
from app.utils.pagination_cache import invalidate_count_cache


class CreateBookSchema(BaseModel):
    """Schema for creating a book via WebSocket."""
    title: str = Field(..., min_length=1, max_length=200)
    author_id: int = Field(..., gt=0)
    isbn: str | None = Field(None, pattern=r"^978-\d{10}$")


class UpdateBookSchema(BaseModel):
    """Schema for updating a book via WebSocket."""
    id: int = Field(..., gt=0)
    title: str | None = Field(None, min_length=1, max_length=200)
    author_id: int | None = Field(None, gt=0)
    isbn: str | None = Field(None, pattern=r"^978-\d{10}$")


@pkg_router.register(
    PkgID.CREATE_BOOK,
    json_schema=CreateBookSchema,
    roles=["create-book"]
)
async def create_book_handler(request: RequestModel) -> ResponseModel:
    """
    Create a new book via WebSocket.

    Requires 'create-book' role.

    Request Data:
        {
            "title": "The Pragmatic Programmer",
            "author_id": 1,
            "isbn": "978-0135957059"
        }

    Response:
        {
            "pkg_id": 3,
            "req_id": "550e8400-e29b-41d4-a716-446655440000",
            "status_code": 0,
            "data": {
                "id": 123,
                "title": "The Pragmatic Programmer",
                "author_id": 1,
                "isbn": "978-0135957059",
                "created_at": "2025-01-29T10:30:00Z"
            }
        }

    Error Codes:
        1 (INVALID_DATA): Invalid book data
        2 (ERROR): Internal server error
    """
    try:
        async with async_session() as session:
            async with session.begin():
                repo = BookRepository(session)
                command = CreateBookCommand(repo)

                # request.data is already validated against CreateBookSchema
                input_data = CreateBookSchema(**request.data)
                book = await command.execute(input_data)

                # Invalidate pagination cache
                await invalidate_count_cache("Book")

                logger.info(
                    f"Book created via WebSocket: {book.title}",
                    extra={"book_id": book.id, "pkg_id": request.pkg_id}
                )

                # Broadcast to all connected clients
                await connection_manager.broadcast({
                    "pkg_id": PkgID.BOOK_CREATED,
                    "req_id": "00000000-0000-0000-0000-000000000000",
                    "data": {
                        "id": book.id,
                        "title": book.title,
                        "action": "created"
                    }
                })

                return ResponseModel.success(
                    pkg_id=request.pkg_id,
                    req_id=request.req_id,
                    data=book.model_dump()
                )

    except ValueError as e:
        logger.warning(f"Invalid book data: {e}")
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
            msg="Failed to create book",
            status_code=RSPCode.ERROR
        )


@pkg_router.register(
    PkgID.GET_BOOKS,
    roles=["view-books"]
)
async def get_books_handler(request: RequestModel) -> ResponseModel:
    """
    Get all books with optional filters and pagination.

    Requires 'view-books' role.

    Request Data:
        {
            "page": 1,
            "per_page": 20,
            "filters": {
                "author_id": 1
            }
        }

    Response:
        {
            "pkg_id": 4,
            "req_id": "...",
            "status_code": 0,
            "data": [
                {"id": 1, "title": "Book 1", ...},
                {"id": 2, "title": "Book 2", ...}
            ],
            "meta": {
                "page": 1,
                "per_page": 20,
                "total": 45,
                "pages": 3
            }
        }
    """
    try:
        async with async_session() as session:
            repo = BookRepository(session)

            # Extract pagination parameters
            page = request.data.get("page", 1)
            per_page = request.data.get("per_page", 20)
            filters = request.data.get("filters", {})

            # Get paginated results
            results, meta = await get_paginated_results(
                Book,
                page=page,
                per_page=per_page,
                filters=filters,
                eager_load=["author"]  # Prevent N+1 queries
            )

            logger.debug(
                f"Retrieved {len(results)} books",
                extra={"page": page, "total": meta.total}
            )

            return ResponseModel.success(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data=[book.model_dump() for book in results],
                meta=meta
            )

    except ValueError as e:
        return ResponseModel.err_msg(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            msg=f"Invalid pagination parameters: {str(e)}",
            status_code=RSPCode.INVALID_DATA
        )
    except Exception as e:
        logger.error(f"Failed to get books: {e}", exc_info=True)
        return ResponseModel.err_msg(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            msg="Failed to retrieve books",
            status_code=RSPCode.ERROR
        )


@pkg_router.register(
    PkgID.UPDATE_BOOK,
    json_schema=UpdateBookSchema,
    roles=["update-book"]
)
async def update_book_handler(request: RequestModel) -> ResponseModel:
    """
    Update book by ID.

    Requires 'update-book' role.

    Request Data:
        {
            "id": 123,
            "title": "Updated Title",
            "isbn": "978-0135957059"
        }

    Only provided fields are updated (partial update).
    """
    try:
        async with async_session() as session:
            async with session.begin():
                repo = BookRepository(session)
                command = UpdateBookCommand(repo)

                book_id = request.data["id"]
                update_data = UpdateBookSchema(**request.data)

                # Check if book exists
                existing_book = await repo.get_by_id(book_id)
                if not existing_book:
                    return ResponseModel.err_msg(
                        pkg_id=request.pkg_id,
                        req_id=request.req_id,
                        msg=f"Book with ID {book_id} not found",
                        status_code=RSPCode.ERROR
                    )

                updated_book = await command.execute(book_id, update_data)

                logger.info(
                    f"Book updated: {updated_book.title}",
                    extra={"book_id": book_id}
                )

                # Broadcast update to all clients
                await connection_manager.broadcast({
                    "pkg_id": PkgID.BOOK_UPDATED,
                    "req_id": "00000000-0000-0000-0000-000000000000",
                    "data": {
                        "id": updated_book.id,
                        "title": updated_book.title,
                        "action": "updated"
                    }
                })

                return ResponseModel.success(
                    pkg_id=request.pkg_id,
                    req_id=request.req_id,
                    data=updated_book.model_dump()
                )

    except ValueError as e:
        logger.warning(f"Invalid update data: {e}")
        return ResponseModel.err_msg(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            msg=str(e),
            status_code=RSPCode.INVALID_DATA
        )
    except Exception as e:
        logger.error(f"Failed to update book: {e}", exc_info=True)
        return ResponseModel.err_msg(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            msg="Failed to update book",
            status_code=RSPCode.ERROR
        )


@pkg_router.register(
    PkgID.DELETE_BOOK,
    roles=["delete-book", "admin"]
)
async def delete_book_handler(request: RequestModel) -> ResponseModel:
    """
    Delete book by ID.

    Requires BOTH 'delete-book' AND 'admin' roles.

    Request Data:
        {
            "id": 123
        }

    Response:
        {
            "pkg_id": 6,
            "req_id": "...",
            "status_code": 0,
            "data": {
                "message": "Book deleted successfully"
            }
        }
    """
    try:
        async with async_session() as session:
            async with session.begin():
                repo = BookRepository(session)
                command = DeleteBookCommand(repo)

                book_id = request.data.get("id")
                if not book_id:
                    return ResponseModel.err_msg(
                        pkg_id=request.pkg_id,
                        req_id=request.req_id,
                        msg="Missing 'id' field",
                        status_code=RSPCode.INVALID_DATA
                    )

                # Check if book exists
                book = await repo.get_by_id(book_id)
                if not book:
                    return ResponseModel.err_msg(
                        pkg_id=request.pkg_id,
                        req_id=request.req_id,
                        msg=f"Book with ID {book_id} not found",
                        status_code=RSPCode.ERROR
                    )

                await command.execute(book_id)

                # Invalidate pagination cache
                await invalidate_count_cache("Book")

                logger.info(
                    f"Book deleted: {book.title}",
                    extra={"book_id": book_id}
                )

                # Broadcast deletion to all clients
                await connection_manager.broadcast({
                    "pkg_id": PkgID.BOOK_DELETED,
                    "req_id": "00000000-0000-0000-0000-000000000000",
                    "data": {
                        "id": book_id,
                        "action": "deleted"
                    }
                })

                return ResponseModel.success(
                    pkg_id=request.pkg_id,
                    req_id=request.req_id,
                    data={"message": "Book deleted successfully"}
                )

    except Exception as e:
        logger.error(f"Failed to delete book: {e}", exc_info=True)
        return ResponseModel.err_msg(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            msg="Failed to delete book",
            status_code=RSPCode.ERROR
        )
```

## Testing

### Basic Test

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

### Complete Test Suite

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.api.ws.constants import PkgID, RSPCode
from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.schemas.request import RequestModel
from tests.conftest import create_request_model_fixture


@pytest.fixture
def mock_book_repo():
    """Mock book repository for testing."""
    repo = AsyncMock(spec=BookRepository)
    repo.get_by_id.return_value = Book(
        id=1,
        title="Test Book",
        author_id=1,
        isbn="978-0135957059"
    )
    repo.create.return_value = Book(
        id=1,
        title="New Book",
        author_id=1
    )
    return repo


class TestBookHandlers:
    """Test suite for book WebSocket handlers."""

    @pytest.mark.asyncio
    async def test_create_book_success(self, mock_book_repo):
        """Test successful book creation."""
        request = create_request_model_fixture(
            pkg_id=PkgID.CREATE_BOOK,
            data={
                "title": "The Pragmatic Programmer",
                "author_id": 1,
                "isbn": "978-0135957059"
            }
        )

        with patch("app.api.ws.handlers.book_handlers.BookRepository",
                   return_value=mock_book_repo):
            response = await create_book_handler(request)

            assert response.status_code == RSPCode.OK
            assert response.pkg_id == PkgID.CREATE_BOOK
            assert response.req_id == request.req_id
            assert "id" in response.data
            mock_book_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_book_invalid_data(self):
        """Test book creation with invalid data."""
        request = create_request_model_fixture(
            pkg_id=PkgID.CREATE_BOOK,
            data={"author_id": 1}  # Missing 'title'
        )

        response = await create_book_handler(request)

        assert response.status_code == RSPCode.INVALID_DATA
        assert "title" in response.data["msg"].lower()

    @pytest.mark.asyncio
    async def test_get_books_with_pagination(self, mock_book_repo):
        """Test getting books with pagination."""
        mock_book_repo.get_all.return_value = [
            Book(id=1, title="Book 1", author_id=1),
            Book(id=2, title="Book 2", author_id=1),
        ]

        request = create_request_model_fixture(
            pkg_id=PkgID.GET_BOOKS,
            data={
                "page": 1,
                "per_page": 10,
                "filters": {"author_id": 1}
            }
        )

        with patch("app.api.ws.handlers.book_handlers.get_paginated_results") as mock_paginate:
            mock_meta = MetadataModel(page=1, per_page=10, total=2, pages=1)
            mock_paginate.return_value = (mock_book_repo.get_all.return_value, mock_meta)

            response = await get_books_handler(request)

            assert response.status_code == RSPCode.OK
            assert len(response.data) == 2
            assert response.meta.page == 1
            assert response.meta.total == 2

    @pytest.mark.asyncio
    async def test_update_book_not_found(self, mock_book_repo):
        """Test updating non-existent book."""
        mock_book_repo.get_by_id.return_value = None

        request = create_request_model_fixture(
            pkg_id=PkgID.UPDATE_BOOK,
            data={
                "id": 999,
                "title": "Updated Title"
            }
        )

        with patch("app.api.ws.handlers.book_handlers.BookRepository",
                   return_value=mock_book_repo):
            response = await update_book_handler(request)

            assert response.status_code == RSPCode.ERROR
            assert "not found" in response.data["msg"].lower()

    @pytest.mark.asyncio
    async def test_delete_book_success(self, mock_book_repo):
        """Test successful book deletion."""
        request = create_request_model_fixture(
            pkg_id=PkgID.DELETE_BOOK,
            data={"id": 1}
        )

        with patch("app.api.ws.handlers.book_handlers.BookRepository",
                   return_value=mock_book_repo):
            response = await delete_book_handler(request)

            assert response.status_code == RSPCode.OK
            assert "deleted successfully" in response.data["message"]
            mock_book_repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_book_missing_id(self):
        """Test deletion without book ID."""
        request = create_request_model_fixture(
            pkg_id=PkgID.DELETE_BOOK,
            data={}  # Missing 'id'
        )

        response = await delete_book_handler(request)

        assert response.status_code == RSPCode.INVALID_DATA
        assert "missing 'id'" in response.data["msg"].lower()

    @pytest.mark.asyncio
    async def test_handler_broadcasts_on_create(self, mock_book_repo):
        """Test that handler broadcasts to all clients on create."""
        request = create_request_model_fixture(
            pkg_id=PkgID.CREATE_BOOK,
            data={"title": "Test", "author_id": 1}
        )

        with patch("app.api.ws.handlers.book_handlers.connection_manager") as mock_manager:
            with patch("app.api.ws.handlers.book_handlers.BookRepository",
                       return_value=mock_book_repo):
                response = await create_book_handler(request)

                assert response.status_code == RSPCode.OK
                mock_manager.broadcast.assert_called_once()

                # Verify broadcast message structure
                broadcast_call = mock_manager.broadcast.call_args[0][0]
                assert broadcast_call["pkg_id"] == PkgID.BOOK_CREATED
                assert broadcast_call["data"]["action"] == "created"
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
