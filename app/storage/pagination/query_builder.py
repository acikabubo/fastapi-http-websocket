"""
Shared query building utilities for pagination strategies.

Extracts filter conversion and query construction logic that is common across
all pagination strategies.
"""

from typing import Any, Callable, Type

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Select
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.logging import logger
from app.schemas.generic_typing import GenericSQLModelType


def convert_filters(
    filters: dict[str, Any] | PydanticBaseModel | None,
) -> dict[str, Any] | None:
    """
    Convert Pydantic filter model to dict or pass through dict filters.

    Args:
        filters: Either a dict (legacy), Pydantic BaseModel (type-safe),
                or None.

    Returns:
        Dictionary of filter key-value pairs with None values excluded,
        or None if no filters provided.

    Example:
        >>> from app.schemas.filters import AuthorFilters
        >>> filters = AuthorFilters(name="John", bio=None)
        >>> convert_filters(filters)
        {'name': 'John'}  # bio excluded because it's None
    """
    if filters is None:
        return None

    if isinstance(filters, PydanticBaseModel):
        # Type-safe Pydantic filter schema
        # Use to_dict() method if available (BaseFilter), else model_dump()
        if hasattr(filters, "to_dict"):
            return filters.to_dict()  # noqa: PGH003
        else:
            # Fallback for custom Pydantic models without to_dict()
            return {
                k: v for k, v in filters.model_dump().items() if v is not None
            }
    else:
        # Legacy dict filters
        return filters


def build_query(
    model: Type[GenericSQLModelType],
    filter_dict: dict[str, Any] | None,
    apply_filters: Callable[
        [Select, Type[GenericSQLModelType], dict[str, Any]], Select
    ]
    | None,
    eager_load: list[str] | None,
) -> Select:
    """
    Build SQLAlchemy Select query with filters and eager loading.

    This is the shared query construction logic used by all pagination
    strategies. The strategy then applies pagination-specific clauses
    (OFFSET/LIMIT or WHERE id > cursor).

    Args:
        model: The SQLModel class to query.
        filter_dict: Dictionary of filter key-value pairs. None values
                    are excluded by convert_filters().
        apply_filters: Optional custom filter function. If None, uses
                      default_apply_filters from app.storage.db.
        eager_load: List of relationship names to eager load (prevents
                   N+1 queries).

    Returns:
        SQLAlchemy Select query with filters and eager loading applied.

    Example:
        >>> from app.models.author import Author
        >>> from app.storage.db import default_apply_filters
        >>> query = build_query(
        ...     Author, {"name": "John"}, default_apply_filters, ["books"]
        ... )
        >>> # Query has filters and eager loading, ready for pagination
    """
    from app.storage.db import (  # Import here to avoid circular dependency
        default_apply_filters,
    )

    query: Select = select(model)

    # Apply eager loading for relationships (prevents N+1 queries)
    if eager_load:
        for relationship in eager_load:
            if hasattr(model, relationship):
                query = query.options(
                    selectinload(getattr(model, relationship))
                )
            else:
                logger.warning(
                    f"Relationship '{relationship}' not found on {model.__name__}"
                )

    # Apply filters
    if filter_dict:
        if apply_filters:
            query = apply_filters(query, model, filter_dict)
        else:
            query = default_apply_filters(query, model, filter_dict)

    return query
