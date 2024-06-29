from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db import get_session
from app.models import Author

router = APIRouter()


@router.post("/author")
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


@router.get("/author", response_model=list[Author])
async def get_authors(
    session: AsyncSession = Depends(get_session),
) -> list[Author]:
    """
    Retrieves a list of all authors from the database.

    Args:
        session (AsyncSession): The database session to use for the query.

    Returns:
        list[Author]: A list of all Author objects in the database.
    """
    result = await session.execute(select(Author))
    authors = result.scalars().all()
    return authors
