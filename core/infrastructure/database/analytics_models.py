"""
Analytics Database Models - Tables for analytics and data warehouse.

Defines:
- KPI tracking tables
- Metric aggregate tables
- Time-series data tables
- Report storage tables
- Performance data warehouse
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, 
    Boolean, Text, Index, UniqueConstraint,
    ForeignKey, JSON, Numeric
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class KPIHistory(Base):
    """Historical KPI values for tracking trends."""
    
    __tablename__ = "kpi_history"
    __table_args__ = (
        Index("idx_kpi_company_date", "company_id", "kpi_name", "timestamp"),
        Index("idx_kpi_timestamp", "timestamp"),
    )
    
    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), nullable=True)
    kpi_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    trend = Column(String(20), nullable=True)  # up, down, stable
    change_percent = Column(Float, nullable=True)
    status = Column(String(20), nullable=False)  # healthy, warning, critical
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MetricAggregate(Base):
    """Aggregated metrics by dimension."""
    
    __tablename__ = "metric_aggregates"
    __table_args__ = (
        Index("idx_metric_dimension_date", "metric_name", "dimension", "dimension_value", "timestamp"),
        Index("idx_metric_timestamp", "timestamp"),
        UniqueConstraint("metric_name", "dimension", "dimension_value", "timestamp", name="uq_metric_aggregate"),
    )
    
    id = Column(String(36), primary_key=True)
    metric_name = Column(String(100), nullable=False)
    dimension = Column(String(50), nullable=False)
    dimension_value = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    count = Column(Integer, nullable=False)
    average = Column(Float, nullable=False)
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimeSeriesData(Base):
    """Time-series data for analytics."""
    
    __tablename__ = "time_series_data"
    __table_args__ = (
        Index("idx_series_entity_metric", "entity_id", "metric_name", "timestamp"),
        Index("idx_series_timestamp", "timestamp"),
    )
    
    id = Column(String(36), primary_key=True)
    entity_id = Column(String(36), nullable=False)
    entity_type = Column(String(50), nullable=False)  # company, market, sector
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    granularity = Column(String(20), nullable=False)  # minute, hour, day, week, month
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrendAnalysisResult(Base):
    """Stored trend analysis results."""
    
    __tablename__ = "trend_analysis_results"
    __table_args__ = (
        Index("idx_trend_metric_company", "metric_name", "company_id", "analysis_date"),
    )
    
    id = Column(String(36), primary_key=True)
    metric_name = Column(String(100), nullable=False)
    company_id = Column(String(36), nullable=True)
    direction = Column(String(20), nullable=False)  # up, down, stable
    magnitude = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    period_days = Column(Integer, nullable=False)
    historical_data = Column(JSON, nullable=True)
    forecast_data = Column(JSON, nullable=True)
    analysis_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PredictiveKPI(Base):
    """Predictive KPI forecasts."""
    
    __tablename__ = "predictive_kpis"
    __table_args__ = (
        Index("idx_predictive_company_kpi", "company_id", "kpi_name", "forecast_date"),
    )
    
    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), nullable=False)
    kpi_name = Column(String(100), nullable=False)
    current_value = Column(Float, nullable=False)
    forecast_value = Column(Float, nullable=False)
    confidence_interval = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False)  # e.g., 0.95 for 95%
    forecast_date = Column(DateTime, nullable=False, index=True)
    forecast_horizon_days = Column(Integer, nullable=False)
    actual_value = Column(Float, nullable=True)  # Filled in after date passes
    accuracy = Column(Float, nullable=True)  # Calculated after actual_value
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalyticsReport(Base):
    """Stored analytics reports."""
    
    __tablename__ = "analytics_reports"
    __table_args__ = (
        Index("idx_report_company_date", "company_id", "report_date"),
    )
    
    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), nullable=True)
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    report_date = Column(DateTime, nullable=False, index=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    summary = Column(Text, nullable=True)
    kpi_data = Column(JSON, nullable=True)
    trend_data = Column(JSON, nullable=True)
    aggregate_data = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceMetric(Base):
    """Application performance metrics."""
    
    __tablename__ = "performance_metrics"
    __table_args__ = (
        Index("idx_perf_metric_date", "metric_name", "timestamp"),
    )
    
    id = Column(String(36), primary_key=True)
    metric_name = Column(String(100), nullable=False)
    operation = Column(String(255), nullable=True)
    duration_ms = Column(Float, nullable=False)
    memory_bytes = Column(Integer, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DimensionTable(Base):
    """Dimension table for analytics (e.g., companies, sectors)."""
    
    __tablename__ = "dimension_tables"
    __table_args__ = (
        Index("idx_dim_type_value", "dimension_type", "dimension_value"),
    )
    
    id = Column(String(36), primary_key=True)
    dimension_type = Column(String(50), nullable=False)  # company, sector, industry
    dimension_value = Column(String(255), nullable=False)
    attributes = Column(JSON, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FactTable(Base):
    """Fact table for analytics (events, transactions, signals)."""
    
    __tablename__ = "fact_tables"
    __table_args__ = (
        Index("idx_fact_date_dims", "date_id", "company_id", "metric_id"),
        Index("idx_fact_timestamp", "event_timestamp"),
    )
    
    id = Column(String(36), primary_key=True)
    date_id = Column(String(10), nullable=False)  # YYYYMMDD
    company_id = Column(String(36), nullable=False)
    metric_id = Column(String(36), nullable=False)
    measure = Column(Float, nullable=False)
    count = Column(Integer, default=1)
    event_timestamp = Column(DateTime, nullable=False, index=True)
    attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAnalyticsPreference(Base):
    """User preferences for analytics views and reports."""
    
    __tablename__ = "user_analytics_preferences"
    __table_args__ = (
        Index("idx_user_pref_date", "user_id", "created_at"),
    )
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    dashboard_layout = Column(JSON, nullable=True)
    preferred_metrics = Column(JSON, nullable=True)
    report_frequency = Column(String(50), nullable=True)  # daily, weekly, monthly
    favorite_reports = Column(JSON, nullable=True)
    chart_preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsCache(Base):
    """Cache for expensive analytics calculations."""
    
    __tablename__ = "analytics_cache"
    __table_args__ = (
        Index("idx_cache_key_ttl", "cache_key", "expires_at"),
    )
    
    id = Column(String(36), primary_key=True)
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    cache_value = Column(JSON, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)


# Alembic migration helper
def get_analytics_models():
    """Return list of all analytics models for migration."""
    return [
        KPIHistory,
        MetricAggregate,
        TimeSeriesData,
        TrendAnalysisResult,
        PredictiveKPI,
        AnalyticsReport,
        PerformanceMetric,
        DimensionTable,
        FactTable,
        UserAnalyticsPreference,
        AnalyticsCache,
    ]
