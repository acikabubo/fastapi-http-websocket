# Database Operations

## Overview

The application uses PostgreSQL with async SQLModel/SQLAlchemy for database operations.

## Configuration

Database configuration in `app/settings.py`:

```python
POSTGRES_SERVER: str = "localhost"
POSTGRES_PORT: int = 5432
POSTGRES_USER: str = "postgres"
POSTGRES_PASSWORD: str = "postgres"
POSTGRES_DB: str = "app_db"

# Connection pool
POOL_SIZE: int = 5
MAX_OVERFLOW: int = 10
```

## Session Management

### Getting a Session

Use the async context manager:

```python
from app.storage.db import async_session

async with async_session() as session:
    async with session.begin():
        # Database operations here
        result = await session.execute(select(Author))
```

### Dependency Injection

For HTTP endpoints, use `SessionDep`:

```python
from app.dependencies import SessionDep

@router.get("/authors")
async def get_authors(session: SessionDep) -> list[Author]:
    """Session is automatically provided and cleaned up."""
    result = await session.execute(select(Author))
    return list(result.scalars().all())
```

## Models

### Defining Models

```python
from sqlmodel import Field, SQLModel

class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Async Relationships

For models with relationships, inherit from `BaseModel`:

```python
from app.models.base import BaseModel
from sqlmodel import Relationship

