# Rate Limiting

## Overview

The application implements Redis-based rate limiting for both HTTP and WebSocket connections to prevent abuse and ensure fair resource allocation.

## Configuration

Rate limiting is configured in `app/settings.py`:

```python
# HTTP Rate Limiting
RATE_LIMIT_ENABLED: bool = True
RATE_LIMIT_PER_MINUTE: int = 60  # Requests per minute
RATE_LIMIT_BURST: int = 10       # Burst allowance

# WebSocket Rate Limiting
WS_MAX_CONNECTIONS_PER_USER: int = 5     # Max concurrent connections
WS_MESSAGE_RATE_LIMIT: int = 100          # Messages per minute
```

## HTTP Rate Limiting

### Implementation

HTTP endpoints are protected by `RateLimitMiddleware`:

**Location:** `app/middlewares/rate_limit.py`

**Algorithm:** Sliding window with Redis sorted sets

**Key:** `user:{user_id}` or `ip:{ip_address}` for unauthenticated requests

### Response Headers

All HTTP responses include rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705320000
```

### Rate Limit Exceeded

When limit is exceeded, returns `429 Too Many Requests`:

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

### Excluded Paths

Some endpoints bypass rate limiting:

- `/health` - Health checks
- `/metrics` - Prometheus metrics
- `/docs` - API documentation
- `/redoc` - Alternative API docs
- `/openapi.json` - OpenAPI schema

## WebSocket Rate Limiting

### Connection Limiting

**Maximum Connections:** 5 per user (configurable)

**Implementation:** `ConnectionLimiter` in `app/utils/rate_limiter.py`

**Enforcement:** On connection in `PackageAuthWebSocketEndpoint.on_connect()`

**Rejection Code:** `1008` (Policy Violation)

```python
# Connection rejected
ws.close(1008, "Maximum concurrent connections exceeded")
```

### Message Rate Limiting

**Limit:** 100 messages per minute (configurable)

**Implementation:** `RateLimiter` in `app/utils/rate_limiter.py`

**Enforcement:** In `Web.on_receive()` before message processing

**Error Response:**

```json
{
  "pkg_id": 0,
  "req_id": "...",
  "status_code": 1,
  "data": {"msg": "Rate limit exceeded"}
}
```

## Client Implementation

### HTTP Clients

#### Handle Rate Limits

```python
import time
import requests

def api_call_with_retry(url, headers, max_retries=3):
    """Make API call with automatic retry on rate limit."""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

#### Check Remaining Limit

```python
response = requests.get(url, headers=headers)

remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
if remaining < 5:
    print(f"Warning: Only {remaining} requests remaining")
    time.sleep(1)  # Slow down
```

### WebSocket Clients

#### Monitor Connection Count

```javascript
let activeConnections = 0;
const MAX_CONNECTIONS = 5;

function connect() {
  if (activeConnections >= MAX_CONNECTIONS) {
    console.error('Max connections reached');
    return;
  }

  const ws = new WebSocket(`ws://localhost:8000/web?token=${token}`);

  ws.onopen = () => {
    activeConnections++;
  };

  ws.onclose = (event) => {
    activeConnections--;

    if (event.code === 1008) {
      console.error('Connection rejected: Rate limit exceeded');
    }
  };
}
```

#### Throttle Messages

```javascript
const messageQueue = [];
const MESSAGE_RATE = 100; // per minute
const MESSAGE_INTERVAL = 60000 / MESSAGE_RATE; // ms between messages

setInterval(() => {
  if (messageQueue.length > 0 && ws.readyState === WebSocket.OPEN) {
    const message = messageQueue.shift();
    ws.send(JSON.stringify(message));
  }
}, MESSAGE_INTERVAL);

