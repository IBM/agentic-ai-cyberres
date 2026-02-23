#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all agents in the system.
    
    Provides common functionality for logging, execution tracking,
    and interaction with MCP tools.
    """
    
    def __init__(self, mcp_client: Any, name: str):
        """Initialize base agent.
        
        Args:
            mcp_client: MCP client instance for tool execution
            name: Agent name for logging and identification
        """
        self.mcp_client = mcp_client
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.execution_history: list[Dict[str, Any]] = []
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute agent's primary task.
        
        Args:
            context: Execution context with required data
        
        Returns:
            Agent-specific result
        
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass
    
    def log_step(self, message: str, level: str = "info", **kwargs):
        """Log agent step with context.
        
        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
            **kwargs: Additional context to log
        """
        log_method = getattr(self.logger, level)
        log_data = {"agent": self.name, **kwargs}
        log_method(f"[{self.name}] {message}", extra=log_data)
    
    def record_execution(self, action: str, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """Record execution for audit trail.
        
        Args:
            action: Action performed
            result: Action result
            metadata: Additional metadata
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "action": action,
            "result": result,
            "metadata": metadata or {}
        }
        self.execution_history.append(record)
        self.log_step(f"Recorded execution: {action}", level="debug")
    
    def get_execution_history(self) -> list[Dict[str, Any]]:
        """Get agent's execution history.
        
        Returns:
            List of execution records
        """
        return self.execution_history.copy()
    
    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()
        self.log_step("Execution history cleared", level="debug")


# Made with Bob