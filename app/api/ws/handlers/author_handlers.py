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
from sqlalchemy.exc import SQLAlchemyError

from app.api.ws.constants import PkgID, RSPCode
from app.api.ws.validation import validator
from app.commands.author_commands import (
    CreateAuthorCommand,
    CreateAuthorInput,
    GetAuthorsCommand,
    GetAuthorsInput,
)
from app.logging import logger
from app.models.author import Author
from app.repositories.author_repository import AuthorRepository
from app.routing import pkg_router
from app.schemas.generic_typing import JsonSchemaType
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
from app.storage.db import async_session, get_paginated_results

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
    try:
        async with async_session() as session:
            # Create repository with session
            repo = AuthorRepository(session)

            # Create command with repository
            command = GetAuthorsCommand(repo)

            # Parse input from request data
            input_data = GetAuthorsInput(**request.data)

            # Execute command (same business logic as HTTP handler!)
            authors = await command.execute(input_data)

            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data=[author.model_dump() for author in authors],
            )
    except ValueError as e:
        # Business logic validation errors
        logger.error(f"Validation error in get_authors: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg=str(e),
            status_code=RSPCode.INVALID_DATA,
        )
    except SQLAlchemyError as e:
        # Database errors
        logger.error(f"Database error in get_authors: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Database error occurred",
            status_code=RSPCode.ERROR,
        )
    except (ValidationError, AttributeError) as e:
        # Pydantic validation errors
        logger.error(f"Invalid request data in get_authors: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Invalid filter parameters",
            status_code=RSPCode.INVALID_DATA,
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
    },
    "additionalProperties": False,
}


@pkg_router.register(
    PkgID.GET_PAGINATED_AUTHORS,
    json_schema=get_paginated_authors_schema,
    validator_callback=validator,
    roles=["get-authors"],
)
async def get_paginated_authors_handler(
    request: RequestModel,
) -> ResponseModel[Author]:
    """
    WebSocket handler to get paginated authors.

    Request Data:
        {
            "page": int (default: 1),
            "per_page": int (default: 20),
            "filters": dict (optional) - e.g., {"id": 1, "name": "John"}
        }

    Response Data: List of author objects with pagination metadata.

    Example:
        {
            "pkg_id": 2,
            "req_id": "uuid-here",
            "data": [...],
            "meta": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "pages": 5
            }
        }
    """
    try:
        authors, meta = await get_paginated_results(Author, **request.data)

        return ResponseModel(
            pkg_id=request.pkg_id,
            req_id=request.req_id,
            data=[author.model_dump() for author in authors],
            meta=meta,
        )
    except SQLAlchemyError as ex:
        logger.error(f"Database error retrieving paginated authors: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Database error occurred",
            status_code=RSPCode.ERROR,
        )
    except (ValidationError, AttributeError) as ex:
        logger.error(f"Validation error: {ex}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Invalid pagination parameters",
            status_code=RSPCode.INVALID_DATA,
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
    try:
        async with async_session() as session:
            async with session.begin():
                # Create repository with session
                repo = AuthorRepository(session)

                # Create command with repository
                command = CreateAuthorCommand(repo)

                # Parse input from request data
                input_data = CreateAuthorInput(**request.data)

                # Execute command
                author = await command.execute(input_data)

                return ResponseModel(
                    pkg_id=request.pkg_id,
                    req_id=request.req_id,
                    data=author.model_dump(),
                )
    except ValueError as e:
        # Business logic validation (e.g., duplicate name)
        logger.error(f"Validation error in create_author: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg=str(e),
            status_code=RSPCode.INVALID_DATA,
        )
    except SQLAlchemyError as e:
        # Database errors
        logger.error(f"Database error in create_author: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Database error occurred",
            status_code=RSPCode.ERROR,
        )
    except (ValidationError, AttributeError) as e:
        # Pydantic validation errors
        logger.error(f"Invalid request data in create_author: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="Invalid author data",
            status_code=RSPCode.INVALID_DATA,
        )


