import json
import uuid
from typing import Any, Type
from uuid import UUID

from pydantic import ValidationError
from starlette import status
from starlette.authentication import UnauthenticatedUser
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.connection_registry import ws_clients
from app.logging import logger
from app.managers.websocket_connection_manager import connection_manager
from app.schemas.response import BroadcastDataModel, ResponseModel
from app.schemas.user import UserModel
from app.settings import app_settings
from app.storage.redis import get_auth_redis_connection
from app.utils.metrics import ws_connections_active, ws_connections_total
from app.utils.rate_limiter import connection_limiter


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""

    def default(self, obj: Any) -> Any:
        """
        Convert UUID objects to strings for JSON serialization.

        Args:
            obj: The object to serialize.

        Returns:
            str: String representation of UUID, or delegates to parent.
        """
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class PackagedWebSocket(WebSocket):  # type: ignore[misc]
    """Extended WebSocket class for sending packaged responses."""

    async def send_response(
        self, data: BroadcastDataModel[Any] | ResponseModel[Any]
    ) -> None:
        """
        Sends a response over the WebSocket connection.

        Parameters:
        - `data`: An instance of either `BroadcastDataModel[Any]` or `ResponseModel` containing the data to be sent.

        This method first serializes the data using the `UUIDEncoder` to handle `UUID` objects, then sends the serialized data over the WebSocket connection with a message type of "websocket.send".
        """
        # await self.send_json(data.model_dump())
        text = json.dumps(data.model_dump(), cls=UUIDEncoder)
        await self.send({"type": "websocket.send", "text": text})


