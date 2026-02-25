"""
Base agent class for BeeAI-based validation agents.
"""

import logging
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod

from beeai_framework.agents import BaseAgent, AgentExecutionConfig
from beeai_framework.memory import SlidingMemory, TokenMemory, UnconstrainedMemory
from beeai_framework.tools import Tool

from .config import BeeAIConfig, MemoryConfig

logger = logging.getLogger(__name__)


class BaseValidationAgent(ABC):
    """
    Base class for all BeeAI validation agents.
    
    Provides common functionality for:
    - Agent initialization
    - Memory management
    - LLM configuration
    - Tool registration
    - Error handling
    """
    
    def __init__(
        self,
        config: BeeAIConfig,
        name: str,
        system_prompt: str,
        tools: Optional[list[Tool]] = None
    ):
        """
        Initialize base validation agent.
        
        Args:
            config: BeeAI configuration
            name: Agent name
            system_prompt: System prompt for the agent
            tools: List of tools available to the agent
        """
        self.config = config
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        # Initialize memory
        self.memory = self._create_memory(config.memory)
        
        # Initialize BeeAI agent
        self.agent = self._create_agent()
        
        logger.info(f"Initialized {self.name} with {len(self.tools)} tools")
    
    def _create_memory(self, memory_config: MemoryConfig):
        """
        Create memory instance based on configuration.
        
        Args:
            memory_config: Memory configuration
            
        Returns:
            Memory instance
        """
        if memory_config.type == "sliding":
            return SlidingMemory(
                max_messages=memory_config.max_messages
            )
        elif memory_config.type == "token":
            return TokenMemory(
                max_tokens=memory_config.max_tokens or 4000
            )
        elif memory_config.type == "unconstrained":
            return UnconstrainedMemory()
        else:
            # Default to sliding memory
            return SlidingMemory(max_messages=50)
    
    def _create_agent(self) -> BaseAgent:
        """
        Create BeeAI agent instance.
        
        Returns:
            BeeAI agent
        """
        # This will be implemented by subclasses with specific agent types
        raise NotImplementedError("Subclasses must implement _create_agent")
    
    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """
        Run the agent with input data.
        
        Args:
            input_data: Input for the agent
            
        Returns:
            Agent output
        """
        pass
    
    def add_tool(self, tool: Tool):
        """
        Add a tool to the agent.
        
        Args:
            tool: Tool to add
        """
        self.tools.append(tool)
        logger.info(f"Added tool {tool.name} to {self.name}")
    
    def get_memory_messages(self) -> list[Dict[str, Any]]:
        """
        Get current memory messages.
        
        Returns:
            List of memory messages
        """
        return self.memory.messages if hasattr(self.memory, 'messages') else []
    
    def clear_memory(self):
        """Clear agent memory."""
        if hasattr(self.memory, 'clear'):
            self.memory.clear()
            logger.info(f"Cleared memory for {self.name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.
        
        Returns:
            Dictionary with agent stats
        """
        return {
            "name": self.name,
            "tools_count": len(self.tools),
            "memory_type": self.config.memory.type,
            "memory_size": len(self.get_memory_messages())
        }


class RetryMixin:
    """Mixin for retry functionality."""
    
    async def run_with_retry(
        self,
        func,
        max_attempts: int = 3,
        *args,
        **kwargs
    ):
        """
        Run function with retry logic.
        
        Args:
            func: Function to run
            max_attempts: Maximum number of attempts
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result
            
        Raises:
            Exception: If all attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}"
                )
                if attempt < max_attempts - 1:
                    # Exponential backoff
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
        
        raise last_exception


class CacheMixin:
    """Mixin for caching functionality."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._cache.get(key)
    
    def set_in_cache(self, key: str, value: Any):
        """Set value in cache."""
        self._cache[key] = value
    
    def clear_cache(self):
        """Clear cache."""
        self._cache.clear()

# Made with Bob
