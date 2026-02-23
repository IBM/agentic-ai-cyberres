#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Coordinates MCP tool execution with caching, retry, and parallel execution."""

import asyncio
import hashlib
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Retry policy for tool execution."""
    max_retries: int = 3
    base_delay: float = 1.0
    exponential_backoff: bool = True
    
    @classmethod
    def default(cls) -> "RetryPolicy":
        """Get default retry policy.
        
        Returns:
            Default RetryPolicy instance
        """
        return cls(max_retries=3, base_delay=1.0, exponential_backoff=True)
    
    @classmethod
    def no_retry(cls) -> "RetryPolicy":
        """Get no-retry policy.
        
        Returns:
            RetryPolicy with no retries
        """
        return cls(max_retries=0, base_delay=0.0, exponential_backoff=False)
    
    @classmethod
    def aggressive(cls) -> "RetryPolicy":
        """Get aggressive retry policy.
        
        Returns:
            RetryPolicy with more retries
        """
        return cls(max_retries=5, base_delay=0.5, exponential_backoff=True)


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    pass


class TransientError(ToolExecutionError):
    """Exception for transient errors that can be retried."""
    pass


class ToolCoordinator:
    """Coordinates MCP tool execution with intelligent features.
    
    Provides:
    - Result caching to avoid redundant tool calls
    - Retry logic with exponential backoff
    - Parallel execution of independent tools
    - Execution history for debugging
    """
    
    def __init__(self, mcp_client: Any):
        """Initialize tool coordinator.
        
        Args:
            mcp_client: MCP client instance
        """
        self.mcp_client = mcp_client
        self.tool_cache: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        logger.info("Tool coordinator initialized")
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        retry_policy: Optional[RetryPolicy] = None,
        use_cache: bool = True
    ) -> dict:
        """Execute MCP tool with caching and retry logic.
        
        Args:
            tool_name: Name of the MCP tool to execute
            arguments: Tool arguments
            retry_policy: Retry policy (uses default if None)
            use_cache: Whether to use cached results
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If tool execution fails after retries
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(tool_name, arguments)
            if cache_key in self.tool_cache:
                logger.debug(
                    f"Cache hit for tool: {tool_name}",
                    extra={"tool": tool_name, "cache_key": cache_key}
                )
                return self.tool_cache[cache_key]
        
        # Execute with retry
        retry_policy = retry_policy or RetryPolicy.default()
        
        try:
            result = await self._execute_with_retry(
                tool_name,
                arguments,
                retry_policy
            )
            
            # Cache result
            if use_cache:
                self.tool_cache[cache_key] = result
            
            # Record execution
            self._record_execution(tool_name, arguments, result, success=True)
            
            return result
            
        except Exception as e:
            # Record failed execution
            self._record_execution(
                tool_name,
                arguments,
                {"error": str(e)},
                success=False
            )
            raise
    
    async def execute_parallel(
        self,
        tool_calls: List[Tuple[str, dict]],
        retry_policy: Optional[RetryPolicy] = None
    ) -> List[dict]:
        """Execute multiple tools in parallel.
        
        Args:
            tool_calls: List of (tool_name, arguments) tuples
            retry_policy: Retry policy for all tools
        
        Returns:
            List of results (may include exceptions)
        """
        logger.info(
            f"Executing {len(tool_calls)} tools in parallel",
            extra={"tool_count": len(tool_calls)}
        )
        
        tasks = [
            self.execute_tool(tool_name, args, retry_policy)
            for tool_name, args in tool_calls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log summary
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(
            f"Parallel execution complete: {success_count}/{len(results)} succeeded",
            extra={
                "total": len(results),
                "succeeded": success_count,
                "failed": len(results) - success_count
            }
        )
        
        return results
    
    async def _execute_with_retry(
        self,
        tool_name: str,
        arguments: dict,
        retry_policy: RetryPolicy
    ) -> dict:
        """Execute tool with retry logic.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            retry_policy: Retry policy
        
        Returns:
            Tool result
        
        Raises:
            ToolExecutionError: If all retries fail
        """
        last_error = None
        
        for attempt in range(retry_policy.max_retries + 1):
            try:
                logger.debug(
                    f"Executing tool: {tool_name} (attempt {attempt + 1})",
                    extra={
                        "tool": tool_name,
                        "attempt": attempt + 1,
                        "max_attempts": retry_policy.max_retries + 1
                    }
                )
                
                result = await self.mcp_client.call_tool(tool_name, arguments)
                
                logger.debug(
                    f"Tool execution succeeded: {tool_name}",
                    extra={"tool": tool_name, "attempt": attempt + 1}
                )
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Check if we should retry
                if attempt < retry_policy.max_retries:
                    # Calculate delay
                    if retry_policy.exponential_backoff:
                        delay = retry_policy.base_delay * (2 ** attempt)
                    else:
                        delay = retry_policy.base_delay
                    
                    logger.warning(
                        f"Tool execution failed, retrying in {delay}s: {tool_name}",
                        extra={
                            "tool": tool_name,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Tool execution failed after {attempt + 1} attempts: {tool_name}",
                        extra={
                            "tool": tool_name,
                            "attempts": attempt + 1,
                            "error": str(e)
                        }
                    )
        
        # All retries exhausted
        raise ToolExecutionError(
            f"Tool {tool_name} failed after {retry_policy.max_retries + 1} attempts: {last_error}"
        )
    
    def _get_cache_key(self, tool_name: str, arguments: dict) -> str:
        """Generate cache key for tool call.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
        
        Returns:
            Cache key (MD5 hash)
        """
        # Create deterministic string representation
        key_data = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _record_execution(
        self,
        tool_name: str,
        arguments: dict,
        result: dict,
        success: bool
    ):
        """Record tool execution in history.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            result: Execution result
            success: Whether execution succeeded
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "success": success
        }
        self.execution_history.append(record)
    
    def get_execution_history(
        self,
        tool_name: Optional[str] = None,
        success_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get execution history, optionally filtered.
        
        Args:
            tool_name: Filter by tool name (optional)
            success_only: Only return successful executions
        
        Returns:
            List of execution records
        """
        history = self.execution_history
        
        if tool_name:
            history = [r for r in history if r["tool"] == tool_name]
        
        if success_only:
            history = [r for r in history if r["success"]]
        
        return history
    
    def clear_cache(self, tool_name: Optional[str] = None):
        """Clear tool result cache.
        
        Args:
            tool_name: Clear cache for specific tool (optional)
        """
        if tool_name:
            # Clear cache entries for specific tool
            keys_to_remove = [
                k for k, v in self.tool_cache.items()
                if k.startswith(tool_name)
            ]
            for key in keys_to_remove:
                del self.tool_cache[key]
            logger.info(f"Cleared cache for tool: {tool_name}")
        else:
            # Clear all cache
            self.tool_cache.clear()
            logger.info("Cleared all tool cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self.tool_cache),
            "execution_count": len(self.execution_history),
            "success_count": sum(1 for r in self.execution_history if r["success"]),
            "failure_count": sum(1 for r in self.execution_history if not r["success"])
        }


# Made with Bob