"""
Infrastructure layer module for the Self-Optimizing Competitive Intelligence Engine.

This layer provides concrete implementations of all domain interfaces using external
services and libraries:

Submodules:
    - database: SQLAlchemy ORM models and async repositories
    - llm: Multi-provider LLM support (OpenAI, Anthropic, Ollama)
    - browser: Playwright-based web automation and scraping
    - vector_store: Vector similarity search (FAISS, Chroma)
    - knowledge_graph: NetworkX knowledge graph implementation
    - tools: Dynamic tool registry and execution framework

Architecture:
    - All operations are fully async
    - All providers implement domain interfaces
    - Dependency inversion: domain interfaces, infrastructure implementations
    - Clean separation: business logic (domain) vs. external services (infrastructure)
    - Easy to swap implementations without affecting domain logic

Dependencies:
    - SQLAlchemy: Database ORM
    - Playwright: Browser automation
    - OpenAI/Anthropic/Ollama: Language models
    - FAISS/Chroma: Vector search
    - NetworkX: Graph algorithms
    - HTTPX: Async HTTP client

Key Exports:
    Database:
        - SQLCompanyRepository, SQLSignalRepository
        - async_session_factory, engine, DATABASE_URL, Base
        
    LLM:
        - OpenAIProvider, AnthropicProvider, OllamaProvider
        - LLMRouter (intelligent model selection)
        
    Browser:
        - PlaywrightBrowserProvider
        
    Vector Store:
        - FAISSVectorStore, ChromaVectorStore
        
    Knowledge Graph:
        - NetworkXGraphRepository
        
    Tools:
        - ToolRegistry

All implementations:
    ✅ Fully async/await
    ✅ Implement domain interfaces
    ✅ Include error handling
    ✅ Support batch operations
    ✅ Include usage tracking
    ✅ Production-grade quality
"""

# Database exports
from core.infrastructure.database import (
    engine,
    async_session_factory,
    AsyncSession,
    Base,
    get_session,
    init_db,
    drop_db,
    DATABASE_URL,
)
from core.infrastructure.database.models import (
    CompanyModel,
    SignalModel,
    ReportModel,
    MarketEventModel,
    AgentPolicyModel,
    KnowledgeNodeModel,
    KnowledgeEdgeModel,
)
from core.infrastructure.database.repositories import (
    SQLCompanyRepository,
    SQLSignalRepository,
)

# LLM exports
from core.infrastructure.llm import (
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    LLMRouter,
)

# Browser exports
from core.infrastructure.browser import PlaywrightBrowserProvider

# Vector Store exports
from core.infrastructure.vector_store import (
    FAISSVectorStore,
    ChromaVectorStore,
)

# Knowledge Graph exports
from core.infrastructure.knowledge_graph import NetworkXGraphRepository

# Tools exports
from core.infrastructure.tools import ToolRegistry

__all__ = [
    # Database
    "engine",
    "async_session_factory",
    "AsyncSession",
    "Base",
    "get_session",
    "init_db",
    "drop_db",
    "DATABASE_URL",
    # Database Models
    "CompanyModel",
    "SignalModel",
    "ReportModel",
    "MarketEventModel",
    "AgentPolicyModel",
    "KnowledgeNodeModel",
    "KnowledgeEdgeModel",
    # Database Repositories
    "SQLCompanyRepository",
    "SQLSignalRepository",
    # LLM Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "LLMRouter",
    # Browser
    "PlaywrightBrowserProvider",
    # Vector Stores
    "FAISSVectorStore",
    "ChromaVectorStore",
    # Knowledge Graph
    "NetworkXGraphRepository",
    # Tools
    "ToolRegistry",
]