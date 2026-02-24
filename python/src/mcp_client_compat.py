#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Compatibility wrapper for MCP client - bridges old and new implementations.

This module provides backward compatibility for code using the old mcp_client_context
while internally using the new MCPStdioClient with dynamic tool discovery.

This is a temporary bridge during the Phase 4 incremental migration.
"""

import logging
from contextlib import asynccontextmanager
from mcp_stdio_client import MCPStdioClient, MCPClientError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def mcp_client_context(server_url_or_command: str):
    """Compatibility wrapper for MCPStdioClient.
    
    Provides the same async context manager interface as the old mcp_client_context
    but uses the new stdio transport with dynamic tool discovery.
    
    Args:
        server_url_or_command: Server URL (ignored, uses stdio transport)
    
    Yields:
        MCPStdioClient: Connected MCP client with dynamic tool discovery
    
    Example:
        async with mcp_client_context("http://localhost:3000") as client:
            # Client is connected and tools are discovered
            tools = client.get_available_tools()
            result = await client.call_tool("discover_applications", {...})
    
    Note:
        This is a compatibility layer. The server_url parameter is ignored
        because we use stdio transport which doesn't need a URL.
        
        In Week 2, this will be replaced with direct MCPStdioClient usage.
    """
    logger.info("Creating MCP client via compatibility wrapper")
    logger.debug(f"Ignoring server_url parameter: {server_url_or_command}")
    
    # Create stdio client
    # Note: We use a fixed command for now, but this could be made configurable
    client = MCPStdioClient(
        server_command="uv",
        server_args=["run", "mcp", "dev", "../cyberres-mcp/src/cyberres_mcp/server.py"]
    )
    
    try:
        # Connect to MCP server (automatically discovers tools)
        await client.connect()
        logger.info("MCP client connected via stdio transport")
        
        # Log discovered tools
        available_tools = client.get_available_tools()
        logger.info(f"Discovered {len(available_tools)} MCP tools")
        logger.debug(f"Available tools: {available_tools}")
        
        # Yield the connected client
        yield client
        
    except Exception as e:
        logger.error(f"Error in MCP client context: {e}")
        raise MCPClientError(f"MCP client error: {e}")
    
    finally:
        # Disconnect from MCP server
        try:
            await client.disconnect()
            logger.info("MCP client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting MCP client: {e}")


# Export for backward compatibility
__all__ = ['mcp_client_context', 'MCPClientError']


# Made with Bob