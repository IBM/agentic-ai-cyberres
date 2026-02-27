#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Logging package for BeeAI validation agents.

Provides dual-stream logging:
- Console: Clean, coloured, human-readable agent activity
- File: Structured JSON lines with full context for debugging

Quick start:
    from agent_logging import setup_logging, AgentTracker

    log_file = setup_logging(log_dir="logs")
    tracker = AgentTracker("DiscoveryAgent", resource="192.168.1.100")

    with tracker.phase("discovery"):
        tracker.decision("Scanning standard ports")
        tracker.tool_call("scan_ports", {"host": "192.168.1.100"})
"""

from agent_logging.agent_logger import (
    setup_logging,
    get_agent_logger,
    get_log_file,
    AgentTracker,
    WorkflowProgressDisplay,
    ConsoleFormatter,
    FileFormatter,
    Colours,
    AGENT_COLOURS,
    PHASE_ICONS,
    STATUS_ICONS,
)

__all__ = [
    "setup_logging",
    "get_agent_logger",
    "get_log_file",
    "AgentTracker",
    "WorkflowProgressDisplay",
    "ConsoleFormatter",
    "FileFormatter",
    "Colours",
    "AGENT_COLOURS",
    "PHASE_ICONS",
    "STATUS_ICONS",
]

# Made with Bob
