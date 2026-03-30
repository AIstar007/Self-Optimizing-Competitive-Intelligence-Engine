"""WebSocket support for real-time communication."""

from core.interfaces.websocket.connection import (
    ConnectionManager,
    WebSocketHandler,
    EventBroadcaster,
    connection_manager,
    event_broadcaster,
)
from core.interfaces.websocket.routes import router

__all__ = [
    "ConnectionManager",
    "WebSocketHandler",
    "EventBroadcaster",
    "connection_manager",
    "event_broadcaster",
    "router",
]
