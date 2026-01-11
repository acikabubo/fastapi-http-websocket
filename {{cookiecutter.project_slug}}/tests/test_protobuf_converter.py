"""
Unit tests for protobuf converter utilities.

Tests bidirectional conversion between Pydantic models and Protocol Buffers.
"""

import json
from uuid import uuid4


from {{cookiecutter.module_name}}.api.ws.constants import PkgID, RSPCode
from {{cookiecutter.module_name}}.schemas.proto import Request as ProtoRequest
from {{cookiecutter.module_name}}.schemas.proto import Response as ProtoResponse
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import MetadataModel, ResponseModel
from {{cookiecutter.module_name}}.utils.protobuf_converter import (
    detect_message_format,
    proto_to_pydantic_request,
    proto_to_pydantic_response,
    pydantic_to_proto_request,
    pydantic_to_proto_response,
    serialize_response,
)


class TestPydanticToProtoRequest:
    """Test conversion from Pydantic RequestModel to Protobuf Request."""

    def test_basic_request_conversion(self):
        """Test converting a basic request without data."""
        req_id = uuid4()
        pydantic_req = RequestModel(
            pkg_id=PkgID.TEST_HANDLER, req_id=req_id, data={}
        )

        proto_req = pydantic_to_proto_request(pydantic_req)

        assert proto_req.pkg_id == PkgID.TEST_HANDLER.value
        assert proto_req.req_id == str(req_id)
        assert proto_req.data_json == "{}"

    def test_request_with_data(self):
        """Test converting a request with data payload."""
        req_id = uuid4()
        data = {"name": "John Doe", "age": 30, "active": True}

        pydantic_req = RequestModel(
            pkg_id=PkgID.TEST_HANDLER, req_id=req_id, data=data
        )

        proto_req = pydantic_to_proto_request(pydantic_req)

        assert proto_req.pkg_id == PkgID.TEST_HANDLER.value
        assert proto_req.req_id == str(req_id)
        assert json.loads(proto_req.data_json) == data

    def test_request_with_method(self):
        """Test converting a request with method field."""
        req_id = uuid4()
        pydantic_req = RequestModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            method="custom_method",
            data={},
        )

        proto_req = pydantic_to_proto_request(pydantic_req)

        assert proto_req.method == "custom_method"


class TestProtoToPydanticRequest:
    """Test conversion from Protobuf Request to Pydantic RequestModel."""

    def test_basic_proto_to_pydantic(self):
        """Test converting a basic protobuf request."""
        req_id = str(uuid4())
        proto_req = ProtoRequest()
        proto_req.pkg_id = PkgID.TEST_HANDLER.value
        proto_req.req_id = req_id
        proto_req.data_json = "{}"

        pydantic_req = proto_to_pydantic_request(proto_req)

        assert pydantic_req.pkg_id == PkgID.TEST_HANDLER
        assert str(pydantic_req.req_id) == req_id
        assert pydantic_req.data == {}

    def test_proto_with_data_to_pydantic(self):
        """Test converting protobuf request with data payload."""
        req_id = str(uuid4())
        data = {"filters": {"status": "active"}, "page": 1}

        proto_req = ProtoRequest()
        proto_req.pkg_id = PkgID.TEST_HANDLER.value
        proto_req.req_id = req_id
        proto_req.data_json = json.dumps(data)

        pydantic_req = proto_to_pydantic_request(proto_req)

        assert pydantic_req.data == data


class TestPydanticToProtoResponse:
    """Test conversion from Pydantic ResponseModel to Protobuf Response."""

    def test_success_response_conversion(self):
        """Test converting a successful response."""
        req_id = uuid4()
        data = {"items": [{"id": 1, "name": "Author 1"}]}

        pydantic_resp = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            status_code=RSPCode.OK,
            data=data,
        )

        proto_resp = pydantic_to_proto_response(pydantic_resp)

        assert proto_resp.pkg_id == PkgID.TEST_HANDLER.value
        assert proto_resp.req_id == str(req_id)
        assert proto_resp.status_code == RSPCode.OK.value
        assert json.loads(proto_resp.data_json) == data

    def test_error_response_conversion(self):
        """Test converting an error response."""
        req_id = uuid4()
        pydantic_resp = ResponseModel.err_msg(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            msg="Not found",
            status_code=RSPCode.ERROR,
        )

        proto_resp = pydantic_to_proto_response(pydantic_resp)

        assert proto_resp.status_code == RSPCode.ERROR.value
        response_data = json.loads(proto_resp.data_json)
        assert response_data["msg"] == "Not found"

    def test_response_with_metadata(self):
        """Test converting response with pagination metadata."""
        req_id = uuid4()
        metadata = MetadataModel(page=1, per_page=20, total=100, pages=5)

        pydantic_resp = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            status_code=RSPCode.OK,
            data={"items": []},
            meta=metadata,
        )

        proto_resp = pydantic_to_proto_response(pydantic_resp)

        assert proto_resp.HasField("meta")
        assert proto_resp.meta.page == 1
        assert proto_resp.meta.per_page == 20
        assert proto_resp.meta.total == 100
        assert proto_resp.meta.pages == 5


