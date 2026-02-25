"""
BeeAI-based agents for CyberRes Recovery Validation.

This package contains agents migrated from Pydantic AI to BeeAI framework.
"""

__version__ = "0.1.0"

from .config import BeeAIConfig
from .base_agent import BaseValidationAgent

__all__ = [
    "BeeAIConfig",
    "BaseValidationAgent",
]

# Made with Bob
