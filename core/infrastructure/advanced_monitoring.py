"""
Advanced Monitoring and Alerting Module
Custom metrics, alert rules, SLI/SLO management, and anomaly detection.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from threading import Lock
from collections import deque

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"  # Cumulative
    GAUGE = "gauge"  # Point in time
    HISTOGRAM = "histogram"  # Distribution
    SUMMARY = "summary"  # Aggregated


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertState(Enum):
    """Alert states."""
    FIRING = "firing"
    RESOLVED = "resolved"
    PENDING = "pending"


@dataclass
class Metric:
    """Metric definition."""
    name: str
    metric_type: MetricType
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    unit: str = ""


@dataclass
class MetricValue:
    """Metric value point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule definition."""
    rule_id: str
    metric_name: str
    condition: str  # e.g., "value > 100", "avg(values, 5) > 50"
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    for_duration_seconds: int = 300  # Must persist for this long
    repeat_interval_seconds: int = 3600  # How often to re-fire


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    metric_name: str
    state: AlertState = AlertState.PENDING
    severity: AlertSeverity = AlertSeverity.WARNING
    fired_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    message: str = ""
    value: float = 0.0


@dataclass
class ServiceLevelIndicator:
    """Service Level Indicator (SLI)."""
    name: str
    metric_name: str
    description: str = ""
    good_condition: str = ""  # e.g., "latency < 100ms"
    total_condition: str = ""


@dataclass
class ServiceLevelObjective:
    """Service Level Objective (SLO)."""
    name: str
    sli: ServiceLevelIndicator
    target: float  # 0-1, e.g., 0.99 for 99%
    window_days: int = 30
    description: str = ""


@dataclass
class SLOMetrics:
    """SLO evaluation metrics."""
    good_events: int = 0
    total_events: int = 0
    current_compliance: float = 0.0  # 0-1
    budget_remaining: float = 0.0  # 0-1
    is_compliant: bool = False


class MetricsCollector:
    """Collects and stores metrics."""
    
    def __init__(self, max_history: int = 10000):
        """Initialize metrics collector."""
        self.max_history = max_history
        self.metrics: Dict[str, deque[MetricValue]] = {}
        self._lock = asyncio.Lock()
    
    async def record_metric(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None
    ) -> None:
        """Record metric value."""
        async with self._lock:
            if name not in self.metrics:
                self.metrics[name] = deque(maxlen=self.max_history)
            
            metric_value = MetricValue(
                timestamp=datetime.utcnow(),
                value=value,
                tags=tags or {}
            )
            self.metrics[name].append(metric_value)
    
    async def get_metric_values(
        self,
        name: str,
        limit: int = 100
    ) -> List[MetricValue]:
        """Get metric values."""
        async with self._lock:
            if name not in self.metrics:
                return []
            
            values = list(self.metrics[name])
            return values[-limit:]
    
    async def get_metric_stats(self, name: str) -> Dict[str, float]:
        """Get metric statistics."""
        async with self._lock:
            if name not in self.metrics or len(self.metrics[name]) == 0:
                return {}
            
            values = [m.value for m in self.metrics[name]]
            sorted_values = sorted(values)
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'median': sorted_values[len(sorted_values) // 2],
                'p95': sorted_values[int(len(sorted_values) * 0.95)],
                'p99': sorted_values[int(len(sorted_values) * 0.99)],
            }


class AlertManager:
    """Manages alert rules and firing."""
    
    def __init__(self, collector: MetricsCollector):
        """Initialize alert manager."""
        self.collector = collector
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._rule_eval_times: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    async def add_rule(self, rule: AlertRule) -> None:
        """Add alert rule."""
        async with self._lock:
            self.rules[rule.rule_id] = rule
            logger.info(f"Alert rule added: {rule.rule_id}")
    
    async def evaluate_rules(self) -> None:
        """Evaluate all alert rules."""
        async with self._lock:
            rules_copy = dict(self.rules)
        
        for rule_id, rule in rules_copy.items():
            if not rule.enabled:
                continue
            
            # Check if enough time has passed since last evaluation
            last_eval = self._rule_eval_times.get(rule_id)
            if last_eval and (datetime.utcnow() - last_eval).total_seconds() < 60:
                continue
            
            await self._evaluate_rule(rule)
            async with self._lock:
                self._rule_eval_times[rule_id] = datetime.utcnow()
    
    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate single rule."""
        metric_values = await self.collector.get_metric_values(rule.metric_name)
        
        if not metric_values:
            return
        
        # Simple threshold check
        latest_value = metric_values[-1].value
        triggered = self._check_condition(rule.condition, rule.threshold, latest_value)
        
        async with self._lock:
            alert_id = f"{rule.rule_id}:{rule.metric_name}"
            
            if triggered:
                if alert_id not in self.active_alerts:
                    # Create new alert
                    alert = Alert(
                        alert_id=alert_id,
                        rule_id=rule.rule_id,
                        metric_name=rule.metric_name,
                        state=AlertState.PENDING,
                        severity=rule.severity,
                        value=latest_value,
                        message=f"{rule.metric_name} triggered: {latest_value}"
                    )
                    self.active_alerts[alert_id] = alert
                    logger.warning(f"Alert triggered: {alert_id}")
                else:
                    # Update existing alert
                    alert = self.active_alerts[alert_id]
                    alert.value = latest_value
                    
                    # Check if should transition from PENDING to FIRING
                    if alert.state == AlertState.PENDING:
                        if alert.fired_at is None:
                            alert.fired_at = datetime.utcnow()
                        
                        elapsed = (datetime.utcnow() - alert.fired_at).total_seconds()
                        if elapsed >= rule.for_duration_seconds:
                            alert.state = AlertState.FIRING
            
            else:
                # Rule no longer triggered
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    if alert.state != AlertState.RESOLVED:
                        alert.state = AlertState.RESOLVED
                        alert.resolved_at = datetime.utcnow()
                        self.alert_history.append(alert)
                        del self.active_alerts[alert_id]
                        logger.info(f"Alert resolved: {alert_id}")
    
    def _check_condition(self, condition: str, threshold: float, value: float) -> bool:
        """Evaluate condition."""
        if ">" in condition:
            return value > threshold
        elif "<" in condition:
            return value < threshold
        elif "==" in condition:
            return value == threshold
        elif ">=" in condition:
            return value >= threshold
        elif "<=" in condition:
            return value <= threshold
        return False
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        async with self._lock:
            return list(self.active_alerts.values())
    
    async def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        async with self._lock:
            return self.alert_history[-limit:]


