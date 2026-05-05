"""
Dynamic Tool Invoker

Constructs and executes MCP tool requests dynamically based on schemas,
with error handling and retry logic.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional

from .models import ToolResult, ToolInvocation
from .connection_manager import MCPConnectionManager
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class DynamicToolInvoker:
    """
    Dynamically invokes MCP tools based on registered schemas.
    
    Features:
    - Schema-driven request construction
    - Parameter validation before invocation
    - Automatic retry with exponential backoff
    - Batch invocation support
    - Comprehensive error handling
    - Execution time tracking
    
    Example:
        >>> invoker = DynamicToolInvoker(connection_manager, registry)
        >>> result = await invoker.invoke_tool(
        ...     "discover_workload",
        ...     {"host": "9.11.69.88", "ssh_user": "admin"}
        ... )
        >>> if result.success:
        ...     print(f"Result: {result.result}")
    """
    
    def __init__(
        self,
        connection_manager: MCPConnectionManager,
        registry: ToolRegistry,
        max_retries: int = 3,
        retry_delay_base: float = 1.0,
        retry_delay_max: float = 10.0,
        timeout: float = 300.0
    ):
        """
        Initialize dynamic tool invoker.
        
        Args:
            connection_manager: MCP connection manager
            registry: Tool registry
            max_retries: Maximum retry attempts
            retry_delay_base: Base delay for exponential backoff (seconds)
            retry_delay_max: Maximum retry delay (seconds)
            timeout: Tool invocation timeout (seconds)
        """
        self.connection_manager = connection_manager
        self.registry = registry
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.retry_delay_max = retry_delay_max
        self.timeout = timeout
        
        logger.info(
            f"Dynamic tool invoker initialized "
            f"(max_retries={max_retries}, timeout={timeout}s)"
        )
    
    async def invoke_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        validate: bool = True,
        retry: bool = True
    ) -> ToolResult:
        """
        Invoke a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to invoke
            parameters: Tool parameters
            validate: Validate parameters before invocation
            retry: Enable automatic retry on failure
            
        Returns:
            ToolResult with execution outcome
        """
        start_time = time.time()
        
        logger.info(f"Invoking tool: {tool_name}")
        logger.debug(f"Parameters: {parameters}")
        
        # Check connection
        if not self.connection_manager.is_connected():
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error="Not connected to MCP server",
                execution_time_ms=0
            )
        
        # Validate parameters if requested
        if validate:
            validation_result = self.registry.validate_parameters(tool_name, parameters)
            if not validation_result.is_valid:
                error_msg = f"Parameter validation failed: {validation_result.error_message}"
                if validation_result.missing_required:
                    error_msg += f"\nMissing required: {validation_result.missing_required}"
                if validation_result.invalid_params:
                    error_msg += f"\nInvalid parameters: {validation_result.invalid_params}"
                
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    error=error_msg,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
        
        # Invoke with retry logic
        if retry:
            return await self._invoke_with_retry(tool_name, parameters, start_time)
        else:
            return await self._invoke_once(tool_name, parameters, start_time)
    
    async def _invoke_once(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        start_time: float
    ) -> ToolResult:
        """
        Invoke tool once without retry.
        
        Args:
            tool_name: Tool name
            parameters: Tool parameters
            start_time: Start timestamp
            
        Returns:
            ToolResult
        """
        try:
            session = self.connection_manager.session
            if not session:
                raise RuntimeError("No active MCP session")
            
            # Invoke tool with timeout
            response = await asyncio.wait_for(
                session.call_tool(tool_name, parameters),
                timeout=self.timeout
            )
            
            # Parse response
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Check if response indicates success
            if hasattr(response, 'content') and response.content:
                # Extract result from content
                result_data = response.content[0].text if response.content else None
                
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result=result_data,
                    execution_time_ms=execution_time_ms,
                    metadata={"response_type": type(response).__name__}
                )
            else:
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result=response,
                    execution_time_ms=execution_time_ms
                )
        
        except asyncio.TimeoutError:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Tool invocation timed out after {self.timeout}s"
            logger.error(error_msg)
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=error_msg,
                execution_time_ms=execution_time_ms
            )
        
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Tool invocation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=error_msg,
                execution_time_ms=execution_time_ms
            )
    
    async def _invoke_with_retry(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        start_time: float
    ) -> ToolResult:
        """
        Invoke tool with retry logic.
        
        Args:
            tool_name: Tool name
            parameters: Tool parameters
            start_time: Start timestamp
            
        Returns:
            ToolResult
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                # Calculate backoff delay
                delay = min(
                    self.retry_delay_base ** attempt,
                    self.retry_delay_max
                )
                logger.info(
                    f"Retry attempt {attempt}/{self.max_retries} "
                    f"for {tool_name} in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            
            # Attempt invocation
            result = await self._invoke_once(tool_name, parameters, start_time)
            
            if result.success:
                if attempt > 0:
                    logger.info(f"Tool {tool_name} succeeded on retry {attempt}")
                return result
            
            last_error = result.error
            
            # Check if error is retryable
            if not self._is_retryable_error(result.error):
                logger.warning(f"Non-retryable error for {tool_name}: {result.error}")
                return result
        
        # All retries exhausted
        logger.error(f"All {self.max_retries} retries exhausted for {tool_name}")
        return ToolResult(
            tool_name=tool_name,
            success=False,
            result=None,
            error=f"Failed after {self.max_retries} retries. Last error: {last_error}",
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def _is_retryable_error(self, error: Optional[str]) -> bool:
        """
        Check if error is retryable.
        
        Args:
            error: Error message
            
        Returns:
            True if error is retryable
        """
        if not error:
            return False
        
        error_lower = error.lower()
        
        # Retryable errors
        retryable_keywords = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
        ]
        
        # Non-retryable errors
        non_retryable_keywords = [
            "validation",
            "not found",
            "invalid",
            "unauthorized",
            "forbidden",
        ]
        
        # Check non-retryable first
        if any(keyword in error_lower for keyword in non_retryable_keywords):
            return False
        
        # Check retryable
        if any(keyword in error_lower for keyword in retryable_keywords):
            return True
        
        # Default: retry on unknown errors
        return True
    
    async def invoke_tool_batch(
        self,
        invocations: List[ToolInvocation]
    ) -> List[ToolResult]:
        """
        Invoke multiple tools in batch.
        
        Args:
            invocations: List of tool invocations
            
        Returns:
            List of tool results (same order as invocations)
        """
        logger.info(f"Invoking {len(invocations)} tools in batch")
        
        # Create tasks for parallel execution
        tasks = [
            self.invoke_tool(inv.tool_name, inv.parameters)
            for inv in invocations
        ]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to ToolResult
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ToolResult(
                    tool_name=invocations[i].tool_name,
                    success=False,
                    result=None,
                    error=str(result),
                    execution_time_ms=0
                ))
            else:
                final_results.append(result)
        
        success_count = sum(1 for r in final_results if r.success)
        logger.info(
            f"Batch invocation complete: {success_count}/{len(invocations)} succeeded"
        )
        
        return final_results
    
    def construct_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Construct MCP request from tool name and parameters.
        
        Args:
            tool_name: Tool name
            parameters: Tool parameters
            
        Returns:
            MCP request dictionary
        """
        return {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parameters
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get invoker statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "max_retries": self.max_retries,
            "retry_delay_base": self.retry_delay_base,
            "retry_delay_max": self.retry_delay_max,
            "timeout": self.timeout,
            "connected": self.connection_manager.is_connected(),
        }


# Made with Bob