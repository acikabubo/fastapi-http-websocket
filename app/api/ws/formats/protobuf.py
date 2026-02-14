"""Protobuf message format strategy for WebSocket communication."""

from typing import Any

from app.schemas.proto import Request as ProtoRequest
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel as BaseResponseModel
from app.utils.protobuf_converter import (
    proto_to_pydantic_request,
    serialize_response,
)

# Type alias for ResponseModel without generic parameter
ResponseModel = BaseResponseModel[Any]


class ProtobufFormatStrategy:
    """
    Protobuf message format strategy.

    Handles binary Protobuf-formatted WebSocket messages.
    Reuses existing protobuf_converter utilities for conversion logic.
    """

    @property
    def format_name(self) -> str:
        """Format identifier for logging."""
        return "protobuf"

    async def deserialize(
        self, raw_data: dict[str, Any] | bytes
    ) -> RequestModel:
        """
        Parse Protobuf bytes to RequestModel.

        Args:
            raw_data: Binary protobuf data

        Returns:
            Converted RequestModel

        Raises:
            DecodeError: If protobuf data is malformed
            ValueError: If dict is received (format mismatch) or conversion fails
        """
        if not isinstance(raw_data, bytes):
            raise ValueError(
                "Protobuf strategy received dict - format mismatch"
            )

        # Decode protobuf message
        proto_request = ProtoRequest()
        proto_request.ParseFromString(raw_data)  # May raise DecodeError

        # Convert to Pydantic model
        return proto_to_pydantic_request(proto_request)  # May raise ValueError

    async def serialize(self, response: ResponseModel) -> bytes:
        """
        Convert ResponseModel to Protobuf bytes.

        Args:
            response: Response to serialize

        Returns:
            Binary protobuf data ready for websocket.send_bytes()
        """
        result = serialize_response(response, "protobuf")
        # serialize_response with "protobuf" always returns bytes
        assert isinstance(result, bytes)
        return result
