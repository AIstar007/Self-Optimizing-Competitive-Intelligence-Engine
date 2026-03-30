"""
Analytics Unit Tests - Test analytics service components.

Test coverage:
- KPI calculations
- Trend analysis
- Metric collection
- Alert generation
- Report generation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from core.application.services.analytics_service import (
    AnalyticsService,
    KPIMetric,
    TrendAnalysis,
    AggregateMetric
)
from core.infrastructure.analytics.kpi_calculator import (
    KPICalculator,
    JobFrequency,
    JobStatus
)
from core.infrastructure.analytics.metrics import (
    MetricsCollector,
    MetricType,
    AlertSeverity,
    MetricPoint,
    Alert
)
from core.application.services.reporting_service import (
    ReportGenerator,
    ReportFormat,
    ReportFrequency,
    ReportTemplate,
    ReportDistributor
)


class TestAnalyticsService:
    """Test analytics service."""
    
    @pytest.mark.asyncio
    async def test_calculate_signal_kpis(self):
        """Test KPI calculation."""
        session = AsyncMock()
        service = AnalyticsService(session)
        
        kpis = await service.calculate_signal_kpis("company123", lookback_days=30)
        
        assert kpis is not None
        assert len(kpis) > 0
        assert all(isinstance(kpi, KPIMetric) for kpi in kpis)
        assert all(hasattr(kpi, 'name') for kpi in kpis)
        assert all(hasattr(kpi, 'value') for kpi in kpis)
    
    @pytest.mark.asyncio
    async def test_calculate_market_event_kpis(self):
        """Test market event KPI calculation."""
        session = AsyncMock()
        service = AnalyticsService(session)
        
        kpis = await service.calculate_market_event_kpis(lookback_days=30)
        
        assert kpis is not None
        assert len(kpis) > 0
        assert all(isinstance(kpi, KPIMetric) for kpi in kpis)
    
    @pytest.mark.asyncio
    async def test_analyze_trend(self):
        """Test trend analysis."""
        session = AsyncMock()
        service = AnalyticsService(session)
        
        trend = await service.analyze_trend("signal_count", "company123", lookback_days=30)
        
        assert trend is None or isinstance(trend, TrendAnalysis)
        if trend:
            assert trend.direction in ["up", "down", "stable"]
            assert 0 <= trend.confidence <= 1
            assert trend.magnitude >= 0
    
    @pytest.mark.asyncio
    async def test_get_aggregate_metrics(self):
        """Test metric aggregation."""
        session = AsyncMock()
        service = AnalyticsService(session)
        
        aggregates = await service.get_aggregate_metrics(
            "company", "signal_count", lookback_days=30
        )
        
        assert aggregates is not None
        assert isinstance(aggregates, list)
        if aggregates:
            assert all(isinstance(agg, AggregateMetric) for agg in aggregates)
    
    @pytest.mark.asyncio
    async def test_calculate_predictive_kpi(self):
        """Test predictive KPI calculation."""
        session = AsyncMock()
        service = AnalyticsService(session)
        
        prediction = await service.calculate_predictive_kpi(
            "company123", "signal_count", forecast_days=30
        )
        
        assert prediction is not None
        assert isinstance(prediction, dict)
        assert "kpi_name" in prediction or "error" in prediction


class TestKPICalculator:
    """Test KPI calculator."""
    
    @pytest.mark.asyncio
    async def test_calculate_real_time_kpis(self):
        """Test real-time KPI calculation."""
        session = AsyncMock()
        calc = KPICalculator(session)
        
        kpis = await calc.calculate_real_time_kpis(
            "company123",
            ["signal_count", "avg_confidence"]
        )
        
        assert kpis is not None
        assert isinstance(kpis, dict)
        assert all(isinstance(v, dict) for v in kpis.values())
    
    @pytest.mark.asyncio
    async def test_schedule_background_job(self):
        """Test background job scheduling."""
        session = AsyncMock()
        calc = KPICalculator(session)
        
        async def dummy_job():
            return {"result": "success"}
        
        job_id = await calc.schedule_background_job(
            "test_job",
            dummy_job,
            JobFrequency.EVERY_MINUTE
        )
        
        assert job_id is not None
        assert job_id in calc.jobs
        
        # Cleanup
        await calc.cancel_job(job_id)
    
    @pytest.mark.asyncio
    async def test_execute_job_once(self):
        """Test one-time job execution."""
        session = AsyncMock()
        calc = KPICalculator(session)
        
        async def dummy_job():
            return {"result": "success"}
        
        result = await calc.execute_job_once("test_job", dummy_job)
        
        assert result is not None
        assert result["status"] in ["completed", "failed"]
        assert "job_id" in result
    
    @pytest.mark.asyncio
    async def test_get_job_status(self):
        """Test getting job status."""
        session = AsyncMock()
        calc = KPICalculator(session)
        
        async def dummy_job():
            return {"result": "success"}
        
        job_id = await calc.schedule_background_job(
            "test_job",
            dummy_job,
            JobFrequency.EVERY_MINUTE
        )
        
        status = await calc.get_job_status(job_id)
        
        assert status is not None
        assert status["job_id"] == job_id
        assert status["job_name"] == "test_job"
        
        # Cleanup
        await calc.cancel_job(job_id)
    
    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Test job cancellation."""
        session = AsyncMock()
        calc = KPICalculator(session)
        
        async def dummy_job():
            return {"result": "success"}
        
        job_id = await calc.schedule_background_job(
            "test_job",
            dummy_job,
            JobFrequency.EVERY_MINUTE
        )
        
        cancelled = await calc.cancel_job(job_id)
        
        assert cancelled is True
        assert job_id not in calc.running_tasks


