"""Unit tests for ProtobufFormatStrategy."""

from uuid import uuid4

import pytest
from google.protobuf.message import DecodeError

from app.api.ws.constants import PkgID
from app.api.ws.formats.protobuf import ProtobufFormatStrategy
from app.schemas.proto import Request as ProtoRequest
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel


@pytest.fixture
def protobuf_strategy() -> ProtobufFormatStrategy:
    """Create ProtobufFormatStrategy instance."""
    return ProtobufFormatStrategy()


class TestProtobufFormatStrategy:
    """Test suite for ProtobufFormatStrategy."""

    def test_format_name(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test format_name property returns 'protobuf'."""
        assert protobuf_strategy.format_name == "protobuf"

    @pytest.mark.asyncio
    async def test_deserialize_valid_protobuf(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test deserializing valid Protobuf bytes."""
        # Create valid protobuf message
        req_id = uuid4()
        proto_request = ProtoRequest()
        proto_request.pkg_id = PkgID.GET_AUTHORS  # Use integer value
        proto_request.req_id = str(req_id)
        proto_request.data_json = '{"name": "Test"}'
        raw_data = proto_request.SerializeToString()

        result = await protobuf_strategy.deserialize(raw_data)

        assert isinstance(result, RequestModel)
        assert result.pkg_id == PkgID.GET_AUTHORS
        assert result.req_id == req_id
        assert result.data == {"name": "Test"}

    @pytest.mark.asyncio
    async def test_deserialize_malformed_bytes(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test deserializing malformed bytes raises DecodeError."""
        raw_data = b"invalid protobuf data"

        with pytest.raises(DecodeError):
            await protobuf_strategy.deserialize(raw_data)

    @pytest.mark.asyncio
    async def test_deserialize_dict_raises_value_error(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test deserializing dict raises ValueError (type guard)."""
        raw_data = {"pkg_id": "GET_AUTHORS"}  # type: ignore[assignment]

        with pytest.raises(
            ValueError,
            match="Protobuf strategy received dict - format mismatch",
        ):
            await protobuf_strategy.deserialize(raw_data)

    @pytest.mark.asyncio
    async def test_serialize_response(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test serializing ResponseModel to Protobuf bytes."""
        req_id = uuid4()
        response = ResponseModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=req_id,
            status_code=0,
            data={"authors": []},
        )

        result = await protobuf_strategy.serialize(response)

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_deserialize_empty_data(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test deserializing protobuf with empty data field."""
        req_id = uuid4()
        proto_request = ProtoRequest()
        proto_request.pkg_id = PkgID.GET_AUTHORS  # Use existing PkgID
        proto_request.req_id = str(req_id)
        proto_request.data_json = "{}"
        raw_data = proto_request.SerializeToString()

        result = await protobuf_strategy.deserialize(raw_data)

        assert result.pkg_id == PkgID.GET_AUTHORS
        assert result.req_id == req_id
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_serialize_error_response(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test serializing error response."""
        req_id = uuid4()
        response = ResponseModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=req_id,
            status_code=1,
            data={"error": "Not found"},
        )

        result = await protobuf_strategy.serialize(response)

        assert isinstance(result, bytes)
        # Verify it can be deserialized back (round-trip test)
        from app.schemas.proto import Response as ProtoResponse

        proto_response = ProtoResponse()
        proto_response.ParseFromString(result)
        assert proto_response.status_code == 1
        # data_json should contain error message
        import json

        data = json.loads(proto_response.data_json)
        assert data["error"] == "Not found"

    @pytest.mark.asyncio
    async def test_deserialize_invalid_json_in_data(
        self, protobuf_strategy: ProtobufFormatStrategy
    ) -> None:
        """Test deserializing protobuf with invalid JSON in data field raises ValueError."""
        req_id = uuid4()
        proto_request = ProtoRequest()
        proto_request.pkg_id = PkgID.GET_AUTHORS  # Use integer value
        proto_request.req_id = str(req_id)
        proto_request.data_json = "invalid json {{"
        raw_data = proto_request.SerializeToString()

        with pytest.raises(ValueError):
            await protobuf_strategy.deserialize(raw_data)
