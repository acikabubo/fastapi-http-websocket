from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Author

router = APIRouter()


@router.post("/author")
async def create_author(
    author: Author = Author, session: AsyncSession = Depends(get_session)
):
    session.add(author)
    session.commit()
    session.refresh(author)
    return author
