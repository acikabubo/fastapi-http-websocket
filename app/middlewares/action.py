import re

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.authentication import UnauthenticatedUser
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.managers.rbac_manager import RBACManager
from app.settings import EXCLUDED_PATHS


class PermAuthHTTPMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, rbac: RBACManager):
        super().__init__(app)
        self.rbac: RBACManager = rbac
        self.excluded_paths = EXCLUDED_PATHS

    async def dispatch(self, request: Request, call_next):
        if self.excluded_paths.match(request.url.path):
            return await call_next(request)

        # Check if user is authenticated
        if isinstance(request.user, UnauthenticatedUser) or not request.user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
            )

        has_permission = self.rbac.check_http_permission(request)

        if has_permission is False:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "User has insufficient permissions"},
            )

        # If all checks pass, continue with the request
        return await call_next(request)
