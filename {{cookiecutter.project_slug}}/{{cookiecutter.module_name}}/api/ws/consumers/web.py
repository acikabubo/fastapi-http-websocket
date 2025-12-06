import time
from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError
from starlette import status

from {{cookiecutter.module_name}}.api.ws.handlers import load_handlers
from {{cookiecutter.module_name}}.api.ws.websocket import PackageAuthWebSocketEndpoint
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.settings import app_settings
{% if cookiecutter.enable_audit_logging == "yes" %}from {{cookiecutter.module_name}}.utils.audit_logger import log_user_action
{% endif %}from {{cookiecutter.module_name}}.utils.metrics import (
    ws_message_processing_duration_seconds,
    ws_messages_received_total,
    ws_messages_sent_total,
)
from {{cookiecutter.module_name}}.utils.rate_limiter import rate_limiter

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
{% if cookiecutter.enable_audit_logging == "yes" %}            duration_ms = int(duration * 1000)
{% endif %}
            # Record processing duration
            ws_message_processing_duration_seconds.labels(
                pkg_id=str(request.pkg_id)
            ).observe(duration)

            await websocket.send_response(response)
            ws_messages_sent_total.inc()
            logger.debug(f"Successfully sent response for {request.pkg_id}")
{% if cookiecutter.enable_audit_logging == "yes" %}
            # Log successful WebSocket action
            await log_user_action(
                user_id=self.user.id,
                username=self.user.username,
                user_roles=self.user.roles,
                action_type=f"WS:{request.pkg_id.name}",
                resource=f"WebSocket:{request.pkg_id.name}",
                outcome="success" if response.status_code == 0 else "error",
                ip_address=websocket.client.host if websocket.client else None,
                request_id=request.req_id,
                request_data=request.data,
                response_status=response.status_code,
                duration_ms=duration_ms,
            )
{% endif %}
        except ValidationError as e:
            logger.debug(
                f"Received invalid data: {data} from user {self.user.username}"
            )
{% if cookiecutter.enable_audit_logging == "yes" %}
            # Log validation error
            await log_user_action(
                user_id=self.user.id,
                username=self.user.username,
                user_roles=self.user.roles,
                action_type="WS:INVALID_REQUEST",
                resource="WebSocket",
                outcome="error",
                ip_address=websocket.client.host if websocket.client else None,
                error_message=f"Validation error: {str(e)}",
            )
{% endif %}
            await websocket.close()
