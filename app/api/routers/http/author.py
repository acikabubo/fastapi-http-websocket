import math

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_paginated_results, get_session
from app.models.author import Author
from app.schemas.response import PaginatedResponseModel

router = APIRouter()


@router.post("/authors")
async def create_author_endpoint(
    author: Author = Author, session: AsyncSession = Depends(get_session)
) -> Author:
    """
    Creates a new author in the database.

    Args:
        author (Author): The author object to create.
        session (AsyncSession): The database session to use for the operation.

    Returns:
        Author: The created author object.
    """
    # TODO: create create_author method in Author model and use like Depends here

    session.add(author)
    await session.commit()
    await session.refresh(author)
    return author


@router.get("/authors", response_model=list[Author])
async def get_authors(
    session: AsyncSession = Depends(get_session),
) -> list[Author]:
    # TODO: add filters
    """
    Retrieves a list of all authors from the database.

    Args:
        session (AsyncSession): The database session to use for the operation.

    Returns:
        list[Author]: A list of all authors in the database.
    """
    result = await session.exec(select(Author))
    authors = result.all()
    return authors


@router.get(
    "/authors_paginated", response_model=PaginatedResponseModel[Author]
)
async def get_paginated_authors(
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponseModel[Author]:
    # TODO: add filters
    """
    Retrieves a paginated list of authors from the database.

    Args:
        page (int): The page number to retrieve. Defaults to 1.
        per_page (int): The number of items to retrieve per page. Defaults to 20.
        session (AsyncSession): The database session to use for the operation.

    Returns:
        PaginatedResponseModel[Author]: A paginated response containing the requested authors.
    """
    items, meta = await get_paginated_results(session, Author, page, per_page)

    return PaginatedResponseModel(items=items, meta=meta)
