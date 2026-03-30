"""Interface layer for the Competitive Intelligence Engine.

Provides entry points for external systems to interact with the system:
- FastAPI REST API with 40+ endpoints
- Click CLI with command hierarchy
- WebSocket real-time communication
- Event pub/sub system
"""

# REST API exports
from core.interfaces.api import (
    app,
    create_app,
    SignalSearchRequest,
    SignalResponse,
    SignalSearchResponse,
    ReportGenerateRequest,
    ReportResponse,
    MarketAnalysisRequest,
    MarketTrendResponse,
    MarketAnalysisResponse,
    CompetitorTrackRequest,
    CompetitorActivityResponse,
    WorkflowExecuteRequest,
    WorkflowTaskResponse,
    WorkflowStatusResponse,
    AgentExecuteRequest,
    AgentResultResponse,
    AgentStatusResponse,
    CompanyCreateRequest,
    CompanyResponse,
    CompanyListResponse,
    TaskScheduleRequest,
    TaskScheduleResponse,
    TaskHistoryResponse,
    HealthResponse,
    StatsResponse,
)

# CLI exports
from core.interfaces.cli import cli

# WebSocket exports
from core.interfaces.websocket import (
    ConnectionManager,
    WebSocketHandler,
    EventBroadcaster,
    connection_manager,
    event_broadcaster,
)

# Event system exports
from core.interfaces.events import (
    Event,
    EventType,
    EventHandler,
    EventBus,
    event_bus,
    create_signal_event,
    create_report_event,
    create_workflow_event,
    create_task_event,
    create_agent_event,
)

__all__ = [
    # Application
    "app",
    "create_app",
    # REST API models
    "SignalSearchRequest",
    "SignalResponse",
    "SignalSearchResponse",
    "ReportGenerateRequest",
    "ReportResponse",
    "MarketAnalysisRequest",
    "MarketTrendResponse",
    "MarketAnalysisResponse",
    "CompetitorTrackRequest",
    "CompetitorActivityResponse",
    "WorkflowExecuteRequest",
    "WorkflowTaskResponse",
    "WorkflowStatusResponse",
    "AgentExecuteRequest",
    "AgentResultResponse",
    "AgentStatusResponse",
    "CompanyCreateRequest",
    "CompanyResponse",
    "CompanyListResponse",
    "TaskScheduleRequest",
    "TaskScheduleResponse",
    "TaskHistoryResponse",
    "HealthResponse",
    "StatsResponse",
    # CLI
    "cli",
    # WebSocket
    "ConnectionManager",
    "WebSocketHandler",
    "EventBroadcaster",
    "connection_manager",
    "event_broadcaster",
    # Event system
    "Event",
    "EventType",
    "EventHandler",
    "EventBus",
    "event_bus",
    "create_signal_event",
    "create_report_event",
    "create_workflow_event",
    "create_task_event",
    "create_agent_event",
]