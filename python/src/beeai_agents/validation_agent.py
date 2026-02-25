"""
BeeAI-based Validation Agent for Creating Validation Plans

This module provides a BeeAI RequirementAgent implementation for creating
intelligent validation plans based on resource classification. It replaces
the Pydantic AI implementation with BeeAI's declarative agent architecture.

Key Features:
- Intelligent validation planning using LLM reasoning
- Category-specific validation strategies
- Priority-based check ordering
- MCP tool selection and configuration
- Fallback plans for robustness
- Comprehensive error handling
"""

import logging
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field

# BeeAI imports
from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig

# Local imports
from models import (
    ResourceClassification,
    ValidationStrategy,
    ResourceCategory,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo
)

# Type aliases
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo

logger = logging.getLogger(__name__)


class ValidationCheck(BaseModel):
    """Individual validation check with MCP tool configuration."""
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
    """Complete validation plan with checks and metadata."""
    strategy_name: str = Field(..., description="Name of the validation strategy")
    resource_category: ResourceCategory = Field(..., description="Resource category")
    checks: List[ValidationCheck] = Field(..., description="List of validation checks")
    priority: int = Field(default=2, ge=1, le=5, description="Overall plan priority (1=highest, 5=lowest)")
    estimated_duration_seconds: int = Field(..., description="Estimated execution time")
    estimated_execution_time: int = Field(default=0, description="Alias for estimated_duration_seconds")
    reasoning: str = Field(..., description="Step-by-step reasoning for this validation plan")
    
    def get_priority_checks(self, max_priority: int = 2) -> List[ValidationCheck]:
        """Get high-priority checks.
        
        Args:
            max_priority: Maximum priority level to include
        
        Returns:
            List of high-priority checks
        """
        return [c for c in self.checks if c.priority <= max_priority]
    
    def get_checks_by_type(self, check_type: str) -> List[ValidationCheck]:
        """Get checks by type.
        
        Args:
            check_type: Type of checks to retrieve
        
        Returns:
            List of checks matching the type
        """
        return [c for c in self.checks if c.check_type == check_type]


