"""
Error handler decorators for unified exception handling across protocols.

This module provides decorators that automatically convert AppException instances
into appropriate HTTP or WebSocket responses with standardized error envelopes,
eliminating duplicate try/except blocks in handlers.

The decorators use unified error envelopes that provide consistent error formatting
across both HTTP and WebSocket protocols.
"""

import inspect
from functools import wraps
from typing import Any, Callable

from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.ws.constants import RSPCode
from app.exceptions import AppException
from app.logging import logger
from app.schemas.errors import ErrorCode, ErrorEnvelope, HTTPErrorResponse
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel


def handle_http_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for HTTP endpoints to convert AppException to unified error envelope.

    Automatically catches AppException instances and converts them to
    JSONResponse with structured error envelope format.

    Args:
        func: The HTTP endpoint function to wrap.

    Returns:
        Wrapped function that handles exceptions.

    Example:
        ```python
        @router.post("/authors")
        @handle_http_errors
        async def create_author(
            data: CreateAuthorInput, repo: AuthorRepoDep
        ) -> Author:
            command = CreateAuthorCommand(repo)
            return await command.execute(data)  # No try/except needed!
        ```

        Error response format:
        ```json
        {
            "error": {
                "code": "validation_error",
                "message": "Author name is required",
                "details": {"field": "name"}
            }
        }
        ```
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except AppException as ex:
            logger.warning(
                f"AppException in {func.__name__}: {ex.message}",
                extra={"exception_type": type(ex).__name__},
            )
            return JSONResponse(
                status_code=ex.http_status,
                content=ex.to_http_response().model_dump(),
            )
        except SQLAlchemyError as ex:
            logger.error(
                f"Database error in {func.__name__}: {ex}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content=HTTPErrorResponse(
                    error=ErrorEnvelope(
                        code=ErrorCode.DATABASE_ERROR,
                        msg="Database error occurred",
                    )
                ).model_dump(),
            )

    return wrapper


def handle_ws_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for WebSocket handlers to convert AppException to unified error envelope.

    Automatically catches AppException instances and converts them to
    WebSocket error responses with structured error envelope in data field.

    Args:
        func: The WebSocket handler function to wrap.

    Returns:
        Wrapped function that handles exceptions.

    Example:
        ```python
        @pkg_router.register(PkgID.CREATE_AUTHOR, roles=["create-author"])
        @handle_ws_errors
        async def create_author_handler(
            request: RequestModel,
        ) -> ResponseModel[Any]:
            async with async_session() as session:
                repo = AuthorRepository(session)
                command = CreateAuthorCommand(repo)
                author = await command.execute(
                    CreateAuthorInput(**request.data)
                )
                return ResponseModel.success(
                    request.pkg_id, request.req_id, data=author.model_dump()
                )
        ```

        Error response format:
        ```json
        {
            "pkg_id": 3,
            "req_id": "123e4567-e89b-12d3-a456-426614174000",
            "status_code": 2,
            "data": {
                "code": "validation_error",
                "message": "Author name is required",
                "details": {"field": "name"}
            }
        }
        ```
    """

    @wraps(func)
    async def wrapper(
        request: RequestModel, *args: Any, **kwargs: Any
    ) -> ResponseModel[Any]:
        try:
            return await func(request, *args, **kwargs)
        except AppException as ex:
            logger.warning(
                f"AppException in {func.__name__}: {ex.message}",
                extra={
                    "exception_type": type(ex).__name__,
                    "pkg_id": request.pkg_id,
                    "req_id": request.req_id,
                },
            )
            error_response = ex.to_ws_response(request.pkg_id, request.req_id)
            # Convert to ResponseModel for backward compatibility
            return ResponseModel(
                pkg_id=error_response.pkg_id,
                req_id=error_response.req_id,
                status_code=error_response.status_code,
                data=error_response.data,
            )
        except SQLAlchemyError as ex:
            logger.error(
                f"Database error in {func.__name__}: {ex}",
                extra={"pkg_id": request.pkg_id, "req_id": request.req_id},
                exc_info=True,
            )
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                status_code=RSPCode.ERROR,
                data=ErrorEnvelope(
                    code=ErrorCode.DATABASE_ERROR,
                    msg="Database error occurred",
                ).model_dump(),
            )

    return wrapper


def handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Auto-detecting decorator that applies appropriate error handling.

    Automatically detects whether the function is an HTTP or WebSocket handler
    based on its signature and applies the appropriate error handler.

    Detection logic:
    - If first parameter is named 'request' with type RequestModel → WebSocket
    - Otherwise → HTTP

    Args:
        func: The handler function to wrap.

    Returns:
        Wrapped function with appropriate error handling.

    Example:
        ```python
        # HTTP Endpoint
        @router.post("/authors")
        @handle_errors
        async def create_author(...) -> Author:
            ...

        # WebSocket Handler
        @pkg_router.register(PkgID.CREATE_AUTHOR)
        @handle_errors
        async def create_author_handler(request: RequestModel) -> ResponseModel[Any]:
            ...
        ```
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Check if first parameter is RequestModel (WebSocket handler)
    if (
        params
        and params[0].name == "request"
        and params[0].annotation == RequestModel
    ):
        return handle_ws_errors(func)

    # Otherwise treat as HTTP handler
    return handle_http_errors(func)
