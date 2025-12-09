"""
Error handler decorators for unified exception handling across protocols.

This module provides decorators that automatically convert AppException instances
into appropriate HTTP or WebSocket responses, eliminating duplicate try/except
blocks in handlers.
"""

import inspect
from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.ws.constants import RSPCode
from app.exceptions import AppException
from app.logging import logger
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel


def handle_http_errors(func: Callable) -> Callable:
    """
    Decorator for HTTP endpoints to convert AppException to HTTPException.

    Automatically catches AppException instances and converts them to
    FastAPI HTTPException with appropriate status codes.

    Args:
        func: The HTTP endpoint function to wrap.

    Returns:
        Wrapped function that handles exceptions.

    Example:
        ```python
        @router.post("/authors")
        @handle_http_errors
        async def create_author(data: CreateAuthorInput, repo: AuthorRepoDep) -> Author:
            command = CreateAuthorCommand(repo)
            return await command.execute(data)  # No try/except needed!
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
            raise HTTPException(
                status_code=ex.http_status,
                detail=ex.message,
            )
        except SQLAlchemyError as ex:
            logger.error(
                f"Database error in {func.__name__}: {ex}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Database error occurred",
            )

    return wrapper


def handle_ws_errors(func: Callable) -> Callable:
    """
    Decorator for WebSocket handlers to convert AppException to ResponseModel.

    Automatically catches AppException instances and converts them to
    WebSocket error responses with appropriate RSPCode values.

    Args:
        func: The WebSocket handler function to wrap.

    Returns:
        Wrapped function that handles exceptions.

    Example:
        ```python
        @pkg_router.register(PkgID.CREATE_AUTHOR, roles=["create-author"])
        @handle_ws_errors
        async def create_author_handler(request: RequestModel) -> ResponseModel:
            async with async_session() as session:
                repo = AuthorRepository(session)
                command = CreateAuthorCommand(repo)
                author = await command.execute(CreateAuthorInput(**request.data))
                return ResponseModel.success(request.pkg_id, request.req_id, data=author.model_dump())
        ```
    """

    @wraps(func)
    async def wrapper(request: RequestModel, *args: Any, **kwargs: Any) -> ResponseModel:
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
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg=ex.message,
                status_code=ex.ws_status,
            )
        except SQLAlchemyError as ex:
            logger.error(
                f"Database error in {func.__name__}: {ex}",
                extra={"pkg_id": request.pkg_id, "req_id": request.req_id},
                exc_info=True,
            )
            return ResponseModel.err_msg(
                request.pkg_id,
                request.req_id,
                msg="Database error occurred",
                status_code=RSPCode.ERROR,
            )

    return wrapper


def handle_errors(func: Callable) -> Callable:
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
        async def create_author_handler(request: RequestModel) -> ResponseModel:
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
