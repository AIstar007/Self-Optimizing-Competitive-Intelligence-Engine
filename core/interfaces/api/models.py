"""REST API models and schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


# ============================================================================
# Signal Models
# ============================================================================

class SignalSearchRequest(BaseModel):
    """Request for searching competitor signals."""

    company_id: str = Field(..., description="Company ID to search signals for")
    keywords: list[str] = Field(..., description="Keywords to search for")
    time_range_days: int = Field(30, ge=1, le=365, description="Time range in days")
    min_severity: str = Field("MEDIUM", description="Minimum severity level")
    include_unverified: bool = Field(False, description="Include unverified signals")


class SignalResponse(BaseModel):
    """Single signal response."""

    id: str
    title: str
    source: str
    severity: str
    signal_type: str
    verified: bool
    created_at: str


class SignalSearchResponse(BaseModel):
    """Response from signal search."""

    success: bool
    signals: list[SignalResponse] = Field(default_factory=list)
    total_count: int = 0
    relevant_count: int = 0
    sources: list[str] = Field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


# ============================================================================
# Report Models
# ============================================================================

class ReportGenerateRequest(BaseModel):
    """Request for generating a report."""

    company_id: str = Field(..., description="Company ID for report")
    report_type: str = Field("COMPETITIVE_ANALYSIS", description="Type of report")
    include_signals: bool = Field(True, description="Include signals section")
    include_analysis: bool = Field(True, description="Include analysis section")
    include_recommendations: bool = Field(True, description="Include recommendations")


class ReportResponse(BaseModel):
    """Report response."""

    success: bool
    report_id: Optional[str] = None
    report_type: str = ""
    content: Optional[str] = None
    sections: dict[str, str] = Field(default_factory=dict)
    word_count: int = 0
    generation_time_seconds: float = 0.0
    error: Optional[str] = None


# ============================================================================
# Market Analysis Models
# ============================================================================

class MarketAnalysisRequest(BaseModel):
    """Request for market analysis."""

    markets: list[str] = Field(..., description="Markets to analyze")
    time_range_days: int = Field(90, ge=1, le=365, description="Time range in days")
    include_forecast: bool = Field(True, description="Include market forecast")


class MarketTrendResponse(BaseModel):
    """Single market trend response."""

    market: str
    current_trends: list[str] = Field(default_factory=list)
    key_players: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    forecast: Optional[str] = None


class MarketAnalysisResponse(BaseModel):
    """Response from market analysis."""

    success: bool
    markets: list[MarketTrendResponse] = Field(default_factory=list)
    total_markets: int = 0
    error: Optional[str] = None


# ============================================================================
# Competitor Tracking Models
# ============================================================================

class CompetitorTrackRequest(BaseModel):
    """Request for tracking competitor activity."""

    competitor_name: str = Field(..., description="Competitor name to track")
    tracking_period_days: int = Field(30, ge=1, le=365, description="Tracking period")
    alert_threshold: str = Field("MEDIUM", description="Alert threshold")


class CompetitorActivityResponse(BaseModel):
    """Response from competitor tracking."""

    success: bool
    competitor_name: str = ""
    total_signals: int = 0
    signals_by_type: dict[str, int] = Field(default_factory=dict)
    activity_level: str = ""
    key_activities: list[str] = Field(default_factory=list)
    risk_level: str = ""
    error: Optional[str] = None


# ============================================================================
# Workflow Models
# ============================================================================

class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow."""

    company_id: str = Field(..., description="Company ID for workflow")
    company_name: str = Field(..., description="Company name")
    workflow_type: str = Field("competitive_intelligence", description="Workflow type")


class WorkflowTaskResponse(BaseModel):
    """Single workflow task response."""

    task_id: str
    agent_type: str
    status: str
    result: Optional[dict] = None
    execution_time_ms: float = 0.0


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""

    success: bool
    workflow_id: str = ""
    status: str = ""
    tasks: list[WorkflowTaskResponse] = Field(default_factory=list)
    completion_percentage: int = 0
    total_execution_time_ms: float = 0.0
    error: Optional[str] = None


# ============================================================================
# Agent Models
# ============================================================================

class AgentExecuteRequest(BaseModel):
    """Request to execute an agent."""

    agent_type: str = Field(..., description="Type of agent to execute")
    task: str = Field(..., description="Task for the agent")
    context: dict[str, Any] = Field(default_factory=dict, description="Agent context")


class AgentResultResponse(BaseModel):
    """Response from agent execution."""

    success: bool
    agent_id: str = ""
    output: Optional[dict] = None
    execution_time_ms: float = 0.0
    thoughts: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Agent status response."""

    agent_id: str
    status: str
    last_execution: Optional[str] = None
    success_rate: float = 0.0
    total_executions: int = 0


# ============================================================================
# Company Models
# ============================================================================

class CompanyCreateRequest(BaseModel):
    """Request to create a company."""

    name: str = Field(..., min_length=1, description="Company name")
    domain: str = Field(..., description="Company domain")
    status: str = Field("ACTIVE", description="Company status")
    stage: str = Field("GROWTH", description="Company stage")
    employees: int = Field(0, ge=0, description="Number of employees")
    markets: list[str] = Field(default_factory=list, description="Markets")
    competitors: list[str] = Field(default_factory=list, description="Competitors")


class CompanyResponse(BaseModel):
    """Company response."""

    id: str
    name: str
    domain: str
    status: str
    stage: str
    employees: int
    markets: list[str]
    competitors: list[str]
    created_at: str
    updated_at: str


class CompanyListResponse(BaseModel):
    """List of companies response."""

    success: bool
    companies: list[CompanyResponse] = Field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None


# ============================================================================
# Task Scheduling Models
# ============================================================================

class TaskScheduleRequest(BaseModel):
    """Request to schedule a task."""

    task_id: str = Field(..., description="Task identifier")
    agent_type: str = Field(..., description="Type of agent")
    context: dict[str, Any] = Field(default_factory=dict, description="Task context")
    schedule: str = Field("immediate", description="Schedule type")
    recurring: bool = Field(False, description="Recurring task")


class TaskScheduleResponse(BaseModel):
    """Response from task scheduling."""

    success: bool
    task_id: Optional[str] = None
    scheduled: bool = False
    schedule: str = ""
    next_run: Optional[str] = None
    error: Optional[str] = None


class TaskHistoryResponse(BaseModel):
    """Task history response."""

    success: bool
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None


# ============================================================================
# Health & Status Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"
    services: dict[str, str] = Field(default_factory=dict)


class StatsResponse(BaseModel):
    """System statistics response."""

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_companies: int = 0
    total_signals: int = 0
    total_reports: int = 0
    active_workflows: int = 0
    api_calls: int = 0
