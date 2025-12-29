"""
Mock factory functions for WebSocket testing.

Provides mocks for WebSocket connections, consumers, and managers.
"""

from unittest.mock import AsyncMock, MagicMock


def create_mock_websocket():
    """
    Creates a mock WebSocket connection with common methods.

    Returns:
        MagicMock: Mocked WebSocket instance
    """
    from fastapi import WebSocket

    ws_mock = MagicMock(spec=WebSocket)

    # Send operations
    ws_mock.send_json = AsyncMock()
    ws_mock.send_text = AsyncMock()
    ws_mock.send_bytes = AsyncMock()

    # Receive operations
    ws_mock.receive_json = AsyncMock(return_value={})
    ws_mock.receive_text = AsyncMock(return_value="")
    ws_mock.receive_bytes = AsyncMock(return_value=b"")

    # Connection lifecycle
    ws_mock.accept = AsyncMock()
    ws_mock.close = AsyncMock()

    # State and headers
    ws_mock.client_state = MagicMock()
    ws_mock.application_state = MagicMock()
    ws_mock.headers = {}
    ws_mock.query_params = {}
    ws_mock.url = MagicMock()
    ws_mock.url.path = "/ws"

    return ws_mock


def create_mock_websocket_consumer():
    """
    Creates a mock WebSocket consumer (e.g., Web consumer).

    Returns:
        MagicMock: Mocked consumer instance
    """
    consumer_mock = MagicMock()

    # Consumer lifecycle methods
    consumer_mock.on_connect = AsyncMock()
    consumer_mock.on_disconnect = AsyncMock()
    consumer_mock.on_receive = AsyncMock()

    # Send operations
    consumer_mock.send_json = AsyncMock()
    consumer_mock.send_response = AsyncMock()

    return consumer_mock


def create_mock_connection_manager():
    """
    Creates a mock ConnectionManager instance.

    Returns:
        MagicMock: Mocked ConnectionManager instance
    """
    from app.managers.websocket_connection_manager import ConnectionManager

    manager_mock = MagicMock(spec=ConnectionManager)
    manager_mock.active_connections = []

    # Connection management
    manager_mock.connect = MagicMock()
    manager_mock.disconnect = MagicMock()

    # Broadcasting
    manager_mock.broadcast = AsyncMock()

    return manager_mock


def create_mock_package_router():
    """
    Creates a mock PackageRouter instance.

    Returns:
        MagicMock: Mocked PackageRouter instance
    """
    from app.routing import PackageRouter

    router_mock = MagicMock(spec=PackageRouter)

    # Request handling
    router_mock.handle_request = AsyncMock()
    router_mock.register = MagicMock(return_value=lambda f: f)

    # Permission checking
    router_mock.permissions_registry = {}
    router_mock.schema_registry = {}
    router_mock.handler_registry = {}

    return router_mock


def create_mock_broadcast_message(
    pkg_id: int = 1, status_code: int = 0, data: dict | None = None
):
    """
    Creates a mock BroadcastDataModel instance.

    Args:
        pkg_id: Package ID
        status_code: Status code
        data: Broadcast data

    Returns:
        BroadcastDataModel: Mocked broadcast message
    """
    from app.schemas.response import BroadcastDataModel

    return BroadcastDataModel(
        pkg_id=pkg_id, status_code=status_code, data=data or {}
    )
