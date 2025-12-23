# WebSocket Performance Profiling with Scalene

This guide provides practical examples for profiling WebSocket performance using Scalene.

## Quick Start

### 1. Install Scalene

```bash
# Using uv (recommended)
uv sync --group profiling

# Or using pip
pip install scalene
```

### 2. Enable Profiling

Add to `docker/.srv_env`:

```bash
PROFILING_ENABLED=true
PROFILING_OUTPUT_DIR=profiling_reports
PROFILING_INTERVAL_SECONDS=30
```

### 3. Run with Scalene

```bash
# Basic profiling
scalene --html --outfile report.html -- uvicorn app:application

# With reduced overhead
scalene --reduced-profile --html --outfile report.html -- uvicorn app:application
```

## Common Profiling Scenarios

### Scenario 1: Profile WebSocket Broadcast Performance

**Problem**: Broadcast operation slowing down with >1000 connections

**Solution**:

```bash
# 1. Start application with profiling
scalene \
  --html \
  --outfile profiling_reports/broadcast_profile.html \
  --profile-only app/managers/websocket_connection_manager.py \
  --cpu-percent-threshold 2 \
  -- uvicorn app:application

# 2. Connect 1000+ WebSocket clients
# Use websocket-bench or custom script

# 3. Send broadcast messages
# Trigger broadcast via API or WebSocket

# 4. Stop application (Ctrl+C)
# Review report in profiling_reports/broadcast_profile.html
```

**What to Look For**:
- High CPU% on broadcast loop
- Memory allocations in message serialization
- JSON encoding overhead

### Scenario 2: Profile Connection Authentication

**Problem**: Slow connection establishment with Keycloak

**Solution**:

```bash
scalene \
  --html \
  --outfile profiling_reports/auth_profile.html \
  --profile-only app/api/ws/websocket.py \
  --profile-only app/auth.py \
  -- uvicorn app:application

# Connect/disconnect many WebSocket clients rapidly
# Review authentication overhead in report
```

**What to Look For**:
- JWT decode time
- Redis session lookup overhead
- Keycloak API calls

### Scenario 3: Profile Message Handler Performance

**Problem**: High latency in WebSocket message handling

**Solution**:

```bash
scalene \
  --html \
  --outfile profiling_reports/handler_profile.html \
  --profile-only app/api/ws/handlers/ \
  --profile-only app/routing.py \
  -- uvicorn app:application

# Send high-volume messages through WebSocket
# Review handler execution time
```

**What to Look For**:
- Pydantic validation overhead
- Database query time
- RBAC permission checking

### Scenario 4: Memory Leak Detection

**Problem**: Memory usage growing over time

**Solution**:

```bash
scalene \
  --html \
  --outfile profiling_reports/memory_profile.html \
  --memory-only \
  -- uvicorn app:application

# Run application for extended period (30+ minutes)
# Connect/disconnect WebSocket clients repeatedly
# Review memory allocation patterns
```

**What to Look For**:
- Growing memory allocations
- Unclosed connections
- Cached data accumulation

## Docker Profiling

### Profile Inside Docker Container

```bash
# Enter container
docker exec -it hw-server-shell bash

# Install scalene (if not in image)
pip install scalene

# Run profiling
scalene --html --outfile /app/profiling_reports/docker_profile.html \
  -- uvicorn app:application --host 0.0.0.0 --port 8000

# Access report from host
open profiling_reports/docker_profile.html
```

### Mount Profiling Directory

Add to `docker-compose.yml`:

```yaml
services:
  shell:
    volumes:
      - ./profiling_reports:/app/profiling_reports
```

## Load Testing with Profiling

### Using Locust

Create `locustfile.py`:

```python
from locust import HttpUser, between, task
import websocket
import json

class WebSocketUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def connect_websocket(self):
        ws = websocket.create_connection("ws://localhost:8000/web")

        # Send request
        ws.send(json.dumps({
            "pkg_id": 1,
            "req_id": "test-" + str(self.environment.runner.user_count),
            "data": {"test": "data"}
        }))

        # Receive response
        response = ws.recv()

        ws.close()
```

Run with profiling:

```bash
# Terminal 1: Start app with Scalene
scalene --html --outfile profiling_reports/load_test.html \
  -- uvicorn app:application

# Terminal 2: Run load test
locust -f locustfile.py --host http://localhost:8000 --users 1000 --spawn-rate 100

# Stop both when done
# Review load_test.html report
```

### Using Custom Script

```python
import asyncio
import websockets
import json

async def connect_and_send(url, num_messages):
    async with websockets.connect(url) as ws:
        for i in range(num_messages):
            await ws.send(json.dumps({
                "pkg_id": 1,
                "req_id": f"req-{i}",
                "data": {"message": f"test-{i}"}
            }))
            response = await ws.recv()

async def main():
    url = "ws://localhost:8000/web?token=YOUR_TOKEN"

    # Spawn 1000 concurrent connections
    tasks = [connect_and_send(url, 100) for _ in range(1000)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

Run with profiling:

```bash
# Start app with Scalene
scalene --html --outfile profiling_reports/concurrent_test.html \
  --reduced-profile \
  -- uvicorn app:application

