from enum import StrEnum


class Role(StrEnum):
    """Application roles — single source of truth for RBAC.

    Using StrEnum ensures Role values are strings, so they work
    transparently wherever a str is expected (e.g. require_roles,
    @pkg_router.register roles=[...]).
    """

    ADMIN = "admin"
    GET_AUTHORS = "get-authors"
    CREATE_AUTHOR = "create-author"
    UPDATE_AUTHOR = "update-author"
    DELETE_AUTHOR = "delete-author"
    VIEW_AUDIT_LOGS = "view-audit-logs"
