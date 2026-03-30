"""
Domain LLM Provider Interfaces

These interfaces define the contract for LLM interaction.
The infrastructure layer implements these interfaces.

Following Dependency Inversion Principle - the domain layer
defines what it needs from LLM providers without coupling
to specific implementations (OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from enum import Enum
from dataclasses import dataclass, field


class ModelProvider(Enum):
    """Supported LLM model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    AZURE = "azure"
    COHERE = "cohere"
    GOOGLE = "google"
    CUSTOM = "custom"


class TaskType(Enum):
    """Types of tasks for model selection."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    STRATEGY = "strategy"
    CRITIQUE = "critique"
    REPORTING = "reporting"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    CODE = "code"
    GENERAL = "general"


@dataclass(frozen=True)
class Message:
    """
    Represents a message in a conversation.

    Attributes:
        role: The role of the message sender (system, user, assistant)
        content: The message content
        metadata: Optional additional data
    """
    role: str
    content: str
    metadata: Dict[str, Any]

    @classmethod
    def system(cls, content: str, **kwargs) -> "Message":
        """Create a system message."""
        return cls("system", content, kwargs)

    @classmethod
    def user(cls, content: str, **kwargs) -> "Message":
        """Create a user message."""
        return cls("user", content, kwargs)

    @classmethod
    def assistant(cls, content: str, **kwargs) -> "Message":
        """Create an assistant message."""
        return cls("assistant", content, kwargs)


@dataclass(frozen=True)
class ModelConfig:
    """
    Configuration for an LLM model.

    Attributes:
        model_name: The name of the model
        provider: The model provider
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0-2)
        top_p: Nucleus sampling threshold
        top_k: Top-k sampling
        frequency_penalty: Frequency penalty (-2 to 2)
        presence_penalty: Presence penalty (-2 to 2)
        timeout: Request timeout in seconds
    """
    model_name: str
    provider: ModelProvider
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = 40
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if not 0 <= self.top_p <= 1:
            raise ValueError("Top_p must be between 0 and 1")
        if not -2 <= self.frequency_penalty <= 2:
            raise ValueError("Frequency penalty must be between -2 and 2")
        if not -2 <= self.presence_penalty <= 2:
            raise ValueError("Presence penalty must be between -2 and 2")

    @classmethod
    def default(cls, model_name: str, provider: ModelProvider = ModelProvider.ANTHROPIC) -> "ModelConfig":
        """Create default configuration."""
        return cls(model_name, provider)

    @classmethod
    def deterministic(cls, model_name: str, provider: ModelProvider = ModelProvider.ANTHROPIC) -> "ModelConfig":
        """Create deterministic configuration (temperature=0)."""
        return cls(model_name, provider, temperature=0.0)

    @classmethod
    def creative(cls, model_name: str, provider: ModelProvider = ModelProvider.ANTHROPIC) -> "ModelConfig":
        """Create creative configuration (higher temperature)."""
        return cls(model_name, provider, temperature=1.2)


@dataclass(frozen=True)
class CompletionResponse:
    """
    Response from an LLM completion request.

    Attributes:
        content: The generated content
        model: The model used
        finish_reason: Why generation finished
        usage: Token usage information
        metadata: Additional response metadata
    """
    content: str
    model: str
    finish_reason: str
    usage: Dict[str, int]
    metadata: Dict[str, Any]

    @property
    def prompt_tokens(self) -> int:
        """Number of tokens in the prompt."""
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """Number of tokens in the completion."""
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.usage.get("total_tokens", 0)


@dataclass(frozen=True)
class EmbeddingResponse:
    """
    Response from an embedding request.

    Attributes:
        embedding: The embedding vector
        model: The model used
        dimensions: Number of dimensions
        metadata: Additional response metadata
    """
    embedding: List[float]
    model: str
    dimensions: int
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class TokenUsage:
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Combine token usage."""
        return TokenUsage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
        )


# ============================================================================
# LLM Provider Interface
# ============================================================================


class LLMProvider(ABC):
    """
    Base interface for LLM providers.

    All LLM implementations (OpenAI, Anthropic, etc.) must
    implement this interface to ensure interchangeability.
    """

    @property
    @abstractmethod
    def provider_type(self) -> ModelProvider:
        """Get the provider type."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        config: Optional[ModelConfig] = None,
    ) -> CompletionResponse:
        """
        Generate a completion from the model.

        Args:
            messages: List of messages in the conversation
            config: Model configuration

        Returns:
            CompletionResponse with generated content
        """
        pass

    @abstractmethod
    async def complete_stream(
        self,
        messages: List[Message],
        config: Optional[ModelConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming completion from the model.

        Args:
            messages: List of messages in the conversation
            config: Model configuration

        Yields:
            Chunks of the generated content
        """
        pass

    @abstractmethod
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """
        Generate an embedding for the given text.

        Args:
            text: Text to embed
            model: Optional model override

        Returns:
            EmbeddingResponse with the embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            model: Optional model override

        Returns:
            List of EmbeddingResponse objects
        """
        pass

    @abstractmethod
    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """
        Count tokens in text for a specific model.

        Args:
            text: Text to count tokens for
            model: Optional model override

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model information
        """
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """
        Validate that the API key is valid.

        Returns:
            True if valid, False otherwise
        """
        pass


