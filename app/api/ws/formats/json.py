"""JSON message format strategy for WebSocket communication."""

from typing import Any

from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel as BaseResponseModel

# Type alias for ResponseModel without generic parameter
ResponseModel = BaseResponseModel[Any]


class JSONFormatStrategy:
    """
    JSON message format strategy (default).

    Handles JSON-formatted WebSocket messages with Pydantic validation.
    Returns dict structures ready for websocket.send_json().
    """

    @property
    def format_name(self) -> str:
        """Format identifier for logging."""
        return "json"

    async def deserialize(
        self, raw_data: dict[str, Any] | bytes
    ) -> RequestModel:
        """
        Parse JSON data to RequestModel.

        Args:
            raw_data: Dict from json.loads() (already parsed by WebSocket decoder)

        Returns:
            Validated RequestModel

        Raises:
            ValidationError: If data doesn't match RequestModel schema
            ValueError: If bytes are received (format mismatch)
        """
        if isinstance(raw_data, bytes):
            raise ValueError("JSON strategy received bytes - format mismatch")

        # Pydantic validation happens here
        return RequestModel(**raw_data)

    async def serialize(self, response: ResponseModel) -> dict[str, Any]:
        """
        Convert ResponseModel to JSON-serializable dict.

        Args:
            response: Response to serialize

        Returns:
            Dict ready for websocket.send_json()
        """
        return response.model_dump()