function sendMessage(data) {
  messageQueue.push(data);
}
```

## Rate Limiter Implementation

### Sliding Window Algorithm

```python
async def check_rate_limit(
    self,
    key: str,
    limit: int,
    window_seconds: int,
    burst: int = 0
) -> tuple[bool, int]:
    """
    Check if request is within rate limit.

    Args:
        key: Rate limit key (e.g., "user:123")
        limit: Max requests in window
        window_seconds: Time window in seconds
        burst: Additional burst allowance

    Returns:
        (is_allowed, remaining_requests)
    """
    now = time.time()
    window_start = now - window_seconds

    # Remove old entries
    await redis.zremrangebyscore(key, '-inf', window_start)

    # Count requests in current window
    current_count = await redis.zcard(key)

    max_allowed = limit + burst

    if current_count >= max_allowed:
        return False, 0

    # Add current request
    await redis.zadd(key, {str(uuid.uuid4()): now})

    # Set expiry
    await redis.expire(key, window_seconds * 2)

    remaining = max_allowed - current_count - 1
    return True, remaining
```

### Connection Limiter

```python
async def add_connection(
    self,
    user_id: str,
    connection_id: str
) -> bool:
    """
    Add connection and check limit.

    Args:
        user_id: User identifier
        connection_id: Unique connection identifier

    Returns:
        True if connection allowed, False if limit exceeded
    """
    key = f"ws:connections:{user_id}"

    # Add connection to set
    await redis.sadd(key, connection_id)

    # Count connections
    count = await redis.scard(key)

    if count > self.max_connections:
        # Remove and reject
        await redis.srem(key, connection_id)
        return False

    return True
```

## Monitoring

### Prometheus Metrics

Rate limit violations are tracked:

```
# Rate limit hits
rate_limit_hits_total{limit_type="http"} 123
rate_limit_hits_total{limit_type="ws_connection"} 5
rate_limit_hits_total{limit_type="ws_message"} 45
```

### Logs

Rate limit events are logged:

```python
logger.warning(
    f"Rate limit exceeded for user {user_id}",
    extra={
        "user_id": user_id,
        "limit_type": "http",
        "current_count": current_count,
        "limit": limit
    }
)
```

## Tuning

### Adjusting Limits

Edit `app/settings.py` or set environment variables:

```bash
# HTTP
export RATE_LIMIT_PER_MINUTE=120
export RATE_LIMIT_BURST=20

# WebSocket
export WS_MAX_CONNECTIONS_PER_USER=10
export WS_MESSAGE_RATE_LIMIT=200
```

### Per-Endpoint Limits

Currently not supported - all endpoints share same limit. To implement:

1. Add endpoint-specific configuration
2. Modify middleware to check endpoint
3. Use different Redis keys per endpoint

## Testing

### Test Rate Limiting

```python
import pytest

@pytest.mark.asyncio
async def test_rate_limit():
    """Test rate limiting blocks excess requests."""
    rate_limiter = RateLimiter(redis)

    # Make requests up to limit
    for i in range(60):
        allowed, remaining = await rate_limiter.check_rate_limit(
            key="test:user",
            limit=60,
            window_seconds=60
        )
        assert allowed is True

    # Next request should be blocked
    allowed, remaining = await rate_limiter.check_rate_limit(
        key="test:user",
        limit=60,
        window_seconds=60
    )
    assert allowed is False
    assert remaining == 0
```

## Troubleshooting

### Redis Connection Issues

If rate limiting fails due to Redis errors:
- HTTP middleware **fails open** (allows requests)
- WebSocket connection limiter **fails closed** (denies connections)

### High False Positives

If legitimate users hit limits:
1. Increase `RATE_LIMIT_PER_MINUTE`
2. Increase `RATE_LIMIT_BURST` for traffic spikes
3. Implement per-user or per-role limits

### Performance Issues

If Redis becomes bottleneck:
1. Use Redis cluster for horizontal scaling
2. Implement local caching with eventual consistency
3. Use approximate counting algorithms

## Related

- [HTTP API](../api-reference/http-api.md#rate-limiting)
- [WebSocket API](../api-reference/websocket-api.md#rate-limiting)
- [Monitoring Guide](monitoring.md)
