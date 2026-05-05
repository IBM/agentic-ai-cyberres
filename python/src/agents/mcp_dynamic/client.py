"""
Dynamic MCP Client

Main client interface that orchestrates all components for dynamic
MCP server integration with runtime tool discovery and invocation.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import ToolSchema, ToolMetadata, ToolResult, ToolInvocation
from .connection_manager import MCPConnectionManager, ConnectionConfig, ConnectionState
from .tool_discovery import ToolDiscoveryEngine
from .tool_registry import ToolRegistry
from .tool_invoker import DynamicToolInvoker

logger = logging.getLogger(__name__)


class DynamicMCPClient:
    """
    Unified client for dynamic MCP server integration.
    
    This is the main entry point for using dynamic MCP integration.
    It orchestrates connection management, tool discovery, registration,
    and invocation in a simple, unified interface.
    
    Features:
    - Automatic connection management
    - Runtime tool discovery
    - Schema-driven tool invocation
    - Hot-reload support
    - LLM-friendly tool descriptions
    - Comprehensive error handling
    
    Example:
        >>> # Initialize and connect
        >>> client = DynamicMCPClient(server_path="python/cyberres-mcp")
        >>> await client.connect()
        >>> 
        >>> # Discover tools
        >>> tools = await client.discover_tools()
        >>> print(f"Discovered {len(tools)} tools")
        >>> 
        >>> # Get LLM descriptions
        >>> llm_tools = client.get_llm_tool_descriptions()
        >>> 
        >>> # Invoke a tool
        >>> result = await client.invoke_tool(
        ...     "discover_workload",
        ...     {"host": "9.11.69.88", "ssh_user": "admin"}
        ... )
        >>> 
        >>> # Disconnect
        >>> await client.disconnect()
    """
    
    def __init__(
        self,
        server_path: str,
        transport: str = "stdio",
        command: str = "uv",
        auto_discover: bool = True,
        enable_hot_reload: bool = False,
        **kwargs
    ):
        """
        Initialize dynamic MCP client.
        
        Args:
            server_path: Path to MCP server directory
            transport: Transport type ("stdio" or "sse")
            command: Command to run MCP server
            auto_discover: Automatically discover tools on connect
            enable_hot_reload: Enable hot-reload watching
            **kwargs: Additional connection configuration options
        """
        self.server_path = Path(server_path)
        self.transport = transport
        self.auto_discover = auto_discover
        self.enable_hot_reload = enable_hot_reload
        
        # Create connection configuration
        self.connection_config = ConnectionConfig(
            server_path=str(self.server_path),
            transport=transport,
            command=command,
            **kwargs
        )
        
        # Initialize components
        self.connection_manager = MCPConnectionManager(self.connection_config)
        self.registry = ToolRegistry()
        self.discovery_engine: Optional[ToolDiscoveryEngine] = None
        self.tool_invoker: Optional[DynamicToolInvoker] = None
        
        # State
        self._initialized = False
        
        logger.info(
            f"Dynamic MCP client created for {server_path} "
            f"(transport={transport}, auto_discover={auto_discover})"
        )
    
    async def connect(self) -> bool:
        """
        Connect to MCP server and optionally discover tools.
        
        Returns:
            True if connection successful
        """
        logger.info("Connecting to MCP server...")
        
        # Connect to server
        success = await self.connection_manager.connect()
        if not success:
            logger.error("Failed to connect to MCP server")
            return False
        
        # Initialize components that need connection
        self.discovery_engine = ToolDiscoveryEngine(
            self.connection_manager,
            cache_enabled=True
        )
        
        self.tool_invoker = DynamicToolInvoker(
            self.connection_manager,
            self.registry,
            max_retries=3
        )
        
        self._initialized = True
        
        # Auto-discover tools if enabled
        if self.auto_discover:
            await self.discover_tools()
        
        # Start hot-reload if enabled
        if self.enable_hot_reload and self.discovery_engine:
            self.discovery_engine.start_watching()
            logger.info("Hot-reload watching enabled")
        
        logger.info("✓ Dynamic MCP client connected and ready")
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        logger.info("Disconnecting from MCP server...")
        
        # Stop hot-reload watching
        if self.discovery_engine:
            self.discovery_engine.stop_watching()
        
        # Disconnect
        await self.connection_manager.disconnect()
        
        self._initialized = False
        logger.info("✓ Disconnected from MCP server")
    
    async def discover_tools(self, force_refresh: bool = False) -> List[ToolSchema]:
        """
        Discover all available tools from MCP server.
        
        Args:
            force_refresh: Force refresh even if cached
            
        Returns:
            List of discovered tool schemas
        """
        if not self._initialized or not self.discovery_engine:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        logger.info("Discovering tools...")
        
        # Discover tools
        schemas = await self.discovery_engine.discover_tools(force_refresh)
        
        # Register all tools
        for schema in schemas:
            self.registry.register_tool(schema)
        
        logger.info(f"✓ Discovered and registered {len(schemas)} tools")
        return schemas
    
    async def refresh_tools(self) -> List[ToolSchema]:
        """
        Refresh tool list (force re-discovery).
        
        Returns:
            List of current tool schemas
        """
        return await self.discover_tools(force_refresh=True)
    
    async def invoke_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        validate: bool = True
    ) -> ToolResult:
        """
        Invoke a tool with given parameters.
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            validate: Validate parameters before invocation
            
        Returns:
            ToolResult with execution outcome
        """
        if not self._initialized or not self.tool_invoker:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        return await self.tool_invoker.invoke_tool(
            tool_name,
            parameters,
            validate=validate
        )
    
    async def invoke_tool_batch(
        self,
        invocations: List[ToolInvocation]
    ) -> List[ToolResult]:
        """
        Invoke multiple tools in batch.
        
        Args:
            invocations: List of tool invocations
            
        Returns:
            List of tool results
        """
        if not self._initialized or not self.tool_invoker:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        return await self.tool_invoker.invoke_tool_batch(invocations)
    
    def get_llm_tool_descriptions(self) -> List[Dict[str, Any]]:
        """
        Get tool descriptions in format suitable for LLM.
        
        Returns:
            List of tool descriptions for LLM context
        """
        return self.registry.get_llm_tool_descriptions()
    
    def list_tools(self) -> List[ToolMetadata]:
        """
        List all registered tools.
        
        Returns:
            List of tool metadata
        """
        return self.registry.list_tools()
    
    def list_tool_names(self) -> List[str]:
        """
        List all registered tool names.
        
        Returns:
            List of tool names
        """
        return self.registry.list_tool_names()
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive information about a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with tool information or None if not found
        """
        return self.registry.get_tool_info(tool_name)
    
    def search_tools(self, query: str) -> List[ToolMetadata]:
        """
        Search tools by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tool metadata
        """
        return self.registry.search_tools(query)
    
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self.connection_manager.is_connected()
    
    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.connection_manager.state
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.
        
        Returns:
            Dictionary with statistics from all components
        """
        stats = {
            "connected": self.is_connected(),
            "connection_state": self.connection_manager.state.value,
            "registry": self.registry.get_statistics(),
        }
        
        if self.discovery_engine:
            stats["discovery"] = self.discovery_engine.get_cache_stats()
        
        if self.tool_invoker:
            stats["invoker"] = self.tool_invoker.get_statistics()
        
        return stats
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    def __repr__(self) -> str:
        """String representation."""
        state = self.connection_manager.state.value
        tools_count = len(self.registry)
        return f"DynamicMCPClient(state={state}, tools={tools_count})"


# Convenience function for quick usage
async def create_client(
    server_path: str,
    **kwargs
) -> DynamicMCPClient:
    """
    Create and connect a dynamic MCP client.
    
    Args:
        server_path: Path to MCP server
        **kwargs: Additional client options
        
    Returns:
        Connected DynamicMCPClient
    """
    client = DynamicMCPClient(server_path, **kwargs)
    await client.connect()
    return client


# Made with Bob