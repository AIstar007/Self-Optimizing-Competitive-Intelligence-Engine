"""WebSocket support for real-time updates."""

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.subscribers: dict[str, list[Callable]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"Client connected: {client_id}")

    async def disconnect(self, client_id: str, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            client_id: Client identifier
            websocket: WebSocket connection to remove
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"Client disconnected: {client_id}")

    async def broadcast(self, channel: str, message: dict[str, Any]):
        """
        Broadcast message to all subscribers on a channel.

        Args:
            channel: Channel name
            message: Message data
        """
        if channel not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[channel]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(websocket)

        for ws in disconnected:
            await self.disconnect(channel, ws)

    async def send_to_client(self, client_id: str, message: dict[str, Any]):
        """
        Send message to specific client.

        Args:
            client_id: Client identifier
            message: Message data
        """
        if client_id not in self.active_connections:
            logger.warning(f"Client not connected: {client_id}")
            return

        for websocket in self.active_connections[client_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")

    def subscribe(self, channel: str, handler: Callable):
        """
        Subscribe handler to a channel.

        Args:
            channel: Channel name
            handler: Async handler function
        """
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(handler)

    async def publish(self, channel: str, data: Any):
        """
        Publish data to channel subscribers.

        Args:
            channel: Channel name
            data: Data to publish
        """
        if channel not in self.subscribers:
            return

        for handler in self.subscribers[channel]:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error in subscriber handler: {e}")

    def get_connected_clients(self, channel: Optional[str] = None) -> list[str]:
        """
        Get list of connected clients.

        Args:
            channel: Optional specific channel

        Returns:
            List of client IDs
        """
        if channel:
            return [channel] if channel in self.active_connections else []
        return list(self.active_connections.keys())

    def get_client_count(self) -> int:
        """
        Get total number of connected clients.

        Returns:
            Number of connected clients
        """
        return len(self.active_connections)


class WebSocketHandler:
    """Handle WebSocket messages and events."""

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize handler.

        Args:
            connection_manager: Connection manager instance
        """
        self.manager = connection_manager
        self.message_handlers: dict[str, Callable] = {}

    def register_handler(self, message_type: str, handler: Callable):
        """
        Register handler for message type.

        Args:
            message_type: Message type identifier
            handler: Async handler function
        """
        self.message_handlers[message_type] = handler

    async def handle_message(self, message: dict[str, Any], client_id: str):
        """
        Handle incoming message.

        Args:
            message: Message data
            client_id: Client identifier
        """
        message_type = message.get("type")
        handler = self.message_handlers.get(message_type)

        if handler:
            try:
                await handler(message, client_id)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                error_msg = {
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                await self.manager.send_to_client(client_id, error_msg)
        else:
            logger.warning(f"No handler for message type: {message_type}")


class EventBroadcaster:
    """Broadcast system events to WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize broadcaster.

        Args:
            connection_manager: Connection manager instance
        """
        self.manager = connection_manager

    async def broadcast_workflow_status(self, workflow_id: str, status: str, data: dict):
        """
        Broadcast workflow status update.

        Args:
            workflow_id: Workflow ID
            status: New status
            data: Additional data
        """
        message = {
            "type": "workflow_status",
            "workflow_id": workflow_id,
            "status": status,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast(f"workflow:{workflow_id}", message)

    async def broadcast_task_status(self, task_id: str, status: str, result: Optional[dict] = None):
        """
        Broadcast task status update.

        Args:
            task_id: Task ID
            status: New status
            result: Optional task result
        """
        message = {
            "type": "task_status",
            "task_id": task_id,
            "status": status,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast(f"task:{task_id}", message)

    async def broadcast_agent_status(self, agent_id: str, status: str, message_text: Optional[str] = None):
        """
        Broadcast agent status update.

        Args:
            agent_id: Agent ID
            status: New status
            message_text: Optional status message
        """
        message = {
            "type": "agent_status",
            "agent_id": agent_id,
            "status": status,
            "message": message_text,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast(f"agent:{agent_id}", message)

    async def broadcast_signal(self, signal_data: dict):
        """
        Broadcast new signal.

        Args:
            signal_data: Signal data
        """
        message = {
            "type": "signal",
            "data": signal_data,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast("signals", message)

    async def broadcast_report_complete(self, report_id: str, report_data: dict):
        """
        Broadcast report completion.

        Args:
            report_id: Report ID
            report_data: Report data
        """
        message = {
            "type": "report_complete",
            "report_id": report_id,
            "data": report_data,
            "timestamp": datetime.now().isoformat(),
        }
        await self.manager.broadcast("reports", message)

    async def broadcast_error(self, error_code: str, error_message: str, channel: Optional[str] = None):
        """
        Broadcast error to clients.

        Args:
            error_code: Error code
            error_message: Error message
            channel: Optional specific channel
        """
        message = {
            "type": "error",
            "code": error_code,
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
        }
        if channel:
            await self.manager.broadcast(channel, message)
        else:
            for client_id in self.manager.get_connected_clients():
                await self.manager.send_to_client(client_id, message)


# Global connection manager instance
connection_manager = ConnectionManager()
event_broadcaster = EventBroadcaster(connection_manager)


async def websocket_receiver(websocket: WebSocket, client_id: str, handler: WebSocketHandler):
    """
    Receive and process WebSocket messages.

    Args:
        websocket: WebSocket connection
        client_id: Client identifier
        handler: Message handler
    """
    try:
        while True:
            data = await websocket.receive_json()
            await handler.handle_message(data, client_id)
    except WebSocketDisconnect:
        await connection_manager.disconnect(client_id, websocket)
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(client_id, websocket)
