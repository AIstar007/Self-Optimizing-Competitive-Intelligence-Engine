"""Comprehensive tests for monitoring infrastructure."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from core.infrastructure.monitoring.metrics import (
    MetricsCollector,
    PerformanceMonitor,
    HealthCheckManager,
    SystemMetricsCollector,
    MetricType,
    HealthStatus,
)
from core.infrastructure.monitoring.logging import (
    StructuredLogger,
    AuditLogger,
    PerformanceLogger,
    AlertManager,
    LogLevel,
    AuditEventType,
    Alert,
    AlertSeverity,
)
from core.infrastructure.deployment.config import (
    ConfigurationManager,
    DeploymentEnvironment,
    DeploymentConfig,
)
from core.infrastructure.deployment.pipeline import (
    DeploymentPipeline,
    DeploymentMonitor,
    CanaryDeployment,
    PipelineStep,
    DeploymentStage,
    DeploymentStatus,
)


# Metrics Tests
class TestMetricsCollector:
    """Tests for metrics collector."""

    def setup_method(self):
        """Setup test environment."""
        self.collector = MetricsCollector()

    def test_increment_counter(self):
        """Test counter increment."""
        self.collector.increment_counter("requests_total", 1.0)
        assert self.collector.get_metric("requests_total") == 1.0

        self.collector.increment_counter("requests_total", 5.0)
        assert self.collector.get_metric("requests_total") == 6.0

    def test_set_gauge(self):
        """Test gauge setting."""
        self.collector.set_gauge("memory_usage", 512.0)
        assert self.collector.get_metric("memory_usage") == 512.0

        self.collector.set_gauge("memory_usage", 620.0)
        assert self.collector.get_metric("memory_usage") == 620.0

    def test_metrics_with_labels(self):
        """Test metrics with labels."""
        labels1 = {"endpoint": "/health"}
        labels2 = {"endpoint": "/metrics"}

        self.collector.increment_counter("api_calls", 1.0, labels1)
        self.collector.increment_counter("api_calls", 2.0, labels2)

        assert self.collector.get_metric("api_calls", labels1) == 1.0
        assert self.collector.get_metric("api_calls", labels2) == 2.0

    def test_get_metrics_history(self):
        """Test metric history retrieval."""
        self.collector.set_gauge("temperature", 20.0)
        self.collector.set_gauge("temperature", 21.0)
        self.collector.set_gauge("temperature", 22.0)

        metrics = self.collector.get_metrics("temperature")
        assert len(metrics) == 3

    def test_reset_metrics(self):
        """Test metrics reset."""
        self.collector.increment_counter("requests", 10.0)
        self.collector.set_gauge("memory", 1024.0)

        self.collector.reset()

        assert len(self.collector.get_all_metrics()) == 0


class TestPerformanceMonitor:
    """Tests for performance monitor."""

    def setup_method(self):
        """Setup test environment."""
        self.monitor = PerformanceMonitor()

    def test_record_operation(self):
        """Test operation recording."""
        self.monitor.record_operation("database_query", 150.0, success=True)
        assert self.monitor.get_statistics("database_query") is not None

    def test_performance_statistics(self):
        """Test performance statistics."""
        for latency in [100, 150, 125, 200, 110]:
            self.monitor.record_operation("query", latency, success=True)

        stats = self.monitor.get_statistics("query")

        assert stats["total"] == 5
        assert stats["successes"] == 5
        assert stats["failures"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["latency_min"] == 100
        assert stats["latency_max"] == 200

    def test_failed_operations(self):
        """Test failed operations tracking."""
        self.monitor.record_operation("query", 100, success=True)
        self.monitor.record_operation("query", 150, success=False, error_message="Timeout")

        stats = self.monitor.get_statistics("query")

        assert stats["successes"] == 1
        assert stats["failures"] == 1
        assert stats["success_rate"] == 0.5

    def test_endpoint_statistics(self):
        """Test endpoint statistics."""
        self.monitor.record_operation(
            "get_data", 100, success=True, endpoint="/api/data", method="GET"
        )
        self.monitor.record_operation(
            "get_data", 150, success=True, endpoint="/api/data", method="GET"
        )

        stats = self.monitor.get_endpoint_statistics("/api/data")

        assert stats["total"] == 2
        assert stats["successes"] == 2


class TestHealthCheckManager:
    """Tests for health check manager."""

    def setup_method(self):
        """Setup test environment."""
        self.manager = HealthCheckManager()

    def test_register_check(self):
        """Test registering health check."""

        def mock_check():
            from core.infrastructure.monitoring.metrics import HealthCheckResult

            return HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message="Database is healthy",
                timestamp=datetime.now(),
                response_time_ms=10.0,
            )

        self.manager.register_check("database", mock_check)
        assert "database" in self.manager.checks

    def test_run_check(self):
        """Test running health check."""

        def mock_check():
            from core.infrastructure.monitoring.metrics import HealthCheckResult

            return HealthCheckResult(
                component="cache",
                status=HealthStatus.HEALTHY,
                message="Cache is healthy",
                timestamp=datetime.now(),
                response_time_ms=5.0,
            )

        self.manager.register_check("cache", mock_check)
        result = self.manager.run_check("cache")

        assert result is not None
        assert result.status == HealthStatus.HEALTHY

    def test_overall_status(self):
        """Test overall health status."""

        def healthy_check():
            from core.infrastructure.monitoring.metrics import HealthCheckResult

            return HealthCheckResult(
                component="service1",
                status=HealthStatus.HEALTHY,
                message="Healthy",
                timestamp=datetime.now(),
                response_time_ms=5.0,
            )

        self.manager.register_check("service1", healthy_check)
        self.manager.run_check("service1")

        assert self.manager.get_overall_status() == HealthStatus.HEALTHY


# Logging Tests
class TestStructuredLogger:
    """Tests for structured logger."""

    def setup_method(self):
        """Setup test environment."""
        self.logger = StructuredLogger("test")

    def test_log_message(self):
        """Test logging message."""
        self.logger.info("Test message", {"key": "value"})
        logs = self.logger.get_logs()

        assert len(logs) > 0
        assert logs[-1].message == "Test message"

    def test_log_levels(self):
        """Test different log levels."""
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")

        logs = self.logger.get_logs()
        assert len(logs) == 4

    def test_log_with_exception(self):
        """Test logging with exception."""
        exc = Exception("Test error")
        self.logger.error("Error occurred", exception=exc)

        logs = self.logger.get_logs(level=LogLevel.ERROR)
        assert len(logs) > 0
        assert logs[-1].exception is not None


class TestAuditLogger:
    """Tests for audit logger."""

    def setup_method(self):
        """Setup test environment."""
        self.logger = AuditLogger()

    def test_log_event(self):
        """Test logging audit event."""
        self.logger.log_event(
            event_type=AuditEventType.RESOURCE_CREATED,
            user_id="user_1",
            resource_type="company",
            resource_id="comp_1",
            action="create",
        )

        logs = self.logger.get_logs()
        assert len(logs) > 0

    def test_filter_by_user(self):
        """Test filtering audit logs by user."""
        self.logger.log_event(
            AuditEventType.DATA_ACCESS, "user_1", "company", "comp_1", "read"
        )
        self.logger.log_event(
            AuditEventType.DATA_ACCESS, "user_2", "company", "comp_2", "read"
        )

        user1_logs = self.logger.get_logs(user_id="user_1")
        assert len(user1_logs) == 1


class TestPerformanceLogger:
    """Tests for performance logger."""

    def setup_method(self):
        """Setup test environment."""
        self.logger = PerformanceLogger()

    def test_log_operation(self):
        """Test logging performance operation."""
        self.logger.log_operation(
            operation="database_query",
            duration_ms=150.0,
            component="database",
            status="success",
        )

        logs = self.logger.get_logs()
        assert len(logs) > 0

    def test_performance_statistics(self):
        """Test performance statistics."""
        for i in range(10):
            self.logger.log_operation(
                operation="query",
                duration_ms=100 + i * 10,
                component="database",
                status="success",
            )

        stats = self.logger.get_statistics(component="database")

        assert stats["total"] == 10
        assert stats["successes"] == 10
        assert stats["failures"] == 0


class TestAlertManager:
    """Tests for alert manager."""

    def setup_method(self):
        """Setup test environment."""
        self.manager = AlertManager()

    def test_register_alert(self):
        """Test registering alert."""
        alert = Alert(
            id="alert_1",
            name="High CPU",
            severity=AlertSeverity.CRITICAL,
            threshold=80.0,
            metric_name="cpu_percent",
            condition="greater_than",
        )

        self.manager.register_alert(alert)
        assert "alert_1" in self.manager.alerts

    def test_check_metric_trigger(self):
        """Test alert triggering."""
        alert = Alert(
            id="alert_1",
            name="High Memory",
            severity=AlertSeverity.WARNING,
            threshold=70.0,
            metric_name="memory_percent",
            condition="greater_than",
        )

        self.manager.register_alert(alert)
        triggered = self.manager.check_metric("memory_percent", 75.0)

        assert triggered is not None
        assert triggered.id == "alert_1"


# Deployment Configuration Tests
class TestConfigurationManager:
    """Tests for configuration manager."""

    def setup_method(self):
        """Setup test environment."""
        self.manager = ConfigurationManager()

    def test_load_from_env(self):
        """Test loading from environment."""
        config = self.manager.load_from_env()

        assert config is not None
        assert config.app_name == "Competitive Intelligence Engine"

    def test_config_validation_production(self):
        """Test configuration validation for production."""
        from core.infrastructure.deployment.config import (
            DatabaseConfig,
            CacheConfig,
            SecurityConfig,
            MonitoringConfig,
            MLConfig,
            APIConfig,
        )

        config = DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            app_name="Test",
            version="1.0.0",
            debug=True,  # Should fail validation
            database=DatabaseConfig("host", 5432, "user", "pass", "db"),
            cache=CacheConfig(),
            security=SecurityConfig("short_key"),  # Too short
            monitoring=MonitoringConfig(),
            ml=MLConfig(),
            api=APIConfig(),
        )

        errors = config.validate()
        assert len(errors) > 0

    def test_set_and_get_secret(self):
        """Test secret management."""
        self.manager.set_secret("api_key", "secret_123")
        assert self.manager.get_secret("api_key") == "secret_123"


# Deployment Pipeline Tests
class TestDeploymentPipeline:
    """Tests for deployment pipeline."""

    def setup_method(self):
        """Setup test environment."""
        self.pipeline = DeploymentPipeline()

    def test_add_step(self):
        """Test adding pipeline step."""
        step = PipelineStep(
            name="test_step",
            stage=DeploymentStage.BUILD,
            command="echo 'test'",
        )

        self.pipeline.add_step(step)
        assert len(self.pipeline.steps) == 1

    def test_trigger_deployment(self):
        """Test triggering deployment."""
        deployment = self.pipeline.trigger_deployment(
            deployment_id="deploy_1",
            version="1.0.0",
            environment="staging",
            triggered_by="user_1",
        )

        assert deployment.deployment_id == "deploy_1"
        assert deployment.status == DeploymentStatus.PENDING

    def test_get_deployment(self):
        """Test retrieving deployment."""
        self.pipeline.trigger_deployment("deploy_1", "1.0.0", "staging", "user_1")

        deployment = self.pipeline.get_deployment("deploy_1")
        assert deployment is not None


class TestDeploymentMonitor:
    """Tests for deployment monitor."""

    def setup_method(self):
        """Setup test environment."""
        self.monitor = DeploymentMonitor()

    def test_register_health_check(self):
        """Test registering health check."""

        def mock_check():
            return True

        self.monitor.register_health_check("database", mock_check)
        assert "database" in self.monitor.health_checks

    def test_run_health_checks(self):
        """Test running health checks."""
        self.monitor.register_health_check("service1", lambda: True)
        self.monitor.register_health_check("service2", lambda: True)

        results = self.monitor.run_health_checks()
        assert len(results) == 2
        assert all(results.values())


class TestCanaryDeployment:
    """Tests for canary deployment."""

    def setup_method(self):
        """Setup test environment."""
        self.canary = CanaryDeployment()

    def test_start_canary(self):
        """Test starting canary."""
        self.canary.start_canary("deploy_1", initial_traffic_percentage=5.0)
        assert self.canary.get_traffic_percentage("deploy_1") == 5.0

    def test_increment_canary(self):
        """Test incrementing canary traffic."""
        self.canary.start_canary("deploy_1", initial_traffic_percentage=5.0)
        self.canary.increment_canary("deploy_1", 10.0)

        assert self.canary.get_traffic_percentage("deploy_1") == 15.0

    def test_complete_canary(self):
        """Test canary completion."""
        self.canary.start_canary("deploy_1", initial_traffic_percentage=95.0)
        self.canary.increment_canary("deploy_1", 10.0)

        # Should be completed (100%)
        percentage = self.canary.get_traffic_percentage("deploy_1")
        assert percentage is None  # Removed after completion


# Integration Tests
class TestMonitoringIntegration:
    """Integration tests for monitoring."""

    def test_metrics_and_performance_together(self):
        """Test metrics and performance monitoring together."""
        metrics = MetricsCollector()
        monitor = PerformanceMonitor()

        # Record metrics
        metrics.set_gauge("requests_active", 10.0)

        # Record performance
        monitor.record_operation("query", 150.0, success=True)

        # Verify both work
        assert metrics.get_metric("requests_active") == 10.0
        stats = monitor.get_statistics("query")
        assert stats["total"] == 1

    def test_logging_and_alerts_together(self):
        """Test logging and alerts together."""
        logger = StructuredLogger()
        alert_mgr = AlertManager()

        # Register alert
        alert = Alert(
            id="alert_1",
            name="High Errors",
            severity=AlertSeverity.CRITICAL,
            threshold=10.0,
            metric_name="error_rate",
            condition="greater_than",
        )
        alert_mgr.register_alert(alert)

        # Log error
        logger.error("Error occurred", {"code": 500})

        # Check alert
        triggered = alert_mgr.check_metric("error_rate", 15.0)
        assert triggered is not None

    def test_deployment_with_monitoring(self):
        """Test deployment with monitoring."""
        pipeline = DeploymentPipeline()
        monitor = DeploymentMonitor()

        # Register health check
        monitor.register_health_check("database", lambda: True)
        monitor.register_health_check("cache", lambda: True)

        # Trigger deployment
        deployment = pipeline.trigger_deployment(
            "deploy_1", "1.0.0", "staging", "user_1"
        )

        # Verify deployment
        assert deployment is not None
        results = monitor.run_health_checks()
        assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
