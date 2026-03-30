"""Structured logging infrastructure.

Provides JSON logging, audit trails, performance tracking, and alerting.
"""

import logging
import json
import threading
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEventType(str, Enum):
    """Audit event types."""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    PERMISSION_CHANGE = "permission_change"
    SECURITY_EVENT = "security_event"
    CONFIGURATION_CHANGE = "configuration_change"
    DATA_ACCESS = "data_access"
    ERROR = "error"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "logger": self.logger_name,
            "message": self.message,
            "context": self.context,
            "exception": self.exception,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
        }

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class AuditLog:
    """Audit log entry."""

    timestamp: datetime
    event_type: AuditEventType
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    changes: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    status: str = "success"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "status": self.status,
        }


@dataclass
class PerformanceLog:
    """Performance log entry."""

    timestamp: datetime
    operation: str
    duration_ms: float
    component: str
    status: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "component": self.component,
            "status": self.status,
            "details": self.details,
        }


@dataclass
class Alert:
    """Alert definition."""

    id: str
    name: str
    severity: AlertSeverity
    threshold: float
    metric_name: str
    condition: str  # "greater_than", "less_than", "equals"
    triggered_at: Optional[datetime] = None
    triggered_value: Optional[float] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "threshold": self.threshold,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "triggered_value": self.triggered_value,
            "message": self.message,
        }


class StructuredLogger:
    """Structured JSON logger."""

    def __init__(self, logger_name: str = "structured", max_history: int = 10000):
        """Initialize logger.

        Args:
            logger_name: Logger name
            max_history: Max log entries to keep
        """
        self.logger_name = logger_name
        self.max_history = max_history
        self.logs: deque = deque(maxlen=max_history)
        self.lock = threading.RLock()
        self.logger = logging.getLogger(logger_name)

    def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Log message with context.

        Args:
            level: Log level
            message: Log message
            context: Context dictionary
            exception: Exception to log
            trace_id: Trace ID
            user_id: User ID
            request_id: Request ID
        """
        with self.lock:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                logger_name=self.logger_name,
                message=message,
                context=context or {},
                exception=str(exception) if exception else None,
                trace_id=trace_id,
                user_id=user_id,
                request_id=request_id,
            )

            self.logs.append(entry)

            # Also use standard logging
            log_method = getattr(self.logger, level.value.lower())
            log_method(entry.to_json())

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Debug level log."""
        self.log(LogLevel.DEBUG, message, context)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Info level log."""
        self.log(LogLevel.INFO, message, context)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Warning level log."""
        self.log(LogLevel.WARNING, message, context)

    def error(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Error level log."""
        self.log(LogLevel.ERROR, message, context, exception)

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Critical level log."""
        self.log(LogLevel.CRITICAL, message, context)

    def get_logs(
        self, level: Optional[LogLevel] = None, limit: int = 100
    ) -> List[LogEntry]:
        """Get logged entries.

        Args:
            level: Filter by level
            limit: Max entries to return

        Returns:
            List of log entries
        """
        with self.lock:
            logs = list(self.logs)
            if level:
                logs = [l for l in logs if l.level == level]
            return logs[-limit:]


class AuditLogger:
    """Audit trail logger."""

    def __init__(self, max_history: int = 50000):
        """Initialize audit logger.

        Args:
            max_history: Max audit logs to keep
        """
        self.max_history = max_history
        self.logs: deque = deque(maxlen=max_history)
        self.lock = threading.RLock()
        self.logger = logging.getLogger("audit")

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
    ) -> None:
        """Log audit event.

        Args:
            event_type: Event type
            user_id: User performing action
            resource_type: Resource type
            resource_id: Resource ID
            action: Action description
            changes: Changes made
            ip_address: Source IP
            status: Event status
        """
        with self.lock:
            log = AuditLog(
                timestamp=datetime.now(),
                event_type=event_type,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                changes=changes or {},
                ip_address=ip_address,
                status=status,
            )

            self.logs.append(log)
            self.logger.info(json.dumps(log.to_dict(), default=str))

    def get_logs(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AuditLog]:
        """Get audit logs.

        Args:
            user_id: Filter by user
            resource_type: Filter by resource type
            limit: Max entries to return

        Returns:
            List of audit logs
        """
        with self.lock:
            logs = list(self.logs)
            if user_id:
                logs = [l for l in logs if l.user_id == user_id]
            if resource_type:
                logs = [l for l in logs if l.resource_type == resource_type]
            return logs[-limit:]


