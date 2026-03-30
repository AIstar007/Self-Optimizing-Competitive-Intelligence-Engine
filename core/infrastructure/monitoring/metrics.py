"""Monitoring and metrics collection infrastructure.

Provides Prometheus-style metrics collection, performance monitoring,
health checks, and system resource tracking.
"""

import logging
import psutil
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class HealthStatus(str, Enum):
    """Health status indicators."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """Individual metric data point."""

    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "help": self.help_text,
        }


@dataclass
class PerformanceMetric:
    """Performance metric with latency, throughput, errors."""

    operation: str
    latency_ms: float
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Health check result."""

    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "details": self.details,
        }


@dataclass
class SystemMetrics:
    """System resource metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    process_memory_mb: float
    thread_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_percent": self.disk_percent,
            "disk_used_gb": self.disk_used_gb,
            "disk_free_gb": self.disk_free_gb,
            "process_memory_mb": self.process_memory_mb,
            "thread_count": self.thread_count,
        }


class MetricsCollector:
    """Collects Prometheus-style metrics."""

    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector.

        Args:
            max_history: Maximum number of metrics to keep in history
        """
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.lock = threading.RLock()

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment counter metric.

        Args:
            name: Metric name
            value: Increment amount
            labels: Metric labels
        """
        with self.lock:
            key = self._make_key(name, labels)
            self.counters[key] += value

            metric = Metric(
                name=name,
                metric_type=MetricType.COUNTER,
                value=self.counters[key],
                timestamp=datetime.now(),
                labels=labels or {},
            )
            self.metrics[name].append(metric)

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Metric labels
        """
        with self.lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value

            metric = Metric(
                name=name,
                metric_type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {},
            )
            self.metrics[name].append(metric)

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record histogram metric.

        Args:
            name: Metric name
            value: Histogram value
            labels: Metric labels
        """
        with self.lock:
            metric = Metric(
                name=name,
                metric_type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {},
            )
            self.metrics[name].append(metric)

    def get_metric(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get current metric value.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Current metric value or None
        """
        with self.lock:
            key = self._make_key(name, labels)
            if name.startswith("counter_"):
                return self.counters.get(key)
            else:
                return self.gauges.get(key)

    def get_metrics(self, name: str) -> List[Metric]:
        """Get all metrics for a name.

        Args:
            name: Metric name

        Returns:
            List of metrics
        """
        with self.lock:
            return list(self.metrics.get(name, []))

    def get_all_metrics(self) -> Dict[str, List[Metric]]:
        """Get all metrics.

        Returns:
            Dictionary of all metrics
        """
        with self.lock:
            return {
                name: list(metrics) for name, metrics in self.metrics.items()
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create unique key for metric."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class PerformanceMonitor:
    """Monitors performance metrics."""

    def __init__(self, max_history: int = 10000):
        """Initialize performance monitor.

        Args:
            max_history: Maximum number of metrics to keep
        """
        self.max_history = max_history
        self.metrics: deque = deque(maxlen=max_history)
        self.lock = threading.RLock()

    def record_operation(
        self,
        operation: str,
        latency_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
    ) -> None:
        """Record operation performance.

        Args:
            operation: Operation name
            latency_ms: Latency in milliseconds
            success: Whether operation succeeded
            error_message: Error message if failed
            endpoint: API endpoint
            method: HTTP method
        """
        with self.lock:
            metric = PerformanceMetric(
                operation=operation,
                latency_ms=latency_ms,
                timestamp=datetime.now(),
                success=success,
                error_message=error_message,
                endpoint=endpoint,
                method=method,
            )
            self.metrics.append(metric)

    def get_statistics(
        self, operation: Optional[str] = None, minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance statistics.

        Args:
            operation: Specific operation or None for all
            minutes: Time window in minutes

        Returns:
            Performance statistics
        """
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            relevant = [
                m
                for m in self.metrics
                if (operation is None or m.operation == operation)
                and m.timestamp >= cutoff
            ]

            if not relevant:
                return {}

            latencies = [m.latency_ms for m in relevant]
            successes = sum(1 for m in relevant if m.success)
            failures = len(relevant) - successes

            return {
                "total": len(relevant),
                "successes": successes,
                "failures": failures,
                "success_rate": successes / len(relevant) if relevant else 0,
                "latency_min": min(latencies),
                "latency_max": max(latencies),
                "latency_avg": sum(latencies) / len(latencies),
                "latency_p50": self._percentile(latencies, 50),
                "latency_p95": self._percentile(latencies, 95),
                "latency_p99": self._percentile(latencies, 99),
            }

    def get_endpoint_statistics(self, endpoint: str) -> Dict[str, Any]:
        """Get statistics for specific endpoint.

        Args:
            endpoint: API endpoint

        Returns:
            Endpoint statistics
        """
        with self.lock:
            relevant = [m for m in self.metrics if m.endpoint == endpoint]

            if not relevant:
                return {}

            latencies = [m.latency_ms for m in relevant]
            successes = sum(1 for m in relevant if m.success)

            return {
                "total": len(relevant),
                "successes": successes,
                "failures": len(relevant) - successes,
                "success_rate": successes / len(relevant) if relevant else 0,
                "latency_avg": sum(latencies) / len(latencies),
                "latency_p95": self._percentile(latencies, 95),
            }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile.

        Args:
            data: Data values
            percentile: Percentile (0-100)

        Returns:
            Percentile value
        """
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]


class HealthCheckManager:
    """Manages health checks for system components."""

    def __init__(self):
        """Initialize health check manager."""
        self.checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.lock = threading.RLock()

    def register_check(
        self, component: str, check_fn: Callable[[], HealthCheckResult]
    ) -> None:
        """Register health check.

        Args:
            component: Component name
            check_fn: Health check function
        """
        with self.lock:
            self.checks[component] = check_fn

    def run_check(self, component: str) -> Optional[HealthCheckResult]:
        """Run health check.

        Args:
            component: Component name

        Returns:
            Health check result
        """
        with self.lock:
            if component not in self.checks:
                return None

            try:
                start = time.time()
                result = self.checks[component]()
                result.response_time_ms = (time.time() - start) * 1000
                self.results[component] = result
                return result
            except Exception as e:
                logger.error(f"Health check failed for {component}: {e}")
                result = HealthCheckResult(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    timestamp=datetime.now(),
                    response_time_ms=(time.time() - start) * 1000,
                )
                self.results[component] = result
                return result

    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered checks.

        Returns:
            Results for all checks
        """
        with self.lock:
            results = {}
            for component in self.checks:
                result = self.run_check(component)
                if result:
                    results[component] = result
            return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status.

        Returns:
            Overall health status
        """
        with self.lock:
            if not self.results:
                return HealthStatus.UNKNOWN

            statuses = [r.status for r in self.results.values()]

            if any(s == HealthStatus.UNHEALTHY for s in statuses):
                return HealthStatus.UNHEALTHY
            elif any(s == HealthStatus.DEGRADED for s in statuses):
                return HealthStatus.DEGRADED
            elif all(s == HealthStatus.HEALTHY for s in statuses):
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN

    def get_result(self, component: str) -> Optional[HealthCheckResult]:
        """Get last health check result.

        Args:
            component: Component name

        Returns:
            Last health check result
        """
        with self.lock:
            return self.results.get(component)

    def get_all_results(self) -> Dict[str, HealthCheckResult]:
        """Get all last health check results.

        Returns:
            All results
        """
        with self.lock:
            return dict(self.results)


class SystemMetricsCollector:
    """Collects system resource metrics."""

    def __init__(self, max_history: int = 1000):
        """Initialize system metrics collector.

        Args:
            max_history: Maximum metrics to keep
        """
        self.max_history = max_history
        self.metrics: deque = deque(maxlen=max_history)
        self.process = psutil.Process()
        self.lock = threading.RLock()

    def collect(self) -> SystemMetrics:
        """Collect current system metrics.

        Returns:
            System metrics
        """
        with self.lock:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            process_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_percent=disk.percent,
                disk_used_gb=disk.used / 1024 / 1024 / 1024,
                disk_free_gb=disk.free / 1024 / 1024 / 1024,
                process_memory_mb=process_memory,
                thread_count=threading.active_count(),
            )

            self.metrics.append(metrics)
            return metrics

    def get_metrics(self) -> List[SystemMetrics]:
        """Get all collected metrics.

        Returns:
            List of metrics
        """
        with self.lock:
            return list(self.metrics)

    def get_latest(self) -> Optional[SystemMetrics]:
        """Get latest metrics.

        Returns:
            Latest metrics
        """
        with self.lock:
            return self.metrics[-1] if self.metrics else None

    def get_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """Get metrics statistics.

        Args:
            minutes: Time window in minutes

        Returns:
            Statistics
        """
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            relevant = [m for m in self.metrics if m.timestamp >= cutoff]

            if not relevant:
                return {}

            cpu_values = [m.cpu_percent for m in relevant]
            memory_values = [m.memory_percent for m in relevant]

            return {
                "count": len(relevant),
                "cpu_avg": sum(cpu_values) / len(cpu_values),
                "cpu_max": max(cpu_values),
                "memory_avg": sum(memory_values) / len(memory_values),
                "memory_max": max(memory_values),
                "process_memory_avg": sum(m.process_memory_mb for m in relevant)
                / len(relevant),
                "process_memory_max": max(m.process_memory_mb for m in relevant),
            }


# Singleton instances
_metrics_collector: Optional[MetricsCollector] = None
_performance_monitor: Optional[PerformanceMonitor] = None
_health_check_manager: Optional[HealthCheckManager] = None
_system_metrics_collector: Optional[SystemMetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        logger.info("Initialized MetricsCollector")
    return _metrics_collector


def get_performance_monitor() -> PerformanceMonitor:
    """Get performance monitor singleton."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        logger.info("Initialized PerformanceMonitor")
    return _performance_monitor


def get_health_check_manager() -> HealthCheckManager:
    """Get health check manager singleton."""
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager()
        logger.info("Initialized HealthCheckManager")
    return _health_check_manager


def get_system_metrics_collector() -> SystemMetricsCollector:
    """Get system metrics collector singleton."""
    global _system_metrics_collector
    if _system_metrics_collector is None:
        _system_metrics_collector = SystemMetricsCollector()
        logger.info("Initialized SystemMetricsCollector")
    return _system_metrics_collector
