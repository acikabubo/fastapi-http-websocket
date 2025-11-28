import time
from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError
from starlette import status

from app.api.ws.handlers import load_handlers
from app.api.ws.websocket import PackageAuthWebSocketEndpoint
from app.logging import logger
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.settings import app_settings
from app.utils.metrics import (
    ws_message_processing_duration_seconds,
    ws_messages_received_total,
    ws_messages_sent_total,
)
from app.utils.rate_limiter import rate_limiter

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
        1. Checks message rate limit for the user
        2. Validates and converts the received data into a RequestModel
        3. Routes the request through pkg_router with user authentication
        4. Sends the response back through the WebSocket
        5. Closes the connection if validation or rate limiting fails

        Args:
            websocket: The WebSocket connection instance
            data (dict[str, Any]): The received message data as a dictionary

        Raises:
            ValidationError: If the received data cannot be parsed into a valid RequestModel.
                            This will result in the WebSocket connection being closed.

        Note:
            On validation or rate limit failure, the connection is closed and the error is logged
            with the username for debugging purposes.
        """
        # Check message rate limit
        rate_limit_key = f"ws_msg:user:{self.user.username}"
        is_allowed, remaining = await rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=app_settings.WS_MESSAGE_RATE_LIMIT,
            window_seconds=60,
        )

        if not is_allowed:
            logger.warning(
                f"WebSocket message rate limit exceeded for user {self.user.username}"
            )
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Message rate limit exceeded",
            )
            return

        # Track received message
        ws_messages_received_total.inc()

        try:
            request = RequestModel(**data)
            logger.debug(f"Received data: {data}")

            # Track message processing duration
            start_time = time.time()
            response = await pkg_router.handle_request(
                self.scope["user"], request
            )
            duration = time.time() - start_time

            # Record processing duration
            ws_message_processing_duration_seconds.labels(
                pkg_id=str(request.pkg_id)
            ).observe(duration)

            await websocket.send_response(response)
            ws_messages_sent_total.inc()
            logger.debug(f"Successfully sent response for {request.pkg_id}")
        except ValidationError:
            logger.debug(
                f"Received invalid data: {data} from user {self.user.username}"
            )
            await websocket.close()