class PackageAuthWebSocketEndpoint(WebSocketEndpoint):  # type: ignore[misc]
    """
    WebSocket endpoint with authentication and package routing.

    Handles WebSocket connections with Keycloak authentication and manages
    the connection lifecycle including authorization and session management.
    Supports both JSON and Protocol Buffers message formats.
    """

    encoding = None  # Handle both JSON and binary (protobuf) formats
    websocket_class: Type[WebSocket] = PackagedWebSocket

    async def dispatch(self) -> None:
        """
        This function is responsible for managing the WebSocket connection lifecycle.

        Parameters:
        - self: The instance of the class that this method belongs to.

        Returns:
        - None: This function does not return any value.

        The function performs the following steps:
        1. Creates a WebSocket instance using the provided scope, receive, and send parameters.
        2. Calls the on_connect method with the WebSocket instance.
        3. Initializes the close_code variable with the value of WS_1000_NORMAL_CLOSURE.
        4. Enters a try-except-finally block to handle the WebSocket communication.
        5. Inside the try block, it continuously receives messages from the WebSocket.
        - If the message type is "websocket.receive", it decodes the message and calls the on_receive method.
        - If the message type is "websocket.disconnect", it sets the close_code and breaks the loop.
        6. In the except block, it sets the close_code to WS_1011_INTERNAL_ERROR and re-raises the exception.
        7. In the finally block, it calls the on_disconnect method with the WebSocket and close_code.
        """

        websocket = self.websocket_class(
            self.scope, receive=self.receive, send=self.send
        )
        await self.on_connect(websocket)  # type: ignore[no-untyped-call]

        close_code = status.WS_1000_NORMAL_CLOSURE

        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.receive":
                    data = await self.decode(websocket, message)
                    await self.on_receive(websocket, data)
                elif message["type"] == "websocket.disconnect":
                    close_code = int(
                        message.get("code") or status.WS_1000_NORMAL_CLOSURE
                    )
                    break
        except (
            ValidationError,
            ValueError,
            KeyError,
            WebSocketDisconnect,
        ) as exc:
            # ValidationError: Pydantic validation failed
            # ValueError: Invalid message format
            # KeyError: Missing required message fields
            # WebSocketDisconnect: Client disconnected
            close_code = status.WS_1003_UNSUPPORTED_DATA
            raise exc
        except Exception as exc:
            # Catch-all for unexpected errors
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc
        finally:
            await self.on_disconnect(websocket, close_code)  # type: ignore[no-untyped-call]

    async def decode(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> dict[str, Any] | bytes:
        """
        Decode incoming WebSocket message.

        Supports both JSON (text) and Protobuf (binary) formats.
        Returns the raw data without decoding to allow format-specific
        handling in on_receive().

        Args:
            websocket: WebSocket connection instance
            message: Raw message dict from WebSocket

        Returns:
            Decoded message data (dict for JSON, bytes for protobuf)
        """
        if "text" in message:
            # JSON format - parse as JSON
            text = message["text"]
            return json.loads(text)
        elif "bytes" in message:
            # Protobuf format - return raw bytes
            return message["bytes"]
        else:
            # Fallback for other message types
            return message.get("text", message.get("bytes", b""))

    async def on_connect(self, websocket):  # type: ignore[no-untyped-def]
        """
        Handles WebSocket client connection with authentication and rate limiting.

        This method performs the following tasks:
        1. Calls the parent class on_connect method
        2. Retrieves authenticated Redis connection
        3. Validates user authentication
        4. Enforces per-user connection limits
        5. Registers the connection in connection manager
        6. Sets up user session in Redis

        Connection is rejected if:
        - User is not authenticated
        - User has exceeded maximum concurrent connections
        """

        await super().on_connect(websocket)

        # Attach auth redis instance on websocket connection instance
        self.r = await get_auth_redis_connection()

        self.user: UserModel = self.scope["user"]

        # Detect message format from query parameters (default: json)
        query_params = dict(websocket.query_params)
        self.message_format = query_params.get("format", "json").lower()

        # Validate format
        if self.message_format not in ("json", "protobuf"):
            logger.warning(
                f"Invalid format '{self.message_format}' specified, defaulting to json"
            )
            self.message_format = "json"

        logger.debug(
            f"WebSocket connection using format: {self.message_format}"
        )

        # Reject unauthenticated connections
        if isinstance(self.user, UnauthenticatedUser) or self.user is None:
            logger.debug(
                "Client is not logged in, websocket connection will be closed!"
            )
            ws_connections_total.labels(status="rejected_auth").inc()
            await websocket.close()
            return

        # Generate unique connection ID
        self.connection_id = str(uuid.uuid4())

        # Extract correlation ID from WebSocket upgrade request headers
        # If X-Correlation-ID header was present in the upgrade request,
        # use it to maintain correlation with preceding HTTP requests
        headers = dict(websocket.headers)
        correlation_id_from_header = headers.get("x-correlation-id", "")

        # Use header correlation ID if present, otherwise use first 8 chars of connection ID
        self.correlation_id = (
            correlation_id_from_header[:8]
            if correlation_id_from_header
            else self.connection_id[:8]
        )

        # Check connection limit
        connection_allowed = await connection_limiter.add_connection(
            user_id=self.user.username, connection_id=self.connection_id
        )

        if not connection_allowed:
            logger.warning(
                f"Connection limit exceeded for user {self.user.username}"
            )
            ws_connections_total.labels(status="rejected_limit").inc()
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Maximum concurrent connections exceeded",
            )
            return

        # Set user username in redis with TTL from expired seconds from keycloak
        await self.r.add_kc_user_session(self.user)  # type: ignore[union-attr]

        # Map username with websocket instance
        ws_clients[
            app_settings.USER_SESSION_REDIS_KEY_PREFIX + self.user.username
        ] = websocket

        connection_manager.connect(websocket)
        ws_connections_total.labels(status="accepted").inc()
        ws_connections_active.inc()
        logger.debug(
            f"Client connected to websocket (connection_id: {self.connection_id})"
        )

    async def on_disconnect(self, websocket, close_code):  # type: ignore[no-untyped-def]
        """
        Handles WebSocket client disconnection and cleanup.

        This method performs the following tasks:
        1. Calls the parent class on_disconnect method
        2. Removes connection from connection manager
        3. Removes connection from connection limiter
        4. Logs disconnection event with username and close code
        """

        await super().on_disconnect(websocket, close_code)
        connection_manager.disconnect(websocket)

        # Remove from connection limiter if connection was established
        if not isinstance(self.user, UnauthenticatedUser) and hasattr(
            self, "connection_id"
        ):
            await connection_limiter.remove_connection(
                user_id=self.user.username, connection_id=self.connection_id
            )
            # Decrement active connections metric
            ws_connections_active.dec()

        log_msg = (
            f"Client of user {self.user.username} disconnected with code {close_code}"
            if not isinstance(self.user, UnauthenticatedUser)
            else f"Unauthenticated user disconnected with code {close_code}"
        )

        logger.debug(log_msg)
