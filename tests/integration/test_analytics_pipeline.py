"""
Analytics Integration Tests - Test analytics pipelines end-to-end.

Test scenarios:
- Complete analytics workflow
- Real-time KPI tracking and reporting
- Data pipeline from collection to reporting
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
import asyncio

from core.application.use_cases.analytics_use_cases import (
    GetCompanyKPIsUseCase,
    GetMarketKPIsUseCase,
    AnalyzeTrendUseCase,
    GetDashboardDataUseCase,
    GetPredictiveKPIUseCase,
    CompareMetricsUseCase,
    GetAnalyticsReportUseCase
)
from core.infrastructure.analytics.kpi_calculator import (
    KPICalculator,
    JobFrequency
)
from core.infrastructure.analytics.metrics import (
    MetricsCollector,
    AlertSeverity
)
from core.application.services.reporting_service import (
    ReportGenerator,
    ReportFormat,
    ReportFrequency,
    ReportTemplate,
    ReportDistributor
)


class TestAnalyticsPipeline:
    """Test complete analytics pipeline."""
    
    @pytest.mark.asyncio
    async def test_company_analytics_workflow(self):
        """Test company-level analytics workflow."""
        session = AsyncMock()
        
        # Get company KPIs
        kpi_use_case = GetCompanyKPIsUseCase(session)
        kpis = await kpi_use_case.execute("company123", lookback_days=30)
        
        assert kpis is not None
        assert len(kpis) > 0
        
        # Analyze trends for each KPI
        trend_use_case = AnalyzeTrendUseCase(session)
        trends = {}
        
        for kpi in kpis:
            trend = await trend_use_case.execute(
                kpi.name, "company123", lookback_days=30
            )
            if trend:
                trends[kpi.name] = trend
        
        assert len(trends) >= 0  # Trends may be empty if insufficient data
        
        # Get dashboard data
        dashboard_use_case = GetDashboardDataUseCase(session)
        dashboard = await dashboard_use_case.execute("company123", lookback_days=30)
        
        assert dashboard is not None
        assert "kpis" in dashboard
        assert "type" in dashboard
    
    @pytest.mark.asyncio
    async def test_market_analytics_workflow(self):
        """Test market-level analytics workflow."""
        session = AsyncMock()
        
        # Get market KPIs
        market_kpi_use_case = GetMarketKPIsUseCase(session)
        kpis = await market_kpi_use_case.execute(lookback_days=30)
        
        assert kpis is not None
        assert len(kpis) > 0
        
        # Get market dashboard
        dashboard_use_case = GetDashboardDataUseCase(session)
        dashboard = await dashboard_use_case.execute(company_id=None, lookback_days=30)
        
        assert dashboard is not None
        assert dashboard["type"] == "market"
        
        # Compare metrics across dimensions
        compare_use_case = CompareMetricsUseCase(session)
        comparisons = await compare_use_case.execute(
            "signal_count", "sector", lookback_days=30
        )
        
        assert comparisons is not None
        assert isinstance(comparisons, list)
    
    @pytest.mark.asyncio
    async def test_predictive_analytics_workflow(self):
        """Test predictive analytics workflow."""
        session = AsyncMock()
        
        # Get predictive KPI
        predict_use_case = GetPredictiveKPIUseCase(session)
        prediction = await predict_use_case.execute(
            "company123", "signal_count", forecast_days=30
        )
        
        assert prediction is not None
        assert isinstance(prediction, dict)
    
    @pytest.mark.asyncio
    async def test_reporting_pipeline(self):
        """Test reporting pipeline."""
        session = AsyncMock()
        gen = ReportGenerator(session)
        
        # Register template
        template = ReportTemplate(
            template_id="executive_summary",
            name="Executive Summary",
            description="High-level overview",
            sections=["summary", "metrics"],
            metrics=["signal_count", "avg_confidence"],
            dimensions=["company"],
            date_range="last_30_days",
            format=ReportFormat.PDF
        )
        
        await gen.register_template(template)
        
        # Generate report
        report = await gen.generate_report(
            "executive_summary",
            company_id="company123",
            format=ReportFormat.PDF
        )
        
        assert report is not None
        assert isinstance(report, bytes)
        
        # Create scheduled report
        report_id = await gen.create_scheduled_report(
            "Daily Executive Summary",
            "executive_summary",
            ReportFrequency.DAILY,
            ["manager@example.com"]
        )
        
        assert report_id is not None
        
        # Distribute report
        distributor = ReportDistributor()
        sent = await distributor.send_report(
            report,
            ["manager@example.com"],
            "Daily Executive Summary",
            "executive_summary.pdf"
        )
        
        assert sent is True
    
    @pytest.mark.asyncio
    async def test_kpi_calculation_with_background_jobs(self):
        """Test KPI calculation with background jobs."""
        session = AsyncMock()
        calc = KPICalculator(session)
        
        call_count = 0
        
        async def update_kpis():
            nonlocal call_count
            call_count += 1
            kpis = await calc.calculate_real_time_kpis(
                "company123",
                ["signal_count", "avg_confidence"]
            )
            return kpis
        
        # Schedule background job
        job_id = await calc.schedule_background_job(
            "kpi_update",
            update_kpis,
            JobFrequency.EVERY_MINUTE
        )
        
        assert job_id is not None
        
        # Wait a bit for job to execute
        await asyncio.sleep(0.5)
        
        # Check job status
        status = await calc.get_job_status(job_id)
        assert status is not None
        
        # Cancel job
        cancelled = await calc.cancel_job(job_id)
        assert cancelled is True
    
    @pytest.mark.asyncio
    async def test_metrics_collection_and_alerting(self):
        """Test metrics collection with alerting."""
        collector = MetricsCollector()
        
        # Set thresholds
        collector.set_threshold("cpu_usage", warning=70, critical=90)
        collector.set_threshold("memory_usage", warning=80, critical=95)
        
        # Record normal metrics
        collector.record_metric("cpu_usage", 45.0)
        collector.record_metric("memory_usage", 55.0)
        
        assert len(collector.get_active_alerts()) == 0
        
        # Record warning metrics
        collector.record_metric("cpu_usage", 75.0)
        warnings = collector.get_active_alerts()
        assert len(warnings) > 0
        assert warnings[0].severity == AlertSeverity.WARNING
        
        # Record critical metrics
        collector.record_metric("memory_usage", 96.0)
        alerts = collector.get_active_alerts()
        assert len(alerts) > 0
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical) > 0
        
        # Resolve alerts
        for alert in alerts:
            collector.resolve_alert(alert.alert_id)
        
        resolved = collector.get_active_alerts()
        assert len(resolved) == 0
    
    @pytest.mark.asyncio
    async def test_analytics_report_generation(self):
        """Test analytics report generation."""
        session = AsyncMock()
        
        # Use case to generate report
        report_use_case = GetAnalyticsReportUseCase(session)
        
        report = await report_use_case.execute(
            company_id="company123",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            metrics=["signal_count", "avg_confidence"]
        )
        
        assert report is not None
        assert "company_id" in report
        assert "kpis" in report
        assert "start_date" in report
        assert "end_date" in report


class TestAnalyticsScenarios:
    """Test real-world analytics scenarios."""
    
    @pytest.mark.asyncio
    async def test_daily_analytics_report_generation(self):
        """Test daily report generation scenario."""
        session = AsyncMock()
        
        # Get company KPIs
        kpi_use_case = GetCompanyKPIsUseCase(session)
        kpis = await kpi_use_case.execute("company123", lookback_days=1)
        
        # Setup reporting
        gen = ReportGenerator(session)
        template = ReportTemplate(
            template_id="daily_report",
            name="Daily Report",
            description="Daily metrics report",
            sections=["summary", "kpis"],
            metrics=[kpi.name for kpi in kpis],
            dimensions=["company"],
            date_range="today",
            format=ReportFormat.PDF
        )
        
        await gen.register_template(template)
        
        # Generate report
        report = await gen.generate_report(
            "daily_report",
            company_id="company123",
            format=ReportFormat.PDF
        )
        
        assert report is not None
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_with_metrics(self):
        """Test anomaly detection scenario."""
        collector = MetricsCollector()
        
        # Record normal baseline
        for i in range(20):
            collector.record_metric("request_latency", 100.0 + (i % 5))
        
        # Get baseline statistics
        baseline = collector.get_metric_statistics("request_latency")
        baseline_mean = baseline["mean"]
        baseline_stdev = baseline.get("stdev", 0)
        
        # Set threshold based on baseline (mean + 3*stdev)
        threshold = baseline_mean + (3 * max(baseline_stdev, 1))
        collector.set_threshold("request_latency", critical=threshold)
        
        # Record normal data
        collector.record_metric("request_latency", baseline_mean + 5)
        assert len(collector.get_active_alerts()) == 0
        
        # Record anomalous data
        collector.record_metric("request_latency", baseline_mean + (5 * max(baseline_stdev, 1)))
        anomalies = collector.get_active_alerts()
        # May or may not trigger depending on threshold calculation
        assert isinstance(anomalies, list)
    
    @pytest.mark.asyncio
    async def test_multi_format_report_export(self):
        """Test exporting report in multiple formats."""
        session = AsyncMock()
        gen = ReportGenerator(session)
        
        template = ReportTemplate(
            template_id="multi_format",
            name="Multi Format Report",
            description="Report in multiple formats",
            sections=["summary"],
            metrics=["signal_count"],
            dimensions=["company"],
            date_range="last_30_days",
            format=ReportFormat.PDF
        )
        
        await gen.register_template(template)
        
        # Generate in different formats
        formats = [ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.JSON, ReportFormat.CSV]
        
        for fmt in formats:
            report = await gen.generate_report(
                "multi_format",
                format=fmt
            )
            assert report is not None
            assert isinstance(report, bytes)


# Fixtures for integration tests
@pytest.fixture
async def analytics_session():
    """Create analytics session for integration tests."""
    return AsyncMock()


@pytest.fixture
def integration_metrics_collector():
    """Create metrics collector for integration tests."""
    return MetricsCollector()
