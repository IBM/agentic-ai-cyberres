"""Validation plan formatter for user-friendly output."""

import json
import re
from typing import Any, Dict, List, Optional


class ValidationPlanFormatter:
    """
    Formats validation plans from JSON to user-friendly text.
    
    Converts technical JSON validation plans into natural language
    descriptions suitable for end users.
    """
    
    def format_plan(self, text: str) -> str:
        """
        Format validation plan text.
        
        Detects if text contains a JSON validation plan and suppresses it
        since the actual plan is generated deterministically and shown separately.
        
        Args:
            text: Raw text that may contain a validation plan
            
        Returns:
            Formatted user-friendly text or empty string if plan detected
        """
        # Check if this looks like a validation plan response
        if not self._is_validation_plan(text):
            return text
        
        # Extract JSON from the text
        plan_json = self._extract_json(text)
        if not plan_json:
            return text
        
        # Suppress the LLM's plan JSON since it's not actually used
        # The actual plan is generated deterministically and shown via wf_tracker.decision()
        return "Analyzing resource requirements and building validation checklist..."
    
    def _is_validation_plan(self, text: str) -> bool:
        """Check if text contains a validation plan."""
        indicators = [
            "validation_plan",
            "check_name",
            "criticality",
            "Network Connectivity",
            "Data Integrity"
        ]
        return any(indicator in text for indicator in indicators)
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text that may contain markdown code blocks."""
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*"validation_plan".*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def _format_plan_json(self, plan_data: Dict[str, Any]) -> str:
        """
        Format validation plan JSON into user-friendly text.
        
        Args:
            plan_data: Parsed JSON validation plan
            
        Returns:
            Formatted text description
        """
        if "validation_plan" not in plan_data:
            return str(plan_data)
        
        checks = plan_data["validation_plan"]
        if not checks:
            return "No validation checks planned."
        
        lines = []
        lines.append(f"Planned {len(checks)} validation checks:")
        lines.append("")
        
        # Sort by criticality
        sorted_checks = sorted(checks, key=lambda x: x.get("criticality", 999))
        
        for i, check in enumerate(sorted_checks, 1):
            check_name = check.get("check_name", "Unknown Check")
            description = check.get("description", "")
            criticality = check.get("criticality", "N/A")
            steps = check.get("steps", [])
            
            # Format criticality as priority level
            priority_label = self._format_priority(criticality)
            
            lines.append(f"{i}. {check_name} ({priority_label})")
            if description:
                lines.append(f"   {description}")
            
            # Summarize steps
            if steps:
                step_summary = self._summarize_steps(steps)
                lines.append(f"   → {step_summary}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_priority(self, criticality: Any) -> str:
        """Format criticality as priority label."""
        try:
            crit_num = int(criticality)
            if crit_num == 1:
                return "Critical"
            elif crit_num == 2:
                return "High Priority"
            elif crit_num == 3:
                return "Medium Priority"
            elif crit_num == 4:
                return "Low Priority"
            else:
                return f"Priority {crit_num}"
        except (ValueError, TypeError):
            return "Standard"
    
    def _summarize_steps(self, steps: List[Dict[str, Any]]) -> str:
        """Summarize validation steps into readable text."""
        if not steps:
            return "No steps defined"
        
        # Extract tool names
        tools = []
        for step in steps:
            tool = step.get("tool", "")
            if tool:
                # Convert tool names to readable format
                readable_tool = self._format_tool_name(tool)
                tools.append(readable_tool)
        
        if not tools:
            return f"{len(steps)} validation steps"
        
        # Create summary
        if len(tools) == 1:
            return f"Using {tools[0]}"
        elif len(tools) == 2:
            return f"Using {tools[0]} and {tools[1]}"
        else:
            return f"Using {tools[0]}, {tools[1]}, and {len(tools)-2} more tools"
    
    def _format_tool_name(self, tool: str) -> str:
        """Convert technical tool name to readable format."""
        # Map common tool names to readable versions
        tool_map = {
            "tcp_portcheck": "port connectivity check",
            "db_oracle_connect": "Oracle database connection test",
            "db_mongo_connect": "MongoDB connection test",
            "vm_linux_uptime_load_mem": "system health check",
            "vm_linux_services": "service status check",
            "ssh_command": "remote command execution",
        }
        
        return tool_map.get(tool, tool.replace("_", " "))

# Made with Bob
