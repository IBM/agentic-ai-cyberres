#
# Copyright contributors to the agentic-ai-cyberres project
#
"""LLM-driven intelligent tool selector for MCP-based validation.

This module uses an LLM to intelligently select validation tools based on:
1. Tool descriptions and capabilities from MCP
2. Available credentials (SSH, database, etc.)
3. Discovered applications and context
4. Validation goals

This approach is more intelligent and maintainable than hardcoded pattern matching.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from llm import get_chat_llm

logger = logging.getLogger(__name__)


class ValidationPriority(Enum):
    """Priority levels for validation tools."""
    CRITICAL = "CRITICAL"  # Discovery and core validation
    HIGH = "HIGH"          # Infrastructure and connectivity
    MEDIUM = "MEDIUM"      # Deep validation requiring app credentials
    LOW = "LOW"            # Optional/nice-to-have validations


@dataclass
class ToolSelectionResult:
    """Result from LLM tool selection."""
    tool_name: str
    priority: str
    can_execute: bool
    reasoning: str
    required_credentials: Optional[List[str]] = None  # Make optional with default
    missing_credentials: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Ensure required_credentials is always a list."""
        if self.required_credentials is None:
            self.required_credentials = []


@dataclass
class ToolSelectionSummary:
    """Summary of tool selection."""
    total_tools_available: int
    tools_can_execute: int
    tools_blocked_by_credentials: int
    recommendation: str


