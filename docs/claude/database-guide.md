# Database Guide

This guide covers database session management, async relationships, migrations, and pagination.

## Table of Contents

- [Database Session Management](#database-session-management)
- [Async Relationships with AsyncAttrs](#async-relationships-with-asyncattrs)
- [Database Migrations](#database-migrations)
- [Database Pagination](#database-pagination)
- [Performance Optimizations](#performance-optimizations)
- [Related Documentation](#related-documentation)

## Database Session Management

**IMPORTANT**: Use the Repository pattern for all database operations. This enables:
- Separation of concerns (models are pure data classes)
- Easier testing with mocked repositories
- Better transaction control
- Reusable business logic via Commands

### Repository Pattern

```python
from app.repositories.base import BaseRepository

class MyModelRepository(BaseRepository[MyModel]):
    async def get_by_name(self, name: str) -> MyModel | None:
        """Get model by name."""
        stmt = select(MyModel).where(MyModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str) -> list[MyModel]:
        """Search models by query."""
        stmt = select(MyModel).where(MyModel.name.contains(query))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

### Usage in HTTP Endpoints

```python
from app.storage.db import async_session
from app.dependencies import MyModelRepoDep  # Dependency injection

@router.post("/my-models")
async def create_model(
    instance: MyModel,
    repo: MyModelRepoDep  # Injected by FastAPI
) -> MyModel:
    return await repo.create(instance)

@router.get("/my-models")
async def get_models(repo: MyModelRepoDep) -> list[MyModel]:
    return await repo.get_all()

@router.get("/my-models/{id}")
async def get_model(id: int, repo: MyModelRepoDep) -> MyModel:
    model = await repo.get_by_id(id)
    if not model:
        raise HTTPException(status_code=404, detail="Not found")
    return model
```

### Usage in WebSocket Handlers

```python
from app.storage.db import async_session

async def my_handler(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        repo = MyModelRepository(session)
        items = await repo.get_all()
        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[item.model_dump() for item in items]
        )
```

### Why Repository Pattern?

- **Testability**: Easy to mock repositories without database
- **Reusability**: Same repository used in HTTP and WebSocket handlers
- **Maintainability**: Business logic separated from data access
- **Type Safety**: Full type hints with FastAPI's `Depends()`

See [Architecture Guide](architecture-guide.md) for complete examples.

## Async Relationships with AsyncAttrs

When SQLModel models have relationships (foreign keys, one-to-many, many-to-many), use the `BaseModel` class which includes SQLAlchemy's `AsyncAttrs` mixin.

### Base Model Pattern

All table models that may have relationships should inherit from `BaseModel`:

```python
# app/models/base.py
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlmodel import SQLModel

class BaseModel(SQLModel, AsyncAttrs):
    """Base model with async relationship support."""
    pass
```

### Model Definition

```python
# app/models/author.py
from sqlmodel import Field, Relationship
from app.models.base import BaseModel

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

### The N+1 Query Problem

Without eager loading, accessing relationships in loops triggers the N+1 query problem:

```python
# ❌ BAD - N+1 queries
async with async_session() as session:
    authors = await session.exec(select(Author))  # 1 query

    for author in authors:  # Loop through N authors
        books = await author.awaitable_attrs.books  # N additional queries!
        print(f"{author.name}: {len(books)} books")

# Total: 1 + N queries (if you have 100 authors, that's 101 queries!)
```

### Accessing Relationships with Eager Loading

**1. selectinload() - For One-to-Many and Many-to-Many (Recommended)**
```python
from sqlalchemy.orm import selectinload

# ✅ GOOD - Only 2 queries total
async with async_session() as session:
    # Load authors with all books in 2 optimized queries
    stmt = select(Author).options(selectinload(Author.books))
    result = await session.execute(stmt)
    authors = result.scalars().all()

    # Relationships already loaded, no await needed
    for author in authors:
        books = author.books  # ✅ Already loaded, no additional query!
        print(f"{author.name}: {len(books)} books")

# Total: 2 queries (1 for authors, 1 for all books in bulk)
```

**2. joinedload() - For Many-to-One Relationships**
```python
from sqlalchemy.orm import joinedload

# ✅ GOOD - Only 1 query with JOIN
async with async_session() as session:
    stmt = select(Book).options(joinedload(Book.author))
    result = await session.execute(stmt)
    books = result.scalars().unique().all()  # unique() required with joins!

    # Author already loaded for each book
    for book in books:
        author = book.author  # ✅ Already loaded!
        print(f"{book.title} by {author.name}")

# Total: 1 query (single JOIN)
```

**3. Nested Eager Loading - For Deep Relationships**
```python
# Load authors → books → reviews (3 levels deep)
stmt = select(Author).options(
    selectinload(Author.books).selectinload(Book.reviews)
)
result = await session.execute(stmt)
authors = result.scalars().all()

for author in authors:
    for book in author.books:
        reviews = book.reviews  # All loaded!

# Total: 3 queries (authors, books, reviews)
```

**4. Lazy Loading with awaitable_attrs (Use Sparingly)**
```python
async with async_session() as session:
    author = await session.get(Author, 1)

    # Access lazy-loaded relationship asynchronously
    books = await author.awaitable_attrs.books  # ✅ Awaitable
    for book in books:
        print(book.title)
```

### Performance Comparison

| Strategy | Query Count | Best For | Example Use Case |
|----------|-------------|----------|------------------|
| Lazy Loading (`awaitable_attrs`) | 1 + N | Single relationship access | Loading one author's books |
| `selectinload()` | 2 | One-to-many, many-to-many | Authors → books, users → roles |
| `joinedload()` | 1 (with JOIN) | Many-to-one | Books → author, orders → customer |
| Nested eager loading | 1 per level | Deep relationships | Authors → books → reviews |

### When to Use Each Strategy

✅ **Use Eager Loading When:**
- Accessing relationships in loops (list views, reports)
- Loading multiple related objects at once
- Building API responses with nested data
- Displaying paginated lists with related entities
- You know you'll need the relationship data

⚠️ **Use Lazy Loading When:**
- Relationship might not be accessed (conditional logic)
- Loading single object with specific relationship
- Relationship access is rare or dynamic
- Eager loading would load too much unnecessary data

### Important Notes

- Models without relationships (e.g., `UserAction` audit logs) don't need to inherit from `BaseModel`
- `AsyncAttrs` has no performance penalty if relationships are not used
- Avoid accessing relationships directly without eager loading or `awaitable_attrs` - it will raise `MissingGreenlet` errors
- Always use `.unique()` when using `joinedload()` to remove duplicate rows from JOIN results
- For repositories, prefer eager loading in `get_all()` methods to avoid N+1 queries

## Database Migrations

This project uses **Alembic** for database schema migrations.

### Key Commands

```bash
# Apply all pending migrations
make migrate

# Generate new migration after model changes
make migration msg="Add email field to Author"

# Rollback last migration
make rollback

# View migration history
make migration-history

# Check current migration version
make migration-current

# Stamp database at specific revision (for existing DBs)
make migration-stamp rev="head"
```

### Important Workflow

1. Modify your SQLModel (e.g., add field to `Author`)
2. Generate migration: `make migration msg="description"`
3. **ALWAYS review** the generated migration in `app/storage/migrations/versions/`
4. Apply migration: `make migrate`
5. If issues occur, rollback: `make rollback`

### Adding New Models

When you create a new model, import it in `app/storage/migrations/env.py`:
```python
from app.models.author import Author  # noqa: F401
from app.models.book import Book  # noqa: F401  # ADD NEW IMPORTS
```

See [docs/DATABASE_MIGRATIONS.md](../../docs/DATABASE_MIGRATIONS.md) for complete guide.

### Migration Testing

The project includes automated migration testing.

**Running migration tests:**
```bash
# Test migrations manually (upgrade/downgrade cycle)
make test-migrations

# Run pytest-based structure tests
uv run pytest tests/test_migrations.py -v
```

**Pre-commit hook:**
Migration tests automatically run before commits when migration files are modified.

**What gets tested:**

1. **Upgrade/Downgrade Cycle** (`scripts/test_migrations.py`):
   - Downgrades by one revision
   - Upgrades back to head
   - Verifies database stays in consistent state

2. **Migration Structure** (`tests/test_migrations.py`):
   - All revision IDs are unique
   - All migrations have descriptive docstrings (>10 chars)
   - No conflicting migration branches exist
   - All migrations (except first) have down_revision

**Best practices enforced:**
- ✅ Every migration must have a clear docstring explaining changes
- ✅ Migrations must be reversible (have downgrade logic)
- ✅ No merge conflicts in migration history
- ✅ Migration IDs must be unique

## Database Pagination

The application supports both **offset-based** (traditional) and **cursor-based** pagination, with optional eager loading.

### Offset-based Pagination (Traditional)

Standard page-based pagination using `OFFSET` and `LIMIT`:

```python
from app.storage.db import get_paginated_results

# Traditional offset pagination
results, meta = await get_paginated_results(
    Author,
    page=request.data.get("page", 1),
    per_page=request.data.get("per_page", 20),
    filters={"status": "active"}  # Optional
)

return ResponseModel.success(
    request.pkg_id,
    request.req_id,
    data=[r.model_dump() for r in results],
    meta=meta
)
```

**Pros:**
- Familiar page-based navigation
- Shows total count and page numbers
- Easy to jump to specific pages

**Cons:**
- O(n) performance - slower for large offsets
- Inconsistent results if data changes
- Expensive `COUNT(*)` query

### Cursor-based Pagination (Recommended)

Provides consistent O(1) performance:

```python
from app.storage.db import get_paginated_results

# First page - no cursor
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor=""  # Empty string or None for first page
)

# Subsequent pages - use next_cursor from previous response
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor=meta.next_cursor  # Base64-encoded last item ID
)
```

**Pros:**
- O(1) performance - consistent speed
- Stable results - no duplicates if data changes
- No expensive `COUNT(*)` query
- Better for infinite scroll

**Cons:**
- Cannot jump to arbitrary pages
- No total count or page numbers

### Eager Loading (Prevent N+1 Queries)

```python
# Eager load relationships to prevent N+1 queries
results, meta = await get_paginated_results(
    Author,
    per_page=20,
    cursor="",
    eager_load=["books"]  # Load books relationship in 2 queries (not N+1)
)
```

### Type-Safe Filters with Pydantic Schemas

```python
# app/schemas/filters.py
from pydantic import BaseModel, Field
from app.schemas.filters import BaseFilter

class AuthorFilters(BaseFilter):
    """Type-safe filters for Author model queries."""

    id: int | None = Field(
        default=None,
        description="Filter by exact author ID",
    )
    name: str | None = Field(
        default=None,
        description="Filter by author name (case-insensitive partial match)",
    )

# Usage
filters = AuthorFilters(name="John")
authors, meta = await get_paginated_results(
    Author,
    page=1,
    per_page=20,
    filters=filters,  # Type-safe!
)
```

### Strategy Pattern (Advanced Usage)

The pagination system uses the **Strategy pattern** to separate different pagination algorithms into focused, testable classes. While `get_paginated_results()` provides a backward-compatible facade, you can use strategies directly for more control.

#### Using Strategies Directly

```python
from app.storage.pagination import OffsetPaginationStrategy, CursorPaginationStrategy
from sqlmodel import select

async with async_session() as session:
    # Offset pagination strategy
    strategy = OffsetPaginationStrategy(
        session=session,
        page=2,
        skip_count=False,  # Include total count
        filter_dict={"status": "active"}
    )

    query = select(Author).where(Author.status == "active").order_by(Author.id)
    items, meta = await strategy.paginate(query, Author, page_size=20)

    # Cursor pagination strategy
    strategy = CursorPaginationStrategy(
        session=session,
        cursor="MTA="  # Base64 cursor from previous page
    )

    query = select(Author).order_by(Author.id)
    items, meta = await strategy.paginate(query, Author, page_size=20)
```

#### Package Structure

```
app/storage/pagination/
├── __init__.py              # Exports strategy classes
├── protocol.py              # PaginationStrategy protocol
├── offset.py                # OffsetPaginationStrategy
├── cursor.py                # CursorPaginationStrategy
├── factory.py               # Strategy selector
└── query_builder.py         # Shared filter/query utilities
```

#### Benefits of Strategy Pattern

- **Clarity**: Each strategy is ~60-120 lines with single responsibility
- **Testability**: Strategies tested independently (117 tests)
- **Extensibility**: Easy to add new strategies (keyset, GraphQL-style)
- **Type Safety**: Protocol-based design with mypy checking
- **Maintainability**: Reduced complexity from 12+ branches to 2-3 per strategy

#### Custom Strategies

To add a custom pagination strategy:

```python
# app/storage/pagination/keyset.py
from typing import Type
from sqlalchemy import Select
from app.schemas.response import MetadataModel
from app.schemas.generic_typing import GenericSQLModelType

class KeysetPaginationStrategy:
    """Keyset pagination using composite keys."""

    def __init__(self, session: AsyncSession, last_seen_key: tuple | None):
        self.session = session
        self.last_seen_key = last_seen_key

    async def paginate(
        self,
        query: Select,
        model: Type[GenericSQLModelType],
        page_size: int,
    ) -> tuple[list[GenericSQLModelType], MetadataModel]:
        # Implement keyset pagination logic
        ...
```

#### Backward Compatibility

All existing code using `get_paginated_results()` works unchanged - the facade delegates to strategies internally:

```python
# This still works (uses OffsetPaginationStrategy internally)
items, meta = await get_paginated_results(Author, page=1, per_page=20)

# This also works (uses CursorPaginationStrategy internally)
items, meta = await get_paginated_results(Author, cursor="MTA=", per_page=20)
```

### Choosing Between Offset and Cursor Pagination

**Use Cursor Pagination When:**
- ✅ Performance is critical (large datasets, high traffic)
- ✅ Real-time data (frequent inserts/updates)
- ✅ Infinite scroll UI pattern
- ✅ Mobile apps (bandwidth-sensitive)

**Use Offset Pagination When:**
- ✅ Need total count and page numbers
- ✅ Users need to jump to arbitrary pages
- ✅ Small datasets (< 1000 items)
- ✅ Data rarely changes
- ✅ Admin dashboards with page selectors

### Testing Pagination Endpoints

The project includes comprehensive test request files for manual testing with the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) VS Code extension.

**Test file**: `api-testing/pagination-test.http`

**Installation:**
```bash
# VS Code extension (search "REST Client" in Extensions)
# Or install directly
code --install-extension humao.rest-client
```

**Usage:**

1. Open `api-testing/pagination-test.http` in VS Code
2. Update the token variable at the top:
   ```http
   @token = YOUR_ACTUAL_TOKEN_HERE
   ```
3. Click "Send Request" above any test case
4. View response in side panel

**Test Coverage (33 scenarios):**

- **Offset Pagination** (Tests 1-10)
  - First/middle/last pages
  - Filter combinations
  - Skip count mode
  - Page size validation
  - Invalid inputs (defaults, boundaries)

- **Cursor Pagination** (Tests 11-17)
  - First page (empty cursor)
  - Next page navigation
  - Filter support
  - Invalid cursor handling

- **Eager Loading** (Tests 18-19)
  - Offset + eager loading
  - Cursor + eager loading

- **Edge Cases** (Tests 20-24)
  - Empty results
  - Large page numbers
  - Boundary values (0, negative)

- **Performance Testing** (Tests 25-29)
  - Offset O(n) degradation (pages 1, 10, 100)
  - Cursor O(1) consistency (shallow/deep pages)

- **Cache Testing** (Tests 30-33)
  - Cache miss/hit scenarios
  - Filter variations
  - Skip count bypass

**Example Test Request:**
```http
### 1. Offset Pagination - First Page
GET {{baseUrl}}/authors/paginated?page=1&per_page=20
Content-Type: application/json
Authorization: Bearer {{token}}
```

**Expected Response Structure:**
```json
{
  "items": [
    {"id": 1, "name": "Author 1"},
    {"id": 2, "name": "Author 2"}
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_more": true,
    "next_cursor": null
  }
}
```

**Note**: WebSocket testing through REST Client is not reliably supported. Use dedicated WebSocket clients (websocat, wscat, Postman) for WebSocket endpoint testing.

## Performance Optimizations

### Slow Query Detection

**Location**: `app/utils/query_monitor.py`

- Automatically tracks all database query execution times
- Logs queries exceeding 100ms threshold (configurable `SLOW_QUERY_THRESHOLD`)
- Records metrics for Prometheus monitoring
- Enabled automatically on application startup

**Metrics:**
- `db_query_duration_seconds{operation="select|insert|update|delete"}` - Query duration histogram
- `db_slow_queries_total{operation="select|insert|update|delete"}` - Counter of slow queries

### Pagination Count Caching

**Location**: `app/utils/pagination_cache.py`

- Redis-based caching of expensive `COUNT(*)` queries
- Default TTL: 5 minutes (configurable)
- Cache keys based on model name and filter hash

**Cache Invalidation:**
```python
from app.utils.pagination_cache import invalidate_count_cache

# After creating a new record
async def create_author(author: Author, repo: AuthorRepository) -> Author:
    result = await repo.create(author)
    await invalidate_count_cache("Author")  # Invalidate all Author counts
    return result
```

**Performance Comparison:**

| Table Size | Without Cache | With Cache | Improvement |
|------------|---------------|------------|-------------|
| 1,000 rows | 5ms          | 1ms        | 80% faster  |
| 10,000 rows| 45ms         | 1ms        | 98% faster  |
| 100,000 rows| 450ms       | 1ms        | 99.8% faster|

### Query Performance Best Practices

1. **Add Database Indexes:**
   ```python
   class Author(BaseModel, table=True):
       name: str = Field(index=True)  # Frequently filtered
       email: str = Field(unique=True, index=True)
       status: str = Field(index=True)
   ```

2. **Use Eager Loading:**
   ```python
   from sqlalchemy.orm import selectinload

   stmt = select(Author).options(selectinload(Author.books))
   authors = await session.exec(stmt)
   # All books loaded in 2 optimized queries (no N+1)
   ```

3. **Monitor Slow Queries:**
   - Check application logs for slow query warnings
   - Review Prometheus metrics for query duration trends
   - Use `EXPLAIN ANALYZE` for query optimization

## Related Documentation

- [Git Workflow Guide](git-workflow.md) - Git workflow, issue management, worktree syncing
- [Architecture Guide](architecture-guide.md) - Design patterns, components, request flow
- [Development Guide](development-guide.md) - Running the app, Docker, WebSocket handlers
- [Testing Guide](testing-guide.md) - Test infrastructure, fixtures, load/chaos tests
- [Code Quality Guide](code-quality-guide.md) - Linting, type checking, pre-commit hooks
- [Configuration Guide](configuration-guide.md) - Settings, environment variables, validation
- [Monitoring Guide](monitoring-guide.md) - Prometheus, alerts, logging, dashboards
