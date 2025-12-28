"""
Utilities for converting between Pydantic models and Protobuf messages.

Provides bidirectional conversion between JSON-based Pydantic models
and binary Protocol Buffers for efficient WebSocket communication.
"""

import json
from typing import Any
from uuid import UUID

from app.api.ws.constants import PkgID, RSPCode
from app.schemas.proto import Request, Response
from app.schemas.request import RequestModel
from app.schemas.response import MetadataModel, ResponseModel


def pydantic_to_proto_request(pydantic_req: RequestModel) -> Request:
    """
    Convert Pydantic RequestModel to Protobuf Request.

    Args:
        pydantic_req: Pydantic RequestModel instance.

    Returns:
        Protobuf Request message.

    Example:
        >>> req = RequestModel(pkg_id=PkgID.GET_AUTHORS, req_id=UUID(...), data={})
        >>> proto_req = pydantic_to_proto_request(req)
        >>> proto_bytes = proto_req.SerializeToString()
    """
    proto_req = Request()
    proto_req.pkg_id = pydantic_req.pkg_id.value
    proto_req.req_id = str(pydantic_req.req_id)
    proto_req.method = pydantic_req.method or ""

    # Serialize data as JSON string
    if pydantic_req.data:
        proto_req.data_json = json.dumps(pydantic_req.data)
    else:
        proto_req.data_json = "{}"

    return proto_req


def proto_to_pydantic_request(proto_req: Request) -> RequestModel:
    """
    Convert Protobuf Request to Pydantic RequestModel.

    Args:
        proto_req: Protobuf Request message.

    Returns:
        Pydantic RequestModel instance.

    Example:
        >>> proto_req = Request.FromString(binary_data)
        >>> pydantic_req = proto_to_pydantic_request(proto_req)
    """
    # Deserialize JSON data
    data = json.loads(proto_req.data_json) if proto_req.data_json else {}

    return RequestModel(
        pkg_id=PkgID(proto_req.pkg_id),
        req_id=UUID(proto_req.req_id),
        method=proto_req.method if proto_req.method else None,
        data=data,
    )


def pydantic_to_proto_response(pydantic_resp: ResponseModel[Any]) -> Response:
    """
    Convert Pydantic ResponseModel to Protobuf Response.

    Args:
        pydantic_resp: Pydantic ResponseModel instance.

    Returns:
        Protobuf Response message.

    Example:
        >>> resp = ResponseModel.success(PkgID.GET_AUTHORS, UUID(...), data={})
        >>> proto_resp = pydantic_to_proto_response(resp)
        >>> proto_bytes = proto_resp.SerializeToString()
    """
    proto_resp = Response()
    proto_resp.pkg_id = pydantic_resp.pkg_id.value
    proto_resp.req_id = str(pydantic_resp.req_id)
    proto_resp.status_code = (
        pydantic_resp.status_code.value if pydantic_resp.status_code else 0
    )

    # Serialize data as JSON string
    if pydantic_resp.data:
        # Handle both dict and list data
        proto_resp.data_json = json.dumps(
            pydantic_resp.data,
            default=lambda obj: (
                obj.model_dump() if hasattr(obj, "model_dump") else str(obj)
            ),
        )
    else:
        proto_resp.data_json = "{}"

    # Add metadata if present
    if pydantic_resp.meta:
        if isinstance(pydantic_resp.meta, MetadataModel):
            proto_resp.meta.page = pydantic_resp.meta.page
            proto_resp.meta.per_page = pydantic_resp.meta.per_page
            proto_resp.meta.total = pydantic_resp.meta.total
            proto_resp.meta.pages = pydantic_resp.meta.pages
        elif isinstance(pydantic_resp.meta, dict):
            # Handle dict metadata
            proto_resp.meta.page = pydantic_resp.meta.get("page", 1)
            proto_resp.meta.per_page = pydantic_resp.meta.get("per_page", 20)
            proto_resp.meta.total = pydantic_resp.meta.get("total", 0)
            proto_resp.meta.pages = pydantic_resp.meta.get("pages", 0)

    return proto_resp


def proto_to_pydantic_response(proto_resp: Response) -> ResponseModel[Any]:
    """
    Convert Protobuf Response to Pydantic ResponseModel.

    Args:
        proto_resp: Protobuf Response message.

    Returns:
        Pydantic ResponseModel instance.

    Example:
        >>> proto_resp = Response.FromString(binary_data)
        >>> pydantic_resp = proto_to_pydantic_response(proto_resp)
    """
    # Deserialize JSON data
    data = json.loads(proto_resp.data_json) if proto_resp.data_json else None

    # Convert metadata if present
    meta = None
    if proto_resp.HasField("meta"):
        meta = MetadataModel(
            page=proto_resp.meta.page,
            per_page=proto_resp.meta.per_page,
            total=proto_resp.meta.total,
            pages=proto_resp.meta.pages,
        )

    return ResponseModel(
        pkg_id=PkgID(proto_resp.pkg_id),
        req_id=UUID(proto_resp.req_id),
        status_code=RSPCode(proto_resp.status_code),
        data=data,
        meta=meta,
    )


def detect_message_format(data: bytes | str) -> str:
    """
    Detect if message is JSON or Protobuf format.

    Args:
        data: Message data (bytes or string).

    Returns:
        "protobuf" if binary data, "json" if text/JSON.

    Example:
        >>> detect_message_format(b"\\x08\\x01\\x12\\x24...")  # "protobuf"
        >>> detect_message_format('{"pkg_id": 1}')  # "json"
    """
    if isinstance(data, bytes):
        # Check if it's valid JSON bytes
        try:
            json.loads(data.decode("utf-8"))
            return "json"
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "protobuf"
    else:
        # String data is assumed to be JSON
        return "json"


def serialize_response(
    response: ResponseModel[Any], format: str = "json"
) -> bytes | dict[str, Any]:
    """
    Serialize ResponseModel to specified format.

    Args:
        response: ResponseModel instance to serialize.
        format: Target format ("json" or "protobuf").

    Returns:
        Serialized data (dict for JSON, bytes for protobuf).

    Example:
        >>> resp = ResponseModel.success(PkgID.GET_AUTHORS, UUID(...), data={})
        >>> json_data = serialize_response(resp, "json")
        >>> proto_data = serialize_response(resp, "protobuf")
    """
    if format == "protobuf":
        proto_resp = pydantic_to_proto_response(response)
        return proto_resp.SerializeToString()
    else:  # json
        return response.model_dump()
