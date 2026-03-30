"""Health check and metrics API endpoints.

Provides health checks, readiness probes, liveness probes, metrics endpoints,
and component status reporting.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.infrastructure.monitoring import (
    get_metrics_collector,
    get_performance_monitor,
    get_health_check_manager,
    get_system_metrics_collector,
    HealthStatus,
)
from core.infrastructure.deployment import get_deployment_config

router = APIRouter(prefix="/api/v1", tags=["health"])


# Response models
class MetricResponse(BaseModel):
    """Metric response."""

    name: str
    type: str
    value: float
    timestamp: str
    labels: Dict[str, str]


class PerformanceStatsResponse(BaseModel):
    """Performance statistics response."""

    total: int
    successes: int
    failures: int
    success_rate: float
    latency_min: float
    latency_max: float
    latency_avg: float
    latency_p50: float
    latency_p95: float
    latency_p99: float


class SystemMetricsResponse(BaseModel):
    """System metrics response."""

    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    process_memory_mb: float
    thread_count: int


class HealthCheckResponse(BaseModel):
    """Health check response."""

    component: str
    status: str
    message: str
    timestamp: str
    response_time_ms: float
    details: Dict[str, Any]


class OverallHealthResponse(BaseModel):
    """Overall health response."""

    status: str
    timestamp: str
    components: List[HealthCheckResponse]
    system_metrics: Optional[SystemMetricsResponse] = None
    uptime_seconds: Optional[float] = None


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    ready: bool
    components: Dict[str, bool]
    message: str


class LivenessResponse(BaseModel):
    """Liveness probe response."""

    alive: bool
    uptime_seconds: float
    message: str


# Health check endpoints
@router.get("/health", response_model=OverallHealthResponse)
async def health_check(
    health_manager=Depends(get_health_check_manager),
    system_collector=Depends(get_system_metrics_collector),
) -> Dict[str, Any]:
    """Get overall system health.

    Returns:
        Overall health status and component details
    """
    results = health_manager.run_all_checks()
    overall_status = health_manager.get_overall_status()
    system_metrics = system_collector.collect()

    components = [
        HealthCheckResponse(
            component=result.component,
            status=result.status.value,
            message=result.message,
            timestamp=result.timestamp.isoformat(),
            response_time_ms=result.response_time_ms,
            details=result.details,
        )
        for result in results.values()
    ]

    return {
        "status": overall_status.value,
        "timestamp": datetime.now().isoformat(),
        "components": components,
        "system_metrics": system_metrics.to_dict(),
    }


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_probe(
    health_manager=Depends(get_health_check_manager),
) -> Dict[str, Any]:
    """Readiness probe for load balancers.

    Returns:
        Readiness status
    """
    results = health_manager.run_all_checks()
    component_statuses = {
        name: result.status == HealthStatus.HEALTHY for name, result in results.items()
    }

    ready = all(component_statuses.values())
    message = "Ready" if ready else "Not ready - unhealthy components detected"

    return {
        "ready": ready,
        "components": component_statuses,
        "message": message,
    }


@router.get("/health/live", response_model=LivenessResponse)
async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe for Kubernetes.

    Returns:
        Liveness status
    """
    # Simple liveness check - just check if service is responding
    return {
        "alive": True,
        "uptime_seconds": 0,  # Would be replaced with actual uptime
        "message": "Service is alive and responding",
    }


@router.get("/health/{component}")
async def component_health(
    component: str,
    health_manager=Depends(get_health_check_manager),
) -> Dict[str, Any]:
    """Get health status for specific component.

    Args:
        component: Component name

    Returns:
        Component health status
    """
    result = health_manager.run_check(component)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Component not found: {component}")

    return result.to_dict()


# Metrics endpoints
@router.get("/metrics")
async def get_metrics(
    metrics_collector=Depends(get_metrics_collector),
) -> Dict[str, Any]:
    """Get all collected metrics.

    Returns:
        All metrics
    """
    all_metrics = metrics_collector.get_all_metrics()

    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            name: [m.to_dict() for m in metrics] for name, metrics in all_metrics.items()
        },
    }


