"""
Domain Interfaces

These interfaces define the contracts for external dependencies.
Following the Dependency Inversion Principle, the domain layer
does not depend on concrete implementations, only on abstractions.

This ensures:
- The domain remains pure and testable
- External systems can be swapped without changing domain code
- Clear boundaries between layers
"""

from .repositories import (
    CompanyRepository,
    SignalRepository,
    ReportRepository,
    MarketEventRepository,
    AgentPolicyRepository,
    KnowledgeGraphRepository,
)

from .llm_providers import (
    ModelProvider,
    TaskType,
    Message,
    ModelConfig,
    CompletionResponse,
    EmbeddingResponse,
    TokenUsage,
    ToolDefinition,
    ToolCall,
    LLMProvider,
    LLMRouter,
    ToolCallingLLM,
)

from .vector_store import (
    VectorStore,
    VectorDistance,
    Document,
    SearchResult,
    VectorStats,
)

from .browser_provider import (
    BrowserType,
    PageLoadState,
    SearchResult as BrowserSearchResult,
    ScrapedContent,
    NavigationResult,
    Screenshot,
    BrowserState,
    BrowserProvider,
    SearchEngine,
)

from .tools import (
    ToolCategory,
    ToolStatus,
    ToolParameter,
    ToolDefinition as ToolDef,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolUsageStats,
    ToolFunction,
    ToolRegistry,
    ToolExecutor,
)

__all__ = [
    # Repository interfaces
    "CompanyRepository",
    "SignalRepository",
    "ReportRepository",
    "MarketEventRepository",
    "AgentPolicyRepository",
    "KnowledgeGraphRepository",
    # LLM provider interfaces
    "ModelProvider",
    "TaskType",
    "Message",
    "ModelConfig",
    "CompletionResponse",
    "EmbeddingResponse",
    "TokenUsage",
    "ToolDefinition",
    "ToolCall",
    "LLMProvider",
    "LLMRouter",
    "ToolCallingLLM",
    # Vector store interfaces
    "VectorStore",
    "VectorDistance",
    "Document",
    "SearchResult",
    "VectorStats",
    # Browser provider interfaces
    "BrowserType",
    "PageLoadState",
    "BrowserSearchResult",
    "ScrapedContent",
    "NavigationResult",
    "Screenshot",
    "BrowserState",
    "BrowserProvider",
    "SearchEngine",
    # Tool interfaces
    "ToolCategory",
    "ToolStatus",
    "ToolParameter",
    "ToolDef",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolUsageStats",
    "ToolFunction",
    "ToolRegistry",
    "ToolExecutor",
]