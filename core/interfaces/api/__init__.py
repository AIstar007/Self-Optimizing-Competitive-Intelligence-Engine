"""FastAPI REST interface for the Competitive Intelligence Engine."""

from core.interfaces.api.app import app, create_app
from core.interfaces.api.models import (
    # Signal models
    SignalSearchRequest,
    SignalResponse,
    SignalSearchResponse,
    # Report models
    ReportGenerateRequest,
    ReportResponse,
    # Market analysis models
    MarketAnalysisRequest,
    MarketTrendResponse,
    MarketAnalysisResponse,
    # Competitor models
    CompetitorTrackRequest,
    CompetitorActivityResponse,
    # Workflow models
    WorkflowExecuteRequest,
    WorkflowTaskResponse,
    WorkflowStatusResponse,
    # Agent models
    AgentExecuteRequest,
    AgentResultResponse,
    AgentStatusResponse,
    # Company models
    CompanyCreateRequest,
    CompanyResponse,
    CompanyListResponse,
    # Task models
    TaskScheduleRequest,
    TaskScheduleResponse,
    TaskHistoryResponse,
    # Health models
    HealthResponse,
    StatsResponse,
)

__all__ = [
    # Application
    "app",
    "create_app",
    # Signal models
    "SignalSearchRequest",
    "SignalResponse",
    "SignalSearchResponse",
    # Report models
    "ReportGenerateRequest",
    "ReportResponse",
    # Market analysis models
    "MarketAnalysisRequest",
    "MarketTrendResponse",
    "MarketAnalysisResponse",
    # Competitor models
    "CompetitorTrackRequest",
    "CompetitorActivityResponse",
    # Workflow models
    "WorkflowExecuteRequest",
    "WorkflowTaskResponse",
    "WorkflowStatusResponse",
    # Agent models
    "AgentExecuteRequest",
    "AgentResultResponse",
    "AgentStatusResponse",
    # Company models
    "CompanyCreateRequest",
    "CompanyResponse",
    "CompanyListResponse",
    # Task models
    "TaskScheduleRequest",
    "TaskScheduleResponse",
    "TaskHistoryResponse",
    # Health models
    "HealthResponse",
    "StatsResponse",
]
