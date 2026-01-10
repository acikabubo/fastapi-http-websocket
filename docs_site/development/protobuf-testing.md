# Protocol Buffers WebSocket Testing Guide

This document provides step-by-step instructions for testing the protobuf WebSocket implementation.

## Prerequisites

1. Docker services running: `make start`
2. Valid Keycloak access token
3. Postman or similar WebSocket client

## Getting a Valid Access Token

### Option 1: Using Keycloak Direct Grant (Password Flow)

```bash
# Login and get access token
curl -X POST "http://localhost:8080/realms/HW-App/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=auth-hw-frontend" \
  -d "username=acika" \
  -d "password=YOUR_PASSWORD" \
  -d "grant_type=password" | jq -r '.access_token'
```

### Option 2: Using Python Script

```python
from app.managers.keycloak_manager import KeycloakManager

kc = KeycloakManager()
token_response = kc.login("acika", "YOUR_PASSWORD")
access_token = token_response["access_token"]
print(f"Token: {access_token}")
```

## Test Scenarios

### Test 1: JSON Format (Default - Backwards Compatibility)

**WebSocket URL:**
```
ws://localhost:8000/web?Authorization=Bearer YOUR_ACCESS_TOKEN
```

**Request Message (JSON):**
```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": null,
  "data": {
    "page": 1,
    "per_page": 10
  }
}
```

**Expected Response (JSON):**
```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 0,
  "data": [
    {
      "id": 1,
      "name": "Author Name",
      "bio": "Author bio..."
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 10,
    "total": 25,
    "pages": 3
  }
}
```

### Test 2: Protobuf Format (New Feature)

**WebSocket URL:**
```
ws://localhost:8000/web?Authorization=Bearer YOUR_ACCESS_TOKEN&format=protobuf
```

**Python Client Example:**

```python
#!/usr/bin/env python3
"""
Protobuf WebSocket client test script.
"""
import asyncio
import json
import uuid
import websockets
from app.schemas.proto import Request, Response

async def test_protobuf_websocket():
    # Replace with your actual token
    token = "YOUR_ACCESS_TOKEN"
    url = f"ws://localhost:8000/web?Authorization=Bearer {token}&format=protobuf"

    async with websockets.connect(url) as websocket:
        # Create protobuf Request message
        request = Request()
        request.pkg_id = 1  # PkgID.GET_AUTHORS
        request.req_id = str(uuid.uuid4())
        request.data_json = json.dumps({
            "page": 1,
            "per_page": 10
        })

        # Serialize and send
        request_bytes = request.SerializeToString()
        print(f"Sending protobuf request ({len(request_bytes)} bytes)")
        await websocket.send(request_bytes)

        # Receive and parse response
        response_bytes = await websocket.recv()
        print(f"Received protobuf response ({len(response_bytes)} bytes)")

        response = Response()
        response.ParseFromString(response_bytes)

        print(f"Status Code: {response.status_code}")
        print(f"Package ID: {response.pkg_id}")
        print(f"Request ID: {response.req_id}")

        if response.data_json:
            data = json.loads(response.data_json)
            print(f"Data: {json.dumps(data, indent=2)}")

        if response.HasField("meta"):
            print(f"Pagination: Page {response.meta.page}/{response.meta.pages}, Total: {response.meta.total}")

if __name__ == "__main__":
    asyncio.run(test_protobuf_websocket())
```

**Running the test:**
```bash
# From project root
python examples/clients/websocket_protobuf_client.py
```

### Test 3: Invalid Format (Should Fallback to JSON)

**WebSocket URL:**
```
ws://localhost:8000/web?Authorization=Bearer YOUR_ACCESS_TOKEN&format=invalid
```

**Expected Behavior:**
- Server logs warning: "Invalid format 'invalid' specified, defaulting to json"
- Connection uses JSON format
- Works exactly like Test 1

### Test 4: Protobuf with Different pkg_id Values

**Test CREATE operation (if available):**

```python
async def test_create_author():
    token = "YOUR_ACCESS_TOKEN"
    url = f"ws://localhost:8000/web?Authorization=Bearer {token}&format=protobuf"

    async with websockets.connect(url) as websocket:
        request = Request()
        request.pkg_id = 2  # PkgID.CREATE_AUTHOR (check actual value)
        request.req_id = str(uuid.uuid4())
        request.data_json = json.dumps({
            "name": "New Author",
            "bio": "Test author created via protobuf"
        })

        await websocket.send(request.SerializeToString())

        response_bytes = await websocket.recv()
        response = Response()
        response.ParseFromString(response_bytes)

        print(f"Create Result: {response.status_code}")
        if response.data_json:
            print(f"Created: {response.data_json}")
```

### Test 5: Size Comparison (JSON vs Protobuf)

**Comparative test script:**

