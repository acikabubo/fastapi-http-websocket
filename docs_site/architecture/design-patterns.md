# Design Patterns Guide

**Status**: ✅ Implemented
**Date**: 2025-12-05
**Issue**: [#29](https://github.com/acikabubo/fastapi-http-websocket/issues/29)

## Table of Contents

- [Overview](#overview)
- [Why These Patterns?](#why-these-patterns)
- [Pattern 1: Dependency Injection](#pattern-1-dependency-injection)
- [Pattern 2: Repository Pattern](#pattern-2-repository-pattern)
- [Pattern 3: Command Pattern](#pattern-3-command-pattern)
- [Complete Example: Author Feature](#complete-example-author-feature)
- [Testing Strategies](#testing-strategies)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)

---

## Overview

This guide explains the modern design patterns implemented in this FastAPI application. These patterns improve code quality through:

- **Testability** - Easy to mock and test in isolation
- **Reusability** - Share logic across HTTP and WebSocket handlers
- **Maintainability** - Clear separation of concerns
- **Type Safety** - Full type hints and IDE support
- **Flexibility** - Easy to swap implementations

### Pattern Summary

| Pattern | Purpose | Location |
|---------|---------|----------|
| **Dependency Injection** | Manage dependencies without singletons | `app/dependencies.py` |
| **Repository** | Abstract data access | `app/repositories/` |
| **Command** | Encapsulate business logic | `app/commands/` |

---

## Why These Patterns?

### Problems with Old Approach

#### ❌ Singleton Pattern (Metaclass)
```python
# OLD: app/managers/rbac_manager.py
from app.utils.singleton import SingletonMeta

class RBACManager(metaclass=SingletonMeta):
    def __init__(self):
        self.config = load_config()

# Usage - hidden dependency!
rbac = RBACManager()  # Always returns same instance
```

**Problems:**
- Hard to test (global mutable state)
- Can't override/mock easily
- Hidden dependencies
- Not compatible with FastAPI's DI

#### ❌ Active Record Pattern
```python
# OLD: app/models/author.py
class Author(SQLModel, table=True):
    id: int | None = None
    name: str

    @classmethod
    async def create(cls, session: AsyncSession, author: "Author"):
        # Data access mixed with model definition
        session.add(author)
        await session.flush()
        return author
```

**Problems:**
- Violates Single Responsibility Principle
- Can't test business logic without database
- Hard to swap data sources
- Business logic tied to data structure

### ✅ Current Pattern: Repository + Command + Dependency Injection

```python
# Clean separation of concerns
Repository (data access) → Command (business logic) → Handler (protocol)
```

**Benefits:**
- Reusable business logic across HTTP and WebSocket
- Easy to test without database
- Clear separation of concerns

---

## Pattern 1: Dependency Injection

### Overview

Replace singleton pattern with FastAPI's dependency injection system.

### Implementation

**File**: `app/dependencies.py`

```python
from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from app.managers.rbac_manager import RBACManager

# Use @lru_cache for singleton behavior
@lru_cache
def get_rbac_manager() -> RBACManager:
    """Get cached RBAC manager instance."""
    return RBACManager()

# Type-safe dependency annotation
RBACDep = Annotated[RBACManager, Depends(get_rbac_manager)]
```

### Usage

**HTTP Handler:**
```python
from app.dependencies import RBACDep, AuthorRepoDep

@router.get("/authors")
async def get_authors(
    rbac: RBACDep,  # Injected automatically!
    repo: AuthorRepoDep,
) -> list[Author]:
    # Dependencies are explicitly declared
    return await repo.get_all()
```

**WebSocket Handler:**
```python
# WebSocket can't use Depends(), so instantiate manually
async def ws_handler(request: RequestModel):
    async with async_session() as session:
        repo = AuthorRepository(session)
        # Use repository...
```

### Testing

```python
def test_endpoint():
    # Override dependency for testing
    app.dependency_overrides[get_rbac_manager] = lambda: MockRBAC()

    # Test with mocked dependency
    response = client.get("/authors")
```

### Benefits

✅ **Testable** - Can override with mocks
✅ **Explicit** - Dependencies clearly declared
✅ **Type-safe** - IDE autocomplete and type checking
✅ **Flexible** - Easy to swap implementations

---

## Pattern 2: Repository Pattern

### Overview

Separate data access logic from business logic by encapsulating all database operations in repository classes.

### Implementation

**Base Repository**: `app/repositories/base.py`

```python
from typing import Generic, Type, TypeVar
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Generic repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        return await self.session.get(self.model, id)

    async def get_all(self, **filters) -> list[T]:
        stmt = select(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def exists(self, **filters) -> bool:
        stmt = select(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.exec(stmt)
        return result.first() is not None
```

**Specific Repository**: `app/repositories/author_repository.py`

```python
from app.models.author import Author
from app.repositories.base import BaseRepository

class AuthorRepository(BaseRepository[Author]):
    """Repository for Author entity with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Author)

    async def get_by_name(self, name: str) -> Author | None:
        """Get author by exact name match."""
        stmt = select(Author).where(Author.name == name)
        result = await self.session.exec(stmt)
        return result.first()

    async def search_by_name(self, name_pattern: str) -> list[Author]:
        """Search authors by name pattern (case-insensitive)."""
        stmt = select(Author).where(Author.name.ilike(f"%{name_pattern}%"))
        result = await self.session.exec(stmt)
        return list(result.all())
```

### Usage

```python
# In handler
async with async_session() as session:
    repo = AuthorRepository(session)

    # Use repository methods
    author = await repo.get_by_id(1)
    all_authors = await repo.get_all()
    johns = await repo.search_by_name("John")
    exists = await repo.exists(name="John Doe")
```

### Testing

```python
@pytest.mark.asyncio
async def test_repository():
    # Mock session
    mock_session = AsyncMock()
    mock_session.get.return_value = Author(id=1, name="Test")

    repo = AuthorRepository(mock_session)
    author = await repo.get_by_id(1)

    assert author.name == "Test"
    mock_session.get.assert_called_once_with(Author, 1)
```

### Benefits

✅ **Abstraction** - Hide database details
✅ **Reusable** - Use same repository in multiple handlers
✅ **Testable** - Mock session, not database
✅ **Maintainable** - Change queries in one place

---

## Pattern 3: Command Pattern

### Overview

Encapsulate business operations as command objects that can be reused across different handler types (HTTP, WebSocket).

### Implementation

**Base Command**: `app/commands/base.py`

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")

class BaseCommand(ABC, Generic[TInput, TOutput]):
    """Base command for business operations."""

    @abstractmethod
    async def execute(self, input_data: TInput) -> TOutput:
        """Execute the command with input data."""
        pass
```

**Specific Command**: `app/commands/author_commands.py`

```python
from pydantic import BaseModel
from app.commands.base import BaseCommand
from app.repositories.author_repository import AuthorRepository

# Input/Output models
class GetAuthorsInput(BaseModel):
    id: int | None = None
    name: str | None = None
    search_term: str | None = None

# Command implementation
class GetAuthorsCommand(BaseCommand[GetAuthorsInput, list[Author]]):
    """Command to get authors with optional filtering."""

    def __init__(self, repository: AuthorRepository):
        self.repository = repository

    async def execute(self, input_data: GetAuthorsInput) -> list[Author]:
        # Business logic here
        if input_data.search_term:
            return await self.repository.search_by_name(input_data.search_term)

        filters = {}
        if input_data.id is not None:
            filters["id"] = input_data.id
        if input_data.name is not None:
            filters["name"] = input_data.name

        return await self.repository.get_all(**filters)


class CreateAuthorCommand(BaseCommand[CreateAuthorInput, Author]):
    """Command to create a new author."""

    def __init__(self, repository: AuthorRepository):
        self.repository = repository

    async def execute(self, input_data: CreateAuthorInput) -> Author:
        # Business logic: Check for duplicates
        existing = await self.repository.get_by_name(input_data.name)
        if existing:
            raise ValueError(f"Author '{input_data.name}' already exists")

        author = Author(name=input_data.name)
        return await self.repository.create(author)
```

### Usage

**HTTP Handler:**
```python
@router.get("/authors")
async def get_authors(
    repo: AuthorRepoDep,
    search: str | None = None,
) -> list[Author]:
    command = GetAuthorsCommand(repo)
    input_data = GetAuthorsInput(search_term=search)
    return await command.execute(input_data)
```

**WebSocket Handler:**
```python
@pkg_router.register(PkgID.GET_AUTHORS)
async def get_authors_ws(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        repo = AuthorRepository(session)
        command = GetAuthorsCommand(repo)  # Same command!
        input_data = GetAuthorsInput(**request.data)
        authors = await command.execute(input_data)

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[a.model_dump() for a in authors]
        )
```

**Key Point**: Same business logic (`GetAuthorsCommand`) used in both protocols! 🎯

### Testing

```python
@pytest.mark.asyncio
async def test_command():
    # Mock repository
    mock_repo = AsyncMock()
    mock_repo.get_by_name.return_value = None
    mock_repo.create.return_value = Author(id=1, name="New")

    # Test command with mock
    command = CreateAuthorCommand(mock_repo)
    input_data = CreateAuthorInput(name="New")
    result = await command.execute(input_data)

    assert result.name == "New"
    mock_repo.get_by_name.assert_called_once_with("New")
    mock_repo.create.assert_called_once()
```

### Benefits

✅ **Reusable** - Same logic in HTTP and WebSocket
✅ **Testable** - Mock repository, not database
✅ **Maintainable** - Change logic in one place
✅ **Composable** - Commands can call other commands

---

## Complete Example: Author Feature

### Architecture Flow

```
HTTP Request → Router → Command → Repository → Database
                  ↓         ↓           ↓
            Dependencies  Business    Data
            Injected      Logic       Access
```

### Step-by-Step Implementation

#### 1. Define Models

```python
# app/models/author.py
class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    # No business logic methods!
```

#### 2. Create Repository

```python
# app/repositories/author_repository.py
class AuthorRepository(BaseRepository[Author]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Author)

    async def get_by_name(self, name: str) -> Author | None:
        # Custom query
        ...
```

#### 3. Create Commands

```python
# app/commands/author_commands.py
class CreateAuthorInput(BaseModel):
    name: str

class CreateAuthorCommand(BaseCommand[CreateAuthorInput, Author]):
    def __init__(self, repository: AuthorRepository):
        self.repository = repository

    async def execute(self, input_data: CreateAuthorInput) -> Author:
        # Business logic with validation
        ...
```

#### 4. Setup Dependencies

```python
# app/dependencies.py
def get_author_repository(session: SessionDep) -> AuthorRepository:
    return AuthorRepository(session)

AuthorRepoDep = Annotated[AuthorRepository, Depends(get_author_repository)]
```

#### 5. Create HTTP Endpoint

```python
# app/api/http/author.py
@router.post("/authors", status_code=201)
async def create_author(
    data: CreateAuthorInput,
    repo: AuthorRepoDep,
) -> Author:
    command = CreateAuthorCommand(repo)
    return await command.execute(data)
```

#### 6. Create WebSocket Handler

```python
# app/api/ws/handlers/author_handlers.py
@pkg_router.register(PkgID.CREATE_AUTHOR)
async def create_author_ws(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        repo = AuthorRepository(session)
        command = CreateAuthorCommand(repo)  # Same command!
        input_data = CreateAuthorInput(**request.data)
        author = await command.execute(input_data)

        return ResponseModel(..., data=author.model_dump())
```

---

## Testing Strategies

### 1. Repository Tests

```python
@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.exec = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_create(mock_session):
    repo = AuthorRepository(mock_session)
    author = Author(name="Test")

    created = await repo.create(author)

    mock_session.add.assert_called_once_with(author)
    mock_session.flush.assert_called_once()
```

### 2. Command Tests

```python
@pytest.mark.asyncio
async def test_create_command():
    mock_repo = AsyncMock()
    mock_repo.get_by_name.return_value = None
    mock_repo.create.return_value = Author(id=1, name="New")

    command = CreateAuthorCommand(mock_repo)
    result = await command.execute(CreateAuthorInput(name="New"))

    assert result.id == 1
    mock_repo.create.assert_called_once()
```

### 3. Handler Tests

```python
def test_http_endpoint(client):
    # Override dependency
    app.dependency_overrides[get_author_repository] = lambda: MockRepo()

    response = client.post("/authors", json={"name": "Test"})
    assert response.status_code == 201
```

---

## Migration Guide

### For New Features

Use the new patterns from the start:

1. Create Repository extending `BaseRepository`
2. Create Commands for business logic
3. Setup Dependencies in `app/dependencies.py`
4. Create HTTP/WebSocket handlers using commands

### For Existing Features

Gradual migration approach:

1. **Create repository** for data access
2. **Create commands** for business logic
3. **Create new endpoints** using new patterns
4. **Keep old endpoints** for backward compatibility
5. **Migrate clients** to use new endpoints
6. **Remove old endpoints** once migration complete

### Example Implementation

```python
# Current pattern: Repository + Command
@router.get("/books")
async def get_books(repo: BookRepoDep):
    command = GetBooksCommand(repo)
    return await command.execute(GetBooksInput())
```

---

## Best Practices

### 1. Keep Models Simple

❌ **Don't** add business logic to models:
```python
class Author(SQLModel, table=True):
    async def validate_unique_name(self):  # ❌ No!
        ...
```

✅ **Do** keep models as data containers:
```python
class Author(SQLModel, table=True):
    id: int | None = None
    name: str
    # Just data, no logic
```

### 2. Use Commands for Business Logic

❌ **Don't** put logic in handlers:
```python
@router.post("/authors")
async def create_author(data: dict):
    # Validation logic here  # ❌ No!
    if len(data["name"]) < 2:
        raise ValueError("Too short")
    ...
```

✅ **Do** encapsulate in commands:
```python
class CreateAuthorCommand:
    async def execute(self, input_data):
        # Validation and business logic here  # ✅ Yes!
        ...
```

### 3. Type Everything

```python
# ✅ Full type hints
class GetAuthorsCommand(BaseCommand[GetAuthorsInput, list[Author]]):
    def __init__(self, repository: AuthorRepository) -> None:
        self.repository = repository

    async def execute(self, input_data: GetAuthorsInput) -> list[Author]:
        ...
```

### 4. Test in Isolation

```python
# ✅ Test command without database
async def test_command():
    mock_repo = AsyncMock()  # No real database!
    command = CreateAuthorCommand(mock_repo)
    result = await command.execute(CreateAuthorInput(name="Test"))
    assert result.name == "Test"
```

---

## References

- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Martin Fowler
- [Command Pattern](https://refactoring.guru/design-patterns/command) - Refactoring Guru
- [Dependency Injection in FastAPI](https://fastapi.tiangolo.com/tutorial/dependencies/)
- Issue [#29](https://github.com/acikabubo/fastapi-http-websocket/issues/29)

---

**Last Updated**: 2025-12-05
**Author**: Claude Code
**Status**: ✅ Active
