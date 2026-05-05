"""Data models for agent output management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class VerbosityLevel(Enum):
    """Output verbosity levels."""
    MINIMAL = 1       # Status updates only: "Agent: Task complete"
    STANDARD = 2      # Key decisions and results (default)
    DETAILED = 3      # Reasoning with context
    COMPREHENSIVE = 4 # Full cognitive process with framework details


@dataclass
class ThoughtStep:
    """Single reasoning step in agent's cognitive process."""
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[int] = None
    
    def has_action(self) -> bool:
        """Check if step includes an action."""
        return self.action is not None
    
    def is_tool_call(self) -> bool:
        """Check if action is a tool call."""
        return self.action is not None and self.action_input is not None


@dataclass
class ReasoningChain:
    """Complete reasoning chain from agent execution."""
    steps: List[ThoughtStep]
    final_answer: str
    total_steps: int
    execution_time_ms: int
    model_used: str
    agent_name: str
    phase: str
    success: bool = True
    error_message: Optional[str] = None
    
    def get_tool_calls(self) -> List[ThoughtStep]:
        """Get all steps that involve tool calls."""
        return [step for step in self.steps if step.is_tool_call()]
    
    def get_thinking_steps(self) -> List[ThoughtStep]:
        """Get all pure reasoning steps (no actions)."""
        return [step for step in self.steps if not step.has_action()]


@dataclass
class ThoughtBlock:
    """Professional representation of agent reasoning for display."""
    title: str
    content: str
    icon: str = "🤔"
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None
    block_type: str = "thinking"  # thinking, action, result, decision, error
    
    def format_for_console(self, agent_name: str = "Agent") -> str:
        """
        Format block for console display in simple format.
        
        Args:
            agent_name: Name of the agent (default: "Agent")
        
        Returns:
            Formatted string: "Agent: message"
        """
        # Simple format: Agent: message
        return f"{agent_name}: {self.content}"
    
    def format_detailed(self) -> str:
        """Format block with full details including icon and metadata."""
        header = f"     {self.icon} {self.title}"
        if self.confidence:
            header += f" (confidence: {self.confidence:.0%})"
        if self.duration_ms:
            header += f" ({self.duration_ms}ms)"
        
        return f"{header}\n     {self.content}"


@dataclass
class OutputConfig:
    """Configuration for output management system."""
    console_verbosity: VerbosityLevel = VerbosityLevel.STANDARD
    log_level: str = "DEBUG"
    log_dir: str = "logs"
    log_rotation_mb: int = 10
    log_retention_count: int = 5
    enable_mcp_logging: bool = True
    enable_framework_logging: bool = True
    sanitize_console: bool = True
    show_timestamps: bool = False
    show_durations: bool = True
    console_format: str = "simple"  # "simple" or "detailed"
    show_agent_name: bool = True

# Made with Bob
