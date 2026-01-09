# Sequence Diagrams

This document provides detailed sequence diagrams for key flows in the application.

## Authentication Flow

### HTTP Login Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant KeycloakManager
    participant Keycloak
    participant Redis

    Client->>FastAPI: POST /login {username, password}
    FastAPI->>KeycloakManager: login(username, password)
    KeycloakManager->>Keycloak: Token request (OAuth2 password grant)
    Keycloak-->>KeycloakManager: {access_token, refresh_token, expires_in}
    KeycloakManager-->>FastAPI: Token data
    FastAPI->>Redis: Store user session
    Redis-->>FastAPI: OK
    FastAPI-->>Client: {access_token, refresh_token, expires_in}
```

### WebSocket Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant AuthBackend
    participant Keycloak
    participant ConnectionLimiter
    participant ConnectionManager

    Client->>WebSocket: Connect ws://host/web?token=<jwt>
    WebSocket->>AuthBackend: authenticate(connection)
    AuthBackend->>AuthBackend: Extract token from query params
    AuthBackend->>Keycloak: Validate JWT signature
    Keycloak-->>AuthBackend: Token valid, user claims
    AuthBackend-->>WebSocket: UserModel(sub, roles, ...)
    WebSocket->>ConnectionLimiter: check_limit(user_id)

    alt Connection limit exceeded
        ConnectionLimiter-->>WebSocket: Limit exceeded
        WebSocket-->>Client: Close 1008 (Policy Violation)
    else Limit OK
        ConnectionLimiter-->>WebSocket: OK
        WebSocket->>ConnectionManager: connect(websocket)
        ConnectionManager-->>WebSocket: Connection added
        WebSocket-->>Client: Connection established
    end
```

## HTTP Request Flow

### GET /authors with Filtering

```mermaid
sequenceDiagram
    participant Client
    participant PrometheusMiddleware
    participant RateLimitMiddleware
    participant AuthMiddleware
    participant Handler
    participant RBACDependency as require_roles()
    participant Database

    Client->>PrometheusMiddleware: GET /authors?name=John
    PrometheusMiddleware->>PrometheusMiddleware: Start metrics timer
    PrometheusMiddleware->>RateLimitMiddleware: Forward request

    RateLimitMiddleware->>RateLimitMiddleware: Get rate limit key
    RateLimitMiddleware->>RateLimitMiddleware: Check Redis counter

    alt Rate limit exceeded
        RateLimitMiddleware-->>Client: 429 Too Many Requests
    else Rate limit OK
        RateLimitMiddleware->>AuthMiddleware: Forward request

        AuthMiddleware->>AuthMiddleware: Extract Authorization header
        AuthMiddleware->>AuthMiddleware: Validate JWT token
        AuthMiddleware->>AuthMiddleware: Populate request.state.user

        alt Invalid token
            AuthMiddleware-->>Client: 401 Unauthorized
        else Valid token
            AuthMiddleware->>RBACDependency: Check permissions (FastAPI dependency)

            RBACDependency->>RBACDependency: Verify user has required roles

            alt Permission denied
                RBACDependency-->>Client: 403 Forbidden
            else Permission granted
                RBACDependency->>Handler: Forward to endpoint

                Handler->>Handler: Validate query params
                Handler->>Database: SELECT * FROM author WHERE name ILIKE '%John%'
                Database-->>Handler: [Author rows]
                Handler-->>RBACDependency: [Author list]
                RBACDependency-->>AuthMiddleware: Response
                AuthMiddleware-->>RateLimitMiddleware: Response
                RateLimitMiddleware->>RateLimitMiddleware: Add X-RateLimit headers
                RateLimitMiddleware-->>PrometheusMiddleware: Response
                PrometheusMiddleware->>PrometheusMiddleware: Record metrics
                PrometheusMiddleware-->>Client: 200 OK + [Authors]
            end
        end
    end
```

### POST /authors (Create)

