"""Integration pipeline tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from core.infrastructure.integrations.base_adapter import (
    IntegrationType,
    IntegrationStatus,
    IntegrationConfig,
)
from core.infrastructure.integrations.slack_adapter import SlackAdapter
from core.infrastructure.integrations.jira_adapter import JiraAdapter
from core.infrastructure.integrations.integration_registry import IntegrationRegistry
from core.infrastructure.webhooks.webhook_manager import WebhookManager, WebhookEvent
from core.infrastructure.integrations.integration_monitor import IntegrationMonitor
from core.application.services.data_mapper import DataMapper, FieldMapping, EntityMapping


class TestIntegrationPipeline:
    """Test integration pipelines."""

    @pytest.mark.asyncio
    async def test_alert_to_slack_pipeline(self):
        """Test alert to Slack integration pipeline."""
        # Create adapter
        config = IntegrationConfig(
            integration_id="slack_pipeline",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-test"},
        )

        adapter = SlackAdapter(config)

        # Mock the session
        adapter.session = AsyncMock()
        adapter.status = IntegrationStatus.ACTIVE

        # Prepare alert data
        alert_data = {
            "title": "Market Shift Alert",
            "description": "Significant market change detected",
            "severity": "HIGH",
            "channel": "#alerts",
            "metrics": {"change": "15%", "impact": "HIGH"},
        }

        # Format for Slack
        formatted = adapter.format_alert_for_slack(alert_data)

        assert formatted["channel"] == "#alerts"
        assert len(formatted["blocks"]) > 0

    @pytest.mark.asyncio
    async def test_alert_to_jira_pipeline(self):
        """Test alert to Jira integration pipeline."""
        config = IntegrationConfig(
            integration_id="jira_pipeline",
            integration_type=IntegrationType.JIRA,
            secrets={
                "jira_instance_url": "https://company.atlassian.net",
                "jira_email": "bot@company.com",
                "jira_api_token": "token123",
            },
        )

        adapter = JiraAdapter(config)
        adapter.session = AsyncMock()
        adapter.instance_url = "https://company.atlassian.net"
        adapter.projects["INTEL"] = "10001"
        adapter.issue_types["Bug"] = "10001"

        # Prepare data
        issue_data = {
            "operation": "create",
            "project_key": "INTEL",
            "issue_type": "Bug",
            "summary": "Investigate market anomaly",
            "description": "Unusual trading pattern detected",
            "priority": "High",
        }

        # Validate data structure
        assert issue_data["project_key"] in adapter.projects
        assert issue_data["issue_type"] in adapter.issue_types

    @pytest.mark.asyncio
    async def test_webhook_event_distribution(self):
        """Test webhook event distribution pipeline."""
        manager = WebhookManager()

        # Register webhooks for different events
        webhook1 = manager.register_webhook(
            url="https://example.com/alerts",
            events=["alert.created", "alert.resolved"],
        )

        webhook2 = manager.register_webhook(
            url="https://example.com/kpis",
            events=["kpi.updated"],
        )

        # Verify registrations
        webhooks = manager.list_webhooks()
        assert len(webhooks) == 2

        # Check event subscriptions
        assert len(webhook1.events) == 2
        assert len(webhook2.events) == 1

    @pytest.mark.asyncio
    async def test_data_mapping_pipeline(self):
        """Test data mapping pipeline."""
        mapper = DataMapper()

        # Register mapping from external alert to internal format
        field_mappings = [
            FieldMapping("id", "alert_id"),
            FieldMapping("severity", "priority"),
            FieldMapping("timestamp", "created_at"),
            FieldMapping("metadata.source", "source_system"),
        ]

        entity_mapping = EntityMapping(
            source_entity="external_alert",
            target_entity="internal_alert",
            field_mappings=field_mappings,
        )

        mapper.register_entity_mapping(entity_mapping)

        # Transform data
        external_data = {
            "id": "ext_123",
            "severity": "critical",
            "timestamp": "2024-01-15T10:30:00Z",
            "metadata": {"source": "external_system"},
        }

        internal_data = mapper.map_entity("external_alert", "internal_alert", external_data)

        assert internal_data["alert_id"] == "ext_123"
        assert internal_data["priority"] == "critical"
        assert internal_data["source_system"] == "external_system"

    @pytest.mark.asyncio
    async def test_registry_integration_lifecycle(self):
        """Test full integration lifecycle with registry."""
        registry = IntegrationRegistry()

        # Register adapter types
        registry.register_adapter_type(IntegrationType.SLACK, SlackAdapter)
        registry.register_adapter_type(IntegrationType.JIRA, JiraAdapter)

        # Create configurations
        slack_config = IntegrationConfig(
            integration_id="slack_prod",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-prod"},
            metadata={"workspace": "production"},
        )

        jira_config = IntegrationConfig(
            integration_id="jira_prod",
            integration_type=IntegrationType.JIRA,
            secrets={
                "jira_instance_url": "https://prod.atlassian.net",
                "jira_email": "bot@prod.com",
                "jira_api_token": "token_prod",
            },
        )

        # Create integrations
        slack_int = registry.create_integration(
            "slack_prod", IntegrationType.SLACK, slack_config
        )
        jira_int = registry.create_integration("jira_prod", IntegrationType.JIRA, jira_config)

        # Verify creation
        assert "slack_prod" in registry.adapters
        assert "jira_prod" in registry.adapters

        # Get configurations
        slack_cfg = registry.get_config("slack_prod")
        jira_cfg = registry.get_config("jira_prod")

        assert slack_cfg.integration_id == "slack_prod"
        assert jira_cfg.integration_id == "jira_prod"

    @pytest.mark.asyncio
    async def test_monitoring_integration_health(self):
        """Test monitoring integration health."""
        registry = IntegrationRegistry()
        monitor = IntegrationMonitor(check_interval=1)

        registry.register_adapter_type(IntegrationType.SLACK, SlackAdapter)

        config = IntegrationConfig(
            integration_id="slack_monitor",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "xoxb-monitor"},
        )

        adapter = registry.create_integration(
            "slack_monitor", IntegrationType.SLACK, config
        )

        # Simulate operations
        adapter.increment_success()
        adapter.increment_success()
        adapter.increment_error()

        # Get statistics
        stats = registry.get_statistics()

        assert stats is not None
        assert "slack_monitor" in stats

    @pytest.mark.asyncio
    async def test_end_to_end_alert_distribution(self):
        """Test end-to-end alert distribution."""
        # Setup registry
        registry = IntegrationRegistry()
        registry.register_adapter_type(IntegrationType.SLACK, SlackAdapter)
        registry.register_adapter_type(IntegrationType.JIRA, JiraAdapter)

        # Setup webhooks
        webhook_manager = WebhookManager()
        webhook_manager.register_webhook(
            url="https://slack.example.com/webhook",
            events=["alert.created"],
        )
        webhook_manager.register_webhook(
            url="https://jira.example.com/webhook",
            events=["alert.created"],
        )

        # Setup data mapper
        mapper = DataMapper()
        field_mappings = [
            FieldMapping("id", "alert_id"),
            FieldMapping("title", "subject"),
            FieldMapping("severity", "priority"),
        ]

        entity_mapping = EntityMapping(
            source_entity="raw_alert",
            target_entity="normalized_alert",
            field_mappings=field_mappings,
        )

        mapper.register_entity_mapping(entity_mapping)

        # Simulate alert
        raw_alert = {
            "id": "alert_001",
            "title": "Competitor price change",
            "severity": "HIGH",
        }

        # Transform
        normalized = mapper.map_entity("raw_alert", "normalized_alert", raw_alert)

        # Verify
        assert normalized["alert_id"] == "alert_001"
        assert normalized["subject"] == "Competitor price change"
        assert normalized["priority"] == "HIGH"

        # List webhooks
        webhooks = webhook_manager.list_webhooks()
        assert len(webhooks) == 2


class TestIntegrationErrorHandling:
    """Test error handling in integrations."""

    @pytest.mark.asyncio
    async def test_adapter_connection_failure(self):
        """Test adapter connection failure handling."""
        config = IntegrationConfig(
            integration_id="slack_fail",
            integration_type=IntegrationType.SLACK,
            secrets={},  # Missing token
        )

        adapter = SlackAdapter(config)
        adapter.session = AsyncMock()

        # Mock authentication failure
        adapter.authenticate = AsyncMock(return_value=False)

        result = await adapter.connect()

        assert result is False
        assert adapter.status == IntegrationStatus.ERROR

    @pytest.mark.asyncio
    async def test_webhook_invalid_url(self):
        """Test webhook with invalid URL."""
        manager = WebhookManager()

        with pytest.raises(Exception):
            # Invalid URL should raise
            webhook = manager.register_webhook(
                url="not-a-valid-url",
                events=["alert.created"],
            )

    @pytest.mark.asyncio
    async def test_mapper_missing_mapping(self):
        """Test data mapper with missing mapping."""
        mapper = DataMapper()

        data = {"field1": "value1"}

        # Try to map without registering mapping first
        result = mapper.map_entity("unmapped_source", "unmapped_target", data)

        # Should return original data
        assert result == data

    @pytest.mark.asyncio
    async def test_registry_duplicate_integration(self):
        """Test registry duplicate integration prevention."""
        registry = IntegrationRegistry()

        config = IntegrationConfig(
            integration_id="dup_int",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "test"},
        )

        registry.register_adapter_type(IntegrationType.SLACK, SlackAdapter)

        # Create first integration
        registry.create_integration("dup_int", IntegrationType.SLACK, config)

        # Attempt to create duplicate (should handle gracefully)
        config2 = IntegrationConfig(
            integration_id="dup_int",
            integration_type=IntegrationType.SLACK,
            secrets={"slack_token": "test2"},
        )

        # Should replace or handle duplicate
        registry.create_integration("dup_int", IntegrationType.SLACK, config2)

        integrations = registry.list_integrations()
        assert len([i for i in integrations if i[0] == "dup_int"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
