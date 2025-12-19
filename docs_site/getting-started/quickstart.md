# Quick Start

Get your first HTTP and WebSocket endpoints running in 10 minutes.

!!! note "Prerequisites"
    Make sure you've completed the [Installation](installation.md) guide before proceeding.

## Start the Application

```bash
# Start infrastructure services
make start

# Start the application with auto-reload
make serve
```

The application should now be running at http://localhost:8000

## Your First HTTP Endpoint

Let's create a simple HTTP endpoint to manage books.

### 1. Create the Model

Create `app/models/book.py`:

```python
from sqlmodel import Field, SQLModel

class Book(SQLModel, table=True):
    """Book model."""

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    author: str
    isbn: str = Field(unique=True)
    published_year: int
```

### 2. Create a Migration

```bash
make migration msg="add book model"
make migrate
```

### 3. Create the Repository

Create `app/repositories/book_repository.py`:

```python
from app.models.book import Book
from app.repositories.base_repository import BaseRepository

class BookRepository(BaseRepository[Book]):
    """Repository for Book operations."""
    pass
```

### 4. Create HTTP Endpoints

Create `app/api/http/book.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.storage.db import async_session

router = APIRouter(prefix="/books", tags=["books"])

@router.post("/", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book(book: Book):
    """Create a new book."""
    async with async_session() as session:
        repo = BookRepository(session)
        return await repo.create(book)

@router.get("/", response_model=list[Book])
async def get_books():
    """Get all books."""
    async with async_session() as session:
        repo = BookRepository(session)
        return await repo.get_all()

@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: int):
    """Get book by ID."""
    async with async_session() as session:
        repo = BookRepository(session)
        book = await repo.get_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        return book
```

### 5. Test the Endpoint

```bash
# Create a book
curl -X POST http://localhost:8000/books/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "978-0132350884",
    "published_year": 2008
  }'

# Get all books
curl http://localhost:8000/books/

# Get specific book
curl http://localhost:8000/books/1
```

Or visit the interactive API docs: http://localhost:8000/docs

## Your First WebSocket Handler

Let's create a WebSocket handler to get books.

### 1. Add Package ID

Edit `app/api/ws/constants.py`:

```python
class PkgID(IntEnum):
    """WebSocket package IDs."""
    # ... existing handlers ...
    GET_BOOKS = 100
    CREATE_BOOK = 101
```

### 2. Create WebSocket Handler

Create `app/api/ws/handlers/book.py`:

```python
from app.routing import pkg_router
from app.api.ws.constants import PkgID
from app.schemas.models import RequestModel, ResponseModel
from app.repositories.book_repository import BookRepository
from app.storage.db import async_session

@pkg_router.register(PkgID.GET_BOOKS)
async def get_books_handler(request: RequestModel) -> ResponseModel:
    """Get all books via WebSocket."""
    async with async_session() as session:
        repo = BookRepository(session)
        books = await repo.get_all()

        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[book.model_dump() for book in books]
        )

@pkg_router.register(PkgID.CREATE_BOOK)
async def create_book_handler(request: RequestModel) -> ResponseModel:
    """Create a book via WebSocket."""
    async with async_session() as session:
        repo = BookRepository(session)
        book_data = request.data
        book = Book(**book_data)
        created_book = await repo.create(book)

        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=created_book.model_dump()
        )
```

### 3. Test WebSocket Handler

Using `wscat` or any WebSocket client:

```bash
# Install wscat (if needed)
npm install -g wscat

# Connect (replace TOKEN with actual JWT token from Keycloak)
wscat -c "ws://localhost:8000/web?access_token=YOUR_TOKEN"

# Send message
{"pkg_id": 100, "req_id": "test-001", "data": {}}

# Expected response
{
  "pkg_id": 100,
  "req_id": "test-001",
  "status_code": 0,
  "data": [...]
}
```

## Add RBAC Permissions

Add role requirements directly to your handler decorators:

**WebSocket Handler** (`app/api/ws/handlers/book_handler.py`):
```python
@pkg_router.register(
    PkgID.GET_BOOKS,
    json_schema=GetBooksModel,
    roles=["get-books"]  # Define required roles
)
async def get_books_handler(request: RequestModel) -> ResponseModel:
    ...

@pkg_router.register(
    PkgID.CREATE_BOOK,
    json_schema=CreateBookModel,
    roles=["create-book", "admin"]  # Multiple roles = user must have ALL
)
async def create_book_handler(request: RequestModel) -> ResponseModel:
    ...
```

**HTTP Endpoint** (`app/api/http/book.py`):
```python
from app.dependencies.permissions import require_roles

@router.get(
    "/books",
    dependencies=[Depends(require_roles("get-books"))]
)
async def get_books():
    ...

@router.post(
    "/books",
    dependencies=[Depends(require_roles("create-book", "admin"))]
)
async def create_book(book: Book):
    ...
```

Now only users with appropriate roles can access these endpoints!

## Next Steps

Congratulations! You've created your first HTTP and WebSocket endpoints. Next, learn about:

- [Authentication](../guides/authentication.md) - Secure your endpoints
- [Rate Limiting](../guides/rate-limiting.md) - Protect against abuse
- [Database Operations](../guides/database.md) - Advanced database patterns
- [Testing](../development/testing.md) - Write tests for your endpoints

## See Also

- [HTTP API Guide](../guides/http-endpoints.md)
- [WebSocket API Guide](../guides/websocket-handlers.md)
- [Design Patterns](../architecture/design-patterns.md)
