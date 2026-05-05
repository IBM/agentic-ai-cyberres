"""
Tool Discovery Engine

Dynamically discovers tools from MCP server, fetches their schemas,
and detects changes for hot-reload support.
"""

import asyncio
import logging
from typing import List, Optional, AsyncIterator, Dict, Any
from datetime import datetime
import hashlib
import json

from .models import ToolSchema, ToolChange
from .connection_manager import MCPConnectionManager

logger = logging.getLogger(__name__)


class ToolDiscoveryEngine:
    """
    Discovers and monitors tools from MCP server.
    
    Features:
    - Query MCP server for available tools
    - Fetch complete schemas for each tool
    - Detect schema changes for hot-reload
    - Cache schemas for performance
    - Watch for tool additions/removals
    
    Example:
        >>> engine = ToolDiscoveryEngine(connection_manager)
        >>> tools = await engine.discover_tools()
        >>> print(f"Discovered {len(tools)} tools")
        >>> 
        >>> # Watch for changes
        >>> async for change in engine.watch_for_changes():
        ...     print(f"Tool {change.tool_name} was {change.change_type}")
    """
    
    def __init__(
        self,
        connection_manager: MCPConnectionManager,
        cache_enabled: bool = True,
        watch_interval: float = 30.0
    ):
        """
        Initialize tool discovery engine.
        
        Args:
            connection_manager: MCP connection manager
            cache_enabled: Enable schema caching
            watch_interval: Interval for watching changes (seconds)
        """
        self.connection_manager = connection_manager
        self.cache_enabled = cache_enabled
        self.watch_interval = watch_interval
        
        # Schema cache: tool_name -> (schema, hash)
        self._schema_cache: Dict[str, tuple[ToolSchema, str]] = {}
        
        # Discovered tool names
        self._discovered_tools: List[str] = []
        
        # Watch task
        self._watch_task: Optional[asyncio.Task] = None
        
        logger.info("Tool discovery engine initialized")
    
    async def discover_tools(self, force_refresh: bool = False) -> List[ToolSchema]:
        """
        Discover all available tools from MCP server.
        
        Args:
            force_refresh: Force refresh even if cached
            
        Returns:
            List of discovered tool schemas
        """
        if not self.connection_manager.is_connected():
            raise RuntimeError("Not connected to MCP server")
        
        logger.info("Discovering tools from MCP server...")
        
        try:
            session = self.connection_manager.session
            if not session:
                raise RuntimeError("No active MCP session")
            
            # List available tools
            tools_response = await session.list_tools()
            
            if not tools_response or not hasattr(tools_response, 'tools'):
                logger.warning("No tools returned from MCP server")
                return []
            
            tools = tools_response.tools
            logger.info(f"Found {len(tools)} tools on MCP server")
            
            # Fetch schema for each tool
            schemas = []
            for tool in tools:
                try:
                    schema = await self._fetch_tool_schema(tool, force_refresh)
                    if schema:
                        schemas.append(schema)
                except Exception as e:
                    logger.error(f"Failed to fetch schema for tool {tool.name}: {e}")
            
            # Update discovered tools list
            self._discovered_tools = [s.name for s in schemas]
            
            logger.info(f"✓ Successfully discovered {len(schemas)} tool schemas")
            return schemas
            
        except Exception as e:
            logger.error(f"Tool discovery failed: {e}", exc_info=True)
            raise
    
    async def _fetch_tool_schema(
        self,
        tool: Any,
        force_refresh: bool = False
    ) -> Optional[ToolSchema]:
        """
        Fetch schema for a specific tool.
        
        Args:
            tool: MCP tool object
            force_refresh: Force refresh even if cached
            
        Returns:
            ToolSchema or None if fetch failed
        """
        tool_name = tool.name
        
        # Check cache
        if not force_refresh and self.cache_enabled and tool_name in self._schema_cache:
            cached_schema, _ = self._schema_cache[tool_name]
            logger.debug(f"Using cached schema for {tool_name}")
            return cached_schema
        
        try:
            # Extract schema from tool object
            schema = ToolSchema(
                name=tool_name,
                description=getattr(tool, 'description', ''),
                input_schema=getattr(tool, 'inputSchema', {}),
                annotations=getattr(tool, 'annotations', None),
            )
            
            # Calculate schema hash for change detection
            schema_hash = self._calculate_schema_hash(schema)
            
            # Update cache
            if self.cache_enabled:
                self._schema_cache[tool_name] = (schema, schema_hash)
            
            logger.debug(f"Fetched schema for {tool_name}")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to fetch schema for {tool_name}: {e}")
            return None
    
    def _calculate_schema_hash(self, schema: ToolSchema) -> str:
        """
        Calculate hash of schema for change detection.
        
        Args:
            schema: Tool schema
            
        Returns:
            SHA256 hash of schema
        """
        # Create deterministic JSON representation
        schema_dict = {
            "name": schema.name,
            "description": schema.description,
            "input_schema": schema.input_schema,
        }
        schema_json = json.dumps(schema_dict, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()
    
    async def get_tool_schema(self, tool_name: str) -> Optional[ToolSchema]:
        """
        Get schema for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolSchema or None if not found
        """
        # Check cache first
        if self.cache_enabled and tool_name in self._schema_cache:
            schema, _ = self._schema_cache[tool_name]
            return schema
        
        # Discover all tools to populate cache
        await self.discover_tools()
        
        # Check cache again
        if tool_name in self._schema_cache:
            schema, _ = self._schema_cache[tool_name]
            return schema
        
        logger.warning(f"Tool {tool_name} not found")
        return None
    
    def get_discovered_tools(self) -> List[str]:
        """
        Get list of discovered tool names.
        
        Returns:
            List of tool names
        """
        return self._discovered_tools.copy()
    
    async def watch_for_changes(self) -> AsyncIterator[ToolChange]:
        """
        Watch for tool changes (additions, removals, modifications).
        
        Yields:
            ToolChange objects when changes detected
        """
        logger.info(f"Starting tool change watcher (interval: {self.watch_interval}s)")
        
        # Take initial snapshot
        previous_tools = set(self._discovered_tools)
        previous_hashes = {
            name: hash_val
            for name, (_, hash_val) in self._schema_cache.items()
        }
        
        while True:
            try:
                await asyncio.sleep(self.watch_interval)
                
                # Discover current tools
                current_schemas = await self.discover_tools(force_refresh=True)
                current_tools = set(s.name for s in current_schemas)
                current_hashes = {
                    name: hash_val
                    for name, (_, hash_val) in self._schema_cache.items()
                }
                
                # Detect additions
                added_tools = current_tools - previous_tools
                for tool_name in added_tools:
                    schema = self._schema_cache.get(tool_name, (None, None))[0]
                    if schema:
                        yield ToolChange(
                            change_type="added",
                            tool_name=tool_name,
                            new_schema=schema,
                            timestamp=datetime.now().timestamp()
                        )
                        logger.info(f"Tool added: {tool_name}")
                
                # Detect removals
                removed_tools = previous_tools - current_tools
                for tool_name in removed_tools:
                    yield ToolChange(
                        change_type="removed",
                        tool_name=tool_name,
                        timestamp=datetime.now().timestamp()
                    )
                    logger.info(f"Tool removed: {tool_name}")
                
                # Detect modifications
                common_tools = current_tools & previous_tools
                for tool_name in common_tools:
                    old_hash = previous_hashes.get(tool_name)
                    new_hash = current_hashes.get(tool_name)
                    
                    if old_hash and new_hash and old_hash != new_hash:
                        new_schema = self._schema_cache.get(tool_name, (None, None))[0]
                        if new_schema:
                            yield ToolChange(
                                change_type="modified",
                                tool_name=tool_name,
                                new_schema=new_schema,
                                timestamp=datetime.now().timestamp()
                            )
                            logger.info(f"Tool modified: {tool_name}")
                
                # Update snapshots
                previous_tools = current_tools
                previous_hashes = current_hashes
                
            except asyncio.CancelledError:
                logger.info("Tool change watcher stopped")
                break
            except Exception as e:
                logger.error(f"Error in tool change watcher: {e}")
    
    def start_watching(self) -> None:
        """Start background task to watch for tool changes."""
        if self._watch_task:
            logger.warning("Watch task already running")
            return
        
        async def watch_loop():
            """Background watch loop."""
            async for change in self.watch_for_changes():
                # Changes are logged in watch_for_changes
                pass
        
        self._watch_task = asyncio.create_task(watch_loop())
        logger.info("Started background tool change watcher")
    
    def stop_watching(self) -> None:
        """Stop background watch task."""
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
            logger.info("Stopped background tool change watcher")
    
    def clear_cache(self) -> None:
        """Clear schema cache."""
        self._schema_cache.clear()
        logger.info("Schema cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "cached_tools": len(self._schema_cache),
            "discovered_tools": len(self._discovered_tools),
            "cache_enabled": self.cache_enabled,
        }


# Made with Bob