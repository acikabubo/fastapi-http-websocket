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


class BaseFilter(BaseModel):  # type: ignore[misc]
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
            >>> filters = AuthorFilters(name="John", id=None)
            >>> filters.to_dict()
            {'name': 'John'}
        """
        return {k: v for k, v in self.model_dump().items() if v is not None}

    model_config = {
        "extra": "forbid",  # Reject unexpected fields
    }


class AuthorFilters(BaseFilter):
    """
    Type-safe filters for Author model queries.

    All fields are optional and use OR logic when multiple filters provided.
    String filters use case-insensitive ILIKE pattern matching.

    Example:
        >>> # Filter by name (case-insensitive partial match)
        >>> filters = AuthorFilters(name="john")
        >>> authors, meta = await get_paginated_results(
        ...     Author, page=1, per_page=20, filters=filters
        ... )
        >>>
        >>> # Filter by exact ID
        >>> filters = AuthorFilters(id=42)
        >>> authors, meta = await get_paginated_results(
        ...     Author, page=1, per_page=20, filters=filters
        ... )
    """

    id: int | None = Field(
        default=None,
        description="Filter by exact author ID",
    )
    name: str | None = Field(
        default=None,
        description="Filter by author name (case-insensitive partial match)",
    )


class UserActionFilters(BaseFilter):
    """
    Type-safe filters for UserAction audit log queries.

    All fields are optional. String filters use case-insensitive ILIKE
    pattern matching. Datetime filters support range queries.

    Example:
        >>> # Filter by user and outcome
        >>> filters = UserActionFilters(username="john.doe", outcome="error")
        >>> actions, meta = await get_paginated_results(
        ...     UserAction, page=1, per_page=50, filters=filters
        ... )
        >>>
        >>> # Filter by timestamp range
        >>> filters = UserActionFilters(
        ...     timestamp_after=datetime(2025, 1, 1),
        ...     timestamp_before=datetime(2025, 1, 31),
        ... )
    """

    id: int | None = Field(
        default=None,
        description="Filter by exact audit log ID",
    )
    user_id: str | None = Field(
        default=None,
        description="Filter by Keycloak user ID",
    )
    username: str | None = Field(
        default=None,
        description="Filter by username (case-insensitive partial match)",
    )
    action_type: str | None = Field(
        default=None,
        description="Filter by action type (GET, POST, WS:*)",
    )
    resource: str | None = Field(
        default=None,
        description="Filter by resource path",
    )
    outcome: str | None = Field(
        default=None,
        description="Filter by outcome (success, error, permission_denied)",
    )
    ip_address: str | None = Field(
        default=None,
        description="Filter by client IP address",
    )
    request_id: str | None = Field(
        default=None,
        description="Filter by request correlation ID",
    )
    timestamp_after: datetime | None = Field(
        default=None,
        description="Filter actions after this timestamp (inclusive)",
    )
    timestamp_before: datetime | None = Field(
        default=None,
        description="Filter actions before this timestamp (inclusive)",
    )
