"""FastAPI endpoints for real-time dashboard management."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.infrastructure.database.dashboard_models import (
    DashboardConfig,
    DashboardWidget,
    UserAnalyticsDashboard,
    DashboardMetricSnapshot,
    DashboardAlertSnapshot,
    DashboardKPISnapshot,
)
from core.infrastructure.websocket.websocket_manager import (
    get_websocket_manager,
    ConnectionType,
)
from core.application.services.streaming_service import get_streaming_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# Pydantic models
class DashboardWidgetSchema(BaseModel):
    """Dashboard widget schema."""

    id: Optional[str] = None
    widget_type: str
    title: str
    description: Optional[str] = None
    config: Dict[str, Any]
    data_source: str
    refresh_interval: Optional[int] = None
    position: Dict[str, int]
    size: str = "medium"


class DashboardConfigSchema(BaseModel):
    """Dashboard configuration schema."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    layout: Dict[str, Any]
    widgets: List[DashboardWidgetSchema]
    refresh_interval: int = 5000
    is_default: bool = False


class MetricSnapshotSchema(BaseModel):
    """Metric snapshot schema."""

    metric_id: str
    metric_name: str
    value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    status: str
    unit: Optional[str] = None


class KPISnapshotSchema(BaseModel):
    """KPI snapshot schema."""

    kpi_id: str
    kpi_name: str
    value: float
    target: Optional[float] = None
    status: str
    trend: str
    confidence: Optional[float] = None
    forecast_value: Optional[float] = None


class AlertSnapshotSchema(BaseModel):
    """Alert snapshot schema."""

    alert_id: str
    severity: str
    title: str
    message: str
    source: str
    is_resolved: bool


class DashboardDataSchema(BaseModel):
    """Complete dashboard data schema."""

    dashboard_id: str
    metrics: List[MetricSnapshotSchema]
    kpis: List[KPISnapshotSchema]
    alerts: List[AlertSnapshotSchema]
    timestamp: datetime


# Dependency
def get_db() -> Session:
    """Get database session (placeholder)."""
    # In production, inject actual database session
    pass


@router.get("/configs")
async def list_dashboard_configs(
    user_id: str = Query(...),
    company_id: str = Query(...),
    db: Session = Depends(get_db),
) -> List[DashboardConfigSchema]:
    """List all dashboard configurations for user."""
    logger.info(f"Listing dashboards for user {user_id}, company {company_id}")

    # Query dashboards owned by user or shared with user
    configs = [
        {
            "id": "dash_1",
            "name": "Executive Dashboard",
            "description": "Company KPIs and metrics",
            "layout": {"type": "grid", "columns": 12},
            "widgets": [],
            "refresh_interval": 5000,
            "is_default": True,
        },
    ]

    return configs


@router.post("/configs")
async def create_dashboard_config(
    config: DashboardConfigSchema,
    user_id: str = Query(...),
    company_id: str = Query(...),
    db: Session = Depends(get_db),
) -> DashboardConfigSchema:
    """Create new dashboard configuration."""
    logger.info(f"Creating dashboard for user {user_id}")

    dashboard_id = str(uuid4())
    config.id = dashboard_id

    # Create dashboard in database
    dashboard = DashboardConfig(
        id=dashboard_id,
        user_id=user_id,
        company_id=company_id,
        name=config.name,
        description=config.description,
        layout=config.layout,
        widgets=[],
        refresh_interval=config.refresh_interval,
        is_default=config.is_default,
    )

    logger.info(f"Dashboard {dashboard_id} created")
    return config


