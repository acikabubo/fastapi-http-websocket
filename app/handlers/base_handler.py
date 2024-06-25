from typing import Any, Dict

from app.schemas import RequestModel, ResponseModel


class BaseHandler:
    async def handle_request(
        self,
        request: RequestModel,
    ) -> ResponseModel:
        """
        Handles a request by processing the provided data.

        Args:
            req_id (int): The unique identifier for the request.
            pkg_id (int): The unique identifier for the package associated with the request.
            data (Dict[str, Any]): The data to be processed for the request.

        Returns:
            ResponseModel: The response model containing the processed data.
        """
        raise NotImplementedError
