"""Unit tests for JSONFormatStrategy."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.ws.constants import PkgID
from app.api.ws.formats.json import JSONFormatStrategy
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel


@pytest.fixture
def json_strategy() -> JSONFormatStrategy:
    """Create JSONFormatStrategy instance."""
    return JSONFormatStrategy()


class TestJSONFormatStrategy:
    """Test suite for JSONFormatStrategy."""

    def test_format_name(self, json_strategy: JSONFormatStrategy) -> None:
        """Test format_name property returns 'json'."""
        assert json_strategy.format_name == "json"

    @pytest.mark.asyncio
    async def test_deserialize_valid_json(
        self, json_strategy: JSONFormatStrategy
    ) -> None:
        """Test deserializing valid JSON data."""
        req_id = uuid4()
        raw_data = {
            "pkg_id": PkgID.GET_AUTHORS,  # Can be enum or int
            "req_id": str(req_id),
            "data": {"name": "Test"},
        }

        result = await json_strategy.deserialize(raw_data)

        assert isinstance(result, RequestModel)
        assert result.pkg_id == PkgID.GET_AUTHORS
        assert result.req_id == req_id
        assert result.data == {"name": "Test"}

    @pytest.mark.asyncio
    async def test_deserialize_invalid_schema(
        self, json_strategy: JSONFormatStrategy
    ) -> None:
        """Test deserializing JSON with invalid schema raises ValidationError."""
        raw_data = {"invalid_field": "value"}

        with pytest.raises(ValidationError):
            await json_strategy.deserialize(raw_data)

    @pytest.mark.asyncio
    async def test_deserialize_bytes_raises_value_error(
        self, json_strategy: JSONFormatStrategy
    ) -> None:
        """Test deserializing bytes raises ValueError (type guard)."""
        raw_data = b"some bytes"

        with pytest.raises(
            ValueError, match="JSON strategy received bytes - format mismatch"
        ):
            await json_strategy.deserialize(raw_data)

    @pytest.mark.asyncio
    async def test_serialize_response(
        self, json_strategy: JSONFormatStrategy
    ) -> None:
        """Test serializing ResponseModel to dict."""
        req_id = uuid4()
        response = ResponseModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=req_id,
            status_code=0,
            data={"authors": []},
        )

        result = await json_strategy.serialize(response)

        assert isinstance(result, dict)
        assert (
            result["pkg_id"] == PkgID.GET_AUTHORS
        )  # Pydantic keeps enum instance
        assert result["req_id"] == req_id  # UUID instance
        assert result["status_code"] == 0
        assert result["data"] == {"authors": []}

    @pytest.mark.asyncio
    async def test_deserialize_minimal_request(
        self, json_strategy: JSONFormatStrategy
    ) -> None:
        """Test deserializing minimal valid request."""
        req_id = uuid4()
        raw_data = {"pkg_id": PkgID.GET_AUTHORS, "req_id": str(req_id)}

        result = await json_strategy.deserialize(raw_data)

        assert result.pkg_id == PkgID.GET_AUTHORS
        assert result.req_id == req_id
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_serialize_error_response(
        self, json_strategy: JSONFormatStrategy
    ) -> None:
        """Test serializing error response."""
        req_id = uuid4()
        response = ResponseModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=req_id,
            status_code=1,
            data={"error": "Not found"},
        )

        result = await json_strategy.serialize(response)

        assert result["status_code"] == 1
        assert result["data"]["error"] == "Not found"
