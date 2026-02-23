#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Validation agent for creating validation plans using Pydantic AI."""

import logging
from typing import Optional, List
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from models import (
    ResourceClassification,
    ValidationStrategy,
    ResourceCategory,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo
)
from agents.base import AgentConfig

logger = logging.getLogger(__name__)

# Type alias for resource info
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo


class ValidationCheck(BaseModel):
    """Individual validation check."""
    check_id: str = Field(..., description="Unique check identifier")
    check_name: str = Field(..., description="Human-readable check name")
    check_type: str = Field(..., description="Type of check (network, database, system, etc.)")
    priority: int = Field(..., ge=1, le=5, description="Priority (1=highest, 5=lowest)")
    description: str = Field(..., description="What this check validates")
    mcp_tool: str = Field(..., description="MCP tool to use for this check")
    tool_args: dict = Field(default_factory=dict, description="Arguments for the MCP tool")
    expected_result: str = Field(..., description="Expected result description")
    failure_impact: str = Field(..., description="Impact if check fails")


class ValidationPlan(BaseModel):
    """Complete validation plan."""
    strategy_name: str = Field(..., description="Name of the validation strategy")
    resource_category: ResourceCategory = Field(..., description="Resource category")
    checks: List[ValidationCheck] = Field(..., description="List of validation checks")
    estimated_duration_seconds: int = Field(..., description="Estimated execution time")
    reasoning: str = Field(..., description="Reasoning for this validation plan")
    
    def get_priority_checks(self, max_priority: int = 2) -> List[ValidationCheck]:
        """Get high-priority checks."""
        return [c for c in self.checks if c.priority <= max_priority]
    
    def get_checks_by_type(self, check_type: str) -> List[ValidationCheck]:
        """Get checks by type."""
        return [c for c in self.checks if c.check_type == check_type]


