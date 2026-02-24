#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
import logging
import os
from datetime import datetime
from pydantic import BaseModel

# Import Phase 1 components
try:
    from tool_coordinator import ToolCoordinator
    from state_manager import StateManager
    from feature_flags import FeatureFlags
except ImportError:
    # Graceful degradation if Phase 1 components not available
    ToolCoordinator = None
    StateManager = None
    FeatureFlags = None

# Type variable for Pydantic AI result types
T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class AgentConfig:
    """Configuration for Pydantic AI agents.
    
    This class provides configuration for creating Pydantic AI agents
    with consistent settings across the system.
    """
    
    def __init__(
        self,
        model: str = "openai:gpt-4",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ):
        """Initialize agent configuration.
        
        Args:
            model: Model identifier (e.g., "openai:gpt-4", "anthropic:claude-3-opus")
            api_key: API key for the model provider (uses env var if not provided)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def create_agent(
        self,
        result_type: Type[T],
        system_prompt: str
    ) -> Any:
        """Create a Pydantic AI agent.
        
        Args:
            result_type: Pydantic model class for structured output
            system_prompt: System prompt for the agent
        
        Returns:
            Configured Pydantic AI Agent instance
        """
        try:
            from pydantic_ai import Agent
            
            return Agent(
                model=self.model,
                result_type=result_type,
                system_prompt=system_prompt
            )
        except ImportError:
            logger.error("pydantic_ai not installed. Install with: pip install pydantic-ai")
            raise


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


class EnhancedAgent(BaseAgent):
    """Enhanced agent with tool coordination and state management.
    
    This class extends BaseAgent with Phase 1 components:
    - ToolCoordinator for intelligent tool execution
    - StateManager for workflow state persistence
    - FeatureFlags for gradual feature rollout
    
    Agents can inherit from this class to get enhanced capabilities
    while maintaining backward compatibility.
    """
    
    def __init__(
        self,
        mcp_client: Any,
        name: str,
        tool_coordinator: Optional[Any] = None,
        state_manager: Optional[Any] = None,
        feature_flags: Optional[Any] = None
    ):
        """Initialize enhanced agent.
        
        Args:
            mcp_client: MCP client instance for tool execution
            name: Agent name for logging and identification
            tool_coordinator: Optional ToolCoordinator for enhanced tool execution
            state_manager: Optional StateManager for workflow state
            feature_flags: Optional FeatureFlags for feature control
        """
        super().__init__(mcp_client, name)
        self.tool_coordinator = tool_coordinator
        self.state_manager = state_manager
        
        # Initialize feature flags with defaults if not provided
        if feature_flags is None and FeatureFlags is not None:
            self.feature_flags = FeatureFlags()
        else:
            self.feature_flags = feature_flags
        
        self.log_step(
            "Enhanced agent initialized",
            level="info",
            has_tool_coordinator=tool_coordinator is not None,
            has_state_manager=state_manager is not None,
            has_feature_flags=feature_flags is not None
        )
    
    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        use_cache: bool = True,
        max_retries: int = 3
    ) -> Any:
        """Execute tool with coordination and retry logic.
        
        This method provides intelligent tool execution with:
        - Automatic retry on failure
        - Result caching for performance
        - Consistent error handling
        - Execution tracking
        
        Args:
            tool_name: Name of the MCP tool to execute
            args: Tool arguments
            use_cache: Whether to use cached results
            max_retries: Maximum retry attempts on failure
        
        Returns:
            Tool execution result
        
        Raises:
            Exception: If tool execution fails after all retries
        """
        # Check if tool coordinator is available and enabled
        use_coordinator = (
            self.tool_coordinator is not None and
            self.feature_flags and
            self.feature_flags.is_enabled("use_tool_coordinator")
        )
        
        if use_coordinator:
            self.log_step(
                f"Executing tool via coordinator: {tool_name}",
                level="debug",
                use_cache=use_cache,
                max_retries=max_retries
            )
            
            result = await self.tool_coordinator.execute_tool(
                tool_name=tool_name,
                args=args,
                use_cache=use_cache,
                max_retries=max_retries
            )
            
            self.record_execution(
                action=f"tool_execution:{tool_name}",
                result={"success": result.get("success", False)},
                metadata={"via_coordinator": True, "cached": use_cache}
            )
            
            return result
        else:
            # Fallback to direct MCP client execution
            self.log_step(
                f"Executing tool directly: {tool_name}",
                level="debug",
                reason="coordinator_not_available_or_disabled"
            )
            
            result = await self.mcp_client.call_tool(tool_name, args)
            
            self.record_execution(
                action=f"tool_execution:{tool_name}",
                result={"success": result.get("success", False)},
                metadata={"via_coordinator": False}
            )
            
            return result
    
    async def execute_tools_parallel(
        self,
        tool_calls: list[tuple[str, Dict[str, Any]]],
        use_cache: bool = True
    ) -> list[Any]:
        """Execute multiple tools in parallel.
        
        Args:
            tool_calls: List of (tool_name, args) tuples
            use_cache: Whether to use cached results
        
        Returns:
            List of tool execution results
        """
        # Check if parallel execution is enabled
        use_parallel = (
            self.tool_coordinator is not None and
            self.feature_flags and
            self.feature_flags.is_enabled("parallel_tool_execution")
        )
        
        if use_parallel:
            self.log_step(
                f"Executing {len(tool_calls)} tools in parallel",
                level="info"
            )
            
            results = await self.tool_coordinator.execute_parallel(
                tool_calls,
                use_cache=use_cache
            )
            
            self.record_execution(
                action="parallel_tool_execution",
                result={"count": len(tool_calls), "success": True},
                metadata={"parallel": True}
            )
            
            return results
        else:
            # Fallback to sequential execution
            self.log_step(
                f"Executing {len(tool_calls)} tools sequentially",
                level="info",
                reason="parallel_execution_not_enabled"
            )
            
            results = []
            for tool_name, args in tool_calls:
                result = await self.execute_tool(tool_name, args, use_cache)
                results.append(result)
            
            return results
    
    async def save_state(self, state_data: Dict[str, Any]):
        """Save agent state.
        
        Args:
            state_data: State data to save
        """
        if self.state_manager:
            await self.state_manager.save_context(state_data)
            self.log_step("State saved", level="debug")
    
    async def load_state(self) -> Optional[Dict[str, Any]]:
        """Load agent state.
        
        Returns:
            Saved state data or None
        """
        if self.state_manager:
            state = await self.state_manager.get_context()
            self.log_step("State loaded", level="debug")
            return state
        return None


# Made with Bob