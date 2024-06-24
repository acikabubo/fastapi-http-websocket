from typing import Any, Dict

from app.models import ResponseModel


class BaseHandler:
    async def handle_request(
        self, pkg_id: int, data: Dict[str, Any]
    ) -> ResponseModel:
        """
        Handles an asynchronous request for a specific package ID, with the provided data.

        Args:
            pkg_id (int): The ID of the package to handle the request for.
            data (Dict[str, Any]): The data associated with the request.

        Returns:
            ResponseModel: The response model containing the result of the request handling.

        Raises:
            NotImplementedError: This method must be implemented by a subclass.
        """
        raise NotImplementedError
