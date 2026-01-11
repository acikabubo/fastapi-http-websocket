"""
Type definitions and aliases for improved type safety.

This module defines domain-specific types using NewType for type-safe IDs
and Literal types for string constants. These types help prevent bugs by
catching type mismatches at type-check time.

Example:
    ```python
    from app.types import UserId, PkgId


    def get_user(user_id: UserId) -> User:
        # Type checker ensures only UserId is passed, not raw int
        ...


    def handle_package(pkg_id: PkgId) -> None:
        # Can't accidentally pass UserId here
        ...
    ```
"""

from typing import Literal, NewType

# Domain-specific ID types
# These prevent accidentally mixing different ID types
UserId = NewType("UserId", str)
"""Type-safe user ID (Keycloak sub claim)."""

Username = NewType("Username", str)
"""Type-safe username (Keycloak preferred_username claim)."""

RequestId = NewType("RequestId", str)
"""Type-safe request correlation ID (UUID string)."""

# Note: PkgId is already defined as IntEnum in app/api/ws/constants.py
# We don't redefine it here to avoid conflicts. Use the enum directly.

# Audit outcome types
AuditOutcome = Literal["success", "error", "permission_denied"]
"""Valid outcomes for audit log entries."""

# Action types for audit logging
ActionType = Literal[
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "WS",  # WebSocket actions
]
"""Valid HTTP methods and WebSocket action types."""
