# Database Schema

This document provides a comprehensive overview of the application's database schema, including entity-relationship diagrams, table structures, migration workflows, and best practices.

## Overview

The application uses **PostgreSQL** as its relational database with **SQLModel** (built on SQLAlchemy 2.0) for ORM functionality and **Alembic** for schema migrations. All models support async operations using SQLAlchemy's async engine.

### Technology Stack

- **Database**: PostgreSQL 17.2
- **ORM**: SQLModel 0.0.22 (SQLAlchemy 2.0+ async)
- **Migrations**: Alembic 1.14.0
- **Connection Pooling**: SQLAlchemy async engine with connection pool
- **Session Management**: AsyncSession with context managers

## Entity-Relationship Diagram

The database schema consists of two primary tables: `author` (example domain entity) and `user_actions` (audit logs).

```mermaid
erDiagram
    author {
        INTEGER id PK "Auto-increment primary key"
        VARCHAR name "Author name"
    }

    user_actions {
        INTEGER id PK "Auto-increment primary key"
        TIMESTAMP timestamp "UTC timestamp with index"
        VARCHAR user_id "Keycloak user ID (indexed)"
        VARCHAR username "Username (indexed)"
        JSON user_roles "User roles array"
        VARCHAR action_type "HTTP method or WS PkgID (indexed)"
        VARCHAR resource "Resource accessed"
        VARCHAR outcome "success, error, permission_denied (indexed)"
        VARCHAR ip_address "Client IP (IPv4/IPv6)"
        TEXT user_agent "Browser/client user agent"
        VARCHAR request_id "Correlation UUID (indexed)"
        JSON request_data "Sanitized request payload"
        INTEGER response_status "HTTP or WebSocket status code"
        TEXT error_message "Error details if failed"
        INTEGER duration_ms "Processing duration in milliseconds"
    }
```

### Database Indexes

Efficient query performance is achieved through strategic indexing:

**`author` table:**
- Primary key: `id` (auto-increment)

**`user_actions` table:**
- Primary key: `id` (auto-increment)
- Single-column indexes:
  - `timestamp` - For time-range queries
  - `user_id` - For user activity lookups
  - `username` - For filtering by username
  - `action_type` - For action type filtering
  - `outcome` - For filtering by success/error/denied
  - `request_id` - For request correlation
- Composite indexes:
  - `idx_user_timestamp` (`user_id`, `timestamp`) - User activity timeline
  - `idx_user_action` (`user_id`, `action_type`) - User-specific action filtering

## Table Schemas

### `author` Table

Domain entity representing authors in the system. This is a simple example table demonstrating the Repository + Command pattern.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `name` | VARCHAR | NOT NULL | Author name |

**Model Definition**: [app/models/author.py](../../app/models/author.py)

**Key Features**:
- Inherits from `BaseModel` for async relationship support
- Clean data model without Active Record methods
- Database operations handled by `AuthorRepository`
- Used in examples for demonstrating CRUD operations

**Example Usage**:
```python
from app.models.author import Author
from app.repositories.author_repository import AuthorRepository
from app.storage.db import async_session

async with async_session() as session:
    repo = AuthorRepository(session)
    author = await repo.create(Author(name="J.R.R. Tolkien"))
```

### `user_actions` Table

Comprehensive audit log for tracking all user activities across the application. Critical for security, compliance, debugging, and analytics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique log entry identifier |
| `timestamp` | TIMESTAMP WITH TIMEZONE | NOT NULL, INDEXED | UTC timestamp when action occurred |
| `user_id` | VARCHAR(255) | NOT NULL, INDEXED | Keycloak user ID (sub claim from JWT) |
| `username` | VARCHAR(255) | NOT NULL, INDEXED | Human-readable username (preferred_username) |
| `user_roles` | JSON | NOT NULL | Array of roles user had at time of action |
| `action_type` | VARCHAR(100) | NOT NULL, INDEXED | HTTP method (GET, POST) or WebSocket PkgID |
| `resource` | VARCHAR(500) | NOT NULL | Resource accessed (URL path or entity ID) |
| `outcome` | VARCHAR(50) | NOT NULL, INDEXED | Result: success, error, permission_denied |
| `ip_address` | VARCHAR(45) | NULLABLE | Client IP address (IPv4 or IPv6) |
| `user_agent` | TEXT | NULLABLE | Browser/client user agent string |
| `request_id` | VARCHAR(100) | NULLABLE, INDEXED | UUID for request correlation across services |
| `request_data` | JSON | NULLABLE | Sanitized request payload (sensitive data redacted) |
| `response_status` | INTEGER | NULLABLE | HTTP status code or WebSocket response code |
| `error_message` | TEXT | NULLABLE | Error details if action failed |
| `duration_ms` | INTEGER | NULLABLE | Request processing duration in milliseconds |