```mermaid
sequenceDiagram
    participant Client
    participant Middleware
    participant Handler
    participant Session
    participant Database

    Client->>Middleware: POST /authors {name: "New Author"}
    Note over Middleware: Authentication & Authorization
    Middleware->>Handler: Validated request

    Handler->>Handler: Validate request body (Pydantic)

    alt Validation error
        Handler-->>Client: 422 Validation Error
    else Valid data
        Handler->>Repository: Inject AuthorRepository via Depends
        Repository-->>Handler: Repository instance

        Handler->>Repository: repo.create(author)
        Repository->>Database: INSERT INTO author VALUES (...)
        Database-->>Repository: Author with ID
        Repository-->>Handler: Created Author

        Handler->>Database: COMMIT transaction
        Database-->>Handler: OK

        Handler-->>Client: 200 OK + {id: 1, name: "New Author"}
    end
```

## WebSocket Request Flow

### GET_AUTHORS Request (PkgID: 1)

```mermaid
sequenceDiagram
    participant Client
    participant WebEndpoint
    participant RateLimiter
    participant PackageRouter
    participant RBACManager
    participant Handler
    participant Database

    Client->>WebEndpoint: Send JSON: {pkg_id: 1, req_id: "uuid", data: {filters: {name: "John"}}}

    WebEndpoint->>WebEndpoint: Parse JSON message
    WebEndpoint->>WebEndpoint: Create RequestModel

    WebEndpoint->>RateLimiter: check_rate_limit(user_id)

    alt Rate limit exceeded
        RateLimiter-->>WebEndpoint: Limit exceeded
        WebEndpoint-->>Client: {status_code: 1, msg: "Rate limit exceeded"}
    else Rate OK
        RateLimiter-->>WebEndpoint: OK

        WebEndpoint->>PackageRouter: handle_request(request)

        PackageRouter->>RBACManager: check_ws_permission(pkg_id, user)

        alt Permission denied
            RBACManager-->>PackageRouter: Permission denied
            PackageRouter-->>WebEndpoint: {status_code: 3, msg: "Permission denied"}
            WebEndpoint-->>Client: Error response
        else Permission granted
            RBACManager-->>PackageRouter: OK

            PackageRouter->>PackageRouter: Validate data against JSON schema

            alt Schema validation error
                PackageRouter-->>WebEndpoint: {status_code: 2, msg: "Invalid data"}
                WebEndpoint-->>Client: Error response
            else Valid schema
                PackageRouter->>Handler: Execute handler(request)

                Handler->>Database: SELECT * FROM author WHERE name ILIKE '%John%'
                Database-->>Handler: [Author rows]

                Handler->>Handler: Build ResponseModel
                Handler-->>PackageRouter: {status_code: 0, data: [...]}

                PackageRouter-->>WebEndpoint: ResponseModel
                WebEndpoint-->>Client: {pkg_id: 1, req_id: "uuid", status_code: 0, data: [...]}
            end
        end
    end
```

### GET_PAGINATED_AUTHORS Request (PkgID: 2)

```mermaid
sequenceDiagram
    participant Client
    participant WebEndpoint
    participant PackageRouter
    participant Handler
    participant PaginationUtil
    participant Database

    Client->>WebEndpoint: {pkg_id: 2, req_id: "uuid", data: {page: 1, per_page: 20}}

    Note over WebEndpoint: Rate limiting & auth checks passed

    WebEndpoint->>PackageRouter: handle_request(request)
    PackageRouter->>Handler: get_paginated_authors_handler(request)

    Handler->>PaginationUtil: get_paginated_results(Author, page=1, per_page=20)

    PaginationUtil->>Database: SELECT COUNT(id) FROM author
    Database-->>PaginationUtil: total=42

    PaginationUtil->>PaginationUtil: Calculate pages (42/20 = 3)

    PaginationUtil->>Database: SELECT * FROM author OFFSET 0 LIMIT 20
    Database-->>PaginationUtil: [20 Author rows]

    PaginationUtil-->>Handler: (results, MetadataModel{page: 1, per_page: 20, total: 42, pages: 3})

    Handler->>Handler: Build ResponseModel with meta
    Handler-->>WebEndpoint: {status_code: 0, data: [...], meta: {...}}

    WebEndpoint-->>Client: Complete response with pagination metadata
```

