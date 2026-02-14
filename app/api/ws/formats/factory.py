"""Factory for selecting WebSocket message format strategies."""

from app.api.ws.formats.json import JSONFormatStrategy
from app.api.ws.formats.protocol import MessageFormatStrategy
from app.api.ws.formats.protobuf import ProtobufFormatStrategy


def select_message_format_strategy(format_name: str) -> MessageFormatStrategy:
    """
    Select message format strategy based on format name.

    Args:
        format_name: Format identifier (e.g., 'json', 'protobuf')

    Returns:
        Appropriate MessageFormatStrategy implementation

    Note:
        Defaults to JSONFormatStrategy for unknown formats
    """
    if format_name == "protobuf":
        return ProtobufFormatStrategy()
    return JSONFormatStrategy()  # Default format
