#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Simplified conversation handler - only asks for hostname + SSH credentials."""

import os
import logging
from typing import Optional, Dict, Any
from pydantic_ai import Agent
from models import ConversationState

logger = logging.getLogger(__name__)


def get_llm_model_from_env() -> str:
    """Get LLM model configuration from environment variables.
    
    Returns:
        Model string in format "backend:model"
    """
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    
    if backend == "ollama":
        # Pydantic AI requires OLLAMA_BASE_URL to be set
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
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
    elif backend == "azure":
        model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")
        return f"azure:{model}"
    elif backend == "vertexai":
        model = os.getenv("VERTEXAI_MODEL", "gemini-1.5-flash-001")
        return f"vertexai:{model}"
    else:
        logger.warning(f"Unknown LLM backend '{backend}', defaulting to ollama:llama3.2")
        return "ollama:llama3.2"


class SimpleConversationHandler:
    """Simplified conversation handler following MCP best practices.
    
    Only asks for:
    1. Hostname/IP
    2. SSH username
    3. SSH password (or key path)
    
    Everything else is discovered automatically using MCP tools.
    """
    
    def __init__(self, llm_model: Optional[str] = None):
        """Initialize conversation handler.
        
        Args:
            llm_model: LLM model to use (if None, reads from env)
        """
        self.llm_model = llm_model or get_llm_model_from_env()
        logger.info(f"SimpleConversationHandler using LLM model: {self.llm_model}")
        self.state = ConversationState()
    
    def get_initial_prompt(self) -> str:
        """Get initial prompt to start conversation.
        
        Returns:
            Initial prompt text
        """
        return """Welcome to the Recovery Validation Agent! 🔍

I'll help you validate your recovered infrastructure by automatically discovering 
and validating all resources on your server.

To get started, I just need three pieces of information:
1. **Hostname or IP address** of the server
2. **SSH username** to connect
3. **SSH password** (or press Enter to use SSH key)

I'll then automatically:
- Detect the operating system
- Discover all running applications (Oracle, MongoDB, web servers, etc.)
- Validate each discovered resource
- Generate a comprehensive report

Please provide the server details:"""
    
    async def parse_minimal_input(self, user_input: str) -> Dict[str, Any]:
        """Parse user input to extract hostname and SSH credentials.
        
        Args:
            user_input: User's input text
        
        Returns:
            Dictionary with hostname, ssh_user, ssh_password/ssh_key
        """
        system_prompt = """You are a helpful assistant that extracts SSH connection information.

Extract the following from the user's input:
- hostname: IP address or hostname (required)
- ssh_user: SSH username (required)
- ssh_password: SSH password (optional, may be empty if using key)
- ssh_key: Path to SSH key file (optional)

Return as JSON with these exact field names. If a field is not provided, set it to null.

Examples:
- "Connect to 192.168.1.100 as admin with password secret123"
  → {"hostname": "192.168.1.100", "ssh_user": "admin", "ssh_password": "secret123", "ssh_key": null}
  
- "Server db-server.local, user oracle, key /home/user/.ssh/id_rsa"
  → {"hostname": "db-server.local", "ssh_user": "oracle", "ssh_password": null, "ssh_key": "/home/user/.ssh/id_rsa"}
  
- "192.168.1.50 username: root password: admin123"
  → {"hostname": "192.168.1.50", "ssh_user": "root", "ssh_password": "admin123", "ssh_key": null}
"""
        
        agent = Agent(
            self.llm_model,
            system_prompt=system_prompt,
            retries=2
        )
        
        try:
            result = await agent.run(user_input)
            parsed = result.data
            
            if isinstance(parsed, dict):
                return parsed
            
            return {"hostname": None, "ssh_user": None, "ssh_password": None, "ssh_key": None}
            
        except Exception as e:
            logger.error(f"Error parsing input: {e}")
            return {"hostname": None, "ssh_user": None, "ssh_password": None, "ssh_key": None}
    
    def validate_credentials(self, creds: Dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate that required credentials are present.
        
        Args:
            creds: Credentials dictionary
        
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        missing = []
        
        if not creds.get("hostname"):
            missing.append("hostname/IP address")
        
        if not creds.get("ssh_user"):
            missing.append("SSH username")
        
        # Either password or key must be provided
        if not creds.get("ssh_password") and not creds.get("ssh_key"):
            missing.append("SSH password or key path")
        
        return (len(missing) == 0, missing)
    
    def format_missing_fields_message(self, missing: list[str]) -> str:
        """Format a message about missing fields.
        
        Args:
            missing: List of missing field names
        
        Returns:
            Formatted message
        """
        if not missing:
            return ""
        
        return f"I still need the following information:\n" + "\n".join(f"- {field}" for field in missing)
    
    def build_ssh_credentials(self, creds: Dict[str, Any]) -> Dict[str, str]:
        """Build SSH credentials dictionary for MCP tools.
        
        Args:
            creds: Raw credentials from user
        
        Returns:
            Formatted credentials for MCP tools
        """
        result = {
            "hostname": creds["hostname"],
            "username": creds["ssh_user"]
        }
        
        if creds.get("ssh_password"):
            result["password"] = creds["ssh_password"]
        elif creds.get("ssh_key"):
            result["key_path"] = creds["ssh_key"]
        
        return result


# Convenience function for backward compatibility
def create_simple_conversation_handler(llm_model: Optional[str] = None) -> SimpleConversationHandler:
    """Create a simple conversation handler instance.
    
    Args:
        llm_model: Optional LLM model override
    
    Returns:
        SimpleConversationHandler instance
    """
    return SimpleConversationHandler(llm_model)

# Made with Bob