class BeeAIValidationAgent:
    """BeeAI-based agent for creating intelligent validation plans.
    
    This agent uses BeeAI's RequirementAgent to create comprehensive validation
    plans based on resource classification and discovered applications. It selects
    appropriate MCP tools and prioritizes checks based on criticality.
    
    Architecture:
    - Planning Agent: Creates validation plans using LLM reasoning
    - Fallback Logic: Provides rule-based plans when LLM fails
    - Category-Specific: Tailors plans to resource categories
    
    Example:
        >>> agent = BeeAIValidationAgent(llm_model="ollama:llama3.2")
        >>> plan = await agent.create_plan(resource, classification)
        >>> priority_checks = plan.get_priority_checks(max_priority=2)
    """
    
    SYSTEM_PROMPT = """You are a validation planning expert specializing in infrastructure validation.

Your role is to:
1. Analyze resource classification and discovered applications
2. Create comprehensive validation plans with appropriate checks
3. Prioritize checks based on criticality and resource type
4. Select the right MCP tools for each validation
5. Provide clear reasoning for your decisions

Available MCP Tool Categories:
- **Network Tools**: tcp_portcheck
- **VM Tools**: vm_linux_uptime_load_mem, vm_linux_fs_usage, vm_linux_services
- **Oracle DB Tools**: db_oracle_connect, db_oracle_tablespaces, db_oracle_discover_and_validate
- **MongoDB Tools**: db_mongo_connect, db_mongo_rs_status, db_mongo_ssh_ping, validate_collection
- **Workload Discovery**: discover_workload, discover_applications, discover_os_only

Validation Plan Guidelines:
- **Comprehensive**: Cover all critical aspects of the resource
- **Prioritized**: Most important checks first (priority 1-2 are critical)
- **Efficient**: Avoid redundant checks, optimize execution order
- **Actionable**: Clear expected results and failure impacts
- **Realistic**: Accurate time estimates (typically 5-10s per check)

Priority Levels:
- Priority 1: Critical checks (connectivity, core functionality)
- Priority 2: Important checks (performance, configuration)
- Priority 3: Standard checks (monitoring, logging)
- Priority 4-5: Optional checks (nice-to-have validations)
"""
    
    PLANNING_INSTRUCTIONS = [
        "Analyze the resource type and classification carefully",
        "Consider discovered applications and their requirements",
        "Select appropriate MCP tools for each validation check",
        "Prioritize critical checks (connectivity, core functionality)",
        "Provide detailed reasoning for your validation strategy",
        "Ensure tool arguments match the resource configuration",
        "Estimate realistic execution times for each check"
    ]
    
    def __init__(
        self,
        llm_model: str = "ollama:llama3.2",
        memory_size: int = 50,
        temperature: float = 0.1
    ):
        """Initialize BeeAI Validation Agent.
        
        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2", "openai:gpt-4")
            memory_size: Size of sliding memory window
            temperature: LLM temperature for planning (0.0-1.0)
        """
        self.llm_model = llm_model
        self.memory_size = memory_size
        self.temperature = temperature
        
        # Planning agent will be created on first use
        self._planning_agent = None
        
        logger.info(
            f"BeeAI Validation Agent initialized with model: {llm_model}"
        )
    
    def _create_planning_agent(self) -> RequirementAgent:
        """Create planning agent for validation plan generation.
        
        Returns:
            Configured RequirementAgent for planning
        """
        if self._planning_agent is not None:
            return self._planning_agent
        
        logger.info("Creating validation planning agent...")
        
        # Create LLM
        llm = ChatModel.from_name(self.llm_model)
        
        # Create memory
        memory = SlidingMemory(SlidingMemoryConfig(size=self.memory_size))
        
        # Create planning agent
        self._planning_agent = RequirementAgent(
            llm=llm,
            memory=memory,
            tools=[],  # Planning doesn't need tools
            name="Validation Planning Agent",
            description="Creates comprehensive validation plans using intelligent reasoning",
            role="Infrastructure Validation Planner",
            instructions=self.PLANNING_INSTRUCTIONS,
            notes=[
                "Always provide detailed step-by-step reasoning",
                "Consider resource category and discovered applications",
                "Prioritize critical checks appropriately",
                "Select MCP tools that match the resource type"
            ],
        )
        
        logger.info("Validation planning agent created")
        return self._planning_agent
    
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
        
        Raises:
            Exception: If plan creation fails
        """
        logger.info(
            f"Creating validation plan for {resource.host} "
            f"(category: {classification.category.value})"
        )
        
        # Build planning prompt
        prompt = self._build_planning_prompt(resource, classification)
        
        try:
            # Use BeeAI agent for planning
            planning_agent = self._create_planning_agent()
            
            result = await planning_agent.run(
                prompt,
                expected_output=ValidationPlan
            )
            
            if result.output_structured:
                plan = result.output_structured
                logger.info(
                    f"Validation plan created: {len(plan.checks)} checks, "
                    f"estimated {plan.estimated_duration_seconds}s"
                )
                return plan
            else:
                logger.warning("No structured output, using fallback plan")
                return self._create_fallback_plan(resource, classification)
        
        except Exception as e:
            logger.warning(f"Failed to create AI plan: {e}, using fallback")
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
            Formatted prompt string
        """
        prompt_parts = [
            "# Validation Planning Task",
            "",
            "## Resource Information",
            f"- **Host**: {resource.host}",
            f"- **Type**: {resource.resource_type.value}",
            f"- **Category**: {classification.category.value}",
            f"- **Classification Confidence**: {classification.confidence:.2f}",
        ]
        
        # Add application information
        if classification.primary_application:
            prompt_parts.append(
                f"- **Primary Application**: {classification.primary_application.name} "
                f"(confidence: {classification.primary_application.confidence:.2f})"
            )
        
        if classification.secondary_applications:
            apps = ", ".join(app.name for app in classification.secondary_applications)
            prompt_parts.append(f"- **Secondary Applications**: {apps}")
        
        if classification.recommended_validations:
            prompt_parts.append(
                f"- **Recommended Validations**: {', '.join(classification.recommended_validations)}"
            )
        
        # Add resource-specific context
        prompt_parts.append("")
        prompt_parts.append("## Resource-Specific Details")
        
        if isinstance(resource, VMResourceInfo):
            prompt_parts.append(f"- SSH User: {resource.ssh_user}")
            prompt_parts.append(f"- SSH Port: {resource.ssh_port}")
            if resource.required_services:
                prompt_parts.append(
                    f"- Required Services: {', '.join(resource.required_services)}"
                )
        elif isinstance(resource, OracleDBResourceInfo):
            prompt_parts.append(f"- Database User: {resource.db_user}")
            prompt_parts.append(f"- Port: {resource.port}")
            if resource.service_name:
                prompt_parts.append(f"- Service Name: {resource.service_name}")
        elif isinstance(resource, MongoDBResourceInfo):
            prompt_parts.append(f"- Port: {resource.port}")
            if resource.database_name:
                prompt_parts.append(f"- Database: {resource.database_name}")
            if resource.validate_replica_set:
                prompt_parts.append("- Validate Replica Set: Yes")
        
        # Add planning requirements
        prompt_parts.extend([
            "",
            "## Your Task",
            "Create a comprehensive validation plan that:",
            "1. Includes appropriate checks for this resource category",
            "2. Uses the correct MCP tools with proper arguments",
            "3. Prioritizes critical checks (priority 1-2 for essential validations)",
            "4. Provides clear expected results and failure impacts",
            "5. Estimates realistic execution time (typically 5-10s per check)",
            "6. Includes step-by-step reasoning for your decisions",
            "",
            "Respond with a complete ValidationPlan including all checks and reasoning."
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
            reasoning="Fallback plan with basic validation checks for reliability"
        )
    
    def _get_database_checks(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> List[ValidationCheck]:
        """Get database-specific validation checks.
        
        Args:
            resource: Resource information
            classification: Resource classification
        
        Returns:
            List of database validation checks
        """
        checks = []
        
        if isinstance(resource, OracleDBResourceInfo):
            checks.append(ValidationCheck(
                check_id="db_oracle_001",
                check_name="Oracle Database Connection",
                check_type="database",
                priority=1,
                description="Verify Oracle database connectivity and basic info",
                mcp_tool="db_oracle_connect",
                tool_args={
                    "host": resource.host,
                    "port": resource.port,
                    "service": resource.service_name,
                    "user": resource.db_user,
                    "password": resource.db_password
                },
                expected_result="Successfully connected to Oracle database",
                failure_impact="Database is not accessible - critical failure"
            ))
            
            checks.append(ValidationCheck(
                check_id="db_oracle_002",
                check_name="Tablespace Usage",
                check_type="database",
                priority=2,
                description="Check Oracle tablespace usage and capacity",
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
                description="Verify MongoDB connectivity and version",
                mcp_tool="db_mongo_connect",
                tool_args={
                    "host": resource.host,
                    "port": resource.port,
                    "user": resource.mongo_user,
                    "password": resource.mongo_password,
                    "database": resource.auth_db
                },
                expected_result="Successfully connected to MongoDB",
                failure_impact="Database is not accessible - critical failure"
            ))
            
            if resource.validate_replica_set:
                checks.append(ValidationCheck(
                    check_id="db_mongo_002",
                    check_name="Replica Set Status",
                    check_type="database",
                    priority=2,
                    description="Check MongoDB replica set health and member status",
                    mcp_tool="db_mongo_rs_status",
                    tool_args={
                        "uri": resource.uri or f"mongodb://{resource.host}:{resource.port}"
                    },
                    expected_result="All replica set members are healthy and in sync",
                    failure_impact="Replica set may have synchronization issues"
                ))
        
        return checks
    
    def _get_web_server_checks(self, resource: ResourceInfo) -> List[ValidationCheck]:
        """Get web server-specific validation checks."""
        checks = []
        
        checks.append(ValidationCheck(
            check_id="web_001",
            check_name="HTTP/HTTPS Port Check",
            check_type="network",
            priority=1,
            description="Verify HTTP and HTTPS ports are accessible",
            mcp_tool="tcp_portcheck",
            tool_args={"host": resource.host, "ports": [80, 443]},
            expected_result="HTTP (80) and/or HTTPS (443) ports are accessible",
            failure_impact="Web server is not accessible to clients"
        ))
        
        if isinstance(resource, VMResourceInfo):
            checks.append(ValidationCheck(
                check_id="web_002",
                check_name="Web Server Process",
                check_type="system",
                priority=2,
                description="Verify web server process is running",
                mcp_tool="discover_applications",
                tool_args={
                    "host": resource.host,
                    "ssh_user": resource.ssh_user,
                    "ssh_password": resource.ssh_password,
                    "ssh_key_path": resource.ssh_key_path,
                    "min_confidence": "medium"
                },
                expected_result="Web server process (nginx/apache/httpd) is running",
                failure_impact="Web server may not be serving requests"
            ))
        
        return checks
    
    def _get_app_server_checks(self, resource: ResourceInfo) -> List[ValidationCheck]:
        """Get application server-specific validation checks."""
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
            
            checks.append(ValidationCheck(
                check_id="app_002",
                check_name="Filesystem Usage",
                check_type="system",
                priority=2,
                description="Check filesystem usage and available space",
                mcp_tool="vm_linux_fs_usage",
                tool_args={
                    "host": resource.host,
                    "username": resource.ssh_user,
                    "password": resource.ssh_password,
                    "key_path": resource.ssh_key_path
                },
                expected_result="All filesystems below 85% usage",
                failure_impact="Application may fail due to disk space issues"
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
                description="Check basic system health metrics",
                mcp_tool="vm_linux_uptime_load_mem",
                tool_args={
                    "host": resource.host,
                    "username": resource.ssh_user,
                    "password": resource.ssh_password,
                    "key_path": resource.ssh_key_path
                },
                expected_result="System is healthy and responsive",
                failure_impact="System may have performance or stability issues"
            ))
        
        return checks


# Backward compatibility alias
ValidationAgent = BeeAIValidationAgent

# Made with Bob
