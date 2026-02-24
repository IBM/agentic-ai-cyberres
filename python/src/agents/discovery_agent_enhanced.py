#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Enhanced Discovery agent with tool coordination and state management."""

import logging
from typing import Optional, Union
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from datetime import datetime

from models import (
    WorkloadDiscoveryResult,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    PortInfo,
    ProcessInfo,
    ApplicationDetection
)
from mcp_client import MCPClient
from mcp_stdio_client import MCPStdioClient
from agents.base import AgentConfig, EnhancedAgent
from tool_coordinator import ToolCoordinator
from state_manager import StateManager, WorkflowState
from feature_flags import FeatureFlags

# Type aliases
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo
MCPClientType = Union[MCPClient, MCPStdioClient]

logger = logging.getLogger(__name__)


class DiscoveryPlan(BaseModel):
    """Plan for workload discovery."""
    scan_ports: bool = Field(default=True, description="Whether to scan ports")
    scan_processes: bool = Field(default=True, description="Whether to scan processes")
    detect_applications: bool = Field(default=True, description="Whether to detect applications")
    use_parallel: bool = Field(default=False, description="Whether to use parallel execution")
    reasoning: str = Field(description="Reasoning for the discovery plan")


class EnhancedDiscoveryAgent(EnhancedAgent):
    """Enhanced discovery agent with tool coordination and state management.
    
    This agent extends the base discovery capabilities with:
    - Tool coordinator for retry and caching
    - State management for workflow persistence
    - Feature flags for gradual rollout
    - Parallel execution support
    """
    
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
Be thorough but efficient - only scan what's necessary.

NEW: You can now recommend parallel execution for independent scans to improve performance."""
    
    def __init__(
        self,
        mcp_client: MCPClientType,
        config: Optional[AgentConfig] = None,
        tool_coordinator: Optional[ToolCoordinator] = None,
        state_manager: Optional[StateManager] = None,
        feature_flags: Optional[FeatureFlags] = None
    ):
        """Initialize enhanced discovery agent.
        
        Args:
            mcp_client: MCP client for tool access
            config: Agent configuration for Pydantic AI
            tool_coordinator: Optional tool coordinator for enhanced execution
            state_manager: Optional state manager for workflow persistence
            feature_flags: Optional feature flags for feature control
        """
        super().__init__(
            mcp_client=mcp_client,
            name="enhanced_discovery",
            tool_coordinator=tool_coordinator,
            state_manager=state_manager,
            feature_flags=feature_flags
        )
        
        self.config = config or AgentConfig()
        
        # Create planning agent with Pydantic AI
        self.planning_agent = self.config.create_agent(
            result_type=DiscoveryPlan,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        self.log_step("Enhanced discovery agent initialized")
    
    async def discover(
        self,
        resource: ResourceInfo,
        workflow_id: Optional[str] = None
    ) -> WorkloadDiscoveryResult:
        """Perform intelligent workload discovery with enhanced capabilities.
        
        Args:
            resource: Resource to discover
            workflow_id: Optional workflow ID for state tracking
        
        Returns:
            WorkloadDiscoveryResult with discovered information
        """
        self.log_step(f"Starting enhanced discovery for {resource.host}")
        
        # Save initial state if state manager available
        if self.state_manager and workflow_id:
            await self.state_manager.transition_to(
                WorkflowState.DISCOVERY,
                {
                    "workflow_id": workflow_id,
                    "resource_host": resource.host,
                    "resource_type": resource.resource_type.value
                }
            )
        
        try:
            # Step 1: Create discovery plan
            plan = await self._create_plan(resource)
            self.log_step(
                f"Discovery plan created: ports={plan.scan_ports}, "
                f"processes={plan.scan_processes}, apps={plan.detect_applications}, "
                f"parallel={plan.use_parallel}"
            )
            
            # Step 2: Execute discovery
            result = await self._execute_discovery(resource, plan)
            
            self.log_step(
                f"Discovery completed for {resource.host}: "
                f"{len(result.ports)} ports, {len(result.processes)} processes, "
                f"{len(result.applications)} applications"
            )
            
            # Record execution
            self.record_execution(
                action="discovery_complete",
                result={
                    "host": resource.host,
                    "ports_found": len(result.ports),
                    "processes_found": len(result.processes),
                    "applications_found": len(result.applications)
                },
                metadata={"plan": plan.model_dump()}
            )
            
            return result
            
        except Exception as e:
            self.log_step(f"Discovery failed: {e}", level="error")
            
            # Save error state
            if self.state_manager and workflow_id:
                await self.state_manager.transition_to(
                    WorkflowState.FAILED,
                    {"error": str(e), "phase": "discovery"}
                )
            
            raise
    
    async def _create_plan(self, resource: ResourceInfo) -> DiscoveryPlan:
        """Create discovery plan using AI.
        
        Args:
            resource: Resource information
        
        Returns:
            DiscoveryPlan
        """
        # Check if parallel execution is available
        can_use_parallel = (
            self.feature_flags and
            self.feature_flags.is_enabled("parallel_tool_execution")
        )
        
        prompt = f"""Create a discovery plan for this resource:

Host: {resource.host}
Type: {resource.resource_type}
SSH User: {resource.ssh_user}
SSH Port: {resource.ssh_port}

Parallel Execution Available: {can_use_parallel}

Consider:
- What discovery methods are most appropriate?
- What information would be most valuable?
- How to be efficient while thorough?
- Should we use parallel execution for independent scans?

