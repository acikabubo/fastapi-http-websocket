from json import loads
from typing import Any

from icecream import ic

from app.logging import logger


def read_json_file(file_path: str) -> dict[str, Any]:
    """
    Reads the contents of a JSON file at the given file path and returns the parsed JSON data as a dictionary.

    Args:
        file_path (str): The file path of the JSON file to read.

    Returns:
        dict[str, Any]: The parsed JSON data as a dictionary.

    Raises:
        Exception: If there is an error reading or parsing the JSON file.
    """
    try:
        with open(file_path, mode="r") as f:
            content = f.read()
            return loads(content)
    except Exception as ex:
        ic(f"Failed to open {file_path}: {ex}")
        logger.debug(f"Failed to open {file_path}: {ex}")
        return {}
