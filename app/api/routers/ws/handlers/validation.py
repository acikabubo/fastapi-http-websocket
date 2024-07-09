from typing import Any, Dict, Union

from jsonschema import ValidationError, validate

from app.contants import PkgID, RSPCode
from app.logging import logger
from app.schemas import PaginatedRequestModel, RequestModel, ResponseModel

# A mapping of PkgID to JSON schema definitions for validating request data.
# The schema definitions are used to validate the `data` field of `RequestModel` instances
# based on the `pkg_id` field. If a schema is not defined for a particular `PkgID`, the
# validation step is skipped.
validation_map: Dict[PkgID, Union[None, Dict[str, Any]]] = {
    PkgID.GET_AUTHORS: {
        "type": "object",
        "properties": {
            "field1": {"type": "string"},
        },
        "required": ["field1"],
    },
    PkgID.GET_PAGINATED_AUTHORS: PaginatedRequestModel().schema(),
    PkgID.THIRD: {
        "type": "object",
        "properties": {
            "field5": {"type": "string"},
            "field6": {"type": "number"},
        },
        "required": ["field5", "field6"],
    },
}


def is_request_data_valid(request: RequestModel) -> ResponseModel | None:
    """
    Validates the data field of a RequestModel instance based on the pkg_id field.

    If a validation schema is defined for the given pkg_id, the data is validated against
    that schema using the jsonschema library. If no schema is defined, the validation step
    is skipped.

    If the data is invalid, a ResponseModel instance with an error message is returned.
    Otherwise, this function returns None, indicating the data is valid.

    Args:
        request (RequestModel): The request model instance to validate.

    Returns:
        ResponseModel | None: A ResponseModel instance with an error message if the data
        is invalid, otherwise None.
    """
    try:
        schema = validation_map[request.pkg_id]

        # Data for a specific PkgID does not need to be validated
        if schema is None:
            return

        validate(request.data, schema)  # JSON schema validation
    except KeyError:
        logger.debug(f"Missing validation schema for PkgID {request.pkg_id}")
        raise Exception("Missing validation schema")
    except ValidationError as ex:
        logger.error(f"Invalid data for PkgID {request.pkg_id}: \n{ex}")

        return ResponseModel.err_msg(
            request.pkg_id, status_code=RSPCode.INVALID_DATA
        )
