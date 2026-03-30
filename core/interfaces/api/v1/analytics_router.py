"""
Analytics Router - FastAPI endpoints for analytics and dashboard data.

Endpoints:
- /api/v1/analytics/kpis - Get KPI metrics
- /api/v1/analytics/trends - Analyze trends
- /api/v1/analytics/dashboard - Get dashboard data
- /api/v1/analytics/predictions - Get predictive KPIs
- /api/v1/analytics/reports - Get analytics reports
- /api/v1/analytics/compare - Compare metrics
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.application.use_cases.analytics_use_cases import (
    GetCompanyKPIsUseCase,
    GetMarketKPIsUseCase,
    AnalyzeTrendUseCase,
    GetDashboardDataUseCase,
    GetPredictiveKPIUseCase,
    CompareMetricsUseCase,
    GetAnalyticsReportUseCase,
)
from core.infrastructure.monitoring import logger, monitor


router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


async def get_db() -> AsyncSession:
    """Get database session."""
    # Placeholder - would use actual session management
    pass


@router.get("/kpis/company/{company_id}")
@monitor.timing
async def get_company_kpis(
    company_id: str,
    lookback_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get KPI metrics for a specific company.
    
    Args:
        company_id: Company identifier
        lookback_days: Number of days to look back (default: 30)
        
    Returns:
        Dictionary with KPI metrics
    """
    try:
        use_case = GetCompanyKPIsUseCase(db)
        kpis = await use_case.execute(company_id, lookback_days)
        
        return {
            "company_id": company_id,
            "lookback_days": lookback_days,
            "kpis": [kpi.to_dict() for kpi in kpis],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching company KPIs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch KPIs"
        )


@router.get("/kpis/market")
@monitor.timing
async def get_market_kpis(
    lookback_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get market-level KPI metrics.
    
    Args:
        lookback_days: Number of days to look back (default: 30)
        
    Returns:
        Dictionary with market KPI metrics
    """
    try:
        use_case = GetMarketKPIsUseCase(db)
        kpis = await use_case.execute(lookback_days)
        
        return {
            "type": "market",
            "lookback_days": lookback_days,
            "kpis": [kpi.to_dict() for kpi in kpis],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching market KPIs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market KPIs"
        )


@router.get("/trends/{metric_name}")
@monitor.timing
async def analyze_trend(
    metric_name: str,
    company_id: Optional[str] = Query(None),
    lookback_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Analyze trend for a specific metric.
    
    Args:
        metric_name: Name of metric to analyze
        company_id: Optional company identifier (if None, market-level)
        lookback_days: Number of days to analyze (default: 30)
        
    Returns:
        Dictionary with trend analysis
    """
    try:
        use_case = AnalyzeTrendUseCase(db)
        trend = await use_case.execute(metric_name, company_id, lookback_days)
        
        if not trend:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trend data available for {metric_name}"
            )
        
        return {
            "metric_name": trend.metric_name,
            "direction": trend.direction,
            "magnitude": trend.magnitude,
            "confidence": trend.confidence,
            "period_days": trend.period_days,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze trend"
        )


@router.get("/dashboard")
@monitor.timing
async def get_dashboard(
    company_id: Optional[str] = Query(None),
    lookback_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get comprehensive dashboard data.
    
    Args:
        company_id: Optional company identifier (if None, market-level)
        lookback_days: Number of days to include (default: 30)
        
    Returns:
        Dictionary with complete dashboard data
    """
    try:
        use_case = GetDashboardDataUseCase(db)
        dashboard_data = await use_case.execute(company_id, lookback_days)
        
        return {
            "type": dashboard_data.get("type", "market"),
            "company_id": company_id,
            "lookback_days": lookback_days,
            "data": dashboard_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data"
        )


@router.get("/predictions/{company_id}/{kpi_name}")
@monitor.timing
async def get_predictive_kpi(
    company_id: str,
    kpi_name: str,
    forecast_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get predictive KPI with forecasting.
    
    Args:
        company_id: Company identifier
        kpi_name: Name of KPI to forecast
        forecast_days: Number of days to forecast (default: 30)
        
    Returns:
        Dictionary with forecast and confidence intervals
    """
    try:
        use_case = GetPredictiveKPIUseCase(db)
        prediction = await use_case.execute(company_id, kpi_name, forecast_days)
        
        if "error" in prediction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=prediction.get("error", "Unable to generate prediction")
            )
        
        return {
            "company_id": company_id,
            "kpi_name": kpi_name,
            "forecast_days": forecast_days,
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate prediction"
        )


@router.get("/compare/{metric_name}")
@monitor.timing
async def compare_metrics(
    metric_name: str,
    dimension: str = Query("company"),
    lookback_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Compare metrics across multiple entities.
    
    Args:
        metric_name: Metric to compare
        dimension: Dimension to compare across (e.g., "company", "sector")
        lookback_days: Number of days to include (default: 30)
        
    Returns:
        Dictionary with metric comparison
    """
    try:
        use_case = CompareMetricsUseCase(db)
        aggregates = await use_case.execute(metric_name, dimension, lookback_days)
        
        return {
            "metric_name": metric_name,
            "dimension": dimension,
            "lookback_days": lookback_days,
            "comparisons": [
                {
                    "dimension_value": agg.dimension,
                    "value": agg.value,
                    "count": agg.count,
                    "average": agg.average,
                    "min": agg.min_value,
                    "max": agg.max_value,
                    "std_dev": agg.std_dev
                }
                for agg in aggregates
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error comparing metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare metrics"
        )


@router.get("/reports/{report_type}")
@monitor.timing
async def get_analytics_report(
    report_type: str,
    company_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get analytics report.
    
    Args:
        report_type: Type of report (daily, weekly, monthly)
        company_id: Optional company identifier
        start_date: Start date for report (default: 30 days ago)
        end_date: End date for report (default: today)
        
    Returns:
        Dictionary with analytics report
    """
    try:
        if report_type not in ["daily", "weekly", "monthly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report type: {report_type}"
            )
        
        if not end_date:
            end_date = datetime.utcnow()
        
        if not start_date:
            if report_type == "daily":
                start_date = end_date - timedelta(days=1)
            elif report_type == "weekly":
                start_date = end_date - timedelta(weeks=1)
            else:  # monthly
                start_date = end_date - timedelta(days=30)
        
        use_case = GetAnalyticsReportUseCase(db)
        report = await use_case.execute(company_id, start_date, end_date)
        
        return {
            "report_type": report_type,
            "company_id": company_id,
            "report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/health")
@monitor.timing
async def analytics_health(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Check analytics service health.
    
    Returns:
        Dictionary with health status
    """
    try:
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service unavailable"
        )


# Export router
__all__ = ["router"]
