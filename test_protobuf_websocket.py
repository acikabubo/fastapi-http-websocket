#!/usr/bin/env python3
"""
Quick test script for protobuf WebSocket implementation.

Usage:
    # Test JSON format (default)
    python test_protobuf_websocket.py json YOUR_ACCESS_TOKEN

    # Test Protobuf format
    python test_protobuf_websocket.py protobuf YOUR_ACCESS_TOKEN

    # Test both and compare
    python test_protobuf_websocket.py both YOUR_ACCESS_TOKEN
"""
import asyncio
import json
import sys
import uuid
from typing import Literal

import websockets

# Import protobuf classes
from app.schemas.proto import Request as ProtoRequest
from app.schemas.proto import Response as ProtoResponse


async def test_json_format(token: str) -> dict:
    """Test WebSocket with JSON format."""
    # Encode token properly for URL
    from urllib.parse import quote
    encoded_token = quote(f"Bearer {token}", safe='')
    url = f"ws://localhost:8000/web?Authorization={encoded_token}"

    print("\n" + "=" * 60)
    print("Testing JSON Format")
    print("=" * 60)
    print(f"URL: ws://localhost:8000/web?Authorization=Bearer ...\n")

    try:
        async with websockets.connect(url) as websocket:
            # Prepare JSON request
            request = {
                "pkg_id": 2,  # GET_AUTHORS
                "req_id": str(uuid.uuid4()),
                "method": None,
                "data": {"page": 1, "per_page": 5},
            }

            request_json = json.dumps(request)
            request_size = len(request_json.encode())

            print(f"Sending JSON request ({request_size} bytes):")
            print(json.dumps(request, indent=2))

            # Send request
            await websocket.send(request_json)

            # Receive response
            response_text = await websocket.recv()
            response_size = len(response_text.encode())

            print(f"\nReceived JSON response ({response_size} bytes):")
            response = json.loads(response_text)
            print(json.dumps(response, indent=2))

            return {
                "format": "json",
                "request_size": request_size,
                "response_size": response_size,
                "status_code": response.get("status_code"),
                "success": response.get("status_code") == 0,
            }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"format": "json", "success": False, "error": str(e)}


async def test_protobuf_format(token: str) -> dict:
    """Test WebSocket with Protobuf format."""
    # Encode token properly for URL
    from urllib.parse import quote
    encoded_token = quote(f"Bearer {token}", safe='')
    url = f"ws://localhost:8000/web?Authorization={encoded_token}&format=protobuf"

    print("\n" + "=" * 60)
    print("Testing Protobuf Format")
    print("=" * 60)
    print(f"URL: ws://localhost:8000/web?Authorization=Bearer ...&format=protobuf\n")

    try:
        async with websockets.connect(url) as websocket:
            # Prepare protobuf request
            request = ProtoRequest()
            request.pkg_id = 2  # GET_AUTHORS
            request.req_id = str(uuid.uuid4())
            request.data_json = json.dumps({"page": 1, "per_page": 5})

            request_bytes = request.SerializeToString()
            request_size = len(request_bytes)

            print(f"Sending Protobuf request ({request_size} bytes):")
            print(f"  pkg_id: {request.pkg_id}")
            print(f"  req_id: {request.req_id}")
            print(f"  data: {request.data_json}")

            # Send request
            await websocket.send(request_bytes)

            # Receive response
            response_bytes = await websocket.recv()
            response_size = len(response_bytes)

            print(f"\nReceived Protobuf response ({response_size} bytes)")

            # Parse response
            response = ProtoResponse()
            response.ParseFromString(response_bytes)

            print(f"  pkg_id: {response.pkg_id}")
            print(f"  req_id: {response.req_id}")
            print(f"  status_code: {response.status_code}")

            if response.data_json:
                data = json.loads(response.data_json)
                print(f"  data: {json.dumps(data, indent=2)}")

            if response.HasField("meta"):
                print(
                    f"  meta: Page {response.meta.page}/{response.meta.pages}, Total: {response.meta.total}"
                )

            return {
                "format": "protobuf",
                "request_size": request_size,
                "response_size": response_size,
                "status_code": response.status_code,
                "success": response.status_code == 0,
            }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return {"format": "protobuf", "success": False, "error": str(e)}


async def test_both_formats(token: str):
    """Test both formats and compare results."""
    json_result = await test_json_format(token)
    protobuf_result = await test_protobuf_format(token)

    print("\n" + "=" * 60)
    print("Comparison Summary")
    print("=" * 60)

    if json_result.get("success") and protobuf_result.get("success"):
        print("✅ Both formats work correctly!\n")

        json_req_size = json_result["request_size"]
        proto_req_size = protobuf_result["request_size"]
        req_reduction = ((json_req_size - proto_req_size) / json_req_size) * 100

        json_resp_size = json_result["response_size"]
        proto_resp_size = protobuf_result["response_size"]
        resp_reduction = (
            (json_resp_size - proto_resp_size) / json_resp_size
        ) * 100

        print("Request Size Comparison:")
        print(f"  JSON:     {json_req_size:5d} bytes")
        print(f"  Protobuf: {proto_req_size:5d} bytes")
        print(f"  Reduction: {req_reduction:5.1f}%\n")

        print("Response Size Comparison:")
        print(f"  JSON:     {json_resp_size:5d} bytes")
        print(f"  Protobuf: {proto_resp_size:5d} bytes")
        print(f"  Reduction: {resp_reduction:5.1f}%\n")

        print("Recommendations:")
        if req_reduction > 20 or resp_reduction > 20:
            print(
                "  🚀 Protobuf shows significant size savings - recommended for high-frequency messaging"
            )
        else:
            print(
                "  📊 Size difference is minimal - choose based on client capabilities"
            )

    else:
        print("❌ One or both formats failed:\n")
        print(f"  JSON:     {'✅ Success' if json_result.get('success') else '❌ Failed'}")
        if "error" in json_result:
            print(f"    Error: {json_result['error']}")

        print(f"  Protobuf: {'✅ Success' if protobuf_result.get('success') else '❌ Failed'}")
        if "error" in protobuf_result:
            print(f"    Error: {protobuf_result['error']}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nExample:")
        print(
            "  python test_protobuf_websocket.py both eyJhbGciOiJSUzI1NiIsInR5cCI6..."
        )
        sys.exit(1)

    mode: Literal["json", "protobuf", "both"] = sys.argv[1].lower()
    token = sys.argv[2]

    if mode == "json":
        await test_json_format(token)
    elif mode == "protobuf":
        await test_protobuf_format(token)
    elif mode == "both":
        await test_both_formats(token)
    else:
        print(f"Invalid mode: {mode}")
        print("Use: json, protobuf, or both")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
