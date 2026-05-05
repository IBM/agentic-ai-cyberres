"""Sanitizer for removing framework artifacts from agent output."""

import re
from typing import Dict, Any


class FrameworkSanitizer:
    """Removes BeeAI framework identifiers and implementation details."""
    
    # Framework markers to remove
    FRAMEWORK_MARKERS = [
        (r"Thought:\s*", ""),
        (r"Action:\s*", ""),
        (r"Action Input:\s*", ""),
        (r"Observation:\s*", ""),
        (r"Final Answer:\s*", ""),
        (r"\[INST\].*?\[/INST\]", ""),
        (r"<\|.*?\|>", ""),
        (r"###\s*Instruction:.*?###\s*Response:", "", re.DOTALL),
    ]
    
    # Model references to remove
    MODEL_REFERENCES = [
        (r"ollama:llama\d+\.\d+", "AI model"),
        (r"gpt-\d+(-\w+)?", "AI model"),
        (r"claude-\d+(-\w+)?", "AI model"),
        (r"ReActAgent", "agent"),
        (r"RequirementAgent", "agent"),
    ]
    
    # Implementation details to sanitize
    IMPLEMENTATION_PATTERNS = [
        (r"tool_name=(\w+)", r"using \1"),
        (r"mcp_tool:\s*(\w+)", r"tool: \1"),
        (r"ssh_password=\*+", "credentials"),
        (r"password=\*+", "credentials"),
    ]
    
    # Tool name mappings for professional display
    TOOL_DISPLAY_NAMES = {
        "discover_workload": "workload discovery",
        "db_mongo_ssh_ping": "MongoDB connectivity check",
        "db_mongo_ssh_rs_status": "MongoDB replica set status check",
        "validate_collection": "collection validation",
        "vm_linux_uptime_load_mem": "system resource check",
        "vm_linux_fs_usage": "filesystem usage check",
        "vm_linux_services": "service status check",
        "tcp_portcheck": "network connectivity check",
        "db_oracle_connect": "Oracle connectivity check",
        "db_oracle_tablespaces": "tablespace usage check",
    }
    
    def sanitize(self, text: str) -> str:
        """
        Remove all framework artifacts from text.
        
        Args:
            text: Raw text with framework markers
        
        Returns:
            Sanitized text suitable for user display
        """
        if not isinstance(text, str):
            text = str(text)
        
        result = text
        
        # Remove framework markers
        for pattern, replacement, *flags in self.FRAMEWORK_MARKERS:
            flag = flags[0] if flags else 0
            result = re.sub(pattern, replacement, result, flags=flag)
        
        # Replace model references
        for pattern, replacement in self.MODEL_REFERENCES:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Sanitize implementation details
        for pattern, replacement in self.IMPLEMENTATION_PATTERNS:
            result = re.sub(pattern, replacement, result)
        
        # Clean up extra whitespace
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
        result = result.strip()
        
        return result
    
    def sanitize_tool_name(self, tool_name: str) -> str:
        """
        Convert tool name to professional display name.
        
        Args:
            tool_name: Technical tool name (e.g., "db_mongo_ssh_ping")
        
        Returns:
            Professional display name (e.g., "MongoDB connectivity check")
        """
        return self.TOOL_DISPLAY_NAMES.get(tool_name, tool_name.replace("_", " "))
    
    def sanitize_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Format tool call professionally.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
        
        Returns:
            Professional description of tool call
        """
        display_name = self.sanitize_tool_name(tool_name)
        
        # Extract key parameters (non-sensitive)
        key_params = []
        for key, value in args.items():
            if key.lower() not in {'password', 'ssh_password', 'key_path', 'token', 'secret'}:
                if key in {'host', 'ssh_host', 'hostname'}:
                    key_params.append(f"on {value}")
                elif key == 'port':
                    key_params.append(f"port {value}")
        
        if key_params:
            return f"{display_name} {' '.join(key_params)}"
        return display_name
    
    def sanitize_observation(self, observation: str) -> str:
        """
        Clean observation text for display.
        
        Args:
            observation: Raw observation from tool execution
        
        Returns:
            Sanitized observation text
        """
        result = observation
        
        # Remove technical error codes
        result = re.sub(r'\[ERROR_CODE_\w+\]', '', result)
        
        # Clean up JSON-like structures
        result = re.sub(r'\{["\']ok["\']: ?true\}', 'Success', result)
        result = re.sub(r'\{["\']ok["\']: ?false\}', 'Failed', result)
        
        return result.strip()

# Made with Bob
