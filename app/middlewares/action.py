from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging import logger
from app.schemas.user import UserModel


class PermAuthHTTPMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, actions: dict[str, Any]):
        super().__init__(app)
        self.actions = actions["http"]

    async def dispatch(self, request: Request, call_next):
        # Check if user is authenticated
        if (
            not hasattr(request, "user")
            or not request.user
            or not request.user.obj
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
            )

        user: UserModel = request.user.obj

        # Get required role using request path and method
        required_role = self.actions.get(request.url.path, {}).get(
            request.method
        )

        # If a role is specified for this endpoint and method
        if required_role and required_role not in user.roles:
            logger.debug(
                f"The user {user.username} made a request to "
                f"{request.method} {request.url.path} but has "
                "insufficient permissions. "
                f"The {required_role} role is required."
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "User has insufficient permissions"},
            )

        # If all checks pass, continue with the request
        return await call_next(request)
