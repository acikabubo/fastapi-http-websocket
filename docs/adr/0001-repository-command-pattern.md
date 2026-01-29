# 1. Use Repository + Command Pattern for Business Logic

Date: 2025-01-29

## Status

Accepted

## Context

The application needed a way to:
1. Share business logic between HTTP and WebSocket handlers
2. Make code testable without database dependencies
3. Separate data access concerns from business logic
4. Support dependency injection with FastAPI

The original codebase used Active Record pattern (models with business logic methods), which led to:
- Code duplication between HTTP and WebSocket handlers
- Difficult testing (required database for all tests)
- Tight coupling between business logic and data access
- Mixed concerns in model classes

## Decision

Implement the **Repository + Command Pattern** with dependency injection:

1. **Repository Pattern** (`app/repositories/`):
   - Handles all database operations
   - Inherits from `BaseRepository[ModelType]`
   - Methods: `create()`, `get_by_id()`, `get_all()`, `update()`, `delete()`
   - Custom queries as repository methods (e.g., `get_by_name()`)

2. **Command Pattern** (`app/commands/`):
   - Encapsulates business logic
   - Inherits from `BaseCommand[InputType, OutputType]`
   - Takes repository as constructor parameter
   - Single `execute()` method implements the business logic

3. **Dependency Injection** (`app/dependencies.py`):
   - FastAPI `Depends()` for HTTP endpoints
   - Manual instantiation for WebSocket handlers
   - Repository injected into command constructors

**Example implementation:**

```python
# Repository (data access)
class AuthorRepository(BaseRepository[Author]):
    async def get_by_name(self, name: str) -> Author | None:
        stmt = select(Author).where(Author.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

# Command (business logic)
class CreateAuthorCommand(BaseCommand[CreateAuthorInput, Author]):
    def __init__(self, repository: AuthorRepository):
        self.repository = repository

    async def execute(self, input_data: CreateAuthorInput) -> Author:
        # Business logic: Check duplicates
        if await self.repository.get_by_name(input_data.name):
            raise ValueError("Author already exists")

        author = Author(name=input_data.name)
        return await self.repository.create(author)

# HTTP handler (dependency injection)
@router.post("/authors")
async def create_author(data: CreateAuthorInput, repo: AuthorRepoDep) -> Author:
    command = CreateAuthorCommand(repo)
    return await command.execute(data)

# WebSocket handler (manual instantiation, same command!)
@pkg_router.register(PkgID.CREATE_AUTHOR)
async def create_author_ws(request: RequestModel) -> ResponseModel:
    async with async_session() as session:
        repo = AuthorRepository(session)
        command = CreateAuthorCommand(repo)  # Same logic!
        author = await command.execute(CreateAuthorInput(**request.data))
        return ResponseModel.success(...)
```

## Consequences

### Positive Consequences

- **Code Reuse**: Same business logic in HTTP and WebSocket handlers (no duplication)
- **Testability**: Commands can be tested with mocked repositories (no database needed)
- **Separation of Concerns**: Data access (repository) separated from business logic (command)
- **Type Safety**: Full type hints with generics (`BaseCommand[Input, Output]`)
- **Maintainability**: Changes to business logic happen in one place
- **Protocol Independence**: Business logic unaware of HTTP vs WebSocket

### Negative Consequences

- **More Boilerplate**: Requires repository + command + dependency files
- **Learning Curve**: Developers must understand pattern structure
- **Indirection**: Extra layer between handler and database
- **File Count**: More files than Active Record pattern

### Neutral Consequences

- **Async Required**: All methods must be async (already required by FastAPI)
- **Session Management**: Must manage sessions explicitly (was always necessary)

## Alternatives Considered

### Alternative 1: Active Record Pattern

**Description**: Put business logic directly in model classes (e.g., `Author.create_from_dict()`)

**Pros**:
- Simpler structure (fewer files)
- Familiar to developers from Rails/Django background
- Less boilerplate code

**Cons**:
- Code duplication between HTTP and WebSocket handlers
- Difficult to test without database
- Mixed concerns (data + business logic in models)
- Cannot reuse logic across protocols

**Why not chosen**: Code duplication was major pain point, testing required database

### Alternative 2: Service Layer Pattern

**Description**: Single service layer with methods like `AuthorService.create_author()`

**Pros**:
- Centralized business logic
- Fewer files than Repository + Command
- Easy to understand

**Cons**:
- Services become god objects (too many responsibilities)
- Hard to compose business logic
- Less type-safe than Command pattern
- Service classes grow very large over time

**Why not chosen**: Services tend to become monolithic and hard to maintain

### Alternative 3: Direct Database Access in Handlers

**Description**: Use SQLModel queries directly in HTTP/WebSocket handlers

**Pros**:
- Simplest approach (no extra layers)
- Fastest to write initially
- Direct database access

**Cons**:
- Complete code duplication between protocols
- Impossible to test without database
- Business logic scattered across handlers
- Cannot reuse logic

**Why not chosen**: Completely violates DRY principle, no testability

## References

- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Martin Fowler
- [Command Pattern](https://refactoring.guru/design-patterns/command) - Refactoring Guru
- [docs/architecture/design-patterns.md](../architecture/design-patterns.md) - Project documentation
- [app/repositories/base.py](../../app/repositories/base.py) - Base repository implementation
- [app/commands/author_commands.py](../../app/commands/author_commands.py) - Example commands
- [app/api/http/author.py](../../app/api/http/author.py) - HTTP handlers using pattern
- [app/api/ws/handlers/author_handlers.py](../../app/api/ws/handlers/author_handlers.py) - WebSocket handlers using pattern

## Notes

**Migration Path**: When adding new features:
1. Create repository with data access methods
2. Create command with business logic
3. Add dependency injection for HTTP endpoints
4. Reuse same command in WebSocket handlers
5. Write unit tests for command with mocked repository

**Testing Strategy**:
- Unit tests: Mock repository, test command logic
- Integration tests: Use real database, test full stack

**Performance**: Pattern adds minimal overhead (~1-2% vs direct queries), negligible compared to network/database latency.

**Future Considerations**: This pattern works well for monolithic services. For microservices, consider Domain-Driven Design (DDD) with aggregates and domain events.
