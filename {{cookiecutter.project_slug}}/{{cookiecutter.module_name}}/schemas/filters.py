"""
Type-safe filter schemas for pagination queries.

This module provides Pydantic models for validating filter parameters
in paginated queries, ensuring type safety and preventing runtime errors
from invalid filter keys.

Key benefits:
- Compile-time safety with IDE autocomplete
- Runtime validation via Pydantic
- Self-documenting filter options
- Security via whitelisted filter fields
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BaseFilter(BaseModel):
    """
    Base class for all filter schemas.

    Provides common utilities for converting filters to dictionaries
    and excluding None values.
    """

    def to_dict(self) -> dict[str, Any]:
        """
        Convert filter schema to dictionary, excluding None values.

        Returns:
            Dictionary of non-None filter values ready for database queries.

        Example:
            >>> filters = MyFilters(name="John", id=None)
            >>> filters.to_dict()
            {'name': 'John'}
        """
        return {k: v for k, v in self.model_dump().items() if v is not None}

    model_config = {
        "extra": "forbid",  # Reject unexpected fields
    }


# Example filter schema - customize for your models
class ExampleFilters(BaseFilter):
    """
    Type-safe filters for example model queries.

    All fields are optional and use OR logic when multiple filters provided.
    String filters use case-insensitive ILIKE pattern matching.

    Example:
        >>> # Filter by name (case-insensitive partial match)
        >>> filters = ExampleFilters(name="john")
        >>> results, meta = await get_paginated_results(
        ...     MyModel, page=1, per_page=20, filters=filters
        ... )
    """

    id: int | None = Field(
        default=None,
        description="Filter by exact ID",
    )
    name: str | None = Field(
        default=None,
        description="Filter by name (case-insensitive partial match)",
    )
    created_after: datetime | None = Field(
        default=None,
        description="Filter by creation date (after this timestamp)",
    )
