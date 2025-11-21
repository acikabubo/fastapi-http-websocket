from typing import List

from fastapi import WebSocket

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.response import BroadcastDataModel


class ConnectionManager:
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
        Broadcasts the provided message to all active WebSocket connections managed by this `ConnectionManager` instance.

        Args:
            message (dict): The message to be broadcast to all active connections.
        """
        for connection in self.active_connections:
            await connection.send_json(message)


connection_manager = ConnectionManager()
