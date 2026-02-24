#
# Copyright contributors to the agentic-ai-cyberres project
#
"""LLM-powered orchestrator for natural language validation workflows."""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName

logger = logging.getLogger(__name__)


class ValidationIntent(BaseModel):
    """Parsed validation intent from user prompt."""
    hostname: str = Field(description="IP address or hostname of the resource")
    resource_type: str = Field(description="Type of resource: VM, Oracle, MongoDB, or Auto")
    actions: List[str] = Field(description="List of actions to perform: discover, validate, report")
    ssh_username: Optional[str] = Field(default=None, description="SSH username if provided")
    ssh_password: Optional[str] = Field(default=None, description="SSH password if provided")
    specific_apps: List[str] = Field(default_factory=list, description="Specific applications to validate")
    validation_scope: str = Field(default="full", description="Scope: full, quick, or custom")


class LLMOrchestrator:
    """LLM-powered orchestrator that understands natural language validation requests.
    
    Example prompts:
    - "I recovered a VM at 9.11.68.243, discover and validate all applications"
    - "Validate Oracle database on db-server.example.com"
    - "Check MongoDB cluster at 192.168.1.100, user: admin"
    """
    
    def __init__(self, llm_model: Optional[str] = None):
        """Initialize LLM orchestrator.
        
        Args:
            llm_model: LLM model to use (if None, reads from env)
        """
        self.llm_model = llm_model or self._get_llm_model_from_env()
        logger.info(f"LLMOrchestrator using model: {self.llm_model}")
        
        # Create PydanticAI agent for intent parsing
        self.agent = Agent(
            self.llm_model,
            result_type=ValidationIntent,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_llm_model_from_env(self) -> str:
        """Get LLM model configuration from environment."""
        backend = os.getenv("LLM_BACKEND", "ollama").lower()
        
        if backend == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            if not os.getenv("OLLAMA_BASE_URL"):
                os.environ["OLLAMA_BASE_URL"] = base_url
            model = os.getenv("OLLAMA_MODEL", "llama3.2")
            return f"ollama:{model}"
        elif backend == "openai":
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return f"openai:{model}"
        elif backend == "groq":
            model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
            return f"groq:{model}"
        else:
            logger.warning(f"Unknown backend '{backend}', defaulting to ollama:llama3.2")
            return "ollama:llama3.2"
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for intent parsing."""
        return """You are an intelligent validation orchestrator for infrastructure recovery.

Your job is to parse user requests and extract:
1. **hostname**: IP address or hostname (REQUIRED)
2. **resource_type**: VM, Oracle, MongoDB, or Auto (for automatic detection)
3. **actions**: What to do - discover, validate, report (default: all three)
4. **ssh_username**: SSH username if mentioned
5. **ssh_password**: SSH password if mentioned (rarely provided)
6. **specific_apps**: Specific applications mentioned (Oracle, MongoDB, PostgreSQL, etc.)
7. **validation_scope**: full (default), quick, or custom

Examples:

User: "I recovered a VM at 9.11.68.243, discover and validate all applications"
Output: {
  "hostname": "9.11.68.243",
  "resource_type": "Auto",
  "actions": ["discover", "validate"],
  "specific_apps": [],
  "validation_scope": "full"
}

User: "Validate Oracle database on db-server.example.com with user oracleadmin"
Output: {
  "hostname": "db-server.example.com",
  "resource_type": "Oracle",
  "actions": ["validate"],
  "ssh_username": "oracleadmin",
  "specific_apps": ["oracle"],
  "validation_scope": "full"
}

User: "Quick check of MongoDB at 192.168.1.100"
Output: {
  "hostname": "192.168.1.100",
  "resource_type": "MongoDB",
  "actions": ["validate"],
  "specific_apps": ["mongodb"],
  "validation_scope": "quick"
}

Be flexible with natural language variations. Extract all relevant information."""
    
    async def parse_intent(self, user_prompt: str) -> ValidationIntent:
        """Parse user prompt into structured validation intent.
        
        Args:
            user_prompt: Natural language validation request
            
        Returns:
            Parsed validation intent
            
        Raises:
            ValueError: If prompt cannot be parsed or missing required info
        """
        try:
            logger.info(f"Parsing user prompt: {user_prompt}")
            
            # Use PydanticAI agent to parse intent
            result = await self.agent.run(user_prompt)
            # PydanticAI returns the result directly
            intent = result if isinstance(result, ValidationIntent) else ValidationIntent(
                hostname="", resource_type="Auto", actions=["discover", "validate"]
            )
            
            # Validate required fields
            if not intent.hostname:
                raise ValueError("Could not extract hostname/IP from prompt")
            
            # Set defaults
            if not intent.actions:
                intent.actions = ["discover", "validate", "report"]
            
            if not intent.resource_type:
                intent.resource_type = "Auto"
            
            logger.info(f"Parsed intent: {intent.model_dump_json(indent=2)}")
            return intent
            
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            raise ValueError(f"Could not parse validation request: {e}")
    
    async def create_execution_plan(self, intent: ValidationIntent, available_tools: List[str]) -> Dict[str, Any]:
        """Create execution plan based on intent and available MCP tools.
        
        Args:
            intent: Parsed validation intent
            available_tools: List of available MCP tool names
            
        Returns:
            Execution plan with ordered steps
        """
        plan = {
            "hostname": intent.hostname,
            "resource_type": intent.resource_type,
            "steps": []
        }
        
        # Step 1: Discovery (if requested or resource_type is Auto)
        if "discover" in intent.actions or intent.resource_type == "Auto":
            plan["steps"].append({
                "phase": "discovery",
                "tools": [
                    {"name": "discover_os_only", "args": {"hostname": intent.hostname}},
                    {"name": "discover_applications", "args": {"hostname": intent.hostname}}
                ],
                "description": "Discover OS and applications on the server"
            })
        
        # Step 2: Validation
        if "validate" in intent.actions:
            validation_tools = []
            
            # Always validate VM/network basics
            if "check_network_connectivity" in available_tools:
                validation_tools.append({
                    "name": "check_network_connectivity",
                    "args": {"hostname": intent.hostname},
                    "priority": "CRITICAL"
                })
            
            if "validate_vm" in available_tools:
                validation_tools.append({
                    "name": "validate_vm",
                    "args": {"hostname": intent.hostname},
                    "priority": "CRITICAL"
                })
            
            # Add application-specific validations
            if intent.specific_apps:
                for app in intent.specific_apps:
                    app_lower = app.lower()
                    if "oracle" in app_lower and "validate_oracle_db" in available_tools:
                        validation_tools.append({
                            "name": "validate_oracle_db",
                            "args": {"hostname": intent.hostname},
                            "priority": "HIGH"
                        })
                    elif "mongo" in app_lower and "validate_mongodb" in available_tools:
                        validation_tools.append({
                            "name": "validate_mongodb",
                            "args": {"hostname": intent.hostname},
                            "priority": "HIGH"
                        })
                    elif "postgres" in app_lower and "validate_postgresql" in available_tools:
                        validation_tools.append({
                            "name": "validate_postgresql",
                            "args": {"hostname": intent.hostname},
                            "priority": "HIGH"
                        })
            
            plan["steps"].append({
                "phase": "validation",
                "tools": validation_tools,
                "description": f"Validate {intent.resource_type} and applications"
            })
        
        # Step 3: Reporting (if requested)
        if "report" in intent.actions:
            plan["steps"].append({
                "phase": "reporting",
                "tools": [
                    {"name": "generate_report", "args": {"hostname": intent.hostname}}
                ],
                "description": "Generate validation report"
            })
        
        logger.info(f"Created execution plan with {len(plan['steps'])} steps")
        return plan
    
    def explain_plan(self, plan: Dict[str, Any]) -> str:
        """Generate human-readable explanation of execution plan.
        
        Args:
            plan: Execution plan
            
        Returns:
            Human-readable explanation
        """
        lines = [
            f"📋 Validation Plan for {plan['hostname']}",
            f"Resource Type: {plan['resource_type']}",
            "",
            "Steps:"
        ]
        
        for i, step in enumerate(plan['steps'], 1):
            lines.append(f"\n{i}. {step['phase'].upper()}: {step['description']}")
            lines.append(f"   Tools: {len(step['tools'])}")
            for tool in step['tools']:
                priority = tool.get('priority', 'NORMAL')
                lines.append(f"   - {tool['name']} [{priority}]")
        
        return "\n".join(lines)


async def demo_orchestrator():
    """Demo the LLM orchestrator with example prompts."""
    orchestrator = LLMOrchestrator()
    
    # Example prompts
    prompts = [
        "I recovered a VM at 9.11.68.243, discover and validate all applications",
        "Validate Oracle database on db-server.example.com",
        "Quick check of MongoDB at 192.168.1.100 with user admin"
    ]
    
    # Simulate available tools
    available_tools = [
        "discover_os_only",
        "discover_applications",
        "check_network_connectivity",
        "validate_vm",
        "validate_oracle_db",
        "validate_mongodb",
        "validate_postgresql",
        "generate_report"
    ]
    
    for prompt in prompts:
        print(f"\n{'='*80}")
        print(f"User Prompt: {prompt}")
        print(f"{'='*80}")
        
        try:
            # Parse intent
            intent = await orchestrator.parse_intent(prompt)
            print(f"\n✅ Parsed Intent:")
            print(f"   Hostname: {intent.hostname}")
            print(f"   Resource Type: {intent.resource_type}")
            print(f"   Actions: {', '.join(intent.actions)}")
            if intent.ssh_username:
                print(f"   SSH User: {intent.ssh_username}")
            if intent.specific_apps:
                print(f"   Specific Apps: {', '.join(intent.specific_apps)}")
            
            # Create execution plan
            plan = await orchestrator.create_execution_plan(intent, available_tools)
            print(f"\n📋 Execution Plan:")
            print(orchestrator.explain_plan(plan))
            
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_orchestrator())

# Made with Bob