class LLMToolSelector:
    """LLM-driven intelligent tool selector.
    
    Uses an LLM to analyze tool descriptions, available credentials, and context
    to intelligently select the most appropriate validation tools.
    """
    
    def __init__(self):
        """Initialize LLM tool selector."""
        self.llm = get_chat_llm()
        logger.info("Initialized LLM tool selector")
    
    async def select_tools(
        self,
        discovered_apps: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        available_credentials: Dict[str, Any],
        validation_goal: str
    ) -> Tuple[List[ToolSelectionResult], ToolSelectionSummary]:
        """Use LLM to intelligently select tools based on context.
        
        Args:
            discovered_apps: Applications discovered on the target
            available_tools: MCP tools with descriptions and parameter info
            available_credentials: Available credentials by type
            validation_goal: What we're trying to validate
        
        Returns:
            Tuple of (selected tools, summary)
        """
        logger.info(f"Starting LLM-driven tool selection for: {validation_goal}")
        logger.info(f"Discovered apps: {len(discovered_apps)}, Available tools: {len(available_tools)}")
        
        # Build context for LLM
        context = {
            "discovered_applications": discovered_apps,
            "available_tools": available_tools,
            "available_credentials": self._sanitize_credentials(available_credentials),
            "validation_goal": validation_goal
        }
        
        # Create prompt
        prompt = self._build_selection_prompt(context)
        
        try:
            # Get LLM response
            logger.info("Requesting tool selection from LLM...")
            response = await self.llm.generate(prompt)
            
            # Parse response
            result = self._parse_llm_response(response)
            
            # Convert to dataclasses
            selected_tools = [
                ToolSelectionResult(**tool)
                for tool in result["selected_tools"]
            ]
            
            summary = ToolSelectionSummary(**result["summary"])
            
            logger.info(f"LLM selected {len(selected_tools)} tools: "
                       f"{summary.tools_can_execute} executable, "
                       f"{summary.tools_blocked_by_credentials} blocked")
            
            return selected_tools, summary
            
        except Exception as e:
            logger.error(f"Error in LLM tool selection: {e}", exc_info=True)
            # Fallback to basic selection if LLM fails
            return self._fallback_selection(discovered_apps, available_tools, available_credentials)
    
    def _sanitize_credentials(self, creds: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from credentials for LLM context.
        
        Args:
            creds: Raw credentials dictionary
        
        Returns:
            Sanitized credentials (passwords replaced with "available")
        """
        sanitized = {}
        for cred_type, cred_data in creds.items():
            if cred_data is None:
                sanitized[cred_type] = None
            elif isinstance(cred_data, dict):
                sanitized[cred_type] = {
                    k: "available" if k in ["password", "key", "ssh_password", "ssh_key_path"] else v
                    for k, v in cred_data.items()
                }
            else:
                sanitized[cred_type] = "available"
        return sanitized
    
    def _build_selection_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for LLM tool selection.
        
        Args:
            context: Context dictionary with apps, tools, credentials, goal
        
        Returns:
            Formatted prompt string
        """
        # Analyze available credentials to provide clear guidance
        available_creds = context.get("available_credentials", {})
        has_ssh = available_creds.get("ssh") is not None
        has_app_creds = any(k != "ssh" and v is not None for k, v in available_creds.items())
        
        cred_status = []
        if has_ssh:
            cred_status.append("✓ SSH credentials ARE AVAILABLE - SSH-based tools CAN execute")
        else:
            cred_status.append("✗ SSH credentials NOT available - SSH-based tools CANNOT execute")
        
        if has_app_creds:
            app_cred_types = [k for k, v in available_creds.items() if k != "ssh" and v is not None]
            cred_status.append(f"✓ Application credentials available for: {', '.join(app_cred_types)}")
        else:
            cred_status.append("✗ No application-specific credentials available")
        
        # Build explicit SSH-enabled tools list if SSH is available
        ssh_enabled_examples = ""
        if has_ssh:
            ssh_enabled_examples = """

CRITICAL: SSH CREDENTIALS ARE AVAILABLE - The following tools CAN EXECUTE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ discover_applications - CAN EXECUTE (uses SSH to scan processes/ports)
✓ discover_workload - CAN EXECUTE (uses SSH to detect applications)
✓ discover_os_only - CAN EXECUTE (uses SSH to get OS info)
✓ get_raw_server_data - CAN EXECUTE (uses SSH to collect system data)
✓ validate_vm - CAN EXECUTE (uses SSH for VM validation)
✓ check_network_connectivity - CAN EXECUTE (uses SSH/ping)

These tools DO NOT need application credentials (Oracle/MongoDB passwords).
They work with SSH credentials alone. Mark them as can_execute: true.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tools that CANNOT execute without app credentials:
✗ connect_to_db - CANNOT EXECUTE (needs Oracle/MongoDB credentials)
✗ validate_oracle_db - CANNOT EXECUTE (needs Oracle credentials)
✗ validate_mongodb - CANNOT EXECUTE (needs MongoDB credentials)
✗ query_database - CANNOT EXECUTE (needs database credentials)
"""
        
        return f"""You are an intelligent tool selector for infrastructure validation.

Your task: Select the most appropriate validation tools based on available context.

CREDENTIAL STATUS (READ THIS CAREFULLY):
{chr(10).join(cred_status)}{ssh_enabled_examples}

Context:
{json.dumps(context, indent=2)}

MANDATORY RULES FOR SSH-BASED TOOLS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. If SSH credentials are available, ALL SSH-based discovery tools MUST be marked as can_execute: true
2. SSH-based tools include ANY tool with these keywords: "discover", "workload", "get_raw_server_data", "validate_vm"
3. SSH-based tools DO NOT require application credentials (Oracle/MongoDB passwords)
4. NEVER mark SSH-based tools as blocked by missing application credentials
5. Application credentials are ONLY needed for direct database connection tools (connect_to_db, validate_oracle_db, etc.)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Instructions:
1. Analyze each available tool's capabilities and requirements
2. Match tools to discovered applications
3. Check if required credentials are available (see CREDENTIAL STATUS above)
4. For SSH-based tools: If SSH is available, mark can_execute: true
5. For direct-access tools: Only mark can_execute: true if app credentials available
6. Provide clear reasoning for each selection

Priority Guidelines:
- CRITICAL: Discovery and core validation tools (especially SSH-based discovery)
- HIGH: Infrastructure and connectivity validation
- MEDIUM: Deep validation requiring app credentials
- LOW: Optional/nice-to-have validations

Tool Classification Examples:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SSH-BASED (need only SSH credentials):
  ✓ discover_applications → can_execute: true (if SSH available)
  ✓ discover_workload → can_execute: true (if SSH available)
  ✓ discover_os_only → can_execute: true (if SSH available)
  ✓ get_raw_server_data → can_execute: true (if SSH available)
  ✓ validate_vm → can_execute: true (if SSH available)

DIRECT-ACCESS (need app credentials):
  ✗ connect_to_db → can_execute: false (if no Oracle/MongoDB creds)
  ✗ validate_oracle_db → can_execute: false (if no Oracle creds)
  ✗ validate_mongodb → can_execute: false (if no MongoDB creds)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output JSON format (IMPORTANT: Return ONLY valid JSON, no markdown):
{{
  "selected_tools": [
    {{
      "tool_name": "tool_name",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "can_execute": true|false,
      "reasoning": "why this tool is selected and what it validates",
      "required_credentials": ["credential_type"],
      "missing_credentials": ["credential_type"] (only if can_execute is false),
      "parameters": {{}} (only if can_execute is true)
    }}
  ],
  "summary": {{
    "total_tools_available": number,
    "tools_can_execute": number,
    "tools_blocked_by_credentials": number,
    "recommendation": "overall recommendation"
  }}
}}

Think step by step and provide comprehensive reasoning. Return ONLY the JSON object."""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.
        
        Args:
            response: Raw LLM response string
        
        Returns:
            Parsed dictionary
        """
        try:
            # Try to extract JSON from response (in case LLM adds markdown)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Try parsing entire response
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response[:500]}...")
            raise ValueError(f"LLM returned invalid JSON: {e}")
    
    def _fallback_selection(
        self,
        discovered_apps: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        available_credentials: Dict[str, Any]
    ) -> Tuple[List[ToolSelectionResult], ToolSelectionSummary]:
        """Fallback selection if LLM fails.
        
        Uses simple heuristics to select tools when LLM is unavailable.
        IMPROVED: Only selects tools for DETECTED applications.
        
        Args:
            discovered_apps: Discovered applications
            available_tools: Available MCP tools
            available_credentials: Available credentials
        
        Returns:
            Tuple of (selected tools, summary)
        """
        logger.warning("Using fallback tool selection (LLM unavailable)")
        
        selected_tools = []
        has_ssh = available_credentials.get("ssh") is not None
        
        # Extract detected application names (lowercase for matching)
        detected_app_names = [
            app.get("name", "").lower()
            for app in discovered_apps
        ]
        
        logger.info(f"Detected applications for tool selection: {detected_app_names}")
        
        # Map application keywords to tool patterns
        app_tool_patterns = {
            "oracle": ["oracle", "db_oracle"],
            "mongodb": ["mongo", "db_mongo"],
            "mongo": ["mongo", "db_mongo"],
            "postgresql": ["postgres", "db_postgres"],
            "postgres": ["postgres", "db_postgres"],
            "mysql": ["mysql", "db_mysql"],
            "nginx": ["nginx", "web"],
            "apache": ["apache", "web"],
            "tomcat": ["tomcat", "app"],
        }
        
        # Select tools based on detected applications
        for tool in available_tools:
            tool_name = tool["name"]
            tool_lower = tool_name.lower()
            
            # Check if this tool matches any detected application
            tool_matches_app = False
            matched_app = None
            
            for app_name in detected_app_names:
                # Check if app name matches any tool patterns
                if app_name in app_tool_patterns:
                    patterns = app_tool_patterns[app_name]
                    if any(pattern in tool_lower for pattern in patterns):
                        tool_matches_app = True
                        matched_app = app_name
                        break
            
            # Only add tool if it matches a detected application
            if tool_matches_app and has_ssh:
                selected_tools.append(ToolSelectionResult(
                    tool_name=tool_name,
                    priority="HIGH",
                    can_execute=True,
                    reasoning=f"Tool for detected application: {matched_app} (fallback selection)",
                    required_credentials=["ssh"],
                    parameters=self._build_ssh_parameters(available_credentials["ssh"])
                ))
                logger.info(f"Selected tool {tool_name} for detected app {matched_app}")
            
            # Always include basic VM validation tools
            elif any(p in tool_lower for p in ["vm_core", "vm_ping"]) and has_ssh:
                selected_tools.append(ToolSelectionResult(
                    tool_name=tool_name,
                    priority="MEDIUM",
                    can_execute=True,
                    reasoning="Basic VM validation tool (fallback selection)",
                    required_credentials=["ssh"],
                    parameters=self._build_ssh_parameters(available_credentials["ssh"])
                ))
                logger.info(f"Selected basic VM tool {tool_name}")
        
        # If no tools selected, add basic VM validation
        if not selected_tools and has_ssh:
            for tool in available_tools:
                tool_name = tool["name"]
                tool_lower = tool_name.lower()
                if "vm" in tool_lower or "ping" in tool_lower:
                    selected_tools.append(ToolSelectionResult(
                        tool_name=tool_name,
                        priority="MEDIUM",
                        can_execute=True,
                        reasoning="Default VM validation (no specific apps detected)",
                        required_credentials=["ssh"],
                        parameters=self._build_ssh_parameters(available_credentials["ssh"])
                    ))
                    break
        
        summary = ToolSelectionSummary(
            total_tools_available=len(available_tools),
            tools_can_execute=len(selected_tools),
            tools_blocked_by_credentials=0,
            recommendation=f"Using fallback selection. Selected {len(selected_tools)} tools based on detected applications."
        )
        
        logger.info(f"Fallback selection complete: {len(selected_tools)} tools selected")
        
        return selected_tools, summary
    
    def _build_ssh_parameters(self, ssh_creds: Dict[str, Any]) -> Dict[str, Any]:
        """Build SSH parameters from credentials.
        
        Args:
            ssh_creds: SSH credentials dictionary
        
        Returns:
            Parameters dictionary for SSH-based tools
        """
        params = {
            "ssh_host": ssh_creds.get("hostname"),
            "ssh_user": ssh_creds.get("username"),
            "ssh_password": ssh_creds.get("password"),
            "ssh_key_path": ssh_creds.get("ssh_key_path"),
        }
        
        # Only add ssh_port if it's not the default (some tools don't accept it)
        port = ssh_creds.get("ssh_port", 22)
        if port != 22:
            params["ssh_port"] = port
        
        return params


def create_tool_selector() -> LLMToolSelector:
    """Factory function to create LLM tool selector.
    
    Returns:
        LLMToolSelector instance
    """
    return LLMToolSelector()

# Made with Bob
