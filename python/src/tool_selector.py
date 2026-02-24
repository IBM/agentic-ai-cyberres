#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Intelligent tool selection based on discovered applications."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationPriority(Enum):
    """Priority levels for validation tools."""
    CRITICAL = 3  # Database connectivity, core services
    HIGH = 2      # Configuration validation, replica status
    MEDIUM = 1    # Performance checks, optional features
    LOW = 0       # Nice-to-have validations


@dataclass
class ToolSelection:
    """Represents a selected validation tool."""
    tool_name: str
    app_info: Dict[str, Any]
    priority: ValidationPriority
    reason: str
    parameters: Dict[str, Any]


class ToolSelector:
    """Selects validation tools based on discovered applications and available MCP tools.
    
    Uses dynamic tool discovery - matches application names to available MCP tools
    by analyzing tool names instead of hardcoded mappings. This follows MCP best practices.
    """
    
    # Keywords that indicate tool priority
    CRITICAL_KEYWORDS = ["validate", "connect", "connectivity", "health"]
    HIGH_KEYWORDS = ["check", "status", "config", "replication", "replica"]
    MEDIUM_KEYWORDS = ["query", "test", "verify"]
    
    # VM core tools (always included if available)
    VM_CORE_PATTERNS = ["vm_", "ping", "ssh", "network"]
    
    def __init__(self):
        """Initialize tool selector."""
        self.selected_tools: List[ToolSelection] = []
    
    def select_tools(
        self,
        discovered_apps: List[Dict[str, Any]],
        available_tools: List[str],
        ssh_creds: Dict[str, str]
    ) -> List[ToolSelection]:
        """Select validation tools based on discovered applications using dynamic discovery.
        
        Automatically matches application names to available MCP tools by analyzing
        tool names instead of using hardcoded mappings.
        
        Args:
            discovered_apps: List of discovered applications from MCP
            available_tools: List of available MCP tool names
            ssh_creds: SSH credentials for tool parameters
        
        Returns:
            List of selected tools with priorities
        """
        selections = []
        
        # Step 1: Add VM core tools (tools matching VM patterns)
        for tool_name in available_tools:
            if any(pattern in tool_name.lower() for pattern in self.VM_CORE_PATTERNS):
                priority = self._determine_priority(tool_name)
                reason = self._generate_reason(tool_name)
                selections.append(ToolSelection(
                    tool_name=tool_name,
                    app_info={"name": "vm", "type": "infrastructure"},
                    priority=priority,
                    reason=reason,
                    parameters=self._build_parameters(tool_name, {}, ssh_creds)
                ))
                logger.info(f"Selected VM tool '{tool_name}' ({reason})")
        
        # Step 2: Match discovered apps to available tools dynamically
        for app in discovered_apps:
            app_name = app.get("name", "").lower()
            
            # Normalize app name: "Oracle Database" -> "oracle"
            normalized_name = app_name.split()[0] if app_name else ""
            
            # Find tools that match this application
            matched_tools = []
            for tool_name in available_tools:
                tool_lower = tool_name.lower()
                
                # Check if tool name contains app name or normalized name
                if normalized_name in tool_lower or any(word in tool_lower for word in app_name.split() if len(word) > 3):
                    matched_tools.append(tool_name)
            
            if matched_tools:
                logger.info(f"Found {len(matched_tools)} tools for {app_name}: {matched_tools}")
                for tool_name in matched_tools:
                    priority = self._determine_priority(tool_name)
                    reason = self._generate_reason(tool_name)
                    selections.append(ToolSelection(
                        tool_name=tool_name,
                        app_info=app,
                        priority=priority,
                        reason=reason,
                        parameters=self._build_parameters(tool_name, app, ssh_creds)
                    ))
                    logger.info(f"Selected tool '{tool_name}' for {app_name} ({reason})")
            else:
                logger.info(f"No matching tools found for application: {app_name}")
        
        # Sort by priority (highest first)
        selections.sort(key=lambda x: x.priority.value, reverse=True)
        
        self.selected_tools = selections
        return selections
    
    def _determine_priority(self, tool_name: str) -> ValidationPriority:
        """Determine priority based on tool name keywords.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            ValidationPriority level
        """
        tool_lower = tool_name.lower()
        
        # Check for critical keywords
        if any(keyword in tool_lower for keyword in self.CRITICAL_KEYWORDS):
            return ValidationPriority.CRITICAL
        
        # Check for high priority keywords
        if any(keyword in tool_lower for keyword in self.HIGH_KEYWORDS):
            return ValidationPriority.HIGH
        
        # Check for medium priority keywords
        if any(keyword in tool_lower for keyword in self.MEDIUM_KEYWORDS):
            return ValidationPriority.MEDIUM
        
        # Default to low priority
        return ValidationPriority.LOW
    
    def _generate_reason(self, tool_name: str) -> str:
        """Generate a human-readable reason for tool selection.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Reason string
        """
        tool_lower = tool_name.lower()
        
        # Generate reason based on tool name
        if "validate" in tool_lower:
            return "Validation check"
        elif "connect" in tool_lower or "connectivity" in tool_lower:
            return "Connectivity check"
        elif "health" in tool_lower:
            return "Health check"
        elif "status" in tool_lower:
            return "Status check"
        elif "config" in tool_lower:
            return "Configuration validation"
        elif "replication" in tool_lower or "replica" in tool_lower:
            return "Replication status"
        elif "query" in tool_lower:
            return "Data integrity check"
        elif "test" in tool_lower:
            return "Functional test"
        else:
            return f"Check {tool_name.replace('_', ' ')}"
    
    def _build_parameters(
        self,
        tool_name: str,
        app_info: Dict[str, Any],
        ssh_creds: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build parameters for a tool based on app info and credentials.
        
        Args:
            tool_name: Name of the tool
            app_info: Application information
            ssh_creds: SSH credentials
        
        Returns:
            Parameters dictionary for the tool
        """
        params = {
            "hostname": ssh_creds.get("hostname"),
            "username": ssh_creds.get("username"),
        }
        
        # Add password or key
        if ssh_creds.get("password"):
            params["password"] = ssh_creds["password"]
        elif ssh_creds.get("key_path"):
            params["key_path"] = ssh_creds["key_path"]
        
        # Add application-specific parameters
        if app_info:
            if "port" in app_info:
                params["port"] = app_info["port"]
            if "version" in app_info:
                params["version"] = app_info["version"]
            if "install_path" in app_info:
                params["install_path"] = app_info["install_path"]
        
        return params
    
    def get_critical_tools(self) -> List[ToolSelection]:
        """Get only critical priority tools.
        
        Returns:
            List of critical tools
        """
        return [t for t in self.selected_tools if t.priority == ValidationPriority.CRITICAL]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about selected tools.
        
        Returns:
            Dictionary with tool counts by priority
        """
        return {
            "total_tools": len(self.selected_tools),
            "critical": len([t for t in self.selected_tools if t.priority == ValidationPriority.CRITICAL]),
            "high": len([t for t in self.selected_tools if t.priority == ValidationPriority.HIGH]),
            "medium": len([t for t in self.selected_tools if t.priority == ValidationPriority.MEDIUM]),
            "low": len([t for t in self.selected_tools if t.priority == ValidationPriority.LOW]),
        }

# Made with Bob
