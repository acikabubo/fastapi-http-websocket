"""
WebSocket handlers using Repository + Command pattern.

This file demonstrates how to use the same Command classes in WebSocket
handlers that are used in HTTP handlers (author.py).

Compare with app/api/http/author.py to see how the same
business logic is shared between HTTP and WebSocket.

Key Benefits:
- Business logic reuse (same commands in HTTP and WS)
- Easy to test (commands can be tested independently)
- Consistent behavior across protocols
"""

from pydantic import ValidationError

from app.api.ws.constants import PkgID
from app.api.ws.validation import validator
from app.commands.author_commands import (
    CreateAuthorCommand,
    CreateAuthorInput,
    GetAuthorsCommand,
    GetAuthorsInput,
)
from app.models.author import Author
from app.repositories.author_repository import AuthorRepository
from app.routing import pkg_router
from app.schemas.filters import AuthorFilters
from app.schemas.generic_typing import JsonSchemaType
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.storage.db import async_session, get_paginated_results
from app.utils.error_handler import handle_ws_errors

# ============================================================================
# GET AUTHORS (Using Repository + Command Pattern)
# ============================================================================

get_authors_schema: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "search_term": {"type": "string"},
    },
    "additionalProperties": False,
}


@pkg_router.register(
    PkgID.GET_AUTHORS,
    json_schema=get_authors_schema,
    validator_callback=validator,
    roles=["get-authors"],
)
@handle_ws_errors
async def get_authors_handler(request: RequestModel) -> ResponseModel[Author]:
    """
    WebSocket handler to get authors using Repository + Command pattern.

    This handler uses the SAME GetAuthorsCommand that is used in the HTTP
    handler (author.py). This demonstrates how business logic
    can be reused across different protocols.

    Request Data:
        {
            "id": int (optional),
            "name": str (optional),
            "search_term": str (optional)
        }

    Response Data: List of author objects.

    Example:
        {
            "pkg_id": 1,
            "req_id": "uuid-here",
            "data": {
                "id": 1,
                "name": "John",
                "search_term": null
            }
        }
    """
    async with async_session() as session:
        # Create repository with session
        repo = AuthorRepository(session)

        # Create command with repository
        command = GetAuthorsCommand(repo)

        # Parse input from request data
        input_data = GetAuthorsInput(**(request.data or {}))

        # Execute command (same business logic as HTTP handler!)
        authors = await command.execute(input_data)

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[author.model_dump() for author in authors],
        )


# ============================================================================
# GET PAGINATED AUTHORS
# ============================================================================

get_paginated_authors_schema: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "filters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "page": {"type": "integer"},
        "per_page": {"type": "integer"},
        "cursor": {"type": "string"},  # Cursor for cursor-based pagination
        "eager_load": {  # Relationships to eager load (prevents N+1 queries)
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


@pkg_router.register(
    PkgID.GET_PAGINATED_AUTHORS,
    json_schema=get_paginated_authors_schema,
    validator_callback=validator,
    roles=["get-authors"],
)
@handle_ws_errors
async def get_paginated_authors_handler(
    request: RequestModel,
) -> ResponseModel[Author]:
    """
    WebSocket handler to get paginated authors with cursor and eager loading support.

    Supports both offset-based (traditional) and cursor-based pagination.
    Cursor-based pagination provides consistent O(1) performance and stable results.

    Request Data:
        {
            "page": int (default: 1) - For offset pagination,
            "per_page": int (default: 20),
            "filters": dict (optional) - e.g., {"id": 1, "name": "John"},
            "cursor": str (optional) - For cursor-based pagination,
            "eager_load": list[str] (optional) - Relationships to load, e.g., ["books"]
        }

    Response Data: List of author objects with pagination metadata.

    Example (offset-based with type-safe filters):
        Request: {"page": 1, "per_page": 20, "filters": {"name": "John"}}
        Response: {
            "pkg_id": 2,
            "req_id": "uuid-here",
            "data": [...],
            "meta": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "pages": 5,
                "next_cursor": null,
                "has_more": true
            }
        }

    Example (cursor-based with eager loading):
        Request: {"per_page": 20, "cursor": "MTA=", "eager_load": ["books"]}
        Response: {
            "pkg_id": 2,
            "req_id": "uuid-here",
            "data": [...],  # Authors with books preloaded
            "meta": {
                "page": 1,
                "per_page": 20,
                "total": 0,  # Skipped for cursor pagination
                "pages": 0,
                "next_cursor": "MjA=",  # Use for next page
                "has_more": true
            }
        }
    """
    # Extract request parameters
    data = request.data or {}
    page = data.get("page", 1)
    per_page = data.get("per_page")
    cursor = data.get("cursor")
    eager_load = data.get("eager_load")

    # Parse filters with type-safe Pydantic schema
    filters = None
    if "filters" in data:
        try:
            filters = AuthorFilters(**data["filters"])
        except ValidationError as e:
            # Return validation error response
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=f"Invalid filter parameters: {str(e)}",
            )

    # Get paginated results with type-safe filters
    authors, meta = await get_paginated_results(
        Author,
        page=page,
        per_page=per_page,
        filters=filters,
        cursor=cursor,
        eager_load=eager_load,
    )

    return ResponseModel(
        pkg_id=request.pkg_id,
        req_id=request.req_id,
        data=[author.model_dump() for author in authors],
        meta=meta,
    )


# ============================================================================
# CREATE AUTHOR (Using Repository + Command Pattern)
# ============================================================================

create_author_schema: JsonSchemaType = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
    },
    "required": ["name"],
    "additionalProperties": False,
}


@pkg_router.register(
    PkgID.CREATE_AUTHOR,
    json_schema=create_author_schema,
    validator_callback=validator,
    roles=["create-author"],
)
@handle_ws_errors
async def create_author_handler(
    request: RequestModel,
) -> ResponseModel[Author]:
    """
    WebSocket handler to create author using Repository + Command pattern.

    Uses the SAME CreateAuthorCommand as the HTTP handler, ensuring
    consistent business logic (duplicate name checking) across protocols.

    Request Data:
        {
            "name": str (required, min length 1)
        }

    Response Data: Created author object.
    """
    async with async_session() as session:
        async with session.begin():
            # Create repository with session
            repo = AuthorRepository(session)

            # Create command with repository
            command = CreateAuthorCommand(repo)

            # Parse input from request data
            input_data = CreateAuthorInput(**(request.data or {}))

            # Execute command
            author = await command.execute(input_data)

            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data=author.model_dump(),
            )