# Run load test in another terminal
python load_test.py
```

## Analyzing Scalene Reports

### Understanding the Report

Scalene HTML reports contain:

1. **Summary Bar**: Total CPU/memory usage
2. **File List**: All profiled files with metrics
3. **Line-by-Line**: Detailed breakdown per line
4. **Timeline**: Resource usage over time

### Key Metrics

| Metric | Meaning | Action |
|--------|---------|--------|
| CPU % > 10% | Hot spot | Optimize this line |
| Memory MB > 100 | High allocation | Reduce allocations, use generators |
| Copy MB > 50 | Excessive copying | Avoid unnecessary data copies |
| GPU % | GPU usage | Leverage GPU if high compute |

### Common Patterns

**High CPU in JSON Serialization**:
```python
# Before (slow)
json.dumps([item.dict() for item in items])

# After (fast with orjson)
import orjson
orjson.dumps([item.dict() for item in items])
```

**High Memory in List Comprehension**:
```python
# Before (high memory)
results = [process(item) for item in large_list]

# After (generator)
results = (process(item) for item in large_list)
```

**Blocking Async Calls**:
```python
# Before (blocks event loop)
def sync_operation():
    return expensive_computation()

# After (non-blocking)
async def async_operation():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, expensive_computation)
```

## API Endpoints

### Check Profiling Status

```bash
curl http://localhost:8000/api/profiling/status

{
  "enabled": true,
  "scalene_installed": true,
  "output_directory": "profiling_reports",
  "interval_seconds": 30
}
```

### List Reports

```bash
curl http://localhost:8000/api/profiling/reports

{
  "reports": [
    {
      "filename": "broadcast_profile.html",
      "size_bytes": 250000,
      "created_at": 1706019000
    }
  ],
  "total_count": 1
}
```

### Download Report

```bash
curl http://localhost:8000/api/profiling/reports/broadcast_profile.html > report.html
open report.html
```

### Delete Report

```bash
curl -X DELETE http://localhost:8000/api/profiling/reports/broadcast_profile.html
```

## Best Practices

### DO ✅

- Profile under realistic load conditions
- Run for at least 30 seconds to collect meaningful data
- Use `--reduced-profile` in production
- Focus on lines with >5% CPU usage
- Save reports for historical comparison
- Cross-reference with Prometheus metrics
- Profile specific modules with `--profile-only`

### DON'T ❌

- Profile without load (won't show bottlenecks)
- Run profiling in production without `--reduced-profile`
- Ignore memory allocations in loops
- Profile with debug logging enabled (adds overhead)
- Compare reports from different load levels
- Profile with hot-reload enabled (uvicorn --reload)

## Troubleshooting

### Scalene Not Found

```bash
# Check installation
python -m scalene --version

# Reinstall if needed
uv sync --group profiling
```

### Permission Denied on Report

```bash
# Fix permissions
mkdir -p profiling_reports
chmod 755 profiling_reports
```

### No Data in Report

```bash
# Ensure app runs long enough
scalene --html --outfile report.html -- uvicorn app:application &
sleep 60  # Let it run for 60 seconds
pkill scalene
```

### High Overhead

```bash
# Use reduced profiling mode
scalene --reduced-profile --html --outfile report.html -- uvicorn app:application
```

## Advanced Usage

### Profile Only Critical Path

```bash
scalene \
  --html \
  --outfile report.html \
  --profile-only app/api/ws/ \
  --profile-exclude app/api/ws/constants.py \
  -- uvicorn app:application
```

### CPU-Only Profiling (Fastest)

```bash
scalene \
  --cpu-only \
  --html \
  --outfile report.html \
  -- uvicorn app:application
```

### Memory-Only Profiling

```bash
scalene \
  --memory-only \
  --html \
  --outfile report.html \
  -- uvicorn app:application
```

### Virtual Time (Better for Async)

```bash
scalene \
  --use-virtual-time \
  --html \
  --outfile report.html \
  -- uvicorn app:application
```

## Integration with CI/CD

Add profiling to your CI pipeline:

```yaml
# .github/workflows/profile.yml
name: Profile Performance

on:
  pull_request:
    paths:
      - 'app/api/ws/**'

jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: uv sync --group profiling

      - name: Run profiling
        run: |
          scalene --html --outfile profile.html \
            --reduced-profile \
            -- uvicorn app:application &
          sleep 60
          pkill scalene

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: profiling-report
          path: profile.html
```

## References

- [Scalene GitHub](https://github.com/plasma-umass/scalene)
- [Scalene Documentation](https://github.com/plasma-umass/scalene#scalene-a-scripting-language-profiler-for-python)
- [Profiling Async Python](https://docs.python.org/3/library/profile.html)
- Project profiling module: `app/utils/profiling.py`
- Profiling API: `app/api/http/profiling.py`
