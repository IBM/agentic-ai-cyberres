"""Output manager for coordinating agent output streams."""

import logging
from typing import Any, Optional
from pathlib import Path

from .models import OutputConfig, VerbosityLevel, ReasoningChain, ThoughtBlock
from .response_parser import AgentResponseParser
from .framework_sanitizer import FrameworkSanitizer
from .plan_formatter import ValidationPlanFormatter

logger = logging.getLogger(__name__)


class OutputManager:
    """
    Manages all agent output streams.
    
    Coordinates:
    - Console output (clean, professional)
    - Debug logs (complete details)
    - Response parsing and sanitization
    - Validation plan formatting
    """
    
    def __init__(self, config: Optional[OutputConfig] = None):
        """
        Initialize output manager.
        
        Args:
            config: Output configuration (uses defaults if None)
        """
        self.config = config or OutputConfig()
        self.parser = AgentResponseParser()
        self.sanitizer = FrameworkSanitizer()
        self.plan_formatter = ValidationPlanFormatter()
        
        # Set up logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"OutputManager initialized with verbosity: {self.config.console_verbosity.name}")
    
    def process_agent_response(
        self,
        response: Any,
        agent_name: str,
        phase: str = ""
    ) -> str:
        """
        Process and display agent response.
        
        This is the main entry point for handling agent responses.
        It extracts the text, sanitizes it, formats validation plans,
        and outputs user-friendly text.
        
        Args:
            response: Raw response from BeeAI agent
            agent_name: Name of the agent (e.g., "DiscoveryAgent")
            phase: Current workflow phase
        
        Returns:
            Formatted text for console output
        """
        try:
            # Extract and sanitize text
            clean_text = self.parser.extract_simple_text(response)
            
            # Format validation plans if this is planning phase
            if phase == "planning" or "validation_plan" in clean_text:
                clean_text = self.plan_formatter.format_plan(clean_text)
            
            # Format for console based on configuration
            if self.config.console_format == "simple":
                # Simple format: "Agent: message"
                if self.config.show_agent_name:
                    formatted = f"{agent_name}: {clean_text}"
                else:
                    formatted = clean_text
            else:
                # Detailed format with icons (future enhancement)
                formatted = f"{agent_name}: {clean_text}"
            
            # Log to console
            print(formatted)
            
            # Also log to debug file (with full details)
            self.logger.debug(
                f"Agent response processed",
                extra={
                    "agent": agent_name,
                    "phase": phase,
                    "raw_response_type": type(response).__name__,
                    "clean_text_length": len(clean_text)
                }
            )
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"Error processing agent response: {e}", exc_info=True)
            # Fallback to simple string conversion
            fallback = f"{agent_name}: {str(response)}"
            print(fallback)
            return fallback
    
    def process_reasoning_chain(
        self,
        chain: ReasoningChain,
        agent_name: str
    ) -> None:
        """
        Process and display a complete reasoning chain.
        
        This method handles the full structured reasoning chain,
        displaying each step according to the verbosity level.
        
        Args:
            chain: Parsed reasoning chain
            agent_name: Name of the agent
        """
        if self.config.console_verbosity == VerbosityLevel.MINIMAL:
            # Just show final answer
            print(f"{agent_name}: {self.sanitizer.sanitize(chain.final_answer)}")
        
        elif self.config.console_verbosity == VerbosityLevel.STANDARD:
            # Show key steps and final answer
            for step in chain.steps:
                if step.has_action() and step.action:
                    # Show actions
                    action_desc = self.sanitizer.sanitize_tool_name(step.action)
                    print(f"{agent_name}: Using {action_desc}")
                if step.observation:
                    # Show observations
                    obs = self.sanitizer.sanitize(step.observation)
                    print(f"{agent_name}: {obs}")
            
            # Show final answer
            print(f"{agent_name}: {self.sanitizer.sanitize(chain.final_answer)}")
        
        elif self.config.console_verbosity == VerbosityLevel.DETAILED:
            # Show thoughts, actions, and observations
            for step in chain.steps:
                print(f"{agent_name}: {self.sanitizer.sanitize(step.thought)}")
                if step.has_action() and step.action:
                    action_desc = self.sanitizer.sanitize_tool_name(step.action)
                    print(f"{agent_name}: Using {action_desc}")
                if step.observation:
                    obs = self.sanitizer.sanitize(step.observation)
                    print(f"{agent_name}: {obs}")
            
            print(f"{agent_name}: {self.sanitizer.sanitize(chain.final_answer)}")
        
        else:  # COMPREHENSIVE
            # Show everything including framework markers (for debugging)
            for step in chain.steps:
                print(f"{agent_name}: Thought: {step.thought}")
                if step.has_action():
                    print(f"{agent_name}: Action: {step.action}")
                    if step.action_input:
                        print(f"{agent_name}: Action Input: {step.action_input}")
                if step.observation:
                    print(f"{agent_name}: Observation: {step.observation}")
            
            print(f"{agent_name}: Final Answer: {chain.final_answer}")
    
    def log_tool_operation(
        self,
        tool_name: str,
        args: dict,
        result: Any,
        duration_ms: int,
        agent_name: str = "Agent"
    ) -> None:
        """
        Log MCP tool operation.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Tool result
            duration_ms: Execution duration in milliseconds
            agent_name: Name of the agent using the tool
        """
        # Sanitize tool name for display
        display_name = self.sanitizer.sanitize_tool_name(tool_name)
        
        # Log to console if verbosity allows
        if self.config.console_verbosity.value >= VerbosityLevel.STANDARD.value:
            print(f"{agent_name}: Executed {display_name} ({duration_ms}ms)")
        
        # Always log to debug file
        self.logger.debug(
            f"Tool operation: {tool_name}",
            extra={
                "agent": agent_name,
                "tool": tool_name,
                "duration_ms": duration_ms,
                "success": result is not None
            }
        )

# Made with Bob
