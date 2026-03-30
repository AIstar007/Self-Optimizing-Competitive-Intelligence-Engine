"""
Analytics Service - Real-time data processing, KPI calculations, trend analysis.

Provides comprehensive analytics capabilities including:
- KPI calculations and tracking
- Trend analysis and forecasting
- Real-time metrics aggregation
- Performance indicators
- Time-series data analysis
- Predictive analytics
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from statistics import mean, stdev
import logging
from dataclasses import dataclass, asdict
import asyncio

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.sql import text

from core.domain.entities.signal import Signal
from core.domain.entities.market_event import MarketEvent
from core.domain.entities.report import Report
from core.domain.entities.company import Company
from core.domain.value_objects.confidence import Confidence
from core.domain.value_objects.timestamp import Timestamp
from core.infrastructure.monitoring import logger, monitor


logger_instance = logging.getLogger(__name__)


@dataclass
class KPIMetric:
    """Key Performance Indicator metric."""
    
    name: str
    value: float
    unit: str
    trend: str  # "up", "down", "stable"
    change_percent: float
    threshold: float
    status: str  # "healthy", "warning", "critical"
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    
    metric_name: str
    direction: str  # "up", "down", "stable"
    magnitude: float
    confidence: float
    period_days: int
    data_points: List[Tuple[datetime, float]]
    forecast: List[Tuple[datetime, float]]


@dataclass
class AggregateMetric:
    """Aggregated metric across multiple dimensions."""
    
    dimension: str
    metric_name: str
    value: float
    count: int
    average: float
    min_value: float
    max_value: float
    std_dev: float


class AnalyticsService:
    """Service for advanced analytics operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize analytics service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.logger = logger_instance
        
    @monitor.timing
    async def calculate_signal_kpis(
        self,
        company_id: str,
        lookback_days: int = 30
    ) -> List[KPIMetric]:
        """
        Calculate key performance indicators for signals.
        
        Args:
            company_id: Company identifier
            lookback_days: Number of days to look back
            
        Returns:
            List of KPI metrics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Calculate metrics
            metrics = []
            
            # 1. Total signals KPI
            total_signals = await self._count_signals(company_id, start_date, end_date)
            signal_trend = await self._calculate_trend(
                "signal_count", company_id, lookback_days
            )
            
            metrics.append(KPIMetric(
                name="total_signals",
                value=total_signals,
                unit="count",
                trend=signal_trend["direction"],
                change_percent=signal_trend["change_percent"],
                threshold=100,
                status=self._get_status(total_signals, 50, 100, 150),
                timestamp=end_date
            ))
            
            # 2. Average signal confidence KPI
            avg_confidence = await self._calculate_avg_confidence(
                company_id, start_date, end_date
            )
            
            metrics.append(KPIMetric(
                name="avg_confidence",
                value=avg_confidence,
                unit="percent",
                trend="stable",
                change_percent=0,
                threshold=0.7,
                status=self._get_status(avg_confidence, 0.5, 0.7, 0.9),
                timestamp=end_date
            ))
            
            # 3. Signal detection rate KPI
            signal_rate = await self._calculate_signal_rate(
                company_id, lookback_days
            )
            
            metrics.append(KPIMetric(
                name="signal_detection_rate",
                value=signal_rate,
                unit="signals/day",
                trend="stable",
                change_percent=0,
                threshold=3.0,
                status=self._get_status(signal_rate, 1.0, 3.0, 5.0),
                timestamp=end_date
            ))
            
            # 4. High-confidence signals ratio
            high_conf_ratio = await self._calculate_high_confidence_ratio(
                company_id, start_date, end_date
            )
            
            metrics.append(KPIMetric(
                name="high_confidence_ratio",
                value=high_conf_ratio,
                unit="percent",
                trend="stable",
                change_percent=0,
                threshold=0.6,
                status=self._get_status(high_conf_ratio, 0.3, 0.6, 0.8),
                timestamp=end_date
            ))
            
            self.logger.info(f"Calculated {len(metrics)} KPI metrics for company {company_id}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating signal KPIs: {e}")
            raise
    
    @monitor.timing
    async def calculate_market_event_kpis(
        self,
        lookback_days: int = 30
    ) -> List[KPIMetric]:
        """
        Calculate KPIs for market events.
        
        Args:
            lookback_days: Number of days to look back
            
        Returns:
            List of KPI metrics
        """
        try:
            metrics = []
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # 1. Total events KPI
            total_events = await self._count_events(start_date, end_date)
            
            metrics.append(KPIMetric(
                name="total_market_events",
                value=total_events,
                unit="count",
                trend="stable",
                change_percent=0,
                threshold=50,
                status=self._get_status(total_events, 20, 50, 100),
                timestamp=end_date
            ))
            
            # 2. Event severity distribution
            high_severity = await self._count_events_by_severity(
                start_date, end_date, "high"
            )
            severity_ratio = high_severity / max(total_events, 1)
            
            metrics.append(KPIMetric(
                name="high_severity_event_ratio",
                value=severity_ratio,
                unit="percent",
                trend="stable",
                change_percent=0,
                threshold=0.3,
                status=self._get_status(severity_ratio, 0.1, 0.3, 0.5),
                timestamp=end_date
            ))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating market event KPIs: {e}")
            raise
    
    @monitor.timing
    async def analyze_trend(
        self,
        metric_name: str,
        company_id: Optional[str] = None,
        lookback_days: int = 30
    ) -> Optional[TrendAnalysis]:
        """
        Analyze trend for a specific metric.
        
        Args:
            metric_name: Name of metric to analyze
            company_id: Optional company identifier
            lookback_days: Number of days to analyze
            
        Returns:
            Trend analysis result
        """
        try:
            # Collect historical data
            data_points = await self._collect_metric_history(
                metric_name, company_id, lookback_days
            )
            
            if len(data_points) < 2:
                self.logger.warning(f"Insufficient data points for trend analysis: {metric_name}")
                return None
            
            # Calculate trend direction and magnitude
            values = [v for _, v in data_points]
            
            # Linear regression for trend
            slope = await self._calculate_slope(values)
            direction = "up" if slope > 0.01 else "down" if slope < -0.01 else "stable"
            
            # Calculate trend confidence
            confidence = await self._calculate_trend_confidence(values)
            
            # Generate forecast
            forecast = await self._forecast_metric(values, days=7)
            
            return TrendAnalysis(
                metric_name=metric_name,
                direction=direction,
                magnitude=abs(slope),
                confidence=confidence,
                period_days=lookback_days,
                data_points=data_points,
                forecast=forecast
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend for {metric_name}: {e}")
            raise
    
    @monitor.timing
    async def get_aggregate_metrics(
        self,
        dimension: str,
        metric_name: str,
        lookback_days: int = 30
    ) -> List[AggregateMetric]:
        """
        Get aggregated metrics by dimension.
        
        Args:
            dimension: Dimension to aggregate by (e.g., "company", "sector")
            metric_name: Metric to aggregate
            lookback_days: Number of days to consider
            
        Returns:
            List of aggregated metrics
        """
        try:
            aggregates = []
            
            # Get all values for this metric
            values_by_dimension = await self._collect_metrics_by_dimension(
                dimension, metric_name, lookback_days
            )
            
            for dim_value, values in values_by_dimension.items():
                if not values:
                    continue
                
                aggregate = AggregateMetric(
                    dimension=dimension,
                    metric_name=metric_name,
                    value=sum(values) / len(values),
                    count=len(values),
                    average=sum(values) / len(values),
                    min_value=min(values),
                    max_value=max(values),
                    std_dev=stdev(values) if len(values) > 1 else 0
                )
                aggregates.append(aggregate)
            
            return sorted(aggregates, key=lambda x: x.value, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting aggregate metrics: {e}")
            raise
    
    @monitor.timing
    async def calculate_predictive_kpi(
        self,
        company_id: str,
        kpi_name: str,
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate predictive KPI with forecasting.
        
        Args:
            company_id: Company identifier
            kpi_name: KPI to forecast
            forecast_days: Number of days to forecast
            
        Returns:
            Dictionary with forecast and confidence intervals
        """
        try:
            # Collect historical data
            historical = await self._collect_kpi_history(company_id, kpi_name, 90)
            
            if len(historical) < 10:
                return {
                    "error": "Insufficient data for prediction",
                    "data_points": len(historical)
                }
            
            values = [v for _, v in historical]
            
            # Simple exponential smoothing forecast
            forecast = self._exponential_smoothing_forecast(values, forecast_days)
            
            # Calculate confidence intervals
            std_dev = stdev(values)
            confidence_interval = 1.96 * std_dev / np.sqrt(len(values))
            
            return {
                "kpi_name": kpi_name,
                "current_value": values[-1],
                "forecast": forecast,
                "confidence_interval": confidence_interval,
                "forecast_days": forecast_days,
                "historical_avg": mean(values),
                "historical_trend": "up" if forecast[-1] > values[-1] else "down"
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating predictive KPI: {e}")
            raise
    
    # Private helper methods
    
    async def _count_signals(
        self,
        company_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Count signals for company in date range."""
        # Placeholder: In production, would query database
        return 45
    
    async def _calculate_trend(
        self,
        metric_name: str,
        company_id: str,
        lookback_days: int
    ) -> Dict[str, float]:
        """Calculate trend for metric."""
        # Placeholder: Would calculate actual trend
        return {
            "direction": "up",
            "change_percent": 5.2
        }
    
    async def _calculate_avg_confidence(
        self,
        company_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate average signal confidence."""
        # Placeholder
        return 0.78
    
    async def _calculate_signal_rate(
        self,
        company_id: str,
        lookback_days: int
    ) -> float:
        """Calculate signal detection rate."""
        # Placeholder
        return 3.2
    
    async def _calculate_high_confidence_ratio(
        self,
        company_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate ratio of high-confidence signals."""
        # Placeholder
        return 0.65
    
    async def _count_events(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Count market events in date range."""
        # Placeholder
        return 42
    
    async def _count_events_by_severity(
        self,
        start_date: datetime,
        end_date: datetime,
        severity: str
    ) -> int:
        """Count events by severity level."""
        # Placeholder
        return 12
    
    async def _collect_metric_history(
        self,
        metric_name: str,
        company_id: Optional[str],
        lookback_days: int
    ) -> List[Tuple[datetime, float]]:
        """Collect historical metric data."""
        # Placeholder
        end_date = datetime.utcnow()
        result = []
        for i in range(lookback_days):
            date = end_date - timedelta(days=lookback_days - i)
            value = 50 + i * 0.5 + np.random.normal(0, 2)
            result.append((date, value))
        return result
    
    async def _calculate_slope(self, values: List[float]) -> float:
        """Calculate slope using linear regression."""
        if len(values) < 2:
            return 0
        x = np.arange(len(values))
        y = np.array(values)
        z = np.polyfit(x, y, 1)
        return z[0]
    
    async def _calculate_trend_confidence(self, values: List[float]) -> float:
        """Calculate confidence in trend."""
        if len(values) < 3:
            return 0.5
        # R-squared calculation
        x = np.arange(len(values))
        y = np.array(values)
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        yhat = p(x)
        ybar = np.mean(y)
        ssreg = np.sum((yhat - ybar) ** 2)
        sstot = np.sum((y - ybar) ** 2)
        r_squared = ssreg / max(sstot, 1)
        return min(1.0, r_squared)
    
    async def _forecast_metric(
        self,
        values: List[float],
        days: int
    ) -> List[Tuple[datetime, float]]:
        """Generate forecast for metric."""
        # Simple exponential smoothing
        forecast_values = self._exponential_smoothing_forecast(values, days)
        
        result = []
        start_date = datetime.utcnow()
        for i, value in enumerate(forecast_values):
            date = start_date + timedelta(days=i+1)
            result.append((date, value))
        
        return result
    
    def _exponential_smoothing_forecast(
        self,
        values: List[float],
        periods: int,
        alpha: float = 0.3
    ) -> List[float]:
        """Exponential smoothing forecast."""
        forecast = []
        
        # Initial value
        current = values[-1]
        forecast.append(current)
        
        # Calculate forecast
        for _ in range(periods):
            current = alpha * forecast[-1] + (1 - alpha) * np.mean(values[-10:])
            forecast.append(current)
        
        return forecast
    
    async def _collect_metrics_by_dimension(
        self,
        dimension: str,
        metric_name: str,
        lookback_days: int
    ) -> Dict[str, List[float]]:
        """Collect metrics grouped by dimension."""
        # Placeholder
        return {
            "value1": [10, 15, 12, 14],
            "value2": [20, 18, 22, 19],
        }
    
    async def _collect_kpi_history(
        self,
        company_id: str,
        kpi_name: str,
        lookback_days: int
    ) -> List[Tuple[datetime, float]]:
        """Collect KPI historical data."""
        # Placeholder
        end_date = datetime.utcnow()
        result = []
        for i in range(lookback_days):
            date = end_date - timedelta(days=lookback_days - i)
            value = 50 + i * 0.3 + np.random.normal(0, 3)
            result.append((date, value))
        return result
    
    def _get_status(
        self,
        value: float,
        warning_threshold: float,
        normal_threshold: float,
        critical_threshold: float
    ) -> str:
        """Determine status based on value."""
        if value >= critical_threshold or value <= warning_threshold:
            return "critical"
        elif value >= normal_threshold * 0.8 or value <= warning_threshold * 1.2:
            return "warning"
        return "healthy"
