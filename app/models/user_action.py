"""User action audit logging model."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class UserAction(SQLModel, table=True):
    """
    Audit log model for tracking user actions across the application.

    This model captures comprehensive information about user activities
    for security, compliance, debugging, and analytics purposes.

    Attributes:
        id: Primary key identifier for the log entry
        timestamp: UTC timestamp when the action occurred
        user_id: Keycloak user ID (sub claim from JWT)
        username: Human-readable username (preferred_username from JWT)
        user_roles: List of roles the user had at time of action
        action_type: Type of action (HTTP method or WebSocket PkgID)
        resource: Resource that was accessed or modified
        outcome: Result of the action (success, error, permission_denied)
        ip_address: Client IP address (proxy-aware)
        user_agent: Browser/client user agent string
        request_id: UUID for request correlation
        request_data: Sanitized request payload (sensitive data redacted)
        response_status: HTTP status code or WebSocket response code
        error_message: Error details if the action failed
        duration_ms: Request processing duration in milliseconds
    """

    __tablename__ = "user_actions"
    __table_args__ = (
        # Composite index for common query pattern (user timeline)
        Index("idx_user_timestamp", "user_id", "timestamp"),
        # Composite index for action type filtering by user
        Index("idx_user_action", "user_id", "action_type"),
        {"extend_existing": True},
    )

    id: int | None = Field(default=None, primary_key=True)

    # Temporal information
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        description="UTC timestamp when the action occurred",
    )

    # User information
    user_id: str = Field(
        index=True,
        max_length=255,
        description="Keycloak user ID (sub claim)",
    )
    username: str = Field(
        index=True,
        max_length=255,
        description="Username (preferred_username claim)",
    )
    user_roles: list[str] = Field(
        sa_column=Column(JSON, nullable=False),
        description="User roles at time of action",
    )

    # Action details
    action_type: str = Field(
        index=True,
        max_length=100,
        description="HTTP method (GET, POST) or WebSocket PkgID",
    )
    resource: str = Field(
        max_length=500,
        description="Resource accessed (URL path or entity identifier)",
    )
    outcome: str = Field(
        index=True,
        max_length=50,
        description="Action outcome: success, error, permission_denied",
    )

    # Request context
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="Client IP address (IPv4 or IPv6)",
    )
    user_agent: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Browser/client user agent string",
    )
    request_id: str | None = Field(
        default=None,
        index=True,
        max_length=100,
        description="Request UUID for correlation",
    )

    # Optional details
    request_data: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Sanitized request payload",
    )
    response_status: int | None = Field(
        default=None,
        description="HTTP status code or WebSocket response code",
    )
    error_message: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Error details if action failed",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Request processing duration in milliseconds",
    )