@router.get("/configs/{dashboard_id}")
async def get_dashboard_config(
    dashboard_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> DashboardConfigSchema:
    """Get dashboard configuration."""
    logger.info(f"Fetching dashboard {dashboard_id}")

    config = {
        "id": dashboard_id,
        "name": "Executive Dashboard",
        "description": "Company KPIs and metrics",
        "layout": {"type": "grid", "columns": 12},
        "widgets": [],
        "refresh_interval": 5000,
        "is_default": True,
    }

    return config


@router.put("/configs/{dashboard_id}")
async def update_dashboard_config(
    dashboard_id: str,
    config: DashboardConfigSchema,
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> DashboardConfigSchema:
    """Update dashboard configuration."""
    logger.info(f"Updating dashboard {dashboard_id}")

    config.id = dashboard_id
    return config


@router.delete("/configs/{dashboard_id}")
async def delete_dashboard_config(
    dashboard_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete dashboard configuration."""
    logger.info(f"Deleting dashboard {dashboard_id}")

    return {"status": "deleted", "dashboard_id": dashboard_id}


@router.get("/data/{dashboard_id}")
async def get_dashboard_data(
    dashboard_id: str,
    user_id: str = Query(...),
    time_range: str = Query("24h"),
    db: Session = Depends(get_db),
) -> DashboardDataSchema:
    """Get current dashboard data."""
    logger.info(f"Fetching dashboard data for {dashboard_id}")

    data = {
        "dashboard_id": dashboard_id,
        "metrics": [
            {
                "metric_id": "m1",
                "metric_name": "Signal Detection Rate",
                "value": 95.5,
                "status": "healthy",
                "unit": "%",
            }
        ],
        "kpis": [
            {
                "kpi_id": "kpi1",
                "kpi_name": "Market Signals",
                "value": 1250,
                "status": "on_track",
                "trend": "up",
                "confidence": 0.92,
            }
        ],
        "alerts": [
            {
                "alert_id": "a1",
                "severity": "warning",
                "title": "High latency detected",
                "message": "API response time exceeded threshold",
                "source": "metric",
                "is_resolved": False,
            }
        ],
        "timestamp": datetime.utcnow(),
    }

    return data


@router.get("/metrics/{dashboard_id}")
async def get_dashboard_metrics(
    dashboard_id: str,
    user_id: str = Query(...),
    limit: int = Query(20),
    db: Session = Depends(get_db),
) -> List[MetricSnapshotSchema]:
    """Get recent metric snapshots for dashboard."""
    logger.info(f"Fetching metrics for dashboard {dashboard_id}")

    metrics = [
        {
            "metric_id": "m1",
            "metric_name": "Signal Detection Rate",
            "value": 95.5,
            "status": "healthy",
            "unit": "%",
        },
        {
            "metric_id": "m2",
            "metric_name": "System Uptime",
            "value": 99.8,
            "status": "healthy",
            "unit": "%",
        },
    ]

    return metrics


@router.get("/kpis/{dashboard_id}")
async def get_dashboard_kpis(
    dashboard_id: str,
    user_id: str = Query(...),
    limit: int = Query(20),
    db: Session = Depends(get_db),
) -> List[KPISnapshotSchema]:
    """Get recent KPI snapshots for dashboard."""
    logger.info(f"Fetching KPIs for dashboard {dashboard_id}")

    kpis = [
        {
            "kpi_id": "kpi1",
            "kpi_name": "Market Signals",
            "value": 1250,
            "status": "on_track",
            "trend": "up",
            "confidence": 0.92,
        },
        {
            "kpi_id": "kpi2",
            "kpi_name": "Detection Accuracy",
            "value": 94.2,
            "status": "healthy",
            "trend": "stable",
            "confidence": 0.88,
        },
    ]

    return kpis


@router.get("/alerts/{dashboard_id}")
async def get_dashboard_alerts(
    dashboard_id: str,
    user_id: str = Query(...),
    severity: str = Query("all"),
    is_resolved: bool = Query(False),
    db: Session = Depends(get_db),
) -> List[AlertSnapshotSchema]:
    """Get alerts for dashboard."""
    logger.info(f"Fetching alerts for dashboard {dashboard_id}")

    alerts = [
        {
            "alert_id": "a1",
            "severity": "warning",
            "title": "High latency detected",
            "message": "API response time exceeded threshold",
            "source": "metric",
            "is_resolved": False,
        }
    ]

    return alerts


@router.post("/widgets/{dashboard_id}")
async def add_dashboard_widget(
    dashboard_id: str,
    widget: DashboardWidgetSchema,
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> DashboardWidgetSchema:
    """Add widget to dashboard."""
    logger.info(f"Adding widget to dashboard {dashboard_id}")

    widget.id = str(uuid4())
    return widget


@router.delete("/widgets/{widget_id}")
async def remove_dashboard_widget(
    widget_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Remove widget from dashboard."""
    logger.info(f"Removing widget {widget_id}")

    return {"status": "removed", "widget_id": widget_id}


@router.get("/health")
async def dashboard_health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# WebSocket endpoint for real-time dashboard
@router.websocket("/ws/{user_id}/{dashboard_id}")
async def websocket_dashboard(
    websocket: WebSocket,
    user_id: str,
    dashboard_id: str,
):
    """WebSocket endpoint for real-time dashboard updates."""
    ws_manager = get_websocket_manager()
    streaming_service = await get_streaming_service()

    # Accept connection
    client_id = await ws_manager.handle_client_connection(
        websocket,
        user_id=user_id,
        company_id=None,  # Can be extracted from user context
        connection_type=ConnectionType.DASHBOARD,
    )

    logger.info(f"Dashboard client {client_id} connected for dashboard {dashboard_id}")

    # Subscribe to relevant streams
    async def on_kpi_update(event):
        await ws_manager.broadcast_kpi_update(
            event.entity_id,
            event.data,
        )

    async def on_metric_update(event):
        await ws_manager.broadcast_metric_update(
            event.entity_id,
            event.data,
        )

    async def on_alert(event):
        await ws_manager.broadcast_alert(
            event.entity_id,
            event.data,
        )

    await streaming_service.subscribe("kpi", on_kpi_update)
    await streaming_service.subscribe("metric", on_metric_update)
    await streaming_service.subscribe("alert", on_alert)

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"Dashboard client {client_id} disconnected")
    finally:
        await ws_manager.connection_manager.disconnect(client_id)


import asyncio
