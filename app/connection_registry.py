"""WebSocket connection registry for managing active client connections."""

from starlette.websockets import WebSocket

# Global registry mapping session keys to WebSocket connections
ws_clients: dict[str, WebSocket] = {}
