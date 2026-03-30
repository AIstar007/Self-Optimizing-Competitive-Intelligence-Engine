"""Event system for pub/sub event handling."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event type enumeration."""

    # Signal events
    SIGNAL_CREATED = "signal.created"
    SIGNAL_VERIFIED = "signal.verified"
    SIGNAL_ENRICHED = "signal.enriched"

    # Report events
    REPORT_GENERATED = "report.generated"
    REPORT_EXPORTED = "report.exported"

    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_CANCELLED = "workflow.cancelled"

    # Task events
    TASK_SCHEDULED = "task.scheduled"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_THINKING = "agent.thinking"
    AGENT_TOOL_USED = "agent.tool_used"
    AGENT_COMPLETED = "agent.completed"

    # Market events
    MARKET_ANALYZED = "market.analyzed"
    MARKET_TREND_IDENTIFIED = "market.trend_identified"

    # Competitor events
    COMPETITOR_TRACKED = "competitor.tracked"
    COMPETITOR_ACTIVITY_DETECTED = "competitor.activity_detected"

    # Learning events
    FEEDBACK_RECEIVED = "feedback.received"
    MODEL_UPDATED = "model.updated"

    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_ERROR = "system.error"


@dataclass
class Event:
    """Base event class."""

    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "data": self.data,
        }


class EventHandler:
    """Handle events from the event bus."""

    def __init__(self, event_type: EventType, handler: Callable):
        """
        Initialize handler.

        Args:
            event_type: Type of event to handle
            handler: Async handler function
        """
        self.event_type = event_type
        self.handler = handler
        self.handler_id = str(uuid.uuid4())

    async def handle(self, event: Event):
        """
        Handle an event.

        Args:
            event: Event to handle
        """
        try:
            await self.handler(event)
        except Exception as e:
            logger.error(f"Error in event handler: {e}")


class EventBus:
    """Publish/subscribe event bus."""

    def __init__(self):
        """Initialize event bus."""
        self.handlers: dict[EventType, list[EventHandler]] = {}
        self.event_history: list[Event] = []
        self.max_history = 1000

    def subscribe(self, event_type: EventType, handler: Callable) -> str:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async handler function

        Returns:
            Handler ID for unsubscribing
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        event_handler = EventHandler(event_type, handler)
        self.handlers[event_type].append(event_handler)
        logger.debug(f"Subscribed to {event_type.value}")
        return event_handler.handler_id

    def unsubscribe(self, event_type: EventType, handler_id: str):
        """
        Unsubscribe from events.

        Args:
            event_type: Type of event
            handler_id: Handler ID to remove
        """
        if event_type not in self.handlers:
            return

        self.handlers[event_type] = [
            h for h in self.handlers[event_type] if h.handler_id != handler_id
        ]
        logger.debug(f"Unsubscribed from {event_type.value}")

    async def publish(self, event: Event):
        """
        Publish an event.

        Args:
            event: Event to publish
        """
        logger.debug(f"Publishing event: {event.event_type.value}")

        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Notify handlers
        handlers = self.handlers.get(event.event_type, [])
        for handler in handlers:
            asyncio.create_task(handler.handle(event))

    async def publish_sync(self, event: Event):
        """
        Publish an event and wait for all handlers.

        Args:
            event: Event to publish
        """
        logger.debug(f"Publishing event (sync): {event.event_type.value}")

        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        handlers = self.handlers.get(event.event_type, [])
        for handler in handlers:
            await handler.handle(event)

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get event history.

        Args:
            event_type: Optional filter by event type
            limit: Maximum events to return

        Returns:
            List of events
        """
        if event_type:
            events = [e for e in self.event_history if e.event_type == event_type]
        else:
            events = self.event_history

        return events[-limit:]

    def get_event_count(self, event_type: Optional[EventType] = None) -> int:
        """
        Get count of events.

        Args:
            event_type: Optional specific event type

        Returns:
            Number of events
        """
        if event_type:
            return len([e for e in self.event_history if e.event_type == event_type])
        return len(self.event_history)

    def clear_history(self):
        """Clear event history."""
        self.event_history.clear()


# Global event bus instance
event_bus = EventBus()


# ============================================================================
# Event Creators
# ============================================================================


def create_signal_event(
    event_type: EventType,
    signal_id: str,
    data: dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Event:
    """Create a signal event."""
    return Event(
        event_type=event_type,
        source="signal",
        data={"signal_id": signal_id, **data},
        correlation_id=correlation_id,
    )


def create_report_event(
    event_type: EventType,
    report_id: str,
    data: dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Event:
    """Create a report event."""
    return Event(
        event_type=event_type,
        source="report",
        data={"report_id": report_id, **data},
        correlation_id=correlation_id,
    )


def create_workflow_event(
    event_type: EventType,
    workflow_id: str,
    data: dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Event:
    """Create a workflow event."""
    return Event(
        event_type=event_type,
        source="workflow",
        data={"workflow_id": workflow_id, **data},
        correlation_id=correlation_id,
    )


def create_task_event(
    event_type: EventType,
    task_id: str,
    data: dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Event:
    """Create a task event."""
    return Event(
        event_type=event_type,
        source="task",
        data={"task_id": task_id, **data},
        correlation_id=correlation_id,
    )


def create_agent_event(
    event_type: EventType,
    agent_id: str,
    data: dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Event:
    """Create an agent event."""
    return Event(
        event_type=event_type,
        source="agent",
        data={"agent_id": agent_id, **data},
        correlation_id=correlation_id,
    )