# ============================================================================
# Multi-LLM Router Interface
# ============================================================================


class LLMRouter(ABC):
    """
    Interface for routing requests to appropriate LLM providers.

    The router selects the best model based on:
    - Task type
    - Complexity
    - Latency requirements
    - Cost considerations
    """

    @abstractmethod
    async def route(
        self,
        task_type: TaskType,
        messages: List[Message],
        config: Optional[ModelConfig] = None,
        prefer_fast: bool = False,
        prefer_cheap: bool = False,
    ) -> CompletionResponse:
        """
        Route a request to the appropriate model.

        Args:
            task_type: Type of task being performed
            messages: List of messages
            config: Optional configuration overrides
            prefer_fast: Prefer faster models
            prefer_cheap: Prefer cheaper models

        Returns:
            CompletionResponse from the selected model
        """
        pass

    @abstractmethod
    async def route_stream(
        self,
        task_type: TaskType,
        messages: List[Message],
        config: Optional[ModelConfig] = None,
        prefer_fast: bool = False,
        prefer_cheap: bool = False,
    ) -> AsyncIterator[str]:
        """
        Route a streaming request to the appropriate model.

        Args:
            task_type: Type of task being performed
            messages: List of messages
            config: Optional configuration overrides
            prefer_fast: Prefer faster models
            prefer_cheap: Prefer cheaper models

        Yields:
            Chunks of the generated content
        """
        pass

    @abstractmethod
    async def get_best_model(
        self,
        task_type: TaskType,
        prefer_fast: bool = False,
        prefer_cheap: bool = False,
    ) -> ModelConfig:
        """
        Get the best model configuration for a task type.

        Args:
            task_type: Type of task
            prefer_fast: Prefer faster models
            prefer_cheap: Prefer cheaper models

        Returns:
            ModelConfig for the best model
        """
        pass

    @abstractmethod
    def register_provider(self, provider: LLMProvider) -> None:
        """
        Register an LLM provider with the router.

        Args:
            provider: The provider to register
        """
        pass

    @abstractmethod
    def get_available_providers(self) -> List[ModelProvider]:
        """Get list of available providers."""
        pass

    @abstractmethod
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all providers."""
        pass


# ============================================================================
# Tool Calling Interface (for function-calling LLMs)
# ============================================================================


@dataclass(frozen=True)
class ToolDefinition:
    """
    Definition of a tool that can be called by an LLM.

    Attributes:
        name: Tool name
        description: Tool description
        parameters: JSON schema for parameters
        metadata: Additional tool metadata
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """
    A tool call made by an LLM.

    Attributes:
        tool_name: Name of the tool to call
        arguments: Arguments to pass to the tool
        call_id: Unique identifier for this call
    """
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str


class ToolCallingLLM(LLMProvider):
    """
    Extended LLM provider that supports tool calling.

    This allows LLMs to call functions/tools to perform actions.
    """

    @abstractmethod
    async def complete_with_tools(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        config: Optional[ModelConfig] = None,
        max_iterations: int = 10,
    ) -> CompletionResponse:
        """
        Generate a completion that can call tools.

        The LLM may request tool calls, which will be executed
        and results fed back to continue the conversation.

        Args:
            messages: List of messages
            tools: Available tools
            config: Model configuration
            max_iterations: Maximum tool-calling iterations

        Returns:
            Final CompletionResponse
        """
        pass

    @abstractmethod
    async def complete_with_tools_stream(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        config: Optional[ModelConfig] = None,
        max_iterations: int = 10,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming completion that can call tools.

        Args:
            messages: List of messages
            tools: Available tools
            config: Model configuration
            max_iterations: Maximum tool-calling iterations

        Yields:
            Chunks of the generated content
        """
        pass


# ============================================================================
# Export all interfaces
# ============================================================================


__all__ = [
    # Enums
    "ModelProvider",
    "TaskType",
    # Data classes
    "Message",
    "ModelConfig",
    "CompletionResponse",
    "EmbeddingResponse",
    "TokenUsage",
    "ToolDefinition",
    "ToolCall",
    # Interfaces
    "LLMProvider",
    "LLMRouter",
    "ToolCallingLLM",
]