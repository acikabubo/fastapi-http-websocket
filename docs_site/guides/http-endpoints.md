# Creating HTTP Endpoints

## Overview

This guide shows how to create new HTTP endpoints using FastAPI with proper authentication, authorization, and the Repository + Command pattern.

## Quick Start

### 1. Define the Model

```python
# app/models/book.py
from sqlmodel import Field, SQLModel

class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author_id: int
```

### 2. Create Repository

```python
# app/repositories/book_repository.py
from app.models.book import Book
from app.repositories.base import BaseRepository

class BookRepository(BaseRepository[Book]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Book)
```

### 3. Create Commands

```python
# app/commands/book_commands.py
from pydantic import BaseModel
from app.commands.base import BaseCommand

class CreateBookInput(BaseModel):
    title: str
    author_id: int

class CreateBookCommand(BaseCommand[CreateBookInput, Book]):
    def __init__(self, repository: BookRepository):
        self.repository = repository

    async def execute(self, input_data: CreateBookInput) -> Book:
        book = Book(**input_data.model_dump())
        return await self.repository.create(book)
```

### 4. Add Dependency

```python
# app/dependencies.py
def get_book_repository(session: SessionDep) -> BookRepository:
    return BookRepository(session)

BookRepoDep = Annotated[BookRepository, Depends(get_book_repository)]
```

### 5. Create Router

```python
# app/api/http/book.py
from fastapi import APIRouter, Depends, status
from app.commands.book_commands import CreateBookCommand, CreateBookInput
from app.dependencies import BookRepoDep
from app.dependencies.permissions import require_roles

router = APIRouter(prefix="/books", tags=["books"])

@router.post("", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: CreateBookInput,
    repo: BookRepoDep,
) -> Book:
    """Create a new book."""
    command = CreateBookCommand(repo)
    return await command.execute(data)

@router.get("", response_model=list[Book])
async def get_books(
    repo: BookRepoDep,
    dependencies=[Depends(require_roles("view-books"))]
) -> list[Book]:
    """Get all books (requires 'view-books' role)."""
    return await repo.get_all()
```

## Adding Authentication

### Public Endpoints

No decorator needed - endpoint is public:

```python
@router.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {"status": "healthy"}
```

### Protected Endpoints

Use `require_roles()` dependency:

```python
@router.get(
    "/books",
    dependencies=[Depends(require_roles("view-books"))]
)
async def get_books(repo: BookRepoDep) -> list[Book]:
    """Requires 'view-books' role."""
    return await repo.get_all()
```

### Multiple Roles

Require ALL specified roles:

```python
@router.delete(
    "/books/{book_id}",
    dependencies=[Depends(require_roles("delete-books", "admin"))]
)
async def delete_book(book_id: int, repo: BookRepoDep):
    """Requires BOTH 'delete-books' AND 'admin' roles."""
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await repo.delete(book)
    return {"message": "Book deleted"}
```

## Request Validation

### Path Parameters

```python
@router.get("/books/{book_id}")
async def get_book(book_id: int, repo: BookRepoDep) -> Book:
    """Get book by ID."""
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
```

### Query Parameters

```python
@router.get("/books")
async def get_books(
    repo: BookRepoDep,
    title: str | None = None,
    author_id: int | None = None,
) -> list[Book]:
    """Get books with optional filters."""
    filters = {}
    if title:
        filters["title"] = title
    if author_id:
        filters["author_id"] = author_id
    return await repo.get_all(**filters)
```

### Request Body

```python
class UpdateBookInput(BaseModel):
    title: str
    author_id: int

@router.put("/books/{book_id}")
async def update_book(
    book_id: int,
    data: UpdateBookInput,
    repo: BookRepoDep,
) -> Book:
    """Update book."""
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.title = data.title
    book.author_id = data.author_id
    return await repo.update(book)
```

## Pagination

```python
from app.storage.db import get_paginated_results

@router.get("/books/paginated")
async def get_books_paginated(
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Get paginated books."""
    results, meta = await get_paginated_results(
        Book,
        page=page,
        per_page=per_page
    )
    return {
        "items": [book.model_dump() for book in results],
        "meta": meta.model_dump()
    }
```

## Error Handling

```python
from fastapi import HTTPException

@router.post("/books")
async def create_book(data: CreateBookInput, repo: BookRepoDep) -> Book:
    """Create book with error handling."""
    try:
        command = CreateBookCommand(repo)
        return await command.execute(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Response Models

### Custom Response Models

```python
class BookResponse(BaseModel):
    id: int
    title: str
    author_name: str

