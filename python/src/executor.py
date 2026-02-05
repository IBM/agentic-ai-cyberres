#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Validation execution for recovery validation agent."""

import logging
import time
from typing import Dict, Any, List, Optional
from mcp_client import MCPClient, MCPClientError
from planner import ValidationPlan, ValidationStep

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of executing a validation step."""
    
    def __init__(
        self,
        step_id: str,
        tool_name: str,
        success: bool,
        result: Dict[str, Any],
        error: Optional[str] = None,
        execution_time: float = 0.0
    ):
        """Initialize execution result.
        
        Args:
            step_id: Step identifier
            tool_name: Tool name that was executed
            success: Whether execution succeeded
            result: Tool result dictionary
            error: Error message if failed
            execution_time: Execution time in seconds
        """
        self.step_id = step_id
        self.tool_name = tool_name
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time
        }


class ValidationExecutor:
    """Execute validation plans using MCP client."""
    
    def __init__(self, mcp_client: MCPClient):
        """Initialize validation executor.
        
        Args:
            mcp_client: Connected MCP client instance
        """
        self.mcp_client = mcp_client
    
    async def execute_step(self, step: ValidationStep) -> ExecutionResult:
        """Execute a single validation step.
        
        Args:
            step: Validation step to execute
        
        Returns:
            ExecutionResult with step results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Executing step: {step.step_id} ({step.tool_name})")
            
            # Filter out None values from arguments
            clean_args = {k: v for k, v in step.arguments.items() if v is not None}
            
            # Call the MCP tool
            result = await self.mcp_client.call_tool(step.tool_name, clean_args)
            
            execution_time = time.time() - start_time
            
            # Check if tool returned ok status
            success = result.get("ok", False)
            
            if success:
                logger.info(
                    f"Step {step.step_id} completed successfully",
                    extra={"execution_time": execution_time}
                )
            else:
                error_info = result.get("error", {})
                error_msg = error_info.get("message", "Unknown error") if isinstance(error_info, dict) else str(error_info)
                logger.warning(
                    f"Step {step.step_id} failed: {error_msg}",
                    extra={"execution_time": execution_time}
                )
            
            return ExecutionResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                success=success,
                result=result,
                error=None if success else result.get("error"),
                execution_time=execution_time
            )
            
        except MCPClientError as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"Step {step.step_id} failed with MCP error: {error_msg}",
                extra={"execution_time": execution_time}
            )
            
            return ExecutionResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                success=False,
                result={},
                error=error_msg,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(
                f"Step {step.step_id} failed: {error_msg}",
                extra={"execution_time": execution_time}
            )
            
            return ExecutionResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                success=False,
                result={},
                error=error_msg,
                execution_time=execution_time
            )
    
    async def execute_plan(
        self,
        plan: ValidationPlan,
        stop_on_failure: bool = False
    ) -> List[ExecutionResult]:
        """Execute a complete validation plan.
        
        Args:
            plan: Validation plan to execute
            stop_on_failure: Stop execution if a required step fails
        
        Returns:
            List of ExecutionResult for each step
        """
        results = []
        total_start_time = time.time()
        
        logger.info(
            f"Starting validation plan execution",
            extra={
                "resource_type": plan.resource_type.value,
                "total_steps": len(plan.steps)
            }
        )
        
        for i, step in enumerate(plan.steps, 1):
            logger.info(f"Executing step {i}/{len(plan.steps)}: {step.description}")
            
            result = await self.execute_step(step)
            results.append(result)
            
            # Check if we should stop on failure
            if not result.success and step.required and stop_on_failure:
                logger.warning(
                    f"Required step {step.step_id} failed, stopping execution",
                    extra={"failed_step": step.step_id}
                )
                break
        
        total_time = time.time() - total_start_time
        successful_steps = sum(1 for r in results if r.success)
        
        logger.info(
            f"Validation plan execution completed",
            extra={
                "total_steps": len(results),
                "successful_steps": successful_steps,
                "failed_steps": len(results) - successful_steps,
                "total_time": total_time
            }
        )
        
        return results
    
    def get_execution_summary(self, results: List[ExecutionResult]) -> Dict[str, Any]:
        """Generate summary of execution results.
        
        Args:
            results: List of execution results
        
        Returns:
            Summary dictionary
        """
        total_steps = len(results)
        successful_steps = sum(1 for r in results if r.success)
        failed_steps = total_steps - successful_steps
        total_time = sum(r.execution_time for r in results)
        
        failed_step_details = [
            {
                "step_id": r.step_id,
                "tool_name": r.tool_name,
                "error": r.error
            }
            for r in results if not r.success
        ]
        
        return {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": (successful_steps / total_steps * 100) if total_steps > 0 else 0,
            "total_execution_time": total_time,
            "failed_step_details": failed_step_details
        }

# Made with Bob
