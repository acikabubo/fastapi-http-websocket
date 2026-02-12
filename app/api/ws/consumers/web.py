import time
from typing import Any

from fastapi import APIRouter
from google.protobuf.message import DecodeError
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
from app.utils.metrics import MetricsCollector
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
        1. Checks message rate limit for the user (with fail-open on Redis errors)
        2. Detects message format (JSON dict or Protobuf bytes)
        3. Validates and converts the received data into a RequestModel
        4. Routes the request through pkg_router with user authentication
        5. Sends the response back in the same format (handles connection failures gracefully)
        6. Logs audit trail for all operations (including errors)
        7. Closes the connection on validation or critical errors

        Args:
            websocket: The WebSocket connection instance
            data: The received message data (dict for JSON, bytes for Protobuf)

        Note:
            All exceptions are caught and handled gracefully to prevent server crashes.
            Rate limiter failures default to allowing the message (fail-open).
            Connection errors during send are logged but don't crash the server.
        """
        # Track received message
        MetricsCollector.record_ws_message_received()

        # Check message rate limit (fail-open on errors)
        try:
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
        except Exception as e:  # noqa: BLE001
            # Fail-open: allow message through if rate limiter fails
            # Catches all exceptions from rate limiter to ensure availability
            logger.warning(
                f"Rate limiter error for user {self.user.username}, failing open: {e}"
            )

        try:
            # Parse request based on message format
            if isinstance(data, bytes):
                # Protobuf format
                proto_request = ProtoRequest()
                proto_request.ParseFromString(data)  # May raise DecodeError
                request = proto_to_pydantic_request(
                    proto_request
                )  # May raise ValueError
                logger.debug(
                    f"Received protobuf request: pkg_id={request.pkg_id}"
                )
                message_format = "protobuf"
            else:
                # JSON format
                request = RequestModel(**data)  # May raise ValidationError
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
            MetricsCollector.record_ws_message_processing(request.pkg_id, duration)

            # Send response in the same format as request
            try:
                if message_format == "protobuf":
                    response_data = serialize_response(response, "protobuf")
                    await websocket.send_bytes(response_data)
                else:
                    await websocket.send_response(response)

                MetricsCollector.record_ws_message_sent()
                logger.debug(
                    f"Successfully sent {message_format} response for {request.pkg_id}"
                )
            except (RuntimeError, ConnectionError) as e:
                # Connection closed during send - log but don't crash
                logger.warning(
                    f"Failed to send response to {self.user.username}: {e}"
                )
                return  # Connection is closed, nothing more to do

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

        except (ValidationError, DecodeError, ValueError) as e:
            # Invalid message format or data
            error_type = type(e).__name__
            logger.warning(
                f"{error_type} from user {self.user.username}: {str(e)[:100]}"
            )

            # Log validation/parsing error
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
                error_message=f"{error_type}: {str(e)}",
            )

            await websocket.close()

        except Exception as e:  # noqa: BLE001
            # Unexpected error (handler exceptions, etc.)
            # Catches all other exceptions to prevent server crashes
            logger.error(
                f"Unexpected error processing message from {self.user.username}: {e}",
                exc_info=True,
            )

            # Log unexpected error
            await log_user_action(
                user_id=UserId(self.user.id),
                username=Username(self.user.username),
                user_roles=self.user.roles,
                action_type="WS:ERROR",
                resource="WebSocket",
                outcome="error",
                ip_address=websocket.client.host if websocket.client else None,
                request_id=(
                    RequestId(self.correlation_id)
                    if self.correlation_id
                    else None
                ),
                error_message=f"Unexpected error: {str(e)}",
            )

            await websocket.close()