@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, repo: BookRepoDep) -> BookResponse:
    """Get book with custom response."""
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookResponse(
        id=book.id,
        title=book.title,
        author_name="..."  # Load from relationship
    )
```

## Complete Example: Book API

Here's a complete example combining all concepts:

```python
# app/api/http/book.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.commands.book_commands import (
    CreateBookCommand,
    UpdateBookCommand,
    DeleteBookCommand,
)
from app.dependencies import BookRepoDep
from app.dependencies.permissions import require_roles
from app.logging import logger
from app.models.book import Book
from app.storage.db import get_paginated_results

router = APIRouter(prefix="/api/books", tags=["books"])


class CreateBookInput(BaseModel):
    """Input for creating a book."""
    title: str
    author_id: int
    isbn: str | None = None


class UpdateBookInput(BaseModel):
    """Input for updating a book."""
    title: str | None = None
    author_id: int | None = None
    isbn: str | None = None


class BookResponse(BaseModel):
    """Book response with additional metadata."""
    id: int
    title: str
    author_id: int
    isbn: str | None
    created_at: str


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("create-book"))],
)
async def create_book(
    data: CreateBookInput,
    repo: BookRepoDep,
) -> Book:
    """
    Create a new book.

    Requires 'create-book' role.

    Example request:
        ```json
        {
            "title": "The Pragmatic Programmer",
            "author_id": 1,
            "isbn": "978-0135957059"
        }
        ```

    Returns:
        Book: Created book with ID and timestamp
    """
    try:
        command = CreateBookCommand(repo)
        book = await command.execute(data)

        logger.info(
            f"Book created: {book.title}",
            extra={"book_id": book.id, "author_id": book.author_id}
        )

        return book

    except ValueError as e:
        logger.warning(f"Invalid book data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create book: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create book"
        )


@router.get(
    "",
    response_model=list[BookResponse],
    dependencies=[Depends(require_roles("view-books"))],
)
async def get_books(
    repo: BookRepoDep,
    author_id: int | None = Query(None, description="Filter by author ID"),
    search: str | None = Query(None, description="Search by title"),
) -> list[Book]:
    """
    Get all books with optional filters.

    Requires 'view-books' role.

    Query Parameters:
        - author_id: Filter books by author
        - search: Search books by title (case-insensitive)

    Example:
        GET /api/books?author_id=1&search=pragmatic
    """
    filters = {}
    if author_id:
        filters["author_id"] = author_id
    if search:
        filters["title_ilike"] = f"%{search}%"

    try:
        books = await repo.get_all(**filters)
        return books
    except Exception as e:
        logger.error(f"Failed to get books: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve books"
        )


@router.get(
    "/paginated",
    dependencies=[Depends(require_roles("view-books"))],
)
async def get_books_paginated(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    author_id: int | None = Query(None, description="Filter by author ID"),
) -> dict:
    """
    Get paginated books.

    Requires 'view-books' role.

    Example:
        GET /api/books/paginated?page=2&per_page=10&author_id=1

    Returns:
        ```json
        {
            "items": [...],
            "meta": {
                "page": 2,
                "per_page": 10,
                "total": 45,
                "pages": 5
            }
        }
        ```
    """
    try:
        filters = {"author_id": author_id} if author_id else {}

        results, meta = await get_paginated_results(
            Book,
            page=page,
            per_page=per_page,
            filters=filters,
        )

        return {
            "items": [book.model_dump() for book in results],
            "meta": meta.model_dump()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get paginated books: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve books"
        )


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_roles("view-books"))],
)
async def get_book(
    book_id: int,
    repo: BookRepoDep,
) -> Book:
    """
    Get book by ID.

    Requires 'view-books' role.

    Example:
        GET /api/books/123

    Raises:
        404: Book not found
    """
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )
    return book


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_roles("update-book"))],
)
async def update_book(
    book_id: int,
    data: UpdateBookInput,
    repo: BookRepoDep,
) -> Book:
    """
    Update book by ID.

    Requires 'update-book' role.

    Example request:
        ```json
        {
            "title": "The Pragmatic Programmer (2nd Edition)",
            "isbn": "978-0135957059"
        }
        ```

    Only provided fields are updated (partial update).

    Raises:
        404: Book not found
        400: Invalid data
    """
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )

    try:
        command = UpdateBookCommand(repo)
        updated_book = await command.execute(book_id, data)

        logger.info(
            f"Book updated: {updated_book.title}",
            extra={"book_id": book_id}
        )

        return updated_book

    except ValueError as e:
        logger.warning(f"Invalid update data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update book: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update book"
        )


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("delete-book", "admin"))],
)
async def delete_book(
    book_id: int,
    repo: BookRepoDep,
) -> None:
    """
    Delete book by ID.

    Requires BOTH 'delete-book' AND 'admin' roles.

    Example:
        DELETE /api/books/123

    Returns:
        204 No Content on success

    Raises:
        404: Book not found
        403: Insufficient permissions
    """
    book = await repo.get_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )

    try:
        command = DeleteBookCommand(repo)
        await command.execute(book_id)

        logger.info(
            f"Book deleted: {book.title}",
            extra={"book_id": book_id}
        )

    except Exception as e:
        logger.error(f"Failed to delete book: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book"
        )
