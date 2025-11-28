# Development Patterns & Best Practices

This document provides recommended patterns and best practices for developing applications generated from this cookiecutter template.

## Table of Contents

- [Database Session Management](#database-session-management)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Testing Patterns](#testing-patterns)
- [Security Best Practices](#security-best-practices)

---

## Database Session Management

### Overview

**IMPORTANT**: Model methods should accept database sessions as parameters rather than creating their own sessions. This pattern provides:

- ✅ Multiple operations in a single transaction
- ✅ Easier testing with mocked sessions
- ✅ Better transaction control and explicit session management
- ✅ Prevention of nested transaction issues
- ✅ Clearer code flow and dependencies

### Pattern for Model Methods

Always pass the database session as the **first parameter** after `cls` in class methods:

```python
from typing import Optional
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from {{cookiecutter.module_name}}.logging import logger


class MyModel(SQLModel, table=True):
    """Example model following session management best practices."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    status: str = "active"

    @classmethod
    async def create(
        cls, session: AsyncSession, instance: "MyModel"
    ) -> "MyModel":
        """
        Creates a new instance in the database.

        Args:
            session: Database session to use for the operation.
            instance: The instance to create.

        Returns:
            The created instance with populated ID.

        Raises:
            IntegrityError: If database constraints are violated.
            SQLAlchemyError: For other database errors.
        """
        try:
            session.add(instance)
            await session.flush()  # Flush to get ID without committing
            await session.refresh(instance)
            return instance
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Integrity error creating {cls.__name__}: {e}")
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error creating {cls.__name__}: {e}")
            raise

    @classmethod
    async def get_by_id(
        cls, session: AsyncSession, model_id: int
    ) -> Optional["MyModel"]:
        """
        Retrieves a single instance by ID.

        Args:
            session: Database session to use for the operation.
            model_id: The ID of the instance to retrieve.

        Returns:
            The model instance if found, None otherwise.

        Raises:
            SQLAlchemyError: For database errors.
        """
        try:
            stmt = select(cls).where(cls.id == model_id)
            result = await session.exec(stmt)
            return result.first()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving {cls.__name__}: {e}")
            raise

    @classmethod
    async def get_list(
        cls, session: AsyncSession, **filters
    ) -> list["MyModel"]:
        """
        Retrieves a list of instances based on filters.

        Args:
            session: Database session to use for the operation.
            **filters: Filter criteria as field=value pairs.

        Returns:
            List of model instances matching the filters.

        Raises:
            SQLAlchemyError: For database errors.
        """
        try:
            stmt = select(cls).where(
                *[getattr(cls, k) == v for k, v in filters.items()]
            )
            result = await session.exec(stmt)
            return result.all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving {cls.__name__}: {e}")
            raise

    @classmethod
    async def update(
        cls, session: AsyncSession, model_id: int, updates: dict
    ) -> Optional["MyModel"]:
        """
        Updates an instance with new values.

        Args:
            session: Database session to use for the operation.
            model_id: The ID of the instance to update.
            updates: Dictionary of field names and new values.

        Returns:
            The updated instance if found, None otherwise.

        Raises:
            SQLAlchemyError: For database errors.
        """
        try:
            instance = await cls.get_by_id(session, model_id)
            if not instance:
                return None

            for key, value in updates.items():
                setattr(instance, key, value)

            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error updating {cls.__name__}: {e}")
            raise

    @classmethod
    async def delete(
        cls, session: AsyncSession, model_id: int
    ) -> bool:
        """
        Deletes an instance by ID.

        Args:
            session: Database session to use for the operation.
            model_id: The ID of the instance to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SQLAlchemyError: For database errors.
        """
        try:
            instance = await cls.get_by_id(session, model_id)
            if not instance:
                return False

            await session.delete(instance)
            await session.flush()
            return True
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error deleting {cls.__name__}: {e}")
            raise
```

### Usage in HTTP Endpoints

HTTP endpoints should manage the session lifecycle using context managers:

```python
from fastapi import APIRouter, HTTPException, status
from {{cookiecutter.module_name}}.storage.db import async_session
from {{cookiecutter.module_name}}.models.my_model import MyModel

router = APIRouter()


@router.post("/my-models", summary="Create new model")
async def create_model(instance: MyModel) -> MyModel:
    """
    Creates a new model instance.

    The session.begin() context manager handles transaction commit/rollback.
    """
    async with async_session() as session:
        async with session.begin():
            return await MyModel.create(session, instance)


@router.get("/my-models/{model_id}", summary="Get model by ID")
async def get_model(model_id: int) -> MyModel:
    """Retrieves a single model by ID."""
    async with async_session() as session:
        instance = await MyModel.get_by_id(session, model_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        return instance


@router.get("/my-models", summary="Get list of models")
async def get_models(status: str = "active") -> list[MyModel]:
    """Retrieves list of models filtered by status."""
    async with async_session() as session:
        return await MyModel.get_list(session, status=status)


@router.patch("/my-models/{model_id}", summary="Update model")
async def update_model(model_id: int, updates: dict) -> MyModel:
    """Updates a model instance."""
    async with async_session() as session:
        async with session.begin():
            instance = await MyModel.update(session, model_id, updates)
            if not instance:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model {model_id} not found"
                )
            return instance


@router.delete("/my-models/{model_id}", summary="Delete model")
async def delete_model(model_id: int) -> dict:
    """Deletes a model instance."""
    async with async_session() as session:
        async with session.begin():
            deleted = await MyModel.delete(session, model_id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model {model_id} not found"
                )
            return {"status": "deleted", "id": model_id}
```

### Usage in WebSocket Handlers

WebSocket handlers follow the same pattern:

```python
from {{cookiecutter.module_name}}.api.ws.constants import PkgID, RSPCode
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import ResponseModel
from {{cookiecutter.module_name}}.storage.db import async_session
from {{cookiecutter.module_name}}.models.my_model import MyModel
from {{cookiecutter.module_name}}.logging import logger
from sqlalchemy.exc import SQLAlchemyError


@pkg_router.register(PkgID.GET_MY_MODELS, json_schema=MyFiltersSchema)
async def get_models_handler(request: RequestModel) -> ResponseModel:
    """
    Handles request to get list of models.

    Args:
        request: The WebSocket request containing filters.

    Returns:
        ResponseModel with list of models or error message.
    """
    try:
        filters = request.data.get("filters", {})

        async with async_session() as session:
            items = await MyModel.get_list(session, **filters)

        return ResponseModel.ok_msg(
            request.pkg_id,
            request.req_id,
            data=[item.model_dump() for item in items]
        )
    except SQLAlchemyError as ex:
        logger.error(f"Database error retrieving models: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Database error occurred",
            status_code=RSPCode.ERROR
        )


@pkg_router.register(PkgID.CREATE_MY_MODEL, json_schema=CreateModelSchema)
async def create_model_handler(request: RequestModel) -> ResponseModel:
    """
    Handles request to create a new model.

    Args:
        request: The WebSocket request containing model data.

    Returns:
        ResponseModel with created model or error message.
    """
    try:
        model_data = request.data

        async with async_session() as session:
            async with session.begin():
                instance = MyModel(**model_data)
                created = await MyModel.create(session, instance)

        return ResponseModel.ok_msg(
            request.pkg_id,
            request.req_id,
            data=created.model_dump()
        )
    except SQLAlchemyError as ex:
        logger.error(f"Database error creating model: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Failed to create model",
            status_code=RSPCode.ERROR
        )
```

### Multiple Operations in Single Transaction

One of the key benefits of passing sessions is the ability to perform multiple operations atomically:

```python
@router.post("/complex-operation")
async def complex_operation(data: ComplexData):
    """
    Performs multiple related database operations in a single transaction.

    If any operation fails, the entire transaction is rolled back.
    """
    async with async_session() as session:
        async with session.begin():
            # All operations share the same session and transaction
            user = await User.create(session, data.user)
            profile = await Profile.create(
                session, Profile(user_id=user.id, **data.profile)
            )
            settings = await Settings.create(
                session, Settings(user_id=user.id, **data.settings)
            )

            # Update user with profile reference
            await User.update(session, user.id, {"profile_id": profile.id})

            # If we reach here, all operations succeeded
            # The transaction will commit when exiting the context
            return {
                "user": user.model_dump(),
                "profile": profile.model_dump(),
                "settings": settings.model_dump()
            }
```

### Testing with Session Management

The session-as-parameter pattern makes testing much easier:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from {{cookiecutter.module_name}}.models.my_model import MyModel


@pytest.mark.asyncio
async def test_create_model_success():
    """Test successful model creation."""
    # Create a mock session
    mock_session = AsyncMock()

    # Create test instance
    instance = MyModel(name="Test", status="active")

    # Call the method with mocked session
    result = await MyModel.create(mock_session, instance)

    # Verify session methods were called correctly
    mock_session.add.assert_called_once_with(instance)
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once_with(instance)

    # Verify result
    assert result == instance


@pytest.mark.asyncio
async def test_create_model_integrity_error():
    """Test model creation with integrity error."""
    from sqlalchemy.exc import IntegrityError

    mock_session = AsyncMock()
    mock_session.flush.side_effect = IntegrityError(
        "duplicate key", {}, None
    )

    instance = MyModel(name="Duplicate", status="active")

    with pytest.raises(IntegrityError):
        await MyModel.create(mock_session, instance)

    # Verify rollback was called
    mock_session.rollback.assert_called_once()
```

### Anti-Patterns to Avoid

❌ **DON'T create sessions inside model methods:**

```python
# BAD: Hard to test, prevents transaction management
class MyModel(SQLModel, table=True):
    @classmethod
    async def create(cls, instance: "MyModel"):
        async with async_session() as session:  # ❌ Session created here
            async with session.begin():
                session.add(instance)
            return instance
```

❌ **DON'T use global sessions:**

```python
# BAD: Thread-unsafe, prevents proper cleanup
global_session = None  # ❌ Global state

async def create_model(instance):
    global global_session
    global_session.add(instance)
```

✅ **DO pass sessions as parameters:**

```python
# GOOD: Testable, flexible, explicit
class MyModel(SQLModel, table=True):
    @classmethod
    async def create(cls, session: AsyncSession, instance: "MyModel"):
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance
```

---

## Rate Limiting

### Overview

The application includes comprehensive rate limiting for both HTTP and WebSocket connections using Redis-based sliding window algorithm. This prevents abuse and ensures fair resource allocation.

### Components

**RateLimiter** (`{{cookiecutter.module_name}}.utils.rate_limiter`):
- Tracks request counts per user/IP within configurable time windows
- Uses Redis sorted sets for efficient sliding window implementation
- Supports burst limits for short-term traffic spikes
- Fails open on Redis errors (allows requests)

**ConnectionLimiter** (`{{cookiecutter.module_name}}.utils.rate_limiter`):
- Manages WebSocket connection limits per user
- Uses Redis sets to track active connections
- Automatic cleanup with expiration

**RateLimitMiddleware** (`{{cookiecutter.module_name}}.middlewares.rate_limit`):
- HTTP middleware for request rate limiting
- Returns 429 Too Many Requests when limits exceeded
- Adds X-RateLimit-* headers to responses
- Uses user ID (authenticated) or IP address (unauthenticated)

### Configuration

Rate limiting settings in `settings.py`:

```python
# Rate limiting settings
RATE_LIMIT_ENABLED: bool = True
RATE_LIMIT_PER_MINUTE: int = 60
RATE_LIMIT_BURST: int = 10

# WebSocket rate limiting settings
WS_MAX_CONNECTIONS_PER_USER: int = 5
WS_MESSAGE_RATE_LIMIT: int = 100  # messages per minute
```

### HTTP Rate Limiting

The `RateLimitMiddleware` is automatically registered in the application:

```python
# In {{cookiecutter.module_name}}/__init__.py
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PermAuthHTTPMiddleware, rbac=RBACManager())
app.add_middleware(AuthenticationMiddleware, backend=AuthBackend())
```

Middleware execution order (reverse of registration):
1. `AuthenticationMiddleware` - Authenticates user
2. `PermAuthHTTPMiddleware` - Checks permissions
3. `RateLimitMiddleware` - Enforces rate limits

### WebSocket Rate Limiting

#### Connection Limiting

WebSocket connection limits are enforced in `PackageAuthWebSocketEndpoint.on_connect()`:

```python
from {{cookiecutter.module_name}}.utils.rate_limiter import connection_limiter

async def on_connect(self, websocket):
    # Generate unique connection ID
    self.connection_id = str(uuid.uuid4())

    # Check connection limit
    connection_allowed = await connection_limiter.add_connection(
        user_id=self.user.username,
        connection_id=self.connection_id
    )

    if not connection_allowed:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Maximum concurrent connections exceeded"
        )
        return
