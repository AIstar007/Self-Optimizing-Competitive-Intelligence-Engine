"""
Analytics Use Cases - Business logic for analytics operations.

Provides use cases for:
- Dashboard data retrieval
- KPI tracking and reporting
- Trend analysis
- Predictive analytics
- Performance metrics
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.application.services.analytics_service import (
    AnalyticsService,
    KPIMetric,
    TrendAnalysis,
    AggregateMetric
)
from core.infrastructure.monitoring import logger as structured_logger, monitor


logger = logging.getLogger(__name__)


class GetCompanyKPIsUseCase:
    """Get KPI metrics for a specific company."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(
        self,
        company_id: str,
        lookback_days: int = 30
    ) -> List[KPIMetric]:
        """
        Execute use case to get company KPIs.
        
        Args:
            company_id: Company identifier
            lookback_days: Number of days to analyze
            
        Returns:
            List of KPI metrics
        """
        try:
            structured_logger.info(
                "Getting KPIs for company",
                {"company_id": company_id, "lookback_days": lookback_days}
            )
            
            kpis = await self.analytics.calculate_signal_kpis(
                company_id, lookback_days
            )
            
            structured_logger.info(
                "Retrieved KPIs",
                {"company_id": company_id, "kpi_count": len(kpis)}
            )
            
            return kpis
            
        except Exception as e:
            structured_logger.error(
                "Error getting company KPIs",
                {"company_id": company_id, "error": str(e)}
            )
            raise


class GetMarketKPIsUseCase:
    """Get market-level KPI metrics."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(self, lookback_days: int = 30) -> List[KPIMetric]:
        """
        Execute use case to get market KPIs.
        
        Args:
            lookback_days: Number of days to analyze
            
        Returns:
            List of market KPI metrics
        """
        try:
            structured_logger.info(
                "Getting market-level KPIs",
                {"lookback_days": lookback_days}
            )
            
            kpis = await self.analytics.calculate_market_event_kpis(lookback_days)
            
            structured_logger.info(
                "Retrieved market KPIs",
                {"kpi_count": len(kpis)}
            )
            
            return kpis
            
        except Exception as e:
            structured_logger.error(
                "Error getting market KPIs",
                {"error": str(e)}
            )
            raise


class AnalyzeTrendUseCase:
    """Analyze trends for specific metrics."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(
        self,
        metric_name: str,
        company_id: Optional[str] = None,
        lookback_days: int = 30
    ) -> Optional[TrendAnalysis]:
        """
        Execute use case to analyze trend.
        
        Args:
            metric_name: Name of metric to analyze
            company_id: Optional company identifier
            lookback_days: Number of days to analyze
            
        Returns:
            Trend analysis result
        """
        try:
            structured_logger.info(
                "Analyzing trend",
                {
                    "metric_name": metric_name,
                    "company_id": company_id,
                    "lookback_days": lookback_days
                }
            )
            
            trend = await self.analytics.analyze_trend(
                metric_name, company_id, lookback_days
            )
            
            if trend:
                structured_logger.info(
                    "Trend analysis complete",
                    {
                        "metric_name": metric_name,
                        "direction": trend.direction,
                        "confidence": trend.confidence
                    }
                )
            else:
                structured_logger.warning(
                    "No trend analysis available",
                    {"metric_name": metric_name}
                )
            
            return trend
            
        except Exception as e:
            structured_logger.error(
                "Error analyzing trend",
                {"metric_name": metric_name, "error": str(e)}
            )
            raise


class GetDashboardDataUseCase:
    """Get comprehensive dashboard data."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(
        self,
        company_id: Optional[str] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Execute use case to get dashboard data.
        
        Args:
            company_id: Optional company identifier (if None, market-level)
            lookback_days: Number of days to include
            
        Returns:
            Dictionary with all dashboard data
        """
        try:
            structured_logger.info(
                "Building dashboard data",
                {"company_id": company_id, "lookback_days": lookback_days}
            )
            
            dashboard_data = {}
            
            # Get KPIs
            if company_id:
                dashboard_data["kpis"] = await self.analytics.calculate_signal_kpis(
                    company_id, lookback_days
                )
                dashboard_data["type"] = "company"
            else:
                dashboard_data["kpis"] = await self.analytics.calculate_market_event_kpis(
                    lookback_days
                )
                dashboard_data["type"] = "market"
            
            # Convert KPIs to dict format
            dashboard_data["kpis"] = [kpi.to_dict() for kpi in dashboard_data["kpis"]]
            
            # Get trends for key metrics
            trends = {}
            key_metrics = ["signal_count", "avg_confidence", "signal_detection_rate"]
            
            for metric in key_metrics:
                trend = await self.analytics.analyze_trend(metric, company_id, lookback_days)
                if trend:
                    trends[metric] = {
                        "direction": trend.direction,
                        "magnitude": trend.magnitude,
                        "confidence": trend.confidence
                    }
            
            dashboard_data["trends"] = trends
            
            # Get aggregates if market-level
            if not company_id:
                dashboard_data["aggregates"] = await self.analytics.get_aggregate_metrics(
                    "sector", "signal_count", lookback_days
                )
                dashboard_data["aggregates"] = [
                    {
                        "dimension": agg.dimension,
                        "metric_name": agg.metric_name,
                        "value": agg.value,
                        "count": agg.count,
                        "average": agg.average
                    }
                    for agg in dashboard_data["aggregates"]
                ]
            
            structured_logger.info(
                "Dashboard data prepared",
                {
                    "company_id": company_id,
                    "kpi_count": len(dashboard_data.get("kpis", [])),
                    "trend_count": len(trends)
                }
            )
            
            return dashboard_data
            
        except Exception as e:
            structured_logger.error(
                "Error building dashboard data",
                {"company_id": company_id, "error": str(e)}
            )
            raise


