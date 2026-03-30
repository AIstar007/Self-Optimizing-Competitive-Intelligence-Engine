"""Tests for integrations framework."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from core.infrastructure.integrations.base_adapter import (
    BaseIntegrationAdapter,
    IntegrationType,
    IntegrationStatus,
    IntegrationConfig,
    IntegrationEvent,
)
from core.infrastructure.integrations.integration_registry import IntegrationRegistry
from core.infrastructure.integrations.slack_adapter import SlackAdapter
from core.infrastructure.integrations.jira_adapter import JiraAdapter
from core.infrastructure.integrations.servicenow_adapter import ServiceNowAdapter
from core.infrastructure.webhooks.webhook_manager import (
    WebhookManager,
    WebhookEvent,
    Webhook,
)
from core.infrastructure.integrations.integration_monitor import IntegrationMonitor
from core.application.services.data_mapper import DataMapper, FieldMapping, EntityMapping


class TestIntegrationConfig:
    """Test IntegrationConfig."""

    def test_integration_config_creation(self):
        """Test creating integration config."""
        config = IntegrationConfig(
            integration_id="test_id",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-test"},
            metadata={"workspace": "test"},
        )

        assert config.integration_id == "test_id"
        assert config.integration_type == IntegrationType.SLACK
        assert config.get_secret("slack_token") == "xoxb-test"

    def test_config_secret_management(self):
        """Test secret management."""
        config = IntegrationConfig(
            integration_id="test_id",
            integration_type=IntegrationType.SLACK,
            secrets={"api_key": "secret123"},
        )

        assert config.get_secret("api_key") == "secret123"
        assert config.get_secret("nonexistent") is None


class TestBaseIntegrationAdapter:
    """Test BaseIntegrationAdapter."""

    def test_adapter_status_tracking(self):
        """Test adapter status tracking."""
        config = IntegrationConfig(
            integration_id="test",
            integration_type=IntegrationType.SLACK,
        )

        adapter = SlackAdapter(config)

        assert adapter.status == IntegrationStatus.DISCONNECTED
        adapter.increment_success()
        assert adapter.get_stats()["success_count"] == 1

    def test_adapter_event_handler(self):
        """Test adapter event handler."""
        config = IntegrationConfig(
            integration_id="test",
            integration_type=IntegrationType.SLACK,
        )

        adapter = SlackAdapter(config)

        events_received = []

        def handler(event: IntegrationEvent):
            events_received.append(event)

        adapter.subscribe(handler)
        adapter.increment_success()

        # Events would be published on certain operations
        assert len(adapter.handlers) == 1


class TestIntegrationRegistry:
    """Test IntegrationRegistry."""

    def test_registry_creation(self):
        """Test registry creation."""
        registry = IntegrationRegistry()
        assert registry is not None

    def test_register_adapter_type(self):
        """Test registering adapter type."""
        registry = IntegrationRegistry()

        registry.register_adapter_type(IntegrationType.SLACK, SlackAdapter)

        assert IntegrationType.SLACK in registry.adapter_types

    def test_integration_lifecycle(self):
        """Test integration lifecycle."""
        registry = IntegrationRegistry()

        config = IntegrationConfig(
            integration_id="test_slack",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-test"},
        )

        registry.register_adapter_type(IntegrationType.SLACK, SlackAdapter)

        integration = registry.create_integration("test_slack", IntegrationType.SLACK, config)

        assert integration is not None
        assert "test_slack" in registry.adapters


class TestWebhookManager:
    """Test WebhookManager."""

    @pytest.mark.asyncio
    async def test_webhook_registration(self):
        """Test webhook registration."""
        manager = WebhookManager()

        webhook = manager.register_webhook(
            url="https://example.com/webhook",
            events=["alert.created"],
        )

        assert webhook is not None
        assert webhook.url == "https://example.com/webhook"
        assert webhook.active is True

    @pytest.mark.asyncio
    async def test_webhook_list(self):
        """Test listing webhooks."""
        manager = WebhookManager()

        manager.register_webhook(
            url="https://example.com/webhook1",
            events=["alert.created"],
        )
        manager.register_webhook(
            url="https://example.com/webhook2",
            events=["kpi.updated"],
        )

        webhooks = manager.list_webhooks()
        assert len(webhooks) == 2

    @pytest.mark.asyncio
    async def test_webhook_update(self):
        """Test updating webhook."""
        manager = WebhookManager()

        webhook = manager.register_webhook(
            url="https://example.com/webhook",
            events=["alert.created"],
        )

        updated = manager.update_webhook(
            webhook.id,
            url="https://example.com/webhook-updated",
            active=False,
        )

        assert updated.url == "https://example.com/webhook-updated"
        assert updated.active is False

    @pytest.mark.asyncio
    async def test_webhook_delete(self):
        """Test deleting webhook."""
        manager = WebhookManager()

        webhook = manager.register_webhook(
            url="https://example.com/webhook",
            events=["alert.created"],
        )

        success = manager.delete_webhook(webhook.id)
        assert success is True

        retrieved = manager.get_webhook(webhook.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_webhook_stats(self):
        """Test webhook statistics."""
        manager = WebhookManager()

        webhook = manager.register_webhook(
            url="https://example.com/webhook",
            events=["alert.created"],
        )

        stats = manager.get_webhook_stats(webhook.id)

        assert stats is not None
        assert stats["total_deliveries"] >= 0
        assert stats["success_rate"] >= 0


class TestDataMapper:
    """Test DataMapper."""

    def test_field_mapping_creation(self):
        """Test creating field mapping."""
        mapping = FieldMapping(
            source_field="slack_channel",
            target_field="channel_id",
            required=True,
        )

        assert mapping.source_field == "slack_channel"
        assert mapping.target_field == "channel_id"

    def test_entity_mapping_creation(self):
        """Test creating entity mapping."""
        field_mapping = FieldMapping(
            source_field="id",
            target_field="alert_id",
        )

        entity_mapping = EntityMapping(
            source_entity="external_alert",
            target_entity="internal_alert",
            field_mappings=[field_mapping],
        )

        assert entity_mapping.source_entity == "external_alert"
        assert len(entity_mapping.field_mappings) == 1

    def test_data_mapper_simple_mapping(self):
        """Test simple data mapping."""
        mapper = DataMapper()

        field_mapping = FieldMapping(
            source_field="title",
            target_field="name",
        )

        entity_mapping = EntityMapping(
            source_entity="source",
            target_entity="target",
            field_mappings=[field_mapping],
        )

        mapper.register_entity_mapping(entity_mapping)

        data = {"title": "Test Alert"}
        result = mapper.map_entity("source", "target", data)

        assert result["name"] == "Test Alert"

    def test_data_mapper_with_transformer(self):
        """Test mapping with field transformer."""
        mapper = DataMapper()

        def uppercase_transformer(value):
            return value.upper() if isinstance(value, str) else value

        field_mapping = FieldMapping(
            source_field="title",
            target_field="name",
            transformer=uppercase_transformer,
        )

        entity_mapping = EntityMapping(
            source_entity="source",
            target_entity="target",
            field_mappings=[field_mapping],
        )

        mapper.register_entity_mapping(entity_mapping)

        data = {"title": "test alert"}
        result = mapper.map_entity("source", "target", data)

        assert result["name"] == "TEST ALERT"

    def test_data_mapper_nested_fields(self):
        """Test mapping nested fields."""
        mapper = DataMapper()

        field_mapping = FieldMapping(
            source_field="data.severity",
            target_field="alert.priority",
        )

        entity_mapping = EntityMapping(
            source_entity="source",
            target_entity="target",
            field_mappings=[field_mapping],
        )

        mapper.register_entity_mapping(entity_mapping)

        data = {"data": {"severity": "high"}}
        result = mapper.map_entity("source", "target", data)

        assert result["alert"]["priority"] == "high"


class TestIntegrationMonitor:
    """Test IntegrationMonitor."""

    @pytest.mark.asyncio
    async def test_monitor_creation(self):
        """Test monitor creation."""
        monitor = IntegrationMonitor()
        assert monitor is not None

    @pytest.mark.asyncio
    async def test_health_status_creation(self):
        """Test health status creation."""
        from core.infrastructure.integrations.integration_monitor import IntegrationHealthStatus

        status = IntegrationHealthStatus(
            integration_id="test",
            status="HEALTHY",
            last_check=datetime.utcnow(),
            success_count=100,
            error_count=5,
            error_rate=5.0,
            uptime_percentage=95.0,
        )

        assert status.integration_id == "test"
        assert status.status == "HEALTHY"

    @pytest.mark.asyncio
    async def test_monitor_alerts(self):
        """Test monitor alerts."""
        monitor = IntegrationMonitor()

        alert = {
            "integration_id": "test",
            "alert_type": "HEALTH_DEGRADATION",
            "timestamp": datetime.utcnow(),
            "error_rate": 50.0,
        }

        monitor.alerts.append(alert)

        alerts = monitor.get_alerts(limit=10)
        assert len(alerts) == 1
        assert alerts[0]["integration_id"] == "test"


class TestSlackAdapter:
    """Test Slack adapter."""

    def test_slack_adapter_creation(self):
        """Test creating Slack adapter."""
        config = IntegrationConfig(
            integration_id="slack_test",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-test"},
        )

        adapter = SlackAdapter(config)
        assert adapter is not None
        assert adapter.config.integration_id == "slack_test"

    @pytest.mark.asyncio
    async def test_slack_alert_formatting(self):
        """Test Slack alert formatting."""
        config = IntegrationConfig(
            integration_id="slack_test",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-test"},
        )

        adapter = SlackAdapter(config)

        alert_data = {
            "title": "High CPU Alert",
            "description": "CPU usage exceeded 80%",
            "severity": "HIGH",
            "channel": "#alerts",
            "metrics": {"cpu": "85%", "memory": "72%"},
        }

        formatted = adapter.format_alert_for_slack(alert_data)

        assert formatted["text"] == "High CPU Alert"
        assert formatted["channel"] == "#alerts"
        assert len(formatted["blocks"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