```

Cleanup on disconnect:

```python
async def on_disconnect(self, websocket, close_code):
    if hasattr(self, "connection_id"):
        await connection_limiter.remove_connection(
            user_id=self.user.username,
            connection_id=self.connection_id
        )
```

#### Message Rate Limiting

WebSocket message limits are enforced in `Web.on_receive()`:

```python
from {{cookiecutter.module_name}}.utils.rate_limiter import rate_limiter
from {{cookiecutter.module_name}}.settings import app_settings

async def on_receive(self, websocket, data):
    # Check message rate limit
    rate_limit_key = f"ws_msg:user:{self.user.username}"
    is_allowed, remaining = await rate_limiter.check_rate_limit(
        key=rate_limit_key,
        limit=app_settings.WS_MESSAGE_RATE_LIMIT,
        window_seconds=60,
    )

    if not is_allowed:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Message rate limit exceeded"
        )
        return
```

### Custom Rate Limiting

You can use the rate limiter directly in your code:

```python
from {{cookiecutter.module_name}}.utils.rate_limiter import rate_limiter

# Check custom rate limit
is_allowed, remaining = await rate_limiter.check_rate_limit(
    key=f"custom:{user_id}:{operation}",
    limit=10,  # 10 requests
    window_seconds=60,  # per minute
    burst=15  # allow burst up to 15
)

