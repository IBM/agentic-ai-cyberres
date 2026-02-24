#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Feature flag system for gradual rollout of new capabilities."""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Manage feature flags for gradual rollout.
    
    Feature flags allow enabling/disabling new features without code changes,
    enabling safe rollout and easy rollback if issues arise.
    """
    
    # Default flag values
    DEFAULT_FLAGS = {
        # Phase 1 flags
        'use_new_orchestrator': False,
        'use_tool_coordinator': True,
        'use_state_management': True,
        'use_discovery_agent': True,
        'use_classification_agent': True,
        'use_validation_agent': True,
        'use_reporting_agent': True,
        'use_parallel_execution': False,
        'enable_tool_caching': True,
        'enable_retry_logic': True,
        'enable_execution_history': True,
        
        # Phase 2 flags - Enhanced Agent Features
        'parallel_tool_execution': False,  # Execute tools in parallel
        'ai_classification': False,        # Use AI for classification
        'ai_reporting': False,             # Use AI for report generation
        'ai_plan_optimization': False,     # Use AI to optimize plans
        'auto_resume_workflows': False,    # Auto-resume failed workflows
        'batch_validations': False,        # Batch multiple validations
        'lazy_discovery': False,           # Only discover when needed
        'enhanced_error_recovery': True,   # Enhanced error recovery
    }
    
    def __init__(self, config: Optional[Dict[str, bool]] = None):
        """Initialize feature flags.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.flags = self.DEFAULT_FLAGS.copy()
        
        # Load from environment variables
        self._load_from_env()
        
        # Override with provided config
        if config:
            self.flags.update(config)
        
        logger.info(
            "Feature flags initialized",
            extra={"enabled_flags": [k for k, v in self.flags.items() if v]}
        )
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag
        
        Returns:
            True if enabled, False otherwise
        """
        enabled = self.flags.get(flag_name, False)
        
        logger.debug(
            f"Feature flag check: {flag_name}",
            extra={"flag": flag_name, "enabled": enabled}
        )
        
        return enabled
    
    def enable(self, flag_name: str):
        """Enable a feature flag.
        
        Args:
            flag_name: Name of the feature flag
        """
        self.flags[flag_name] = True
        logger.info(f"Feature flag enabled: {flag_name}")
    
    def disable(self, flag_name: str):
        """Disable a feature flag.
        
        Args:
            flag_name: Name of the feature flag
        """
        self.flags[flag_name] = False
        logger.info(f"Feature flag disabled: {flag_name}")
    
    def set(self, flag_name: str, value: bool):
        """Set a feature flag value.
        
        Args:
            flag_name: Name of the feature flag
            value: Flag value (True/False)
        """
        self.flags[flag_name] = value
        logger.info(f"Feature flag set: {flag_name} = {value}")
    
    def get_all(self) -> Dict[str, bool]:
        """Get all feature flags.
        
        Returns:
            Dictionary of all flags and their values
        """
        return self.flags.copy()
    
    def get_enabled(self) -> list[str]:
        """Get list of enabled feature flags.
        
        Returns:
            List of enabled flag names
        """
        return [name for name, enabled in self.flags.items() if enabled]
    
    def get_disabled(self) -> list[str]:
        """Get list of disabled feature flags.
        
        Returns:
            List of disabled flag names
        """
        return [name for name, enabled in self.flags.items() if not enabled]
    
    def _load_from_env(self):
        """Load feature flags from environment variables.
        
        Environment variables should be in format: FEATURE_FLAG_<NAME>=true/false
        For example: FEATURE_FLAG_USE_NEW_ORCHESTRATOR=true
        """
        for flag_name in self.flags.keys():
            env_var = f"FEATURE_FLAG_{flag_name.upper()}"
            env_value = os.getenv(env_var)
            
            if env_value is not None:
                # Parse boolean value
                self.flags[flag_name] = self._parse_bool(env_value)
                logger.debug(
                    f"Loaded feature flag from environment: {flag_name}",
                    extra={"flag": flag_name, "value": self.flags[flag_name]}
                )
    
    def _parse_bool(self, value: str) -> bool:
        """Parse boolean value from string.
        
        Args:
            value: String value to parse
        
        Returns:
            Boolean value
        """
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def __repr__(self) -> str:
        """String representation of feature flags.
        
        Returns:
            String representation
        """
        enabled = self.get_enabled()
        return f"FeatureFlags(enabled={len(enabled)}, flags={enabled})"


# Global instance
feature_flags = FeatureFlags()


# Convenience functions
def is_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled.
    
    Args:
        flag_name: Name of the feature flag
    
    Returns:
        True if enabled, False otherwise
    """
    return feature_flags.is_enabled(flag_name)


def enable(flag_name: str):
    """Enable a feature flag.
    
    Args:
        flag_name: Name of the feature flag
    """
    feature_flags.enable(flag_name)


def disable(flag_name: str):
    """Disable a feature flag.
    
    Args:
        flag_name: Name of the feature flag
    """
    feature_flags.disable(flag_name)


# Made with Bob