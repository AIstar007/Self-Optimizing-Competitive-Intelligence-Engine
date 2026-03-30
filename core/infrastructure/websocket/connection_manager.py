"""WebSocket connection management for real-time dashboard updates."""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConnectionType(str, Enum):
    """Types of WebSocket connections."""

    DASHBOARD = "dashboard"
    ANALYTICS = "analytics"
    ALERTS = "alerts"
    METRICS = "metrics"


class MessageType(str, Enum):
    """Types of WebSocket messages."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    KPI_UPDATE = "kpi_update"
    METRIC_UPDATE = "metric_update"
    ALERT_NOTIFICATION = "alert_notification"
    TREND_UPDATE = "trend_update"
    FORECAST_UPDATE = "forecast_update"
    HEALTH_CHECK = "health_check"
    DASHBOARD_CONFIG = "dashboard_config"
    BULK_UPDATE = "bulk_update"
    ERROR = "error"
    ACKNOWLEDGMENT = "acknowledgment"


@dataclass
class WSMessage(BaseModel):
    """WebSocket message structure."""

    type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message_id: str = field(default_factory=lambda: str(uuid4()))

    class Config:
        json_encoders = {MessageType: lambda v: v.value, datetime: lambda v: v.isoformat()}

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(
            {
                "type": self.type.value,
                "payload": self.payload,
                "timestamp": self.timestamp.isoformat(),
                "message_id": self.message_id,
            }
        )


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client."""

    client_id: str
    websocket: WebSocket
    connection_type: ConnectionType
    user_id: Optional[str] = None
    company_id: Optional[str] = None
    subscribed_metrics: Set[str] = field(default_factory=set)
    subscribed_kpis: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    async def send_message(self, message: WSMessage) -> bool:
        """Send message to connected client."""
        try:
            self.last_activity = datetime.utcnow()
            await self.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.error(f"Error sending message to {self.client_id}: {e}")
            return False

    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Send JSON data to connected client."""
        try:
            self.last_activity = datetime.utcnow()
            await self.websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending JSON to {self.client_id}: {e}")
            return False

    def subscribe_to_metric(self, metric_id: str) -> None:
        """Subscribe client to a metric stream."""
        self.subscribed_metrics.add(metric_id)
        logger.debug(f"Client {self.client_id} subscribed to metric {metric_id}")

    def unsubscribe_from_metric(self, metric_id: str) -> None:
        """Unsubscribe client from a metric stream."""
        self.subscribed_metrics.discard(metric_id)
        logger.debug(f"Client {self.client_id} unsubscribed from metric {metric_id}")

    def subscribe_to_kpi(self, kpi_id: str) -> None:
        """Subscribe client to a KPI stream."""
        self.subscribed_kpis.add(kpi_id)
        logger.debug(f"Client {self.client_id} subscribed to KPI {kpi_id}")

    def unsubscribe_from_kpi(self, kpi_id: str) -> None:
        """Unsubscribe client from a KPI stream."""
        self.subscribed_kpis.discard(kpi_id)
        logger.debug(f"Client {self.client_id} unsubscribed from KPI {kpi_id}")

    def is_subscribed_to_metric(self, metric_id: str) -> bool:
        """Check if client is subscribed to a metric."""
        return metric_id in self.subscribed_metrics

    def is_subscribed_to_kpi(self, kpi_id: str) -> bool:
        """Check if client is subscribed to a KPI."""
        return kpi_id in self.subscribed_kpis


class ConnectionManager:
    """Manages WebSocket connections for real-time communication."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, ClientConnection] = {}
        self.connections_by_user: Dict[str, Set[str]] = {}
        self.connections_by_company: Dict[str, Set[str]] = {}
        self.connections_by_metric: Dict[str, Set[str]] = {}
        self.connections_by_kpi: Dict[str, Set[str]] = {}
        self.message_buffer: asyncio.Queue = asyncio.Queue()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: WebSocket,
        connection_type: ConnectionType,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> str:
        """Register a new WebSocket connection."""
        await websocket.accept()
        client_id = str(uuid4())

        connection = ClientConnection(
            client_id=client_id,
            websocket=websocket,
            connection_type=connection_type,
            user_id=user_id,
            company_id=company_id,
        )

        self.active_connections[client_id] = connection

        if user_id:
            if user_id not in self.connections_by_user:
                self.connections_by_user[user_id] = set()
            self.connections_by_user[user_id].add(client_id)

        if company_id:
            if company_id not in self.connections_by_company:
                self.connections_by_company[company_id] = set()
            self.connections_by_company[company_id].add(client_id)

        logger.info(
            f"Client {client_id} connected ({connection_type.value}). "
            f"Total connections: {len(self.active_connections)}"
        )

        return client_id

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket client."""
        if client_id not in self.active_connections:
            return

        connection = self.active_connections.pop(client_id)

        if connection.user_id and connection.user_id in self.connections_by_user:
            self.connections_by_user[connection.user_id].discard(client_id)

        if connection.company_id and connection.company_id in self.connections_by_company:
            self.connections_by_company[connection.company_id].discard(client_id)

        # Clean up metric subscriptions
        for metric_id in list(connection.subscribed_metrics):
            if metric_id in self.connections_by_metric:
                self.connections_by_metric[metric_id].discard(client_id)

        # Clean up KPI subscriptions
        for kpi_id in list(connection.subscribed_kpis):
            if kpi_id in self.connections_by_kpi:
                self.connections_by_kpi[kpi_id].discard(client_id)

        logger.info(f"Client {client_id} disconnected. Remaining: {len(self.active_connections)}")

    async def send_personal_message(self, message: WSMessage, client_id: str) -> bool:
        """Send message to a specific client."""
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]
        return await connection.send_message(message)

    async def broadcast(
        self, message: WSMessage, exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all connected clients."""
        count = 0
        disconnected = []

        for client_id, connection in self.active_connections.items():
            if exclude_client_id and client_id == exclude_client_id:
                continue

            if await connection.send_message(message):
                count += 1
            else:
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

        logger.debug(f"Broadcast message sent to {count} clients")
        return count

    async def broadcast_to_company(
        self, message: WSMessage, company_id: str, exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all clients of a company."""
        if company_id not in self.connections_by_company:
            return 0

        count = 0
        disconnected = []

        for client_id in self.connections_by_company[company_id]:
            if exclude_client_id and client_id == exclude_client_id:
                continue

            if client_id in self.active_connections:
                connection = self.active_connections[client_id]
                if await connection.send_message(message):
                    count += 1
                else:
                    disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

        logger.debug(f"Broadcast to company {company_id} sent to {count} clients")
        return count

    async def broadcast_to_user(
        self, message: WSMessage, user_id: str, exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all clients of a user."""
        if user_id not in self.connections_by_user:
            return 0

        count = 0
        disconnected = []

        for client_id in self.connections_by_user[user_id]:
            if exclude_client_id and client_id == exclude_client_id:
                continue

            if client_id in self.active_connections:
                connection = self.active_connections[client_id]
                if await connection.send_message(message):
                    count += 1
                else:
                    disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

        logger.debug(f"Broadcast to user {user_id} sent to {count} clients")
        return count

    async def send_to_metric_subscribers(
        self, message: WSMessage, metric_id: str, exclude_client_id: Optional[str] = None
    ) -> int:
        """Send message to all subscribers of a metric."""
        if metric_id not in self.connections_by_metric:
            return 0

        count = 0
        disconnected = []

        for client_id in self.connections_by_metric[metric_id]:
            if exclude_client_id and client_id == exclude_client_id:
                continue

            if client_id in self.active_connections:
                connection = self.active_connections[client_id]
                if await connection.send_message(message):
                    count += 1
                else:
                    disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

        return count

    async def send_to_kpi_subscribers(
        self, message: WSMessage, kpi_id: str, exclude_client_id: Optional[str] = None
    ) -> int:
        """Send message to all subscribers of a KPI."""
        if kpi_id not in self.connections_by_kpi:
            return 0

        count = 0
        disconnected = []

        for client_id in self.connections_by_kpi[kpi_id]:
            if exclude_client_id and client_id == exclude_client_id:
                continue

            if client_id in self.active_connections:
                connection = self.active_connections[client_id]
                if await connection.send_message(message):
                    count += 1
                else:
                    disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

        return count

    def subscribe_to_metric(self, client_id: str, metric_id: str) -> bool:
        """Subscribe client to metric updates."""
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]
        connection.subscribe_to_metric(metric_id)

        if metric_id not in self.connections_by_metric:
            self.connections_by_metric[metric_id] = set()
        self.connections_by_metric[metric_id].add(client_id)

        logger.debug(f"Client {client_id} subscribed to metric {metric_id}")
        return True

    def unsubscribe_from_metric(self, client_id: str, metric_id: str) -> bool:
        """Unsubscribe client from metric updates."""
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]
        connection.unsubscribe_from_metric(metric_id)

        if metric_id in self.connections_by_metric:
            self.connections_by_metric[metric_id].discard(client_id)

        logger.debug(f"Client {client_id} unsubscribed from metric {metric_id}")
        return True

    def subscribe_to_kpi(self, client_id: str, kpi_id: str) -> bool:
        """Subscribe client to KPI updates."""
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]
        connection.subscribe_to_kpi(kpi_id)

        if kpi_id not in self.connections_by_kpi:
            self.connections_by_kpi[kpi_id] = set()
        self.connections_by_kpi[kpi_id].add(client_id)

        logger.debug(f"Client {client_id} subscribed to KPI {kpi_id}")
        return True

    def unsubscribe_from_kpi(self, client_id: str, kpi_id: str) -> bool:
        """Unsubscribe client from KPI updates."""
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]
        connection.unsubscribe_from_kpi(kpi_id)

        if kpi_id in self.connections_by_kpi:
            self.connections_by_kpi[kpi_id].discard(client_id)

        logger.debug(f"Client {client_id} unsubscribed from KPI {kpi_id}")
        return True

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "total_users": len(self.connections_by_user),
            "total_companies": len(self.connections_by_company),
            "total_metric_subscriptions": sum(
                len(clients) for clients in self.connections_by_metric.values()
            ),
            "total_kpi_subscriptions": sum(
                len(clients) for clients in self.connections_by_kpi.values()
            ),
            "connections_by_type": {
                ct.value: sum(
                    1
                    for c in self.active_connections.values()
                    if c.connection_type == ct
                )
                for ct in ConnectionType
            },
        }

    async def cleanup_inactive_connections(self, timeout_seconds: int = 300) -> int:
        """Remove inactive connections."""
        now = datetime.utcnow()
        disconnected = []

        for client_id, connection in self.active_connections.items():
            elapsed = (now - connection.last_activity).total_seconds()
            if elapsed > timeout_seconds:
                disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect(client_id)

        if disconnected:
            logger.info(f"Cleaned up {len(disconnected)} inactive connections")

        return len(disconnected)

    def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection."""
        if client_id not in self.active_connections:
            return None

        conn = self.active_connections[client_id]
        return {
            "client_id": conn.client_id,
            "connection_type": conn.connection_type.value,
            "user_id": conn.user_id,
            "company_id": conn.company_id,
            "subscribed_metrics": list(conn.subscribed_metrics),
            "subscribed_kpis": list(conn.subscribed_kpis),
            "connected_at": conn.connected_at.isoformat(),
            "last_activity": conn.last_activity.isoformat(),
            "is_active": conn.is_active,
        }
