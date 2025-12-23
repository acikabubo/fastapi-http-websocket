# Design Patterns Quick Reference

**Quick lookup guide for implementing Repository + Command + DI patterns**

## 📋 Checklist: Adding a New Feature

- [ ] Create model in `app/models/`
- [ ] Create repository in `app/repositories/`
- [ ] Create commands in `app/commands/`
- [ ] Add repository dependency in `app/dependencies.py`
- [ ] Create HTTP endpoint in `app/api/http/`
- [ ] Create WebSocket handler in `app/api/ws/handlers/`
- [ ] Write tests

---

## 🚀 Quick Start Template

### 1. Model (Data Structure)

```python
# app/models/book.py
from sqlmodel import Field, SQLModel

class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author_id: int
    # Keep simple - no business logic!
```

### 2. Repository (Data Access)

```python
# app/repositories/book_repository.py
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.book import Book
from app.repositories.base import BaseRepository

class BookRepository(BaseRepository[Book]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Book)

    # Add custom queries
    async def get_by_title(self, title: str) -> Book | None:
        from sqlmodel import select
        stmt = select(Book).where(Book.title == title)
        result = await self.session.exec(stmt)
        return result.first()
```

### 3. Commands (Business Logic)

```python
# app/commands/book_commands.py
from pydantic import BaseModel
from app.commands.base import BaseCommand
from app.models.book import Book
from app.repositories.book_repository import BookRepository

# Input/Output models
class GetBooksInput(BaseModel):
    title: str | None = None
    author_id: int | None = None

class CreateBookInput(BaseModel):
    title: str
    author_id: int

# Commands
class GetBooksCommand(BaseCommand[GetBooksInput, list[Book]]):
    def __init__(self, repository: BookRepository):
        self.repository = repository

    async def execute(self, input_data: GetBooksInput) -> list[Book]:
        filters = {}
        if input_data.title:
            filters["title"] = input_data.title
        if input_data.author_id:
            filters["author_id"] = input_data.author_id
        return await self.repository.get_all(**filters)

class CreateBookCommand(BaseCommand[CreateBookInput, Book]):
    def __init__(self, repository: BookRepository):
        self.repository = repository

    async def execute(self, input_data: CreateBookInput) -> Book:
        # Business logic: Check for duplicates
        existing = await self.repository.get_by_title(input_data.title)
        if existing:
            raise ValueError(f"Book '{input_data.title}' already exists")

        book = Book(**input_data.model_dump())
        return await self.repository.create(book)
```

### 4. Dependencies

```python
# app/dependencies.py
def get_book_repository(session: SessionDep) -> BookRepository:
    return BookRepository(session)

BookRepoDep = Annotated[BookRepository, Depends(get_book_repository)]
```

### 5. HTTP Endpoint

```python
# app/api/http/book.py
from fastapi import APIRouter, status
from app.commands.book_commands import CreateBookCommand, CreateBookInput
from app.dependencies import BookRepoDep, RBACDep
from app.models.book import Book

router = APIRouter(prefix="/books", tags=["books"])

@router.post("", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: CreateBookInput,
    repo: BookRepoDep,
    rbac: RBACDep,
) -> Book:
    try:
        command = CreateBookCommand(repo)
        return await command.execute(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 6. WebSocket Handler

```python
# app/api/ws/handlers/book_handlers.py
from app.api.ws.constants import PkgID, RSPCode
from app.commands.book_commands import CreateBookCommand, CreateBookInput
from app.repositories.book_repository import BookRepository
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.storage.db import async_session

@pkg_router.register(PkgID.CREATE_BOOK, roles=["create-book"])
async def create_book_handler(request: RequestModel) -> ResponseModel:
    try:
        async with async_session() as session:
            async with session.begin():
                repo = BookRepository(session)
                command = CreateBookCommand(repo)
                input_data = CreateBookInput(**request.data)
                book = await command.execute(input_data)

                return ResponseModel(
                    pkg_id=request.pkg_id,
                    req_id=request.req_id,
                    data=book.model_dump()
                )
    except ValueError as e:
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg=str(e),
            status_code=RSPCode.INVALID_DATA
        )
```

---

## 🧪 Testing Templates

### Repository Test

```python
# tests/test_book_repository.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.repositories.book_repository import BookRepository

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.exec = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_create_book(mock_session):
    repo = BookRepository(mock_session)
    book = Book(title="Test", author_id=1)

    created = await repo.create(book)

    assert created == book
    mock_session.add.assert_called_once_with(book)
    mock_session.flush.assert_called_once()
```

### Command Test

```python
# tests/test_book_commands.py
import pytest
from unittest.mock import AsyncMock
from app.commands.book_commands import CreateBookCommand, CreateBookInput

