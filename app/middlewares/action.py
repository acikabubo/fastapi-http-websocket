from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class PermAuthHTTPMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, actions):
        super().__init__(app)
        self.actions = actions

    async def dispatch(self, request: Request, call_next):
        print()
        print("HTTP Middleware")
        print(self.actions)
        print()
        return await call_next(request)
