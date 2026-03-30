"""
Tool infrastructure module for dynamic agent capabilities.

Provides a comprehensive tool registry system for agents to discover and execute
external capabilities including:
    - Web searching and scraping
    - API calls
    - Data analysis
    - Report generation
    - Code execution
    - Notifications

Features:
    - Dynamic tool registration
    - Parameter validation
    - Async execution
    - Streaming support
    - Usage tracking
    - Status management
    - Error handling

Usage:
    from core.infrastructure.tools import ToolRegistry
    
    registry = ToolRegistry()
    
    # Get available tools
    tools = await registry.get_tools(category=ToolCategory.SEARCH)
    
    # Execute tool
    request = ToolExecutionRequest(
        tool_name="web_search",
        arguments={"query": "competitive intelligence"}
    )
    result = await registry.execute(request)
    
    # Check statistics
    stats = registry.get_usage_stats("web_search")
"""

from core.infrastructure.tools.tool_registry import ToolRegistry

__all__ = [
    "ToolRegistry",
]
