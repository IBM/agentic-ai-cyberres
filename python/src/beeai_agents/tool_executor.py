"""
Tool execution layer for BeeAI agents.
Handles MCP tool execution, result parsing, and error handling.
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from beeai_framework.tools.mcp import MCPTool
from models import CheckResult, ValidationStatus

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class ToolExecutor:
    """Executes MCP tools with proper error handling and retry logic."""
    
    def __init__(self, mcp_tools: List[MCPTool], max_retries: int = 3):
        """Initialize tool executor.
        
        Args:
            mcp_tools: List of available MCP tools
            max_retries: Maximum retry attempts for failed executions
        """
        self.mcp_tools = mcp_tools
        self.max_retries = max_retries
        self._tool_map = {tool.name: tool for tool in mcp_tools}
        
        logger.info(f"Tool executor initialized with {len(mcp_tools)} tools")
    
    def find_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Find tool by name.
        
        Args:
            tool_name: Name of the tool to find
        
        Returns:
            MCPTool or None if not found
        """
        return self._tool_map.get(tool_name)
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute MCP tool with arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If tool execution fails
        """
        tool = self.find_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool not found: {tool_name}")
        
        logger.info(f"Executing tool: {tool_name}")
        logger.debug(f"Tool arguments: {tool_args}")
        
        try:
            # Execute the tool using BeeAI's MCPTool interface
            # MCPTool.run() returns JSONToolOutput with .result attribute
            result_output = await tool.run(input=tool_args)
            
            # Get result - it's already a dict if it's JSON, or a string otherwise
            import json
            if isinstance(result_output.result, str):
                result = json.loads(result_output.result)
            else:
                result = result_output.result
            
            logger.info(f"Tool {tool_name} executed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {tool_name} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ToolExecutionError(error_msg) from e
    
    async def execute_with_retry(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool with exponential backoff retry.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If all retry attempts fail
        """
        import asyncio
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retry attempt {attempt} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                
                return await self.execute_tool(tool_name, tool_args)
                
            except ToolExecutionError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        raise ToolExecutionError(
            f"Tool execution failed after {self.max_retries} attempts: {last_error}"
        )
    
    def parse_check_result(
        self,
        tool_result: Dict[str, Any],
        check_def: Any,
        expected_value: Optional[str] = None
    ) -> CheckResult:
        """Parse tool result into CheckResult.
        
        Args:
            tool_result: Raw tool execution result
            check_def: Check definition with expected criteria
            expected_value: Optional expected value for comparison
        
        Returns:
            CheckResult with status and details
        """
        # Extract status from tool result
        # MCP tools typically return: {"success": bool, "data": {...}, "error": str}
        
        success = tool_result.get("success", False)
        data = tool_result.get("data", {})
        error = tool_result.get("error")
        
        if not success:
            return CheckResult(
                check_id=check_def.check_id,
                check_name=check_def.check_name,
                status=ValidationStatus.FAIL,
                message=error or "Tool execution failed",
                expected=expected_value or check_def.expected_result,
                actual="Execution failed"
            )
        
        # Compare actual vs expected if criteria provided
        if expected_value:
            actual_value = self._extract_value(data, check_def)
            matches = self._compare_values(actual_value, expected_value)
            
            if matches:
                return CheckResult(
                    check_id=check_def.check_id,
                    check_name=check_def.check_name,
                    status=ValidationStatus.PASS,
                    message="Check passed successfully",
                    expected=expected_value,
                    actual=str(actual_value),
                    details=data
                )
            else:
                return CheckResult(
                    check_id=check_def.check_id,
                    check_name=check_def.check_name,
                    status=ValidationStatus.FAIL,
                    message="Value does not match expected criteria",
                    expected=expected_value,
                    actual=str(actual_value),
                    details=data
                )
        
        # No expected value - just report success
        return CheckResult(
            check_id=check_def.check_id,
            check_name=check_def.check_name,
            status=ValidationStatus.PASS,
            message="Tool executed successfully",
            details=data
        )
    
    def _extract_value(self, data: Dict[str, Any], check_def: Any) -> Any:
        """Extract relevant value from tool result data."""
        # This would be customized based on check type
        # For now, return the whole data
        return data
    
    def _compare_values(self, actual: Any, expected: str) -> bool:
        """Compare actual value against expected criteria.
        
        Args:
            actual: Actual value from tool execution
            expected: Expected value or criteria string
        
        Returns:
            True if values match criteria
        """
        # Simple string comparison for now
        # In production, this would handle:
        # - Numeric comparisons (>, <, >=, <=)
        # - Range checks
        # - Pattern matching
        # - Complex criteria
        
        return str(actual) == expected


# Made with Bob