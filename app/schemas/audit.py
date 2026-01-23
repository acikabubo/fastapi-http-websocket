"""
Pydantic schemas for audit log validation.

This module provides validation models for audit log entries to ensure
type safety and data integrity before persisting to the database.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.types import ActionType, AuditOutcome, RequestId, UserId, Username


class AuditLogInput(BaseModel):  # type: ignore[misc]
    """
    Pydantic model for validating audit log input parameters.

    This model provides automatic type validation and ensures required fields
    are present and have valid types before creating UserAction instances.
    """

    user_id: UserId = Field(..., description="Keycloak user ID (sub claim)")
    username: Username = Field(
        ..., description="Username (preferred_username claim)"
    )
    user_roles: list[str] = Field(
        ..., description="List of user roles at time of action"
    )
    action_type: ActionType | str = Field(
        ...,
        description="Type of action (HTTP method, WS, or WebSocket PkgID string)",
    )
    resource: str = Field(
        ..., description="Resource accessed (URL path or entity identifier)"
    )
    outcome: AuditOutcome = Field(
        ...,
        description="Result of the action (success, error, permission_denied)",
    )
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(
        None, description="Browser/client user agent string"
    )
    request_id: RequestId | None = Field(
        None, description="Request UUID for correlation"
    )
    request_data: dict[str, Any] | None = Field(
        None, description="Request payload (will be sanitized)"
    )
    response_status: int | None = Field(
        None, description="HTTP status code or WebSocket response code"
    )
    error_message: str | None = Field(
        None, description="Error details if action failed"
    )
    duration_ms: int | None = Field(
        None, description="Request processing duration in milliseconds"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of the action",
    )

    @field_validator(
        "user_id", "username", "action_type", "resource", "outcome"
    )
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: Any) -> str:
        """
        Validate that required string fields are not empty.

        Args:
            v: Field value to validate.
            info: Validation info containing field name.

        Returns:
            Validated string value.

        Raises:
            ValueError: If string is empty or contains only whitespace.
        """
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} cannot be empty")
        return v

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        """
        Validate that outcome is one of the allowed literal values.

        Args:
            v: Outcome value to validate.

        Returns:
            Validated outcome value.

        Raises:
            ValueError: If outcome is not a valid AuditOutcome literal.
        """
        valid_outcomes = {"success", "error", "permission_denied"}
        if v not in valid_outcomes:
            raise ValueError(
                f"outcome must be one of {valid_outcomes}, got '{v}'"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "abc-123-def",
                    "username": "john.doe",
                    "user_roles": ["user", "admin"],
                    "action_type": "POST",
                    "resource": "/api/authors",
                    "outcome": "success",
                    "ip_address": "192.168.1.100",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "response_status": 201,
                    "duration_ms": 45,
                }
            ]
        }
    }
