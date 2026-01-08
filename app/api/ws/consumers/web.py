import time
from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError
from starlette import status

from app.api.ws.handlers import load_handlers
from app.api.ws.websocket import PackageAuthWebSocketEndpoint
from app.logging import logger
from app.routing import pkg_router
from app.schemas.proto import Request as ProtoRequest
from app.schemas.request import RequestModel
from app.settings import app_settings
from app.types import RequestId, UserId, Username
from app.utils.audit_logger import log_user_action
from app.utils.metrics import (
    ws_message_processing_duration_seconds,
    ws_messages_received_total,
    ws_messages_sent_total,
)
from app.utils.protobuf_converter import (
    proto_to_pydantic_request,
    serialize_response,
)
from app.utils.rate_limiter import rate_limiter

load_handlers()  # type: ignore[no-untyped-call]

router = APIRouter()


@router.websocket_route("/web")
class Web(PackageAuthWebSocketEndpoint):
    """
    Defines the `Web` class, which is a WebSocket endpoint for handling package-related requests.

    The `Web` class inherits from `PackageAuthWebSocketEndpoint` and implements the following methods:

    - `on_receive`: Called when data is received on the WebSocket connection. Logs the received data, creates a `RequestModel` instance from the data, handles the request using the `pkg_router`, and sends the response back to the client.
    """

    async def on_receive(  # type: ignore[no-untyped-def]
        self, websocket, data: dict[str, Any] | bytes
    ) -> None:
        """
        Handles incoming WebSocket messages by processing the request and sending back a response.

        Supports both JSON and Protocol Buffers formats based on connection negotiation.

        This method performs the following steps:
        1. Checks message rate limit for the user
        2. Detects message format (JSON dict or Protobuf bytes)
        3. Validates and converts the received data into a RequestModel
        4. Routes the request through pkg_router with user authentication
        5. Sends the response back in the same format
        6. Closes the connection if validation or rate limiting fails

        Args:
            websocket: The WebSocket connection instance
            data: The received message data (dict for JSON, bytes for Protobuf)

        Raises:
            ValidationError: If the received data cannot be parsed into a valid RequestModel.
                            This will result in the WebSocket connection being closed.

        Note:
            On validation or rate limit failure, the connection is closed and the error is logged
            with the username for debugging purposes.
        """
        # Check message rate limit
        rate_limit_key = f"ws_msg:user:{self.user.username}"
        is_allowed, _ = await rate_limiter.check_rate_limit(
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
            # Parse request based on message format
            if isinstance(data, bytes):
                # Protobuf format
                proto_request = ProtoRequest()
                proto_request.ParseFromString(data)
                request = proto_to_pydantic_request(proto_request)
                logger.debug(
                    f"Received protobuf request: pkg_id={request.pkg_id}"
                )
                message_format = "protobuf"
            else:
                # JSON format
                request = RequestModel(**data)
                logger.debug(f"Received JSON request: {data}")
                message_format = "json"

            # Track message processing duration
            start_time = time.time()
            response = await pkg_router.handle_request(
                self.scope["user"], request
            )
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)

            # Record processing duration
            ws_message_processing_duration_seconds.labels(
                pkg_id=str(request.pkg_id)
            ).observe(duration)

            # Send response in the same format as request
            if message_format == "protobuf":
                response_data = serialize_response(response, "protobuf")
                await websocket.send_bytes(response_data)
            else:
                await websocket.send_response(response)

            ws_messages_sent_total.inc()
            logger.debug(
                f"Successfully sent {message_format} response for {request.pkg_id}"
            )

            # Log successful WebSocket action
            await log_user_action(
                user_id=UserId(self.user.id),
                username=Username(self.user.username),
                user_roles=self.user.roles,
                action_type=f"WS:{request.pkg_id.name}",
                resource=f"WebSocket:{request.pkg_id.name}",
                outcome="success" if response.status_code == 0 else "error",
                ip_address=websocket.client.host if websocket.client else None,
                request_id=(
                    RequestId(self.correlation_id)
                    if self.correlation_id
                    else None
                ),
                request_data=request.data,
                response_status=response.status_code,
                duration_ms=duration_ms,
            )

        except ValidationError as e:
            data_str = data.decode() if isinstance(data, bytes) else str(data)
            logger.debug(
                f"Received invalid data: {data_str} from user {self.user.username}"
            )

            # Log validation error
            await log_user_action(
                user_id=UserId(self.user.id),
                username=Username(self.user.username),
                user_roles=self.user.roles,
                action_type="WS:INVALID_REQUEST",
                resource="WebSocket",
                outcome="error",
                ip_address=websocket.client.host if websocket.client else None,
                request_id=(
                    RequestId(self.correlation_id)
                    if self.correlation_id
                    else None
                ),
                error_message=f"Validation error: {str(e)}",
            )

            await websocket.close()
