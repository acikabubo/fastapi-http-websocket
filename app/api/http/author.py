"""
Author endpoints using Repository + Command + Dependency Injection.

These endpoints use:
- Dependency Injection for testability
- Repository pattern for data access
- Command pattern for business logic
- Decorator-based RBAC for permissions
- Unified error handling across protocols

Example:
    command = GetAuthorsCommand(repo)
    return await command.execute(input_data)
"""

from typing import Any

from fastapi import APIRouter, Depends, status

from app.commands.author_commands import (
    CreateAuthorCommand,
    CreateAuthorInput,
    DeleteAuthorCommand,
    GetAuthorsCommand,
    GetAuthorsInput,
    UpdateAuthorCommand,
    UpdateAuthorInput,
)
from app.dependencies import AuthorRepoDep
from app.dependencies.permissions import require_roles
from app.models.author import Author
from app.schemas.response import PaginatedResponseModel
from app.settings import app_settings
from app.storage.db import get_paginated_results
from app.utils.error_handler import handle_http_errors

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get(
    "",
    response_model=list[Author],
    summary="Get all authors",
    description="Get authors using Repository + Command pattern",
    dependencies=[Depends(require_roles("get-authors"))],
)
@handle_http_errors
async def get_authors(
    repo: AuthorRepoDep,
    id: int | None = None,
    name: str | None = None,
    search: str | None = None,
) -> list[Author]:
    """
    Get all authors with optional filtering.

    This endpoint demonstrates the Repository + Command pattern.
    Business logic is encapsulated in GetAuthorsCommand, making it
    reusable in WebSocket handlers.

    Requires role: get-authors

    Args:
        repo: Author repository (injected via dependency).
        id: Optional author ID filter.
        name: Optional exact name filter.
        search: Optional name search term (case-insensitive).

    Returns:
        List of authors matching filters.

    Example:
        GET /authors?search=John
        GET /authors?id=1
        GET /authors?name=John%20Doe
    """
    command = GetAuthorsCommand(repo)
    input_data = GetAuthorsInput(id=id, name=name, search_term=search)
    return await command.execute(input_data)


@router.post(
    "",
    response_model=Author,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new author",
    description="Create author using Repository + Command pattern",
    dependencies=[Depends(require_roles("create-author"))],
)
@handle_http_errors
async def create_author(
    author_data: CreateAuthorInput,
    repo: AuthorRepoDep,
) -> Author:
    """
    Create a new author.

    This endpoint demonstrates the Repository + Command pattern.
    Business logic (checking for duplicate names) is in CreateAuthorCommand.

    Requires role: create-author

    Args:
        author_data: Author data to create.
        repo: Author repository (injected via dependency).

    Returns:
        Created author with generated ID.

    Raises:
        HTTPException: 409 if author with same name exists.

    Example:
        POST /authors
        {
            "name": "John Doe"
        }
    """
    command = CreateAuthorCommand(repo)
    return await command.execute(author_data)


@router.put(
    "/{author_id}",
    response_model=Author,
    summary="Update an author",
    description="Update author using Repository + Command pattern",
    dependencies=[Depends(require_roles("update-author"))],
)
@handle_http_errors
async def update_author(
    author_id: int,
    author_data: CreateAuthorInput,
    repo: AuthorRepoDep,
) -> Author:
    """
    Update an existing author.

    Requires role: update-author

    Args:
        author_id: ID of author to update.
        author_data: New author data.
        repo: Author repository (injected via dependency).

    Returns:
        Updated author.

    Raises:
        HTTPException: 404 if author not found, 409 if name conflicts.

    Example:
        PUT /authors/1
        {
            "name": "Jane Doe"
        }
    """
    command = UpdateAuthorCommand(repo)
    input_data = UpdateAuthorInput(id=author_id, name=author_data.name)
    return await command.execute(input_data)


@router.delete(
    "/{author_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an author",
    description="Delete author using Repository + Command pattern",
    dependencies=[Depends(require_roles("delete-author"))],
)
@handle_http_errors
async def delete_author(
    author_id: int,
    repo: AuthorRepoDep,
) -> None:
    """
    Delete an author.

    Requires role: delete-author

    Args:
        author_id: ID of author to delete.
        repo: Author repository (injected via dependency).

    Raises:
        HTTPException: 404 if author not found.

    Example:
        DELETE /authors/1
    """
    command = DeleteAuthorCommand(repo)
    await command.execute(author_id)


@router.get(
    "/paginated",
    response_model=PaginatedResponseModel[Author],
    summary="Get paginated list of authors",
    description="Get paginated authors with offset or cursor pagination",
    dependencies=[Depends(require_roles("get-authors"))],
)
@handle_http_errors
async def get_paginated_authors(
    repo: AuthorRepoDep,
    page: int = 1,
    per_page: int = app_settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    id: int | None = None,
    name: str | None = None,
) -> PaginatedResponseModel[Author]:
    """
    Get paginated list of authors with offset or cursor pagination.

    Supports both pagination strategies:
    - **Offset Pagination**: Use `page` parameter (traditional page-based)
    - **Cursor Pagination**: Use `cursor` parameter (high-performance)

    Cursor pagination takes precedence if both are provided.

    Requires role: get-authors

    Args:
        repo: Author repository (injected via dependency).
        page: Page number (starts at 1) - used for offset pagination.
        per_page: Items per page.
        cursor: Base64 cursor from previous response - used for cursor pagination.
        id: Optional author ID filter.
        name: Optional name filter.

    Returns:
        Paginated response with items and metadata.

    Examples:
        Offset pagination:
            GET /authors/paginated?page=1&per_page=10

        Cursor pagination (first page):
            GET /authors/paginated?per_page=10&cursor=

        Cursor pagination (next page):
            GET /authors/paginated?per_page=10&cursor=MjA=
    """
    filters: dict[str, Any] = {}
    if id is not None:
        filters["id"] = id
    if name is not None:
        filters["name"] = name

    items, meta = await get_paginated_results(
        Author,
        page=page,
        per_page=per_page,
        cursor=cursor,
        filters=filters,
    )

    return PaginatedResponseModel(items=items, meta=meta)
