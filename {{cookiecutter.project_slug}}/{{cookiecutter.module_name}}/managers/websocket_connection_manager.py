import asyncio
from typing import List

from fastapi import WebSocket

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.response import BroadcastDataModel


class ConnectionManager:
    """
    Manager for active WebSocket connections.

    Tracks connected WebSocket clients and provides broadcast capabilities
    for sending messages to all active connections.
    """

    def __init__(self):
        """
        Initializes a new instance of the `ConnectionManager` class.

        The `active_connections` attribute is a list that stores the active WebSocket connections managed by this instance.
        """
        self.active_connections: List[WebSocket] = []

    def connect(self, websocket: WebSocket):
        """
        Accepts a new WebSocket connection and adds it to the list of active connections managed by this `ConnectionManager` instance.

        Args:
            websocket (WebSocket): The WebSocket connection to be accepted and added to the list of active connections.
        """
        self.active_connections.append(websocket)
        logger.debug(
            f"websocket object ({id(websocket)}) added to active connections"
        )

    def disconnect(self, websocket: WebSocket):
        """
        Removes the specified WebSocket connection from the list of active connections managed by this `ConnectionManager` instance.

        Args:
            websocket (WebSocket): The WebSocket connection to be removed
                from the list of active connections.
        """
        if websocket not in self.active_connections:
            return

        self.active_connections.remove(websocket)
        logger.debug(
            f"websocket objects ({id(websocket)}) removed from active connections"
        )

    async def broadcast(self, message: BroadcastDataModel):
        """
        Broadcasts message to all active connections concurrently.

        Uses asyncio.gather to send messages to all connections in parallel,
        improving performance when broadcasting to many connections.

        Args:
            message (BroadcastDataModel): The message to be broadcast to all
                active connections.
        """
        if not self.active_connections:
            return

        # Create a snapshot of connections to avoid modification during iteration
        connections_snapshot = list(self.active_connections)

        async def safe_send(connection: WebSocket):
            """
            Safely sends a message to a single connection with error handling.

            Args:
                connection (WebSocket): The WebSocket connection to send to.
            """
            try:
                await connection.send_json(message.model_dump(mode="json"))
            except Exception as e:
                logger.warning(
                    f"Failed to send to connection {id(connection)}: {e}"
                )
                self.disconnect(connection)

        await asyncio.gather(
            *[safe_send(conn) for conn in connections_snapshot],
            return_exceptions=True,
        )


connection_manager = ConnectionManager()
