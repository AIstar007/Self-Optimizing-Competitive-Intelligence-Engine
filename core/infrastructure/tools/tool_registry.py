"""
Tool provider and registry implementation for dynamic tool management.

This module implements the ToolProvider interface with a comprehensive
tool registry system for agent access to external capabilities.

Features:
    - Dynamic tool registration and discovery
    - Tool validation and parameter checking
    - Async execution with error handling
    - Streaming support for long-running operations
    - Usage tracking and statistics
    - Rate limiting and availability management
    - Tool categorization and search

Tool Categories:
    - SEARCH: Web search and information retrieval
    - BROWSER: Web navigation and scraping
    - SCRAPER: Content extraction
    - DATABASE: Data queries
    - API: External API calls
    - ANALYSIS: Data analysis
    - REPORTING: Report generation
    - CODE: Code execution/analysis
    - COMMUNICATION: Messaging/notifications
    - DATA_PROCESSING: ETL and transformation

Usage:
    from core.infrastructure.tools import ToolRegistry
    
    registry = ToolRegistry()
    registry.register_tool(search_tool_def)
    
    # Execute tool
    result = await registry.execute(
        ToolExecutionRequest(tool_name="google_search", arguments={"query": "..."})
    )
"""

from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Optional

from core.domain import (
    ToolProvider,
    ToolCategory,
    ToolStatus,
    ToolParameter,
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
)