class Author(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    books: list["Book"] = Relationship(back_populates="author")

class Book(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author_id: int = Field(foreign_key="author.id")
    author: Author = Relationship(back_populates="books")
```

### Eager Loading

```python
from sqlalchemy.orm import selectinload

# Load author with all books
stmt = select(Author).options(selectinload(Author.books))
result = await session.execute(stmt)
author = result.scalar_one()

# Relationship already loaded
books = author.books  # No await needed!
```

## CRUD Operations

### Create

```python
from app.storage.db import async_session

async with async_session() as session:
    async with session.begin():
        author = Author(name="John Doe")
        session.add(author)
        await session.flush()  # Get ID
        await session.refresh(author)
        return author
```

### Read

```python
from sqlmodel import select

# Get by ID
async with async_session() as session:
    author = await session.get(Author, 1)

# Query with filters
async with async_session() as session:
    stmt = select(Author).where(Author.name == "John Doe")
    result = await session.execute(stmt)
    author = result.scalar_one_or_none()

# Get all
async with async_session() as session:
    result = await session.execute(select(Author))
    authors = list(result.scalars().all())
```

### Update

```python
async with async_session() as session:
    async with session.begin():
        author = await session.get(Author, 1)
        if author:
            author.name = "Jane Doe"
            session.add(author)
            await session.flush()
            await session.refresh(author)
```

### Delete

```python
async with async_session() as session:
    async with session.begin():
        author = await session.get(Author, 1)
        if author:
            await session.delete(author)
```

## Repository Pattern

### Using Repositories

Encapsulate database logic in repositories:

```python
from app.repositories.author_repository import AuthorRepository

async with async_session() as session:
    repo = AuthorRepository(session)

    # Create
    author = await repo.create(Author(name="John Doe"))

    # Read
    author = await repo.get_by_id(1)
    authors = await repo.get_all()
    john = await repo.get_by_name("John")

    # Update
    author.name = "Jane Doe"
    await repo.update(author)

    # Delete
    await repo.delete(author)
```

### Custom Queries

Add repository methods for complex queries:

```python
class AuthorRepository(BaseRepository[Author]):
    async def search_by_name(self, pattern: str) -> list[Author]:
        """Search authors by name pattern."""
        stmt = select(Author).where(Author.name.ilike(f"%{pattern}%"))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

## Pagination

### Using get_paginated_results

```python
from app.storage.db import get_paginated_results

results, meta = await get_paginated_results(
    Author,
    page=1,
    per_page=20,
    filters={"name": "John"}
)

# meta contains: page, per_page, total, pages
```

### Custom Pagination

```python
from sqlmodel import select, func

async def get_paginated_authors(page: int, per_page: int):
    async with async_session() as session:
        # Count total
        count_stmt = select(func.count(Author.id))
        total = (await session.execute(count_stmt)).scalar_one()

        # Get page
        offset = (page - 1) * per_page
        stmt = select(Author).offset(offset).limit(per_page)
        result = await session.execute(stmt)
        items = list(result.scalars().all())

        return items, {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
```

## Transactions

### Automatic Transactions

Using `session.begin()`:

```python
async with async_session() as session:
    async with session.begin():
        # All operations in one transaction
        author = Author(name="John")
        session.add(author)
        await session.flush()

        book = Book(title="Book", author_id=author.id)
        session.add(book)
        # Commits automatically on exit
```

### Manual Commit/Rollback

```python
async with async_session() as session:
    try:
        author = Author(name="John")
        session.add(author)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

## Migrations

### Create Migration

```bash
make migration msg="Add email to Author"
```

### Apply Migrations

```bash
make migrate
```

### Rollback

```bash
make rollback
```

See [Database Migrations](../development/migrations.md) for full guide.

## Error Handling

### IntegrityError

```python
from sqlalchemy.exc import IntegrityError

try:
    author = Author(name="John")
    session.add(author)
    await session.commit()
except IntegrityError as e:
    await session.rollback()
    logger.error(f"Constraint violation: {e}")
    raise HTTPException(status_code=400, detail="Duplicate entry")
```

### NoResultFound

```python
from sqlalchemy.exc import NoResultFound

try:
    stmt = select(Author).where(Author.id == 999)
    author = (await session.execute(stmt)).scalar_one()
except NoResultFound:
    raise HTTPException(status_code=404, detail="Author not found")
```

## Best Practices

### 1. Always Use Sessions as Context Managers

```python
# ✅ Good
async with async_session() as session:
    async with session.begin():
        # operations

# ❌ Bad
session = async_session()
# operations
await session.close()  # Easy to forget!
```

### 2. Use Repositories

```python
# ✅ Good - testable, reusable
repo = AuthorRepository(session)
authors = await repo.get_all()

# ❌ Bad - logic in handlers
result = await session.execute(select(Author))
authors = list(result.scalars().all())
```

### 3. Eager Load Relationships

```python
# ✅ Good - one query
stmt = select(Author).options(selectinload(Author.books))
authors = (await session.execute(stmt)).scalars().all()

# ❌ Bad - N+1 queries
authors = (await session.execute(select(Author))).scalars().all()
for author in authors:
    books = await author.awaitable_attrs.books  # Separate query!
```

### 4. Use Transactions

```python
# ✅ Good - atomic operation
async with session.begin():
    author = Author(name="John")
    session.add(author)
    await session.flush()

    book = Book(author_id=author.id)
    session.add(book)

# ❌ Bad - partial commits possible
author = Author(name="John")
session.add(author)
await session.commit()

book = Book(author_id=author.id)
session.add(book)
await session.commit()  # If this fails, author still created!
```

## Performance

### Connection Pooling

Adjust pool size in settings:

```python
POOL_SIZE: int = 10
MAX_OVERFLOW: int = 20
```

### Query Optimization

```python
# Use select() for better performance
stmt = select(Author).where(Author.name == "John")

# Use indexes
class Author(SQLModel, table=True):
    name: str = Field(index=True)  # Indexed!

# Limit results
stmt = select(Author).limit(100)
```

## Testing

### Test with In-Memory Database

```python
import pytest
from sqlmodel import create_engine, Session

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

### Mock Repository

```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_by_id.return_value = Author(id=1, name="Test")
    return repo
```

## Related

- [Database Migrations](../development/migrations.md)
- [Design Patterns](../architecture/design-patterns.md)
- [Testing Guide](../development/testing.md)
