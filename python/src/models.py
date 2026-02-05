#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Pydantic models for recovery validation agent."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class ResourceType(str, Enum):
    """Supported resource types for validation."""
    VM = "vm"
    ORACLE = "oracle"
    MONGODB = "mongodb"


class CredentialSource(str, Enum):
    """Source of credentials."""
    ENV = "env"
    USER_PROVIDED = "user_provided"
    AUTO_DISCOVERED = "auto_discovered"


class ValidationStatus(str, Enum):
    """Validation status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


# Base Models
class BaseResourceInfo(BaseModel):
    """Base resource information."""
    resource_type: ResourceType
    host: str = Field(..., description="IP address or hostname")
    description: Optional[str] = Field(None, description="User-provided description")
    
    @field_validator('host')
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v.strip()


class VMResourceInfo(BaseResourceInfo):
    """VM-specific resource information."""
    resource_type: ResourceType = Field(default=ResourceType.VM, frozen=True)
    ssh_user: str = Field(..., description="SSH username")
    ssh_password: Optional[str] = Field(None, description="SSH password")
    ssh_key_path: Optional[str] = Field(None, description="Path to SSH private key")
    ssh_port: int = Field(22, description="SSH port")
    required_services: List[str] = Field(default_factory=list, description="Required systemd services")
    
    @field_validator('ssh_password', 'ssh_key_path')
    @classmethod
    def validate_auth(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure at least one authentication method is provided."""
        values = info.data
        if 'ssh_password' in values and 'ssh_key_path' in values:
            if not values.get('ssh_password') and not values.get('ssh_key_path'):
                raise ValueError("Either ssh_password or ssh_key_path must be provided")
        return v


class OracleDBResourceInfo(BaseResourceInfo):
    """Oracle database resource information."""
    resource_type: ResourceType = Field(default=ResourceType.ORACLE, frozen=True)
    
    # Connection options
    dsn: Optional[str] = Field(None, description="Oracle DSN string")
    port: int = Field(1521, description="Oracle listener port")
    service_name: Optional[str] = Field(None, description="Oracle service name")
    
    # Database credentials
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    
    # SSH for discovery
    ssh_user: Optional[str] = Field(None, description="SSH username for discovery")
    ssh_password: Optional[str] = Field(None, description="SSH password")
    ssh_key_path: Optional[str] = Field(None, description="Path to SSH private key")
    
    @field_validator('dsn', 'service_name')
    @classmethod
    def validate_connection(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure either DSN or service_name is provided."""
        values = info.data
        if 'dsn' in values and 'service_name' in values:
            if not values.get('dsn') and not values.get('service_name'):
                raise ValueError("Either dsn or service_name must be provided")
        return v


class MongoDBResourceInfo(BaseResourceInfo):
    """MongoDB resource information."""
    resource_type: ResourceType = Field(default=ResourceType.MONGODB, frozen=True)
    
    # Connection options
    uri: Optional[str] = Field(None, description="MongoDB connection URI")
    port: int = Field(27017, description="MongoDB port")
    
    # Database credentials
    mongo_user: Optional[str] = Field(None, description="MongoDB username")
    mongo_password: Optional[str] = Field(None, description="MongoDB password")
    auth_db: str = Field("admin", description="Authentication database")
    
    # SSH for local access
    ssh_user: Optional[str] = Field(None, description="SSH username")
    ssh_password: Optional[str] = Field(None, description="SSH password")
    ssh_key_path: Optional[str] = Field(None, description="Path to SSH private key")
    
    # Validation options
    database_name: Optional[str] = Field(None, description="Database to validate")
    collection_name: Optional[str] = Field(None, description="Collection to validate")
    validate_replica_set: bool = Field(True, description="Validate replica set status")


class ValidationRequest(BaseModel):
    """Complete validation request."""
    resource_info: VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo = Field(
        ..., discriminator='resource_type'
    )
    credential_source: CredentialSource = Field(
        CredentialSource.USER_PROVIDED,
        description="Source of credentials"
    )
    auto_discover: bool = Field(True, description="Enable auto-discovery")
    send_email: bool = Field(True, description="Send email report")
    email_recipient: Optional[str] = Field(None, description="Email recipient")
    custom_acceptance_criteria: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom acceptance criteria overrides"
    )


# Validation Result Models
class CheckResult(BaseModel):
    """Individual check result."""
    check_id: str = Field(..., description="Unique check identifier")
    check_name: str = Field(..., description="Human-readable check name")
    status: ValidationStatus
    expected: Optional[str] = Field(None, description="Expected value/condition")
    actual: Optional[str] = Field(None, description="Actual value/condition")
    message: Optional[str] = Field(None, description="Result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResourceValidationResult(BaseModel):
    """Validation results for a resource."""
    resource_type: ResourceType
    resource_host: str
    overall_status: ValidationStatus
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    checks: List[CheckResult] = Field(default_factory=list)
    discovery_info: Optional[Dict[str, Any]] = Field(None, description="Auto-discovered information")
    execution_time_seconds: float = Field(..., description="Total execution time")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def passed_checks(self) -> int:
        """Count of passed checks."""
        return sum(1 for c in self.checks if c.status == ValidationStatus.PASS)
    
    @property
    def failed_checks(self) -> int:
        """Count of failed checks."""
        return sum(1 for c in self.checks if c.status == ValidationStatus.FAIL)
    
    @property
    def warning_checks(self) -> int:
        """Count of warning checks."""
        return sum(1 for c in self.checks if c.status == ValidationStatus.WARNING)


class ValidationReport(BaseModel):
    """Complete validation report."""
    request: ValidationRequest
    result: ResourceValidationResult
    recommendations: List[str] = Field(default_factory=list)
    report_generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_summary(self) -> str:
        """Generate a text summary."""
        lines = [
            f"Validation Report - {self.result.resource_type.value.upper()}",
            f"Host: {self.result.resource_host}",
            f"Status: {self.result.overall_status.value}",
            f"Score: {self.result.score}/100",
            f"Checks: {self.result.passed_checks} passed, {self.result.failed_checks} failed, {self.result.warning_checks} warnings",
            f"Execution Time: {self.result.execution_time_seconds:.2f}s",
        ]
        
        if self.result.failed_checks > 0:
            lines.append("\nFailed Checks:")
            for check in self.result.checks:
                if check.status == ValidationStatus.FAIL:
                    lines.append(f"  - {check.check_name}: {check.message}")
        
        if self.recommendations:
            lines.append("\nRecommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")
        
        return "\n".join(lines)


# Conversation State Models
class ConversationState(BaseModel):
    """Track conversation state during information gathering."""
    resource_type: Optional[ResourceType] = None
    collected_info: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    current_question: Optional[str] = None
    completed: bool = False

# Made with Bob
