"""
BeeAI Validation Agent — Deterministic Validation Planning

Creates validation plans by mapping resource category + discovered applications
to exact MCP tool names and pre-populated tool_args (including SSH credentials).

Key design decisions:
- **No LLM in the planning path** — LLMs proved unreliable at (a) picking valid
  tool names and (b) injecting SSH credentials into every tool_args dict.
  Deterministic mapping eliminates both failure modes.
- **Credentials from resource object** — SSH username/password are resolved from
  secrets.json before planning starts and injected directly into tool_args.
- **Category-specific checks** — DATABASE_SERVER → Oracle/MongoDB checks + VM
  health; WEB_SERVER → HTTP port + VM health; generic → VM health.
- **API-compatible** — ``create_plan()`` still accepts ``available_tools`` for
  logging; the ``llm_model`` / ``memory_size`` / ``temperature`` constructor
  args are kept for backward compatibility.
"""

import logging
from typing import Optional, List

from pydantic import BaseModel, Field

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
    
    def __init__(
        self,
        llm_model: str = "ollama:llama3.2",
        memory_size: int = 50,
        temperature: float = 0.1
    ):
        """Initialize BeeAI Validation Agent.

        Note: ``llm_model``, ``memory_size``, and ``temperature`` are accepted
        for API compatibility but are not used — planning is fully deterministic
        and does not involve an LLM.

        Args:
            llm_model: LLM model identifier (kept for API compatibility)
            memory_size: Memory window size (kept for API compatibility)
            temperature: LLM temperature (kept for API compatibility)
        """
        self.llm_model = llm_model
        self.memory_size = memory_size
        self.temperature = temperature

        logger.info("BeeAI Validation Agent initialized (deterministic planner)")
    
    async def create_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification,
        available_tools: Optional[List] = None,
    ) -> ValidationPlan:
        """Create validation plan based on resource classification.

        Strategy: **Deterministic planning only**.

        The LLM was previously used to generate plans, but it proved unreliable
        at two things simultaneously:
          1. Picking valid tool names (hallucination)
          2. Injecting SSH credentials into every tool_args dict

        The deterministic planner solves both problems definitively:
          - Tool names are hard-coded from the known MCP server catalog
          - Credentials are injected directly from the ``resource`` object
            (which already holds the resolved SSH username/password from
            secrets.json) — no LLM involvement needed

        The ``available_tools`` parameter is accepted for API compatibility and
        is used only to log which tools are available on the server.

        Args:
            resource: Resource information (contains resolved SSH credentials)
            classification: Resource classification from discovery
            available_tools: Real MCPTool objects from the MCP server (used for
                logging only; planning is deterministic)

        Returns:
            ValidationPlan with checks and strategy

        Raises:
            Exception: If plan creation fails
        """
        logger.info(
            f"Creating validation plan for {resource.host} "
            f"(category: {classification.category.value})"
        )

        if available_tools:
            tool_names = [
                getattr(t, "name", str(t)) for t in available_tools
            ]
            logger.debug(
                f"[Planner] MCP server has {len(available_tools)} tools: "
                f"{tool_names}"
            )

        # ── Deterministic planning (sole planner) ─────────────────────────────
        # Credentials are injected directly from the resource object — no LLM.
        logger.info("[Planner] Using deterministic validation plan")
        return self._create_deterministic_plan(resource, classification)
    
    def _create_deterministic_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> ValidationPlan:
        """Create a deterministic, rule-based validation plan.

        This is the primary planner.  It maps resource category and discovered
        applications to the exact MCP tool names exposed by the server, so every
        generated check is guaranteed to be executable.

        Args:
            resource: Resource information (contains resolved SSH credentials)
            classification: Resource classification from discovery

        Returns:
            ValidationPlan with correct MCP tool names and arguments
        """
        logger.info("Creating deterministic validation plan")
        
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
            strategy_name=f"{classification.category.value}_deterministic",
            resource_category=classification.category,
            checks=checks,
            estimated_duration_seconds=len(checks) * 5,
            reasoning=(
                "Deterministic plan: checks are mapped directly from resource "
                "category and discovered applications to known MCP tool names."
            )
        )

    # Keep old name as alias so any external callers still work
    def _create_fallback_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> ValidationPlan:
        """Alias for _create_deterministic_plan (backward compatibility)."""
        return self._create_deterministic_plan(resource, classification)
    
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
        
        # Check if Oracle is detected (either as OracleDBResourceInfo or discovered on VM)
        is_oracle = isinstance(resource, OracleDBResourceInfo)
        if not is_oracle and classification.primary_application:
            app_name = classification.primary_application.name.lower()
            is_oracle = "oracle" in app_name
        
        if is_oracle:
            logger.info(f"Creating Oracle validation checks for {resource.host}")
            
            # Extract port from discovery or use default
            port = 1521
            service_name = "orcl"
            
            if isinstance(resource, OracleDBResourceInfo):
                port = resource.port
                service_name = resource.service_name or "orcl"
            elif classification.primary_application and hasattr(classification.primary_application, 'network_bindings'):
                # Extract port from discovered application
                bindings = classification.primary_application.network_bindings
                if bindings and len(bindings) > 0:
                    port = bindings[0].port
                    logger.info(f"Using discovered Oracle port: {port}")
            
            # Get credentials from resource
            db_user = "system"
            db_password = "oracle"
            
            if isinstance(resource, OracleDBResourceInfo):
                db_user = resource.db_user
                db_password = resource.db_password
            elif isinstance(resource, VMResourceInfo):
                # For VM resources, we might not have DB credentials
                # Use SSH to discover or use defaults
                logger.warning(f"Using default Oracle credentials for VM resource {resource.host}")
            
            # Get SSH credentials for all Oracle checks
            ssh_user = None
            ssh_password = None
            
            if isinstance(resource, VMResourceInfo):
                ssh_user = resource.ssh_user
                ssh_password = resource.ssh_password
            
            # Check 1: Oracle connectivity via SSH
            # ONLY send SSH parameters - MCP tools have extra='forbid'
            if ssh_user:
                checks.append(ValidationCheck(
                    check_id="db_oracle_001",
                    check_name="Oracle Database Connection",
                    check_type="database",
                    priority=1,
                    description="Verify Oracle database connectivity via SSH",
                    mcp_tool="db_oracle_connect",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "sudo_oracle": False
                    },
                    expected_result="Successfully connected to Oracle database",
                    failure_impact="Database is not accessible - critical failure"
                ))
            
            # Check 2: Tablespace usage via SSH
            # ONLY send SSH parameters - MCP tools have extra='forbid'
            if ssh_user:
                checks.append(ValidationCheck(
                    check_id="db_oracle_002",
                    check_name="Tablespace Usage",
                    check_type="database",
                    priority=2,
                    description="Check Oracle tablespace usage via SSH",
                    mcp_tool="db_oracle_tablespaces",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "sudo_oracle": True  # Set to True for tablespace query
                    },
                    expected_result="All tablespaces below 85% usage",
                    failure_impact="Database may run out of space"
                ))
            
            # Check 3: Oracle data integrity validation via SSH
            # db_oracle_data_validation checks: open_mode, database_role, log_mode,
            # corrupted blocks, offline datafiles, invalid objects, tablespace usage,
            # backup age, archive dest errors — comprehensive post-recovery readiness.
            if ssh_user:
                checks.append(ValidationCheck(
                    check_id="db_oracle_003",
                    check_name="Oracle Data Integrity Validation",
                    check_type="database",
                    priority=2,
                    description=(
                        "SSH into the VM and run comprehensive Oracle data integrity checks: "
                        "open_mode, database_role, corrupted blocks, offline datafiles, "
                        "invalid objects, tablespace usage, backup age, archive dest errors."
                    ),
                    mcp_tool="db_oracle_data_validation",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "ssh_key_path": resource.ssh_key_path if isinstance(resource, VMResourceInfo) else None,
                        "sudo_oracle": True,
                    },
                    expected_result=(
                        "Database is READ WRITE, PRIMARY role, no corrupted blocks, "
                        "no offline datafiles, no invalid objects, tablespaces < 95% full"
                    ),
                    failure_impact="Data integrity issues detected — database may not be production-ready"
                ))

            # Check 4: Oracle discovery and validation via SSH
            if ssh_user:
                checks.append(ValidationCheck(
                    check_id="db_oracle_004",
                    check_name="Oracle Discovery and Validation",
                    check_type="database",
                    priority=3,
                    description="Discover Oracle via SSH and validate configuration",
                    mcp_tool="db_oracle_discover_and_validate",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "oracle_user": db_user,
                        "oracle_password": db_password,
                        "sudo_oracle": False,
                    },
                    expected_result="Oracle discovered and validated successfully",
                    failure_impact="Cannot discover Oracle configuration via SSH"
                ))

            logger.info(f"Created {len(checks)} Oracle validation checks")
        
        # Check if MongoDB is detected
        is_mongo = isinstance(resource, MongoDBResourceInfo)
        if not is_mongo and classification.primary_application:
            app_name = classification.primary_application.name.lower()
            is_mongo = "mongo" in app_name
        
        if is_mongo:
            logger.info(f"Creating MongoDB validation checks for {resource.host}")
            
            # Extract port from discovery or use default
            port = 27017
            if isinstance(resource, MongoDBResourceInfo):
                port = resource.port
            elif classification.primary_application and hasattr(classification.primary_application, 'network_bindings'):
                bindings = classification.primary_application.network_bindings
                if bindings and len(bindings) > 0:
                    port = bindings[0].port
                    logger.info(f"Using discovered MongoDB port: {port}")
        
            # Get MongoDB credentials
            mongo_user = None
            mongo_password = None
            auth_db = "admin"
            validate_replica_set = False

            if isinstance(resource, MongoDBResourceInfo):
                mongo_user = resource.mongo_user
                mongo_password = resource.mongo_password
                auth_db = resource.auth_db
                validate_replica_set = resource.validate_replica_set
            elif isinstance(resource, VMResourceInfo):
                logger.info(
                    f"MongoDB on VM {resource.host}: will use SSH tunnel via "
                    "db_mongo_ssh_ping (MongoDB typically listens on 127.0.0.1 only)"
                )

            # ── Choose the right tool based on resource type ──────────────────
            # For a VMResourceInfo: MongoDB listens on 127.0.0.1 of the remote
            # host, so we SSH in and run mongosh locally (db_mongo_ssh_ping).
            # For a MongoDBResourceInfo: the caller has already confirmed the
            # MongoDB port is reachable from the agent, so use db_mongo_connect.
            if isinstance(resource, VMResourceInfo):
                ssh_user = resource.ssh_user
                ssh_password = resource.ssh_password
                ssh_key_path = resource.ssh_key_path

                # Check 1: MongoDB ping via SSH
                # MCP tool signature: db_mongo_ssh_ping(ssh_host, ssh_user,
                #   ssh_password, ssh_key_path, credential_id)
                # The MCP server resolves mongo auth internally via credential_id
                # or falls back to unauthenticated local access.
                # Extra params (port, mongo_user, mongo_password, auth_db) are
                # NOT accepted — the tool uses extra='forbid'.
                checks.append(ValidationCheck(
                    check_id="db_mongo_001",
                    check_name="MongoDB SSH Ping",
                    check_type="database",
                    priority=1,
                    description=(
                        "SSH into the VM and run db.adminCommand({ping:1}) via mongosh. "
                        "Works even when MongoDB listens only on 127.0.0.1."
                    ),
                    mcp_tool="db_mongo_ssh_ping",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "ssh_key_path": ssh_key_path,
                    },
                    expected_result="MongoDB ping returns {ok: 1}",
                    failure_impact="MongoDB is not running or not reachable via SSH"
                ))

                # Check 2: Replica set status via SSH
                # Same parameter contract as db_mongo_ssh_ping.
                checks.append(ValidationCheck(
                    check_id="db_mongo_002",
                    check_name="MongoDB Replica Set Status (SSH)",
                    check_type="database",
                    priority=2,
                    description="SSH into the VM and run rs.status() via mongosh.",
                    mcp_tool="db_mongo_ssh_rs_status",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "ssh_key_path": ssh_key_path,
                    },
                    expected_result="Replica set status returned (or standalone acknowledged)",
                    failure_impact="Cannot determine replica set health"
                ))

                # Check 3: Collection integrity validation via SSH
                # MCP tool: validate_collection(ssh_host, ssh_user, ssh_password,
                #   ssh_key_path, credential_id, db_name, collection, full)
                # collection="" → auto-discover all collections in the db and
                # validate each one.  This works on both standalone and replica-set
                # MongoDB without needing to know collection names in advance.
                checks.append(ValidationCheck(
                    check_id="db_mongo_003",
                    check_name="MongoDB Collection Integrity",
                    check_type="database",
                    priority=3,
                    description=(
                        "SSH into the VM and run validate() on all collections in "
                        "the admin database. Verifies MongoDB storage engine integrity."
                    ),
                    mcp_tool="validate_collection",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user,
                        "ssh_password": ssh_password,
                        "ssh_key_path": ssh_key_path,
                        "db_name": "admin",
                        "collection": "",   # empty = auto-discover all collections
                        "full": True,
                    },
                    expected_result="All collections in admin database pass full integrity validation",
                    failure_impact="MongoDB storage engine may have corruption — do not promote to production"
                ))

            else:
                # MongoDBResourceInfo: SSH-based tools are still used because
                # all MongoDB MCP tools now go via SSH (mongosh on the remote VM).
                # MCP tool signature: db_mongo_connect(ssh_host, ssh_user,
                #   ssh_password, ssh_key_path, credential_id)
                # The host field on MongoDBResourceInfo is the SSH host.
                ssh_user_mongo = getattr(resource, "ssh_user", None)
                ssh_password_mongo = getattr(resource, "ssh_password", None)
                ssh_key_path_mongo = getattr(resource, "ssh_key_path", None)

                checks.append(ValidationCheck(
                    check_id="db_mongo_001",
                    check_name="MongoDB Connection",
                    check_type="database",
                    priority=1,
                    description=(
                        "SSH into the VM and run db.adminCommand({ping:1}) via mongosh "
                        "(db_mongo_connect is an SSH-based tool)."
                    ),
                    mcp_tool="db_mongo_connect",
                    tool_args={
                        "ssh_host": resource.host,
                        "ssh_user": ssh_user_mongo,
                        "ssh_password": ssh_password_mongo,
                        "ssh_key_path": ssh_key_path_mongo,
                    },
                    expected_result="Successfully connected to MongoDB via SSH",
                    failure_impact="Database is not accessible - critical failure"
                ))

                if validate_replica_set:
                    checks.append(ValidationCheck(
                        check_id="db_mongo_002",
                        check_name="Replica Set Status",
                        check_type="database",
                        priority=2,
                        description="SSH into the VM and run rs.status() via mongosh.",
                        mcp_tool="db_mongo_rs_status",
                        tool_args={
                            "ssh_host": resource.host,
                            "ssh_user": ssh_user_mongo,
                            "ssh_password": ssh_password_mongo,
                            "ssh_key_path": ssh_key_path_mongo,
                        },
                        expected_result="All replica set members are healthy and in sync",
                        failure_impact="Replica set may have synchronization issues"
                    ))

            logger.info(f"Created {len(checks)} MongoDB validation checks")
        
        # Add VM-level health checks for database servers
        if isinstance(resource, VMResourceInfo):
            logger.info(f"Adding VM health checks for database server at {resource.host}")
            vm_checks = self._get_vm_health_checks(resource, prefix="db")
            checks.extend(vm_checks)

        # If still no checks (no DB detected, not a VM), add generic SSH connectivity check
        if not checks:
            logger.info(
                f"No specific database type detected for {resource.host} — "
                "adding generic SSH health checks"
            )
            checks.extend(self._get_generic_checks(resource))

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
        
        # Add VM-level health checks for web servers
        if isinstance(resource, VMResourceInfo):
            logger.info(f"Adding VM health checks for web server at {resource.host}")
            vm_checks = self._get_vm_health_checks(resource, prefix="web")
            checks.extend(vm_checks)
        
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
    
    def _get_vm_health_checks(self, resource: VMResourceInfo, prefix: str = "vm") -> List[ValidationCheck]:
        """Get standard VM-level health validation checks.
        
        This method provides comprehensive VM infrastructure validation that should
        be added to all resource types running on VMs (databases, web servers, etc.).
        
        Args:
            resource: VM resource information with SSH credentials
            prefix: Prefix for check IDs (e.g., "db", "web", "app", "vm")
        
        Returns:
            List of VM health validation checks (system resources, disk, services)
        """
        checks = []
        
        # Check 1: System Resources (CPU, Memory, Load)
        checks.append(ValidationCheck(
            check_id=f"{prefix}_vm_001",
            check_name="VM System Resources",
            check_type="system",
            priority=2,
            description="Check VM system load, memory usage, and uptime",
            mcp_tool="vm_linux_uptime_load_mem",
            tool_args={
                "host": resource.host,
                "username": resource.ssh_user,
                "password": resource.ssh_password,
                "key_path": resource.ssh_key_path
            },
            expected_result="System load and memory within acceptable limits",
            failure_impact="High system load or low memory may affect performance"
        ))
        
        # Check 2: Filesystem Usage
        checks.append(ValidationCheck(
            check_id=f"{prefix}_vm_002",
            check_name="VM Filesystem Usage",
            check_type="system",
            priority=2,
            description="Check disk space usage across all filesystems",
            mcp_tool="vm_linux_fs_usage",
            tool_args={
                "host": resource.host,
                "username": resource.ssh_user,
                "password": resource.ssh_password,
                "key_path": resource.ssh_key_path
            },
            expected_result="All filesystems below 85% usage",
            failure_impact="Low disk space may cause application failures"
        ))
        
        # Check 3: Critical Services (category-specific)
        required_services = []
        if prefix == "db":
            # For database servers, check for Oracle or MongoDB services
            required_services = ["oracle.service", "mongod.service"]
        elif prefix == "web":
            # For web servers, check for common web server services
            required_services = ["nginx.service", "httpd.service", "apache2.service"]
        
        if required_services:
            checks.append(ValidationCheck(
                check_id=f"{prefix}_vm_003",
                check_name="VM Critical Services",
                check_type="system",
                priority=3,
                description=f"Verify critical services are running: {', '.join(required_services)}",
                mcp_tool="vm_linux_services",
                tool_args={
                    "host": resource.host,
                    "username": resource.ssh_user,
                    "password": resource.ssh_password,
                    "key_path": resource.ssh_key_path,
                    "required": required_services
                },
                expected_result="At least one required service is active",
                failure_impact="Missing services may indicate application is not running"
            ))
        
        logger.info(f"Created {len(checks)} VM health checks with prefix '{prefix}'")
        return checks


# Backward compatibility alias
ValidationAgent = BeeAIValidationAgent

# Made with Bob