@router.get("/metrics/{metric_name}")
async def get_metric(
    metric_name: str,
    metrics_collector=Depends(get_metrics_collector),
) -> Dict[str, Any]:
    """Get specific metric.

    Args:
        metric_name: Metric name

    Returns:
        Metric history
    """
    metrics = metrics_collector.get_metrics(metric_name)

    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metric not found: {metric_name}")

    return {
        "name": metric_name,
        "timestamp": datetime.now().isoformat(),
        "history": [m.to_dict() for m in metrics],
    }


# Performance endpoints
@router.get("/performance/statistics")
async def performance_statistics(
    operation: Optional[str] = None,
    minutes: int = 60,
    perf_monitor=Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """Get performance statistics.

    Args:
        operation: Specific operation or None for all
        minutes: Time window in minutes

    Returns:
        Performance statistics
    """
    stats = perf_monitor.get_statistics(operation, minutes)

    if not stats:
        return {
            "operation": operation,
            "minutes": minutes,
            "message": "No data available",
        }

    return {
        "operation": operation or "all",
        "minutes": minutes,
        "timestamp": datetime.now().isoformat(),
        **stats,
    }


@router.get("/performance/endpoints")
async def endpoint_statistics(
    endpoint: str,
    perf_monitor=Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """Get statistics for specific endpoint.

    Args:
        endpoint: API endpoint

    Returns:
        Endpoint statistics
    """
    stats = perf_monitor.get_endpoint_statistics(endpoint)

    if not stats:
        raise HTTPException(status_code=404, detail=f"No data for endpoint: {endpoint}")

    return {
        "endpoint": endpoint,
        "timestamp": datetime.now().isoformat(),
        **stats,
    }


# System metrics endpoints
@router.get("/system/metrics", response_model=SystemMetricsResponse)
async def system_metrics(
    system_collector=Depends(get_system_metrics_collector),
) -> Dict[str, Any]:
    """Get current system metrics.

    Returns:
        System resource metrics
    """
    metrics = system_collector.collect()
    return metrics.to_dict()


@router.get("/system/metrics/history")
async def system_metrics_history(
    minutes: int = 60,
    system_collector=Depends(get_system_metrics_collector),
) -> Dict[str, Any]:
    """Get system metrics history.

    Args:
        minutes: Time window in minutes

    Returns:
        System metrics history and statistics
    """
    stats = system_collector.get_statistics(minutes)

    if not stats:
        return {"minutes": minutes, "message": "No data available"}

    return {
        "minutes": minutes,
        "timestamp": datetime.now().isoformat(),
        **stats,
    }


# Configuration endpoints
@router.get("/config")
async def get_configuration() -> Dict[str, Any]:
    """Get deployment configuration (non-sensitive).

    Returns:
        Deployment configuration
    """
    config = get_deployment_config()

    return {
        "environment": config.environment.value,
        "app_name": config.app_name,
        "version": config.version,
        "debug": config.debug,
        "api": {
            "host": config.api.host,
            "port": config.api.port,
            "workers": config.api.workers,
        },
        "database": {
            "host": config.database.host,
            "port": config.database.port,
            "database": config.database.database,
            "pool_size": config.database.pool_size,
        },
        "monitoring": {
            "enabled": config.monitoring.enabled,
            "log_level": config.monitoring.log_level.value,
            "structured_logging": config.monitoring.structured_logging,
        },
    }


# Status endpoints
@router.get("/status")
async def status(
    health_manager=Depends(get_health_check_manager),
    system_collector=Depends(get_system_metrics_collector),
) -> Dict[str, Any]:
    """Get overall service status.

    Returns:
        Service status and metrics
    """
    health_results = health_manager.run_all_checks()
    overall_status = health_manager.get_overall_status()
    system_metrics = system_collector.collect()

    unhealthy = [
        name
        for name, result in health_results.items()
        if result.status != HealthStatus.HEALTHY
    ]

    return {
        "timestamp": datetime.now().isoformat(),
        "overall_status": overall_status.value,
        "uptime_seconds": 0,  # Would be replaced with actual uptime
        "components_total": len(health_results),
        "components_healthy": len(
            [r for r in health_results.values() if r.status == HealthStatus.HEALTHY]
        ),
        "components_unhealthy": len(unhealthy),
        "unhealthy_components": unhealthy,
        "system": {
            "cpu_percent": system_metrics.cpu_percent,
            "memory_percent": system_metrics.memory_percent,
            "disk_percent": system_metrics.disk_percent,
        },
    }
