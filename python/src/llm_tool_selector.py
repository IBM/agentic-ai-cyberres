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
    required_credentials: List[str]
    missing_credentials: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None


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
        return f"""You are an intelligent tool selector for infrastructure validation.

Your task: Select the most appropriate validation tools based on available context.

Context:
{json.dumps(context, indent=2)}

Instructions:
1. Analyze each available tool's capabilities and requirements
2. Match tools to discovered applications
3. Check if required credentials are available
4. Prioritize tools that can execute with available credentials
5. Provide clear reasoning for each selection
6. Explain why tools cannot execute if credentials are missing

Priority Guidelines:
- CRITICAL: Discovery and core validation tools (especially SSH-based discovery)
- HIGH: Infrastructure and connectivity validation
- MEDIUM: Deep validation requiring app credentials
- LOW: Optional/nice-to-have validations

Credential Awareness:
- SSH-based tools (like *_discover_and_validate) only need SSH credentials
- Direct-access tools (like *_connect, *_query) need application credentials
- Prefer SSH-based tools when app credentials are unavailable

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
        
        # Select SSH-based discovery tools
        for tool in available_tools:
            tool_name = tool["name"]
            tool_lower = tool_name.lower()
            
            # Prioritize discover_and_validate tools
            if "discover" in tool_lower and "validate" in tool_lower and has_ssh:
                selected_tools.append(ToolSelectionResult(
                    tool_name=tool_name,
                    priority="CRITICAL",
                    can_execute=True,
                    reasoning="SSH-based discovery tool (fallback selection)",
                    required_credentials=["ssh"],
                    parameters=self._build_ssh_parameters(available_credentials["ssh"])
                ))
            
            # Add VM tools
            elif any(p in tool_lower for p in ["vm_", "ping", "ssh"]) and has_ssh:
                selected_tools.append(ToolSelectionResult(
                    tool_name=tool_name,
                    priority="HIGH",
                    can_execute=True,
                    reasoning="Infrastructure validation tool (fallback selection)",
                    required_credentials=["ssh"],
                    parameters=self._build_ssh_parameters(available_credentials["ssh"])
                ))
        
        summary = ToolSelectionSummary(
            total_tools_available=len(available_tools),
            tools_can_execute=len(selected_tools),
            tools_blocked_by_credentials=0,
            recommendation="Using fallback selection. LLM unavailable."
        )
        
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
