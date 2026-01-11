"""
TypedDict definitions for structured dictionaries.

TypedDict provides type safety for dictionary structures without the overhead
of creating full Pydantic models. Use these for internal data structures,
function parameters, and return types where dict is currently used.

Example:
    ```python
    from {{cookiecutter.module_name}}.schemas.types import FilterDict, PaginationParams


    def search_authors(params: PaginationParams) -> list[Author]:
        # Type checker ensures params has correct structure
        page = params["page"]
        filters = params.get("filters", {})
        ...
    ```
"""

from typing import Any, NotRequired, TypedDict


class FilterDict(TypedDict, total=False):
    """
    Type-safe filter dictionary for database queries.

    All fields are optional. Add additional fields as needed for
    specific models (e.g., id, name, status, etc.).
    """

    id: int
    name: str
    status: str


class PaginationParams(TypedDict):
    """
    Pagination parameters for list endpoints.

    Required fields: page, per_page
    Optional fields: filters
    """

    page: int
    per_page: int
    filters: NotRequired[dict[str, Any]]


class RedisPoolStats(TypedDict):
    """
    Redis connection pool statistics.

    Used by RedisPool.get_pool_stats() for monitoring.
    """

    db: int
    max_connections: int
    connection_kwargs: "RedisConnectionKwargs"


class RedisConnectionKwargs(TypedDict):
    """
    Redis connection configuration parameters.

    Used in RedisPoolStats for displaying connection settings.
    """

    socket_timeout: int
    socket_connect_timeout: int
    health_check_interval: int


class AuditLogData(TypedDict, total=False):
    """
    Audit log entry data structure.

    Optional fields for audit logging. Not all fields are
    required for every audit entry.
    """

    user_id: str
    username: str
    user_roles: list[str]
    action_type: str
    resource: str
    outcome: str
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    request_data: dict[str, Any] | None
    response_status: int | None
    error_message: str | None
    duration_ms: int | None
