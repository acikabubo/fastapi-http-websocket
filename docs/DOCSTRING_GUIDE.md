# Docstring Style Guide

## Overview

This project uses **Google-style docstrings** for all Python code. This provides a consistent, readable format that integrates well with documentation tools like Sphinx and IDE tooltips.

## Requirements

- **Coverage**: Minimum 80% docstring coverage (enforced by `interrogate`)
- **Style**: Google-style format
- **Language**: Clear, concise English
- **Type Hints**: Required (don't duplicate in docstrings)
- **Examples**: Include for complex functions/classes

## Google-Style Format

### Module Docstring

Every module (`.py` file) should start with a module-level docstring:

```python
"""
Short one-line description of the module.

More detailed description if needed. Can span multiple lines.
Explain the purpose, main classes/functions, and usage patterns.
"""

import statements...
```

**Example**:
```python
"""
Redis-based rate limiter using sliding window algorithm.

This module provides rate limiting functionality for both HTTP and WebSocket
connections using Redis as the backend storage.
"""

import time
from app.storage.redis import get_redis_connection
```

### Class Docstring

Classes should have docstrings describing their purpose and main attributes:

```python
class ClassName:
    """
    Short description of the class.

    Longer description if needed, explaining purpose, behavior,
    and important design decisions.

    Attributes:
        attribute_name: Description of the attribute.
        another_attr: Description of another attribute.
    """

    def __init__(self, param: str):
        """Initialize with description of what init does."""
        self.attribute_name = param
```

**Example**:
```python
class Author(SQLModel, table=True):
    """
    SQLModel representing an author entity in the database.

    Attributes:
        id: Primary key identifier for the author.
        name: Name of the author.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
```

### Function/Method Docstring

Functions and methods use the most detailed format:

```python
def function_name(arg1: str, arg2: int | None = None) -> bool:
    """
    Short description of what the function does.

    More detailed description if needed. Explain the algorithm,
    behavior, or important notes about usage.

    Args:
        arg1: Description of the first argument.
        arg2: Description of the second argument (optional).
            Can span multiple lines with indentation.

    Returns:
        Description of the return value. Explain what it represents
        and any important details.

    Raises:
        ExceptionType: Description of when this exception is raised.
        AnotherException: Description of another exception.

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        True

    Note:
        Important notes about behavior, caveats, or warnings.
    """
    # Implementation
    pass
```

**Real Example**:
```python
async def check_rate_limit(
    self,
    key: str,
    limit: int,
    window_seconds: int = 60,
    burst: int | None = None,
) -> tuple[bool, int]:
    """
    Check if a request is within rate limits using sliding window.

    Args:
        key: Unique identifier for the rate limit (e.g., user_id, IP).
        limit: Maximum number of requests allowed in the window.
        window_seconds: Time window in seconds (default: 60).
        burst: Optional burst limit for short-term spikes.

    Returns:
        Tuple of (is_allowed, remaining_requests).

    Raises:
        Exception: If Redis connection fails.
    """
    # Implementation...
```

## Sections

### Required Sections

**For all functions/methods**:
- Short description (one line)
- `Args` (if function has parameters)
- `Returns` (if function returns a value)

**When applicable**:
- `Raises` (if function can raise exceptions)
- Longer description (if behavior is complex)

### Optional Sections

Use when helpful:

- `Example`: Code examples showing usage
- `Note`: Important caveats or warnings
- `Warning`: Critical information about misuse
- `See Also`: Links to related functions/classes
- `Todo`: Planned improvements (use sparingly)

## Guidelines

### 1. Be Concise but Clear

**Good**:
```python
def get_user(user_id: int) -> User:
    """
    Retrieves a user by ID from the database.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        User object if found.

    Raises:
        UserNotFoundError: If user doesn't exist.
    """
```

**Too Verbose**:
```python
def get_user(user_id: int) -> User:
    """
    This function retrieves a user from the database by looking up
    their unique identifier. It will search through the database
    to find the user and return the user object if successful.

    Args:
        user_id: This is the unique identifier that is assigned to
            each user in the system and can be used to look them up.

    Returns:
        This returns a User object which contains all the information
        about the user including their name, email, and other attributes.
    """
```

### 2. Don't Duplicate Type Hints

Type hints are already in the signature, so don't repeat them:

**Good**:
```python
def process_data(items: list[str], count: int) -> dict[str, int]:
    """
    Process items and return frequency count.

    Args:
        items: List of strings to process.
        count: Maximum items to process.

    Returns:
        Mapping of item to frequency.
    """
```

**Bad** (redundant type information):
```python
def process_data(items: list[str], count: int) -> dict[str, int]:
    """
    Process items and return frequency count.

    Args:
        items (list[str]): List of strings to process.
        count (int): Maximum items to process.

    Returns:
        dict[str, int]: Mapping of item to frequency.
    """
```

### 3. Document Exceptions Meaningfully

Only document exceptions that callers need to handle:

**Good**:
```python
async def create_author(session: AsyncSession, author: Author) -> Author:
    """
    Creates a new author in the database.

    Args:
        session: Database session to use for the operation.
        author: The author instance to create.

    Returns:
        The created author instance.

    Raises:
        IntegrityError: If the author violates database constraints.
        SQLAlchemyError: For other database-related errors.
    """
```

**Unnecessary** (documenting framework exceptions):
```python
def get_value(key: str) -> str:
    """
    Get configuration value.

    Raises:
        KeyError: If dictionary key doesn't exist.
        TypeError: If key is not a string.
        AttributeError: If dict has no __getitem__.
    """
    return config[key]  # Caller knows dict can raise KeyError
```

### 4. Use Examples for Complex Functions

```python
async def get_paginated_results(
    model: Type[GenericSQLModelType],
    page: int = 1,
    per_page: int = 20,
    *,
    filters: dict[str, Any] | None = None,
) -> tuple[list[GenericSQLModelType], MetadataModel]:
    """
    Get paginated results from a SQLModel query.

    Args:
        model: The SQLModel class to query.
        page: The page number to retrieve (starts at 1).
        per_page: Number of results per page.
        filters: Optional dictionary of filters to apply.

    Returns:
        Tuple of (results list, pagination metadata).

    Example:
        >>> results, meta = await get_paginated_results(
        ...     Author,
        ...     page=2,
        ...     per_page=10,
        ...     filters={"status": "active"}
        ... )
        >>> print(meta.total)
        42
        >>> print(len(results))
        10
    """
```

### 5. Property Docstrings

Properties should have simple docstrings:

```python
@property
def is_expired(self) -> bool:
    """Check if the token has expired."""
    return datetime.now() > self.expiry_time

@property
def full_name(self) -> str:
    """Get user's full name combining first and last name."""
    return f"{self.first_name} {self.last_name}"
```

### 6. Private Methods

Private methods (starting with `_`) should still have docstrings:

```python
async def _get_redis(self):
    """Get or create Redis connection."""
    if self.redis is None:
        self.redis = await get_redis_connection()
    return self.redis
```

### 7. Special Methods

Special methods like `__init__`, `__str__`, etc. need docstrings:

```python
def __init__(self, name: str, email: str):
    """
    Initialize user instance.

    Args:
        name: User's full name.
        email: User's email address.
    """
    self.name = name
    self.email = email

def __str__(self) -> str:
    """Return string representation of user."""
    return f"User({self.name}, {self.email})"
```

## Common Patterns

### Async Functions

No special docstring format needed, just describe async behavior if relevant:

```python
async def fetch_data(url: str) -> dict[str, Any]:
    """
    Fetch data from URL asynchronously.

    Args:
        url: The URL to fetch data from.

    Returns:
        Parsed JSON response as dictionary.

    Raises:
        HTTPError: If request fails.
    """
```

### Context Managers

```python
@contextmanager
def database_session():
    """
    Provide a database session context manager.

    Yields:
        Database session that auto-commits on success
        and rolls back on exception.

    Example:
        >>> with database_session() as session:
        ...     user = session.query(User).first()
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### Decorators

```python
def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for endpoint.

    Args:
        func: The endpoint function to decorate.

    Returns:
        Wrapped function that checks authentication.

    Example:
        >>> @require_auth
        ... async def get_profile(request: Request):
        ...     return request.user.profile
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check auth...
        return await func(*args, **kwargs)
    return wrapper
```

### Class Methods

```python
@classmethod
async def create(cls, session: AsyncSession, instance: "Author") -> "Author":
    """
    Creates a new instance in the database.

    Args:
        session: Database session to use.
        instance: The instance to create.

    Returns:
        The created instance with ID populated.
    """
```

## Tools and Validation

### Interrogate

Check docstring coverage:

```bash
# Check coverage (must be >= 80%)
uvx interrogate app/

# Show missing docstrings
uvx interrogate -v app/
```

### Configuration

In `pyproject.toml`:

```toml
[tool.interrogate]
ignore-init-method = true
ignore-init-module = false
ignore-magic = false
ignore-private = false
ignore-property-decorators = false
fail-under = 80
exclude = ["tests", "docs", ".venv"]
verbose = 1
```

### Pre-commit Hook

Runs automatically on commit to enforce coverage:

```yaml
- repo: local
  hooks:
    - id: interrogate
      name: interrogate
      entry: interrogate
      args: [-vv, --fail-under=80, app/]
      language: system
      pass_filenames: false
```

## Examples from Codebase

### Well-Documented Module

`app/utils/rate_limiter.py`:
```python
"""
Redis-based rate limiter using sliding window algorithm.

This module provides rate limiting functionality for both HTTP and WebSocket
connections using Redis as the backend storage.
"""
```

### Well-Documented Class

`app/models/author.py`:
```python
class Author(SQLModel, table=True):
    """
    SQLModel representing an author entity in the database.

    Attributes:
        id: Primary key identifier for the author.
        name: Name of the author.
    """
```

### Well-Documented Function

`app/storage/db.py`:
```python
async def get_paginated_results(
    model: Type[GenericSQLModelType],
    page: int = 1,
    per_page: int = 20,
    *,
    filters: dict[str, Any] | None = None,
) -> tuple[list[GenericSQLModelType], MetadataModel]:
    """
    Get paginated results from a SQLModel query with optional filters.

    This function executes a SQLModel query, applies any provided filters,
    and returns the paginated results along with metadata about the query.

    Args:
        model: The SQLModel class to query.
        page: The page number to retrieve (starts at 1).
        per_page: Number of results to return per page.
        filters: Optional dictionary of filters to apply to the query.

    Returns:
        Tuple containing the list of results and a MetadataModel instance
        with pagination metadata.
    """
```

## Resources

- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Sphinx Napoleon Extension](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [interrogate Documentation](https://interrogate.readthedocs.io/)

## Summary

**Key Rules**:
1. All public modules, classes, functions need docstrings
2. Use Google-style format (Args, Returns, Raises)
3. Be concise but clear
4. Don't duplicate type hints
5. Include examples for complex functionality
6. Minimum 80% coverage enforced by pre-commit
