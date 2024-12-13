from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError

from {{cookiecutter.module_name}}.api.ws.handlers import load_handlers
from {{cookiecutter.module_name}}.api.ws import (
    handlers,  # FIXME: Need this import for handler registration, try to find better way
)
from {{cookiecutter.module_name}}.api.ws.websocket import PackageAuthWebSocketEndpoint
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.schemas.request import RequestModel

load_handlers()

router = APIRouter()


@router.websocket_route("/web")
class Web(PackageAuthWebSocketEndpoint):
    """
    Defines the `Web` class, which is a WebSocket endpoint for handling package-related requests.

    The `Web` class inherits from `PackageAuthWebSocketEndpoint` and implements the following methods:

    - `on_connect`: Called when a WebSocket connection is established. Calls the parent class's `on_connect` method.
    - `on_receive`: Called when data is received on the WebSocket connection. Logs the received data, creates a `RequestModel` instance from the data, handles the request using the `pkg_router`, and sends the response back to the client.
    - `on_disconnect`: Called when the WebSocket connection is closed. Calls the parent class's `on_disconnect` method.
    """

    # TODO: There is no need of this method
    async def on_connect(self, websocket):
        await super().on_connect(websocket)

    async def on_receive(self, websocket, data: dict[str, Any]):
        try:
            logger.debug(f"Receive data: {data}")
            request = RequestModel(**data)
            response = await pkg_router.handle_request(
                self.scope["user"].obj, request
            )

            await websocket.send_response(response)
            logger.debug(f"Successfully sent response for PkgID {request.pkg_id}")
        except ValidationError:
            logger.debug(
                f"Received invalid data: {data} from user {self.user.username}"
            )
            await websocket.close()

    async def on_disconnect(self, websocket, close_code):
        await super().on_disconnect(websocket, close_code)
