import json
import uuid
from typing import Type
from uuid import UUID

from starlette import status
from starlette.authentication import UnauthenticatedUser
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from {{cookiecutter.module_name}}.connection_registry import ws_clients
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.managers.websocket_connection_manager import connection_manager
from {{cookiecutter.module_name}}.schemas.response import BroadcastDataModel, ResponseModel
from {{cookiecutter.module_name}}.schemas.user import UserModel
from {{cookiecutter.module_name}}.settings import app_settings
from {{cookiecutter.module_name}}.storage.redis import get_auth_redis_connection
from {{cookiecutter.module_name}}.utils.metrics import ws_connections_active, ws_connections_total
from {{cookiecutter.module_name}}.utils.rate_limiter import connection_limiter, rate_limiter


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""

    def default(self, obj):
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


class PackagedWebSocket(WebSocket):
    """Extended WebSocket class for sending packaged responses."""

    async def send_response(
        self, data: BroadcastDataModel | ResponseModel
    ) -> None:
        """
        Sends a response over the WebSocket connection.

        Parameters:
        - `data`: An instance of either `BroadcastDataModel` or `ResponseModel` containing the data to be sent.

        This method first serializes the data using the `UUIDEncoder` to handle `UUID` objects, then sends the serialized data over the WebSocket connection with a message type of "websocket.send".
        """
        # await self.send_json(data.model_dump())
        text = json.dumps(data.model_dump(), cls=UUIDEncoder)
        await self.send({"type": "websocket.send", "text": text})


class PackageAuthWebSocketEndpoint(WebSocketEndpoint):
    """
    WebSocket endpoint with authentication and package routing.

    Handles WebSocket connections with Keycloak authentication and manages
    the connection lifecycle including authorization and session management.
    """

    encoding = "json"
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
        await self.on_connect(websocket)

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
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc
        finally:
            await self.on_disconnect(websocket, close_code)

    async def on_connect(self, websocket):
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
        await self.r.add_kc_user_session(self.user)

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

    async def on_disconnect(self, websocket, close_code):
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
        if (
            not isinstance(self.user, UnauthenticatedUser)
            and hasattr(self, "connection_id")
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