@pytest.mark.asyncio
async def test_create_book_command():
    mock_repo = AsyncMock()
    mock_repo.get_by_title.return_value = None  # No duplicate
    mock_repo.create.return_value = Book(id=1, title="New", author_id=1)

    command = CreateBookCommand(mock_repo)
    result = await command.execute(CreateBookInput(title="New", author_id=1))

    assert result.title == "New"
    mock_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_create_duplicate_book():
    mock_repo = AsyncMock()
    mock_repo.get_by_title.return_value = Book(id=1, title="Existing", author_id=1)

    command = CreateBookCommand(mock_repo)

    with pytest.raises(ValueError, match="already exists"):
        await command.execute(CreateBookInput(title="Existing", author_id=1))
```

---

## 📝 Common Patterns

### Pagination in Commands

```python
class GetBooksInput(BaseModel):
    page: int = 1
    per_page: int = 20
    title: str | None = None

class GetBooksCommand(BaseCommand[GetBooksInput, tuple[list[Book], MetadataModel]]):
    async def execute(self, input_data: GetBooksInput):
        from app.storage.db import get_paginated_results

        filters = {}
        if input_data.title:
            filters["title"] = input_data.title

        results, meta = await get_paginated_results(
            Book,
            page=input_data.page,
            per_page=input_data.per_page,
            filters=filters
        )
        return results, meta
```

### Transactions in Commands

```python
class CreateBookWithAuthorsCommand(BaseCommand[CreateBookInput, Book]):
    def __init__(
        self,
        book_repo: BookRepository,
        author_repo: AuthorRepository
    ):
        self.book_repo = book_repo
        self.author_repo = author_repo

    async def execute(self, input_data: CreateBookInput) -> Book:
        # All operations in same transaction (same session)
        # If any fails, all rollback
        author = await self.author_repo.get_by_id(input_data.author_id)
        if not author:
            raise ValueError("Author not found")

        book = Book(**input_data.model_dump())
        return await self.book_repo.create(book)
```

### Update Pattern

```python
class UpdateBookInput(BaseModel):
    id: int
    title: str

class UpdateBookCommand(BaseCommand[UpdateBookInput, Book]):
    async def execute(self, input_data: UpdateBookInput) -> Book:
        # Get existing
        book = await self.repository.get_by_id(input_data.id)
        if not book:
            raise ValueError(f"Book {input_data.id} not found")

        # Check for conflicts
        existing = await self.repository.get_by_title(input_data.title)
        if existing and existing.id != input_data.id:
            raise ValueError(f"Title '{input_data.title}' already exists")

        # Update
        book.title = input_data.title
        return await self.repository.update(book)
```

### Delete Pattern

```python
class DeleteBookCommand(BaseCommand[int, None]):
    async def execute(self, book_id: int) -> None:
        book = await self.repository.get_by_id(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")

        await self.repository.delete(book)
```

---

## 🎯 Decision Tree

### When to Create a New Command?

```
Is it a distinct business operation? → YES → Create new command
                                    → NO  → Add to existing command

Does it have different validation rules? → YES → Create new command
                                         → NO  → Use existing command

Is it used in multiple places? → YES → Definitely create command
                               → NO  → Still create it (future-proof)
```

### When to Add Custom Repository Methods?

```
Is it a common query pattern? → YES → Add to repository
                             → NO  → Use base repository methods

Does it need complex joins? → YES → Add to repository
                           → NO  → Use get_all() with filters

Is it specific to one entity? → YES → Add to specific repository
                              → NO  → Consider a service layer
```

---

## 🔍 Troubleshooting

### Common Issues

**Issue**: Circular import errors
```python
# ❌ Don't import from __init__.py
from app.repositories import AuthorRepository

# ✅ Import directly from module
from app.repositories.author_repository import AuthorRepository
```

**Issue**: Session not flushed
```python
# ❌ Forgot to flush
async def create(self, entity):
    self.session.add(entity)
    return entity  # ID not set!

# ✅ Always flush
async def create(self, entity):
    self.session.add(entity)
    await self.session.flush()  # ID now set
    await self.session.refresh(entity)
    return entity
```

**Issue**: Can't mock dependencies in tests
```python
# ❌ Direct instantiation
repo = AuthorRepository(session)

# ✅ Use dependency override
app.dependency_overrides[get_author_repository] = lambda: MockRepo()
```

---

## 📚 See Also

- [Full Design Patterns Guide](../architecture/design-patterns.md)
- [Testing Guide](testing.md)
- [Example: Author Implementation](../../app/api/http/author.py)
- Issue [#29](https://github.com/acikabubo/fastapi-http-websocket/issues/29)

---

**Last Updated**: 2025-12-05