class GetPredictiveKPIUseCase:
    """Get predictive KPI with forecasting."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(
        self,
        company_id: str,
        kpi_name: str,
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """
        Execute use case to get predictive KPI.
        
        Args:
            company_id: Company identifier
            kpi_name: Name of KPI to forecast
            forecast_days: Number of days to forecast
            
        Returns:
            Dictionary with forecast and confidence
        """
        try:
            structured_logger.info(
                "Calculating predictive KPI",
                {
                    "company_id": company_id,
                    "kpi_name": kpi_name,
                    "forecast_days": forecast_days
                }
            )
            
            prediction = await self.analytics.calculate_predictive_kpi(
                company_id, kpi_name, forecast_days
            )
            
            structured_logger.info(
                "Predictive KPI calculated",
                {
                    "company_id": company_id,
                    "kpi_name": kpi_name,
                    "forecast_days": forecast_days
                }
            )
            
            return prediction
            
        except Exception as e:
            structured_logger.error(
                "Error calculating predictive KPI",
                {
                    "company_id": company_id,
                    "kpi_name": kpi_name,
                    "error": str(e)
                }
            )
            raise


class CompareMetricsUseCase:
    """Compare metrics across multiple entities."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(
        self,
        metric_name: str,
        dimension: str,
        lookback_days: int = 30
    ) -> List[AggregateMetric]:
        """
        Execute use case to compare metrics.
        
        Args:
            metric_name: Metric to compare
            dimension: Dimension to compare across
            lookback_days: Number of days to include
            
        Returns:
            List of aggregated metrics for comparison
        """
        try:
            structured_logger.info(
                "Comparing metrics",
                {
                    "metric_name": metric_name,
                    "dimension": dimension,
                    "lookback_days": lookback_days
                }
            )
            
            aggregates = await self.analytics.get_aggregate_metrics(
                dimension, metric_name, lookback_days
            )
            
            structured_logger.info(
                "Metrics compared",
                {
                    "metric_name": metric_name,
                    "dimension": dimension,
                    "count": len(aggregates)
                }
            )
            
            return aggregates
            
        except Exception as e:
            structured_logger.error(
                "Error comparing metrics",
                {
                    "metric_name": metric_name,
                    "dimension": dimension,
                    "error": str(e)
                }
            )
            raise


class GetAnalyticsReportUseCase:
    """Generate comprehensive analytics report."""
    
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)
        self.session = session
    
    @monitor.timing
    async def execute(
        self,
        company_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute use case to generate analytics report.
        
        Args:
            company_id: Optional company identifier
            start_date: Start date for report
            end_date: End date for report
            metrics: List of metrics to include
            
        Returns:
            Dictionary with comprehensive analytics report
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            structured_logger.info(
                "Generating analytics report",
                {
                    "company_id": company_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "metric_count": len(metrics) if metrics else 0
                }
            )
            
            report = {
                "company_id": company_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "metrics": {}
            }
            
            # Add KPIs
            if company_id:
                kpis = await self.analytics.calculate_signal_kpis(
                    company_id,
                    (end_date - start_date).days
                )
            else:
                kpis = await self.analytics.calculate_market_event_kpis(
                    (end_date - start_date).days
                )
            
            report["kpis"] = [kpi.to_dict() for kpi in kpis]
            
            structured_logger.info(
                "Analytics report generated",
                {
                    "company_id": company_id,
                    "kpi_count": len(kpis)
                }
            )
            
            return report
            
        except Exception as e:
            structured_logger.error(
                "Error generating analytics report",
                {"company_id": company_id, "error": str(e)}
            )
            raise
