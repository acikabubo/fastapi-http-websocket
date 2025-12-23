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

## Testing

```python
from fastapi.testclient import TestClient

def test_create_book(client: TestClient):
    """Test book creation."""
    response = client.post(
        "/books",
        json={"title": "Test Book", "author_id": 1},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Book"
```

## Related

- [Design Patterns Guide](../architecture/design-patterns.md)
- [WebSocket Handlers](websocket-handlers.md)
- [Authentication Guide](authentication.md)
- [Testing Guide](../development/testing.md)
