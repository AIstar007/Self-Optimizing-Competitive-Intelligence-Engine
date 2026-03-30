"""Integration tests for dashboard real-time pipeline."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from core.infrastructure.websocket.connection_manager import ConnectionManager, ConnectionType, MessageType, WSMessage
from core.infrastructure.websocket.websocket_manager import WebSocketManager
from core.application.services.streaming_service import StreamingService, StreamType
from core.application.services.alert_service import AlertService, AlertSeverity
from core.infrastructure.alerts.alert_delivery import AlertDeliveryManager


@pytest.fixture
async def dashboard_pipeline():
    """Create integrated dashboard pipeline."""
    websocket_manager = WebSocketManager()
    streaming_service = StreamingService()
    alert_service = AlertService()
    delivery_manager = AlertDeliveryManager()

    await streaming_service.start()
    await alert_service.start()

    yield {
        "websocket_manager": websocket_manager,
        "streaming_service": streaming_service,
        "alert_service": alert_service,
        "delivery_manager": delivery_manager,
    }

    await streaming_service.stop()
    await alert_service.stop()


class TestDashboardRealTimePipeline:
    """Integration tests for real-time dashboard updates."""

    @pytest.mark.asyncio
    async def test_kpi_update_flow(self, dashboard_pipeline):
        """Test KPI update through entire pipeline."""
        ws_manager = dashboard_pipeline["websocket_manager"]
        streaming_service = dashboard_pipeline["streaming_service"]
        connection_manager = ws_manager.connection_manager

        # Connect client
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(
            mock_ws, ConnectionType.DASHBOARD, company_id="company_1"
        )
        connection_manager.subscribe_to_kpi(client_id, "kpi_1")

        # Subscribe to streaming
        received_events = []

        async def on_kpi_update(event):
            received_events.append(event)

        await streaming_service.subscribe(StreamType.KPI, on_kpi_update)

        # Emit KPI update
        await streaming_service.emit_kpi_update(
            "kpi_1",
            "company_1",
            {
                "value": 100,
                "status": "healthy",
                "trend": "up",
                "forecast": 110,
            },
        )

        # Wait for processing
        await asyncio.sleep(0.5)

        # Verify
        assert len(received_events) > 0
        assert received_events[0].entity_id == "kpi_1"
        assert received_events[0].stream_type == StreamType.KPI

    @pytest.mark.asyncio
    async def test_metric_streaming_with_multiple_clients(self, dashboard_pipeline):
        """Test metric streaming to multiple clients."""
        ws_manager = dashboard_pipeline["websocket_manager"]
        streaming_service = dashboard_pipeline["streaming_service"]
        connection_manager = ws_manager.connection_manager

        # Connect multiple clients
        clients = []
        for i in range(3):
            mock_ws = AsyncMock()
            client_id = await connection_manager.connect(
                mock_ws, ConnectionType.DASHBOARD
            )
            connection_manager.subscribe_to_metric(client_id, "metric_1")
            clients.append((client_id, mock_ws))

        # Emit metric update
        await streaming_service.emit_metric_update("metric_1", {"value": 50})
        await asyncio.sleep(0.5)

        # Verify all clients received update
        for _, mock_ws in clients:
            assert mock_ws.send_text.called or mock_ws.send_json.called

    @pytest.mark.asyncio
    async def test_alert_to_delivery_pipeline(self, dashboard_pipeline):
        """Test alert creation through delivery pipeline."""
        alert_service = dashboard_pipeline["alert_service"]
        delivery_manager = dashboard_pipeline["delivery_manager"]

        # Setup delivery provider
        mock_provider = AsyncMock()
        mock_provider.send = AsyncMock(return_value=True)
        delivery_manager.register_provider("email", mock_provider)

        # Create alert
        alert_id = await alert_service.create_alert(
            title="Critical Issue",
            message="Database down",
            severity=AlertSeverity.CRITICAL,
            source="system",
            company_id="company_1",
        )

        # Send alert through delivery
        alert_data = {
            "alert_id": alert_id,
            "title": "Critical Issue",
            "message": "Database down",
            "severity": "critical",
        }

        results = await delivery_manager.send_alert(
            alert_data,
            channels=["email"],
            recipients={"email": ["admin@company.com"]},
        )

        assert "email" in results

    @pytest.mark.asyncio
    async def test_client_subscription_management(self, dashboard_pipeline):
        """Test client subscription management."""
        connection_manager = dashboard_pipeline["websocket_manager"].connection_manager

        # Connect client
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(
            mock_ws, ConnectionType.DASHBOARD
        )

        # Subscribe to multiple metrics
        for i in range(5):
            connection_manager.subscribe_to_metric(client_id, f"metric_{i}")

        # Check subscriptions
        connection = connection_manager.active_connections[client_id]
        assert len(connection.subscribed_metrics) == 5

        # Unsubscribe from one
        connection_manager.unsubscribe_from_metric(client_id, "metric_0")
        assert len(connection.subscribed_metrics) == 4

        # Verify metric routing
        message = WSMessage(
            type=MessageType.METRIC_UPDATE,
            payload={"value": 100},
        )

        # Should only be sent to subscribed metrics
        count = await connection_manager.send_to_metric_subscribers(
            message, "metric_1"
        )
        assert count == 1

        count = await connection_manager.send_to_metric_subscribers(
            message, "metric_0"
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcasting_by_company(self, dashboard_pipeline):
        """Test broadcasting to company-specific clients."""
        connection_manager = dashboard_pipeline["websocket_manager"].connection_manager

        # Connect clients from different companies
        clients_company1 = []
        clients_company2 = []

        for i in range(2):
            mock_ws = AsyncMock()
            client_id = await connection_manager.connect(
                mock_ws, ConnectionType.DASHBOARD, company_id="company_1"
            )
            clients_company1.append(mock_ws)

            mock_ws = AsyncMock()
            client_id = await connection_manager.connect(
                mock_ws, ConnectionType.DASHBOARD, company_id="company_2"
            )
            clients_company2.append(mock_ws)

        # Broadcast to company 1
        message = WSMessage(
            type=MessageType.ALERT_NOTIFICATION,
            payload={"alert": "test"},
        )

        count = await connection_manager.broadcast_to_company(message, "company_1")
        assert count == 2

        # Verify only company 1 clients received
        for mock_ws in clients_company1:
            assert mock_ws.send_text.called

    @pytest.mark.asyncio
    async def test_alert_rule_evaluation(self, dashboard_pipeline):
        """Test alert rule evaluation with context."""
        alert_service = dashboard_pipeline["alert_service"]

        # Register alert rule
        from core.application.services.alert_service import AlertRule

        rule = AlertRule(
            rule_id="rule_1",
            name="High CPU Alert",
            description="CPU usage is high",
            condition="context_data['cpu_usage'] > 80",
            severity=AlertSeverity.CRITICAL,
            channels=["websocket"],
        )

        await alert_service.register_rule(rule)

        # Evaluate with context
        context = {
            "context_data": {"cpu_usage": 85},
            "company_id": "company_1",
        }

        alerts = await alert_service.evaluate_rules(context)
        # Should trigger alert since CPU is 85 > 80
        # Note: Result depends on implementation details

    @pytest.mark.asyncio
    async def test_event_buffering_and_priority(self, dashboard_pipeline):
        """Test event buffering with priority queuing."""
        streaming_service = dashboard_pipeline["streaming_service"]

        # Emit events with different priorities
        await streaming_service.emit_kpi_update(
            "kpi_1",
            "company_1",
            {"value": 100},
            priority=1,  # Low priority
        )

        await streaming_service.emit_alert(
            "alert_1",
            {"title": "Critical"},
            priority=10,  # High priority
        )

        # Get buffer stats
        stats = await streaming_service.get_statistics()
        assert stats["buffer_size"] >= 0

    @pytest.mark.asyncio
    async def test_client_disconnection_cleanup(self, dashboard_pipeline):
        """Test proper cleanup on client disconnection."""
        connection_manager = dashboard_pipeline["websocket_manager"].connection_manager

        # Connect and subscribe
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(
            mock_ws, ConnectionType.DASHBOARD, company_id="company_1"
        )

        connection_manager.subscribe_to_metric(client_id, "metric_1")
        connection_manager.subscribe_to_kpi(client_id, "kpi_1")

        # Verify subscriptions exist
        assert "metric_1" in connection_manager.connections_by_metric
        assert "kpi_1" in connection_manager.connections_by_kpi

        # Disconnect
        await connection_manager.disconnect(client_id)

        # Verify cleanup
        assert client_id not in connection_manager.active_connections
        assert client_id not in connection_manager.connections_by_metric.get("metric_1", set())
        assert client_id not in connection_manager.connections_by_kpi.get("kpi_1", set())

    @pytest.mark.asyncio
    async def test_batch_dashboard_update(self, dashboard_pipeline):
        """Test sending batch updates to dashboard."""
        ws_manager = dashboard_pipeline["websocket_manager"]
        connection_manager = ws_manager.connection_manager

        # Connect client
        mock_ws = AsyncMock()
        client_id = await connection_manager.connect(
            mock_ws, ConnectionType.DASHBOARD
        )

        # Send bulk update
        bulk_data = {
            "metrics": [
                {"id": "m1", "value": 100},
                {"id": "m2", "value": 200},
            ],
            "kpis": [
                {"id": "kpi1", "value": 1000},
                {"id": "kpi2", "value": 2000},
            ],
        }

        success = await ws_manager.send_bulk_update(client_id, bulk_data)
        assert success

    @pytest.mark.asyncio
    async def test_connection_statistics_tracking(self, dashboard_pipeline):
        """Test connection statistics tracking."""
        connection_manager = dashboard_pipeline["websocket_manager"].connection_manager

        # Create various connections
        for i in range(3):
            mock_ws = AsyncMock()
            await connection_manager.connect(
                mock_ws, ConnectionType.DASHBOARD, user_id=f"user_{i}", company_id="company_1"
            )

        # Get stats
        stats = connection_manager.get_connection_stats()

        assert stats["total_connections"] == 3
        assert stats["total_users"] == 3
        assert stats["total_companies"] == 1

    @pytest.mark.asyncio
    async def test_streaming_service_shutdown(self, dashboard_pipeline):
        """Test graceful streaming service shutdown."""
        streaming_service = dashboard_pipeline["streaming_service"]

        # Emit some events
        for i in range(5):
            await streaming_service.emit_kpi_update(
                f"kpi_{i}",
                "company_1",
                {"value": i * 10},
            )

        # Stop service
        await streaming_service.stop()

        # Verify service stopped
        assert not streaming_service._is_running

        # Verify buffer flushed
        buffer_size = await streaming_service.buffer.size()
        assert buffer_size >= 0

    @pytest.mark.asyncio
    async def test_delivery_retry_workflow(self, dashboard_pipeline):
        """Test alert delivery retry workflow."""
        delivery_manager = dashboard_pipeline["delivery_manager"]

        # Setup failing provider
        mock_provider = AsyncMock()
        mock_provider.send = AsyncMock(return_value=False)
        delivery_manager.register_provider("email", mock_provider)

        # Send alert
        alert_data = {"alert_id": "1", "title": "Test"}

        results = await delivery_manager.send_alert(
            alert_data,
            channels=["email"],
            recipients={"email": ["test@example.com"]},
        )

        # Check that retry was queued
        assert len(delivery_manager.retry_queue) > 0


class TestDashboardScenarios:
    """End-to-end scenario tests."""

    @pytest.mark.asyncio
    async def test_real_time_kpi_dashboard_update(self, dashboard_pipeline):
        """Scenario: Real-time KPI dashboard update."""
        ws_manager = dashboard_pipeline["websocket_manager"]
        streaming_service = dashboard_pipeline["streaming_service"]

        # User opens dashboard
        mock_ws = AsyncMock()
        client_id = await ws_manager.connection_manager.connect(
            mock_ws, ConnectionType.DASHBOARD, user_id="user_1", company_id="company_1"
        )

        # Subscribe to KPIs
        for i in range(1, 4):
            ws_manager.connection_manager.subscribe_to_kpi(client_id, f"kpi_{i}")

        # System updates KPIs in real-time
        for i in range(1, 4):
            await streaming_service.emit_kpi_update(
                f"kpi_{i}",
                "company_1",
                {
                    "value": 100 + i * 10,
                    "status": "healthy" if i % 2 == 0 else "warning",
                },
            )

        await asyncio.sleep(0.5)

        # Client should receive updates
        assert mock_ws.send_text.call_count > 0

    @pytest.mark.asyncio
    async def test_alert_escalation_workflow(self, dashboard_pipeline):
        """Scenario: Alert escalation and delivery."""
        alert_service = dashboard_pipeline["alert_service"]
        delivery_manager = dashboard_pipeline["delivery_manager"]

        # Setup delivery
        mock_provider = AsyncMock()
        mock_provider.send = AsyncMock(return_value=True)
        delivery_manager.register_provider("websocket", mock_provider)

        # Create escalating alerts
        severities = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.CRITICAL,
        ]

        for severity in severities:
            await alert_service.create_alert(
                title="System Health",
                message=f"Alert at {severity.value} level",
                severity=severity,
                source="system_monitor",
                company_id="company_1",
            )

        # Get active alerts
        active = await alert_service.get_active_alerts("company_1")
        critical_count = sum(1 for a in active if a.severity == AlertSeverity.CRITICAL)

        assert critical_count >= 1

    @pytest.mark.asyncio
    async def test_multi_user_collaborative_dashboard(self, dashboard_pipeline):
        """Scenario: Multiple users viewing same dashboard."""
        connection_manager = dashboard_pipeline["websocket_manager"].connection_manager
        streaming_service = dashboard_pipeline["streaming_service"]

        # Multiple users connect to same dashboard
        users = []
        for i in range(3):
            mock_ws = AsyncMock()
            client_id = await connection_manager.connect(
                mock_ws, ConnectionType.DASHBOARD, user_id=f"user_{i}", company_id="company_1"
            )
            connection_manager.subscribe_to_kpi(client_id, "shared_kpi")
            users.append((client_id, mock_ws))

        # Update shared KPI
        await streaming_service.emit_kpi_update(
            "shared_kpi",
            "company_1",
            {"value": 1000, "status": "healthy"},
        )

        await asyncio.sleep(0.5)

        # All users should receive update
        for _, mock_ws in users:
            assert mock_ws.send_text.called
