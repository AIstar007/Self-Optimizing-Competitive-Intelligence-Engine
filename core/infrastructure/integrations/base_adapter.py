"""Base adapter for third-party integrations."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Types of integrations."""

    SLACK = "slack"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    GITHUB = "github"
    ZAPIER = "zapier"
    CUSTOM_WEBHOOK = "custom_webhook"


class IntegrationStatus(str, Enum):
    """Integration status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"


@dataclass
class IntegrationConfig:
    """Integration configuration."""

    integration_id: str
    integration_type: IntegrationType
    name: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    workspace_id: Optional[str] = None
    additional_config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (exclude secrets)."""
        return {
            "integration_id": self.integration_id,
            "integration_type": self.integration_type.value,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class IntegrationEvent:
    """Integration event for tracking."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    integration_id: str = ""
    event_type: str = ""  # sent, received, error, sync, etc.
    direction: str = ""  # inbound, outbound
    payload: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, success, failed, retry
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    retry_until: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "integration_id": self.integration_id,
            "event_type": self.event_type,
            "direction": self.direction,
            "payload": self.payload,
            "response": self.response,
            "status": self.status,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
        }


class BaseIntegrationAdapter(ABC):
    """Base class for integration adapters."""

    def __init__(self, config: IntegrationConfig):
        """Initialize adapter."""
        self.config = config
        self.status = IntegrationStatus.INACTIVE
        self.last_sync: Optional[datetime] = None
        self.error_count = 0
        self.success_count = 0
        self.total_events = 0

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to external service."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from external service."""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with external service."""
        pass

    @abstractmethod
    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to external service."""
        pass

    @abstractmethod
    async def receive_data(self) -> Dict[str, Any]:
        """Receive data from external service."""
        pass

    @abstractmethod
    async def sync(self) -> bool:
        """Sync data with external service."""
        pass

    async def health_check(self) -> bool:
        """Check if integration is healthy."""
        try:
            # Try a simple operation to verify connection
            is_healthy = await self.authenticate()
            if is_healthy:
                self.status = IntegrationStatus.ACTIVE
            else:
                self.status = IntegrationStatus.ERROR
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {self.config.name}: {e}")
            self.status = IntegrationStatus.ERROR
            return False

    async def test_connection(self) -> bool:
        """Test connection to external service."""
        try:
            logger.info(f"Testing connection to {self.config.name}")

            # Connect
            if not await self.connect():
                return False

            # Authenticate
            if not await self.authenticate():
                await self.disconnect()
                return False

            # Disconnect
            await self.disconnect()

            logger.info(f"Connection test successful for {self.config.name}")
            self.status = IntegrationStatus.TESTING
            return True

        except Exception as e:
            logger.error(f"Connection test failed for {self.config.name}: {e}")
            self.status = IntegrationStatus.ERROR
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {
            "integration_id": self.config.integration_id,
            "integration_type": self.config.integration_type.value,
            "name": self.config.name,
            "status": self.status.value,
            "is_active": self.config.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "total_events": self.total_events,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        total = self.success_count + self.error_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0

        return {
            "total_events": self.total_events,
            "successful": self.success_count,
            "failed": self.error_count,
            "success_rate": success_rate,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
        }

    def increment_success(self) -> None:
        """Increment success counter."""
        self.success_count += 1
        self.total_events += 1

    def increment_error(self) -> None:
        """Increment error counter."""
        self.error_count += 1
        self.total_events += 1

    def set_last_sync(self) -> None:
        """Set last sync timestamp."""
        self.last_sync = datetime.utcnow()


class IntegrationEventHandler:
    """Handles integration events."""

    def __init__(self):
        """Initialize handler."""
        self.event_listeners: List = []

    async def subscribe(self, callback) -> None:
        """Subscribe to integration events."""
        if callback not in self.event_listeners:
            self.event_listeners.append(callback)

    async def unsubscribe(self, callback) -> None:
        """Unsubscribe from integration events."""
        if callback in self.event_listeners:
            self.event_listeners.remove(callback)

    async def handle_event(self, event: IntegrationEvent) -> None:
        """Handle integration event."""
        for callback in self.event_listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")


class DataMapping:
    """Maps between external and internal data models."""

    def __init__(self):
        """Initialize mapper."""
        self.mappings: Dict[str, Dict[str, str]] = {}

    def register_mapping(
        self, integration_type: str, external_fields: Dict[str, str]
    ) -> None:
        """Register field mapping for integration.

        Args:
            integration_type: Type of integration
            external_fields: Mapping of external field -> internal field
        """
        self.mappings[integration_type] = external_fields
        logger.debug(f"Registered mapping for {integration_type}")

    def map_incoming(self, integration_type: str, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map external data to internal format."""
        if integration_type not in self.mappings:
            return external_data

        mapping = self.mappings[integration_type]
        internal_data = {}

        for external_field, internal_field in mapping.items():
            if external_field in external_data:
                internal_data[internal_field] = external_data[external_field]

        return internal_data

    def map_outgoing(self, integration_type: str, internal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map internal data to external format."""
        if integration_type not in self.mappings:
            return internal_data

        mapping = self.mappings[integration_type]
        external_data = {}

        # Reverse mapping
        reverse_mapping = {v: k for k, v in mapping.items()}

        for internal_field, value in internal_data.items():
            external_field = reverse_mapping.get(internal_field, internal_field)
            external_data[external_field] = value

        return external_data
