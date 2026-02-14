"""
Protocol for WebSocket message format strategies.

Defines the interface for handling different message formats (JSON, Protobuf, etc.)
using structural subtyping (Protocol). Any class implementing these methods is
compatible without explicit inheritance.
"""

from typing import Any, Protocol

from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel as BaseResponseModel

# Type alias for ResponseModel without generic parameter
ResponseModel = BaseResponseModel[Any]


class MessageFormatStrategy(Protocol):
    """
    Protocol for WebSocket message format handling.

    Uses structural subtyping - any class with these methods is compatible,
    no explicit inheritance needed.

    Example:
        ```python
        from app.api.ws.formats import select_message_format_strategy


        strategy = select_message_format_strategy("json")
        request = await strategy.deserialize(raw_data)
        response_data = await strategy.serialize(response_model)
        ```
    """

    async def deserialize(
        self, raw_data: dict[str, Any] | bytes
    ) -> RequestModel:
        """
        Convert raw WebSocket data to RequestModel.

        Args:
            raw_data: Raw message data (dict for JSON, bytes for binary formats)

        Returns:
            Parsed and validated RequestModel

        Raises:
            ValidationError: If data doesn't match RequestModel schema
            DecodeError: If binary data is malformed (Protobuf)
            ValueError: If format mismatch or conversion fails
        """
        ...

    async def serialize(
        self, response: ResponseModel
    ) -> dict[str, Any] | bytes:
        """
        Convert ResponseModel to wire format.

        Args:
            response: Response model to serialize

        Returns:
            Serialized data ready for websocket.send_json() or websocket.send_bytes()
        """
        ...

    @property
    def format_name(self) -> str:
        """Human-readable format name for logging (e.g., 'json', 'protobuf')."""
        ...
