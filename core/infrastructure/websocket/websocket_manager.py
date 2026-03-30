"""WebSocket manager for handling real-time communication protocol."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps

from fastapi import WebSocket, WebSocketDisconnect

from .connection_manager import (
    ConnectionManager,
    ConnectionType,
    MessageType,
    WSMessage,
)

logger = logging.getLogger(__name__)


def broadcast_decorator(connection_type: ConnectionType):
    """Decorator for broadcasting messages to specific connection types."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return result

        return wrapper

    return decorator


class WebSocketManager:
    """High-level WebSocket manager for real-time dashboard communication."""

    def __init__(self):
        """Initialize WebSocket manager."""
        self.connection_manager = ConnectionManager()
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.heartbeat_interval = 30  # seconds
        self.max_message_size = 1024 * 1024  # 1MB

    async def handle_client_connection(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.DASHBOARD,
    ) -> str:
        """Handle a new WebSocket client connection."""
        client_id = await self.connection_manager.connect(
            websocket, connection_type, user_id, company_id
        )

        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._send_heartbeat(client_id))

        try:
            await self._receive_messages(client_id)
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            await self.connection_manager.disconnect(client_id)

        return client_id

    async def _receive_messages(self, client_id: str) -> None:
        """Receive and process messages from a client."""
        connection = self.connection_manager.active_connections.get(client_id)
        if not connection:
            return

        while True:
            try:
                data = await connection.websocket.receive_text()
                await self._process_message(client_id, data)
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error receiving message from {client_id}: {e}")
                # Send error response
                error_msg = WSMessage(
                    type=MessageType.ERROR,
                    payload={"error": str(e)},
                )
                await self.connection_manager.send_personal_message(error_msg, client_id)

    async def _process_message(self, client_id: str, data: str) -> None:
        """Process incoming message from client."""
        try:
            import json

            message_data = json.loads(data)
            message_type = MessageType(message_data.get("type"))
            payload = message_data.get("payload", {})

            logger.debug(f"Received {message_type.value} from {client_id}: {payload}")

            # Route to appropriate handler
            if message_type == MessageType.SUBSCRIBE:
                await self._handle_subscribe(client_id, payload)
            elif message_type == MessageType.UNSUBSCRIBE:
                await self._handle_unsubscribe(client_id, payload)
            elif message_type == MessageType.HEALTH_CHECK:
                await self._handle_health_check(client_id)
            elif message_type in self.message_handlers:
                await self.message_handlers[message_type](client_id, payload)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {client_id}: {e}")
        except ValueError as e:
            logger.error(f"Invalid message type from {client_id}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")

    async def _handle_subscribe(self, client_id: str, payload: Dict[str, Any]) -> None:
        """Handle metric/KPI subscription."""
        metric_ids = payload.get("metrics", [])
        kpi_ids = payload.get("kpis", [])

        for metric_id in metric_ids:
            self.connection_manager.subscribe_to_metric(client_id, metric_id)

        for kpi_id in kpi_ids:
            self.connection_manager.subscribe_to_kpi(client_id, kpi_id)

        # Send acknowledgment
        ack_msg = WSMessage(
            type=MessageType.ACKNOWLEDGMENT,
            payload={
                "action": "subscribe",
                "metrics": metric_ids,
                "kpis": kpi_ids,
            },
        )
        await self.connection_manager.send_personal_message(ack_msg, client_id)

        logger.info(
            f"Client {client_id} subscribed to {len(metric_ids)} metrics and {len(kpi_ids)} KPIs"
        )

    async def _handle_unsubscribe(self, client_id: str, payload: Dict[str, Any]) -> None:
        """Handle metric/KPI unsubscription."""
        metric_ids = payload.get("metrics", [])
        kpi_ids = payload.get("kpis", [])

        for metric_id in metric_ids:
            self.connection_manager.unsubscribe_from_metric(client_id, metric_id)

        for kpi_id in kpi_ids:
            self.connection_manager.unsubscribe_from_kpi(client_id, kpi_id)

        # Send acknowledgment
        ack_msg = WSMessage(
            type=MessageType.ACKNOWLEDGMENT,
            payload={
                "action": "unsubscribe",
                "metrics": metric_ids,
                "kpis": kpi_ids,
            },
        )
        await self.connection_manager.send_personal_message(ack_msg, client_id)

        logger.info(
            f"Client {client_id} unsubscribed from {len(metric_ids)} metrics and {len(kpi_ids)} KPIs"
        )

    async def _handle_health_check(self, client_id: str) -> None:
        """Handle health check from client."""
        health_msg = WSMessage(
            type=MessageType.HEALTH_CHECK,
            payload={"status": "healthy"},
        )
        await self.connection_manager.send_personal_message(health_msg, client_id)

    async def _send_heartbeat(self, client_id: str) -> None:
        """Send periodic heartbeat to client."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if client_id not in self.connection_manager.active_connections:
                    break

                heartbeat = WSMessage(
                    type=MessageType.HEALTH_CHECK,
                    payload={"type": "heartbeat"},
                )

                success = await self.connection_manager.send_personal_message(
                    heartbeat, client_id
                )
                if not success:
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error sending heartbeat to {client_id}: {e}")
                break

    async def broadcast_kpi_update(
        self,
        kpi_id: str,
        kpi_data: Dict[str, Any],
        exclude_client_id: Optional[str] = None,
    ) -> int:
        """Broadcast KPI update to all subscribers."""
        message = WSMessage(
            type=MessageType.KPI_UPDATE,
            payload={
                "kpi_id": kpi_id,
                "data": kpi_data,
            },
        )

        count = await self.connection_manager.send_to_kpi_subscribers(
            message, kpi_id, exclude_client_id
        )
        logger.debug(f"KPI update for {kpi_id} sent to {count} clients")
        return count

    async def broadcast_metric_update(
        self,
        metric_id: str,
        metric_data: Dict[str, Any],
        exclude_client_id: Optional[str] = None,
    ) -> int:
        """Broadcast metric update to all subscribers."""
        message = WSMessage(
            type=MessageType.METRIC_UPDATE,
            payload={
                "metric_id": metric_id,
                "data": metric_data,
            },
        )

        count = await self.connection_manager.send_to_metric_subscribers(
            message, metric_id, exclude_client_id
        )
        logger.debug(f"Metric update for {metric_id} sent to {count} clients")
        return count

    async def broadcast_alert(
        self,
        alert_id: str,
        alert_data: Dict[str, Any],
        company_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> int:
        """Broadcast alert notification to specific audience."""
        message = WSMessage(
            type=MessageType.ALERT_NOTIFICATION,
            payload={
                "alert_id": alert_id,
                "alert": alert_data,
            },
        )

        count = 0
        if company_id:
            count = await self.connection_manager.broadcast_to_company(message, company_id)
        elif user_id:
            count = await self.connection_manager.broadcast_to_user(message, user_id)
        else:
            count = await self.connection_manager.broadcast(message)

        logger.info(f"Alert {alert_id} sent to {count} clients")
        return count

    async def broadcast_trend_update(
        self,
        company_id: str,
        trend_data: Dict[str, Any],
    ) -> int:
        """Broadcast trend analysis update to company clients."""
        message = WSMessage(
            type=MessageType.TREND_UPDATE,
            payload={
                "company_id": company_id,
                "trend": trend_data,
            },
        )

        count = await self.connection_manager.broadcast_to_company(message, company_id)
        logger.debug(f"Trend update for company {company_id} sent to {count} clients")
        return count

    async def broadcast_forecast_update(
        self,
        company_id: str,
        forecast_data: Dict[str, Any],
    ) -> int:
        """Broadcast forecast update to company clients."""
        message = WSMessage(
            type=MessageType.FORECAST_UPDATE,
            payload={
                "company_id": company_id,
                "forecast": forecast_data,
            },
        )

        count = await self.connection_manager.broadcast_to_company(message, company_id)
        logger.debug(f"Forecast update for company {company_id} sent to {count} clients")
        return count

    async def send_bulk_update(
        self,
        client_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Send bulk update to specific client."""
        message = WSMessage(
            type=MessageType.BULK_UPDATE,
            payload=data,
        )

        success = await self.connection_manager.send_personal_message(message, client_id)
        logger.debug(f"Bulk update sent to {client_id}")
        return success

    def register_message_handler(
        self, message_type: MessageType, handler: Callable
    ) -> None:
        """Register custom message handler."""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type.value}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        stats = self.connection_manager.get_connection_stats()
        stats["heartbeat_interval"] = self.heartbeat_interval
        stats["max_message_size"] = self.max_message_size
        return stats

    async def cleanup(self) -> int:
        """Clean up inactive connections."""
        return await self.connection_manager.cleanup_inactive_connections()


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create global WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
