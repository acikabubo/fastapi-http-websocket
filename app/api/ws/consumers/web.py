import time
from typing import Any
from urllib.parse import parse_qsl

from fastapi import APIRouter
from google.protobuf.message import DecodeError
from pydantic import ValidationError
from starlette import status

from app.api.ws.formats import select_message_format_strategy
from app.api.ws.handlers import load_handlers
from app.api.ws.websocket import PackageAuthWebSocketEndpoint
from app.logging import logger
from app.routing import pkg_router
from app.settings import app_settings
from app.types import RequestId, UserId, Username
from app.utils.audit_logger import log_user_action
from app.utils.metrics import MetricsCollector
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize WebSocket endpoint with message format strategy.

        Parses the 'format' query parameter to select appropriate strategy:
        - ?format=json (default)
        - ?format=protobuf
        """
        super().__init__(*args, **kwargs)

        # Parse query parameters for format negotiation
        query_params = dict(
            parse_qsl(self.scope.get("query_string", b"").decode())
        )
        format_name = query_params.get("format", "json").lower()

        # Select and initialize strategy
        self.format_strategy = select_message_format_strategy(format_name)

        logger.debug(
            f"WebSocket initialized with {self.format_strategy.format_name} format"
        )

    async def on_receive(  # type: ignore[no-untyped-def]
        self, websocket, data: dict[str, Any] | bytes
    ) -> None:
        """
        Handles incoming WebSocket messages by processing the request and sending back a response.

        Uses message format strategy (selected during connection initialization) for serialization.

        This method performs the following steps:
        1. Checks message rate limit for the user (with fail-open on Redis errors)
        2. Deserializes data using the connection's format strategy
        3. Routes the request through pkg_router with user authentication
        4. Serializes and sends the response using the same format strategy
        5. Logs audit trail for all operations (including errors)
        6. Closes the connection on validation or critical errors

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
                MetricsCollector.record_rate_limit_hit("websocket")
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
            # Deserialize using strategy
            request = await self.format_strategy.deserialize(data)
            logger.debug(
                f"Received {self.format_strategy.format_name} request: "
                f"pkg_id={request.pkg_id}"
            )

            # Track message processing duration
            start_time = time.time()
            response = await pkg_router.handle_request(
                self.scope["user"], request
            )
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)

            # Record processing duration
            MetricsCollector.record_ws_message_processing(
                request.pkg_id, duration
            )

            # Serialize and send response using strategy
            try:
                response_data = await self.format_strategy.serialize(response)

                # Send appropriate message type
                if isinstance(response_data, bytes):
                    await websocket.send_bytes(response_data)
                else:
                    # Use send_response() for JSON to handle UUID encoding
                    await websocket.send_response(response)

                MetricsCollector.record_ws_message_sent()
                logger.debug(
                    f"Successfully sent {self.format_strategy.format_name} response "
                    f"for {request.pkg_id}"
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
            MetricsCollector.record_app_error(
                error_type=type(e).__name__, handler="websocket"
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
