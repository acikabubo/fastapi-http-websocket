"""Unit tests for message format strategy factory."""

import pytest

from app.api.ws.formats.factory import select_message_format_strategy
from app.api.ws.formats.json import JSONFormatStrategy
from app.api.ws.formats.protobuf import ProtobufFormatStrategy


class TestSelectMessageFormatStrategy:
    """Test suite for select_message_format_strategy factory."""

    def test_select_json_strategy(self) -> None:
        """Test selecting JSON strategy."""
        strategy = select_message_format_strategy("json")

        assert isinstance(strategy, JSONFormatStrategy)
        assert strategy.format_name == "json"

    def test_select_protobuf_strategy(self) -> None:
        """Test selecting Protobuf strategy."""
        strategy = select_message_format_strategy("protobuf")

        assert isinstance(strategy, ProtobufFormatStrategy)
        assert strategy.format_name == "protobuf"

    def test_select_invalid_format_defaults_to_json(self) -> None:
        """Test that invalid format name defaults to JSON strategy."""
        strategy = select_message_format_strategy("invalid_format")

        assert isinstance(strategy, JSONFormatStrategy)
        assert strategy.format_name == "json"

    def test_select_empty_string_defaults_to_json(self) -> None:
        """Test that empty string defaults to JSON strategy."""
        strategy = select_message_format_strategy("")

        assert isinstance(strategy, JSONFormatStrategy)

    def test_select_case_sensitive(self) -> None:
        """Test that format selection is case-sensitive (lowercase expected)."""
        # Uppercase should not match 'protobuf' and should default to JSON
        strategy = select_message_format_strategy("PROTOBUF")

        assert isinstance(strategy, JSONFormatStrategy)

    def test_select_protobuf_lowercase(self) -> None:
        """Test that lowercase 'protobuf' correctly selects Protobuf strategy."""
        strategy = select_message_format_strategy("protobuf")

        assert isinstance(strategy, ProtobufFormatStrategy)

    @pytest.mark.parametrize(
        "format_name",
        [
            "messagepack",
            "cbor",
            "xml",
            "yaml",
            "unknown",
        ],
    )
    def test_unsupported_formats_default_to_json(
        self, format_name: str
    ) -> None:
        """Test that unsupported formats default to JSON."""
        strategy = select_message_format_strategy(format_name)

        assert isinstance(strategy, JSONFormatStrategy)
