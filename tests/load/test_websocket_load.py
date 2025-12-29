"""
WebSocket load tests for concurrent connections.

Tests application behavior under high load with multiple concurrent
WebSocket connections and message throughput.

Run with: pytest tests/load/test_websocket_load.py -v -s
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.managers.websocket_connection_manager import ConnectionManager
from app.schemas.response import BroadcastDataModel

# Mark all tests in this module as slow (skip by default, run with -m load)
pytestmark = pytest.mark.load


@pytest.fixture
def connection_manager():
    """
    Provides a fresh ConnectionManager instance for each test.

    Returns:
        ConnectionManager: Fresh manager instance
    """
    return ConnectionManager()


class TestWebSocketConcurrentConnections:
    """Tests for concurrent WebSocket connection handling."""

    @pytest.mark.asyncio
    async def test_100_concurrent_connections(self, connection_manager):
        """Test handling 100 concurrent WebSocket connections."""
        mock_connections = []

        # Create 100 mock WebSocket connections
        for i in range(100):
            ws_mock = MagicMock()
            ws_mock.send_json = AsyncMock()
            mock_connections.append(ws_mock)

        # Add all connections
        start_time = time.time()
        for ws in mock_connections:
            connection_manager.connect(ws)
        connection_time = time.time() - start_time

        # Verify all connections are tracked
        assert len(connection_manager.active_connections) == 100, (
            "Should track 100 connections"
        )
        assert connection_time < 1.0, (
            f"Connection time {connection_time:.3f}s should be < 1s"
        )

        # Test broadcast to all connections
        broadcast_msg = BroadcastDataModel(
            pkg_id=1, status_code=0, data={"message": "test"}
        )

        start_time = time.time()
        await connection_manager.broadcast(broadcast_msg)
        broadcast_time = time.time() - start_time

        # Verify all connections received the message
        for ws in mock_connections:
            ws.send_json.assert_called_once()

        # Broadcast to 100 connections should complete quickly
        assert broadcast_time < 2.0, (
            f"Broadcast time {broadcast_time:.3f}s should be < 2s"
        )

    @pytest.mark.asyncio
    async def test_1000_concurrent_connections(self, connection_manager):
        """Test handling 1000 concurrent WebSocket connections."""
        mock_connections = []

        # Create 1000 mock WebSocket connections
        for i in range(1000):
            ws_mock = MagicMock()
            ws_mock.send_json = AsyncMock()
            mock_connections.append(ws_mock)

        # Add all connections
        start_time = time.time()
        for ws in mock_connections:
            connection_manager.connect(ws)
        connection_time = time.time() - start_time

        # Verify all connections are tracked
        assert len(connection_manager.active_connections) == 1000, (
            "Should track 1000 connections"
        )
        assert connection_time < 5.0, (
            f"Connection time {connection_time:.3f}s should be < 5s"
        )

        # Test broadcast to all connections
        broadcast_msg = BroadcastDataModel(
            pkg_id=1, status_code=0, data={"message": "load_test"}
        )

        start_time = time.time()
        await connection_manager.broadcast(broadcast_msg)
        broadcast_time = time.time() - start_time

        # Verify all connections received the message
        for ws in mock_connections:
            ws.send_json.assert_called_once()

        # Broadcast to 1000 connections should complete in reasonable time
        assert broadcast_time < 10.0, (
            f"Broadcast time {broadcast_time:.3f}s should be < 10s"
        )

        # Measure memory usage by checking active connections
        assert len(connection_manager.active_connections) == 1000, (
            "All connections still tracked"
        )

    @pytest.mark.asyncio
    async def test_connection_churn(self, connection_manager):
        """
        Test rapid connect/disconnect cycles (connection churn).

        Simulates realistic scenario where clients frequently
        connect and disconnect.
        """
        # Perform 500 connect/disconnect cycles
        cycles = 500
        start_time = time.time()

        for i in range(cycles):
            ws_mock = MagicMock()
            ws_mock.send_json = AsyncMock()

            # Connect
            connection_manager.connect(ws_mock)
            assert len(connection_manager.active_connections) == 1

            # Disconnect
            connection_manager.disconnect(ws_mock)
            assert len(connection_manager.active_connections) == 0

        churn_time = time.time() - start_time

        # 500 cycles should complete quickly
        assert churn_time < 5.0, (
            f"Churn time {churn_time:.3f}s should be < 5s for 500 cycles"
        )

        # No connections should remain
        assert len(connection_manager.active_connections) == 0


class TestWebSocketMessageThroughput:
    """Tests for WebSocket message throughput under load."""

    @pytest.mark.asyncio
    async def test_high_frequency_broadcasts(self, connection_manager):
        """Test high-frequency broadcast throughput."""
        # Setup 50 connections
        mock_connections = []
        for i in range(50):
            ws_mock = MagicMock()
            ws_mock.send_json = AsyncMock()
            mock_connections.append(ws_mock)
            connection_manager.connect(ws_mock)

        # Send 100 broadcasts rapidly
        broadcasts = 100
        start_time = time.time()

        for i in range(broadcasts):
            broadcast_msg = BroadcastDataModel(
                pkg_id=1, status_code=0, data={"seq": i}
            )
            await connection_manager.broadcast(broadcast_msg)

        throughput_time = time.time() - start_time

        # 100 broadcasts to 50 connections = 5000 messages
        total_messages = broadcasts * len(mock_connections)
        messages_per_second = total_messages / throughput_time

        # Verify throughput
        assert messages_per_second > 500, (
            f"Throughput {messages_per_second:.0f} msg/s should be > 500 msg/s"
        )

        # Verify all connections received all messages
        for ws in mock_connections:
            assert ws.send_json.call_count == broadcasts

    @pytest.mark.asyncio
    async def test_large_message_broadcast(self, connection_manager):
        """Test broadcasting large messages (e.g., 100KB payload)."""
        # Setup 20 connections
        mock_connections = []
        for i in range(20):
            ws_mock = MagicMock()
            ws_mock.send_json = AsyncMock()
            mock_connections.append(ws_mock)
            connection_manager.connect(ws_mock)

        # Create large payload (~100KB JSON)
        large_data = {
            "records": [{"id": i, "data": "x" * 1000} for i in range(100)]
        }

        broadcast_msg = BroadcastDataModel(
            pkg_id=1, status_code=0, data=large_data
        )

        start_time = time.time()
        await connection_manager.broadcast(broadcast_msg)
        broadcast_time = time.time() - start_time

        # Large message broadcast should still be fast with asyncio.gather
        assert broadcast_time < 2.0, (
            f"Large message broadcast {broadcast_time:.3f}s should be < 2s"
        )

        # Verify all connections received the large message
        for ws in mock_connections:
            ws.send_json.assert_called_once()


class TestWebSocketErrorResilience:
    """Tests for WebSocket error handling under load."""

    @pytest.mark.asyncio
    async def test_partial_connection_failures(self, connection_manager):
        """Test resilience when some connections fail during broadcast."""
        # Setup 100 connections, 20% will fail
        mock_connections = []
        failing_connections = []

        for i in range(100):
            ws_mock = MagicMock()

            if i % 5 == 0:  # 20% failure rate
                ws_mock.send_json = AsyncMock(
                    side_effect=ConnectionError("Connection lost")
                )
                failing_connections.append(ws_mock)
            else:
                ws_mock.send_json = AsyncMock()

            mock_connections.append(ws_mock)
            connection_manager.connect(ws_mock)

        # Broadcast message
        broadcast_msg = BroadcastDataModel(
            pkg_id=1, status_code=0, data={"message": "test"}
        )

        await connection_manager.broadcast(broadcast_msg)

        # Verify failed connections were removed
        assert len(connection_manager.active_connections) == 80, (
            "Failed connections should be removed"
        )

        # Verify successful connections still tracked
        for ws in mock_connections:
            if ws not in failing_connections:
                assert ws in connection_manager.active_connections, (
                    "Successful connections should remain"
                )

    @pytest.mark.asyncio
    async def test_concurrent_broadcasts(self, connection_manager):
        """Test multiple concurrent broadcasts do not interfere."""
        # Setup 30 connections
        mock_connections = []
        for i in range(30):
            ws_mock = MagicMock()
            ws_mock.send_json = AsyncMock()
            mock_connections.append(ws_mock)
            connection_manager.connect(ws_mock)

        # Send 10 broadcasts concurrently
        async def send_broadcast(seq: int):
            broadcast_msg = BroadcastDataModel(
                pkg_id=seq, status_code=0, data={"seq": seq}
            )
            await connection_manager.broadcast(broadcast_msg)

        start_time = time.time()
        await asyncio.gather(*[send_broadcast(i) for i in range(10)])
        concurrent_time = time.time() - start_time

        # Concurrent broadcasts should complete quickly
        assert concurrent_time < 2.0, (
            f"Concurrent broadcasts {concurrent_time:.3f}s should be < 2s"
        )

        # Each connection should receive 10 messages
        for ws in mock_connections:
            assert ws.send_json.call_count == 10, (
                "Each connection should receive all 10 broadcasts"
            )
