from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError

from {{cookiecutter.module_name}}.api.ws.handlers import load_handlers
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

    - `on_receive`: Called when data is received on the WebSocket connection. Logs the received data, creates a `RequestModel` instance from the data, handles the request using the `pkg_router`, and sends the response back to the client.
    """

    async def on_receive(self, websocket, data: dict[str, Any]):
        """
        Handles incoming WebSocket messages by processing the request and sending back a response.

        This method performs the following steps:
        1. Validates and converts the received data into a RequestModel
        2. Routes the request through pkg_router with user authentication
        3. Sends the response back through the WebSocket
        4. Closes the connection if validation fails

        Args:
            websocket: The WebSocket connection instance
            data (dict[str, Any]): The received message data as a dictionary

        Raises:
            ValidationError: If the received data cannot be parsed into a valid RequestModel.
                            This will result in the WebSocket connection being closed.

        Note:
            On validation failure, the connection is closed and the error is logged
            with the username for debugging purposes.
        """
        try:
            request = RequestModel(**data)
            logger.debug(f"Received data: {data}")

            response = await pkg_router.handle_request(
                self.scope["user"], request
            )

            await websocket.send_response(response)
            logger.debug(f"Successfully sent response for {request.pkg_id}")
        except ValidationError:
            logger.debug(
                f"Received invalid data: {data} from user {self.user.username}"
            )
            await websocket.close()