class SLOEvaluator:
    """Evaluates Service Level Objectives."""
    
    def __init__(self, collector: MetricsCollector):
        """Initialize SLO evaluator."""
        self.collector = collector
        self.slos: Dict[str, ServiceLevelObjective] = {}
        self.slo_metrics: Dict[str, SLOMetrics] = {}
        self._lock = asyncio.Lock()
    
    async def add_slo(self, slo: ServiceLevelObjective) -> None:
        """Add SLO."""
        async with self._lock:
            self.slos[slo.name] = slo
            self.slo_metrics[slo.name] = SLOMetrics()
    
    async def evaluate_slos(self) -> None:
        """Evaluate all SLOs."""
        async with self._lock:
            slos_copy = dict(self.slos)
        
        for slo_name, slo in slos_copy.items():
            await self._evaluate_slo(slo)
    
    async def _evaluate_slo(self, slo: ServiceLevelObjective) -> None:
        """Evaluate single SLO."""
        metric_values = await self.collector.get_metric_values(slo.sli.metric_name)
        
        if not metric_values:
            return
        
        # Count good events
        good_count = 0
        total_count = len(metric_values)
        
        for mv in metric_values:
            if self._check_sli_condition(slo.sli.good_condition, mv.value):
                good_count += 1
        
        compliance = good_count / total_count if total_count > 0 else 0.0
        
        # Calculate error budget
        target = slo.target
        error_budget = 1.0 - target
        used_budget = 1.0 - compliance
        remaining_budget = max(0, error_budget - used_budget)
        
        async with self._lock:
            self.slo_metrics[slo.name] = SLOMetrics(
                good_events=good_count,
                total_events=total_count,
                current_compliance=compliance,
                budget_remaining=remaining_budget / error_budget if error_budget > 0 else 0.0,
                is_compliant=compliance >= target
            )
    
    def _check_sli_condition(self, condition: str, value: float) -> bool:
        """Check SLI condition."""
        # Simple implementation
        if "<" in condition:
            threshold = float(condition.split("<")[1].strip())
            return value < threshold
        elif ">" in condition:
            threshold = float(condition.split(">")[1].strip())
            return value > threshold
        return True
    
    async def get_slo_metrics(self, slo_name: str) -> Optional[SLOMetrics]:
        """Get SLO metrics."""
        async with self._lock:
            return self.slo_metrics.get(slo_name)
    
    async def get_all_slo_metrics(self) -> Dict[str, SLOMetrics]:
        """Get all SLO metrics."""
        async with self._lock:
            return dict(self.slo_metrics)