class ValidationAgent:
    """Agent for creating intelligent validation plans."""
    
    SYSTEM_PROMPT = """You are a validation planning expert. Your role is to:
1. Analyze the resource classification and discovered applications
2. Create a comprehensive validation plan with appropriate checks
3. Prioritize checks based on criticality and resource type
4. Select the right MCP tools for each validation

You have access to these MCP tool categories:
- Network tools: tcp_portcheck
- VM tools: vm_linux_uptime_load_mem, vm_linux_fs_usage, vm_linux_services
- Oracle DB tools: db_oracle_connect, db_oracle_tablespaces, db_oracle_discover_and_validate
- MongoDB tools: db_mongo_connect, db_mongo_rs_status, db_mongo_ssh_ping, validate_collection
- Workload discovery tools: workload_scan_ports, workload_scan_processes, workload_detect_applications

Create validation plans that are:
- Comprehensive: Cover all critical aspects
- Prioritized: Most important checks first
- Efficient: Avoid redundant checks
- Actionable: Clear expected results and failure impacts"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize validation agent.
        
        Args:
            config: Agent configuration (uses defaults if not provided)
        """
        self.config = config or AgentConfig()
        
        # Create planning agent
        self.planning_agent = self.config.create_agent(
            result_type=ValidationPlan,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        logger.info("Validation agent initialized")
    
    async def create_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> ValidationPlan:
        """Create validation plan based on resource classification.
        
        Args:
            resource: Resource information
            classification: Resource classification from discovery
        
        Returns:
            ValidationPlan with checks and strategy
        """
        logger.info(
            f"Creating validation plan for {resource.host} "
            f"(category: {classification.category.value})"
        )
        
        # Build context for the agent
        prompt = self._build_planning_prompt(resource, classification)
        
        try:
            result = await self.planning_agent.run(prompt)
            plan = result.data
            
            logger.info(
                f"Validation plan created: {len(plan.checks)} checks, "
                f"estimated {plan.estimated_duration_seconds}s"
            )
            
            return plan
            
        except Exception as e:
            logger.warning(f"Failed to create AI plan, using fallback: {e}")
            return self._create_fallback_plan(resource, classification)
    
    def _build_planning_prompt(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> str:
        """Build prompt for validation planning.
        
        Args:
            resource: Resource information
            classification: Resource classification
        
        Returns:
            Prompt string
        """
        prompt_parts = [
            "Create a validation plan for this resource:",
            f"\nHost: {resource.host}",
            f"Resource Type: {resource.resource_type.value}",
            f"Category: {classification.category.value}",
            f"Classification Confidence: {classification.confidence:.2f}",
        ]
        
        if classification.primary_application:
            prompt_parts.append(
                f"Primary Application: {classification.primary_application.name} "
                f"(confidence: {classification.primary_application.confidence:.2f})"
            )
        
        if classification.secondary_applications:
            apps = ", ".join(app.name for app in classification.secondary_applications)
            prompt_parts.append(f"Secondary Applications: {apps}")
        
        if classification.recommended_validations:
            prompt_parts.append(
                f"Recommended Validations: {', '.join(classification.recommended_validations)}"
            )
        
        # Add resource-specific context
        if isinstance(resource, VMResourceInfo):
            prompt_parts.append(f"SSH User: {resource.ssh_user}")
            if resource.required_services:
                prompt_parts.append(
                    f"Required Services: {', '.join(resource.required_services)}"
                )
        elif isinstance(resource, OracleDBResourceInfo):
            prompt_parts.append(f"Database User: {resource.db_user}")
            prompt_parts.append(f"Port: {resource.port}")
            if resource.service_name:
                prompt_parts.append(f"Service Name: {resource.service_name}")
        elif isinstance(resource, MongoDBResourceInfo):
            prompt_parts.append(f"Port: {resource.port}")
            if resource.database_name:
                prompt_parts.append(f"Database: {resource.database_name}")
            if resource.validate_replica_set:
                prompt_parts.append("Validate Replica Set: Yes")
        
        prompt_parts.extend([
            "\nCreate a validation plan that:",
            "1. Includes appropriate checks for this resource category",
            "2. Uses the correct MCP tools",
            "3. Prioritizes critical checks (priority 1-2)",
            "4. Provides clear expected results and failure impacts",
            "5. Estimates realistic execution time",
            "\nProvide reasoning for your plan."
        ])
        
        return "\n".join(prompt_parts)
    
    def _create_fallback_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> ValidationPlan:
        """Create fallback validation plan when AI fails.
        
        Args:
            resource: Resource information
            classification: Resource classification
        
        Returns:
            ValidationPlan with basic checks
        """
        logger.info("Creating fallback validation plan")
        
        checks = []
        
        # Basic network check (always included)
        checks.append(ValidationCheck(
            check_id="net_001",
            check_name="Network Connectivity",
            check_type="network",
            priority=1,
            description="Verify network connectivity to the resource",
            mcp_tool="tcp_portcheck",
            tool_args={"host": resource.host, "ports": [22]},
            expected_result="Port 22 (SSH) is accessible",
            failure_impact="Cannot connect to resource for further validation"
        ))
        
        # Category-specific checks
        if classification.category == ResourceCategory.DATABASE_SERVER:
            checks.extend(self._get_database_checks(resource, classification))
        elif classification.category == ResourceCategory.WEB_SERVER:
            checks.extend(self._get_web_server_checks(resource))
        elif classification.category == ResourceCategory.APPLICATION_SERVER:
            checks.extend(self._get_app_server_checks(resource))
        else:
            checks.extend(self._get_generic_checks(resource))
        
        return ValidationPlan(
            strategy_name=f"{classification.category.value}_fallback",
            resource_category=classification.category,
            checks=checks,
            estimated_duration_seconds=len(checks) * 5,
            reasoning="Fallback plan with basic validation checks"
        )
    
    def _get_database_checks(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> List[ValidationCheck]:
        """Get database-specific checks."""
        checks = []
        
        if isinstance(resource, OracleDBResourceInfo):
            checks.append(ValidationCheck(
                check_id="db_oracle_001",
                check_name="Oracle Database Connection",
                check_type="database",
                priority=1,
                description="Verify Oracle database connectivity",
                mcp_tool="db_oracle_connect",
                tool_args={
                    "host": resource.host,
                    "port": resource.port,
                    "service": resource.service_name,
                    "user": resource.db_user,
                    "password": resource.db_password
                },
                expected_result="Successfully connected to Oracle database",
                failure_impact="Database is not accessible"
            ))
            
            checks.append(ValidationCheck(
                check_id="db_oracle_002",
                check_name="Tablespace Usage",
                check_type="database",
                priority=2,
                description="Check Oracle tablespace usage",
                mcp_tool="db_oracle_tablespaces",
                tool_args={
                    "dsn": resource.dsn or f"{resource.host}:{resource.port}/{resource.service_name}",
                    "user": resource.db_user,
                    "password": resource.db_password
                },
                expected_result="All tablespaces below 85% usage",
                failure_impact="Database may run out of space"
            ))
        
        elif isinstance(resource, MongoDBResourceInfo):
            checks.append(ValidationCheck(
                check_id="db_mongo_001",
                check_name="MongoDB Connection",
                check_type="database",
                priority=1,
                description="Verify MongoDB connectivity",
                mcp_tool="db_mongo_connect",
                tool_args={
                    "host": resource.host,
                    "port": resource.port,
                    "user": resource.mongo_user,
                    "password": resource.mongo_password,
                    "database": resource.auth_db
                },
                expected_result="Successfully connected to MongoDB",
                failure_impact="Database is not accessible"
            ))
            
            if resource.validate_replica_set:
                checks.append(ValidationCheck(
                    check_id="db_mongo_002",
                    check_name="Replica Set Status",
                    check_type="database",
                    priority=2,
                    description="Check MongoDB replica set health",
                    mcp_tool="db_mongo_rs_status",
                    tool_args={
                        "uri": resource.uri or f"mongodb://{resource.host}:{resource.port}"
                    },
                    expected_result="All replica set members are healthy",
                    failure_impact="Replica set may have issues"
                ))
        
        return checks
    
    def _get_web_server_checks(self, resource: ResourceInfo) -> List[ValidationCheck]:
        """Get web server-specific checks."""
        checks = []
        
        checks.append(ValidationCheck(
            check_id="web_001",
            check_name="HTTP Port Check",
            check_type="network",
            priority=1,
            description="Verify HTTP port is accessible",
            mcp_tool="tcp_portcheck",
            tool_args={"host": resource.host, "ports": [80, 443]},
            expected_result="HTTP/HTTPS ports are accessible",
            failure_impact="Web server is not accessible"
        ))
        
        if isinstance(resource, VMResourceInfo):
            checks.append(ValidationCheck(
                check_id="web_002",
                check_name="Web Server Process",
                check_type="system",
                priority=2,
                description="Verify web server process is running",
                mcp_tool="workload_scan_processes",
                tool_args={
                    "host": resource.host,
                    "ssh_user": resource.ssh_user,
                    "ssh_password": resource.ssh_password,
                    "ssh_key_path": resource.ssh_key_path
                },
                expected_result="Web server process (nginx/apache) is running",
                failure_impact="Web server may not be serving requests"
            ))
        
        return checks
    
    def _get_app_server_checks(self, resource: ResourceInfo) -> List[ValidationCheck]:
        """Get application server-specific checks."""
        checks = []
        
        if isinstance(resource, VMResourceInfo):
            checks.append(ValidationCheck(
                check_id="app_001",
                check_name="System Resources",
                check_type="system",
                priority=1,
                description="Check system resources (CPU, memory, disk)",
                mcp_tool="vm_linux_uptime_load_mem",
                tool_args={
                    "host": resource.host,
                    "username": resource.ssh_user,
                    "password": resource.ssh_password,
                    "key_path": resource.ssh_key_path
                },
                expected_result="System resources within acceptable limits",
                failure_impact="Application may experience performance issues"
            ))
        
        return checks
    
    def _get_generic_checks(self, resource: ResourceInfo) -> List[ValidationCheck]:
        """Get generic checks for unknown resource types."""
        checks = []
        
        if isinstance(resource, VMResourceInfo):
            checks.append(ValidationCheck(
                check_id="sys_001",
                check_name="System Health",
                check_type="system",
                priority=2,
                description="Check basic system health",
                mcp_tool="vm_linux_uptime_load_mem",
                tool_args={
                    "host": resource.host,
                    "username": resource.ssh_user,
                    "password": resource.ssh_password,
                    "key_path": resource.ssh_key_path
                },
                expected_result="System is healthy and responsive",
                failure_impact="System may have issues"
            ))
        
        return checks


# Made with Bob