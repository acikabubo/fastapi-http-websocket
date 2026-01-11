"""
Tests for WebSocket connection manager.

This module tests the ConnectionManager functionality including
connection tracking and broadcasting.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket

from app.api.ws.constants import PkgID
from app.managers.websocket_connection_manager import ConnectionManager
from app.schemas.response import BroadcastDataModel


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    def test_init(self):
        """Test ConnectionManager initialization."""
        manager = ConnectionManager()
        assert manager.connections == {}

    def test_connect(self):
        """Test adding WebSocket connection."""
        manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)

        manager.connect("session:test1", mock_ws)

        assert "session:test1" in manager.connections
        assert manager.connections["session:test1"] is mock_ws
        assert len(manager.connections) == 1

    def test_connect_multiple(self):
        """Test adding multiple WebSocket connections."""
        manager = ConnectionManager()
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws2 = MagicMock(spec=WebSocket)
        mock_ws3 = MagicMock(spec=WebSocket)

        manager.connect("session:user1", mock_ws1)
        manager.connect("session:user2", mock_ws2)
        manager.connect("session:user3", mock_ws3)

        assert len(manager.connections) == 3
        assert manager.connections["session:user1"] is mock_ws1
        assert manager.connections["session:user2"] is mock_ws2
        assert manager.connections["session:user3"] is mock_ws3

    def test_disconnect(self):
        """Test removing WebSocket connection."""
        manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)

        manager.connect("session:test1", mock_ws)
        assert len(manager.connections) == 1

        manager.disconnect("session:test1")
        assert len(manager.connections) == 0
        assert "session:test1" not in manager.connections

    def test_disconnect_nonexistent(self):
        """Test disconnecting non-existent WebSocket (should do nothing)."""
        manager = ConnectionManager()
        mock_ws1 = MagicMock(spec=WebSocket)

        manager.connect("session:test1", mock_ws1)
        assert len(manager.connections) == 1

        # Try to disconnect a connection that was never added
        manager.disconnect("session:test2")

        # Should not affect connections
        assert len(manager.connections) == 1
        assert "session:test1" in manager.connections

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        """Test broadcast when no active connections (should return early)."""
        manager = ConnectionManager()

        broadcast_msg = BroadcastDataModel(
            pkg_id=PkgID.TEST_HANDLER,
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

        manager.connect("session:test1", mock_ws)

        broadcast_msg = BroadcastDataModel(
            pkg_id=PkgID.TEST_HANDLER,
            data={"message": "test"},
        )

        await manager.broadcast(broadcast_msg)

        # Verify send_json was called
        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["pkg_id"] == PkgID.TEST_HANDLER
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

        manager.connect("session:user1", mock_ws1)
        manager.connect("session:user2", mock_ws2)
        manager.connect("session:user3", mock_ws3)

        broadcast_msg = BroadcastDataModel(
            pkg_id=PkgID.TEST_HANDLER,
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

        manager.connect("session:test1", mock_ws1)
        manager.connect("session:test2", mock_ws2)

        broadcast_msg = BroadcastDataModel(
            pkg_id=PkgID.TEST_HANDLER,
            data={"message": "test"},
        )

        # Should not raise exception
        await manager.broadcast(broadcast_msg)

        # Failed connection should be disconnected
        assert "session:test1" not in manager.connections

        # Second connection should still receive message
        mock_ws2.send_json.assert_called_once()
        assert "session:test2" in manager.connections
