"""Dashboard data models and ORM entities."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class DashboardConfig(Base):
    """Dashboard configuration and layout."""

    __tablename__ = "dashboard_configs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    company_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    layout = Column(JSON, nullable=False)  # Grid/widget configuration
    widgets = Column(JSON, nullable=False)  # Widget definitions
    refresh_interval = Column(Integer, default=5000)  # ms
    is_default = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    shared_with = Column(JSON, default=[])  # List of user IDs
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_company_dashboard", "user_id", "company_id"),
        Index("idx_dashboard_created", "created_at"),
    )


class DashboardWidget(Base):
    """Widget configuration for dashboards."""

    __tablename__ = "dashboard_widgets"

    id = Column(String, primary_key=True, index=True)
    dashboard_config_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    widget_type = Column(String, nullable=False)  # chart, metric, alert, etc.
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    config = Column(JSON, nullable=False)  # Widget-specific configuration
    data_source = Column(String, nullable=False)  # API endpoint or stream
    refresh_interval = Column(Integer, nullable=True)  # Override dashboard interval
    position = Column(JSON, nullable=False)  # {x, y, w, h} for grid layout
    size = Column(String, default="medium")  # small, medium, large
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_widget_dashboard", "dashboard_config_id"),
        Index("idx_widget_type", "widget_type"),
    )


class UserAnalyticsDashboard(Base):
    """User dashboard preferences and settings."""

    __tablename__ = "user_analytics_dashboards"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)
    active_dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=True)
    theme = Column(String, default="light")  # light, dark, custom
    view_mode = Column(String, default="grid")  # grid, list, compact
    notifications_enabled = Column(Boolean, default=True)
    alert_severity_filter = Column(String, default="all")  # all, critical, warning
    auto_refresh = Column(Boolean, default=True)
    default_time_range = Column(String, default="24h")  # 24h, 7d, 30d, custom
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_user_dashboard", "user_id"),)


class DashboardCache(Base):
    """Cache for dashboard data to improve performance."""

    __tablename__ = "dashboard_cache"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    cache_key = Column(String, nullable=False, index=True)
    data = Column(JSON, nullable=False)
    ttl_seconds = Column(Integer, default=300)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    hit_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_cache_dashboard_key", "dashboard_id", "cache_key"),
        Index("idx_cache_expires", "expires_at"),
    )


class DashboardMetricSnapshot(Base):
    """Snapshot of metrics at specific time for dashboard."""

    __tablename__ = "dashboard_metric_snapshots"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    metric_id = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # healthy, warning, critical
    unit = Column(String, nullable=True)
    comparison_period = Column(String, nullable=True)  # 1h, 24h, 7d, etc.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_snapshot_dashboard_time", "dashboard_id", "created_at"),
        Index("idx_snapshot_metric", "metric_id", "created_at"),
    )


class DashboardAlertSnapshot(Base):
    """Snapshot of alerts for dashboard display."""

    __tablename__ = "dashboard_alert_snapshots"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    alert_id = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False)  # info, warning, critical
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    source = Column(String, nullable=False)  # metric, threshold, system
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_alert_dashboard_severity", "dashboard_id", "severity"),
        Index("idx_alert_resolved", "is_resolved"),
    )


class DashboardKPISnapshot(Base):
    """Snapshot of KPIs for dashboard."""

    __tablename__ = "dashboard_kpi_snapshots"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    kpi_id = Column(String, nullable=False, index=True)
    kpi_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    target = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # healthy, warning, critical, on_track, at_risk
    trend = Column(String, nullable=False)  # up, down, stable
    confidence = Column(Float, nullable=True)
    forecast_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_kpi_snapshot_dashboard", "dashboard_id", "created_at"),
        Index("idx_kpi_snapshot", "kpi_id", "created_at"),
    )


class DashboardChartData(Base):
    """Pre-calculated chart data for performance."""

    __tablename__ = "dashboard_chart_data"

    id = Column(String, primary_key=True, index=True)
    dashboard_widget_id = Column(String, ForeignKey("dashboard_widgets.id"), nullable=False)
    chart_type = Column(String, nullable=False)  # line, bar, pie, area, etc.
    series_data = Column(JSON, nullable=False)  # Chart data points
    labels = Column(JSON, nullable=False)
    metadata = Column(JSON, nullable=True)
    data_points_count = Column(Integer, nullable=False)
    time_range_start = Column(DateTime, nullable=False)
    time_range_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_chart_widget", "dashboard_widget_id"),
        Index("idx_chart_expires", "expires_at"),
    )


class DashboardAuditLog(Base):
    """Audit log for dashboard changes."""

    __tablename__ = "dashboard_audit_logs"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # created, updated, deleted, viewed, shared
    changes = Column(JSON, nullable=True)  # Before/after for updates
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_audit_dashboard", "dashboard_id", "created_at"),
        Index("idx_audit_user", "user_id", "created_at"),
    )


class DashboardNotification(Base):
    """Notification preferences per dashboard."""

    __tablename__ = "dashboard_notifications"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    user_id = Column(String, nullable=False)
    alert_severity = Column(String, default="all")  # all, critical, warning
    notification_channels = Column(JSON, default=["websocket"])  # websocket, email, slack
    is_enabled = Column(Boolean, default=True)
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String, nullable=True)  # HH:MM format
    quiet_hours_end = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_notification_dashboard", "dashboard_id", "user_id"),
        Index("idx_notification_enabled", "is_enabled"),
    )


class DashboardViewHistory(Base):
    """Track dashboard view history for analytics."""

    __tablename__ = "dashboard_view_history"

    id = Column(String, primary_key=True, index=True)
    dashboard_id = Column(String, ForeignKey("dashboard_configs.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False)
    view_duration_seconds = Column(Integer, nullable=False)
    widgets_interacted = Column(JSON, default=[])
    filters_applied = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_view_dashboard_user", "dashboard_id", "user_id", "created_at"),
        Index("idx_view_session", "session_id"),
    )
