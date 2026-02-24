#
# Copyright contributors to the agentic-ai-cyberres project
#
"""MCP client using stdio transport - Industry standard approach."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Exception raised for MCP client errors."""
    pass


class MCPStdioClient:
    """MCP client using stdio transport - compatible with all MCP servers.
    
    This is the industry-standard approach used by:
    - Claude Desktop
    - Bee-AI framework
    - Other production agentic systems
    
    The stdio transport is more reliable than HTTP/SSE for MCP communication.
    """
    
    def __init__(self, server_command: str = "cyberres-mcp", server_args: Optional[List[str]] = None,
                 server_env: Optional[Dict[str, str]] = None, timeout: float = 30.0):
        """Initialize MCP stdio client.
        
        Args:
            server_command: Command to start MCP server (default: "cyberres-mcp")
            server_args: Additional arguments for server command
            server_env: Environment variables for server process
            timeout: Request timeout in seconds
        """
        self.server_command = server_command
        self.server_args = server_args or []
        self.server_env = server_env
        self.timeout = timeout
        self.session: Optional[ClientSession] = None
        self._connected = False
        self._server_params: Optional[StdioServerParameters] = None
        self._stdio_context = None
        self._session_context = None
    
    async def connect(self) -> None:
        """Establish connection to MCP server using stdio transport."""
        try:
            logger.info(f"Starting MCP server: {self.server_command}")
            
            # Create server parameters for stdio transport
            self._server_params = StdioServerParameters(
                command=self.server_command,
                args=self.server_args,
                env=self.server_env  # Use provided environment or inherit
            )
            
            # Create stdio client context
            self._stdio_context = stdio_client(self._server_params)
            read, write = await self._stdio_context.__aenter__()
            
            # Create session context
            self._session_context = ClientSession(read, write)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session
            await self.session.initialize()
            
            self._connected = True
            logger.info(f"Connected to MCP server via stdio")
            
            # Discover available tools dynamically
            await self.discover_tools()
                    
        except Exception as e:
            raise MCPClientError(f"Error connecting to MCP server: {e}")
    
    async def discover_tools(self) -> Dict[str, Any]:
        """Discover available MCP tools dynamically.
        
        Returns:
            Dictionary mapping tool names to tool information
        """
        if not self._connected or not self.session:
            raise MCPClientError("Not connected to MCP server")
        
        try:
            # List available tools from MCP server
            tools_result = await self.session.list_tools()
            
            # Store tools in a dictionary for easy lookup
            self.available_tools = {}
            self.tool_descriptions = {}
            
            for tool in tools_result.tools:
                self.available_tools[tool.name] = tool
                self.tool_descriptions[tool.name] = tool.description if hasattr(tool, 'description') else ""
            
            logger.info(f"Discovered {len(self.available_tools)} MCP tools: {list(self.available_tools.keys())}")
            
            return {
                "tool_count": len(self.available_tools),
                "tools": list(self.available_tools.keys()),
                "descriptions": self.tool_descriptions
            }
            
        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
            raise MCPClientError(f"Error discovering tools: {e}")
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names.
        
        Returns:
            List of tool names
        """
        return list(getattr(self, 'available_tools', {}).keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available.
        
        Args:
            tool_name: Name of the tool to check
        
        Returns:
            True if tool is available, False otherwise
        """
        return tool_name in getattr(self, 'available_tools', {})
    
    def get_tool_description(self, tool_name: str) -> Optional[str]:
        """Get description of a tool.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Tool description or None if tool not found
        """
        return getattr(self, 'tool_descriptions', {}).get(tool_name)
    
    async def list_tools(self) -> List[Any]:
        """Get list of all tools with their full information.
        
        Returns:
            List of tool objects with name, description, and schema
        """
        if not self._connected or not self.session:
            raise MCPClientError("Not connected to MCP server")
        
        try:
            tools_result = await self.session.list_tools()
            return tools_result.tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise MCPClientError(f"Error listing tools: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
            
            self._connected = False
            self.session = None
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
        
        Returns:
            Tool response dictionary
        
        Raises:
            MCPClientError: If tool call fails
        """
        if not self._connected or not self.session:
            raise MCPClientError("Not connected to MCP server")
        
        try:
            logger.debug(f"Calling MCP tool: {tool_name}", extra={"arguments": arguments})
            
            # Call the tool using MCP SDK
            result = await self.session.call_tool(tool_name, arguments)
            
            logger.debug(f"Tool {tool_name} completed successfully")
            
            # Extract content from result
            if hasattr(result, 'content') and result.content:
                # Parse the content - it's usually a list of content items
                content_items = result.content
                if content_items:
                    # Get the first text content
                    for item in content_items:
                        if hasattr(item, 'type') and item.type == 'text':
                            import json
                            try:
                                return json.loads(item.text)
                            except json.JSONDecodeError:
                                return {"text": item.text}
                    
                    # If no text content, return raw content
                    return {"content": [{"type": item.type, "text": str(item)} for item in content_items]}
            
            return {"result": str(result)}
            
        except Exception as e:
            raise MCPClientError(f"Error calling tool {tool_name}: {e}")
    
    # Network Tools
    async def tcp_portcheck(
        self,
        host: str,
        ports: List[int],
        timeout_s: float = 1.0
    ) -> Dict[str, Any]:
        """Check TCP port connectivity."""
        return await self.call_tool("tcp_portcheck", {
            "host": host,
            "ports": ports,
            "timeout_s": timeout_s
        })
    
    # VM Tools
    async def vm_linux_uptime_load_mem(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get VM uptime, load, and memory information."""
        args = {"host": host, "username": username}
        if password:
            args["password"] = password
        if key_path:
            args["key_path"] = key_path
        return await self.call_tool("vm_linux_uptime_load_mem", args)
    
    async def vm_linux_disk_usage(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get VM disk usage information."""
        args = {"host": host, "username": username}
        if password:
            args["password"] = password
        if key_path:
            args["key_path"] = key_path
        return await self.call_tool("vm_linux_disk_usage", args)
    
    # Oracle DB Tools
    async def oracle_db_connectivity(
        self,
        host: str,
        port: int,
        service_name: str,
        db_username: str,
        db_password: str,
        ssh_username: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test Oracle database connectivity."""
        args = {
            "host": host,
            "port": port,
            "service_name": service_name,
            "db_username": db_username,
            "db_password": db_password
        }
        if ssh_username:
            args["ssh_username"] = ssh_username
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        return await self.call_tool("oracle_db_connectivity", args)
    
    # MongoDB Tools
    async def mongo_db_connectivity(
        self,
        host: str,
        port: int,
        db_username: str,
        db_password: str,
        auth_db: str = "admin",
        ssh_username: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test MongoDB connectivity."""
        args = {
            "host": host,
            "port": port,
            "db_username": db_username,
            "db_password": db_password,
            "auth_db": auth_db
        }
        if ssh_username:
            args["ssh_username"] = ssh_username
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        return await self.call_tool("mongo_db_connectivity", args)
    
    # Workload Discovery Tools
    async def workload_scan_ports(
        self,
        host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        port_range: str = "1-65535",
        scan_type: str = "common"
    ) -> Dict[str, Any]:
        """Scan ports on a host."""
        args = {
            "host": host,
            "ssh_user": ssh_user,
            "port_range": port_range,
            "scan_type": scan_type
        }
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        return await self.call_tool("workload_scan_ports", args)
    
    async def workload_scan_processes(
        self,
        host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scan running processes on a host."""
        args = {"host": host, "ssh_user": ssh_user}
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        return await self.call_tool("workload_scan_processes", args)
    
    async def workload_detect_applications(
        self,
        host: str,
        ports: List[Dict[str, Any]],
        processes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect applications based on ports and processes."""
        return await self.call_tool("workload_detect_applications", {
            "host": host,
            "ports": ports,
            "processes": processes
        })
    
    async def workload_aggregate_results(
        self,
        host: str,
        port_results: Dict[str, Any],
        process_results: Dict[str, Any],
        app_detections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate workload discovery results."""
        return await self.call_tool("workload_aggregate_results", {
            "host": host,
            "port_results": port_results,
            "process_results": process_results,
            "app_detections": app_detections
        })

# Made with Bob
