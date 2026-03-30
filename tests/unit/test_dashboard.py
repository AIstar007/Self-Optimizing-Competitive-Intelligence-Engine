"""Unit tests for dashboard components."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from core.infrastructure.websocket.connection_manager import (
    ConnectionManager,
    ClientConnection,
    ConnectionType,
    MessageType,
    WSMessage,
)
from core.infrastructure.websocket.websocket_manager import WebSocketManager
from core.application.services.streaming_service import (
    StreamingService,
    StreamType,
    StreamEvent,
)
from core.application.services.alert_service import AlertService, AlertSeverity, AlertRule
from core.infrastructure.alerts.alert_delivery import (
    AlertDeliveryManager,
    EmailDeliveryProvider,
    SlackDeliveryProvider,
)


# Fixtures
@pytest.fixture
def connection_manager():
    """Create connection manager."""
    return ConnectionManager()


@pytest.fixture
def websocket_manager():
    """Create WebSocket manager."""
    return WebSocketManager()


@pytest.fixture
async def streaming_service():
    """Create and start streaming service."""
    service = StreamingService()
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
async def alert_service():
    """Create and start alert service."""
    service = AlertService()
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
def alert_delivery_manager():
    """Create alert delivery manager."""
    return AlertDeliveryManager()


# Connection Manager Tests
class TestConnectionManager:
    """Tests for connection manager."""

    @pytest.mark.asyncio
    async def test_connect_client(self, connection_manager):
        """Test client connection."""
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD)

        assert client_id in connection_manager.active_connections
        connection = connection_manager.active_connections[client_id]
        assert connection.connection_type == ConnectionType.DASHBOARD

    @pytest.mark.asyncio
    async def test_disconnect_client(self, connection_manager):
        """Test client disconnection."""
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD)

        await connection_manager.disconnect(client_id)
        assert client_id not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_subscribe_to_metric(self, connection_manager):
        """Test metric subscription."""
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD)

        success = connection_manager.subscribe_to_metric(client_id, "metric_1")
        assert success
        assert "metric_1" in connection_manager.connections_by_metric
        assert client_id in connection_manager.connections_by_metric["metric_1"]

    @pytest.mark.asyncio
    async def test_broadcast_message(self, connection_manager):
        """Test message broadcast."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        client_id1 = await connection_manager.connect(mock_ws1, ConnectionType.DASHBOARD)
        client_id2 = await connection_manager.connect(mock_ws2, ConnectionType.DASHBOARD)

        message = WSMessage(type=MessageType.KPI_UPDATE, payload={"kpi_id": "1"})
        count = await connection_manager.broadcast(message)

        assert count == 2
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_metric_subscribers(self, connection_manager):
        """Test sending to metric subscribers."""
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD)
        connection_manager.subscribe_to_metric(client_id, "metric_1")

        message = WSMessage(type=MessageType.METRIC_UPDATE, payload={"value": 100})
        count = await connection_manager.send_to_metric_subscribers(message, "metric_1")

        assert count == 1
        mock_ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_stats(self, connection_manager):
        """Test connection statistics."""
        mock_ws = AsyncMock()
        await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD, "user1", "company1")

        stats = connection_manager.get_connection_stats()
        assert stats["total_connections"] == 1
        assert stats["total_users"] == 1
        assert stats["total_companies"] == 1


