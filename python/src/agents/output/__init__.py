"""
Production-grade agent output management system.

This package provides comprehensive output management for BeeAI agents, including:
- Response parsing from BeeAI agent outputs
- Framework artifact sanitization
- Professional narrative formatting
- Multi-tier logging (console, debug, audit, MCP)
- Configurable verbosity levels

Usage:
    from agents.output import OutputManager, OutputConfig, VerbosityLevel
    
    config = OutputConfig(console_verbosity=VerbosityLevel.STANDARD)
    manager = OutputManager(config)
    
    # Process agent response
    manager.process_agent_response(response, "DiscoveryAgent", "discovery")
"""

from .models import (
    VerbosityLevel,
    ThoughtStep,
    ReasoningChain,
    ThoughtBlock,
    OutputConfig,
)
from .response_parser import AgentResponseParser
from .framework_sanitizer import FrameworkSanitizer
from .output_manager import OutputManager
from .log_transformer import (
    AgentLogTransformer,
    AgentConsoleFormatter,
    setup_agent_log_transformation,
)
from .plan_formatter import ValidationPlanFormatter

__all__ = [
    "VerbosityLevel",
    "ThoughtStep",
    "ReasoningChain",
    "ThoughtBlock",
    "OutputConfig",
    "AgentResponseParser",
    "FrameworkSanitizer",
    "OutputManager",
    "AgentLogTransformer",
    "AgentConsoleFormatter",
    "setup_agent_log_transformation",
    "ValidationPlanFormatter",
]

__version__ = "1.0.0"

# Made with Bob
