import asyncio
import json
import uuid
from typing import Any, Type
from uuid import UUID

from fastapi.security.utils import get_authorization_scheme_param
from jwcrypto.jwt import JWTExpired
from keycloak.exceptions import KeycloakAuthenticationError
from pydantic import ValidationError
from starlette import status
from starlette.authentication import UnauthenticatedUser
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.logging import logger, set_log_context
from app.managers.websocket_connection_manager import connection_manager
from app.schemas.response import BroadcastDataModel, ResponseModel
from fastapi_keycloak_rbac.manager import keycloak_manager
from fastapi_keycloak_rbac.models import UserModel
from app.settings import app_settings
from app.storage.redis import get_auth_redis_connection
from app.utils.metrics import MetricsCollector
from app.utils.rate_limiter import connection_limiter


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""

    def default(self, o: Any) -> Any:
        """
        Convert UUID objects to strings for JSON serialization.

        Args:
            o: The object to serialize.

        Returns:
            str: String representation of UUID, or delegates to parent.
        """
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)


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
    WebSocket endpoint with first-message authentication and package routing.

    Auth flow (RFC 9700 §4.3.2 compliant):
    1. HTTP upgrade accepted without token (no query-param exposure)
    2. Client sends {"type": "auth", "token": "Bearer <jwt>"} as first frame
    3. Server validates token within 5s timeout
    4. On success: server sends {"type": "auth_ok"}, normal message loop begins
    5. On failure/timeout: server closes with 4001 (Unauthorized) or 4002 (timeout)

    Supports both JSON and Protocol Buffers message formats.
    """

    encoding = None  # Handle both JSON and binary (protobuf) formats
    websocket_class: Type[WebSocket] = PackagedWebSocket
    user: UserModel | UnauthenticatedUser

    # Close codes for auth failures
    WS_4001_UNAUTHORIZED = 4001
    WS_4002_AUTH_TIMEOUT = 4002

    # Auth handshake timeout in seconds
    AUTH_TIMEOUT = 5.0

    def _is_origin_allowed(self, websocket: WebSocket) -> bool:
        """
        Validate WebSocket origin for CSRF protection.

        Prevents Cross-Site WebSocket Hijacking (CSWSH) attacks by validating
        the Origin header against the allowed origins list.

        Args:
            websocket: The WebSocket connection instance.

        Returns:
            True if the origin is allowed, False otherwise.
        """
        allowed_origins = app_settings.ALLOWED_WS_ORIGINS

        # Wildcard permits all origins (use only in development)
        if "*" in allowed_origins:
            return True

        origin = websocket.headers.get("origin")

        # No Origin header means same-origin request from browser (safe)
        if origin is None:
            return True

        # Check if origin exactly matches an allowed origin
        if origin in allowed_origins:
            return True

        # Origin not in allowed list - reject connection
        return False

    async def dispatch(self) -> None:
        """
        Manage the WebSocket connection lifecycle with first-message auth.

        Flow:
        1. Accept HTTP upgrade (on_connect — origin check only, no auth)
        2. Run first-message auth handshake (on_first_message)
        3. If auth fails, return early (connection already closed)
        4. Enter normal message loop
        5. Always call on_disconnect for cleanup
        """
        websocket = self.websocket_class(
            self.scope, receive=self.receive, send=self.send
        )
        await self.on_connect(websocket)  # type: ignore[no-untyped-call]

        # Run first-message auth — returns False if connection was closed
        if not await self.on_first_message(websocket):
            await self.on_disconnect(websocket, self.WS_4001_UNAUTHORIZED)  # type: ignore[no-untyped-call]
            return

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

    async def on_first_message(self, websocket: WebSocket) -> bool:
        """
        Perform first-message authentication handshake.

        Waits up to AUTH_TIMEOUT seconds for the client to send:
            {"type": "auth", "token": "Bearer <jwt>"}

        On success, calls _post_auth_setup() and returns True.
        On failure (bad token, wrong format, timeout, disconnect), closes
        the connection and returns False.

        Args:
            websocket: The accepted WebSocket connection.

        Returns:
            True if authentication succeeded, False otherwise.
        """
        try:
            raw = await asyncio.wait_for(
                websocket.receive(), timeout=self.AUTH_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning("WebSocket auth timeout — no auth frame received")
            MetricsCollector.record_ws_connection_rejected("auth_timeout")
            try:
                await websocket.close(code=self.WS_4002_AUTH_TIMEOUT)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        # Client disconnected during auth window
        if raw.get("type") == "websocket.disconnect":
            logger.debug("Client disconnected during auth window")
            return False

        # Must be a text frame
        text = raw.get("text")
        if not text:
            logger.warning("WebSocket auth frame is not a text frame")
            MetricsCollector.record_ws_connection_rejected("auth")
            try:
                await websocket.close(code=self.WS_4001_UNAUTHORIZED)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        # Parse the auth frame
        try:
            frame = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            logger.warning("WebSocket auth frame is not valid JSON")
            MetricsCollector.record_ws_connection_rejected("auth")
            try:
                await websocket.close(code=self.WS_4001_UNAUTHORIZED)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        if frame.get("type") != "auth":
            logger.warning(
                f"WebSocket first frame type is not 'auth': {frame.get('type')}"
            )
            MetricsCollector.record_ws_connection_rejected("auth")
            try:
                await websocket.close(code=self.WS_4001_UNAUTHORIZED)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        token_header = frame.get("token", "")
        scheme, token = get_authorization_scheme_param(token_header)

        if scheme.lower() != "bearer" or not token:
            logger.warning(
                "WebSocket auth frame missing or invalid Bearer token"
            )
            MetricsCollector.record_ws_connection_rejected("auth")
            try:
                await websocket.close(code=self.WS_4001_UNAUTHORIZED)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        # Validate token with Keycloak
        try:
            user_info = await keycloak_manager.decode_token(token)
            self.user = UserModel(**user_info)
        except (JWTExpired, KeycloakAuthenticationError, ValueError) as exc:
            logger.warning(f"WebSocket token validation failed: {exc}")
            MetricsCollector.record_ws_connection_rejected("auth")
            try:
                await websocket.close(code=self.WS_4001_UNAUTHORIZED)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Unexpected error during WebSocket token validation: {exc}",
                exc_info=True,
            )
            MetricsCollector.record_ws_connection_rejected("auth")
            try:
                await websocket.close(code=self.WS_4001_UNAUTHORIZED)
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        return await self._post_auth_setup(websocket)

    async def _post_auth_setup(self, websocket: WebSocket) -> bool:
        """
        Complete connection setup after successful token validation.

        Assigns connection ID, sets log context, enforces connection limits,
        registers in Redis and the connection manager, and sends auth_ok.

        Args:
            websocket: The authenticated WebSocket connection.

        Returns:
            True if setup succeeded, False if connection limit was exceeded.
        """
        # Generate unique connection ID
        self.connection_id = str(uuid.uuid4())

        # Extract correlation ID from upgrade request headers
        headers = dict(websocket.headers)
        correlation_id_from_header = headers.get("x-correlation-id", "")
        self.correlation_id = (
            correlation_id_from_header[:8]
            if correlation_id_from_header
            else self.connection_id[:8]
        )

        # Set log context for all subsequent WS logs on this connection
        set_log_context(
            endpoint="/web",
            user_id=self.user.username,
            request_id=self.correlation_id,
        )

        # Check connection limit
        connection_allowed = await connection_limiter.add_connection(
            user_id=self.user.username, connection_id=self.connection_id
        )

        if not connection_allowed:
            logger.warning(
                f"Connection limit exceeded for user {self.user.username}"
            )
            MetricsCollector.record_ws_connection_rejected("limit")
            try:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Maximum concurrent connections exceeded",
                )
            except (RuntimeError, WebSocketDisconnect):
                pass
            return False

        # Set user session in Redis with TTL from Keycloak token expiry
        await self.r.add_kc_user_session(self.user)  # type: ignore[union-attr]

        # Store session key for cleanup in on_disconnect
        self.session_key = (
            app_settings.USER_SESSION_REDIS_KEY_PREFIX + self.user.username
        )

        # Register connection in connection manager
        connection_manager.connect(self.session_key, websocket)
        MetricsCollector.record_ws_connection_accepted()

        # Notify client that auth succeeded
        await websocket.send_text(json.dumps({"type": "auth_ok"}))

        logger.debug(
            f"Client authenticated and connected (connection_id: {self.connection_id})"
        )
        return True

    async def decode(
        self, _websocket: WebSocket, message: dict[str, Any]
    ) -> dict[str, Any] | bytes:
        """
        Decode incoming WebSocket message.

        Supports both JSON (text) and Protobuf (binary) formats.
        Returns the raw data without decoding to allow format-specific
        handling in on_receive().

        Args:
            _websocket: WebSocket connection instance (unused — required by parent)
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
        Accept the WebSocket upgrade and perform pre-auth setup.

        Only validates the Origin header (CSRF protection) and attaches
        the Redis connection. Authentication is deferred to the first
        message handshake (on_first_message) to avoid exposing tokens
        in the HTTP upgrade URL (RFC 9700 §4.3.2).

        Connection is rejected if:
        - Origin is not in allowed origins list (CSRF protection)
        """
        # Validate origin for CSRF protection (before accepting connection)
        if not self._is_origin_allowed(websocket):
            origin = websocket.headers.get("origin")
            logger.warning(
                f"Rejected WebSocket from untrusted origin: {origin}"
            )
            MetricsCollector.record_ws_connection_rejected("origin")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await super().on_connect(websocket)

        # Attach Redis connection — needed by _post_auth_setup
        self.r = await get_auth_redis_connection()

        # Detect message format from query parameters (default: json)
        query_params = dict(websocket.query_params)
        self.message_format = query_params.get("format", "json").lower()

        if self.message_format not in ("json", "protobuf"):
            logger.warning(
                f"Invalid format '{self.message_format}' specified, defaulting to json"
            )
            self.message_format = "json"

        logger.debug(
            f"WebSocket connection using format: {self.message_format}"
        )

        # user is set after successful first-message auth in on_first_message
        self.user = UnauthenticatedUser()

    async def on_disconnect(self, websocket, close_code):  # type: ignore[no-untyped-def]
        """
        Handle WebSocket client disconnection and cleanup.

        Removes connection from the connection manager and connection limiter,
        then logs the disconnection event.
        """
        await super().on_disconnect(websocket, close_code)

        # Remove from connection manager if auth completed
        if hasattr(self, "session_key"):
            connection_manager.disconnect(self.session_key)

        # Remove from connection limiter if auth completed
        if not isinstance(self.user, UnauthenticatedUser) and hasattr(
            self, "connection_id"
        ):
            await connection_limiter.remove_connection(
                user_id=self.user.username, connection_id=self.connection_id
            )
            MetricsCollector.record_ws_disconnection()

        log_msg = (
            f"Client of user {self.user.username} disconnected with code {close_code}"
            if not isinstance(self.user, UnauthenticatedUser)
            else f"Unauthenticated user disconnected with code {close_code}"
        )

        logger.debug(log_msg)
