#
# Copyright contributors to the agentic-ai-cyberres project
#
"""MCP client integration for recovery validation agent."""

import logging
from typing import Dict, Any, List, Optional
import httpx
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Exception raised for MCP client errors."""
    pass


class MCPClient:
    """Client for interacting with the cyberres-mcp server."""
    
    def __init__(self, server_url: str, timeout: float = 30.0):
        """Initialize MCP client.
        
        Args:
            server_url: URL of the MCP server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Establish connection to MCP server."""
        try:
            self.client = httpx.AsyncClient(timeout=self.timeout)
            # Test connection
            response = await self.client.get(f"{self.server_url}/health", timeout=5.0)
            if response.status_code == 200:
                self._connected = True
                logger.info(f"Connected to MCP server at {self.server_url}")
            else:
                raise MCPClientError(f"MCP server returned status {response.status_code}")
        except httpx.ConnectError as e:
            raise MCPClientError(f"Failed to connect to MCP server: {e}")
        except Exception as e:
            raise MCPClientError(f"Error connecting to MCP server: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        if self.client:
            await self.client.aclose()
            self._connected = False
            logger.info("Disconnected from MCP server")
    
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
        if not self._connected or not self.client:
            raise MCPClientError("Not connected to MCP server")
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            logger.debug(f"Calling MCP tool: {tool_name}", extra={"arguments": arguments})
            
            response = await self.client.post(
                f"{self.server_url}/",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise MCPClientError(f"Tool call failed with status {response.status_code}")
            
            result = response.json()
            
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise MCPClientError(f"Tool {tool_name} failed: {error_msg}")
            
            tool_result = result.get("result", {})
            logger.debug(f"Tool {tool_name} completed successfully")
            
            return tool_result
            
        except httpx.HTTPError as e:
            raise MCPClientError(f"HTTP error calling tool {tool_name}: {e}")
        except Exception as e:
            raise MCPClientError(f"Error calling tool {tool_name}: {e}")
    
    # Network Tools
    async def tcp_portcheck(
        self,
        host: str,
        ports: List[int],
        timeout_s: float = 1.0
    ) -> Dict[str, Any]:
        """Check TCP port connectivity.
        
        Args:
            host: Hostname or IP address
            ports: List of ports to check
            timeout_s: Timeout per port in seconds
        
        Returns:
            Port check results
        """
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
        """Get VM uptime, load, and memory information.
        
        Args:
            host: VM hostname or IP
            username: SSH username
            password: SSH password (optional)
            key_path: SSH key path (optional)
        
        Returns:
            Uptime and memory information
        """
        args = {"host": host, "username": username}
        if password:
            args["password"] = password
        if key_path:
            args["key_path"] = key_path
        
        return await self.call_tool("vm_linux_uptime_load_mem", args)
    
    async def vm_linux_fs_usage(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get VM filesystem usage.
        
        Args:
            host: VM hostname or IP
            username: SSH username
            password: SSH password (optional)
            key_path: SSH key path (optional)
        
        Returns:
            Filesystem usage information
        """
        args = {"host": host, "username": username}
        if password:
            args["password"] = password
        if key_path:
            args["key_path"] = key_path
        
        return await self.call_tool("vm_linux_fs_usage", args)
    
    async def vm_linux_services(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        required: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Check VM services status.
        
        Args:
            host: VM hostname or IP
            username: SSH username
            password: SSH password (optional)
            key_path: SSH key path (optional)
            required: List of required services
        
        Returns:
            Service status information
        """
        args = {"host": host, "username": username}
        if password:
            args["password"] = password
        if key_path:
            args["key_path"] = key_path
        if required:
            args["required"] = required
        
        return await self.call_tool("vm_linux_services", args)
    
    # Oracle DB Tools
    async def db_oracle_connect(
        self,
        dsn: Optional[str] = None,
        host: Optional[str] = None,
        port: int = 1521,
        service: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Connect to Oracle database.
        
        Args:
            dsn: Oracle DSN string (optional)
            host: Database host (optional)
            port: Database port
            service: Service name (optional)
            user: Database username
            password: Database password
        
        Returns:
            Connection and instance information
        """
        args = {}
        if dsn:
            args["dsn"] = dsn
        if host:
            args["host"] = host
        if port:
            args["port"] = port
        if service:
            args["service"] = service
        if user:
            args["user"] = user
        if password:
            args["password"] = password
        
        return await self.call_tool("db_oracle_connect", args)
    
    async def db_oracle_tablespaces(
        self,
        dsn: str,
        user: str,
        password: str
    ) -> Dict[str, Any]:
        """Get Oracle tablespace usage.
        
        Args:
            dsn: Oracle DSN string
            user: Database username
            password: Database password
        
        Returns:
            Tablespace usage information
        """
        return await self.call_tool("db_oracle_tablespaces", {
            "dsn": dsn,
            "user": user,
            "password": password
        })
    
    async def db_oracle_discover_and_validate(
        self,
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        oracle_user: Optional[str] = None,
        oracle_password: Optional[str] = None,
        lsnrctl_path: str = "lsnrctl",
        sudo_oracle: bool = False
    ) -> Dict[str, Any]:
        """Discover and validate Oracle database.
        
        Args:
            ssh_host: SSH host
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH key path (optional)
            oracle_user: Oracle database username (optional)
            oracle_password: Oracle database password (optional)
            lsnrctl_path: Path to lsnrctl command
            sudo_oracle: Use sudo to run as oracle user
        
        Returns:
            Discovery and validation results
        """
        args = {
            "ssh_host": ssh_host,
            "ssh_user": ssh_user,
            "lsnrctl_path": lsnrctl_path,
            "sudo_oracle": sudo_oracle
        }
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        if oracle_user:
            args["oracle_user"] = oracle_user
        if oracle_password:
            args["oracle_password"] = oracle_password
        
        return await self.call_tool("db_oracle_discover_and_validate", args)
    
    # MongoDB Tools
    async def db_mongo_connect(
        self,
        uri: Optional[str] = None,
        host: Optional[str] = None,
        port: int = 27017,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "admin"
    ) -> Dict[str, Any]:
        """Connect to MongoDB.
        
        Args:
            uri: MongoDB connection URI (optional)
            host: MongoDB host (optional)
            port: MongoDB port
            user: MongoDB username (optional)
            password: MongoDB password (optional)
            database: Database name
        
        Returns:
            Connection information
        """
        args = {"port": port, "database": database}
        if uri:
            args["uri"] = uri
        if host:
            args["host"] = host
        if user:
            args["user"] = user
        if password:
            args["password"] = password
        
        return await self.call_tool("db_mongo_connect", args)
    
    async def db_mongo_rs_status(self, uri: str) -> Dict[str, Any]:
        """Get MongoDB replica set status.
        
        Args:
            uri: MongoDB connection URI
        
        Returns:
            Replica set status
        """
        return await self.call_tool("db_mongo_rs_status", {"uri": uri})
    
    async def db_mongo_ssh_ping(
        self,
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        port: int = 27017,
        mongo_user: Optional[str] = None,
        mongo_password: Optional[str] = None,
        auth_db: str = "admin",
        mongosh_path: str = "mongosh"
    ) -> Dict[str, Any]:
        """Ping MongoDB via SSH.
        
        Args:
            ssh_host: SSH host
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH key path (optional)
            port: MongoDB port
            mongo_user: MongoDB username (optional)
            mongo_password: MongoDB password (optional)
            auth_db: Authentication database
            mongosh_path: Path to mongosh command
        
        Returns:
            Ping results
        """
        args = {
            "ssh_host": ssh_host,
            "ssh_user": ssh_user,
            "port": port,
            "auth_db": auth_db,
            "mongosh_path": mongosh_path
        }
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        if mongo_user:
            args["mongo_user"] = mongo_user
        if mongo_password:
            args["mongo_password"] = mongo_password
        
        return await self.call_tool("db_mongo_ssh_ping", args)
    
    async def validate_collection(
        self,
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        port: int = 27017,
        mongo_user: Optional[str] = None,
        mongo_password: Optional[str] = None,
        auth_db: str = "admin",
        db_name: str = "admin",
        collection: str = "",
        full: bool = True,
        mongosh_path: str = "mongosh"
    ) -> Dict[str, Any]:
        """Validate MongoDB collection.
        
        Args:
            ssh_host: SSH host
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH key path (optional)
            port: MongoDB port
            mongo_user: MongoDB username (optional)
            mongo_password: MongoDB password (optional)
            auth_db: Authentication database
            db_name: Database name
            collection: Collection name
            full: Perform full validation
            mongosh_path: Path to mongosh command
        
        Returns:
            Collection validation results
        """
        args = {
            "ssh_host": ssh_host,
            "ssh_user": ssh_user,
            "port": port,
            "auth_db": auth_db,
            "db_name": db_name,
            "collection": collection,
            "full": full,
            "mongosh_path": mongosh_path
        }
        if ssh_password:
            args["ssh_password"] = ssh_password
        if ssh_key_path:
            args["ssh_key_path"] = ssh_key_path
        if mongo_user:
            args["mongo_user"] = mongo_user
        if mongo_password:
            args["mongo_password"] = mongo_password
        
        return await self.call_tool("validate_collection", args)


@asynccontextmanager
async def mcp_client_context(server_url: str, timeout: float = 30.0):
    """Context manager for MCP client.
    
    Args:
        server_url: URL of the MCP server
        timeout: Request timeout in seconds
    
    Yields:
        Connected MCPClient instance
    """
    client = MCPClient(server_url, timeout)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()

# Made with Bob
