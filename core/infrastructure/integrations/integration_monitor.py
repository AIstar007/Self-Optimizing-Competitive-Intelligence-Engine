"""Integration monitoring and health tracking service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from core.infrastructure.integrations.base_adapter import BaseIntegrationAdapter
from core.infrastructure.integrations.integration_registry import get_integration_registry

logger = logging.getLogger(__name__)


@dataclass
class IntegrationHealthStatus:
    """Health status of an integration."""

    integration_id: str
    status: str
    last_check: datetime
    success_count: int
    error_count: int
    error_rate: float
    uptime_percentage: float
    last_error: Optional[str] = None
    recommendations: List[str] = None

    def __post_init__(self):
        """Initialize recommendations."""
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class IntegrationMetrics:
    """Metrics for an integration over time."""

    integration_id: str
    timestamp: datetime
    success_count: int
    error_count: int
    total_operations: int
    success_rate: float
    response_time_ms: float = 0.0
    data_transferred_bytes: int = 0


class IntegrationMonitor:
    """Monitor and track integration health and performance."""

    def __init__(self, check_interval: int = 300):
        """Initialize monitor."""
        self.check_interval = check_interval  # seconds
        self.registry = get_integration_registry()
        self.health_history: Dict[str, List[IntegrationHealthStatus]] = {}
        self.metrics_history: Dict[str, List[IntegrationMetrics]] = {}
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.alerts: List[Dict[str, Any]] = []

    async def start_monitoring(self) -> None:
        """Start monitoring integrations."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Integration monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop monitoring integrations."""
        self.monitoring_active = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Integration monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self.check_all_integrations()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)

    async def check_all_integrations(self) -> List[IntegrationHealthStatus]:
        """Check health of all active integrations."""
        health_statuses = []

        integrations = self.registry.get_active_integrations()

        for integration_id, adapter in integrations.items():
            try:
                status = await self.check_integration_health(integration_id, adapter)
                health_statuses.append(status)

                # Track history
                if integration_id not in self.health_history:
                    self.health_history[integration_id] = []

                self.health_history[integration_id].append(status)

                # Keep last 1000 records
                if len(self.health_history[integration_id]) > 1000:
                    self.health_history[integration_id] = self.health_history[integration_id][-1000:]

                # Check for alerts
                await self._check_for_alerts(integration_id, status)
            except Exception as e:
                logger.error(f"Error checking integration {integration_id}: {e}")

        return health_statuses

    async def check_integration_health(
        self, integration_id: str, adapter: BaseIntegrationAdapter
    ) -> IntegrationHealthStatus:
        """Check health of a single integration."""
        try:
            # Get current statistics
            stats = adapter.get_stats()

            # Run health check
            is_healthy = await adapter.health_check()

            # Calculate metrics
            total_ops = stats.get("success_count", 0) + stats.get("error_count", 0)
            success_rate = (
                stats.get("success_count", 0) / total_ops * 100 if total_ops > 0 else 0
            )
            error_rate = (
                stats.get("error_count", 0) / total_ops * 100 if total_ops > 0 else 0
            )

            # Calculate uptime based on error rate
            uptime_percentage = 100 - error_rate

            status_str = "HEALTHY" if is_healthy else "UNHEALTHY"

            recommendations = self._generate_recommendations(
                integration_id, adapter, stats, error_rate
            )

            health_status = IntegrationHealthStatus(
                integration_id=integration_id,
                status=status_str,
                last_check=datetime.utcnow(),
                success_count=stats.get("success_count", 0),
                error_count=stats.get("error_count", 0),
                error_rate=error_rate,
                uptime_percentage=uptime_percentage,
                last_error=stats.get("last_error", None),
                recommendations=recommendations,
            )

            return health_status
        except Exception as e:
            logger.error(f"Health check error for {integration_id}: {e}")

            return IntegrationHealthStatus(
                integration_id=integration_id,
                status="ERROR",
                last_check=datetime.utcnow(),
                success_count=0,
                error_count=1,
                error_rate=100.0,
                uptime_percentage=0.0,
                last_error=str(e),
                recommendations=["Review integration configuration", "Check integration logs"],
            )

    async def _check_for_alerts(
        self, integration_id: str, health_status: IntegrationHealthStatus
    ) -> None:
        """Check for alert conditions."""
        if health_status.status == "UNHEALTHY" or health_status.error_rate > 25:
            alert = {
                "integration_id": integration_id,
                "alert_type": "HEALTH_DEGRADATION",
                "timestamp": datetime.utcnow(),
                "error_rate": health_status.error_rate,
                "status": health_status.status,
            }

            self.alerts.append(alert)

            # Keep last 100 alerts
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]

            logger.warning(f"Alert for {integration_id}: {alert}")

    def _generate_recommendations(
        self,
        integration_id: str,
        adapter: BaseIntegrationAdapter,
        stats: Dict[str, Any],
        error_rate: float,
    ) -> List[str]:
        """Generate recommendations based on integration health."""
        recommendations = []

        if error_rate > 50:
            recommendations.append("High error rate detected - review recent changes")
            recommendations.append("Check integration credentials and permissions")

        if error_rate > 25:
            recommendations.append("Elevated error rate - monitor closely")
            recommendations.append("Review integration logs for failure patterns")

        if adapter.get_last_sync() is None:
            recommendations.append("Integration has never been synced - run initial sync")

        last_sync = adapter.get_last_sync()
        if last_sync and (datetime.utcnow() - last_sync).total_seconds() > 86400:
            recommendations.append("No recent sync - may need to trigger manual sync")

        return recommendations

    def get_integration_health(self, integration_id: str) -> Optional[IntegrationHealthStatus]:
        """Get latest health status for integration."""
        if integration_id not in self.health_history or not self.health_history[integration_id]:
            return None

        return self.health_history[integration_id][-1]

    def get_health_history(
        self, integration_id: str, limit: int = 100
    ) -> List[IntegrationHealthStatus]:
        """Get health history for integration."""
        if integration_id not in self.health_history:
            return []

        return self.health_history[integration_id][-limit:]

    def get_all_health_status(self) -> Dict[str, IntegrationHealthStatus]:
        """Get latest health status for all integrations."""
        result = {}

        for integration_id, history in self.health_history.items():
            if history:
                result[integration_id] = history[-1]

        return result

    def get_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self.alerts[-limit:]

    def get_alerts_by_integration(
        self, integration_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get alerts for specific integration."""
        filtered = [a for a in self.alerts if a["integration_id"] == integration_id]
        return filtered[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall monitoring statistics."""
        all_statuses = self.get_all_health_status()

        healthy_count = sum(1 for s in all_statuses.values() if s.status == "HEALTHY")
        unhealthy_count = sum(1 for s in all_statuses.values() if s.status != "HEALTHY")

        avg_error_rate = (
            sum(s.error_rate for s in all_statuses.values()) / len(all_statuses)
            if all_statuses
            else 0
        )

        return {
            "total_integrations": len(all_statuses),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "health_percentage": (
                healthy_count / len(all_statuses) * 100 if all_statuses else 0
            ),
            "average_error_rate": avg_error_rate,
            "total_alerts": len(self.alerts),
            "last_check": max(
                (s.last_check for s in all_statuses.values()),
                default=None,
            ),
        }


# Global instance
_monitor: Optional[IntegrationMonitor] = None


def get_integration_monitor(check_interval: int = 300) -> IntegrationMonitor:
    """Get or create global integration monitor."""
    global _monitor
    if _monitor is None:
        _monitor = IntegrationMonitor(check_interval=check_interval)
    return _monitor
