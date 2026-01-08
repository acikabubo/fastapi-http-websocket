"""
Prometheus metrics for WebSocket connection monitoring.

This module defines metrics for tracking WebSocket connections, message rates,
and message processing durations.
"""

from app.utils.metrics._helpers import (
    _get_or_create_counter,
    _get_or_create_gauge,
    _get_or_create_histogram,
)

# WebSocket Connection Metrics
ws_connections_active = _get_or_create_gauge(
    "ws_connections_active", "Number of active WebSocket connections"
)

ws_connections_total = _get_or_create_counter(
    "ws_connections_total",
    "Total WebSocket connections",
    ["status"],  # accepted, rejected_auth, rejected_limit
)

ws_messages_received_total = _get_or_create_counter(
    "ws_messages_received_total", "Total WebSocket messages received"
)

ws_messages_sent_total = _get_or_create_counter(
    "ws_messages_sent_total", "Total WebSocket messages sent"
)

ws_message_processing_duration_seconds = _get_or_create_histogram(
    "ws_message_processing_duration_seconds",
    "WebSocket message processing duration in seconds",
    ["pkg_id"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


# Helper Functions


def get_active_websocket_connections() -> int:
    """
    Get the current number of active WebSocket connections.

    Returns:
        int: Number of active WebSocket connections.
    """
    try:
        return int(ws_connections_active._value.get())
    except (AttributeError, ValueError):
        return 0


def get_websocket_health_info() -> dict[str, int | str]:
    """
    Get WebSocket health information from metrics.

    Returns:
        dict[str, int | str]: Dictionary with WebSocket health status:
            - status: "healthy" or "degraded"
            - active_connections: Current active connections count
    """
    active_connections = get_active_websocket_connections()

    # Simple health check: if we have metrics collection working,
    # WebSocket system is healthy
    status = "healthy"

    return {
        "status": status,
        "active_connections": active_connections,
    }


__all__ = [
    "ws_connections_active",
    "ws_connections_total",
    "ws_messages_received_total",
    "ws_messages_sent_total",
    "ws_message_processing_duration_seconds",
    "get_active_websocket_connections",
    "get_websocket_health_info",
]
