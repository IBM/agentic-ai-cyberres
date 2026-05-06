"""
Pydantic models for structured LLM planning output.

This module defines the schema for validation plan generation using
structured output (JSON mode) instead of ReActAgent format.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class CheckType(str, Enum):
    """Types of validation checks."""
    NETWORK = "network"
    DATABASE = "database"
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"


class ValidationCheckSchema(BaseModel):
    """Schema for a single validation check in the plan."""
    
    check_id: str = Field(
        ...,
        description="Unique identifier for the check (e.g., 'db_001', 'net_001')",
        pattern=r"^[a-z]+_\d{3}$"
    )
    
    check_name: str = Field(
        ...,
        description="Human-readable name for the check",
        min_length=5,
        max_length=100
    )
    
    check_type: CheckType = Field(
        ...,
        description="Type of check being performed"
    )
    
    priority: int = Field(
        ...,
        description="Priority level (1=critical, 2=high, 3=medium, 4-5=low)",
        ge=1,
        le=5
    )
    
    description: str = Field(
        ...,
        description="Detailed description of what this check validates",
        min_length=10,
        max_length=500
    )
    
    mcp_tool: str = Field(
        ...,
        description="Exact name of the MCP tool to use for this check",
        min_length=3
    )
    
    tool_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the MCP tool (credentials will be injected automatically)"
    )
    
    expected_result: str = Field(
        ...,
        description="What a successful check result should look like",
        min_length=5,
        max_length=200
    )
    
    failure_impact: str = Field(
        ...,
        description="Impact if this check fails",
        min_length=10,
        max_length=300
    )
    
    @validator('tool_args')
    def validate_no_credentials(cls, v):
        """Ensure no credentials are included in tool_args."""
        # Forbidden keys - actual sensitive data
        forbidden_keys = {'password', 'secret', 'token', 'key_path', 'ssh_key', 'private_key'}
        # Allowed keys - non-sensitive references
        allowed_keys = {'credential_id', 'host', 'port', 'ports', 'database', 'database_name',
                       'collection', 'command', 'timeout', 'service_name'}
        
        for key in v.keys():
            key_lower = key.lower()
            # Skip if it's an allowed key
            if key_lower in allowed_keys or key in allowed_keys:
                continue
            # Check if it matches any forbidden pattern
            if any(forbidden in key_lower for forbidden in forbidden_keys):
                raise ValueError(f"Credentials not allowed in tool_args: {key}")
            # Also check for standalone credential field names
            if key_lower in {'user', 'username', 'ssh_user', 'db_user', 'mongo_user', 'passwd'}:
                raise ValueError(f"Credentials not allowed in tool_args: {key}")
        return v


class ValidationPlanSchema(BaseModel):
    """Schema for the complete validation plan output."""
    
    reasoning: str = Field(
        ...,
        description="Explanation of the validation strategy and why these checks were selected",
        min_length=50,
        max_length=1000
    )
    
    checks: List[ValidationCheckSchema] = Field(
        ...,
        description="List of validation checks to perform",
        min_items=1,
        max_items=20
    )
    
    confidence: float = Field(
        default=0.8,
        description="Confidence in the plan quality (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    strategy: str = Field(
        default="llm_structured",
        description="Planning strategy used"
    )
    
    @validator('checks')
    def validate_check_ids_unique(cls, v):
        """Ensure all check IDs are unique."""
        check_ids = [check.check_id for check in v]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("Duplicate check IDs found")
        return v
    
    @validator('checks')
    def validate_priority_distribution(cls, v):
        """Ensure at least one critical (priority 1) check."""
        priorities = [check.priority for check in v]
        if 1 not in priorities:
            raise ValueError("Plan must include at least one critical (priority 1) check")
        return v


class PlanningContext(BaseModel):
    """Context information for planning."""
    
    host: str = Field(..., description="Target host")
    resource_type: str = Field(..., description="Type of resource")
    category: str = Field(..., description="Resource category")
    primary_application: Optional[str] = Field(None, description="Primary application detected")
    secondary_applications: List[str] = Field(default_factory=list, description="Secondary applications")
    available_tools: List[str] = Field(..., description="Available MCP tool names")
    
    class Config:
        """Pydantic config."""
        use_enum_values = True


# Example for documentation
EXAMPLE_PLAN = {
    "reasoning": "For a MongoDB database server, we need to verify connectivity, replica set health, and data integrity. Priority 1 checks ensure the database is accessible and operational. Priority 2 checks validate data integrity and configuration.",
    "checks": [
        {
            "check_id": "net_001",
            "check_name": "Network Connectivity",
            "check_type": "network",
            "priority": 1,
            "description": "Verify network connectivity to the MongoDB server on port 27017",
            "mcp_tool": "tcp_portcheck",
            "tool_args": {"port": 27017},
            "expected_result": "Port 27017 is open and accepting connections",
            "failure_impact": "Cannot connect to database - all subsequent checks will fail"
        },
        {
            "check_id": "db_001",
            "check_name": "MongoDB Ping",
            "check_type": "database",
            "priority": 1,
            "description": "Verify MongoDB is responding to ping commands",
            "mcp_tool": "db_mongo_ssh_ping",
            "tool_args": {},
            "expected_result": "MongoDB responds with version and status",
            "failure_impact": "Database is not operational"
        },
        {
            "check_id": "db_002",
            "check_name": "Replica Set Status",
            "check_type": "database",
            "priority": 2,
            "description": "Check MongoDB replica set configuration and member health",
            "mcp_tool": "db_mongo_ssh_rs_status",
            "tool_args": {},
            "expected_result": "All replica set members are healthy and in sync",
            "failure_impact": "Replica set may not be properly configured for high availability"
        }
    ],
    "confidence": 0.9,
    "strategy": "llm_structured"
}

# Made with Bob
