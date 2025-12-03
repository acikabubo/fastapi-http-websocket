from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.ws.constants import PkgID, RSPCode
from app.api.ws.validation import validator
from app.logging import logger
from app.models.author import Author
from app.routing import pkg_router
from app.schemas.generic_typing import JsonSchemaType
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.storage.db import async_session, get_paginated_results

get_authors_schema: JsonSchemaType = {
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


class GetAuthorsModel(BaseModel):
    """Schema for filtering authors in get_authors requests."""

    id: int | None = None
    name: str | None = None


@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=GetAuthorsModel,
    validator_callback=validator,
)
async def get_authors_handler(request: RequestModel) -> ResponseModel[Author]:
    """
    Handles the request to get a list of authors.

    Args:
        request (RequestModel): The request model containing the filters to apply.

    Returns:
        ResponseModel[Author]: The response model containing the list of authors.

    Raises:
        Exception: If an unexpected error occurs while handling the request.
    """
    try:
        filters = request.data.get("filters", {})
        async with async_session() as session:
            authors = await Author.get_list(session, **filters)

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[author.model_dump() for author in authors],
        )
    except SQLAlchemyError as ex:
        logger.error(f"Database error retrieving authors: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Database error occurred",
            status_code=RSPCode.ERROR,
        )
    except (ValidationError, AttributeError) as ex:
        logger.error(f"Validation error: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Invalid filter parameters",
            status_code=RSPCode.INVALID_DATA,
        )
    # Let unexpected errors propagate for proper logging


get_paginated_authors_schema: JsonSchemaType = {
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
    json_schema=get_paginated_authors_schema,
    validator_callback=validator,
)
async def get_paginated_authors_handler(
    request: RequestModel,
) -> ResponseModel[Author]:
    """
    Handles the request to get a paginated list of authors.

    Returns:
        ResponseModel[Author]: The response model containing the paginated list of authors.

    Raises:
        Exception: If an unexpected error occurs while handling the request.
    """
    try:
        authors, meta = await get_paginated_results(Author, **request.data)

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[author.model_dump() for author in authors],
            meta=meta,
        )
    except SQLAlchemyError as ex:
        logger.error(f"Database error retrieving paginated authors: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Database error occurred",
            status_code=RSPCode.ERROR,
        )
    except (ValidationError, AttributeError) as ex:
        logger.error(f"Validation error: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Invalid pagination parameters",
            status_code=RSPCode.INVALID_DATA,
        )
    # Let unexpected errors propagate for proper logging