**Model Definition**: [app/models/user_action.py](../../app/models/user_action.py)

**Key Features**:
- Immutable audit trail (insert-only, no updates/deletes)
- JSON columns for flexible data storage
- Comprehensive indexing for fast queries
- Timezone-aware timestamps (UTC)
- Proxy-aware IP address tracking
- Request correlation via `request_id`

**Example Queries**:

```sql
-- Find all failed actions for a specific user
SELECT timestamp, action_type, resource, error_message
FROM user_actions
WHERE username = 'acika'
  AND outcome IN ('error', 'permission_denied')
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Analyze slow operations (>1 second)
SELECT action_type, AVG(duration_ms), MAX(duration_ms), COUNT(*)
FROM user_actions
WHERE duration_ms > 1000
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY action_type
ORDER BY AVG(duration_ms) DESC;

-- Track user activity timeline
SELECT
  DATE_TRUNC('hour', timestamp) AS hour,
  COUNT(*) AS events,
  COUNT(CASE WHEN outcome = 'error' THEN 1 END) AS errors
FROM user_actions
WHERE user_id = 'user-uuid-here'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

## Database Migrations

### Migration System

The application uses **Alembic** for schema version control. All schema changes are managed through migration files stored in [app/storage/migrations/versions/](../../app/storage/migrations/versions/).

```mermaid
graph LR
    A[Modify SQLModel] --> B[Generate Migration]
    B --> C[Review Migration File]
    C --> D{Changes OK?}
    D -->|No| E[Edit Migration]
    D -->|Yes| F[Apply Migration]
    E --> F
    F --> G[Test Database]
    G --> H{Tests Pass?}
    H -->|No| I[Rollback]
    H -->|Yes| J[Commit Changes]
    I --> E
```

### Migration Workflow

#### 1. Creating New Migrations

When you modify a SQLModel (add/remove/change columns), generate a migration:

```bash
# Generate migration after model changes
make migration msg="Add email field to Author"

# Or use alembic directly
alembic -c app/storage/alembic.ini revision --autogenerate -m "Add email field to Author"
```

This creates a new file in `app/storage/migrations/versions/` with upgrade/downgrade logic.

#### 2. Reviewing Migrations

**CRITICAL**: Always review generated migrations before applying them.

```bash
# View the generated migration file
cat app/storage/migrations/versions/XXXX_description.py

# Check migration structure
uv run pytest tests/test_migrations.py -v
```

Common issues to check:
- Verify column types are correct
- Check for unintended table drops
- Ensure indexes are created efficiently
- Validate foreign key constraints
- Review data migrations (if any)

#### 3. Applying Migrations

```bash
# Apply all pending migrations
make migrate

# Or use alembic directly
alembic -c app/storage/alembic.ini upgrade head

# Apply specific number of migrations
alembic -c app/storage/alembic.ini upgrade +1
```

#### 4. Rolling Back Migrations

If a migration causes issues:

```bash
# Rollback last migration
make rollback

# Or use alembic directly
alembic -c app/storage/alembic.ini downgrade -1

# Rollback to specific revision
alembic -c app/storage/alembic.ini downgrade <revision_id>
```

#### 5. Viewing Migration History

```bash
# View migration history
make migration-history

# Check current database version
make migration-current

