"""Real-time alert notification and delivery service."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from core.infrastructure.websocket.websocket_manager import get_websocket_manager, MessageType, WSMessage

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert notification channels."""

    WEBSOCKET = "websocket"
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert notification."""

    alert_id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    company_id: str
    user_id: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    is_resolved: bool = False

    def __post_init__(self):
        """Post-initialization processing."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "is_resolved": self.is_resolved,
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""

    rule_id: str
    name: str
    description: str
    condition: str  # Expression to evaluate
    severity: AlertSeverity
    channels: List[AlertChannel]
    enabled: bool = True
    throttle_duration_seconds: int = 300  # Prevent alert spam
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class AlertQueue:
    """Priority queue for alert delivery."""

    def __init__(self, max_size: int = 1000):
        """Initialize alert queue."""
        self.max_size = max_size
        self.alerts: List[Alert] = []
        self.lock = asyncio.Lock()

    async def enqueue(self, alert: Alert) -> bool:
        """Add alert to queue."""
        async with self.lock:
            if len(self.alerts) >= self.max_size:
                # Remove lowest priority alert
                self.alerts.sort(
                    key=lambda a: (
                        AlertSeverity[a.severity.upper()] == AlertSeverity.CRITICAL,
                        a.created_at,
                    )
                )
                self.alerts.pop(0)

            self.alerts.append(alert)
            # Sort by severity (critical first)
            self.alerts.sort(
                key=lambda a: (
                    a.severity != AlertSeverity.CRITICAL,
                    a.created_at,
                ),
                reverse=True,
            )
            return True

    async def dequeue(self) -> Optional[Alert]:
        """Get next alert from queue."""
        async with self.lock:
            if not self.alerts:
                return None
            return self.alerts.pop(0)

    async def size(self) -> int:
        """Get queue size."""
        async with self.lock:
            return len(self.alerts)

    async def clear(self) -> int:
        """Clear queue and return count."""
        async with self.lock:
            count = len(self.alerts)
            self.alerts.clear()
            return count


class AlertService:
    """Service for managing alerts and notifications."""

    def __init__(self):
        """Initialize alert service."""
        self.queue = AlertQueue()
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: Dict[str, List[Alert]] = {}
        self.max_history_per_source = 100
        self.recent_alerts: Dict[str, datetime] = {}  # For throttling
        self.listeners: List[Callable] = []
        self._processing_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        """Start alert processing service."""
        if self._is_running:
            return

        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_alerts())
        logger.info("Alert service started")

    async def stop(self) -> None:
        """Stop alert processing service."""
        if not self._is_running:
            return

        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert service stopped")

    async def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        company_id: str,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create and queue an alert."""
        alert_id = str(uuid4())
        alert = Alert(
            alert_id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            company_id=company_id,
            user_id=user_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        await self.queue.enqueue(alert)

        # Store in history
        if source not in self.alert_history:
            self.alert_history[source] = []

        history = self.alert_history[source]
        history.append(alert)

        if len(history) > self.max_history_per_source:
            history.pop(0)

        logger.info(f"Alert {alert_id} created: {title}")
        return alert_id

    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved."""
        # Search through history and mark as resolved
        for alerts in self.alert_history.values():
            for alert in alerts:
                if alert.alert_id == alert_id:
                    alert.is_resolved = True
                    logger.info(f"Alert {alert_id} resolved")
                    return True

        return False

    async def register_rule(self, rule: AlertRule) -> None:
        """Register alert rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Alert rule {rule.rule_id} registered: {rule.name}")

    async def evaluate_rules(self, context: Dict[str, Any]) -> List[Alert]:
        """Evaluate alert rules against context."""
        triggered_alerts = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                # Simple condition evaluation (in production, use safer evaluation)
                if await self._evaluate_condition(rule.condition, context):
                    alert_id = str(uuid4())
                    alert = Alert(
                        alert_id=alert_id,
                        title=rule.name,
                        message=rule.description,
                        severity=rule.severity,
                        source=f"rule_{rule.rule_id}",
                        company_id=context.get("company_id", ""),
                        metadata={"rule_id": rule.rule_id, **rule.metadata},
                    )

                    # Check throttling
                    throttle_key = f"{rule.rule_id}_{context.get('company_id')}"
                    now = datetime.utcnow()

                    if throttle_key in self.recent_alerts:
                        elapsed = (now - self.recent_alerts[throttle_key]).total_seconds()
                        if elapsed < rule.throttle_duration_seconds:
                            continue

                    self.recent_alerts[throttle_key] = now
                    triggered_alerts.append(alert)
                    await self.queue.enqueue(alert)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")

        return triggered_alerts

    async def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition expression."""
        try:
            # Simple evaluation (in production, use restricted eval)
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    async def _process_alerts(self) -> None:
        """Process alerts from queue."""
        ws_manager = get_websocket_manager()

        while self._is_running:
            try:
                alert = await self.queue.dequeue()

                if alert:
                    # Broadcast via WebSocket
                    await ws_manager.broadcast_alert(
                        alert.alert_id,
                        alert.to_dict(),
                        company_id=alert.company_id,
                    )

                    # Notify listeners
                    for listener in self.listeners:
                        try:
                            if asyncio.iscoroutinefunction(listener):
                                await listener(alert)
                            else:
                                listener(alert)
                        except Exception as e:
                            logger.error(f"Error in alert listener: {e}")

                    logger.info(f"Alert {alert.alert_id} processed")

                else:
                    # Small delay when queue is empty
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing alerts: {e}")
                await asyncio.sleep(1)

    async def subscribe(self, callback: Callable) -> None:
        """Subscribe to alert notifications."""
        if callback not in self.listeners:
            self.listeners.append(callback)
            logger.debug("New alert subscriber registered")

    async def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from alert notifications."""
        if callback in self.listeners:
            self.listeners.remove(callback)
            logger.debug("Alert subscriber removed")

    async def get_alert_history(
        self,
        source: str,
        limit: int = 50,
    ) -> List[Alert]:
        """Get alert history for a source."""
        history = self.alert_history.get(source, [])
        return history[-limit:] if limit else history

    async def get_active_alerts(self, company_id: Optional[str] = None) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        active = []

        for alerts in self.alert_history.values():
            for alert in alerts:
                if not alert.is_resolved:
                    if company_id is None or alert.company_id == company_id:
                        active.append(alert)

        return active

    async def get_statistics(self) -> Dict[str, Any]:
        """Get alert service statistics."""
        active_alerts = await self.get_active_alerts()
        critical_count = sum(1 for a in active_alerts if a.severity == AlertSeverity.CRITICAL)
        warning_count = sum(1 for a in active_alerts if a.severity == AlertSeverity.WARNING)

        return {
            "is_running": self._is_running,
            "queue_size": await self.queue.size(),
            "active_alerts": len(active_alerts),
            "critical_alerts": critical_count,
            "warning_alerts": warning_count,
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "history_sources": len(self.alert_history),
            "listeners": len(self.listeners),
        }


# Global alert service instance
_alert_service: Optional[AlertService] = None


async def get_alert_service() -> AlertService:
    """Get or create global alert service."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
        await _alert_service.start()
    return _alert_service