# WebSocket Manager Tests
class TestWebSocketManager:
    """Tests for WebSocket manager."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, websocket_manager):
        """Test WebSocket statistics."""
        stats = websocket_manager.get_statistics()

        assert "total_connections" in stats
        assert "heartbeat_interval" in stats
        assert "max_message_size" in stats

    @pytest.mark.asyncio
    async def test_broadcast_kpi_update(self, websocket_manager):
        """Test KPI broadcast."""
        mock_ws = AsyncMock()
        connection_manager = websocket_manager.connection_manager

        client_id = await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD)
        connection_manager.subscribe_to_kpi(client_id, "kpi_1")

        count = await websocket_manager.broadcast_kpi_update(
            "kpi_1", {"value": 100, "status": "healthy"}
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_alert(self, websocket_manager):
        """Test alert broadcast."""
        mock_ws = AsyncMock()
        connection_manager = websocket_manager.connection_manager

        client_id = await connection_manager.connect(
            mock_ws, ConnectionType.DASHBOARD, company_id="company_1"
        )

        count = await websocket_manager.broadcast_alert(
            "alert_1",
            {"title": "Test Alert", "severity": "critical"},
            company_id="company_1",
        )

        assert count == 1


# Streaming Service Tests
class TestStreamingService:
    """Tests for streaming service."""

    @pytest.mark.asyncio
    async def test_emit_kpi_update(self, streaming_service):
        """Test KPI update emission."""
        callback = AsyncMock()
        await streaming_service.subscribe(StreamType.KPI, callback)

        await streaming_service.emit_kpi_update(
            "kpi_1", "company_1", {"value": 100, "status": "healthy"}
        )

        await asyncio.sleep(0.5)  # Allow processing
        callback.assert_called()

    @pytest.mark.asyncio
    async def test_emit_metric_update(self, streaming_service):
        """Test metric update emission."""
        callback = AsyncMock()
        await streaming_service.subscribe(StreamType.METRIC, callback)

        await streaming_service.emit_metric_update("metric_1", {"value": 50})

        await asyncio.sleep(0.5)
        callback.assert_called()

    @pytest.mark.asyncio
    async def test_emit_alert(self, streaming_service):
        """Test alert emission."""
        callback = AsyncMock()
        await streaming_service.subscribe(StreamType.ALERT, callback)

        await streaming_service.emit_alert("alert_1", {"title": "Test"})

        await asyncio.sleep(0.5)
        callback.assert_called()

    @pytest.mark.asyncio
    async def test_get_event_history(self, streaming_service):
        """Test event history retrieval."""
        await streaming_service.emit_kpi_update("kpi_1", "company_1", {"value": 100})
        await streaming_service.emit_kpi_update("kpi_2", "company_1", {"value": 200})

        history = await streaming_service.get_event_history(StreamType.KPI, limit=10)
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, streaming_service):
        """Test streaming service statistics."""
        stats = await streaming_service.get_statistics()

        assert stats["is_running"] is True
        assert "subscribers_count" in stats
        assert "buffer_size" in stats


# Alert Service Tests
class TestAlertService:
    """Tests for alert service."""

    @pytest.mark.asyncio
    async def test_create_alert(self, alert_service):
        """Test alert creation."""
        alert_id = await alert_service.create_alert(
            title="Test Alert",
            message="This is a test",
            severity=AlertSeverity.WARNING,
            source="test_source",
            company_id="company_1",
        )

        assert alert_id is not None
        history = await alert_service.get_alert_history("test_source")
        assert len(history) > 0

    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_service):
        """Test alert resolution."""
        alert_id = await alert_service.create_alert(
            title="Test Alert",
            message="This is a test",
            severity=AlertSeverity.WARNING,
            source="test_source",
            company_id="company_1",
        )

        success = await alert_service.resolve_alert(alert_id)
        assert success

    @pytest.mark.asyncio
    async def test_register_alert_rule(self, alert_service):
        """Test alert rule registration."""
        rule = AlertRule(
            rule_id="rule_1",
            name="High CPU",
            description="CPU usage is high",
            condition="cpu_usage > 80",
            severity=AlertSeverity.CRITICAL,
            channels=["websocket", "email"],
        )

        await alert_service.register_rule(rule)
        assert "rule_1" in alert_service.rules

    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alert_service):
        """Test getting active alerts."""
        await alert_service.create_alert(
            title="Critical Alert",
            message="Critical issue",
            severity=AlertSeverity.CRITICAL,
            source="test",
            company_id="company_1",
        )

        active = await alert_service.get_active_alerts("company_1")
        assert len(active) > 0

    @pytest.mark.asyncio
    async def test_alert_statistics(self, alert_service):
        """Test alert service statistics."""
        await alert_service.create_alert(
            title="Test",
            message="Test",
            severity=AlertSeverity.INFO,
            source="test",
            company_id="company_1",
        )

        stats = await alert_service.get_statistics()
        assert "active_alerts" in stats
        assert "queue_size" in stats


# Alert Delivery Tests
class TestAlertDeliveryManager:
    """Tests for alert delivery manager."""

    def test_register_provider(self, alert_delivery_manager):
        """Test provider registration."""
        provider = Mock(spec=EmailDeliveryProvider)
        alert_delivery_manager.register_provider("email", provider)

        assert "email" in alert_delivery_manager.providers

    @pytest.mark.asyncio
    async def test_send_alert(self, alert_delivery_manager):
        """Test alert sending."""
        provider = AsyncMock()
        provider.send = AsyncMock(return_value=True)
        alert_delivery_manager.register_provider("email", provider)

        results = await alert_delivery_manager.send_alert(
            alert_data={"alert_id": "1", "title": "Test"},
            channels=["email"],
            recipients={"email": ["test@example.com"]},
        )

        assert "email" in results

    @pytest.mark.asyncio
    async def test_delivery_statistics(self, alert_delivery_manager):
        """Test delivery statistics."""
        stats = await alert_delivery_manager.get_statistics()

        assert "total_deliveries" in stats
        assert "success_rate" in stats


# Integration tests
@pytest.mark.asyncio
class TestDashboardIntegration:
    """Integration tests for dashboard components."""

    async def test_websocket_to_streaming_pipeline(self, websocket_manager):
        """Test WebSocket to streaming pipeline."""
        mock_ws = AsyncMock()
        connection_manager = websocket_manager.connection_manager

        client_id = await connection_manager.connect(mock_ws, ConnectionType.DASHBOARD)
        connection_manager.subscribe_to_kpi(client_id, "kpi_1")

        # Simulate KPI update
        await websocket_manager.broadcast_kpi_update(
            "kpi_1", {"value": 100, "status": "healthy"}
        )

        mock_ws.send_text.assert_called_once()

    async def test_alert_workflow(self, alert_service, alert_delivery_manager):
        """Test complete alert workflow."""
        # Register delivery provider
        provider = AsyncMock()
        provider.send = AsyncMock(return_value=True)
        alert_delivery_manager.register_provider("websocket", provider)

        # Create alert
        alert_id = await alert_service.create_alert(
            title="Critical Issue",
            message="System down",
            severity=AlertSeverity.CRITICAL,
            source="system",
            company_id="company_1",
        )

        # Get active alerts
        active = await alert_service.get_active_alerts()
        assert len(active) > 0

        # Resolve alert
        await alert_service.resolve_alert(alert_id)
        resolved = await alert_service.get_active_alerts()
        assert len(resolved) == 0

    async def test_multiple_client_broadcast(self, connection_manager):
        """Test broadcast to multiple clients."""
        clients = []

        for i in range(5):
            mock_ws = AsyncMock()
            client_id = await connection_manager.connect(
                mock_ws, ConnectionType.DASHBOARD
            )
            clients.append((client_id, mock_ws))

        message = WSMessage(type=MessageType.BULK_UPDATE, payload={"data": "test"})
        count = await connection_manager.broadcast(message)

        assert count == 5

        for _, mock_ws in clients:
            mock_ws.send_text.assert_called_once()