if not is_allowed:
    raise HTTPException(
        status_code=429,
        detail="Rate limit exceeded"
    )
```

### Testing Rate Limiting

Example test with mocked Redis:

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def rate_limiter_with_mock_redis():
    from {{cookiecutter.module_name}}.utils.rate_limiter import RateLimiter

    with patch("{{cookiecutter.module_name}}.utils.rate_limiter.RRedis") as mock_rredis:
        mock_redis = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=5)

        mock_instance = MagicMock()
        mock_instance.r = mock_redis
        mock_rredis.return_value = mock_instance

        limiter = RateLimiter()
        limiter.redis.r = mock_redis

        yield limiter

@pytest.mark.asyncio
async def test_rate_limit_allows_request(rate_limiter_with_mock_redis):
    is_allowed, remaining = await rate_limiter_with_mock_redis.check_rate_limit(
        key="test_user",
        limit=10,
        window_seconds=60
    )

    assert is_allowed is True
    assert remaining == 4
```

### Best Practices

1. **Choose Appropriate Limits**: Balance between preventing abuse and allowing legitimate usage
2. **Use Burst Limits**: Allow short-term traffic spikes with `burst` parameter
3. **Monitor Rate Limit Hits**: Log rate limit violations for security monitoring
4. **Test with Realistic Traffic**: Ensure limits work under actual usage patterns
5. **Document Limits**: Inform API consumers about rate limits in documentation
6. **Graceful Degradation**: Always fail open on infrastructure errors

---

## Error Handling

_(To be added)_

---

## Testing Patterns

_(To be added)_

---

## Security Best Practices

_(To be added)_

---

*This document is maintained as part of the cookiecutter template. Add new patterns and best practices as they emerge from real-world usage.*
