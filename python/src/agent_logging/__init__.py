#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Agent logging package for BeeAI recovery-validation workflow.

Provides structured dual-stream logging:
  - Console: clean agent role banners at INFO level
  - File:    JSON-structured DEBUG events for post-run analysis

Usage::

    from agent_logging.agent_logger import setup_logging, AgentTracker, WorkflowProgressDisplay

    log_file = setup_logging(log_dir="logs", log_level="DEBUG", console_level="INFO")
    tracker = AgentTracker("DiscoveryAgent", resource="192.168.1.100")
    tracker.start("Scanning workloads")
"""

from agent_logging.agent_logger import (
    setup_logging,
    AgentTracker,
    WorkflowProgressDisplay,
)

__all__ = ["setup_logging", "AgentTracker", "WorkflowProgressDisplay"]

# Made with Bob
