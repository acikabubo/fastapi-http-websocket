# API and WS handers documentation

## Establish WebSocket conenction

```mermaid
sequenceDiagram
    actor C as Client
    participant WA as Web Application
    participant S as Backend-Server
    participant DB as PostgreSQL

    alt Establishing WebSocket connection
        C->>WA: <br/>
        WA->>S: GET /web
        WA->>S: Established WebSocket connection
        S->>WA: Send initial data to client
    end
```

## Make WebSocket Request/Response

### Request data format
```json
{
    "pkg_id": "<int>",
    "req_id": "<uuid>",
    "data": {...}
}
```

### Response data format
```json
{
    "pkg_id": "<int>",
    "req_id": "Same <UUID> like request",
    "status": "OK"
    "data": {...}
}
```

```mermaid
sequenceDiagram
    actor C as Client
    participant WA as Web Application
    participant S as BackendServer

    alt Make WebSocket Request/Response
        C->>WA: <br/>
        WA->>S: GET /web
        S-->>WA: 101 Switching Protocols
        WA->>S: Send request with data like above
        S->>S: Handler the request
        S-->WA: Return the response
    end
```

## Make HTTP Request/Response

```mermaid
sequenceDiagram
    actor C as Client
    participant WA as Web Application
    participant S as BackendServer


    alt Make HTTP Rest Request/Response
        C->>WA: <br/>
        WA->>S: GET /web
        S->>WA: Server send response
    end
```
