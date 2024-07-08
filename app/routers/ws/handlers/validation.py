from jsonschema import validate
from typing import Dict, Any, Union
from app.logging import logger
from app.schemas import PaginatedRequestModel, RequestModel

validation_map: Dict[int, Union[None, Dict[str, Any]]] = {
    1: None,
    2: PaginatedRequestModel().schema(),
    3: {
        "type": "object",
        "properties": {
            "field5": {"type": "string"},
            "field6": {"type": "number"},
        },
        "required": ["field5", "field6"],
    },
}

def is_request_data_valid(request: RequestModel) -> None:
    try:
        schema = validation_map[request.pkg_id]

        # Data for a specific PkgID does not need to be validated
        if schema is None:
            return

        validate(request.data, schema)  # JSON schema validation
    except KeyError:
        logger.debug(f"Missing validation schema for PkgID {request.pkg_id}")
        raise Exception('Missing validation schema')

