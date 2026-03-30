"""Integration framework for third-party systems."""

from .base_adapter import (
    BaseIntegrationAdapter,
    IntegrationConfig,
    IntegrationStatus,
    IntegrationType,
)
from .integration_registry import IntegrationRegistry, get_integration_registry

__all__ = [
    "BaseIntegrationAdapter",
    "IntegrationConfig",
    "IntegrationStatus",
    "IntegrationType",
    "IntegrationRegistry",
    "get_integration_registry",
]
