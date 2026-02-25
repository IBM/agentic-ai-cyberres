#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Discovery agent for intelligent workload discovery using Pydantic AI."""

import logging
from typing import Optional, Union
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from models import (
    WorkloadDiscoveryResult,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo
)
from mcp_client import MCPClient
from mcp_stdio_client import MCPStdioClient
from agents.base import AgentConfig

# Type alias for resource info
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo

# Type alias for MCP clients
MCPClientType = Union[MCPClient, MCPStdioClient]

logger = logging.getLogger(__name__)


class DiscoveryContext(BaseModel):
    """Context for discovery agent."""
    mcp_client: MCPClientType
    resource: ResourceInfo
    
    class Config:
        arbitrary_types_allowed = True


class DiscoveryPlan(BaseModel):
    """Plan for workload discovery."""
    scan_ports: bool = Field(default=True, description="Whether to scan ports")
    scan_processes: bool = Field(default=True, description="Whether to scan processes")
    detect_applications: bool = Field(default=True, description="Whether to detect applications")
    reasoning: str = Field(description="Reasoning for the discovery plan")


class DiscoveryAgent:
    """Agent for intelligent workload discovery."""
    
    SYSTEM_PROMPT = """You are a workload discovery expert. Your role is to:
1. Analyze the resource information provided
2. Create an optimal discovery plan
3. Execute discovery using available MCP tools
4. Return comprehensive workload discovery results

You have access to these discovery capabilities:
- Port scanning: Identify open ports and services
- Process scanning: Analyze running processes
- Application detection: Identify applications based on ports and processes

Consider the resource type and available information to create an efficient discovery plan.
Be thorough but efficient - only scan what's necessary."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize discovery agent.
        
        Args:
            config: Agent configuration (uses defaults if not provided)
        """
        self.config = config or AgentConfig()
        
        # Create planning agent
        self.planning_agent = self.config.create_agent(
            result_type=DiscoveryPlan,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        logger.info("Discovery agent initialized")
    
    async def discover(
        self,
        mcp_client: MCPClient,
        resource: ResourceInfo
    ) -> WorkloadDiscoveryResult:
        """Perform intelligent workload discovery.
        
        Args:
            mcp_client: MCP client for tool access
            resource: Resource to discover
        
        Returns:
            WorkloadDiscoveryResult with discovered information
        """
        logger.info(f"Starting workload discovery for {resource.host}")
        
        # Create context
        context = DiscoveryContext(
            mcp_client=mcp_client,
            resource=resource
        )
        
        # Step 1: Create discovery plan
        plan = await self._create_plan(resource)
        logger.info(
            f"Discovery plan created: ports={plan.scan_ports}, "
            f"processes={plan.scan_processes}, apps={plan.detect_applications}"
        )
        
        # Step 2: Execute discovery
        result = await self._execute_discovery(context, plan)
        
        logger.info(
            f"Discovery completed for {resource.host}: "
            f"{len(result.ports)} ports, {len(result.processes)} processes, "
            f"{len(result.applications)} applications"
        )
        
        return result
    
    async def _create_plan(self, resource: ResourceInfo) -> DiscoveryPlan:
        """Create discovery plan using AI with Chain-of-Thought reasoning.
        
        Args:
            resource: Resource information
        
        Returns:
            DiscoveryPlan
        """
        # Fast-path for simple VM discovery (Day 3 optimization)
        if (resource.resource_type.value == "vm" and
            not hasattr(resource, 'required_services') or
            (hasattr(resource, 'required_services') and not resource.required_services)):
            
            logger.info("Using fast-path discovery plan (simple VM)")
            return DiscoveryPlan(
                scan_ports=True,
                scan_processes=True,
                detect_applications=True,
                reasoning="Standard VM discovery (fast-path - no LLM needed for simple cases)"
            )
        
        # Use LLM with Chain-of-Thought for complex cases
        logger.info("Using AI-powered discovery planning with Chain-of-Thought")
        
        prompt = f"""# Discovery Planning Task with Chain-of-Thought Reasoning

## Resource Context
- **Host**: {resource.host}
- **Type**: {resource.resource_type.value}
- **SSH Access**: {resource.ssh_user}@{resource.host}:{resource.ssh_port}

## Available Discovery Methods
1. **Port Scanning**: Identify open ports and services (fast, non-invasive)
2. **Process Scanning**: List running processes (requires SSH, more detailed)
3. **Application Detection**: Identify applications from ports/processes (intelligent analysis)

## Your Task: Create Discovery Plan with Step-by-Step Reasoning

Please think through this step-by-step:

### Step 1: Resource Analysis
What do we know about this resource? What type of workload might it run?

### Step 2: Discovery Goals
What specific information would be most valuable to discover?

### Step 3: Method Selection
Which discovery methods should we use and why?

### Step 4: Efficiency Considerations
How can we balance thoroughness with execution time?

### Step 5: Final Decision
Based on the above reasoning, what's your discovery plan?

## Example Reasoning:
```
Step 1: This is a VM with SSH access. General-purpose server.
Step 2: Need to identify running applications and services.
Step 3: Use all three methods for comprehensive discovery.
Step 4: Run port scan first (fast), then processes, then detection.
Step 5: Plan: scan_ports=true, scan_processes=true, detect_applications=true
Reasoning: Comprehensive discovery needed for unknown VM.
```

Now provide YOUR reasoning and plan."""
        
        try:
            result = await self.planning_agent.run(prompt)
            return result.data
        except Exception as e:
            logger.warning(f"Failed to create AI plan, using default: {e}")
            # Fallback to default plan
            return DiscoveryPlan(
                scan_ports=True,
                scan_processes=True,
                detect_applications=True,
                reasoning="Default plan: comprehensive discovery (AI failed)"
            )
    
    async def _execute_discovery(
        self,
        context: DiscoveryContext,
        plan: DiscoveryPlan
    ) -> WorkloadDiscoveryResult:
        """Execute discovery plan.
        
        Args:
            context: Discovery context
            plan: Discovery plan
        
        Returns:
            WorkloadDiscoveryResult
        """
        resource = context.resource
        mcp_client = context.mcp_client
        
        # Initialize results
        port_results = []
        process_results = []
        app_results = []
        
        # Step 1: Port scanning
        if plan.scan_ports:
            try:
                logger.info(f"Scanning ports on {resource.host}")
                port_data = await mcp_client.workload_scan_ports(
                    host=resource.host,
                    ssh_user=resource.ssh_user,
                    ssh_password=getattr(resource, 'ssh_password', None),
                    ssh_key_path=getattr(resource, 'ssh_key_path', None)
                )
                
                if port_data.get("success"):
                    port_results = port_data.get("ports", [])
                    logger.info(f"Found {len(port_results)} open ports")
                else:
                    logger.warning(f"Port scan failed: {port_data.get('error')}")
            except Exception as e:
                logger.error(f"Port scanning error: {e}")
        
        # Step 2: Process scanning
        if plan.scan_processes:
            try:
                logger.info(f"Scanning processes on {resource.host}")
                process_data = await mcp_client.workload_scan_processes(
                    host=resource.host,
                    ssh_user=resource.ssh_user,
                    ssh_password=getattr(resource, 'ssh_password', None),
                    ssh_key_path=getattr(resource, 'ssh_key_path', None)
                )
                
                if process_data.get("success"):
                    process_results = process_data.get("processes", [])
                    logger.info(f"Found {len(process_results)} processes")
                else:
                    logger.warning(f"Process scan failed: {process_data.get('error')}")
            except Exception as e:
                logger.error(f"Process scanning error: {e}")
        
        # Step 3: Application detection
        if plan.detect_applications and (port_results or process_results):
            try:
                logger.info(f"Detecting applications on {resource.host}")
                app_data = await mcp_client.workload_detect_applications(
                    host=resource.host,
                    ports=port_results,
                    processes=process_results
                )
                
                if app_data.get("success"):
                    app_results = app_data.get("applications", [])
                    logger.info(f"Detected {len(app_results)} applications")
                else:
                    logger.warning(f"Application detection failed: {app_data.get('error')}")
            except Exception as e:
                logger.error(f"Application detection error: {e}")
        
        # Step 4: Aggregate results
        try:
            logger.info(f"Aggregating discovery results for {resource.host}")
            aggregated = await mcp_client.workload_aggregate_results(
                host=resource.host,
                port_results={"ports": port_results},
                process_results={"processes": process_results},
                app_detections={"applications": app_results}
            )
            
            if aggregated.get("success"):
                result_data = aggregated.get("result", {})
                return WorkloadDiscoveryResult(**result_data)
            else:
                logger.warning(f"Aggregation failed: {aggregated.get('error')}")
                # Return basic result
                from datetime import datetime
                from models import PortInfo, ProcessInfo, ApplicationDetection
                
                return WorkloadDiscoveryResult(
                    host=resource.host,
                    ports=[PortInfo(**p) for p in port_results],
                    processes=[ProcessInfo(**p) for p in process_results],
                    applications=[ApplicationDetection(**a) for a in app_results],
                    discovery_time=datetime.now()
                )
        except Exception as e:
            logger.error(f"Result aggregation error: {e}")
            # Return basic result on error
            from datetime import datetime
            from models import PortInfo, ProcessInfo, ApplicationDetection
            
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[PortInfo(**p) for p in port_results] if port_results else [],
                processes=[ProcessInfo(**p) for p in process_results] if process_results else [],
                applications=[ApplicationDetection(**a) for a in app_results] if app_results else [],
                discovery_time=datetime.now()
            )
    
    async def discover_with_retry(
        self,
        mcp_client: MCPClient,
        resource: ResourceInfo,
        max_retries: int = 2
    ) -> WorkloadDiscoveryResult:
        """Perform discovery with retry logic.
        
        Args:
            mcp_client: MCP client
            resource: Resource to discover
            max_retries: Maximum retry attempts
        
        Returns:
            WorkloadDiscoveryResult
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for {resource.host}")
                
                return await self.discover(mcp_client, resource)
            
            except Exception as e:
                last_error = e
                logger.warning(f"Discovery attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    import asyncio
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        error_msg = f"Discovery failed after {max_retries + 1} attempts"
        if last_error:
            error_msg += f": {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg) if last_error is None else last_error


# Made with Bob