# Response Models

## Overview

This document describes the standard response models used across both HTTP and WebSocket APIs.

## HTTP Response Models

### Standard Response

HTTP endpoints return data directly with appropriate status codes:

```json
{
  "id": 1,
  "name": "John Doe"
}
```

### Paginated Response

Paginated endpoints return data with metadata:

```json
{
  "items": [...],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 42,
    "pages": 3
  }
}
```

### Error Response

```json
{
  "detail": "Error message"
}
```

## WebSocket Response Models

### ResponseModel

All WebSocket responses use the `ResponseModel` structure:

```python
class ResponseModel(BaseModel):
    pkg_id: int
    req_id: str
    status_code: int
    data: dict | list | None = None
    meta: MetadataModel | None = None
```

**Example Success Response:**

```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 0,
  "data": [{"id": 1, "name": "John Doe"}],
  "meta": null
}
```

**Example Error Response:**

```json
{
  "pkg_id": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 2,
  "data": {"msg": "Invalid data"},
  "meta": null
}
```

### MetadataModel

Pagination metadata for WebSocket responses:

```python
class MetadataModel(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
```

**Example:**

```json
{
  "page": 1,
  "per_page": 20,
  "total": 42,
  "pages": 3
}
```

## Helper Methods

### ResponseModel.success()

Create a success response:

```python
return ResponseModel.success(
    pkg_id=request.pkg_id,
    req_id=request.req_id,
    data=[author.model_dump() for author in authors]
)
```

### ResponseModel.err_msg()

Create an error response:

```python
return ResponseModel.err_msg(
    pkg_id=request.pkg_id,
    req_id=request.req_id,
    msg="Author not found",
    status_code=RSPCode.ERROR
)
```

## Response Status Codes

See [WebSocket API](websocket-api.md#response-code-reference-rspcode) for complete list of response codes.

## Related

- [HTTP API](http-api.md) - HTTP endpoints and responses
- [WebSocket API](websocket-api.md) - WebSocket message format
