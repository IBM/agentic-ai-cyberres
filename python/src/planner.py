#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Validation plan generation for recovery validation agent."""

import logging
from typing import Dict, Any, List
from models import ResourceType, VMResourceInfo, OracleDBResourceInfo, MongoDBResourceInfo

logger = logging.getLogger(__name__)


class ValidationStep:
    """Represents a single validation step."""
    
    def __init__(
        self,
        step_id: str,
        tool_name: str,
        description: str,
        arguments: Dict[str, Any],
        required: bool = True
    ):
        """Initialize validation step.
        
        Args:
            step_id: Unique step identifier
            tool_name: MCP tool name to call
            description: Human-readable description
            arguments: Tool arguments
            required: Whether step is required for validation
        """
        self.step_id = step_id
        self.tool_name = tool_name
        self.description = description
        self.arguments = arguments
        self.required = required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "arguments": self.arguments,
            "required": self.required
        }


class ValidationPlan:
    """Validation plan containing ordered steps."""
    
    def __init__(self, resource_type: ResourceType, steps: List[ValidationStep]):
        """Initialize validation plan.
        
        Args:
            resource_type: Type of resource being validated
            steps: List of validation steps
        """
        self.resource_type = resource_type
        self.steps = steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type.value,
            "steps": [step.to_dict() for step in self.steps]
        }
    
    def __len__(self) -> int:
        """Return number of steps."""
        return len(self.steps)


