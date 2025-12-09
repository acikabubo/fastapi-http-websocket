"""
Author endpoints using Repository + Command + Dependency Injection.

These endpoints use:
- Dependency Injection for testability
- Repository pattern for data access
- Command pattern for business logic
- Decorator-based RBAC for permissions

Example:
    command = GetAuthorsCommand(repo)
    return await command.execute(input_data)
"""

from fastapi import APIRouter, Depends, HTTPException, status

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

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get(
    "",
    response_model=list[Author],
    summary="Get all authors",
    description="Get authors using Repository + Command pattern",
    dependencies=[Depends(require_roles("get-authors"))],
)
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
        HTTPException: 400 if author with same name exists.

    Example:
        POST /authors
        {
            "name": "John Doe"
        }
    """
    try:
        command = CreateAuthorCommand(repo)
        return await command.execute(author_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put(
    "/{author_id}",
    response_model=Author,
    summary="Update an author",
    description="Update author using Repository + Command pattern",
    dependencies=[Depends(require_roles("update-author"))],
)
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
        HTTPException: 404 if author not found, 400 if name conflicts.

    Example:
        PUT /authors/1
        {
            "name": "Jane Doe"
        }
    """
    try:
        command = UpdateAuthorCommand(repo)
        input_data = UpdateAuthorInput(id=author_id, name=author_data.name)
        return await command.execute(input_data)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.delete(
    "/{author_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an author",
    description="Delete author using Repository + Command pattern",
    dependencies=[Depends(require_roles("delete-author"))],
)
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
    try:
        command = DeleteAuthorCommand(repo)
        await command.execute(author_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/paginated",
    response_model=PaginatedResponseModel[Author],
    summary="Get paginated list of authors",
    description="Get paginated authors using helper function",
    dependencies=[Depends(require_roles("get-authors"))],
)
async def get_paginated_authors(
    repo: AuthorRepoDep,
    page: int = 1,
    per_page: int = app_settings.DEFAULT_PAGE_SIZE,
    id: int | None = None,
    name: str | None = None,
) -> PaginatedResponseModel[Author]:
    """
    Get paginated list of authors.

    This endpoint shows how pagination works with the pattern.
    For now, it still uses get_paginated_results() helper, but data
    access could be moved to repository if needed.

    Requires role: get-authors

    Args:
        repo: Author repository (injected via dependency).
        page: Page number (starts at 1).
        per_page: Items per page.
        id: Optional author ID filter.
        name: Optional name filter.

    Returns:
        Paginated response with items and metadata.

    Example:
        GET /authors/paginated?page=1&per_page=10
    """
    filters = {}
    if id is not None:
        filters["id"] = id
    if name is not None:
        filters["name"] = name

    items, meta = await get_paginated_results(
        Author, page=page, per_page=per_page, filters=filters
    )

    return PaginatedResponseModel(items=items, meta=meta)