Provide a plan with reasoning."""
        
        try:
            result = await self.planning_agent.run(prompt)
            return result.data
        except Exception as e:
            self.log_step(f"Failed to create AI plan, using default: {e}", level="warning")
            # Fallback to default plan
            return DiscoveryPlan(
                scan_ports=True,
                scan_processes=True,
                detect_applications=True,
                use_parallel=can_use_parallel,
                reasoning="Default plan: comprehensive discovery"
            )
    
    async def _execute_discovery(
        self,
        resource: ResourceInfo,
        plan: DiscoveryPlan
    ) -> WorkloadDiscoveryResult:
        """Execute discovery plan with enhanced capabilities.
        
        Args:
            resource: Resource to discover
            plan: Discovery plan
        
        Returns:
            WorkloadDiscoveryResult
        """
        # Prepare tool calls
        tool_calls = []
        
        if plan.scan_ports:
            tool_calls.append((
                "workload_scan_ports",
                {
                    "host": resource.host,
                    "ssh_user": resource.ssh_user,
                    "ssh_password": getattr(resource, 'ssh_password', None),
                    "ssh_key_path": getattr(resource, 'ssh_key_path', None)
                }
            ))
        
        if plan.scan_processes:
            tool_calls.append((
                "workload_scan_processes",
                {
                    "host": resource.host,
                    "ssh_user": resource.ssh_user,
                    "ssh_password": getattr(resource, 'ssh_password', None),
                    "ssh_key_path": getattr(resource, 'ssh_key_path', None)
                }
            ))
        
        # Execute scans (parallel or sequential based on plan)
        if plan.use_parallel and len(tool_calls) > 1:
            self.log_step(f"Executing {len(tool_calls)} scans in parallel")
            results = await self.execute_tools_parallel(tool_calls, use_cache=True)
            port_data = results[0] if plan.scan_ports else {"ports": []}
            process_data = results[1] if plan.scan_processes else {"processes": []}
        else:
            self.log_step(f"Executing {len(tool_calls)} scans sequentially")
            port_data = {"ports": []}
            process_data = {"processes": []}
            
            if plan.scan_ports:
                port_data = await self.execute_tool(
                    "workload_scan_ports",
                    tool_calls[0][1],
                    use_cache=True,
                    max_retries=3
                )
            
            if plan.scan_processes:
                process_idx = 1 if plan.scan_ports else 0
                process_data = await self.execute_tool(
                    "workload_scan_processes",
                    tool_calls[process_idx][1],
                    use_cache=True,
                    max_retries=3
                )
        
        # Extract results
        port_results = port_data.get("ports", []) if port_data.get("success") else []
        process_results = process_data.get("processes", []) if process_data.get("success") else []
        
        self.log_step(f"Found {len(port_results)} ports, {len(process_results)} processes")
        
        # Application detection
        app_results = []
        if plan.detect_applications and (port_results or process_results):
            try:
                self.log_step(f"Detecting applications on {resource.host}")
                app_data = await self.execute_tool(
                    "workload_detect_applications",
                    {
                        "host": resource.host,
                        "ports": port_results,
                        "processes": process_results
                    },
                    use_cache=True,
                    max_retries=2
                )
                
                if app_data.get("success"):
                    app_results = app_data.get("applications", [])
                    self.log_step(f"Detected {len(app_results)} applications")
            except Exception as e:
                self.log_step(f"Application detection error: {e}", level="warning")
        
        # Aggregate results
        try:
            self.log_step(f"Aggregating discovery results for {resource.host}")
            aggregated = await self.execute_tool(
                "workload_aggregate_results",
                {
                    "host": resource.host,
                    "port_results": {"ports": port_results},
                    "process_results": {"processes": process_results},
                    "app_detections": {"applications": app_results}
                },
                use_cache=False,  # Don't cache aggregation
                max_retries=1
            )
            
            if aggregated.get("success"):
                result_data = aggregated.get("result", {})
                return WorkloadDiscoveryResult(**result_data)
        except Exception as e:
            self.log_step(f"Aggregation error: {e}", level="warning")
        
        # Fallback: create result manually
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[PortInfo(**p) for p in port_results] if port_results else [],
            processes=[ProcessInfo(**p) for p in process_results] if process_results else [],
            applications=[ApplicationDetection(**a) for a in app_results] if app_results else [],
            discovery_time=datetime.now()
        )
    
    async def discover_with_retry(
        self,
        resource: ResourceInfo,
        max_retries: int = 2,
        workflow_id: Optional[str] = None
    ) -> WorkloadDiscoveryResult:
        """Perform discovery with retry logic.
        
        Args:
            resource: Resource to discover
            max_retries: Maximum retry attempts
            workflow_id: Optional workflow ID for state tracking
        
        Returns:
            WorkloadDiscoveryResult
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.log_step(f"Retry attempt {attempt} for {resource.host}")
                
                return await self.discover(resource, workflow_id)
            
            except Exception as e:
                last_error = e
                self.log_step(f"Discovery attempt {attempt + 1} failed: {e}", level="warning")
                
                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    import asyncio
                    wait_time = 2 ** attempt
                    self.log_step(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        error_msg = f"Discovery failed after {max_retries + 1} attempts"
        if last_error:
            error_msg += f": {last_error}"
        self.log_step(error_msg, level="error")
        raise Exception(error_msg) if last_error is None else last_error


# Made with Bob