class AdvancedMonitoringEngine:
    """Main advanced monitoring engine."""
    
    def __init__(self):
        """Initialize monitoring engine."""
        self.collector = MetricsCollector()
        self.alert_manager = AlertManager(self.collector)
        self.slo_evaluator = SLOEvaluator(self.collector)
        self._evaluation_task: Optional[asyncio.Task] = None
    
    async def start(self, evaluation_interval: int = 60) -> None:
        """Start monitoring engine."""
        if self._evaluation_task is None:
            self._evaluation_task = asyncio.create_task(
                self._continuous_evaluation(evaluation_interval)
            )
            logger.info("Advanced monitoring engine started")
    
    async def stop(self) -> None:
        """Stop monitoring engine."""
        if self._evaluation_task:
            self._evaluation_task.cancel()
            self._evaluation_task = None
            logger.info("Advanced monitoring engine stopped")
    
    async def _continuous_evaluation(self, interval: int) -> None:
        """Continuously evaluate rules and SLOs."""
        while True:
            try:
                await self.alert_manager.evaluate_rules()
                await self.slo_evaluator.evaluate_slos()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring evaluation: {e}")
                await asyncio.sleep(interval)
    
    async def record_metric(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None
    ) -> None:
        """Record metric."""
        await self.collector.record_metric(name, value, tags)
    
    async def get_monitoring_report(self) -> Dict[str, Any]:
        """Get comprehensive monitoring report."""
        active_alerts = await self.alert_manager.get_active_alerts()
        slo_metrics = await self.slo_evaluator.get_all_slo_metrics()
        
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_metrics': len(self.collector.metrics),
            'active_alerts': len(active_alerts),
            'critical_alerts': len(critical_alerts),
            'slos_compliant': sum(1 for m in slo_metrics.values() if m.is_compliant),
            'slos_total': len(slo_metrics),
            'alerts': [
                {
                    'id': a.alert_id,
                    'severity': a.severity.value,
                    'message': a.message
                }
                for a in critical_alerts
            ]
        }


_monitoring_engine: Optional[AdvancedMonitoringEngine] = None
_monitoring_lock = Lock()


async def get_advanced_monitoring_engine() -> AdvancedMonitoringEngine:
    """Get or create advanced monitoring engine."""
    global _monitoring_engine
    
    if _monitoring_engine is None:
        with _monitoring_lock:
            if _monitoring_engine is None:
                _monitoring_engine = AdvancedMonitoringEngine()
    
    return _monitoring_engine


__all__ = [
    "MetricsCollector",
    "AlertManager",
    "SLOEvaluator",
    "AdvancedMonitoringEngine",
    "Metric",
    "MetricValue",
    "AlertRule",
    "Alert",
    "ServiceLevelIndicator",
    "ServiceLevelObjective",
    "SLOMetrics",
    "MetricType",
    "AlertSeverity",
    "AlertState",
    "get_advanced_monitoring_engine",
]
