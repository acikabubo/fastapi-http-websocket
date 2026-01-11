# Advanced Features & Best Practices

This document provides recommendations for advanced features you can add to your project based on production experience with this template.

## Table of Contents
- [Protocol Buffers (Protobuf) for WebSocket Communication](#protocol-buffers-protobuf-for-websocket-communication)
- [Performance Profiling with Scalene](#performance-profiling-with-scalene)
- [When to Use These Features](#when-to-use-these-features)

---

## Protocol Buffers (Protobuf) for WebSocket Communication

### Overview
Protocol Buffers provide a more efficient alternative to JSON for WebSocket communication, offering smaller message sizes and faster serialization.

### Benefits
- **40% smaller message size** - Binary encoding vs JSON text
- **3.3x faster serialization** - Measured in production workloads
- **Strong typing** - Schema validation with `.proto` files
- **Language agnostic** - Easy client implementation in any language
- **Backwards compatible** - Can run both JSON and Protobuf simultaneously

### When to Add Protobuf
Consider adding Protobuf support when:
- You have high-frequency WebSocket messaging (>100 messages/sec)
- Message size is a concern (mobile/limited bandwidth)
- You need clients in multiple languages
- You want stronger type safety and schema validation

### Implementation Steps

#### 1. Add Dependencies
```toml
# pyproject.toml
dependencies = [
    # ... existing dependencies
    "protobuf>=5.29.0",
    "grpcio-tools>=1.68.0",
]
```

#### 2. Create Proto Schema
Create `proto/websocket.proto`:
```protobuf
syntax = "proto3";

package websocket;

message Request {
  int32 pkg_id = 1;
  string req_id = 2;
  string method = 3;
  string data_json = 4;  // Flexible JSON payload
}

message Response {
  int32 pkg_id = 1;
  string req_id = 2;
  int32 status_code = 3;
  string data_json = 4;
  Metadata meta = 5;
}

message Metadata {
  int32 page = 1;
  int32 per_page = 2;
  int32 total = 3;
  int32 pages = 4;
}
```

#### 3. Add Makefile Commands
```makefile
# Makefile
protobuf-install:
	@uv sync --all-groups

protobuf-generate:
	@mkdir -p app/schemas/proto
	@uv run python -m grpc_tools.protoc \
		-I=proto \
		--python_out=app/schemas/proto \
		--pyi_out=app/schemas/proto \
		proto/websocket.proto

protobuf-clean:
	@rm -rf app/schemas/proto
```

#### 4. Create Converter Utilities
Create `app/utils/protobuf_converter.py`:
```python
"""Utilities for converting between Pydantic and Protobuf messages."""
import json
from app.schemas.proto import Request, Response
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel

def proto_to_pydantic_request(proto_req: Request) -> RequestModel:
    """Convert Protobuf Request to Pydantic RequestModel."""
    data = json.loads(proto_req.data_json) if proto_req.data_json else {}
    return RequestModel(
        pkg_id=proto_req.pkg_id,
        req_id=proto_req.req_id,
        method=proto_req.method or None,
        data=data,
    )

def serialize_response(response: ResponseModel, format: str = "json"):
    """Serialize ResponseModel to JSON or Protobuf format."""
    if format == "protobuf":
        proto_resp = Response()
        proto_resp.pkg_id = response.pkg_id
        proto_resp.req_id = str(response.req_id)
        proto_resp.status_code = response.status_code or 0
        if response.data:
            proto_resp.data_json = json.dumps(response.data)
        return proto_resp.SerializeToString()
    else:
        return response.model_dump()
```

#### 5. Update WebSocket Consumer
Modify `app/api/ws/consumers/web.py`:
```python
from app.schemas.proto import Request as ProtoRequest
from app.utils.protobuf_converter import (
    proto_to_pydantic_request,
    serialize_response,
)

async def on_receive(self, websocket, data: dict[str, Any] | bytes):
    # Detect format based on data type
    if isinstance(data, bytes):
        # Protobuf format
        proto_request = ProtoRequest()
        proto_request.ParseFromString(data)
        request = proto_to_pydantic_request(proto_request)
        message_format = "protobuf"
    else:
        # JSON format
        request = RequestModel(**data)
        message_format = "json"

    # Process request (format-agnostic)
    response = await pkg_router.handle_request(self.scope["user"], request)

    # Send response in same format as request
    if message_format == "protobuf":
        response_data = serialize_response(response, "protobuf")
        await websocket.send_bytes(response_data)
    else:
        await websocket.send_response(response)
```

#### 6. Update WebSocket Endpoint
Modify `app/api/ws/websocket.py`:
```python
class PackageAuthWebSocketEndpoint(WebSocketEndpoint):
    encoding = None  # Support both JSON and binary

    async def decode(self, websocket: WebSocket, message: dict):
        """Decode both JSON (text) and Protobuf (binary) messages."""
        if "text" in message:
            return json.loads(message["text"])
        elif "bytes" in message:
            return message["bytes"]
        return message.get("text", message.get("bytes", b""))
```

### Client Usage
```python
# Protobuf client
url = "ws://localhost:8000/web?token=TOKEN&format=protobuf"
request = Request()
request.pkg_id = 1
request.req_id = str(uuid.uuid4())
request.data_json = json.dumps({"page": 1})

await websocket.send(request.SerializeToString())
response_bytes = await websocket.recv()
response = Response()
response.ParseFromString(response_bytes)
```

### Performance Expectations
Based on production measurements:
- **Message size**: 40% reduction (e.g., 150 bytes → 90 bytes)
- **Serialization**: 3.3x faster (e.g., 0.3ms → 0.09ms)
- **Throughput**: Significant improvement at >100 msg/sec
- **Bandwidth**: 40% reduction in network traffic

---

## Performance Profiling with Scalene

### Overview
Scalene is a high-performance CPU, GPU, and memory profiler specifically designed for async Python applications.

### Benefits
- **Zero-overhead profiling** - Minimal performance impact
- **Line-level visibility** - See exactly which lines are slow
- **Async-aware** - Properly profiles async/await code
- **Memory profiling** - Identify memory leaks and inefficiencies
- **GPU profiling** - Track GPU usage if applicable

### When to Add Scalene
Use Scalene profiling when:
- You need to optimize WebSocket performance
- You're experiencing high CPU or memory usage
- You want to identify bottlenecks in request handling
- You're preparing for high-load production deployment

### Implementation Steps

#### 1. Add Dependencies
```toml
# pyproject.toml
[dependency-groups]
profiling = [
    "scalene>=1.5.0",
]
```

#### 2. Add Makefile Commands
```makefile
# Makefile
profile-install:
	@uv sync --group profiling

profile:
	@uv run --group profiling scalene run run_server.py

profile-view:
	@uv run --group profiling scalene view

profile-view-cli:
	@uv run --group profiling scalene view --cli

profile-clean:
	@rm -f scalene-profile.json
```

#### 3. Create Server Wrapper
Create `run_server.py`:
```python
#!/usr/bin/env python3
"""Server wrapper for Scalene profiling."""
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000)
```

#### 4. Add Settings (Optional)
```python
# app/settings.py
class Settings(BaseSettings):
    # ... existing settings

    # Profiling settings
    PROFILING_ENABLED: bool = False
    PROFILING_OUTPUT_DIR: str = "profiling_reports"
```

### Usage

**Basic profiling:**
```bash
# Run application with profiling
make profile

# Generate load (in another terminal)
# ... run your load tests ...

# Stop profiler (Ctrl+C)
# View report in browser
make profile-view

# Or view in terminal
make profile-view-cli
```

**Advanced profiling:**
```bash
# Profile only specific modules
scalene run --profile-only app/api/ws/ run_server.py

# CPU-only profiling (faster)
scalene run --cpu-only run_server.py

# Lower overhead mode
scalene run --reduced-profile run_server.py
```

### What to Profile

Focus profiling on:
1. **WebSocket handlers** - Identify slow request processing
2. **Database queries** - Find N+1 queries and missing indexes
3. **Serialization** - Pydantic validation and JSON encoding
4. **Business logic** - Complex computations and algorithms
5. **Memory usage** - Identify leaks and excessive allocations

### Interpreting Results

Scalene reports show:
- **CPU %**: Time spent on each line
- **Memory**: Allocations per line
- **Copy Volume**: Data copying overhead

Look for:
- Lines with >5% CPU usage
- Memory allocations in loops
- High copy volumes (inefficient data handling)

### Example Optimizations Found

Common bottlenecks discovered with Scalene:
- Pydantic validation in loops → Use `model_validate()` outside loop
- JSON serialization overhead → Consider `orjson` library
- List comprehensions in broadcast → Use async generators
- Database N+1 queries → Add eager loading
- Sync code in async → Use `run_in_executor()`

---

## When to Use These Features

### Project Maturity Guide

**Early Stage (MVP)**
- ✅ Use JSON for WebSocket (simpler debugging)
- ❌ Skip Protobuf (premature optimization)
- ❌ Skip profiling (no load yet)

**Growth Stage (100-1000 users)**
- ✅ Add basic monitoring (Prometheus metrics)
- ⚠️ Consider Protobuf if bandwidth is an issue
- ✅ Profile occasionally to identify obvious bottlenecks

**Scale Stage (1000+ concurrent users)**
- ✅ Add Protobuf for high-frequency messaging
- ✅ Regular profiling sessions
- ✅ Optimize based on real production data

### Resource Constraints

**Limited Bandwidth (Mobile, IoT)**
- ✅ Add Protobuf immediately - 40% size reduction matters

**High Message Frequency (>100/sec per connection)**
- ✅ Add Protobuf - serialization speed matters
- ✅ Profile regularly - every millisecond counts

**Complex Business Logic**
- ✅ Profile early - find algorithmic issues before scale

---

## Implementation Checklist

### Protobuf Implementation
- [ ] Add protobuf dependencies to `pyproject.toml`
- [ ] Create `proto/websocket.proto` schema
- [ ] Add Makefile commands for code generation
- [ ] Generate Python protobuf code
- [ ] Create converter utilities
- [ ] Update WebSocket consumer for dual-format
- [ ] Update WebSocket endpoint decode method
- [ ] Add unit tests for converters
- [ ] Create client examples
- [ ] Update documentation

### Profiling Setup
- [ ] Add Scalene to profiling dependency group
- [ ] Create `run_server.py` wrapper
- [ ] Add Makefile profiling commands
- [ ] Test profiling workflow
- [ ] Document profiling best practices
- [ ] Set up regular profiling schedule

---

## Additional Resources

### Protobuf
- [Protocol Buffers Documentation](https://protobuf.dev/)
- [grpcio-tools PyPI](https://pypi.org/project/grpcio-tools/)
- [Protobuf Python Tutorial](https://protobuf.dev/getting-started/pythontutorial/)

### Scalene
- [Scalene GitHub](https://github.com/plasma-umass/scalene)
- [Scalene Documentation](https://github.com/plasma-umass/scalene#readme)
- [Profiling Async Python](https://github.com/plasma-umass/scalene/wiki/Profiling-async-code)

### Performance Optimization
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/deployment/concepts/)
- [Async Python Best Practices](https://docs.python.org/3/library/asyncio-dev.html)
- [WebSocket Optimization Guide](https://websockets.readthedocs.io/en/stable/topics/performance.html)

---

## Questions?

If you implement these features and encounter issues:
1. Check the examples in the main project repository
2. Review the generated protobuf code for correctness
3. Profile before and after optimizations to measure impact
4. Consider your specific use case - not all optimizations apply to all scenarios

Remember: **Measure first, optimize second**. Use profiling to identify real bottlenecks before adding complexity.
