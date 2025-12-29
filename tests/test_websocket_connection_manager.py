"""
Tests for WebSocket connection manager.

This module tests the ConnectionManager functionality including
connection tracking and broadcasting.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket

from app.managers.websocket_connection_manager import ConnectionManager
from app.schemas.response import BroadcastDataModel


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    def test_init(self):
        """Test ConnectionManager initialization."""
        manager = ConnectionManager()
        assert manager.active_connections == []

    def test_connect(self):
        """Test adding WebSocket connection."""
        manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)

        manager.connect(mock_ws)

        assert mock_ws in manager.active_connections
        assert len(manager.active_connections) == 1

    def test_connect_multiple(self):
        """Test adding multiple WebSocket connections."""
        manager = ConnectionManager()
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws2 = MagicMock(spec=WebSocket)
        mock_ws3 = MagicMock(spec=WebSocket)

        manager.connect(mock_ws1)
        manager.connect(mock_ws2)
        manager.connect(mock_ws3)

        assert len(manager.active_connections) == 3
        assert mock_ws1 in manager.active_connections
        assert mock_ws2 in manager.active_connections
        assert mock_ws3 in manager.active_connections

    def test_disconnect(self):
        """Test removing WebSocket connection."""
        manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)

        manager.connect(mock_ws)
        assert len(manager.active_connections) == 1

        manager.disconnect(mock_ws)
        assert len(manager.active_connections) == 0
        assert mock_ws not in manager.active_connections

    def test_disconnect_nonexistent(self):
        """Test disconnecting non-existent WebSocket (should do nothing)."""
        manager = ConnectionManager()
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws2 = MagicMock(spec=WebSocket)

        manager.connect(mock_ws1)
        assert len(manager.active_connections) == 1

        # Try to disconnect a connection that was never added
        manager.disconnect(mock_ws2)

        # Should not affect active_connections
        assert len(manager.active_connections) == 1
        assert mock_ws1 in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        """Test broadcast when no active connections (should return early)."""
        manager = ConnectionManager()

        broadcast_msg = BroadcastDataModel(
            pkg_id=1,
            status_code=0,
            data={"message": "test"},
        )

        # Should not raise exception
        await manager.broadcast(broadcast_msg)

        # No connections, nothing to verify

    @pytest.mark.asyncio
    async def test_broadcast_single_connection(self):
        """Test broadcast to single WebSocket connection."""
        manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()

        manager.connect(mock_ws)

        broadcast_msg = BroadcastDataModel(
            pkg_id=1,
            status_code=0,
            data={"message": "test"},
        )

        await manager.broadcast(broadcast_msg)

        # Verify send_json was called
        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["pkg_id"] == 1
        assert sent_data["data"] == {"message": "test"}

    @pytest.mark.asyncio
    async def test_broadcast_multiple_connections(self):
        """Test broadcast to multiple WebSocket connections."""
        manager = ConnectionManager()
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws2 = MagicMock(spec=WebSocket)
        mock_ws3 = MagicMock(spec=WebSocket)

        mock_ws1.send_json = AsyncMock()
        mock_ws2.send_json = AsyncMock()
        mock_ws3.send_json = AsyncMock()

        manager.connect(mock_ws1)
        manager.connect(mock_ws2)
        manager.connect(mock_ws3)

        broadcast_msg = BroadcastDataModel(
            pkg_id=1,
            status_code=0,
            data={"message": "test"},
        )

        await manager.broadcast(broadcast_msg)

        # All connections should receive the message
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()
        mock_ws3.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_error(self):
        """Test broadcast handles send errors gracefully."""
        manager = ConnectionManager()
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws2 = MagicMock(spec=WebSocket)

        # First connection will fail to send
        mock_ws1.send_json = AsyncMock(
            side_effect=Exception("Connection closed")
        )
        mock_ws2.send_json = AsyncMock()

        manager.connect(mock_ws1)
        manager.connect(mock_ws2)

        broadcast_msg = BroadcastDataModel(
            pkg_id=1,
            status_code=0,
            data={"message": "test"},
        )

        # Should not raise exception
        await manager.broadcast(broadcast_msg)

        # Failed connection should be disconnected
        assert mock_ws1 not in manager.active_connections

        # Second connection should still receive message
        mock_ws2.send_json.assert_called_once()
        assert mock_ws2 in manager.active_connections
