#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Resource auto-discovery for recovery validation agent."""

import logging
from typing import Dict, Any, Optional
from models import ResourceType, VMResourceInfo, OracleDBResourceInfo, MongoDBResourceInfo
from mcp_client import MCPClient, MCPClientError

logger = logging.getLogger(__name__)


class DiscoveryError(Exception):
    """Exception raised for discovery errors."""
    pass


class ResourceDiscovery:
    """Auto-discover resource details using MCP tools."""
    
    def __init__(self, mcp_client: MCPClient):
        """Initialize resource discovery.
        
        Args:
            mcp_client: Connected MCP client instance
        """
        self.mcp_client = mcp_client
    
    async def discover_vm(self, resource_info: VMResourceInfo) -> Dict[str, Any]:
        """Discover VM details.
        
        Args:
            resource_info: VM resource information
        
        Returns:
            Dictionary with discovered information
        
        Raises:
            DiscoveryError: If discovery fails
        """
        discovery = {
            "resource_type": "vm",
            "host": resource_info.host,
            "ssh_accessible": False,
            "os_info": None,
            "services": [],
            "errors": []
        }
        
        try:
            # Check SSH port connectivity
            logger.info(f"Checking SSH connectivity to {resource_info.host}")
            port_check = await self.mcp_client.tcp_portcheck(
                host=resource_info.host,
                ports=[resource_info.ssh_port],
                timeout_s=5.0
            )
            
            if port_check.get("ok") and port_check.get("all_ok"):
                discovery["ssh_accessible"] = True
                logger.info(f"SSH port {resource_info.ssh_port} is accessible")
            else:
                discovery["errors"].append(f"SSH port {resource_info.ssh_port} not accessible")
                logger.warning(f"SSH port {resource_info.ssh_port} not accessible")
                return discovery
            
            # Get uptime and system info
            try:
                logger.info("Fetching VM uptime and memory info")
                uptime_result = await self.mcp_client.vm_linux_uptime_load_mem(
                    host=resource_info.host,
                    username=resource_info.ssh_user,
                    password=resource_info.ssh_password,
                    key_path=resource_info.ssh_key_path
                )
                
                if uptime_result.get("ok"):
                    discovery["os_info"] = {
                        "uptime_output": uptime_result.get("stdout", ""),
                        "raw_output": uptime_result.get("stdout", "")
                    }
                    logger.info("Successfully retrieved VM system info")
                else:
                    discovery["errors"].append("Failed to get uptime info")
            except MCPClientError as e:
                discovery["errors"].append(f"Uptime check failed: {str(e)}")
                logger.error(f"Uptime check failed: {e}")
            
            # Get running services
            try:
                logger.info("Fetching running services")
                services_result = await self.mcp_client.vm_linux_services(
                    host=resource_info.host,
                    username=resource_info.ssh_user,
                    password=resource_info.ssh_password,
                    key_path=resource_info.ssh_key_path,
                    required=resource_info.required_services
                )
                
                if services_result.get("ok"):
                    discovery["services"] = services_result.get("running", [])
                    logger.info(f"Found {len(discovery['services'])} running services")
                else:
                    discovery["errors"].append("Failed to get services list")
            except MCPClientError as e:
                discovery["errors"].append(f"Services check failed: {str(e)}")
                logger.error(f"Services check failed: {e}")
            
        except Exception as e:
            discovery["errors"].append(f"Discovery failed: {str(e)}")
            logger.error(f"VM discovery failed: {e}")
        
        return discovery
    
    async def discover_oracle(self, resource_info: OracleDBResourceInfo) -> Dict[str, Any]:
        """Discover Oracle database details.
        
        Args:
            resource_info: Oracle resource information
        
        Returns:
            Dictionary with discovered information
        
        Raises:
            DiscoveryError: If discovery fails
        """
        discovery = {
            "resource_type": "oracle",
            "host": resource_info.host,
            "port_accessible": False,
            "discovered_services": [],
            "discovered_sids": [],
            "instance_info": None,
            "errors": []
        }
        
        try:
            # Check Oracle port connectivity
            logger.info(f"Checking Oracle port connectivity to {resource_info.host}:{resource_info.port}")
            port_check = await self.mcp_client.tcp_portcheck(
                host=resource_info.host,
                ports=[resource_info.port],
                timeout_s=5.0
            )
            
            if port_check.get("ok") and port_check.get("all_ok"):
                discovery["port_accessible"] = True
                logger.info(f"Oracle port {resource_info.port} is accessible")
            else:
                discovery["errors"].append(f"Oracle port {resource_info.port} not accessible")
                logger.warning(f"Oracle port {resource_info.port} not accessible")
            
            # If SSH credentials provided, use discovery tool
            if resource_info.ssh_user:
                try:
                    logger.info("Running Oracle discovery via SSH")
                    discover_result = await self.mcp_client.db_oracle_discover_and_validate(
                        ssh_host=resource_info.host,
                        ssh_user=resource_info.ssh_user,
                        ssh_password=resource_info.ssh_password,
                        ssh_key_path=resource_info.ssh_key_path,
                        oracle_user=resource_info.db_user,
                        oracle_password=resource_info.db_password
                    )
                    
                    if discover_result.get("ok"):
                        discoveries = discover_result.get("discoveries", {})
                        discovery["discovered_services"] = discoveries.get("services", [])
                        discovery["discovered_sids"] = discoveries.get("sids", [])
                        discovery["discovered_ports"] = discoveries.get("ports", [])
                        
                        # If validation was performed
                        if "validation" in discover_result:
                            discovery["instance_info"] = discover_result["validation"]
                        
                        logger.info(f"Discovered {len(discovery['discovered_services'])} Oracle services")
                    else:
                        discovery["errors"].append("Oracle discovery failed")
                except MCPClientError as e:
                    discovery["errors"].append(f"Oracle discovery failed: {str(e)}")
                    logger.error(f"Oracle discovery failed: {e}")
            
            # Try direct connection if we have DSN or service name
            if resource_info.dsn or resource_info.service_name:
                try:
                    logger.info("Testing Oracle database connection")
                    connect_result = await self.mcp_client.db_oracle_connect(
                        dsn=resource_info.dsn,
                        host=resource_info.host if not resource_info.dsn else None,
                        port=resource_info.port,
                        service=resource_info.service_name,
                        user=resource_info.db_user,
                        password=resource_info.db_password
                    )
                    
                    if connect_result.get("ok"):
                        discovery["instance_info"] = {
                            "instance_name": connect_result.get("instance_name"),
                            "version": connect_result.get("version"),
                            "open_mode": connect_result.get("open_mode"),
                            "database_role": connect_result.get("database_role")
                        }
                        logger.info("Successfully connected to Oracle database")
                    else:
                        discovery["errors"].append("Oracle connection failed")
                except MCPClientError as e:
                    discovery["errors"].append(f"Oracle connection failed: {str(e)}")
                    logger.error(f"Oracle connection failed: {e}")
            
        except Exception as e:
            discovery["errors"].append(f"Discovery failed: {str(e)}")
            logger.error(f"Oracle discovery failed: {e}")
        
        return discovery
    
    async def discover_mongodb(self, resource_info: MongoDBResourceInfo) -> Dict[str, Any]:
        """Discover MongoDB details.
        
        Args:
            resource_info: MongoDB resource information
        
        Returns:
            Dictionary with discovered information
        
        Raises:
            DiscoveryError: If discovery fails
        """
        discovery = {
            "resource_type": "mongodb",
            "host": resource_info.host,
            "port_accessible": False,
            "version": None,
            "replica_set": None,
            "is_replica_set": False,
            "errors": []
        }
        
        try:
            # Check MongoDB port connectivity
            logger.info(f"Checking MongoDB port connectivity to {resource_info.host}:{resource_info.port}")
            port_check = await self.mcp_client.tcp_portcheck(
                host=resource_info.host,
                ports=[resource_info.port],
                timeout_s=5.0
            )
            
            if port_check.get("ok") and port_check.get("all_ok"):
                discovery["port_accessible"] = True
                logger.info(f"MongoDB port {resource_info.port} is accessible")
            else:
                discovery["errors"].append(f"MongoDB port {resource_info.port} not accessible")
                logger.warning(f"MongoDB port {resource_info.port} not accessible")
            
            # Try SSH-based ping if SSH credentials provided
            if resource_info.ssh_user:
                try:
                    logger.info("Testing MongoDB via SSH")
                    ping_result = await self.mcp_client.db_mongo_ssh_ping(
                        ssh_host=resource_info.host,
                        ssh_user=resource_info.ssh_user,
                        ssh_password=resource_info.ssh_password,
                        ssh_key_path=resource_info.ssh_key_path,
                        port=resource_info.port,
                        mongo_user=resource_info.mongo_user,
                        mongo_password=resource_info.mongo_password,
                        auth_db=resource_info.auth_db
                    )
                    
                    if ping_result.get("ok"):
                        logger.info("MongoDB ping via SSH successful")
                    else:
                        discovery["errors"].append("MongoDB ping via SSH failed")
                except MCPClientError as e:
                    discovery["errors"].append(f"MongoDB SSH ping failed: {str(e)}")
                    logger.error(f"MongoDB SSH ping failed: {e}")
            
            # Try direct connection if URI provided or can build one
            try:
                logger.info("Testing MongoDB direct connection")
                connect_result = await self.mcp_client.db_mongo_connect(
                    uri=resource_info.uri,
                    host=resource_info.host if not resource_info.uri else None,
                    port=resource_info.port,
                    user=resource_info.mongo_user,
                    password=resource_info.mongo_password,
                    database=resource_info.auth_db
                )
                
                if connect_result.get("ok"):
                    discovery["version"] = connect_result.get("version")
                    logger.info(f"Connected to MongoDB version {discovery['version']}")
                else:
                    discovery["errors"].append("MongoDB connection failed")
            except MCPClientError as e:
                discovery["errors"].append(f"MongoDB connection failed: {str(e)}")
                logger.error(f"MongoDB connection failed: {e}")
            
            # Check replica set status if requested
            if resource_info.validate_replica_set and resource_info.uri:
                try:
                    logger.info("Checking MongoDB replica set status")
                    rs_result = await self.mcp_client.db_mongo_rs_status(uri=resource_info.uri)
                    
                    if rs_result.get("ok"):
                        discovery["is_replica_set"] = True
                        discovery["replica_set"] = {
                            "set": rs_result.get("set"),
                            "myState": rs_result.get("myState"),
                            "members_count": len(rs_result.get("members", []))
                        }
                        logger.info(f"Replica set: {discovery['replica_set']['set']}")
                    else:
                        discovery["errors"].append("Replica set status check failed")
                except MCPClientError as e:
                    # Not being a replica set is not necessarily an error
                    logger.info(f"Not a replica set or status check failed: {e}")
            
        except Exception as e:
            discovery["errors"].append(f"Discovery failed: {str(e)}")
            logger.error(f"MongoDB discovery failed: {e}")
        
        return discovery
    
    async def discover(
        self,
        resource_info: VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo
    ) -> Dict[str, Any]:
        """Discover resource details based on type.
        
        Args:
            resource_info: Resource information
        
        Returns:
            Dictionary with discovered information
        
        Raises:
            DiscoveryError: If discovery fails
        """
        if resource_info.resource_type == ResourceType.VM:
            return await self.discover_vm(resource_info)
        elif resource_info.resource_type == ResourceType.ORACLE:
            return await self.discover_oracle(resource_info)
        elif resource_info.resource_type == ResourceType.MONGODB:
            return await self.discover_mongodb(resource_info)
        else:
            raise DiscoveryError(f"Unsupported resource type: {resource_info.resource_type}")

# Made with Bob
