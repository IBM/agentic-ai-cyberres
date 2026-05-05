"""
MCP Connection Manager

Handles connection lifecycle, health monitoring, and automatic reconnection
for MCP servers using stdio or SSE transport.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass
from pathlib import Path

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class ConnectionConfig:
    """Configuration for MCP connection."""
    server_path: str
    transport: str = "stdio"  # "stdio" or "sse"
    command: str = "uv"
    args: list[str] = None
    env: dict[str, str] = None
    connect_timeout: float = 30.0
    health_check_interval: float = 60.0
    max_reconnect_attempts: int = 5
    reconnect_backoff_base: float = 2.0
    reconnect_backoff_max: float = 60.0
    
    def __post_init__(self):
        if self.args is None:
            self.args = ["--directory", self.server_path, "run", "cyberres-mcp"]
        if self.env is None:
            import os
            self.env = {
                **os.environ,
                "MCP_TRANSPORT": "stdio",
                "PYTHONUNBUFFERED": "1",
                "LOG_LEVEL": "WARNING",
                "LOGURU_LEVEL": "WARNING",
                "FASTMCP_QUIET": "1",
                "SSH_STRICT_HOST_KEY_CHECKING": "false",
                "SSH_TRUST_UNKNOWN_HOSTS": "true",
            }


class MCPConnectionManager:
    """
    Manages MCP server connection lifecycle.
    
    Features:
    - Automatic connection establishment
    - Health monitoring with periodic checks
    - Automatic reconnection with exponential backoff
    - Connection state tracking
    - Graceful disconnection
    
    Example:
        >>> config = ConnectionConfig(server_path="python/cyberres-mcp")
        >>> manager = MCPConnectionManager(config)
        >>> await manager.connect()
        >>> if manager.is_connected():
        ...     # Use connection
        ...     pass
        >>> await manager.disconnect()
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize connection manager.
        
        Args:
            config: Connection configuration
        """
        self.config = config
        self._state = ConnectionState.DISCONNECTED
        self._client_context = None
        self._read_stream = None
        self._write_stream = None
        self._session: Optional[ClientSession] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._last_error: Optional[str] = None
        
        logger.info(f"Connection manager initialized for {config.server_path}")
    
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    @property
    def session(self) -> Optional[ClientSession]:
        """Get MCP session if connected."""
        return self._session
    
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._state == ConnectionState.CONNECTED and self._session is not None
    
    async def connect(self) -> bool:
        """
        Establish connection to MCP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected():
            logger.info("Already connected to MCP server")
            return True
        
        self._state = ConnectionState.CONNECTING
        logger.info(f"Connecting to MCP server at {self.config.server_path}...")
        
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env
            )
            
            # Establish connection with timeout
            self._client_context = stdio_client(server_params)
            
            # Enter context and get streams
            self._read_stream, self._write_stream = await asyncio.wait_for(
                self._client_context.__aenter__(),
                timeout=self.config.connect_timeout
            )
            
            # Create session
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()
            
            # Initialize session
            await self._session.initialize()
            
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0
            self._last_error = None
            
            logger.info("✓ Connected to MCP server successfully")
            
            # Start health check task
            self._start_health_check()
            
            return True
            
        except asyncio.TimeoutError:
            self._last_error = f"Connection timeout after {self.config.connect_timeout}s"
            logger.error(f"Failed to connect: {self._last_error}")
            self._state = ConnectionState.ERROR
            return False
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Failed to connect to MCP server: {e}", exc_info=True)
            self._state = ConnectionState.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from MCP server."""
        if self._state == ConnectionState.DISCONNECTED:
            logger.info("Already disconnected")
            return
        
        logger.info("Disconnecting from MCP server...")
        
        # Stop health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
        
        # Close session
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            self._session = None
        
        # Close client context
        if self._client_context:
            try:
                await self._client_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing client context: {e}")
            self._client_context = None
        
        self._read_stream = None
        self._write_stream = None
        self._state = ConnectionState.DISCONNECTED
        
        logger.info("✓ Disconnected from MCP server")
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to MCP server.
        
        Uses exponential backoff for retry attempts.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self._reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error(
                f"Max reconnection attempts ({self.config.max_reconnect_attempts}) reached"
            )
            self._state = ConnectionState.ERROR
            return False
        
        self._state = ConnectionState.RECONNECTING
        self._reconnect_attempts += 1
        
        # Calculate backoff delay
        delay = min(
            self.config.reconnect_backoff_base ** self._reconnect_attempts,
            self.config.reconnect_backoff_max
        )
        
        logger.info(
            f"Reconnection attempt {self._reconnect_attempts}/"
            f"{self.config.max_reconnect_attempts} in {delay:.1f}s..."
        )
        
        await asyncio.sleep(delay)
        
        # Disconnect first
        await self.disconnect()
        
        # Attempt connection
        return await self.connect()
    
    async def health_check(self) -> bool:
        """
        Perform health check on connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            # Try to list tools as a health check
            if self._session:
                result = await asyncio.wait_for(
                    self._session.list_tools(),
                    timeout=10.0
                )
                return result is not None
            return False
            
        except asyncio.TimeoutError:
            logger.warning("Health check timed out")
            return False
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def _start_health_check(self) -> None:
        """Start periodic health check task."""
        if self._health_check_task:
            return
        
        async def health_check_loop():
            """Periodic health check loop."""
            while True:
                try:
                    await asyncio.sleep(self.config.health_check_interval)
                    
                    if not await self.health_check():
                        logger.warning("Health check failed, attempting reconnection...")
                        await self.reconnect()
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in health check loop: {e}")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
        logger.debug("Health check task started")
    
    def get_last_error(self) -> Optional[str]:
        """Get last connection error message."""
        return self._last_error
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Made with Bob