## Broadcast Flow

### Server-Initiated Broadcast

```mermaid
sequenceDiagram
    participant BackgroundTask
    participant ConnectionManager
    participant WebSocket1
    participant WebSocket2
    participant WebSocket3
    participant Client1
    participant Client2
    participant Client3

    BackgroundTask->>BackgroundTask: Event occurs (e.g., data update)
    BackgroundTask->>BackgroundTask: Build BroadcastDataModel
    BackgroundTask->>ConnectionManager: broadcast(message)

    ConnectionManager->>ConnectionManager: Create connections snapshot
    ConnectionManager->>ConnectionManager: asyncio.gather(...)

    par Broadcast to all clients
        ConnectionManager->>WebSocket1: send_json(message)
        WebSocket1-->>Client1: {pkg_id: 1, req_id: "00000000-...", data: {...}}
    and
        ConnectionManager->>WebSocket2: send_json(message)
        WebSocket2-->>Client2: {pkg_id: 1, req_id: "00000000-...", data: {...}}
    and
        ConnectionManager->>WebSocket3: send_json(message)

        Note over WebSocket3: Connection failed
        WebSocket3--xClient3: Exception
        ConnectionManager->>ConnectionManager: Safe error handling
        ConnectionManager->>ConnectionManager: disconnect(WebSocket3)
    end

    ConnectionManager-->>BackgroundTask: Broadcast complete
```

## Rate Limiting Flow

### Sliding Window Rate Limiting

```mermaid
sequenceDiagram
    participant Request
    participant RateLimiter
    participant Redis

    Request->>RateLimiter: check_rate_limit(key="user:john", limit=60, window=60s)

    RateLimiter->>RateLimiter: current_time = now()
    RateLimiter->>RateLimiter: window_start = current_time - 60

    RateLimiter->>Redis: ZREMRANGEBYSCORE(key, -inf, window_start)
    Note over Redis: Remove old requests outside window
    Redis-->>RateLimiter: Removed count

    RateLimiter->>Redis: ZCARD(key)
    Note over Redis: Count requests in current window
    Redis-->>RateLimiter: current_count=45

    alt current_count >= limit
        RateLimiter-->>Request: (False, 0) - Rate limit exceeded
        Note over Request: Return 429 error
    else current_count < limit
        RateLimiter->>Redis: ZADD(key, current_time, request_id)
        Note over Redis: Add current request to set
        Redis-->>RateLimiter: OK

        RateLimiter->>Redis: EXPIRE(key, window * 2)
        Note over Redis: Set TTL for automatic cleanup
        Redis-->>RateLimiter: OK

        RateLimiter->>RateLimiter: remaining = limit - current_count - 1
        RateLimiter-->>Request: (True, remaining) - Request allowed
        Note over Request: Continue processing
    end
```

### WebSocket Connection Limiting

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant ConnectionLimiter
    participant Redis

    Client->>WebSocket: Connect (user_id="user123")
    WebSocket->>ConnectionLimiter: add_connection(user_id, connection_id)

    ConnectionLimiter->>Redis: SADD("ws:connections:user123", connection_id)
    Redis-->>ConnectionLimiter: OK

    ConnectionLimiter->>Redis: SCARD("ws:connections:user123")
    Note over Redis: Count connections for user
    Redis-->>ConnectionLimiter: count=5

    alt count > max_connections (e.g., 5)
        ConnectionLimiter->>Redis: SREM("ws:connections:user123", connection_id)
        Redis-->>ConnectionLimiter: OK
        ConnectionLimiter-->>WebSocket: False - Limit exceeded
        WebSocket-->>Client: Close 1008 (Policy Violation)
    else count <= max_connections
        ConnectionLimiter-->>WebSocket: True - Connection allowed
        WebSocket-->>Client: Connection established
    end
