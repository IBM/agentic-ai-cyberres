"""
Log Transformer for Agent-Style Output

Transforms technical log messages into natural language agent narratives.
Intercepts MCP tool warnings and converts them to user-friendly messages.
"""

import logging
import re
from typing import Optional, Dict, Any


class AgentLogTransformer(logging.Filter):
    """
    Transforms technical log messages into agent-style narratives.
    
    Converts messages like:
        "2026-03-12 13:15:39,664 WARNING mcp.ssh_utils SSH trust_unknown_hosts is enabled"
    
    Into:
        "Agent: Connecting to remote system (accepting new host keys)..."
    """
    
    # Patterns to match and transform
    TRANSFORMATIONS = {
        # SSH connection messages
        r"SSH trust_unknown_hosts is enabled.*": 
            "Connecting to remote system (accepting new host keys)...",
        
        # Command failures
        r"Command failed with exit code (\d+)":
            "Tool execution failed (exit code {0}), trying alternative approach...",
        
        # Connection errors
        r"Connection refused|Connection timed out":
            "Unable to connect to target system, retrying with different method...",
        
        # Authentication errors
        r"Authentication failed|Permission denied":
            "Authentication unsuccessful, attempting alternative credentials...",
        
        # Tool execution
        r"Executing tool: (\w+)":
            "Using {0} to gather information...",
        
        # Discovery operations
        r"Scanning ports|Port scan":
            "Scanning target system for active services...",
        
        r"Detecting workloads|Workload discovery":
            "Analyzing system workloads and applications...",
        
        # Validation operations
        r"Validating.*database":
            "Verifying database connectivity and integrity...",
        
        r"Checking.*connectivity":
            "Testing network connectivity...",
        
        # Generic retry
        r"Retrying|Retry attempt (\d+)":
            "Retrying operation (attempt {0})...",
    }
    
    # Patterns to completely suppress (don't show at all)
    SUPPRESS_PATTERNS = [
        r"Using AiohttpTransport",
        r"Creating new ClientSession",
        r"NEW SESSION",
        r"setup plugin alembic",
        r"Phoenix Project:",
        r"Span Processor:",
    ]
    
    def __init__(self, agent_name: str = "Agent"):
        """
        Initialize the transformer.
        
        Args:
            agent_name: Name to use in transformed messages (e.g., "Discovery", "Validation")
        """
        super().__init__()
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Compile patterns for efficiency
        self.compiled_transforms = {
            re.compile(pattern): template 
            for pattern, template in self.TRANSFORMATIONS.items()
        }
        self.compiled_suppress = [
            re.compile(pattern) 
            for pattern in self.SUPPRESS_PATTERNS
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and transform log records.
        
        Returns:
            True to emit the record, False to suppress it
        """
        message = record.getMessage()
        
        # Check if message should be completely suppressed
        for pattern in self.compiled_suppress:
            if pattern.search(message):
                return False  # Suppress this message
        
        # Try to transform the message
        transformed = self._transform_message(message, record)
        
        if transformed:
            # Replace the message with transformed version
            record.msg = transformed
            record.args = ()  # Clear args since we've formatted the message
            
            # Remove timestamp and logger name from console output
            # by modifying the record's formatting attributes
            if hasattr(record, 'funcName'):
                record.funcName = ''
            if hasattr(record, 'name'):
                record.name = self.agent_name
        
        return True  # Emit the (possibly transformed) record
    
    def _transform_message(self, message: str, record: logging.LogRecord) -> Optional[str]:
        """
        Transform a message using pattern matching.
        
        Args:
            message: Original log message
            record: Log record for context
        
        Returns:
            Transformed message or None if no transformation applies
        """
        for pattern, template in self.compiled_transforms.items():
            match = pattern.search(message)
            if match:
                # Extract groups for template formatting
                groups = match.groups()
                
                try:
                    if groups:
                        # Format template with captured groups
                        transformed = template.format(*groups)
                    else:
                        transformed = template
                    
                    # Add agent name prefix
                    return f"{self.agent_name}: {transformed}"
                
                except (IndexError, KeyError) as e:
                    self.logger.debug(f"Template formatting error: {e}")
                    return None
        
        return None  # No transformation applied


class AgentConsoleFormatter(logging.Formatter):
    """
    Custom formatter for agent-style console output.
    
    Removes timestamps and technical details, showing only the message.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the record for console output."""
        # If the message has been transformed (starts with "Agent:"), 
        # just return the message without timestamp/level
        message = record.getMessage()
        
        if message.startswith(("Agent:", "Discovery:", "Validation:", "Evaluation:")):
            return message
        
        # For other messages, use minimal formatting
        if record.levelno >= logging.WARNING:
            return f"⚠️  {message}"
        elif record.levelno >= logging.ERROR:
            return f"❌ {message}"
        else:
            return message


def setup_agent_log_transformation(
    agent_name: str = "Agent",
    console_handler: Optional[logging.Handler] = None
) -> AgentLogTransformer:
    """
    Set up log transformation for agent-style output.
    
    Args:
        agent_name: Name to use in transformed messages
        console_handler: Console handler to apply formatter to (optional)
    
    Returns:
        The transformer filter instance
    """
    transformer = AgentLogTransformer(agent_name=agent_name)
    
    # Add transformer to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(transformer)
    
    # If console handler provided, apply custom formatter
    if console_handler:
        console_handler.setFormatter(AgentConsoleFormatter())
    
    return transformer


# Made with Bob