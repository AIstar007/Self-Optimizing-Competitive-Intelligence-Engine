"""
Domain Layer

The core business logic of the Competitive Intelligence Engine.

This layer contains:
- Entities: Core business objects (Company, Signal, Report, etc.)
- Value Objects: Immutable value types (Money, Timestamp, Confidence, etc.)
- Interfaces: Abstract contracts for external dependencies

IMPORTANT: This layer has ZERO external dependencies. All interfaces are
defined here and implemented by the Infrastructure layer.

Dependency Rule: Outer layers may depend on this layer, but this layer
does not depend on any other layer.
"""

from .entities import (
    Company,
    CompanyStatus,
    CompanyStage,
    CompanySnapshot,
    Signal,
    SignalType,
    SignalSeverity,
    SignalSource,
    SignalPattern,
    Report,
    ReportFormat,
    ReportStatus,
    ReportType,
    ReportSection,
    MarketEvent,
    MarketEventType,
    MarketEventImpact,
    MarketEventDuration,
    AgentPolicy,
    PolicyType,
    PolicyStatus,
    PolicySource,
    ToolPreference,
    StrategyPattern,
    PolicyFeedback,
)

from .value_objects import (
    EntityId,
    Money,
    Confidence,
    ConfidenceLevel,
    Timestamp,
    TimestampPrecision,
)

from .interfaces import (
    # Repositories
    CompanyRepository,
    SignalRepository,
    ReportRepository,
    MarketEventRepository,
    AgentPolicyRepository,
    KnowledgeGraphRepository,
    # LLM Provider
    ModelProvider,
    TaskType,
    Message,
    ModelConfig,
    CompletionResponse,
    EmbeddingResponse,
    TokenUsage,
    ToolDefinition as LLMDToolDefinition,
    ToolCall,
    LLMProvider,
    LLMRouter,
    ToolCallingLLM,
    # Vector Store
    VectorStore,
    VectorDistance,
    Document,
    SearchResult,
    VectorStats,
    # Browser Provider
    BrowserType,
    PageLoadState,
    ScrapedContent,
    NavigationResult,
    Screenshot,
    BrowserState,
    BrowserProvider,
    SearchEngine,
    # Tools
    ToolCategory,
    ToolStatus,
    ToolParameter,
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolUsageStats,
    ToolFunction,
    ToolRegistry,
    ToolExecutor,
)

__all__ = [
    # Entities
    "Company",
    "CompanyStatus",
    "CompanyStage",
    "CompanySnapshot",
    "Signal",
    "SignalType",
    "SignalSeverity",
    "SignalSource",
    "SignalPattern",
    "Report",
    "ReportFormat",
    "ReportStatus",
    "ReportType",
    "ReportSection",
    "MarketEvent",
    "MarketEventType",
    "MarketEventImpact",
    "MarketEventDuration",
    "AgentPolicy",
    "PolicyType",
    "PolicyStatus",
    "PolicySource",
    "ToolPreference",
    "StrategyPattern",
    "PolicyFeedback",
    # Value Objects
    "EntityId",
    "Money",
    "Confidence",
    "ConfidenceLevel",
    "Timestamp",
    "TimestampPrecision",
    # Repository Interfaces
    "CompanyRepository",
    "SignalRepository",
    "ReportRepository",
    "MarketEventRepository",
    "AgentPolicyRepository",
    "KnowledgeGraphRepository",
    # LLM Provider Interfaces
    "ModelProvider",
    "TaskType",
    "Message",
    "ModelConfig",
    "CompletionResponse",
    "EmbeddingResponse",
    "TokenUsage",
    "LLMDToolDefinition",
    "ToolCall",
    "LLMProvider",
    "LLMRouter",
    "ToolCallingLLM",
    # Vector Store Interfaces
    "VectorStore",
    "VectorDistance",
    "Document",
    "SearchResult",
    "VectorStats",
    # Browser Provider Interfaces
    "BrowserType",
    "PageLoadState",
    "ScrapedContent",
    "NavigationResult",
    "Screenshot",
    "BrowserState",
    "BrowserProvider",
    "SearchEngine",
    # Tool Interfaces
    "ToolCategory",
    "ToolStatus",
    "ToolParameter",
    "ToolDefinition",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolUsageStats",
    "ToolFunction",
    "ToolRegistry",
    "ToolExecutor",
]