```

## Testing

### Basic Test

```python
from fastapi.testclient import TestClient

def test_create_book(client: TestClient):
    """Test book creation."""
    response = client.post(
        "/api/books",
        json={"title": "Test Book", "author_id": 1},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Book"
```

### Complete Test Suite

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.models.book import Book
from app.repositories.book_repository import BookRepository


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
    repo.get_all.return_value = [
        Book(id=1, title="Book 1", author_id=1),
        Book(id=2, title="Book 2", author_id=1),
    ]
    return repo


@pytest.fixture
def auth_token():
    """Generate test authentication token."""
    # Mock Keycloak token with required roles
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."


class TestBookEndpoints:
    """Test suite for book endpoints."""

    def test_create_book_success(
        self, client: TestClient, auth_token: str, mock_book_repo
    ):
        """Test successful book creation."""
        with patch("app.dependencies.get_book_repository", return_value=mock_book_repo):
            response = client.post(
                "/api/books",
                json={
                    "title": "The Pragmatic Programmer",
                    "author_id": 1,
                    "isbn": "978-0135957059"
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "The Pragmatic Programmer"
            assert data["author_id"] == 1
            assert "id" in data
            assert "created_at" in data

    def test_create_book_missing_required_field(
        self, client: TestClient, auth_token: str
    ):
        """Test book creation with missing required field."""
        response = client.post(
            "/api/books",
            json={"author_id": 1},  # Missing 'title'
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 422  # Validation error
        assert "title" in response.json()["detail"][0]["loc"]

    def test_create_book_unauthorized(self, client: TestClient):
        """Test book creation without authentication."""
        response = client.post(
            "/api/books",
            json={"title": "Test", "author_id": 1}
        )

        assert response.status_code == 401

    def test_get_books_with_filters(
        self, client: TestClient, auth_token: str, mock_book_repo
    ):
        """Test getting books with query filters."""
        with patch("app.dependencies.get_book_repository", return_value=mock_book_repo):
            response = client.get(
                "/api/books?author_id=1&search=pragmatic",
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 200
            books = response.json()
            assert isinstance(books, list)
            assert len(books) > 0

            mock_book_repo.get_all.assert_called_once()

    def test_get_book_by_id_not_found(
        self, client: TestClient, auth_token: str
    ):
        """Test getting non-existent book."""
        mock_repo = AsyncMock(spec=BookRepository)
        mock_repo.get_by_id.return_value = None

        with patch("app.dependencies.get_book_repository", return_value=mock_repo):
            response = client.get(
                "/api/books/999",
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_update_book_partial(
        self, client: TestClient, auth_token: str, mock_book_repo
    ):
        """Test partial book update."""
        with patch("app.dependencies.get_book_repository", return_value=mock_book_repo):
            response = client.put(
                "/api/books/1",
                json={"title": "Updated Title"},
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated Title"

    def test_delete_book_requires_admin(
        self, client: TestClient
    ):
        """Test deletion requires admin role."""
        # Token without admin role
        response = client.delete(
            "/api/books/1",
            headers={"Authorization": "Bearer non_admin_token"}
        )

        assert response.status_code == 403

    def test_pagination_parameters(
        self, client: TestClient, auth_token: str
    ):
        """Test pagination with various parameters."""
        response = client.get(
            "/api/books/paginated?page=2&per_page=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert data["meta"]["page"] == 2
        assert data["meta"]["per_page"] == 10
```

## Related

- [Design Patterns Guide](../architecture/design-patterns.md)
- [WebSocket Handlers](websocket-handlers.md)
- [Authentication Guide](authentication.md)
- [Testing Guide](../development/testing.md)
