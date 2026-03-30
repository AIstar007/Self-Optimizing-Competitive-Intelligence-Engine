"""Comprehensive audit logging system."""

import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    AUTHENTICATION_FAILED = "auth_failed"
    TOKEN_GENERATED = "token_generated"
    TOKEN_REVOKED = "token_revoked"

    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"

    # Role management
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Data operations
    DATA_READ = "data_read"
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"

    # Integration operations
    INTEGRATION_CREATED = "integration_created"
    INTEGRATION_UPDATED = "integration_updated"
    INTEGRATION_DELETED = "integration_deleted"
    INTEGRATION_ACTIVATED = "integration_activated"
    INTEGRATION_DEACTIVATED = "integration_deactivated"

    # Security events
    SECURITY_CONFIG_CHANGED = "security_config_changed"
    ENCRYPTION_KEY_ROTATED = "encryption_key_rotated"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    PERMISSION_DENIED = "permission_denied"

    # System events
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    DATABASE_BACKUP = "database_backup"
    API_ERROR = "api_error"


class AuditSeverity(Enum):
    """Audit event severity."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record."""

    event_type: AuditEventType
    user_id: Optional[str]
    timestamp: datetime
    resource_type: str
    resource_id: Optional[str]
    action: str
    status: str  # success, failure
    severity: AuditSeverity
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Comprehensive audit logging system."""

    def __init__(self, max_history: int = 10000):
        """Initialize audit logger."""
        self.events: List[AuditEvent] = []
        self.max_history = max_history

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        resource_type: str,
        action: str,
        status: str,
        resource_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log audit event."""
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            severity=severity,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
        )

        self.events.append(event)

        # Maintain max history
        if len(self.events) > self.max_history:
            self.events = self.events[-self.max_history :]

        logger.info(f"Audit event: {event_type.value} - {action} - {status}")
        return event

    def log_authentication(
        self,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """Log authentication event."""
        if success:
            event_type = AuditEventType.LOGIN
            status = "success"
            severity = AuditSeverity.INFO
        else:
            event_type = AuditEventType.AUTHENTICATION_FAILED
            status = "failure"
            severity = AuditSeverity.WARNING

        return self.log_event(
            event_type=event_type,
            user_id=user_id if success else None,
            resource_type="authentication",
            action="login" if success else "login_attempt",
            status=status,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_user_action(
        self,
        actor_id: str,
        user_id: str,
        action: str,
        success: bool,
        changes: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log user management action."""
        event_type_map = {
            "create": AuditEventType.USER_CREATED,
            "update": AuditEventType.USER_UPDATED,
            "delete": AuditEventType.USER_DELETED,
            "activate": AuditEventType.USER_ACTIVATED,
            "deactivate": AuditEventType.USER_DEACTIVATED,
        }

        event_type = event_type_map.get(action, AuditEventType.USER_UPDATED)

        return self.log_event(
            event_type=event_type,
            user_id=actor_id,
            resource_type="user",
            resource_id=user_id,
            action=action,
            status="success" if success else "failure",
            severity=AuditSeverity.INFO,
            changes=changes,
        )

    def log_data_access(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        success: bool,
        record_count: int = 0,
    ) -> AuditEvent:
        """Log data access event."""
        event_type_map = {
            "read": AuditEventType.DATA_READ,
            "create": AuditEventType.DATA_CREATED,
            "update": AuditEventType.DATA_UPDATED,
            "delete": AuditEventType.DATA_DELETED,
            "export": AuditEventType.DATA_EXPORTED,
        }

        event_type = event_type_map.get(action, AuditEventType.DATA_READ)

        return self.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status="success" if success else "failure",
            details={"record_count": record_count},
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        action: str,
        success: bool,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log security event."""
        return self.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_type="security",
            action=action,
            status="success" if success else "failure",
            severity=AuditSeverity.CRITICAL if not success else AuditSeverity.INFO,
            details=details,
        )

    def get_events_by_user(self, user_id: str, limit: int = 100) -> List[AuditEvent]:
        """Get events for specific user."""
        filtered = [e for e in self.events if e.user_id == user_id]
        return filtered[-limit :]

    def get_events_by_type(
        self, event_type: AuditEventType, limit: int = 100
    ) -> List[AuditEvent]:
        """Get events of specific type."""
        filtered = [e for e in self.events if e.event_type == event_type]
        return filtered[-limit :]

    def get_events_by_resource(
        self, resource_type: str, resource_id: Optional[str] = None, limit: int = 100
    ) -> List[AuditEvent]:
        """Get events for specific resource."""
        filtered = [
            e
            for e in self.events
            if e.resource_type == resource_type
            and (resource_id is None or e.resource_id == resource_id)
        ]
        return filtered[-limit :]

    def get_critical_events(self, limit: int = 100) -> List[AuditEvent]:
        """Get critical events."""
        filtered = [e for e in self.events if e.severity == AuditSeverity.CRITICAL]
        return filtered[-limit :]

    def get_events_in_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[AuditEvent]:
        """Get events within time range."""
        return [
            e for e in self.events
            if start_time <= e.timestamp <= end_time
        ]

    def export_events(self, filters: Optional[Dict[str, Any]] = None) -> str:
        """Export events as JSON."""
        events = self.events

        if filters:
            if "user_id" in filters:
                events = [e for e in events if e.user_id == filters["user_id"]]
            if "event_type" in filters:
                event_type = filters["event_type"]
                if isinstance(event_type, str):
                    event_type = AuditEventType[event_type]
                events = [e for e in events if e.event_type == event_type]
            if "severity" in filters:
                severity = filters["severity"]
                if isinstance(severity, str):
                    severity = AuditSeverity[severity]
                events = [e for e in events if e.severity == severity]

        return json.dumps([e.to_dict() for e in events], indent=2, default=str)

    def get_statistics(self) -> Dict:
        """Get audit statistics."""
        event_types = {}
        for event in self.events:
            key = event.event_type.value
            event_types[key] = event_types.get(key, 0) + 1

        critical_count = sum(1 for e in self.events if e.severity == AuditSeverity.CRITICAL)
        failed_count = sum(1 for e in self.events if e.status == "failure")

        return {
            "total_events": len(self.events),
            "critical_events": critical_count,
            "failed_events": failed_count,
            "event_types": event_types,
            "unique_users": len(set(e.user_id for e in self.events if e.user_id)),
            "date_range": {
                "start": self.events[0].timestamp.isoformat() if self.events else None,
                "end": self.events[-1].timestamp.isoformat() if self.events else None,
            },
        }

    def clear_old_events(self, days: int = 90) -> int:
        """Clear events older than specified days."""
        cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)
        original_count = len(self.events)
        self.events = [e for e in self.events if e.timestamp >= cutoff]
        removed = original_count - len(self.events)
        logger.info(f"Removed {removed} audit events older than {days} days")
        return removed


# Global instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
