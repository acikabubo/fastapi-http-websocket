from json import loads
from typing import Any

from icecream import ic
from jsonschema import ValidationError, validate

from app.logging import logger
from app.schemas.generic_typing import JsonSchemaType


def read_json_file(file_path: str, schema: JsonSchemaType) -> dict[str, Any]:
    try:
        content = {}
        with open(file_path, mode="r") as f:
            content = loads(f.read())

        if schema:
            validate(content, schema)

        return content
    except ValidationError as ex:
        logger.error(f"Invalid data for {file_path}")
        raise ex
    except Exception as ex:
        ic(f"Failed to open {file_path}: {ex}")
        logger.debug(f"Failed to open {file_path}: {ex}")
        return {}