# Show pending migrations
alembic -c app/storage/alembic.ini current
alembic -c app/storage/alembic.ini heads
```

### Existing Migrations

The application has the following migrations (in chronological order):

1. **`94cef3eb6eae`** - "Add user_actions table for audit logging"
   - Creates `user_actions` table with all columns
   - Adds indexes: `timestamp`, `user_id`, `username`, `action_type`, `outcome`, `request_id`
   - Adds composite indexes: `idx_user_timestamp`, `idx_user_action`

2. **`b857e3e16921`** - "Add author table"
   - Creates `author` table
   - Simple structure: `id` (PK) and `name`

### Migration Testing

Migrations are automatically tested to ensure they can be applied and rolled back cleanly.

**Automated Testing**:
```bash
# Run migration tests manually
make test-migrations

# Run pytest-based structure tests
uv run pytest tests/test_migrations.py -v
```

**What Gets Tested**:
1. **Upgrade/Downgrade Cycle** - Migrations can be applied and reverted
2. **Migration Structure** - All revision IDs are unique
3. **Docstrings** - All migrations have descriptive docstrings
4. **No Conflicts** - No branching conflicts in migration history
5. **Dependencies** - All migrations (except first) have `down_revision`

**Pre-commit Hook**:
Migration structure tests run automatically when migration files are modified during commit. The hook prevents commits if migrations have structural issues.

### Adding New Models

When creating a new SQLModel table, you must import it in the migrations environment:

**File**: [app/storage/migrations/env.py](../../app/storage/migrations/env.py)

```python
# Import all models for Alembic autogenerate
from app.models.author import Author  # noqa: F401
from app.models.user_action import UserAction  # noqa: F401
from app.models.your_new_model import YourNewModel  # noqa: F401  # ADD THIS
```

Without this import, Alembic won't detect your new model when generating migrations.

## Database Connection Management

### Connection Configuration

Database connections are configured via environment variables in `docker/.db_env`:

```bash
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=hwdev123!@#
POSTGRES_DB=hwdb

# Connection Settings (app/settings.py)
DB_HOST=hw-db
DB_PORT=5432
DB_NAME=hwdb
DB_USER=postgres
DB_PASSWORD=hwdev123!@#
```

### Connection URL Format

```
postgresql+asyncpg://user:password@host:port/database
```

**Example**: `postgresql+asyncpg://postgres:hwdev123!@#@hw-db:5432/hwdb`

### Async Engine and Session

The application uses SQLAlchemy's async engine with connection pooling:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.settings import settings

# Create async engine with connection pool
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,  # Set to True for SQL query logging
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)

# Async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### Session Usage Patterns

**HTTP Endpoints**:
```python
from app.storage.db import async_session

@router.post("/authors")
async def create_author(author: Author) -> Author:
    async with async_session() as session:
        async with session.begin():  # Automatic commit on success
            session.add(author)
            await session.flush()
            await session.refresh(author)
            return author
```

**WebSocket Handlers**:
```python
async def my_handler(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        items = await MyModel.get_list(session)
        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[item.model_dump() for item in items]
        )
```

**Repository Pattern**:
```python
from app.repositories.author_repository import AuthorRepository

async with async_session() as session:
    repo = AuthorRepository(session)
    authors = await repo.get_all()
```

## Performance Optimizations

### Query Monitoring

The application includes automatic slow query detection to identify performance bottlenecks.

**How It Works**:
- SQLAlchemy event listeners track query execution time
- Queries exceeding 100ms threshold are logged as warnings
- Metrics exported to Prometheus for monitoring

**Configuration**:
```python
# app/utils/query_monitor.py
SLOW_QUERY_THRESHOLD = 0.1  # 100ms
```

**Prometheus Metrics**:
- `db_query_duration_seconds{operation="select|insert|update|delete"}` - Query duration histogram
- `db_slow_queries_total{operation="select|insert|update|delete"}` - Slow query counter

**Example Log**:
```
WARNING - Slow query detected: 0.245s [SELECT] Statement: SELECT * FROM authors WHERE ...
```

### Pagination Count Caching

For large tables, `COUNT(*)` queries can be expensive. The application caches pagination counts in Redis.

**How It Works**:
1. First request: Execute `COUNT(*)` query, cache result in Redis (5-minute TTL)
2. Subsequent requests: Return cached count (99% faster)
3. After data changes: Invalidate cache for that model

**Usage**:
```python
from app.storage.db import get_paginated_results

# Cached count (default)
results, meta = await get_paginated_results(
    Author,
    page=1,
    per_page=20
)

# Skip count entirely (for infinite scroll)
results, meta = await get_paginated_results(
    Author,
    page=1,
    per_page=20,
    skip_count=True  # meta.total will be 0
)
```