```

## Error Handling Flow

### Handler Error Recovery

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant Database
    participant Logger

    Client->>Handler: Request with valid data

    Handler->>Database: Execute query

    alt Database error (SQLAlchemyError)
        Database--xHandler: SQLAlchemyError
        Handler->>Logger: log.error("Database error: ...")
        Handler->>Handler: Build error ResponseModel
        Handler-->>Client: {status_code: 1, msg: "Database error occurred"}
    else Validation error
        Database-->>Handler: Success
        Handler->>Handler: Process results
        Handler->>Handler: Validation fails
        Handler->>Logger: log.error("Validation error: ...")
        Handler-->>Client: {status_code: 2, msg: "Invalid data"}
    else Unexpected error
        Database-->>Handler: Success
        Handler->>Handler: Processing...
        Handler--xHandler: Unexpected exception
        Note over Handler: Exception propagates up
        Handler->>Logger: log.exception("Unexpected error")
        Handler-->>Client: {status_code: 1, msg: "Internal error"}
    else Success
        Database-->>Handler: Results
        Handler->>Handler: Process and format
        Handler-->>Client: {status_code: 0, data: [...]}
    end
```

## Health Check Flow

### Health Check with Dependency Verification

```mermaid
sequenceDiagram
    participant Client
    participant HealthEndpoint
    participant Database
    participant Redis

    Client->>HealthEndpoint: GET /health

    par Check all dependencies
        HealthEndpoint->>Database: SELECT 1

        alt Database OK
            Database-->>HealthEndpoint: Success
            HealthEndpoint->>HealthEndpoint: db_status = "healthy"
        else Database failed
            Database--xHealthEndpoint: Exception
            HealthEndpoint->>HealthEndpoint: db_status = "unhealthy"
        end
    and
        HealthEndpoint->>Redis: PING

        alt Redis OK
            Redis-->>HealthEndpoint: PONG
            HealthEndpoint->>HealthEndpoint: redis_status = "healthy"
        else Redis failed
            Redis--xHealthEndpoint: Exception
            HealthEndpoint->>HealthEndpoint: redis_status = "unhealthy"
        end
    end

    HealthEndpoint->>HealthEndpoint: Aggregate statuses

    alt All healthy
        HealthEndpoint-->>Client: 200 OK {status: "healthy", database: "healthy", redis: "healthy"}
    else Any unhealthy
        HealthEndpoint-->>Client: 503 Service Unavailable {status: "unhealthy", ...}
    end
```

## Metrics Collection Flow

### Prometheus Metrics Scraping

```mermaid
sequenceDiagram
    participant Prometheus
    participant MetricsEndpoint
    participant MetricsRegistry

    loop Every scrape_interval (15s)
        Prometheus->>MetricsEndpoint: GET /metrics

        MetricsEndpoint->>MetricsRegistry: Collect all metrics

        MetricsRegistry->>MetricsRegistry: Gather HTTP request counters
        MetricsRegistry->>MetricsRegistry: Gather WebSocket metrics
        MetricsRegistry->>MetricsRegistry: Gather application metrics

        MetricsRegistry-->>MetricsEndpoint: Metrics in text format

        MetricsEndpoint-->>Prometheus: text/plain metrics
        Note over MetricsEndpoint,Prometheus: # HELP http_requests_total...<br/># TYPE http_requests_total counter<br/>http_requests_total{...} 1234.0

        Prometheus->>Prometheus: Store time series data
        Prometheus->>Prometheus: Evaluate alerting rules
    end
```

## Notes

These diagrams use Mermaid syntax and can be rendered using:
- GitHub (automatic rendering)
- Mermaid Live Editor: https://mermaid.live/
- VS Code with Mermaid extension
- Documentation tools that support Mermaid

For complex flows, refer to the source code in:
- `app/middlewares/` - Middleware implementations
- `app/routing.py` - WebSocket routing logic
- `app/api/ws/handlers/` - WebSocket handlers
- `app/api/http/` - HTTP handlers