class TestMetricsCollector:
    """Test metrics collector."""
    
    def test_record_metric(self):
        """Test metric recording."""
        collector = MetricsCollector()
        
        collector.record_metric("test_metric", 42.0, unit="count")
        
        assert "test_metric" in collector.metrics
        assert len(collector.metrics["test_metric"]) == 1
        assert collector.metrics["test_metric"][0].value == 42.0
    
    def test_get_metric_history(self):
        """Test getting metric history."""
        collector = MetricsCollector()
        
        # Record metrics
        for i in range(10):
            collector.record_metric("test_metric", float(i))
        
        history = collector.get_metric_history("test_metric", lookback_minutes=60)
        
        assert history is not None
        assert len(history) == 10
        assert all(isinstance(p, MetricPoint) for p in history)
    
    def test_get_metric_statistics(self):
        """Test metric statistics calculation."""
        collector = MetricsCollector()
        
        # Record metrics
        values = [10, 20, 30, 40, 50]
        for v in values:
            collector.record_metric("test_metric", float(v))
        
        stats = collector.get_metric_statistics("test_metric")
        
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0
    
    def test_set_threshold(self):
        """Test setting metric thresholds."""
        collector = MetricsCollector()
        
        collector.set_threshold("test_metric", warning=80, critical=95)
        
        assert "test_metric" in collector.thresholds
        assert collector.thresholds["test_metric"]["warning"] == 80
        assert collector.thresholds["test_metric"]["critical"] == 95
    
    def test_create_alert(self):
        """Test alert creation."""
        collector = MetricsCollector()
        
        collector.set_threshold("test_metric", warning=50, critical=100)
        collector.record_metric("test_metric", 110.0)  # Exceeds critical
        
        alerts = collector.get_active_alerts()
        
        assert len(alerts) > 0
        assert alerts[0].metric_name == "test_metric"
        assert alerts[0].severity == AlertSeverity.CRITICAL
    
    def test_resolve_alert(self):
        """Test alert resolution."""
        collector = MetricsCollector()
        
        collector.set_threshold("test_metric", warning=50, critical=100)
        collector.record_metric("test_metric", 110.0)
        
        alerts = collector.get_active_alerts()
        alert_id = alerts[0].alert_id
        
        resolved = collector.resolve_alert(alert_id)
        
        assert resolved is True
        active_alerts = collector.get_active_alerts()
        assert len(active_alerts) == 0
    
    def test_get_metric_summary(self):
        """Test getting metrics summary."""
        collector = MetricsCollector()
        
        collector.record_metric("metric1", 10.0)
        collector.record_metric("metric2", 20.0)
        
        summary = collector.get_metric_summary()
        
        assert summary["total_metrics"] == 2
        assert summary["timestamp"] is not None


