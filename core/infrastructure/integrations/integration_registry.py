"""Integration registry for managing multiple integrations."""

import logging
from typing import Dict, List, Optional, Type
from datetime import datetime

from .base_adapter import (
    BaseIntegrationAdapter,
    IntegrationConfig,
    IntegrationStatus,
    IntegrationType,
)

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """Registry for managing integration adapters."""

    def __init__(self):
        """Initialize registry."""
        self.adapters: Dict[str, BaseIntegrationAdapter] = {}
        self.adapter_types: Dict[IntegrationType, Type[BaseIntegrationAdapter]] = {}
        self.configs: Dict[str, IntegrationConfig] = {}

    def register_adapter_type(
        self,
        integration_type: IntegrationType,
        adapter_class: Type[BaseIntegrationAdapter],
    ) -> None:
        """Register adapter type."""
        self.adapter_types[integration_type] = adapter_class
        logger.info(f"Registered adapter type: {integration_type.value}")

    async def create_integration(self, config: IntegrationConfig) -> bool:
        """Create and initialize integration."""
        try:
            if config.integration_type not in self.adapter_types:
                logger.error(f"Unknown integration type: {config.integration_type.value}")
                return False

            adapter_class = self.adapter_types[config.integration_type]
            adapter = adapter_class(config)

            # Test connection
            if not await adapter.test_connection():
                logger.warning(f"Failed to connect to integration: {config.name}")
                return False

            self.adapters[config.integration_id] = adapter
            self.configs[config.integration_id] = config

            logger.info(f"Integration created: {config.name}")
            return True

        except Exception as e:
            logger.error(f"Error creating integration: {e}")
            return False

    async def activate_integration(self, integration_id: str) -> bool:
        """Activate an integration."""
        if integration_id not in self.adapters:
            logger.error(f"Integration not found: {integration_id}")
            return False

        adapter = self.adapters[integration_id]

        try:
            if await adapter.connect() and await adapter.authenticate():
                adapter.status = IntegrationStatus.ACTIVE
                self.configs[integration_id].is_active = True
                logger.info(f"Integration activated: {adapter.config.name}")
                return True
            else:
                adapter.status = IntegrationStatus.ERROR
                return False
        except Exception as e:
            logger.error(f"Error activating integration: {e}")
            adapter.status = IntegrationStatus.ERROR
            return False

    async def deactivate_integration(self, integration_id: str) -> bool:
        """Deactivate an integration."""
        if integration_id not in self.adapters:
            logger.error(f"Integration not found: {integration_id}")
            return False

        adapter = self.adapters[integration_id]

        try:
            await adapter.disconnect()
            adapter.status = IntegrationStatus.INACTIVE
            self.configs[integration_id].is_active = False
            logger.info(f"Integration deactivated: {adapter.config.name}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating integration: {e}")
            return False

    async def remove_integration(self, integration_id: str) -> bool:
        """Remove an integration."""
        if integration_id not in self.adapters:
            logger.error(f"Integration not found: {integration_id}")
            return False

        try:
            adapter = self.adapters[integration_id]
            await adapter.disconnect()

            del self.adapters[integration_id]
            del self.configs[integration_id]

            logger.info(f"Integration removed: {integration_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing integration: {e}")
            return False

    def get_integration(self, integration_id: str) -> Optional[BaseIntegrationAdapter]:
        """Get integration adapter."""
        return self.adapters.get(integration_id)

    def get_config(self, integration_id: str) -> Optional[IntegrationConfig]:
        """Get integration configuration."""
        return self.configs.get(integration_id)

    def list_integrations(self) -> List[Dict]:
        """List all integrations."""
        return [adapter.get_status() for adapter in self.adapters.values()]

    def list_integrations_by_type(self, integration_type: IntegrationType) -> List[Dict]:
        """List integrations by type."""
        return [
            adapter.get_status()
            for adapter in self.adapters.values()
            if adapter.config.integration_type == integration_type
        ]

    def get_active_integrations(self) -> List[BaseIntegrationAdapter]:
        """Get all active integrations."""
        return [
            adapter
            for adapter in self.adapters.values()
            if adapter.status == IntegrationStatus.ACTIVE
        ]

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all integrations."""
        results = {}

        for integration_id, adapter in self.adapters.items():
            try:
                is_healthy = await adapter.health_check()
                results[integration_id] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {integration_id}: {e}")
                results[integration_id] = False

        return results

    async def sync_all(self) -> Dict[str, bool]:
        """Sync all active integrations."""
        results = {}

        for adapter in self.get_active_integrations():
            try:
                success = await adapter.sync()
                results[adapter.config.integration_id] = success
            except Exception as e:
                logger.error(f"Sync failed for {adapter.config.name}: {e}")
                results[adapter.config.integration_id] = False

        return results

    def get_statistics(self) -> Dict:
        """Get registry statistics."""
        total_integrations = len(self.adapters)
        active = sum(1 for a in self.adapters.values() if a.status == IntegrationStatus.ACTIVE)
        inactive = sum(1 for a in self.adapters.values() if a.status == IntegrationStatus.INACTIVE)
        error = sum(1 for a in self.adapters.values() if a.status == IntegrationStatus.ERROR)

        stats_by_type = {}
        for adapter in self.adapters.values():
            integration_type = adapter.config.integration_type.value
            if integration_type not in stats_by_type:
                stats_by_type[integration_type] = []
            stats_by_type[integration_type].append(adapter.get_stats())

        return {
            "total_integrations": total_integrations,
            "active": active,
            "inactive": inactive,
            "error": error,
            "stats_by_type": stats_by_type,
        }


# Global registry instance
_registry: Optional[IntegrationRegistry] = None


def get_integration_registry() -> IntegrationRegistry:
    """Get or create global integration registry."""
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry()
    return _registry
