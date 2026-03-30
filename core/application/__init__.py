"""
Application Layer - Use Cases, Services, Agents, and Orchestration

This module orchestrates business logic using domain entities and infrastructure
providers to implement the competitive intelligence system's core functionality.
"""

# ============================================================================
# Use Cases
# ============================================================================

from core.application.use_cases import (
    # Base
    UseCase,
    UseCaseResponse,
    # Search Competitor Signals
    SearchCompetitorSignalsUseCase,
    SearchCompetitorSignalsRequest,
    SearchCompetitorSignalsResponse,
    # Generate Intelligence Report
    GenerateIntelligenceReportUseCase,
    GenerateIntelligenceReportRequest,
    GenerateIntelligenceReportResponse,
    # Analyze Market Trends
    AnalyzeMarketTrendsUseCase,
    AnalyzeMarketTrendsRequest,
    AnalyzeMarketTrendsResponse,
    # Track Competitor Activity
    TrackCompetitorActivityUseCase,
    TrackCompetitorActivityRequest,
    TrackCompetitorActivityResponse,
    # Learn From Feedback
    LearnFromFeedbackUseCase,
    LearnFromFeedbackRequest,
    LearnFromFeedbackResponse,
)

# ============================================================================
# Services
# ============================================================================

from core.application.services import (
    CompetitiveIntelligenceService,
    SignalProcessingService,
    ReportGenerationService,
    KnowledgeGraphService,
    AgentPolicyService,
)

# ============================================================================
# Agents
# ============================================================================

from core.application.agents import (
    # Base
    Agent,
    AgentMemory,
    AgentExecutionResult,
    # Specialized Agents
    ResearchAgent,
    AnalysisAgent,
    StrategyAgent,
    ReportAgent,
    CritiqueAgent,
    PlannerAgent,
)

# ============================================================================
# Orchestrators
# ============================================================================

from core.application.orchestrators import (
    # Workflow
    WorkflowOrchestrator,
    WorkflowExecution,
    WorkflowTask,
    WorkflowStatus,
    TaskStatus,
    # Task Scheduling
    TaskScheduler,
    # Agent Communication
    AgentCommunicator,
)

__all__ = [
    # ========================================================================
    # Use Cases (Requests, Responses, Implementations)
    # ========================================================================
    "UseCase",
    "UseCaseResponse",
    # Search Competitor Signals
    "SearchCompetitorSignalsUseCase",
    "SearchCompetitorSignalsRequest",
    "SearchCompetitorSignalsResponse",
    # Generate Intelligence Report
    "GenerateIntelligenceReportUseCase",
    "GenerateIntelligenceReportRequest",
    "GenerateIntelligenceReportResponse",
    # Analyze Market Trends
    "AnalyzeMarketTrendsUseCase",
    "AnalyzeMarketTrendsRequest",
    "AnalyzeMarketTrendsResponse",
    # Track Competitor Activity
    "TrackCompetitorActivityUseCase",
    "TrackCompetitorActivityRequest",
    "TrackCompetitorActivityResponse",
    # Learn From Feedback
    "LearnFromFeedbackUseCase",
    "LearnFromFeedbackRequest",
    "LearnFromFeedbackResponse",
    # ========================================================================
    # Services (Business Logic Orchestrators)
    # ========================================================================
    "CompetitiveIntelligenceService",
    "SignalProcessingService",
    "ReportGenerationService",
    "KnowledgeGraphService",
    "AgentPolicyService",
    # ========================================================================
    # Agents (Autonomous Agents)
    # ========================================================================
    "Agent",
    "AgentMemory",
    "AgentExecutionResult",
    "ResearchAgent",
    "AnalysisAgent",
    "StrategyAgent",
    "ReportAgent",
    "CritiqueAgent",
    "PlannerAgent",
    # ========================================================================
    # Orchestration (Workflow Management)
    # ========================================================================
    "WorkflowOrchestrator",
    "WorkflowExecution",
    "WorkflowTask",
    "WorkflowStatus",
    "TaskStatus",
    "TaskScheduler",
    "AgentCommunicator",
]