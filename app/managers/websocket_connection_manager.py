import asyncio
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.logging import logger
from app.schemas.response import BroadcastDataModel


class ConnectionManager:
    """
    Manager for active WebSocket connections.

    Tracks connected WebSocket clients using session keys for O(1) lookups
    and provides broadcast capabilities for sending messages to all active
    connections.
    """

    def __init__(self) -> None:
        """
        Initializes a new instance of the `ConnectionManager` class.

        The `connections` attribute is a dict mapping session keys to
        WebSocket connections for efficient lookups.
        """
        self.connections: dict[str, WebSocket] = {}

    def connect(self, session_key: str, websocket: WebSocket) -> None:
        """
        Adds a new WebSocket connection with associated session key.

        Args:
            session_key: Unique identifier for this connection (e.g., user session).
            websocket: The WebSocket connection to be added.
        """
        self.connections[session_key] = websocket
        logger.debug(
            f"websocket object ({id(websocket)}) added to active connections "
            f"with key {session_key}"
        )

    def disconnect(self, session_key: str) -> None:
        """
        Removes a WebSocket connection by session key.

        Args:
            session_key: The session key of the connection to remove.
        """
        if session_key not in self.connections:
            return

        websocket = self.connections.pop(session_key)
        logger.debug(
            f"websocket object ({id(websocket)}) removed from active connections "
            f"for key {session_key}"
        )

    def get_connection(self, session_key: str) -> WebSocket | None:
        """
        Get WebSocket connection by session key.

        Args:
            session_key: The session key to look up.

        Returns:
            WebSocket connection if found, None otherwise.
        """
        return self.connections.get(session_key)

    async def broadcast(self, message: BroadcastDataModel[Any]) -> None:
        """
        Broadcasts message to all active connections concurrently.

        Uses asyncio.gather to send messages to all connections in parallel,
        improving performance when broadcasting to many connections.

        Args:
            message (BroadcastDataModel[Any]): The message to be broadcast to all
                active connections.
        """
        if not self.connections:
            return

        # Create a snapshot of connections to avoid modification during iteration
        connections_snapshot = list(self.connections.items())

        async def safe_send(session_key: str, connection: WebSocket) -> None:
            """
            Safely sends a message to a single connection with error handling.

            Args:
                session_key: The session key for this connection.
                connection: The WebSocket connection to send to.
            """
            try:
                await connection.send_json(message.model_dump(mode="json"))
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                # WebSocketDisconnect: Client disconnected
                # ConnectionError: Network errors
                # RuntimeError: WebSocket in invalid state
                logger.warning(
                    f"Failed to send to connection {id(connection)} "
                    f"(key: {session_key}): {e}"
                )
                self.disconnect(session_key)
            except Exception as e:
                # Catch-all for unexpected send errors
                logger.warning(
                    f"Unexpected error sending to connection {id(connection)} "
                    f"(key: {session_key}): {e}"
                )
                self.disconnect(session_key)

        await asyncio.gather(
            *[safe_send(key, conn) for key, conn in connections_snapshot],
            return_exceptions=True,
        )


connection_manager = ConnectionManager()
