"""
Metrics Module - Metrics collection, aggregation, and monitoring.

Provides:
- Metric collection and storage
- Real-time metric aggregation
- Performance metrics tracking
- Alert threshold management
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
from enum import Enum
from collections import defaultdict

from core.infrastructure.monitoring import logger as structured_logger, monitor


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    
    COUNTER = "counter"  # Monotonically increasing
    GAUGE = "gauge"  # Current value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"  # Timing measurements


class AlertSeverity(Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point."""
    
    name: str
    value: float
    timestamp: datetime
    dimensions: Optional[Dict[str, str]] = None
    unit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "dimensions": self.dimensions,
            "unit": self.unit
        }


@dataclass
class Alert:
    """Alert generated from metric threshold."""
    
    alert_id: str
    metric_name: str
    severity: AlertSeverity
    value: float
    threshold: float
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "metric_name": self.metric_name,
            "severity": self.severity.value,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class MetricsCollector:
    """Collect and aggregate metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.alerts: Dict[str, Alert] = {}
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.logger = logger
    
    @monitor.timing
    def record_metric(
        self,
        name: str,
        value: float,
        dimensions: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a metric data point.
        
        Args:
            name: Metric name
            value: Metric value
            dimensions: Optional dimensions
            unit: Optional unit
            timestamp: Optional timestamp (default: now)
        """
        try:
            if not timestamp:
                timestamp = datetime.utcnow()
            
            point = MetricPoint(
                name=name,
                value=value,
                timestamp=timestamp,
                dimensions=dimensions,
                unit=unit
            )
            
            self.metrics[name].append(point)
            
            # Check thresholds
            self._check_thresholds(name, value)
            
        except Exception as e:
            self.logger.error(f"Error recording metric {name}: {e}")
    
    @monitor.timing
    def get_metric_history(
        self,
        name: str,
        lookback_minutes: int = 60
    ) -> List[MetricPoint]:
        """
        Get metric history.
        
        Args:
            name: Metric name
            lookback_minutes: Minutes to look back
            
        Returns:
            List of metric points
        """
        try:
            if name not in self.metrics:
                return []
            
            cutoff_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)
            history = [
                point for point in self.metrics[name]
                if point.timestamp >= cutoff_time
            ]
            
            return sorted(history, key=lambda p: p.timestamp)
            
        except Exception as e:
            self.logger.error(f"Error getting metric history: {e}")
            return []
    
    @monitor.timing
    def get_metric_statistics(
        self,
        name: str,
        lookback_minutes: int = 60
    ) -> Dict[str, float]:
        """
        Get statistics for a metric.
        
        Args:
            name: Metric name
            lookback_minutes: Minutes to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            history = self.get_metric_history(name, lookback_minutes)
            
            if not history:
                return {
                    "name": name,
                    "count": 0,
                    "error": "No data available"
                }
            
            values = [point.value for point in history]
            
            # Calculate statistics
            import statistics
            
            stats = {
                "name": name,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
            }
            
            if len(values) > 1:
                stats["stdev"] = statistics.stdev(values)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}")
            return {"error": str(e)}
    
    @monitor.timing
    def set_threshold(
        self,
        metric_name: str,
        warning: Optional[float] = None,
        critical: Optional[float] = None
    ) -> None:
        """
        Set alert thresholds for a metric.
        
        Args:
            metric_name: Metric name
            warning: Warning threshold
            critical: Critical threshold
        """
        try:
            if metric_name not in self.thresholds:
                self.thresholds[metric_name] = {}
            
            if warning is not None:
                self.thresholds[metric_name]["warning"] = warning
            
            if critical is not None:
                self.thresholds[metric_name]["critical"] = critical
            
            structured_logger.info(
                "Metric threshold set",
                {"metric_name": metric_name, "thresholds": self.thresholds[metric_name]}
            )
            
        except Exception as e:
            self.logger.error(f"Error setting threshold: {e}")
    
    @monitor.timing
    def get_active_alerts(self) -> List[Alert]:
        """
        Get all active (unresolved) alerts.
        
        Returns:
            List of active alerts
        """
        try:
            active = [
                alert for alert in self.alerts.values()
                if not alert.resolved
            ]
            
            return sorted(active, key=lambda a: a.timestamp, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []
    
    @monitor.timing
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            True if resolved
        """
        try:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            structured_logger.info(
                "Alert resolved",
                {"alert_id": alert_id, "metric_name": alert.metric_name}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")
            return False
    
    @monitor.timing
    def get_metric_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.
        
        Returns:
            Dictionary with metric summary
        """
        try:
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_metrics": len(self.metrics),
                "metrics": {},
                "active_alerts": len(self.get_active_alerts()),
                "total_alerts": len(self.alerts)
            }
            
            for metric_name in self.metrics.keys():
                stats = self.get_metric_statistics(metric_name, 60)
                summary["metrics"][metric_name] = stats
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting metric summary: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    def _check_thresholds(self, metric_name: str, value: float) -> None:
        """Check thresholds and generate alerts."""
        try:
            if metric_name not in self.thresholds:
                return
            
            thresholds = self.thresholds[metric_name]
            
            # Check critical threshold
            if "critical" in thresholds and value > thresholds["critical"]:
                self._create_alert(
                    metric_name,
                    value,
                    thresholds["critical"],
                    AlertSeverity.CRITICAL
                )
            
            # Check warning threshold
            elif "warning" in thresholds and value > thresholds["warning"]:
                self._create_alert(
                    metric_name,
                    value,
                    thresholds["warning"],
                    AlertSeverity.WARNING
                )
            
        except Exception as e:
            self.logger.error(f"Error checking thresholds: {e}")
    
    def _create_alert(
        self,
        metric_name: str,
        value: float,
        threshold: float,
        severity: AlertSeverity
    ) -> None:
        """Create an alert."""
        try:
            import uuid
            alert_id = str(uuid.uuid4())
            
            alert = Alert(
                alert_id=alert_id,
                metric_name=metric_name,
                severity=severity,
                value=value,
                threshold=threshold,
                message=f"{metric_name} exceeded {severity.value} threshold: {value} > {threshold}",
                timestamp=datetime.utcnow()
            )
            
            self.alerts[alert_id] = alert
            
            structured_logger.info(
                "Alert created",
                {
                    "alert_id": alert_id,
                    "metric_name": metric_name,
                    "severity": severity.value,
                    "value": value
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error creating alert: {e}")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset metrics collector (for testing)."""
    global _metrics_collector
    _metrics_collector = None
