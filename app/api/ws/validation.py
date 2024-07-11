from typing import Any

from jsonschema import ValidationError, validate

from app.api.ws.constants import RSPCode
from app.core.logging import logger
from app.schemas.generic_typing import JsonSchemaType
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel


def validator(
    request: RequestModel, schema: JsonSchemaType
) -> ResponseModel[dict[str, Any]] | None:
    """
    Validates the data field of a RequestModel instance against the provided JSON schema.

    If the data is invalid, a ResponseModel instance with an error message is returned.
    Otherwise, this function returns None, indicating the data is valid.

    Args:
        request (RequestModel): The request model instance to validate.
        schema (JsonSchemaType): The JSON schema to validate the request data against.

    Returns:
        ResponseModel | None: A ResponseModel instance with an error message if the data
        is invalid, otherwise None.
    """
    try:
        validate(request.data, schema)  # JSON schema validation
    except ValidationError as ex:
        logger.error(f"Invalid data for PkgID {request.pkg_id}: \n{ex}")

        return ResponseModel.err_msg(
            request.pkg_id, status_code=RSPCode.INVALID_DATA
        )
