from json import loads
from typing import Any

from jsonschema import ValidationError, validate

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.generic_typing import JsonSchemaType


def read_json_file(file_path: str, schema: JsonSchemaType) -> dict[str, Any]:
    """
    Reads the contents of a JSON file at the given `file_path` and validates it against the provided `schema`.
    If the file is successfully read and validated, the function returns the parsed JSON content as a dictionary.
    If there are any errors, the function logs the error and returns an empty dictionary.

    Parameters:
    - `file_path` (str): The path to the JSON file to be read.
    - `schema` (JsonSchemaType): The JSON schema to validate the file contents against.

    Returns:
    - dict[str, Any]: The parsed JSON content as a dictionary, or an empty dictionary if there were any errors.
    """
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
        logger.error(f"Failed to open {file_path}: {ex}")
        return {}