**Cache Invalidation**:
```python
from app.utils.pagination_cache import invalidate_count_cache

async def create_author(author: Author) -> Author:
    async with async_session() as session:
        result = await Author.create(session, author)
        await invalidate_count_cache("Author")  # Invalidate cache
        return result
```

**Performance Comparison**:

| Table Size | Without Cache | With Cache | Improvement |
|------------|---------------|------------|-------------|
| 1,000 rows | 5ms          | 1ms        | 80% faster  |
| 10,000 rows| 45ms         | 1ms        | 98% faster  |
| 100,000 rows| 450ms       | 1ms        | 99.8% faster|

### Database Indexes

Strategic indexing is critical for query performance:

**Best Practices**:
1. **Index frequently filtered columns**: `WHERE`, `JOIN`, `ORDER BY` clauses
2. **Composite indexes for common queries**: `(user_id, timestamp)` for user timelines
3. **Avoid over-indexing**: Each index slows down writes
4. **Use partial indexes**: For conditional queries (`WHERE status = 'active'`)
5. **Monitor index usage**: PostgreSQL `pg_stat_user_indexes` view

**Example Indexes**:
```sql
-- Single-column index
CREATE INDEX idx_user_id ON user_actions(user_id);

-- Composite index (order matters!)
CREATE INDEX idx_user_timestamp ON user_actions(user_id, timestamp);

-- Partial index (only active users)
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';
```

### Eager Loading Relationships

Prevent N+1 query problems by eager loading relationships:

```python
from sqlalchemy.orm import selectinload

# Bad: N+1 queries (1 for authors + N for each author's books)
authors = await session.exec(select(Author))
for author in authors:
    books = await author.awaitable_attrs.books  # Separate query per author

# Good: 2 optimized queries (1 for authors + 1 for all books)
stmt = select(Author).options(selectinload(Author.books))
authors = await session.exec(stmt)
for author in authors:
    books = author.books  # Already loaded, no query
```

**Loading Strategies**:
- `selectinload()` - Separate optimized SELECT query (best for one-to-many)
- `joinedload()` - Single query with JOIN (best for many-to-one)
- `subqueryload()` - Subquery approach (for complex relationships)

## Async Relationship Handling

All table models that may have relationships inherit from `BaseModel`, which includes SQLAlchemy's `AsyncAttrs` mixin.

### BaseModel Pattern

```python
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlmodel import SQLModel

class BaseModel(SQLModel, AsyncAttrs):
    """Base model with async relationship support."""
    pass

# All models inherit from BaseModel
class Author(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    books: list["Book"] = Relationship(back_populates="author")
```

### Accessing Relationships

**Preferred: Eager Loading** (Best Performance)
```python
from sqlalchemy.orm import selectinload

stmt = select(Author).options(selectinload(Author.books))
author = await session.execute(stmt).scalar_one()
books = author.books  # Already loaded, no await needed
```

**Alternative: Lazy Loading** (When Needed)
```python
author = await session.get(Author, 1)
books = await author.awaitable_attrs.books  # Awaitable accessor
```

**Rule of Thumb**:
- ✅ Use eager loading (`selectinload`, `joinedload`) for better performance
- ⚠️ Use `awaitable_attrs` only for dynamic relationship access

## Database Initialization

### Application Startup

Database initialization happens automatically on application startup with retry logic:

```python
# app/storage/db.py
async def wait_and_init_db():
    """Wait for database and run migrations with retry logic."""
    for attempt in range(DB_MAX_RETRIES):
        try:
            # Test connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            # Run migrations
            alembic_cfg = Config("app/storage/alembic.ini")
            command.upgrade(alembic_cfg, "head")

            logger.info("Database initialized successfully")
            return
        except Exception as e:
            if attempt < DB_MAX_RETRIES - 1:
                await asyncio.sleep(DB_RETRY_DELAY_SECONDS)
            else:
                raise
```

**Retry Configuration**:
- `DB_MAX_RETRIES = 5` - Maximum connection attempts
- `DB_RETRY_DELAY_SECONDS = 5` - Delay between retries

### Docker Compose Health Checks

