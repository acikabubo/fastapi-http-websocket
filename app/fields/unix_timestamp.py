"""
Custom SQLModel field for Unix timestamp handling.

This module provides a custom field type that stores datetime values as
Unix timestamps (BIGINT) in the database while maintaining datetime objects
in Python code for type safety and ease of use.

Benefits:
- Storage efficiency: 8 bytes (BIGINT) vs ~25 bytes (string)
- Performance: Fast integer comparisons for date range queries
- Type safety: Work with datetime objects in Python, not raw integers
- Index performance: Integer indexes are faster than timestamp indexes
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, TypeDecorator
from sqlmodel import Field


class UnixTimestampType(TypeDecorator):  # type: ignore[misc]
    """
    SQLAlchemy type decorator for Unix timestamps.

    Stores timestamps as BIGINT in the database but works with
    datetime objects in Python code. All datetimes are stored
    and retrieved in UTC.

    Example:
        Column definition in database: BIGINT
        Python value: datetime(2025, 12, 12, 10, 30, 0, tzinfo=timezone.utc)
        Database value: 1765615800
    """

    impl = BigInteger
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Any
    ) -> int | None:
        """
        Convert datetime to Unix timestamp when saving to database.

        Args:
            value: datetime object to convert (None allowed)
            dialect: SQLAlchemy dialect (unused)

        Returns:
            Unix timestamp in seconds, or None if value is None

        Note:
            If datetime is timezone-naive, UTC is assumed.
        """
        if value is None:
            return None

        # Ensure timezone-aware datetime (assume UTC if naive)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        # Convert to Unix timestamp (seconds since epoch)
        return int(value.timestamp())

    def process_result_value(
        self, value: int | None, dialect: Any
    ) -> datetime | None:
        """
        Convert Unix timestamp to datetime when loading from database.

        Args:
            value: Unix timestamp in seconds (None allowed)
            dialect: SQLAlchemy dialect (unused)

        Returns:
            UTC datetime object, or None if value is None
        """
        if value is None:
            return None

        # Convert from Unix timestamp to UTC datetime
        return datetime.fromtimestamp(value, tz=timezone.utc)


def UnixTimestampField(
    *,
    default: datetime | None = ...,  # type: ignore
    default_factory: Any | None = None,
    nullable: bool = False,
    index: bool = False,
    **kwargs: Any,
) -> datetime:
    """
    Create a Unix timestamp field for SQLModel.

    This field stores datetimes as Unix timestamps (BIGINT) in the database
    but provides datetime objects in Python code. The field automatically
    handles conversion between datetime and Unix timestamp.

    Args:
        default: Default datetime value (cannot be used with default_factory)
        default_factory: Callable that returns default datetime
            (e.g., lambda: datetime.now(timezone.utc))
        nullable: Whether the field can be NULL (default: False)
        index: Whether to create an index on this column (default: False)
        **kwargs: Additional Field arguments (description, etc.)

    Returns:
        A Field configured for Unix timestamp storage

    Example:
        Basic usage with default factory:
            created_at: datetime = UnixTimestampField(
                default_factory=lambda: datetime.now(timezone.utc)
            )

        Nullable field:
            updated_at: datetime | None = UnixTimestampField(
                default=None,
                nullable=True
            )

        With index for efficient queries:
            scheduled_at: datetime = UnixTimestampField(
                default_factory=lambda: datetime.now(timezone.utc),
                index=True,
                description="Scheduled execution time"
            )
    """
    # Build field kwargs conditionally to avoid default + default_factory conflict
    field_kwargs: dict[str, Any] = {
        "sa_type": UnixTimestampType(),
        "sa_column_kwargs": {
            "nullable": nullable,
            "index": index,
        },
        **kwargs,
    }

    # Only add default or default_factory, not both
    if default_factory is not None:
        field_kwargs["default_factory"] = default_factory
    elif default is not ...:  # type: ignore[comparison-overlap]
        field_kwargs["default"] = default

    return Field(**field_kwargs)
