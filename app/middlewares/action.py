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
        """
        This middleware function is responsible for handling permission-based authentication and authorization for incoming HTTP requests.
        It checks if the request is for an excluded path, and if so, allows the request to continue.
        Otherwise, it checks if the user is authenticated, and if not, returns a 401 Unauthorized response.
        If the user is authenticated, it checks if the user has the necessary permissions to access the requested resource using the RBAC manager.
        If the user does not have permission, it returns a 403 Forbidden response.
        If all checks pass, the middleware allows the request to continue.
        """
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