class PerformanceLogger:
    """Performance tracking logger."""

    def __init__(self, max_history: int = 10000):
        """Initialize performance logger.

        Args:
            max_history: Max logs to keep
        """
        self.max_history = max_history
        self.logs: deque = deque(maxlen=max_history)
        self.lock = threading.RLock()
        self.logger = logging.getLogger("performance")

    def log_operation(
        self,
        operation: str,
        duration_ms: float,
        component: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log performance operation.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            component: Component name
            status: Operation status
            details: Additional details
        """
        with self.lock:
            log = PerformanceLog(
                timestamp=datetime.now(),
                operation=operation,
                duration_ms=duration_ms,
                component=component,
                status=status,
                details=details or {},
            )

            self.logs.append(log)
            self.logger.info(json.dumps(log.to_dict(), default=str))

    def get_logs(
        self, component: Optional[str] = None, limit: int = 1000
    ) -> List[PerformanceLog]:
        """Get performance logs.

        Args:
            component: Filter by component
            limit: Max entries to return

        Returns:
            List of logs
        """
        with self.lock:
            logs = list(self.logs)
            if component:
                logs = [l for l in logs if l.component == component]
            return logs[-limit:]

    def get_statistics(
        self, component: Optional[str] = None, minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance statistics.

        Args:
            component: Filter by component
            minutes: Time window in minutes

        Returns:
            Performance statistics
        """
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            logs = [
                l
                for l in self.logs
                if l.timestamp >= cutoff
                and (component is None or l.component == component)
            ]

            if not logs:
                return {}

            durations = [l.duration_ms for l in logs]
            successes = sum(1 for l in logs if l.status == "success")

            return {
                "total": len(logs),
                "successes": successes,
                "failures": len(logs) - successes,
                "success_rate": successes / len(logs) if logs else 0,
                "duration_min": min(durations),
                "duration_max": max(durations),
                "duration_avg": sum(durations) / len(durations),
                "duration_p95": self._percentile(durations, 95),
            }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]


class AlertManager:
    """Manages alerts and thresholds."""

    def __init__(self):
        """Initialize alert manager."""
        self.alerts: Dict[str, Alert] = {}
        self.triggered_alerts: deque = deque(maxlen=10000)
        self.lock = threading.RLock()
        self.logger = logging.getLogger("alerts")

    def register_alert(self, alert: Alert) -> None:
        """Register alert rule.

        Args:
            alert: Alert definition
        """
        with self.lock:
            self.alerts[alert.id] = alert
            self.logger.info(f"Registered alert: {alert.name}")

    def check_metric(self, metric_name: str, value: float) -> Optional[Alert]:
        """Check metric against alert rules.

        Args:
            metric_name: Metric name
            value: Metric value

        Returns:
            Alert if triggered, else None
        """
        with self.lock:
            triggered = None
            for alert in self.alerts.values():
                if alert.metric_name != metric_name:
                    continue

                should_trigger = False
                if alert.condition == "greater_than":
                    should_trigger = value > alert.threshold
                elif alert.condition == "less_than":
                    should_trigger = value < alert.threshold
                elif alert.condition == "equals":
                    should_trigger = value == alert.threshold

                if should_trigger and alert.triggered_at is None:
                    alert.triggered_at = datetime.now()
                    alert.triggered_value = value
                    triggered = alert
                    self.triggered_alerts.append(alert)
                    self.logger.warning(
                        f"Alert triggered: {alert.name} (value={value}, "
                        f"threshold={alert.threshold})"
                    )
                elif not should_trigger and alert.triggered_at is not None:
                    alert.triggered_at = None
                    alert.triggered_value = None

            return triggered

    def get_triggered_alerts(self) -> List[Alert]:
        """Get currently triggered alerts.

        Returns:
            List of triggered alerts
        """
        with self.lock:
            return [a for a in self.alerts.values() if a.triggered_at is not None]

    def get_alert_history(self, limit: int = 1000) -> List[Alert]:
        """Get alert history.

        Args:
            limit: Max entries to return

        Returns:
            Alert history
        """
        with self.lock:
            return list(self.triggered_alerts)[-limit:]


# Singleton instances
_structured_logger: Optional[StructuredLogger] = None
_audit_logger: Optional[AuditLogger] = None
_performance_logger: Optional[PerformanceLogger] = None
_alert_manager: Optional[AlertManager] = None


def get_structured_logger() -> StructuredLogger:
    """Get structured logger singleton."""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
        logging.getLogger("structured").info("Initialized StructuredLogger")
    return _structured_logger


def get_audit_logger() -> AuditLogger:
    """Get audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
        logging.getLogger("audit").info("Initialized AuditLogger")
    return _audit_logger


def get_performance_logger() -> PerformanceLogger:
    """Get performance logger singleton."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
        logging.getLogger("performance").info("Initialized PerformanceLogger")
    return _performance_logger


def get_alert_manager() -> AlertManager:
    """Get alert manager singleton."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        logging.getLogger("alerts").info("Initialized AlertManager")
    return _alert_manager