```python
import json
from app.schemas.proto import Request
from app.schemas.request import RequestModel
from uuid import uuid4
from app.api.ws.constants import PkgID

# Create same request in both formats
req_id = uuid4()
data = {"page": 1, "per_page": 20}

# JSON format
json_request = RequestModel(
    pkg_id=PkgID.GET_AUTHORS,
    req_id=req_id,
    data=data
)
json_size = len(json.dumps(json_request.model_dump()).encode())

# Protobuf format
proto_request = Request()
proto_request.pkg_id = PkgID.GET_AUTHORS.value
proto_request.req_id = str(req_id)
proto_request.data_json = json.dumps(data)
protobuf_size = len(proto_request.SerializeToString())

print(f"JSON size: {json_size} bytes")
print(f"Protobuf size: {protobuf_size} bytes")
print(f"Size reduction: {((json_size - protobuf_size) / json_size * 100):.1f}%")
```

## Testing with Postman

### Setup for JSON Format

1. **Create New WebSocket Request**
2. **Set URL:** `ws://localhost:8000/web?Authorization=Bearer YOUR_TOKEN`
3. **Connect**
4. **Send Message:**
   ```json
   {
     "pkg_id": 1,
     "req_id": "550e8400-e29b-41d4-a716-446655440000",
     "data": {"page": 1, "per_page": 10}
   }
   ```

### Setup for Protobuf Format

**Note:** Postman doesn't natively support sending binary protobuf messages. Use Python client or tools like `websocat` for protobuf testing.

Alternative: Use Postman's pre-request script to encode protobuf (requires additional setup).

## Testing with websocat (Command Line)

### JSON Format:
```bash
# Install websocat: cargo install websocat or download binary

echo '{"pkg_id": 1, "req_id": "550e8400-e29b-41d4-a716-446655440000", "data": {"page": 1}}' | \
  websocat "ws://localhost:8000/web?Authorization=Bearer YOUR_TOKEN"
```

### Protobuf Format:
```bash
# Requires pre-encoded protobuf message in a file
websocat --binary "ws://localhost:8000/web?Authorization=Bearer YOUR_TOKEN&format=protobuf" < request.pb
```

## Verification Checklist

- [ ] JSON format works (backwards compatibility)
- [ ] Protobuf format works with `?format=protobuf`
- [ ] Invalid format falls back to JSON with warning in logs
- [ ] Server logs show correct format detection
- [ ] Response format matches request format
- [ ] Protobuf messages are smaller than JSON
- [ ] Both formats produce identical data results
- [ ] Rate limiting works for both formats
- [ ] Authentication works for both formats
- [ ] Audit logs record correct message format

## Expected Server Logs

### For JSON Request:
```
DEBUG - Received JSON request: {'pkg_id': 1, 'req_id': '...', 'data': {...}}
DEBUG - Successfully sent json response for PkgID.GET_AUTHORS
```

### For Protobuf Request:
```
DEBUG - WebSocket connection using format: protobuf
DEBUG - Received protobuf request: pkg_id=PkgID.GET_AUTHORS
DEBUG - Successfully sent protobuf response for PkgID.GET_AUTHORS
```

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'google'"
**Solution:** Rebuild Docker container with protobuf dependencies:
```bash
make build
make stop && make start
```

### Error: "Connection rejected"
**Solution:** Check if token is valid and not expired. Get new token.

### Error: "Permission denied"
**Solution:** Ensure user has required roles for the pkg_id being accessed.

### Protobuf parsing fails
**Solution:**
- Verify `format=protobuf` query parameter is set
- Ensure message is properly serialized binary data
- Check protobuf schema matches (run `make protobuf-generate` if needed)

## Performance Testing

### Recommended Load Testing Tools:
- **k6** for WebSocket load testing
- **Artillery** for continuous load
- **locust** for distributed testing

### Sample k6 Script:
```javascript
import ws from 'k6/ws';
import { check } from 'k6';

export default function () {
  const url = 'ws://localhost:8000/web?Authorization=Bearer YOUR_TOKEN&format=protobuf';

  const res = ws.connect(url, function (socket) {
    socket.on('open', () => {
      // Send protobuf binary message
      socket.sendBinary(protobufMessage);
    });

    socket.on('message', (data) => {
      console.log('Received response:', data);
      socket.close();
    });
  });

  check(res, { 'status is 101': (r) => r && r.status === 101 });
}
```

## Next Steps

After successful testing:
1. Monitor Prometheus metrics for protobuf message processing
2. Compare performance (throughput, latency) between JSON and Protobuf
3. Update client applications to use protobuf for high-frequency messaging
4. Document migration path for existing clients
5. Consider adding compression for even smaller messages

## Related Files

- Protobuf schema: `proto/websocket.proto`
- Converter utilities: `app/utils/protobuf_converter.py`
- WebSocket consumer: `app/api/ws/consumers/web.py`
- Format negotiation: `app/api/ws/websocket.py`
- Python client example: `examples/clients/websocket_protobuf_client.py`
- Unit tests: `tests/test_protobuf_converter.py`
