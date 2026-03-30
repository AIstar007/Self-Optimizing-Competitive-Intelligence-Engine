"""
Domain Tool Provider Interface

Defines the contract for agent tool discovery and execution.
The infrastructure layer implements this interface.

Following Dependency Inversion Principle - the domain layer
defines what it needs from tool systems without coupling
to specific implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Set, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    SEARCH = "search"
    BROWSER = "browser"
    SCRAPER = "scraper"
    DATABASE = "database"
    API = "api"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    FILE = "file"
    MEMORY = "memory"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    CUSTOM = "custom"


class ToolStatus(Enum):
    """Status of a tool."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass(frozen=True)
class ToolParameter:
    """
    Definition of a tool parameter.

    Attributes:
        name: Parameter name
        type: Parameter type (string, number, boolean, etc.)
        description: Parameter description
        required: Whether the parameter is required
        default: Default value
        enum: Optional list of allowed values
    """
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


@dataclass(frozen=True)
class ToolDefinition:
    """
    Definition of a tool available to agents.

    Attributes:
        name: Unique tool name
        display_name: Human-readable display name
        description: Tool description
        category: Tool category
        parameters: List of tool parameters
        examples: Usage examples
        status: Tool status
        requires_auth: Whether the tool requires authentication
        requires_api_key: Whether the tool requires an API key
        metadata: Additional tool metadata
        version: Tool version
        author: Tool author
        tags: Tags for filtering
    """
    name: str
    display_name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    examples: List[str]
    status: ToolStatus = ToolStatus.AVAILABLE
    requires_auth: bool = False
    requires_api_key: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    author: str = "system"
    tags: Set[str] = field(default_factory=set)

    @property
    def required_parameters(self) -> List[ToolParameter]:
        """Get list of required parameters."""
        return [p for p in self.parameters if p.required]

    @property
    def optional_parameters(self) -> List[ToolParameter]:
        """Get list of optional parameters."""
        return [p for p in self.parameters if not p.required]

    def get_parameter(self, name: str) -> Optional[ToolParameter]:
        """Get a parameter by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def has_parameter(self, name: str) -> bool:
        """Check if a parameter exists."""
        return self.get_parameter(name) is not None


@dataclass(frozen=True)
class ToolExecutionRequest:
    """
    A request to execute a tool.

    Attributes:
        tool_name: Name of the tool to execute
        arguments: Arguments to pass to the tool
        context: Optional execution context
        request_id: Unique request identifier
        requested_by: Agent or system making the request
    """
    tool_name: str
    arguments: Dict[str, Any]
    context: Optional[Dict[str, Any]]
    request_id: str
    requested_by: str = "unknown"


@dataclass(frozen=True)
class ToolExecutionResult:
    """
    Result of a tool execution.

    Attributes:
        success: Whether execution succeeded
        data: Result data (if successful)
        error: Error message (if failed)
        error_type: Type of error (if failed)
        metadata: Additional execution metadata
        execution_time_ms: Execution time in milliseconds
        tool_name: Name of the executed tool
        request_id: Request identifier
    """
    success: bool
    data: Optional[Any]
    error: Optional[str]
    error_type: Optional[str]
    metadata: Dict[str, Any]
    execution_time_ms: int
    tool_name: str
    request_id: str

    @classmethod
    def success_result(
        cls,
        data: Any,
        tool_name: str,
        request_id: str,
        execution_time_ms: int,
        **metadata,
    ) -> "ToolExecutionResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            error=None,
            error_type=None,
            metadata=metadata,
            execution_time_ms=execution_time_ms,
            tool_name=tool_name,
            request_id=request_id,
        )

    @classmethod
    def failure_result(
        cls,
        error: str,
        error_type: str,
        tool_name: str,
        request_id: str,
        execution_time_ms: int,
        **metadata,
    ) -> "ToolExecutionResult":
        """Create a failed result."""
        return cls(
            success=False,
            data=None,
            error=error,
            error_type=error_type,
            metadata=metadata,
            execution_time_ms=execution_time_ms,
            tool_name=tool_name,
            request_id=request_id,
        )


@dataclass(frozen=True)
class ToolUsageStats:
    """
    Statistics about tool usage.

    Attributes:
        tool_name: Tool name
        total_calls: Total number of calls
        successful_calls: Number of successful calls
        failed_calls: Number of failed calls
        avg_execution_time_ms: Average execution time
        last_used: When the tool was last used
        success_rate: Success rate (0-1)
    """
    tool_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    avg_execution_time_ms: float
    last_used: Optional[datetime]
    success_rate: float


# ============================================================================
# Tool Registry Interface
# ============================================================================


class ToolRegistry(ABC):
    """
    Interface for tool discovery and management.

    Provides methods for:
    - Registering tools
    - Discovering available tools
    - Getting tool definitions
    """

    @abstractmethod
    async def register(self, tool: ToolDefinition) -> None:
        """
        Register a tool with the registry.

        Args:
            tool: Tool definition to register
        """
        pass

    @abstractmethod
    async def register_batch(self, tools: List[ToolDefinition]) -> None:
        """
        Register multiple tools.

        Args:
            tools: List of tool definitions to register
        """
        pass

    @abstractmethod
    async def unregister(self, tool_name: str) -> bool:
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to unregister

        Returns:
            True if unregistered, False if not found
        """
        pass

    @abstractmethod
    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool definition if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
        tags: Optional[Set[str]] = None,
    ) -> List[ToolDefinition]:
        """
        List available tools with optional filters.

        Args:
            category: Filter by category
            status: Filter by status
            tags: Filter by tags (must have all specified tags)

        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def search_tools(
        self,
        query: str,
        limit: int = 10,
    ) -> List[ToolDefinition]:
        """
        Search for tools by name or description.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching tool definitions
        """
        pass

    @abstractmethod
    async def get_categories(self) -> List[ToolCategory]:
        """Get list of available tool categories."""
        pass

    @abstractmethod
    async def get_tools_by_category(
        self,
        category: ToolCategory,
    ) -> List[ToolDefinition]:
        """
        Get tools by category.

        Args:
            category: Tool category

        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def exists(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool exists
        """
        pass

    @abstractmethod
    async def count(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
    ) -> int:
        """
        Count tools with optional filters.

        Args:
            category: Filter by category
            status: Filter by status

        Returns:
            Number of tools
        """
        pass


# ============================================================================
# Tool Executor Interface
# ============================================================================


class ToolExecutor(ABC):
    """
    Interface for executing tools.

    Provides methods for:
    - Executing tools
    - Validating tool arguments
    - Handling tool errors
    """

    @abstractmethod
    async def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        """
        Execute a tool.

        Args:
            request: Tool execution request

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    async def execute_batch(
        self,
        requests: List[ToolExecutionRequest],
        parallel: bool = True,
    ) -> List[ToolExecutionResult]:
        """
        Execute multiple tools.

        Args:
            requests: List of execution requests
            parallel: Execute in parallel if True

        Returns:
            List of execution results
        """
        pass

    @abstractmethod
    async def validate_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Validate tool arguments.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    async def get_required_arguments(
        self,
        tool_name: str,
    ) -> List[ToolParameter]:
        """
        Get required arguments for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of required parameters
        """
        pass

    @abstractmethod
    async def get_execution_stats(
        self,
        tool_name: str,
    ) -> Optional[ToolUsageStats]:
        """
        Get usage statistics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Usage statistics if tool exists
        """
        pass

    @abstractmethod
    async def get_all_stats(self) -> Dict[str, ToolUsageStats]:
        """
        Get usage statistics for all tools.

        Returns:
            Dictionary mapping tool names to stats
        """
        pass


# ============================================================================
# Custom Tool Registration
# ============================================================================


class ToolFunction:
    """
    Wrapper for custom tool functions.

    Allows Python functions to be registered as tools.
    """

    def __init__(
        self,
        definition: ToolDefinition,
        func: Callable[..., Awaitable[Any]],
    ):
        self.definition = definition
        self.func = func

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool function."""
        return await self.func(**arguments)


# ============================================================================
# Export all interfaces
# ============================================================================


__all__ = [
    # Enums
    "ToolCategory",
    "ToolStatus",
    # Data classes
    "ToolParameter",
    "ToolDefinition",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolUsageStats",
    "ToolFunction",
    # Interfaces
    "ToolRegistry",
    "ToolExecutor",
]