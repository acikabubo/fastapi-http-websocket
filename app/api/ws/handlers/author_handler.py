from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.ws.constants import PkgID, RSPCode
from app.api.ws.validation import validator
from app.db import get_paginated_results
from app.logging import logger
from app.models.author import Author
from app.routing import pkg_router
from app.schemas.generic_typing import JsonSchemaType
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel

filters_schema: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "filters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


@pkg_router.register(
    PkgID.GET_AUTHORS, json_schema=filters_schema, validator_callback=validator
)
async def get_authors_handler(
    request: RequestModel, session: AsyncSession
) -> ResponseModel[Author]:
    """
    Handles the request to retrieve a list of authors based on the provided filters.

    Args:
        request (RequestModel): The request model containing the package ID, request ID, and filters.
        session (AsyncSession): The database session to use for the query.

    Returns:
        ResponseModel[Author]: The response model containing the list of authors.
    """
    try:
        filters = request.data.get("filters", {})
        authors = await Author.get_list(session, **filters)

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
            status_code=RSPCode.ERROR,
        )


filters_schema: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "filters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "page": {"type": "integer"},
        "per_page": {"type": "integer"},
    },
    "additionalProperties": False,
}


@pkg_router.register(
    PkgID.GET_PAGINATED_AUTHORS,
    json_schema=filters_schema,
    validator_callback=validator,
)
async def get_paginated_authers_handler(
    request: RequestModel, session: AsyncSession
) -> ResponseModel[Author]:
    """
    Handles the request to get a paginated list of authors.

    Args:
        request (RequestModel): The request model containing the package ID, request ID, and filters.
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
