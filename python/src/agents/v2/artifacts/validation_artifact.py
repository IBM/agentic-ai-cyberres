"""
Validation Artifact Schema

This module defines the artifact schema produced by the Validation Agent.
It represents the validation plan and execution results.

The ValidationArtifact is used for:
- Agent-to-agent communication (Validation → Evaluation)
- Type-safe validation plan representation
- Execution tracking and results
- Historical auditing
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    """Individual validation check definition."""
    
    check_id: str = Field(description="Unique check identifier")
    check_name: str = Field(description="Human-readable check name")
    tool_name: str = Field(description="MCP tool to execute")
    parameters: Dict[str, Any] = Field(description="Tool parameters")
    expected_outcome: str = Field(description="What success looks like")
    reasoning: str = Field(description="Why this check is needed")
    priority: str = Field(default="medium", description="Priority: high, medium, low")
    
    # Execution results (populated after execution)
    executed: bool = Field(default=False, description="Whether check was executed")
    passed: bool = Field(default=False, description="Whether check passed")
    result: Optional[str] = Field(default=None, description="Execution result")
    error: Optional[str] = Field(default=None, description="Error if failed")
    execution_time_seconds: float = Field(default=0.0, description="Execution time")


class ValidationArtifact(BaseModel):
    """
    Artifact produced by Validation Agent.
    
    This artifact contains the validation plan created by the Validation Agent
    and the results of executing that plan.
    
    It serves as input for the Evaluation Agent, enabling assessment of
    validation quality and completeness.
    
    Attributes:
        discovery_artifact_id: Reference to discovery artifact used
        resource_id: Resource being validated
        resource_type: Type of resource
        validation_checks: List of validation checks to perform
        validation_strategy: Strategy used (comprehensive, targeted, minimal)
        checks_executed: Number of checks executed
        checks_passed: Number of checks that passed
        checks_failed: Number of checks that failed
        checks_skipped: Number of checks skipped
        validation_timestamp: When validation was performed
        execution_time_seconds: Total execution time
        planning_reasoning: LLM reasoning for validation plan
        execution_summary: Summary of validation execution
        plan_quality: Quality of the plan (high, medium, low)
        coverage_percentage: Percentage of resource covered by validation
        errors: Any errors encountered
    
    Example:
        >>> artifact = ValidationArtifact(
        ...     discovery_artifact_id="discovery:v1",
        ...     resource_id="vm-prod-web-01",
        ...     resource_type="vm",
        ...     validation_checks=[
        ...         ValidationCheck(
        ...             check_id="check_001",
        ...             check_name="Verify nginx service",
        ...             tool_name="check_service_status",
        ...             parameters={"service": "nginx"},
        ...             expected_outcome="Service is running",
        ...             reasoning="Nginx was detected in discovery"
        ...         )
        ...     ],
        ...     validation_strategy="comprehensive",
        ...     planning_reasoning="Created comprehensive plan...",
        ...     plan_quality="high",
        ...     coverage_percentage=95.0
        ... )
    """
    
    # Reference to discovery
    discovery_artifact_id: str = Field(
        description="ID of discovery artifact used for planning"
    )
    
    # Resource identification
    resource_id: str = Field(description="Resource being validated")
    resource_type: str = Field(description="Type: vm, oracle_db, mongo_db")
    
    # Validation plan
    validation_checks: List[ValidationCheck] = Field(
        description="Ordered list of validation checks"
    )
    validation_strategy: str = Field(
        description="Strategy: comprehensive, targeted, minimal, custom"
    )
    
    # Execution results
    checks_executed: int = Field(default=0, description="Number of checks executed")
    checks_passed: int = Field(default=0, description="Number of checks passed")
    checks_failed: int = Field(default=0, description="Number of checks failed")
    checks_skipped: int = Field(default=0, description="Number of checks skipped")
    
    # Metadata
    validation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When validation was performed"
    )
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time"
    )
    
    # Reasoning and quality
    planning_reasoning: str = Field(
        description="LLM reasoning for why this validation plan was chosen"
    )
    execution_summary: str = Field(
        default="",
        description="Summary of validation execution and results"
    )
    plan_quality: str = Field(
        description="Quality of the plan: high, medium, low"
    )
    coverage_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of resource covered by validation checks"
    )
    
    # Error tracking
    errors: List[str] = Field(
        default_factory=list,
        description="Any errors encountered during planning or execution"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "discovery_artifact_id": "discovery:v1",
                "resource_id": "vm-prod-web-01",
                "resource_type": "vm",
                "validation_checks": [
                    {
                        "check_id": "check_001",
                        "check_name": "Verify nginx service status",
                        "tool_name": "check_service_status",
                        "parameters": {"service": "nginx"},
                        "expected_outcome": "Service is running and healthy",
                        "reasoning": "Nginx was detected in discovery with high confidence",
                        "priority": "high",
                        "executed": True,
                        "passed": True,
                        "result": "nginx is active (running)",
                        "execution_time_seconds": 1.2
                    },
                    {
                        "check_id": "check_002",
                        "check_name": "Verify port 80 accessibility",
                        "tool_name": "check_port_connectivity",
                        "parameters": {"port": 80, "protocol": "tcp"},
                        "expected_outcome": "Port is accessible",
                        "reasoning": "Port 80 was found open in discovery",
                        "priority": "high",
                        "executed": True,
                        "passed": True,
                        "result": "Port 80 is accessible",
                        "execution_time_seconds": 0.5
                    }
                ],
                "validation_strategy": "comprehensive",
                "checks_executed": 2,
                "checks_passed": 2,
                "checks_failed": 0,
                "checks_skipped": 0,
                "validation_timestamp": "2026-03-17T18:05:00Z",
                "execution_time_seconds": 1.7,
                "planning_reasoning": "Created comprehensive validation plan based on discovery findings. Prioritized service and connectivity checks for detected nginx application.",
                "execution_summary": "All validation checks passed successfully. Resource is functioning as expected.",
                "plan_quality": "high",
                "coverage_percentage": 95.0,
                "errors": []
            }
        }
    
    def get_success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.checks_executed == 0:
            return 0.0
        return (self.checks_passed / self.checks_executed) * 100.0
    
    def get_failed_checks(self) -> List[ValidationCheck]:
        """Get list of failed checks."""
        return [check for check in self.validation_checks if check.executed and not check.passed]
    
    def get_high_priority_checks(self) -> List[ValidationCheck]:
        """Get high priority checks."""
        return [check for check in self.validation_checks if check.priority == "high"]
    
    def has_errors(self) -> bool:
        """Check if any errors were encountered."""
        return len(self.errors) > 0
    
    def is_complete(self) -> bool:
        """Check if all checks were executed."""
        return self.checks_executed == len(self.validation_checks)
    
    def is_successful(self) -> bool:
        """Check if validation was successful (all checks passed)."""
        return (
            self.checks_executed > 0 and
            self.checks_passed == self.checks_executed and
            self.checks_failed == 0
        )

# Made with Bob