class TestReportGenerator:
    """Test report generator."""
    
    @pytest.mark.asyncio
    async def test_register_template(self):
        """Test template registration."""
        session = AsyncMock()
        gen = ReportGenerator(session)
        
        template = ReportTemplate(
            template_id="test_template",
            name="Test Report",
            description="A test report",
            sections=["summary", "metrics"],
            metrics=["signal_count"],
            dimensions=["company"],
            date_range="last_30_days",
            format=ReportFormat.PDF
        )
        
        await gen.register_template(template)
        
        assert "test_template" in gen.templates
        assert gen.templates["test_template"].name == "Test Report"
    
    @pytest.mark.asyncio
    async def test_get_template_list(self):
        """Test getting template list."""
        session = AsyncMock()
        gen = ReportGenerator(session)
        
        template = ReportTemplate(
            template_id="test_template",
            name="Test Report",
            description="A test report",
            sections=["summary"],
            metrics=["signal_count"],
            dimensions=["company"],
            date_range="last_30_days",
            format=ReportFormat.PDF
        )
        
        await gen.register_template(template)
        templates = await gen.get_template_list()
        
        assert len(templates) > 0
        assert any(t["template_id"] == "test_template" for t in templates)
    
    @pytest.mark.asyncio
    async def test_create_scheduled_report(self):
        """Test creating scheduled report."""
        session = AsyncMock()
        gen = ReportGenerator(session)
        
        report_id = await gen.create_scheduled_report(
            "Daily Report",
            "test_template",
            ReportFrequency.DAILY,
            ["user@example.com"]
        )
        
        assert report_id is not None
        assert report_id in gen.scheduled_reports
    
    @pytest.mark.asyncio
    async def test_generate_report_json(self):
        """Test generating JSON report."""
        session = AsyncMock()
        gen = ReportGenerator(session)
        
        template = ReportTemplate(
            template_id="test_template",
            name="Test Report",
            description="A test report",
            sections=["summary"],
            metrics=["signal_count"],
            dimensions=["company"],
            date_range="last_30_days",
            format=ReportFormat.JSON
        )
        
        await gen.register_template(template)
        
        report = await gen.generate_report(
            "test_template",
            format=ReportFormat.JSON
        )
        
        assert report is not None
        assert isinstance(report, bytes)


class TestReportDistributor:
    """Test report distributor."""
    
    @pytest.mark.asyncio
    async def test_send_report(self):
        """Test sending report."""
        distributor = ReportDistributor()
        
        report_data = b"Test report content"
        recipients = ["user@example.com"]
        
        sent = await distributor.send_report(
            report_data,
            recipients,
            "Daily Report",
            "report.pdf"
        )
        
        assert sent is True
    
    @pytest.mark.asyncio
    async def test_upload_report_to_storage(self):
        """Test uploading report to storage."""
        distributor = ReportDistributor()
        
        report_data = b"Test report content"
        
        url = await distributor.upload_report_to_storage(
            report_data,
            "reports/test_report.pdf"
        )
        
        assert url is not None
        assert "storage.example.com" in url


# Integration test fixtures
@pytest.fixture
async def analytics_service():
    """Create analytics service for testing."""
    session = AsyncMock()
    return AnalyticsService(session)


@pytest.fixture
def metrics_collector():
    """Create metrics collector for testing."""
    return MetricsCollector()


@pytest.fixture
async def report_generator():
    """Create report generator for testing."""
    session = AsyncMock()
    return ReportGenerator(session)
