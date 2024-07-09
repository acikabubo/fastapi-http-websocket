from typing import Dict

from fastapi import Request


class ActionMiddleware:
    def __init__(self, app, action_map: Dict[int, str]):
        # Store the FastAPI application instance
        self.app = app
        # Store the provided action map dictionary
        self.action_map = action_map

    async def __call__(self, request: Request, call_next):
        """
        Middleware that checks the request path parameters for a "pkg_id" value and sets the "action" attribute on the request state if the "pkg_id" is found in the provided action map.
        """

        # Get the "pkg_id" value from the request path parameters
        pkg_id = request.path_params.get("pkg_id")

        # If the "pkg_id" exists and is present in the action map
        if pkg_id and pkg_id in self.action_map:
            # Set the "action" attribute on the request state
            # with the corresponding value from the action map
            request.state.action = self.action_map[pkg_id]

        # Call the next middleware or route handler
        response = await call_next(request)

        # Return the response
        return response
