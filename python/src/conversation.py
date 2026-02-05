#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Interactive conversation handler for gathering resource information."""

import logging
from typing import Optional, Dict, Any
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
from models import (
    ResourceType, 
    VMResourceInfo, 
    OracleDBResourceInfo, 
    MongoDBResourceInfo,
    ConversationState
)

logger = logging.getLogger(__name__)


class ConversationHandler:
    """Handle interactive conversation to gather resource information."""
    
    def __init__(self, llm_model: str = "openai:gpt-4o-mini"):
        """Initialize conversation handler.
        
        Args:
            llm_model: LLM model to use for conversation
        """
        self.llm_model = llm_model
        self.state = ConversationState()
    
    def get_initial_prompt(self) -> str:
        """Get initial prompt to start conversation.
        
        Returns:
            Initial prompt text
        """
        return """Welcome to the Recovery Validation Agent!

I'll help you validate your recovered infrastructure resources (VMs, Oracle databases, or MongoDB clusters).

To get started, please tell me:
1. What type of resource did you recover? (VM, Oracle, or MongoDB)
2. What is the IP address or hostname of the resource?

You can provide this information in natural language, for example:
- "I recovered a VM at 192.168.1.100"
- "I have an Oracle database on db-server.example.com"
- "MongoDB cluster at mongo1.local"
"""
    
    def get_follow_up_questions(self, resource_type: ResourceType) -> list[str]:
        """Get follow-up questions based on resource type.
        
        Args:
            resource_type: Type of resource
        
        Returns:
            List of follow-up questions
        """
        if resource_type == ResourceType.VM:
            return [
                "What is the SSH username for this VM?",
                "Do you have an SSH password or key file? (I can also check environment variables)",
                "Are there any specific services that must be running? (optional)"
            ]
        elif resource_type == ResourceType.ORACLE:
            return [
                "What is the Oracle database username?",
                "What is the database password?",
                "What is the service name or SID?",
                "Do you have SSH access to the server? (optional, for auto-discovery)"
            ]
        elif resource_type == ResourceType.MONGODB:
            return [
                "What is the MongoDB port? (default: 27017)",
                "Do you have MongoDB credentials? (username/password)",
                "Do you have SSH access to the server?",
                "Should I validate a specific collection? (optional)"
            ]
        return []
    
    async def parse_initial_input(self, user_input: str) -> Dict[str, Any]:
        """Parse initial user input to extract resource type and host.
        
        Args:
            user_input: User's input text
        
        Returns:
            Dictionary with parsed information
        """
        # Create a simple agent to extract structured data
        system_prompt = """You are a helpful assistant that extracts structured information from user input.
        
Extract the following information:
- resource_type: One of "vm", "oracle", or "mongodb"
- host: IP address or hostname

Return the information as a JSON object with these fields.
If you cannot determine the resource type or host, set them to null.
"""
        
        agent = Agent(
            self.llm_model,
            system_prompt=system_prompt,
            retries=2
        )
        
        try:
            result = await agent.run(user_input)
            parsed = result.data
            
            # Validate and normalize
            if isinstance(parsed, dict):
                resource_type_str = parsed.get("resource_type", "").lower()
                if resource_type_str in ["vm", "linux", "server"]:
                    parsed["resource_type"] = ResourceType.VM
                elif resource_type_str in ["oracle", "oracle db", "oracledb"]:
                    parsed["resource_type"] = ResourceType.ORACLE
                elif resource_type_str in ["mongodb", "mongo", "mongo db"]:
                    parsed["resource_type"] = ResourceType.MONGODB
                else:
                    parsed["resource_type"] = None
                
                return parsed
            
            return {"resource_type": None, "host": None}
            
        except Exception as e:
            logger.error(f"Error parsing initial input: {e}")
            return {"resource_type": None, "host": None}
    
    async def parse_credentials(
        self,
        user_input: str,
        resource_type: ResourceType
    ) -> Dict[str, Any]:
        """Parse credential information from user input.
        
        Args:
            user_input: User's input text
            resource_type: Type of resource
        
        Returns:
            Dictionary with credential information
        """
        if resource_type == ResourceType.VM:
            system_prompt = """Extract SSH credentials from the user input.
            
Look for:
- ssh_user: SSH username
- ssh_password: SSH password (if mentioned)
- ssh_key_path: Path to SSH private key file (if mentioned)

Return as JSON. Set fields to null if not mentioned.
"""
        elif resource_type == ResourceType.ORACLE:
            system_prompt = """Extract Oracle database credentials from the user input.
            
Look for:
- db_user: Database username
- db_password: Database password
- service_name: Oracle service name or SID
- ssh_user: SSH username (if mentioned)
- ssh_password: SSH password (if mentioned)

Return as JSON. Set fields to null if not mentioned.
"""
        elif resource_type == ResourceType.MONGODB:
            system_prompt = """Extract MongoDB credentials from the user input.
            
Look for:
- mongo_user: MongoDB username (if mentioned)
- mongo_password: MongoDB password (if mentioned)
- port: MongoDB port number (default 27017)
- ssh_user: SSH username (if mentioned)
- database_name: Database to validate (if mentioned)
- collection_name: Collection to validate (if mentioned)

Return as JSON. Set fields to null if not mentioned.
"""
        else:
            return {}
        
        agent = Agent(
            self.llm_model,
            system_prompt=system_prompt,
            retries=2
        )
        
        try:
            result = await agent.run(user_input)
            return result.data if isinstance(result.data, dict) else {}
        except Exception as e:
            logger.error(f"Error parsing credentials: {e}")
            return {}
    
    def build_resource_info(
        self,
        resource_type: ResourceType,
        collected_info: Dict[str, Any]
    ) -> VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo:
        """Build resource info object from collected information.
        
        Args:
            resource_type: Type of resource
            collected_info: Collected information dictionary
        
        Returns:
            Resource info object
        
        Raises:
            ValueError: If required information is missing
        """
        if resource_type == ResourceType.VM:
            return VMResourceInfo(
                host=collected_info["host"],
                ssh_user=collected_info.get("ssh_user"),
                ssh_password=collected_info.get("ssh_password"),
                ssh_key_path=collected_info.get("ssh_key_path"),
                ssh_port=collected_info.get("ssh_port", 22),
                required_services=collected_info.get("required_services", []),
                description=collected_info.get("description")
            )
        elif resource_type == ResourceType.ORACLE:
            return OracleDBResourceInfo(
                host=collected_info["host"],
                port=collected_info.get("port", 1521),
                service_name=collected_info.get("service_name"),
                dsn=collected_info.get("dsn"),
                db_user=collected_info.get("db_user"),
                db_password=collected_info.get("db_password"),
                ssh_user=collected_info.get("ssh_user"),
                ssh_password=collected_info.get("ssh_password"),
                ssh_key_path=collected_info.get("ssh_key_path"),
                description=collected_info.get("description")
            )
        elif resource_type == ResourceType.MONGODB:
            return MongoDBResourceInfo(
                host=collected_info["host"],
                port=collected_info.get("port", 27017),
                uri=collected_info.get("uri"),
                mongo_user=collected_info.get("mongo_user"),
                mongo_password=collected_info.get("mongo_password"),
                auth_db=collected_info.get("auth_db", "admin"),
                ssh_user=collected_info.get("ssh_user"),
                ssh_password=collected_info.get("ssh_password"),
                ssh_key_path=collected_info.get("ssh_key_path"),
                database_name=collected_info.get("database_name"),
                collection_name=collected_info.get("collection_name"),
                validate_replica_set=collected_info.get("validate_replica_set", True),
                description=collected_info.get("description")
            )
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def get_missing_fields(
        self,
        resource_type: ResourceType,
        collected_info: Dict[str, Any]
    ) -> list[str]:
        """Get list of missing required fields.
        
        Args:
            resource_type: Type of resource
            collected_info: Collected information
        
        Returns:
            List of missing field names
        """
        missing = []
        
        if not collected_info.get("host"):
            missing.append("host")
        
        if resource_type == ResourceType.VM:
            if not collected_info.get("ssh_user"):
                missing.append("ssh_user")
            if not collected_info.get("ssh_password") and not collected_info.get("ssh_key_path"):
                missing.append("ssh_password or ssh_key_path")
        
        elif resource_type == ResourceType.ORACLE:
            if not collected_info.get("db_user"):
                missing.append("db_user")
            if not collected_info.get("db_password"):
                missing.append("db_password")
            if not collected_info.get("service_name") and not collected_info.get("dsn"):
                missing.append("service_name or dsn")
        
        elif resource_type == ResourceType.MONGODB:
            # MongoDB can work without credentials for local connections
            pass
        
        return missing
    
    def format_missing_fields_message(self, missing_fields: list[str]) -> str:
        """Format a message about missing fields.
        
        Args:
            missing_fields: List of missing field names
        
        Returns:
            Formatted message
        """
        if not missing_fields:
            return ""
        
        return f"I still need the following information:\n" + "\n".join(
            f"- {field}" for field in missing_fields
        )

# Made with Bob