PostgreSQL container includes health checks to ensure readiness:

```yaml
hw-db:
  image: postgres:17.2-alpine
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Application waits for database health check before starting:

```yaml
shell:
  depends_on:
    hw-db:
      condition: service_healthy
```

## Best Practices

### Model Design

1. **Inherit from BaseModel**: All table models should extend `BaseModel` for async support
2. **Use type hints**: Full type annotations for all columns
3. **Document models**: Comprehensive docstrings explaining purpose and attributes
4. **Avoid Active Record**: Keep models as data containers, use repositories for operations
5. **Use Field constraints**: Leverage `max_length`, `index`, `unique`, `nullable`

### Session Management

1. **Always use context managers**: `async with async_session() as session:`
2. **Pass sessions to methods**: Don't create sessions inside models
3. **Use transactions explicitly**: `async with session.begin():`
4. **Avoid long-lived sessions**: Keep session scope minimal
5. **Don't mix sync and async**: Use async methods consistently

### Migration Management

1. **Review all migrations**: Never blindly apply autogenerated migrations
2. **Test migrations locally**: Use `make test-migrations` before committing
3. **Write reversible migrations**: Always implement `downgrade()`
4. **Use descriptive messages**: Clear migration names for easy identification
5. **Backup before production migrations**: Always have a rollback plan

### Performance

1. **Use eager loading**: Prevent N+1 queries with `selectinload()`
2. **Index strategically**: Balance read performance vs write overhead
3. **Cache expensive queries**: Use Redis for pagination counts
4. **Monitor slow queries**: Set up alerts for queries >100ms
5. **Use database connection pooling**: Configure `pool_size` and `max_overflow`

### Security

1. **Sanitize audit data**: Redact sensitive information before logging
2. **Use parameterized queries**: Never build SQL strings with user input
3. **Validate input**: Use Pydantic models for request validation
4. **Limit exposed data**: Only return necessary columns in API responses
5. **Rotate credentials**: Regularly update database passwords

## Troubleshooting

### Common Issues

**1. "MissingGreenlet" Error**

**Symptom**: `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`

**Cause**: Accessing lazy-loaded relationships without `await`

**Solution**:
```python
# Bad
books = author.books  # MissingGreenlet error

# Good (eager loading)
stmt = select(Author).options(selectinload(Author.books))
author = await session.execute(stmt).scalar_one()
books = author.books

# Or (lazy loading)
books = await author.awaitable_attrs.books
```

**2. Migration Conflicts**

**Symptom**: `alembic.util.exc.CommandError: Multiple head revisions are present`

**Cause**: Conflicting migrations from multiple branches

**Solution**:
```bash
# View all heads
alembic heads

# Merge heads
alembic merge heads -m "Merge migration branches"
```

**3. Connection Pool Exhausted**

**Symptom**: `TimeoutError: QueuePool limit of size X overflow Y reached`

**Cause**: Not closing sessions or holding sessions too long

**Solution**:
```python
# Always use context managers
async with async_session() as session:
    # Your code here
    pass
# Session automatically closed here
```

**4. Slow Pagination on Large Tables**

**Symptom**: Slow API responses for paginated endpoints

**Cause**: Expensive `COUNT(*)` queries on large tables

**Solution**:
```python
# Enable count caching
results, meta = await get_paginated_results(
    Model,
    page=1,
    per_page=20
)  # Automatically uses Redis cache

# Or skip count for infinite scroll
results, meta = await get_paginated_results(
    Model,
    page=1,
    per_page=20,
    skip_count=True
)
```

### Diagnostic Queries

```sql
-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan AS index_scans,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Find unused indexes
SELECT
  schemaname,
  tablename,
  indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey';

-- Check active connections
SELECT
  state,
  COUNT(*)
FROM pg_stat_activity
GROUP BY state;
```

## Related Documentation

- [Database Migrations Guide](../../docs/DATABASE_MIGRATIONS.md) - Detailed migration workflow
- [Repository Pattern](./design-patterns.md) - Database access patterns
- [Performance Optimization](../guides/database.md) - Query optimization techniques
- [Docker Services](./docker-services.md) - PostgreSQL container configuration
- [Monitoring](../guides/monitoring.md) - Database metrics and alerting
