from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.contants import PkgID
from app.db import get_paginated_results
from app.handlers.registry import register_handler
from app.logging import logger
from app.models import Author
from app.schemas import RequestModel, ResponseModel


@register_handler(PkgID.GET_AUTHORS)
async def get_authors_handler(
    request: RequestModel, session: AsyncSession
) -> ResponseModel[Author]:
    """
    Handles the request to retrieve a list of authors.

    Args:
        request (RequestModel): The request model containing the package ID and request ID.
        session (AsyncSession): The database session to use for the query.

    Returns:
        ResponseModel[Author]: The response model containing the list of authors.
    """
    try:
        # author = Author(**data)
        # self.session.add(author)
        # await self.session.commit()
        # await self.session.refresh(author)

        result = await session.exec(select(Author))
        authors = result.all()

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=authors,
        )
    except Exception as ex:
        logger.error(ex)
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Error occurred while handle get authors",
        )


@register_handler(PkgID.GET_PAGINATED_AUTHORS)
async def get_paginated_authers_handlers(
    request: RequestModel, session: AsyncSession
) -> ResponseModel[Author]:
    """
    Handles the request to retrieve a paginated list of authors.

    Args:
        request (RequestModel): The request model containing the package ID, request ID, and pagination parameters.
        session (AsyncSession): The database session to use for the query.

    Returns:
        ResponseModel[Author]: The response model containing the list of authors and pagination metadata.
    """
    try:
        authors, meta = await get_paginated_results(
            session, Author, **request.data
        )

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=authors,
            meta=meta,
        )
    except Exception as ex:
        logger.error(ex)
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Error occurred while handle get paginated authors",
        )
