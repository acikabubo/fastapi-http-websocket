"""
Example WebSocket client using Protocol Buffers for communication.

This client demonstrates how to connect to the FastAPI WebSocket server
using Protocol Buffers for efficient binary message serialization.

Requirements:
    pip install websockets protobuf

Usage:
    python examples/clients/websocket_protobuf_client.py
"""

import asyncio
import json
import uuid

import websockets

# Import generated protobuf classes
# Note: You need to generate these from proto/websocket.proto
from app.schemas.proto import Request, Response


async def connect_with_protobuf(token: str, pkg_id: int, data: dict):
    """
    Connect to WebSocket server using Protobuf format.

    Args:
        token: Authentication token from Keycloak
        pkg_id: Package ID to route the request
        data: Request data payload
    """
    # WebSocket URL with format=protobuf query parameter
    url = f"ws://localhost:8000/web?token={token}&format=protobuf"

    async with websockets.connect(url) as websocket:
        print(f"✓ Connected to {url}")

        # Create protobuf Request message
        request = Request()
        request.pkg_id = pkg_id
        request.req_id = str(uuid.uuid4())
        request.method = ""
        request.data_json = json.dumps(data)

        # Serialize to bytes
        request_bytes = request.SerializeToString()

        print(f"→ Sending protobuf request ({len(request_bytes)} bytes)")
        print(f"  pkg_id: {pkg_id}")
        print(f"  req_id: {request.req_id}")
        print(f"  data: {data}")

        # Send binary protobuf message
        await websocket.send(request_bytes)

        # Receive binary response
        response_bytes = await websocket.recv()

        print(f"← Received protobuf response ({len(response_bytes)} bytes)")

        # Parse protobuf Response
        response = Response()
        response.ParseFromString(response_bytes)

        print(f"  pkg_id: {response.pkg_id}")
        print(f"  req_id: {response.req_id}")
        print(f"  status_code: {response.status_code}")

        # Parse JSON data from response
        response_data = (
            json.loads(response.data_json) if response.data_json else {}
        )
        print(f"  data: {response_data}")

        # Check if response has metadata (pagination)
        if response.HasField("meta"):
            print("  pagination:")
            print(f"    page: {response.meta.page}")
            print(f"    per_page: {response.meta.per_page}")
            print(f"    total: {response.meta.total}")
            print(f"    pages: {response.meta.pages}")


async def connect_with_json(token: str, pkg_id: int, data: dict):
    """
    Connect to WebSocket server using JSON format (for comparison).

    Args:
        token: Authentication token from Keycloak
        pkg_id: Package ID to route the request
        data: Request data payload
    """
    # WebSocket URL with default JSON format
    url = f"ws://localhost:8000/web?token={token}"

    async with websockets.connect(url) as websocket:
        print(f"✓ Connected to {url}")

        # Create JSON request
        request = {
            "pkg_id": pkg_id,
            "req_id": str(uuid.uuid4()),
            "method": "",
            "data": data,
        }

        request_json = json.dumps(request)

        print(f"→ Sending JSON request ({len(request_json)} bytes)")
        print(f"  {request_json}")

        # Send JSON message
        await websocket.send(request_json)

        # Receive JSON response
        response_json = await websocket.recv()

        print(f"← Received JSON response ({len(response_json)} bytes)")
        print(f"  {response_json}")

        response = json.loads(response_json)
        print(f"  status_code: {response.get('status_code')}")


async def compare_formats(token: str, pkg_id: int, data: dict):
    """
    Compare Protobuf vs JSON message sizes and formats.

    Args:
        token: Authentication token
        pkg_id: Package ID
        data: Request data
    """
    print("=" * 60)
    print("PROTOBUF FORMAT")
    print("=" * 60)
    await connect_with_protobuf(token, pkg_id, data)

    print("\n" + "=" * 60)
    print("JSON FORMAT")
    print("=" * 60)
    await connect_with_json(token, pkg_id, data)


async def main():
    """Main example demonstrating protobuf WebSocket client."""
    # Replace with your actual token from Keycloak
    token = "YOUR_KEYCLOAK_TOKEN_HERE"

    # Example: Get authors (assuming PkgID.GET_AUTHORS = 1)
    pkg_id = 1
    data = {}

    try:
        await compare_formats(token, pkg_id, data)
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