class ValidationPlanner:
    """Generate validation plans based on resource type."""
    
    def __init__(self):
        """Initialize validation planner."""
        pass
    
    def plan_vm_validation(self, resource_info: VMResourceInfo) -> ValidationPlan:
        """Generate validation plan for VM.
        
        Based on planner.md:
        1. Check network reachability (SSH port)
        2. Get uptime, load, and memory info
        3. Check filesystem usage
        4. Verify required services
        
        Args:
            resource_info: VM resource information
        
        Returns:
            ValidationPlan for VM
        """
        steps = []
        
        # Step 1: Network connectivity check
        steps.append(ValidationStep(
            step_id="vm_network_check",
            tool_name="tcp_portcheck",
            description=f"Check SSH port {resource_info.ssh_port} connectivity",
            arguments={
                "host": resource_info.host,
                "ports": [resource_info.ssh_port],
                "timeout_s": 5.0
            },
            required=True
        ))
        
        # Step 2: Uptime, load, and memory
        steps.append(ValidationStep(
            step_id="vm_uptime_load_mem",
            tool_name="vm_linux_uptime_load_mem",
            description="Get VM uptime, load averages, and memory information",
            arguments={
                "host": resource_info.host,
                "username": resource_info.ssh_user,
                "password": resource_info.ssh_password,
                "key_path": resource_info.ssh_key_path
            },
            required=True
        ))
        
        # Step 3: Filesystem usage
        steps.append(ValidationStep(
            step_id="vm_fs_usage",
            tool_name="vm_linux_fs_usage",
            description="Check filesystem usage for all mounted filesystems",
            arguments={
                "host": resource_info.host,
                "username": resource_info.ssh_user,
                "password": resource_info.ssh_password,
                "key_path": resource_info.ssh_key_path
            },
            required=True
        ))
        
        # Step 4: Services check (if required services specified)
        if resource_info.required_services:
            steps.append(ValidationStep(
                step_id="vm_services_check",
                tool_name="vm_linux_services",
                description=f"Verify {len(resource_info.required_services)} required services are running",
                arguments={
                    "host": resource_info.host,
                    "username": resource_info.ssh_user,
                    "password": resource_info.ssh_password,
                    "key_path": resource_info.ssh_key_path,
                    "required": resource_info.required_services
                },
                required=True
            ))
        
        logger.info(f"Generated VM validation plan with {len(steps)} steps")
        return ValidationPlan(ResourceType.VM, steps)
    
    def plan_oracle_validation(self, resource_info: OracleDBResourceInfo) -> ValidationPlan:
        """Generate validation plan for Oracle database.
        
        Based on planner.md:
        1. Check network reachability (Oracle port 1521)
        2. Test database connection
        3. Check tablespace usage
        
        Args:
            resource_info: Oracle resource information
        
        Returns:
            ValidationPlan for Oracle
        """
        steps = []
        
        # Step 1: Network connectivity check
        steps.append(ValidationStep(
            step_id="oracle_network_check",
            tool_name="tcp_portcheck",
            description=f"Check Oracle port {resource_info.port} connectivity",
            arguments={
                "host": resource_info.host,
                "ports": [resource_info.port],
                "timeout_s": 5.0
            },
            required=True
        ))
        
        # Step 2: Database connection
        connect_args = {
            "user": resource_info.db_user,
            "password": resource_info.db_password,
            "port": resource_info.port
        }
        
        if resource_info.dsn:
            connect_args["dsn"] = resource_info.dsn
        else:
            connect_args["host"] = resource_info.host
            if resource_info.service_name:
                connect_args["service"] = resource_info.service_name
        
        steps.append(ValidationStep(
            step_id="oracle_connect",
            tool_name="db_oracle_connect",
            description="Test Oracle database connection and get instance info",
            arguments=connect_args,
            required=True
        ))
        
        # Step 3: Tablespace usage
        # Build DSN if not provided
        dsn = resource_info.dsn
        if not dsn and resource_info.service_name:
            dsn = f"{resource_info.host}:{resource_info.port}/{resource_info.service_name}"
        
        if dsn:
            steps.append(ValidationStep(
                step_id="oracle_tablespaces",
                tool_name="db_oracle_tablespaces",
                description="Check tablespace usage and free space",
                arguments={
                    "dsn": dsn,
                    "user": resource_info.db_user,
                    "password": resource_info.db_password
                },
                required=True
            ))
        
        logger.info(f"Generated Oracle validation plan with {len(steps)} steps")
        return ValidationPlan(ResourceType.ORACLE, steps)
    
    def plan_mongodb_validation(self, resource_info: MongoDBResourceInfo) -> ValidationPlan:
        """Generate validation plan for MongoDB.
        
        Based on planner.md:
        1. Check network reachability (MongoDB port 27017)
        2. Test database connection
        3. Check replica set status (if applicable)
        4. Validate collection (if specified)
        
        Args:
            resource_info: MongoDB resource information
        
        Returns:
            ValidationPlan for MongoDB
        """
        steps = []
        
        # Step 1: Network connectivity check
        steps.append(ValidationStep(
            step_id="mongodb_network_check",
            tool_name="tcp_portcheck",
            description=f"Check MongoDB port {resource_info.port} connectivity",
            arguments={
                "host": resource_info.host,
                "ports": [resource_info.port],
                "timeout_s": 5.0
            },
            required=True
        ))
        
        # Step 2: Database connection
        connect_args = {
            "port": resource_info.port,
            "database": resource_info.auth_db
        }
        
        if resource_info.uri:
            connect_args["uri"] = resource_info.uri
        else:
            connect_args["host"] = resource_info.host
            if resource_info.mongo_user:
                connect_args["user"] = resource_info.mongo_user
            if resource_info.mongo_password:
                connect_args["password"] = resource_info.mongo_password
        
        steps.append(ValidationStep(
            step_id="mongodb_connect",
            tool_name="db_mongo_connect",
            description="Test MongoDB connection and get server version",
            arguments=connect_args,
            required=True
        ))
        
        # Step 3: Replica set status (if requested and URI available)
        if resource_info.validate_replica_set and resource_info.uri:
            steps.append(ValidationStep(
                step_id="mongodb_replica_status",
                tool_name="db_mongo_rs_status",
                description="Check MongoDB replica set status",
                arguments={"uri": resource_info.uri},
                required=False  # Not all MongoDB instances are replica sets
            ))
        
        # Step 4: Collection validation (if specified and SSH available)
        if (resource_info.database_name and 
            resource_info.collection_name and 
            resource_info.ssh_user):
            steps.append(ValidationStep(
                step_id="mongodb_collection_validate",
                tool_name="validate_collection",
                description=f"Validate collection {resource_info.database_name}.{resource_info.collection_name}",
                arguments={
                    "ssh_host": resource_info.host,
                    "ssh_user": resource_info.ssh_user,
                    "ssh_password": resource_info.ssh_password,
                    "ssh_key_path": resource_info.ssh_key_path,
                    "port": resource_info.port,
                    "mongo_user": resource_info.mongo_user,
                    "mongo_password": resource_info.mongo_password,
                    "auth_db": resource_info.auth_db,
                    "db_name": resource_info.database_name,
                    "collection": resource_info.collection_name,
                    "full": True
                },
                required=False
            ))
        
        logger.info(f"Generated MongoDB validation plan with {len(steps)} steps")
        return ValidationPlan(ResourceType.MONGODB, steps)
    
    def generate_plan(
        self,
        resource_info: VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo
    ) -> ValidationPlan:
        """Generate validation plan based on resource type.
        
        Args:
            resource_info: Resource information
        
        Returns:
            ValidationPlan for the resource
        
        Raises:
            ValueError: If resource type is not supported
        """
        if resource_info.resource_type == ResourceType.VM:
            return self.plan_vm_validation(resource_info)
        elif resource_info.resource_type == ResourceType.ORACLE:
            return self.plan_oracle_validation(resource_info)
        elif resource_info.resource_type == ResourceType.MONGODB:
            return self.plan_mongodb_validation(resource_info)
        else:
            raise ValueError(f"Unsupported resource type: {resource_info.resource_type}")

# Made with Bob
