from jsonschema import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.routers.ws.constants import PkgID, RSPCode
from app.api.routers.ws.handlers.registry import register_handler, validate
from app.api.routers.ws.validation import validator
from app.core.db import get_paginated_results
from app.core.logging import logger
from app.models.author import Author
from app.schemas.generic import JsonSchemaType
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel

json_schema: JsonSchemaType = {
    "type": "object",
    "properties": {
        "field1": {"type": "string"},
    },
    "required": ["field1"],
}


@register_handler(PkgID.GET_AUTHORS)
@validate(json_schema=json_schema, validator=validator)
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
        result = await session.exec(select(Author))
        authors = result.all()

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=authors,
        )
    except ValidationError as ex:
        logger.error(f"Invalid data for PkgID {request.pkg_id}: \n{ex}")

        return ResponseModel.err_msg(
            request.pkg_id, status_code=RSPCode.INVALID_DATA
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
