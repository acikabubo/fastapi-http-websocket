from fastapi import APIRouter, Depends

from app.models.author import Author
from app.schemas.author import AuthorQueryParams
from app.schemas.response import PaginatedResponseModel
from app.settings import app_settings
from app.storage.db import get_paginated_results

router = APIRouter()


@router.post("/authors", summary="Create new author")
async def create_author_endpoint(author: Author) -> Author:
    """
    Creates a new author in the database.

    Args:
        author (Author): The author object to create.

    Returns:
        Author: The created author object.
    """
    return await Author.create(author)


@router.get(
    "/authors",
    response_model=list[Author],
    summary="Get list of authors",
)
async def get_authors_endpoint(
    q: AuthorQueryParams = Depends(),
) -> list[Author]:
    """
    Retrieves a list of authors from the database based on the provided query parameters.

    Args:
        q (AuthorQueryParams): The query parameters to filter the authors by.

    Returns:
        list[Author]: A list of author objects matching the provided query parameters.
    """
    return await Author.get_list(**q.model_dump(exclude_none=True))


@router.get(
    "/authors_paginated",
    response_model=PaginatedResponseModel[Author],
    summary="Get paginated list of authors",
)
async def get_paginated_authors_endpoint(
    page: int = 1,
    per_page: int = app_settings.DEFAULT_PAGE_SIZE,
    q: AuthorQueryParams = Depends(),
) -> PaginatedResponseModel[Author]:
    """
    Retrieves a paginated list of authors from the database based on the provided query parameters.

    Args:
        page (int): The page number to retrieve.
        per_page (int): The number of items to return per page.
        q (AuthorQueryParams): The query parameters to filter the authors by.

    Returns:
        PaginatedResponseModel[Author]: A paginated response containing the list of authors matching the provided query parameters.
    """
    items, meta = await get_paginated_results(
        Author, page, per_page, filters=q.model_dump(exclude_none=True)
    )

    return PaginatedResponseModel(items=items, meta=meta)
