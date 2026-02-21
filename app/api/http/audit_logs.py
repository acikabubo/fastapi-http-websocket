"""HTTP endpoints for querying audit logs."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import select

from fastapi_keycloak_rbac.dependencies import require_roles
from app.models.user_action import UserAction
from app.schemas.response import PaginatedResponseModel
from app.settings import app_settings
from app.storage.db import async_session, get_paginated_results

router = APIRouter()


@router.get(
    "/audit-logs",
    response_model=PaginatedResponseModel[UserAction],
    summary="Get paginated audit logs",
    dependencies=[Depends(require_roles("admin"))],
)
async def get_audit_logs_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(
        app_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=100,
        description="Items per page",
    ),
    user_id: str | None = Query(None, description="Filter by user ID"),
    username: str | None = Query(None, description="Filter by username"),
    action_type: str | None = Query(None, description="Filter by action type"),
    resource: str | None = Query(None, description="Filter by resource"),
    outcome: str | None = Query(
        None,
        description="Filter by outcome (success, error, permission_denied)",
    ),
    start_date: datetime | None = Query(
        None, description="Filter by start date (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        None, description="Filter by end date (ISO 8601)"
    ),
) -> PaginatedResponseModel[UserAction]:
    """
    Retrieve paginated audit logs with optional filters.

    This endpoint is restricted to admin users only and provides access to
    the complete audit trail of user actions.

    Args:
        page: Page number (default: 1).
        per_page: Number of items per page (default: 20, max: 100).
        user_id: Filter logs by Keycloak user ID.
        username: Filter logs by username.
        action_type: Filter logs by action type (e.g., GET, POST, WS:PkgID).
        resource: Filter logs by resource (e.g., /api/authors, Author:123).
        outcome: Filter logs by outcome (success, error, permission_denied).
        start_date: Filter logs from this date (inclusive).
        end_date: Filter logs until this date (inclusive).

    Returns:
        Paginated response containing audit log entries and metadata.
    """

    # Build filters dictionary
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if username:
        filters["username"] = username
    if action_type:
        filters["action_type"] = action_type
    if resource:
        filters["resource"] = resource
    if outcome:
        filters["outcome"] = outcome

    # Custom filter function for date range
    def apply_date_filters(stmt: Any) -> Any:
        """Apply date range filters to the query."""
        if start_date:
            stmt = stmt.where(UserAction.timestamp >= start_date)
        if end_date:
            stmt = stmt.where(UserAction.timestamp <= end_date)
        # Order by timestamp descending (most recent first)
        stmt = stmt.order_by(UserAction.timestamp.desc())  # type: ignore[attr-defined]
        return stmt

    # Get paginated results
    items, meta = await get_paginated_results(
        UserAction,
        page,
        per_page,
        filters=filters,
        apply_filters=apply_date_filters if (start_date or end_date) else None,  # type: ignore[arg-type]
    )

    return PaginatedResponseModel(items=items, meta=meta)


@router.get(
    "/audit-logs/{log_id}",
    response_model=UserAction,
    summary="Get specific audit log entry",
    dependencies=[Depends(require_roles("admin"))],
)
async def get_audit_log_by_id_endpoint(log_id: int) -> UserAction | None:
    """
    Retrieve a specific audit log entry by ID.

    Args:
        log_id: The ID of the audit log entry.

    Returns:
        The audit log entry, or None if not found.
    """
    async with async_session() as session:
        stmt = select(UserAction).where(UserAction.id == log_id)
        result = await session.exec(stmt)
        return result.first()


@router.get(
    "/audit-logs/user/{user_id}",
    response_model=PaginatedResponseModel[UserAction],
    summary="Get audit logs for a specific user",
    dependencies=[Depends(require_roles("admin"))],
)
async def get_user_audit_logs_endpoint(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(
        app_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=100,
        description="Items per page",
    ),
    start_date: datetime | None = Query(
        None, description="Filter by start date (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        None, description="Filter by end date (ISO 8601)"
    ),
) -> PaginatedResponseModel[UserAction]:
    """
    Retrieve all audit logs for a specific user.

    Args:
        user_id: Keycloak user ID to retrieve logs for.
        page: Page number (default: 1).
        per_page: Number of items per page (default: 20, max: 100).
        start_date: Filter logs from this date (inclusive).
        end_date: Filter logs until this date (inclusive).

    Returns:
        Paginated response containing the user's audit log entries.
    """

    # Custom filter function for date range
    def apply_date_filters(stmt: Any) -> Any:
        """Apply date range filters to the query."""
        if start_date:
            stmt = stmt.where(UserAction.timestamp >= start_date)
        if end_date:
            stmt = stmt.where(UserAction.timestamp <= end_date)
        # Order by timestamp descending (most recent first)
        stmt = stmt.order_by(UserAction.timestamp.desc())  # type: ignore[attr-defined]
        return stmt

    # Get paginated results
    items, meta = await get_paginated_results(
        UserAction,
        page,
        per_page,
        filters={"user_id": user_id},
        apply_filters=apply_date_filters if (start_date or end_date) else None,  # type: ignore[arg-type]
    )

    return PaginatedResponseModel(items=items, meta=meta)
