"""
Modern author endpoints using Repository + Command + Dependency Injection.

This file demonstrates the new design patterns and can be compared with
app/api/http/author.py to see the differences. These endpoints use:
- Dependency Injection for testability
- Repository pattern for data access
- Command pattern for business logic

Compare with app/api/http/author.py to see how the same functionality
is implemented with modern patterns vs. the old Active Record pattern.

Example:
    # Old pattern (author.py)
    async with async_session() as session:
        return await Author.get_list(session, **filters)

    # New pattern (author_refactored.py)
    command = GetAuthorsCommand(repo)
    return await command.execute(input_data)
"""

from fastapi import APIRouter, HTTPException, status

from app.commands.author_commands import (
    CreateAuthorCommand,
    CreateAuthorInput,
    DeleteAuthorCommand,
    GetAuthorsCommand,
    GetAuthorsInput,
    UpdateAuthorCommand,
    UpdateAuthorInput,
)
from app.dependencies import AuthorRepoDep, RBACDep
from app.models.author import Author
from app.schemas.response import PaginatedResponseModel
from app.settings import app_settings
from app.storage.db import get_paginated_results

router = APIRouter(prefix="/authors-v2", tags=["authors-v2"])


@router.get(
    "",
    response_model=list[Author],
    summary="Get all authors (V2)",
    description="Get authors using Repository + Command pattern",
)
async def get_authors_v2(
    repo: AuthorRepoDep,
    rbac: RBACDep,
    id: int | None = None,
    name: str | None = None,
    search: str | None = None,
) -> list[Author]:
    """
    Get all authors with optional filtering.

    This endpoint demonstrates the Repository + Command pattern.
    Business logic is encapsulated in GetAuthorsCommand, making it
    reusable in WebSocket handlers.

    Args:
        repo: Author repository (injected via dependency).
        rbac: RBAC manager (injected via dependency).
        id: Optional author ID filter.
        name: Optional exact name filter.
        search: Optional name search term (case-insensitive).

    Returns:
        List of authors matching filters.

    Example:
        GET /authors-v2?search=John
        GET /authors-v2?id=1
        GET /authors-v2?name=John%20Doe
    """
    command = GetAuthorsCommand(repo)
    input_data = GetAuthorsInput(id=id, name=name, search_term=search)
    return await command.execute(input_data)


@router.post(
    "",
    response_model=Author,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new author (V2)",
    description="Create author using Repository + Command pattern",
)
async def create_author_v2(
    author_data: CreateAuthorInput,
    repo: AuthorRepoDep,
    rbac: RBACDep,
) -> Author:
    """
    Create a new author.

    This endpoint demonstrates the Repository + Command pattern.
    Business logic (checking for duplicate names) is in CreateAuthorCommand.

    Args:
        author_data: Author data to create.
        repo: Author repository (injected via dependency).
        rbac: RBAC manager (injected via dependency).

    Returns:
        Created author with generated ID.

    Raises:
        HTTPException: 400 if author with same name exists.

    Example:
        POST /authors-v2
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
    summary="Update an author (V2)",
    description="Update author using Repository + Command pattern",
)
async def update_author_v2(
    author_id: int,
    author_data: CreateAuthorInput,
    repo: AuthorRepoDep,
    rbac: RBACDep,
) -> Author:
    """
    Update an existing author.

    Args:
        author_id: ID of author to update.
        author_data: New author data.
        repo: Author repository (injected via dependency).
        rbac: RBAC manager (injected via dependency).

    Returns:
        Updated author.

    Raises:
        HTTPException: 404 if author not found, 400 if name conflicts.

    Example:
        PUT /authors-v2/1
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
    summary="Delete an author (V2)",
    description="Delete author using Repository + Command pattern",
)
async def delete_author_v2(
    author_id: int,
    repo: AuthorRepoDep,
    rbac: RBACDep,
) -> None:
    """
    Delete an author.

    Args:
        author_id: ID of author to delete.
        repo: Author repository (injected via dependency).
        rbac: RBAC manager (injected via dependency).

    Raises:
        HTTPException: 404 if author not found.

    Example:
        DELETE /authors-v2/1
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
    summary="Get paginated list of authors (V2)",
    description="Get paginated authors using helper function",
)
async def get_paginated_authors_v2(
    repo: AuthorRepoDep,
    rbac: RBACDep,
    page: int = 1,
    per_page: int = app_settings.DEFAULT_PAGE_SIZE,
    id: int | None = None,
    name: str | None = None,
) -> PaginatedResponseModel[Author]:
    """
    Get paginated list of authors.

    This endpoint shows how pagination works with the new pattern.
    For now, it still uses get_paginated_results() helper, but data
    access could be moved to repository if needed.

    Args:
        repo: Author repository (injected via dependency).
        rbac: RBAC manager (injected via dependency).
        page: Page number (starts at 1).
        per_page: Items per page.
        id: Optional author ID filter.
        name: Optional name filter.

    Returns:
        Paginated response with items and metadata.

    Example:
        GET /authors-v2/paginated?page=1&per_page=10
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