class TestProtoToPydanticResponse:
    """Test conversion from Protobuf Response to Pydantic ResponseModel."""

    def test_basic_proto_response_to_pydantic(self):
        """Test converting basic protobuf response."""
        req_id = str(uuid4())
        data = {"result": "success"}

        proto_resp = ProtoResponse()
        proto_resp.pkg_id = PkgID.TEST_HANDLER.value
        proto_resp.req_id = req_id
        proto_resp.status_code = RSPCode.OK.value
        proto_resp.data_json = json.dumps(data)

        pydantic_resp = proto_to_pydantic_response(proto_resp)

        assert pydantic_resp.pkg_id == PkgID.TEST_HANDLER
        assert str(pydantic_resp.req_id) == req_id
        assert pydantic_resp.status_code == RSPCode.OK
        assert pydantic_resp.data == data

    def test_proto_response_with_metadata_to_pydantic(self):
        """Test converting protobuf response with metadata."""
        req_id = str(uuid4())

        proto_resp = ProtoResponse()
        proto_resp.pkg_id = PkgID.TEST_HANDLER.value
        proto_resp.req_id = req_id
        proto_resp.status_code = RSPCode.OK.value
        proto_resp.data_json = json.dumps({"items": []})

        # Set metadata
        proto_resp.meta.page = 2
        proto_resp.meta.per_page = 10
        proto_resp.meta.total = 50
        proto_resp.meta.pages = 5

        pydantic_resp = proto_to_pydantic_response(proto_resp)

        assert pydantic_resp.meta is not None
        assert isinstance(pydantic_resp.meta, MetadataModel)
        assert pydantic_resp.meta.page == 2
        assert pydantic_resp.meta.per_page == 10


class TestBidirectionalConversion:
    """Test round-trip conversion: Pydantic → Proto → Pydantic."""

    def test_request_round_trip(self):
        """Test request conversion round-trip preserves data."""
        req_id = uuid4()
        original = RequestModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            method="test",
            data={"key": "value"},
        )

        # Convert to proto and back
        proto = pydantic_to_proto_request(original)
        converted = proto_to_pydantic_request(proto)

        assert converted.pkg_id == original.pkg_id
        assert converted.req_id == original.req_id
        assert converted.method == original.method
        assert converted.data == original.data

    def test_response_round_trip(self):
        """Test response conversion round-trip preserves data."""
        req_id = uuid4()
        original = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=req_id,
            status_code=RSPCode.OK,
            data={"items": [1, 2, 3]},
            meta=MetadataModel(page=1, per_page=20, total=3, pages=1),
        )

        # Convert to proto and back
        proto = pydantic_to_proto_response(original)
        converted = proto_to_pydantic_response(proto)

        assert converted.pkg_id == original.pkg_id
        assert converted.req_id == original.req_id
        assert converted.status_code == original.status_code
        assert converted.data == original.data
        assert converted.meta.page == original.meta.page


class TestMessageFormatDetection:
    """Test automatic format detection."""

    def test_detect_json_string(self):
        """Test detecting JSON string format."""
        json_data = '{"pkg_id": 1, "req_id": "test"}'
        assert detect_message_format(json_data) == "json"

    def test_detect_json_bytes(self):
        """Test detecting JSON bytes format."""
        json_bytes = b'{"pkg_id": 1, "req_id": "test"}'
        assert detect_message_format(json_bytes) == "json"

    def test_detect_protobuf_bytes(self):
        """Test detecting protobuf binary format."""
        # Create a protobuf message and serialize it
        proto_req = ProtoRequest()
        proto_req.pkg_id = 1
        proto_req.req_id = str(uuid4())
        proto_req.data_json = "{}"

        protobuf_bytes = proto_req.SerializeToString()
        assert detect_message_format(protobuf_bytes) == "protobuf"


class TestSerializeResponse:
    """Test response serialization to different formats."""

    def test_serialize_to_json(self):
        """Test serializing response to JSON format."""
        response = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=uuid4(),
            status_code=RSPCode.OK,
            data={"test": "data"},
        )

        result = serialize_response(response, "json")

        assert isinstance(result, dict)
        assert result["pkg_id"] == PkgID.TEST_HANDLER
        assert result["status_code"] == RSPCode.OK
        assert result["data"] == {"test": "data"}

    def test_serialize_to_protobuf(self):
        """Test serializing response to Protobuf format."""
        response = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=uuid4(),
            status_code=RSPCode.OK,
            data={"test": "data"},
        )

        result = serialize_response(response, "protobuf")

        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify it can be deserialized
        proto_resp = ProtoResponse()
        proto_resp.ParseFromString(result)
        assert proto_resp.pkg_id == PkgID.TEST_HANDLER.value