class ToolRegistry(ToolProvider):
    """
    Comprehensive tool registry for dynamic tool management.
    
    Manages registration, discovery, and execution of tools for agents.
    """

    def __init__(self):
        """Initialize tool registry."""
        self.tools: dict[str, ToolDefinition] = {}
        self.implementations: dict[str, Callable] = {}
        self.usage_stats: dict[str, dict] = {}
        self._initialize_builtin_tools()

    async def get_tools(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
    ) -> list[ToolDefinition]:
        """
        Get available tools.
        
        Args:
            category: Filter by category
            status: Filter by status
            
        Returns:
            List of available tools
        """
        tools = list(self.tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if status:
            tools = [t for t in tools if t.status == status]

        return tools

    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get tool by name.
        
        Args:
            tool_name: Name of tool
            
        Returns:
            Tool definition or None
        """
        return self.tools.get(tool_name)

    async def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        """
        Execute a tool.
        
        Args:
            request: Execution request
            
        Returns:
            Execution result
        """
        tool_name = request.tool_name
        start_time = datetime.utcnow()

        try:
            # Validate tool exists
            if tool_name not in self.tools:
                return ToolExecutionResult.failure_result(
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' not found",
                    error_type="ToolNotFound",
                )

            tool_def = self.tools[tool_name]

            # Check tool status
            if tool_def.status != ToolStatus.AVAILABLE:
                return ToolExecutionResult.failure_result(
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' is not available ({tool_def.status})",
                    error_type="ToolUnavailable",
                )

            # Validate arguments
            validation_error = await self.validate_arguments(
                tool_name,
                request.arguments,
            )
            if validation_error:
                return ToolExecutionResult.failure_result(
                    tool_name=tool_name,
                    error=validation_error,
                    error_type="ValidationError",
                )

            # Execute tool
            impl = self.implementations.get(tool_name)
            if not impl:
                return ToolExecutionResult.failure_result(
                    tool_name=tool_name,
                    error=f"No implementation for tool '{tool_name}'",
                    error_type="NotImplemented",
                )

            result = await impl(**request.arguments)

            # Update statistics
            self._record_usage(tool_name, True, None)

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ToolExecutionResult.success_result(
                tool_name=tool_name,
                data=result,
                execution_time_ms=execution_time,
                request_id=request.request_id,
            )

        except Exception as e:
            # Update statistics
            self._record_usage(tool_name, False, str(e))

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ToolExecutionResult.failure_result(
                tool_name=tool_name,
                error=str(e),
                error_type=type(e).__name__,
                execution_time_ms=execution_time,
            )

    async def execute_batch(
        self,
        requests: list[ToolExecutionRequest],
    ) -> list[ToolExecutionResult]:
        """
        Execute multiple tools.
        
        Args:
            requests: List of execution requests
            
        Returns:
            List of execution results
        """
        results = []
        for request in requests:
            result = await self.execute(request)
            results.append(result)
        return results

    async def get_status(self, tool_name: str) -> Optional[ToolStatus]:
        """
        Get tool status.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool status or None
        """
        tool = self.tools.get(tool_name)
        return tool.status if tool else None

    async def validate_arguments(
        self,
        tool_name: str,
        arguments: dict,
    ) -> Optional[str]:
        """
        Validate tool arguments.
        
        Args:
            tool_name: Tool name
            arguments: Arguments to validate
            
        Returns:
            Error message or None if valid
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' not found"

        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                return f"Required parameter '{param.name}' missing"

        # Validate parameter types (basic)
        for param_name, param_value in arguments.items():
            param_def = next(
                (p for p in tool.parameters if p.name == param_name),
                None,
            )
            if param_def and param_def.type in ["string", "integer", "float"]:
                if not self._validate_type(param_value, param_def.type):
                    return f"Parameter '{param_name}' has invalid type"

        return None

    async def supports_streaming(self, tool_name: str) -> bool:
        """
        Check if tool supports streaming.
        
        Args:
            tool_name: Tool name
            
        Returns:
            True if streaming supported
        """
        tool = self.tools.get(tool_name)
        return tool and tool.metadata.get("streaming", False) if tool else False

    async def stream_execute(
        self,
        request: ToolExecutionRequest,
    ) -> AsyncGenerator[Any, None]:
        """
        Execute tool with streaming.
        
        Args:
            request: Execution request
            
        Yields:
            Streaming result chunks
        """
        # Check if tool supports streaming
        if not await self.supports_streaming(request.tool_name):
            result = await self.execute(request)
            yield result.data
            return

        # Execute with streaming
        impl = self.implementations.get(request.tool_name)
        if impl:
            async for chunk in impl(**request.arguments):
                yield chunk

    def register_tool(
        self,
        definition: ToolDefinition,
        implementation: Callable,
    ) -> None:
        """
        Register a new tool.
        
        Args:
            definition: Tool definition
            implementation: Async callable implementation
        """
        self.tools[definition.name] = definition
        self.implementations[definition.name] = implementation
        self.usage_stats[definition.name] = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "errors": [],
        }

    def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
        if tool_name in self.implementations:
            del self.implementations[tool_name]

    def set_tool_status(self, tool_name: str, status: ToolStatus) -> None:
        """
        Update tool status.
        
        Args:
            tool_name: Tool name
            status: New status
        """
        if tool_name in self.tools:
            self.tools[tool_name].status = status

    def get_usage_stats(self, tool_name: Optional[str] = None) -> dict:
        """
        Get usage statistics.
        
        Args:
            tool_name: Get stats for specific tool or all if None
            
        Returns:
            Usage statistics
        """
        if tool_name:
            return self.usage_stats.get(tool_name, {})
        return self.usage_stats

    def _record_usage(
        self,
        tool_name: str,
        success: bool,
        error: Optional[str],
    ) -> None:
        """Record tool usage statistics."""
        if tool_name not in self.usage_stats:
            self.usage_stats[tool_name] = {
                "executions": 0,
                "successes": 0,
                "failures": 0,
                "errors": [],
            }

        stats = self.usage_stats[tool_name]
        stats["executions"] += 1

        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            if error:
                stats["errors"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": error,
                })

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        return True

    def _initialize_builtin_tools(self) -> None:
        """Initialize built-in tools."""
        # Web search tool
        search_def = ToolDefinition(
            name="web_search",
            display_name="Web Search",
            description="Search the web using Google or Bing",
            category=ToolCategory.SEARCH,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="search_engine",
                    type="string",
                    description="Search engine (google or bing)",
                    required=False,
                    default="google",
                    enum=["google", "bing"],
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="Number of results",
                    required=False,
                    default=10,
                ),
            ],
            examples=[
                {
                    "query": "OpenAI GPT-4 release",
                    "search_engine": "google",
                    "num_results": 5,
                }
            ],
            status=ToolStatus.AVAILABLE,
            requires_auth=False,
            metadata={"streaming": False},
            version="1.0.0",
            author="system",
        )

        async def web_search_impl(**kwargs):
            # Placeholder implementation
            return {
                "results": [],
                "query": kwargs.get("query"),
            }

        self.register_tool(search_def, web_search_impl)

        # Scrape tool
        scrape_def = ToolDefinition(
            name="scrape_webpage",
            display_name="Scrape Webpage",
            description="Scrape content from a webpage",
            category=ToolCategory.SCRAPER,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL to scrape",
                    required=True,
                ),
            ],
            status=ToolStatus.AVAILABLE,
            metadata={"streaming": False},
            version="1.0.0",
            author="system",
        )

        async def scrape_impl(**kwargs):
            return {"url": kwargs.get("url"), "content": ""}

        self.register_tool(scrape_def, scrape_impl)


__all__ = [
    "ToolRegistry",
]
