"""
Dynamic MCP Integration Package

Runtime tool discovery and invocation for MCP servers without hardcoding.
Provides schema-driven, LLM-friendly interface for dynamic tool usage.

Main Components:
- DynamicMCPClient: Unified client interface
- ToolRegistry: Tool schema storage and management
- ToolDiscoveryEngine: Runtime tool discovery
- DynamicToolInvoker: Schema-driven tool invocation
- MCPConnectionManager: Connection lifecycle management

Quick Start:
    >>> from agents.mcp_dynamic import DynamicMCPClient
    >>> 
    >>> # Create and connect
    >>> client = DynamicMCPClient(server_path="python/cyberres-mcp")
    >>> await client.connect()
    >>> 
    >>> # Discover tools
    >>> tools = await client.discover_tools()
    >>> 
    >>> # Invoke a tool
    >>> result = await client.invoke_tool(
    ...     "discover_workload",
    ...     {"host": "9.11.69.88", "ssh_user": "admin"}
    ... )
    >>> 
    >>> # Disconnect
    >>> await client.disconnect()

Context Manager Usage:
    >>> async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
    ...     tools = await client.discover_tools()
    ...     result = await client.invoke_tool("tool_name", {...})
"""

from .models import (
    ToolSchema,
    ToolMetadata,
    ToolResult,
    ParameterInfo,
    ToolInvocation,
    ToolChange,
)

from .connection_manager import (
    MCPConnectionManager,
    ConnectionConfig,
    ConnectionState,
)

from .tool_discovery import ToolDiscoveryEngine

from .tool_registry import ToolRegistry

from .tool_invoker import DynamicToolInvoker

from .client import DynamicMCPClient, create_client

__all__ = [
    # Main client
    "DynamicMCPClient",
    "create_client",
    
    # Core components
    "MCPConnectionManager",
    "ToolDiscoveryEngine",
    "ToolRegistry",
    "DynamicToolInvoker",
    
    # Data models
    "ToolSchema",
    "ToolMetadata",
    "ToolResult",
    "ParameterInfo",
    "ToolInvocation",
    "ToolChange",
    
    # Configuration
    "ConnectionConfig",
    "ConnectionState",
]

__version__ = "1.0.0"

# Made with Bob
