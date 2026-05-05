"""
BeeAI-based Discovery Agent for Intelligent Workload Discovery

This module provides a BeeAI RequirementAgent implementation for discovering
workloads on target infrastructure resources. It replaces the Pydantic AI
implementation with BeeAI's declarative agent architecture.

Key Features:
- Intelligent discovery planning using LLM reasoning
- MCP tool integration for port/process scanning
- Application detection and aggregation
- Retry logic with exponential backoff
- Comprehensive error handling
"""

import logging
from typing import Optional, Union, List
from datetime import datetime

from pydantic import BaseModel, Field

# BeeAI imports
from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig
from beeai_framework.tools.mcp import MCPTool

# MCP client imports
from mcp.client.stdio import StdioServerParameters, stdio_client

# Output management imports
from agents.output import OutputManager, VerbosityLevel

# Local imports
from models import (
    WorkloadDiscoveryResult,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    PortInfo,
    ProcessInfo,
    ApplicationDetection
)

# Type aliases
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo

logger = logging.getLogger(__name__)


class DiscoveryPlan(BaseModel):
    """Plan for workload discovery with reasoning."""
    scan_ports: bool = Field(default=True, description="Whether to scan ports")
    scan_processes: bool = Field(default=True, description="Whether to scan processes")
    detect_applications: bool = Field(default=True, description="Whether to detect applications")
    reasoning: str = Field(description="Step-by-step reasoning for the discovery plan")


class BeeAIDiscoveryAgent:
    """BeeAI-based agent for intelligent workload discovery.
    
    This agent uses BeeAI's RequirementAgent to perform intelligent workload
    discovery on target infrastructure resources. It creates discovery plans
    using LLM reasoning and executes them using MCP tools.
    
    Architecture:
    - Planning Agent: Creates optimal discovery plans using Chain-of-Thought
    - Execution: Uses MCP tools for actual discovery operations
    - Aggregation: Combines results into comprehensive discovery output
    
    Example:
        >>> agent = BeeAIDiscoveryAgent(
        ...     llm_model="ollama:llama3.2",
        ...     mcp_server_path="/path/to/cyberres-mcp"
        ... )
        >>> result = await agent.discover(resource_info)
    """
    
    SYSTEM_PROMPT = """You are a workload discovery expert specializing in infrastructure analysis.

Your role is to:
1. Analyze resource information to understand the target system
2. Create optimal discovery plans using step-by-step reasoning
3. Consider efficiency vs thoroughness tradeoffs
4. Provide clear reasoning for your decisions

Available Discovery Methods:
- **Port Scanning**: Fast, identifies open ports and listening services
- **Process Scanning**: Detailed, requires SSH, shows running processes
- **Application Detection**: Intelligent, correlates ports/processes to identify applications

Guidelines:
- For simple VMs: Use all three methods for comprehensive discovery
- For databases: Focus on connectivity and service detection
- For unknown systems: Start with port scanning, then expand based on findings
- Always explain your reasoning step-by-step

Output Format:
Provide a discovery plan with:
- scan_ports: boolean
- scan_processes: boolean  
- detect_applications: boolean
- reasoning: detailed step-by-step explanation of your decision
"""
    
    PLANNING_INSTRUCTIONS = [
        "Analyze the resource type and available information",
        "Consider what discovery methods would be most effective",
        "Balance thoroughness with execution efficiency",
        "Provide clear step-by-step reasoning for your plan",
        "Ensure the plan is practical and executable"
    ]
    
    def __init__(
        self,
        llm_model: str = "ollama:llama3.2",
        mcp_tools: Optional[List[MCPTool]] = None,
        mcp_server_path: Optional[str] = None,
        memory_size: int = 50,
        temperature: float = 0.1
    ):
        """Initialize BeeAI Discovery Agent.
        
        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2", "openai:gpt-4")
            mcp_tools: List of MCP tools (if None, will auto-load)
            mcp_server_path: Path to MCP server directory (auto-detected if None)
            memory_size: Size of sliding memory window
            temperature: LLM temperature for planning (0.0-1.0)
        """
        self.llm_model = llm_model
        self.mcp_tools = mcp_tools
        self.mcp_server_path = mcp_server_path
        self.memory_size = memory_size
        self.temperature = temperature
        
        # MCP tools will be loaded on first use if not provided.
        # Typed as List[MCPTool] (never None after _ensure_mcp_tools runs).
        self._mcp_tools: List[MCPTool] = mcp_tools if mcp_tools is not None else []
        self._mcp_client = None
        
        # Planning agent will be created on first use
        self._planning_agent = None
        
        # Initialize output manager for clean agent response display
        from agents.output import OutputConfig
        config = OutputConfig(
            console_verbosity=VerbosityLevel.STANDARD,
            show_agent_name=True,
            show_timestamps=False
        )
        self.output_manager = OutputManager(config=config)
        
        logger.info(
            f"BeeAI Discovery Agent initialized with model: {llm_model}"
        )
    
    async def _ensure_mcp_tools(self):
        """Ensure MCP tools are loaded with diagnostic logging."""
        if self._mcp_tools is not None:
            return
        
        logger.info("Loading MCP tools...")
        
        # Auto-detect MCP server path if not provided
        if self.mcp_server_path is None:
            from pathlib import Path
            # Assume we're in python/src/beeai_agents, go up to python/cyberres-mcp
            self.mcp_server_path = str(Path(__file__).parent.parent.parent / "cyberres-mcp")
        
        # Create MCP client
        import os
        from pathlib import Path
        server_path = Path(self.mcp_server_path)
        
        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", str(server_path), "run", "cyberres-mcp"],
            env={
                **os.environ,
                "MCP_TRANSPORT": "stdio",
                "PYTHONPATH": str(server_path / "src"),
                "LOG_LEVEL": "WARNING",      # suppress MCP server logs
                "LOGURU_LEVEL": "WARNING",
                "FASTMCP_QUIET": "1",        # suppress FastMCP banner
            }
        )
        
        self._mcp_client = stdio_client(server_params)
        
        # Load tools
        self._mcp_tools = await MCPTool.from_client(self._mcp_client)
        
        # DIAGNOSTIC LOGGING
        logger.info(f"✓ Loaded {len(self._mcp_tools)} MCP tools")
        logger.info(f"✓ All available tools: {[t.name for t in self._mcp_tools]}")
        
        # Log discovery tools specifically
        discovery_tools = self.get_available_discovery_tools()
        logger.info(f"✓ Discovery tools available: {discovery_tools}")
        
        # Log discovery strategy
        strategy = self.get_discovery_strategy()
        logger.info(f"✓ Discovery strategy: {strategy}")
        
        # Warn if no discovery tools
        if not discovery_tools:
            logger.warning(
                "⚠️  No discovery tools found! "
                f"Available tools: {[t.name for t in self._mcp_tools]}"
            )
    
    def _create_planning_agent(self) -> RequirementAgent:
        """Create planning agent for discovery plan generation.
        
        Returns:
            Configured RequirementAgent for planning
        """
        if self._planning_agent is not None:
            return self._planning_agent
        
        logger.info("Creating planning agent...")
        
        # Create LLM
        llm = ChatModel.from_name(self.llm_model)
        
        # Create memory
        memory = SlidingMemory(SlidingMemoryConfig(size=self.memory_size))
        
        # Create planning agent (no tools needed for planning)
        self._planning_agent = RequirementAgent(
            llm=llm,
            memory=memory,
            tools=[],  # Planning doesn't need tools
            name="Discovery Planning Agent",
            description="Creates optimal discovery plans using Chain-of-Thought reasoning",
            role="Workload Discovery Planner",
            instructions=self.PLANNING_INSTRUCTIONS,
            notes=[
                "Always provide detailed step-by-step reasoning",
                "Consider resource type and available information",
                "Balance efficiency with thoroughness"
            ],
        )
        
        logger.info("Planning agent created")
        return self._planning_agent
    
    async def _create_discovery_plan(self, resource: ResourceInfo) -> DiscoveryPlan:
        """Create discovery plan using AI reasoning.
        
        Args:
            resource: Resource information
        
        Returns:
            DiscoveryPlan with reasoning
        """
        # Fast-path for simple VMs (optimization from original)
        if (resource.resource_type.value == "vm" and
            (not hasattr(resource, 'required_services') or
             not resource.required_services)):
            
            logger.info("Using fast-path discovery plan (simple VM)")
            return DiscoveryPlan(
                scan_ports=True,
                scan_processes=True,
                detect_applications=True,
                reasoning="Standard VM discovery (fast-path - no LLM needed for simple cases)"
            )
        
        # Use LLM for complex cases
        logger.info("Creating AI-powered discovery plan...")

        planning_agent = self._create_planning_agent()

        # Build credential context block — injected so the LLM knows which
        # credentials to use when calling SSH-based discovery tools.
        cred_lines = self._build_credential_context_block(resource)
        cred_block = "\n".join(cred_lines)

        prompt = f"""# Discovery Planning Task

{cred_block}
## Resource Information
- **Host**: {resource.host}
- **Type**: {resource.resource_type.value}
- **SSH User**: {getattr(resource, 'ssh_user', 'N/A')}
- **SSH Port**: {getattr(resource, 'ssh_port', 22)}

## Your Task
Create an optimal discovery plan for this resource using step-by-step reasoning.

### Step 1: Resource Analysis
What do we know about this resource? What type of workload might it run?

### Step 2: Discovery Goals
What specific information would be most valuable to discover?

### Step 3: Method Selection
Which discovery methods should we use and why?
- Port Scanning: Fast, identifies open ports
- Process Scanning: Detailed, requires SSH (use credentials above)
- Application Detection: Intelligent correlation

### Step 4: Efficiency Considerations
How can we balance thoroughness with execution time?

### Step 5: Final Decision
Based on the above reasoning, provide your discovery plan.

Respond with a JSON object containing:
- scan_ports: boolean
- scan_processes: boolean
- detect_applications: boolean
- reasoning: your complete step-by-step analysis
"""
        
        try:
            result = await planning_agent.run(
                prompt,
                expected_output=DiscoveryPlan
            )
            
            # Process agent response for clean console output
            self.output_manager.process_agent_response(
                response=result,
                agent_name="Discovery",
                phase="planning"
            )
            
            if result.output_structured:
                plan = result.output_structured
                logger.info(f"AI plan created: {plan.reasoning[:100]}...")
                return plan
            else:
                # Parse from text output
                logger.warning("No structured output, using default plan")
                return self._default_plan()
        
        except Exception as e:
            logger.warning(f"Failed to create AI plan: {e}, using default")
            return self._default_plan()
    
    def _default_plan(self) -> DiscoveryPlan:
        """Get default discovery plan.
        
        Returns:
            Default comprehensive discovery plan
        """
        return DiscoveryPlan(
            scan_ports=True,
            scan_processes=True,
            detect_applications=True,
            reasoning="Default comprehensive discovery plan (fallback)"
        )

    @staticmethod
    def _build_credential_context_block(resource) -> list:
        """Build a credential context block for injection into LLM prompts.

        The LLM must include these credentials in every tool_args that requires
        SSH access.  This keeps the MCP server stateless w.r.t. credentials.

        Args:
            resource: ResourceInfo object with optional ssh_user / ssh_password.

        Returns:
            List of prompt lines (join with "\\n" before embedding).
        """
        lines = [
            "## ⚠️  SSH CREDENTIALS FOR THIS SESSION",
            "Use the values below in **every** tool call that requires SSH access.",
            "```",
            f"host:     {resource.host}",
        ]
        ssh_user = getattr(resource, "ssh_user", None)
        ssh_password = getattr(resource, "ssh_password", None)
        ssh_port = getattr(resource, "ssh_port", 22)
        if ssh_user:
            lines.append(f"username: {ssh_user}")
            lines.append(
                f"password: {ssh_password if ssh_password else '(key-based auth)'}"
            )
            lines.append(f"port:     {ssh_port}")
        lines += [
            "```",
            "**Do NOT ask for credentials. Use the values above in every tool call.**",
            "",
        ]
        return lines
    
    async def discover(
        self,
        resource: ResourceInfo,
        mcp_tools: Optional[List[MCPTool]] = None,
        max_retries: int = 2
    ) -> WorkloadDiscoveryResult:
        """Perform intelligent workload discovery.
        
        Args:
            resource: Resource to discover
            mcp_tools: Optional list of MCP tools (uses instance tools if None)
            max_retries: Maximum retry attempts on failure
        
        Returns:
            WorkloadDiscoveryResult with discovered information
        
        Raises:
            Exception: If discovery fails after all retries
        """
        logger.info(f"Starting workload discovery for {resource.host}")
        
        # Use provided tools or instance tools
        if mcp_tools:
            self._mcp_tools = mcp_tools
        elif not self._mcp_tools:
            # Ensure MCP tools are loaded
            await self._ensure_mcp_tools()
        
        # Retry logic
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for {resource.host}")
                    import asyncio
                    wait_time = 2 ** (attempt - 1)
                    await asyncio.sleep(wait_time)
                
                # Step 1: Create discovery plan
                plan = await self._create_discovery_plan(resource)
                logger.info(
                    f"Discovery plan: ports={plan.scan_ports}, "
                    f"processes={plan.scan_processes}, apps={plan.detect_applications}"
                )
                
                # Step 2: Execute discovery
                result = await self._execute_discovery(resource, plan)
                
                logger.info(
                    f"Discovery completed: {len(result.ports)} ports, "
                    f"{len(result.processes)} processes, "
                    f"{len(result.applications)} applications"
                )
                
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(f"Discovery attempt {attempt + 1} failed: {e}")
        
        # All retries failed
        error_msg = f"Discovery failed after {max_retries + 1} attempts: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_available_discovery_tools(self) -> List[str]:
        """Get list of available discovery tool names.
        
        Returns:
            List of tool names available for discovery
        """
        if not self._mcp_tools:
            return []
        
        discovery_tools = [
            "discover_workload",
            "discover_os_only",
            "discover_applications",
            "get_raw_server_data"
        ]
        
        available = [
            tool.name for tool in self._mcp_tools
            if tool.name in discovery_tools
        ]
        
        return available
    
    def has_discovery_tool(self, tool_name: str) -> bool:
        """Check if a specific discovery tool is available.
        
        Args:
            tool_name: Name of the tool to check
        
        Returns:
            True if tool is available, False otherwise
        """
        if not self._mcp_tools:
            return False
        
        return any(tool.name == tool_name for tool in self._mcp_tools)
    
    def get_discovery_strategy(self) -> str:
        """Determine the best discovery strategy based on available tools.
        
        Returns:
            Strategy name: "comprehensive", "individual", "raw_data", or "none"
        """
        available = self.get_available_discovery_tools()
        
        if "discover_workload" in available:
            return "comprehensive"
        elif "discover_os_only" in available and "discover_applications" in available:
            return "individual"
        elif "get_raw_server_data" in available:
            return "raw_data"
        else:
            return "none"
    
    async def _execute_discovery(
        self,
        resource: ResourceInfo,
        plan: DiscoveryPlan
    ) -> WorkloadDiscoveryResult:
        """Execute discovery plan using MCP tools with dynamic tool selection.
        
        Args:
            resource: Resource information
            plan: Discovery plan
        
        Returns:
            WorkloadDiscoveryResult
        """
        logger.info(f"Executing discovery plan for {resource.host}")
        
        # Ensure tools are available
        if not self._mcp_tools:
            await self._ensure_mcp_tools()
        
        # DYNAMIC TOOL DISCOVERY: Get available tools and select strategy
        available_tool_names = [tool.name for tool in self._mcp_tools]
        logger.info(f"Available MCP tools: {available_tool_names}")
        
        discovery_tools = self.get_available_discovery_tools()
        logger.info(f"Available discovery tools: {discovery_tools}")
        
        strategy = self.get_discovery_strategy()
        logger.info(f"Selected discovery strategy: {strategy}")
        
        # Strategy 1: Try comprehensive discovery first (best option)
        comprehensive_success = False
        if strategy == "comprehensive":
            logger.info("="*60)
            logger.info("ATTEMPTING COMPREHENSIVE DISCOVERY")
            logger.info("="*60)
            try:
                result = await self._execute_comprehensive_discovery(resource, plan)
                
                # Check if result is valid and has data
                has_data = (
                    len(result.applications) > 0 or
                    len(result.ports) > 0 or
                    len(result.processes) > 0
                )
                
                # Also check if OS was detected - check for os_type (not os_name)
                os_detected = False
                if hasattr(result, 'os_info') and result.os_info:
                    # MCP tools return 'os_type', not 'os_name'
                    os_type = result.os_info.get('os_type', 'Unknown')
                    os_detected = os_type not in ['Unknown', '', None]
                
                logger.info(f"Comprehensive discovery result: has_data={has_data}, os_detected={os_detected}")
                
                if has_data or os_detected:
                    logger.info("✓ Comprehensive discovery successful - returning result")
                    comprehensive_success = True
                    return result
                else:
                    logger.warning("✗ Comprehensive discovery returned empty/invalid results")
                    logger.warning("  Applications: %d, Ports: %d, Processes: %d",
                                 len(result.applications), len(result.ports), len(result.processes))
                    # Check for os_type (not os_name) in warning message
                    os_display = result.os_info.get('os_type', 'Unknown') if hasattr(result, 'os_info') and result.os_info else 'No OS info'
                    logger.warning("  OS: %s", os_display)
                    logger.warning("  Falling back to individual tools...")
            except Exception as e:
                logger.warning(f"✗ Comprehensive discovery failed with exception: {e}")
                logger.warning("  Falling back to individual tools...")
        
        # Strategy 2: Fallback to individual tools (ALWAYS try if comprehensive failed)
        if not comprehensive_success and strategy in ["individual", "comprehensive"]:
            if "discover_os_only" in discovery_tools and "discover_applications" in discovery_tools:
                logger.info("="*60)
                logger.info("ATTEMPTING INDIVIDUAL DISCOVERY")
                logger.info("="*60)
                try:
                    result = await self._execute_individual_discovery(resource, plan)
                    if result:
                        # Validate individual discovery result
                        has_data = (
                            len(result.applications) > 0 or
                            len(result.ports) > 0 or
                            len(result.processes) > 0
                        )
                        logger.info(f"Individual discovery result: has_data={has_data}")
                        logger.info(f"  Applications: {len(result.applications)}, Ports: {len(result.ports)}, Processes: {len(result.processes)}")
                        
                        if has_data:
                            logger.info("✓ Individual discovery successful - returning result")
                            return result
                        else:
                            logger.warning("✗ Individual discovery returned empty results")
                except Exception as e:
                    logger.warning(f"✗ Individual discovery failed: {e}")
            else:
                logger.warning("Individual discovery tools not available")
                logger.warning(f"  Available tools: {discovery_tools}")
        
        # Strategy 3: Fallback to raw data collection (if individual also failed)
        if strategy in ["raw_data", "individual", "comprehensive"]:
            if "get_raw_server_data" in discovery_tools:
                logger.info("="*60)
                logger.info("ATTEMPTING RAW DATA COLLECTION")
                logger.info("="*60)
                try:
                    result = await self._execute_raw_data_discovery(resource, plan)
                    if result:
                        logger.info("✓ Raw data collection successful - returning result")
                        return result
                except Exception as e:
                    logger.warning(f"✗ Raw data collection failed: {e}")
            else:
                logger.warning("Raw data collection tool not available")
        
        # All strategies failed - return minimal result
        logger.error("="*60)
        logger.error("ALL DISCOVERY STRATEGIES FAILED")
        logger.error("="*60)
        logger.error(f"Available tools: {available_tool_names}")
        logger.error(f"Discovery tools: {discovery_tools}")
        logger.error(f"Strategy attempted: {strategy}")
        
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],
            processes=[],
            applications=[],
            discovery_time=datetime.now()
        )
    
    async def _execute_comprehensive_discovery(
        self,
        resource: ResourceInfo,
        plan: DiscoveryPlan
    ) -> WorkloadDiscoveryResult:
        """Execute discovery using the comprehensive discover_workload tool.
        
        Args:
            resource: Resource information
            plan: Discovery plan
        
        Returns:
            WorkloadDiscoveryResult
        """
        logger.info("Starting comprehensive discovery...")
        logger.info(f"  Host: {resource.host}")
        logger.info(f"  SSH User: {getattr(resource, 'ssh_user', 'NOT SET')}")
        logger.info(f"  SSH Password: {'SET' if getattr(resource, 'ssh_password', None) else 'NOT SET'}")
        logger.info(f"  SSH Port: {getattr(resource, 'ssh_port', 22)}")
        
        # Find the tool dynamically
        workload_tool = next(
            (tool for tool in self._mcp_tools if tool.name == "discover_workload"),
            None
        )
        
        if not workload_tool:
            logger.error("discover_workload tool not found in MCP tools")
            raise Exception("discover_workload tool not found")
        
        logger.info(f"✓ Found discover_workload tool")
        
        # Prepare arguments
        tool_args = {
            "host": resource.host,
            "detect_os": True,
            "detect_applications": plan.detect_applications,
            "detect_containers": True,
            "min_confidence": "medium"
        }
        
        # Add SSH credentials
        if hasattr(resource, 'ssh_user') and resource.ssh_user:
            tool_args["ssh_user"] = resource.ssh_user
            logger.info(f"  Added SSH user: {resource.ssh_user}")
        if hasattr(resource, 'ssh_password') and resource.ssh_password:
            tool_args["ssh_password"] = resource.ssh_password
            logger.info(f"  Added SSH password: {'*' * len(resource.ssh_password)}")
        if hasattr(resource, 'ssh_key_path') and resource.ssh_key_path:
            tool_args["ssh_key_path"] = resource.ssh_key_path
            logger.info(f"  Added SSH key path: {resource.ssh_key_path}")
        if hasattr(resource, 'ssh_port'):
            tool_args["ssh_port"] = resource.ssh_port
            logger.info(f"  Added SSH port: {resource.ssh_port}")
        
        logger.info(f"Calling discover_workload with {len(tool_args)} arguments")
        logger.debug(f"Tool arguments (excluding password): {dict((k, v) for k, v in tool_args.items() if k != 'ssh_password')}")
        
        result_output = await workload_tool.run(input=tool_args)
        logger.info(f"✓ Tool execution completed")
        logger.debug(f"Result output type: {type(result_output)}")
        
        # Parse result
        import json
        if isinstance(result_output.result, str):
            result = json.loads(result_output.result)
        else:
            result = result_output.result
        
        # DEBUG: Log the full response structure
        logger.info(f"Raw result from discover_workload: {json.dumps(result, indent=2)[:500]}")
        
        # Check if tool is not yet implemented (returns ok but with pending message)
        if result.get("status") == "pending_implementation" or "not yet implemented" in result.get("message", "").lower():
            logger.warning(f"discover_workload not yet fully implemented, falling back to individual tools")
            raise Exception("Tool not yet implemented")
        
        # Check success
        if not result.get("success") and not result.get("ok"):
            error_msg = result.get('error', 'Unknown error')
            raise Exception(f"Comprehensive discovery failed: {error_msg}")
        
        # Extract data - handle both wrapped and unwrapped responses
        # MCP tools may return data directly or wrapped in {"data": {...}}
        logger.debug(f"Result type: {type(result)}, Result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT A DICT'}")
        logger.debug(f"Result has 'data' key: {'data' in result if isinstance(result, dict) else False}")
        
        if "data" in result and isinstance(result.get("data"), dict):
            data = result["data"]
            logger.debug("Extracted data from result['data']")
        else:
            # Result is already the data dictionary
            data = result
            logger.debug("Using result directly as data")
        
        logger.debug(f"Data type after extraction: {type(data)}, is dict: {isinstance(data, dict)}")
        logger.debug(f"Data keys after extraction: {list(data.keys()) if isinstance(data, dict) else 'NOT A DICT'}")
        
        # Check if data is empty or missing
        if not data or not isinstance(data, dict):
            logger.warning(f"discover_workload returned no data, falling back to individual tools")
            logger.warning(f"Data value: {data}")
            raise Exception("No data returned from discover_workload")
        
        # Additional validation: check for expected keys
        expected_keys = ["os_info", "applications"]
        has_expected_data = any(key in data for key in expected_keys)
        
        logger.debug(f"Checking for expected keys {expected_keys} in data keys: {list(data.keys())}")
        logger.debug(f"Has expected data: {has_expected_data}")
        
        if not has_expected_data:
            logger.warning(f"discover_workload returned data but missing expected keys: {expected_keys}")
            logger.debug(f"Received keys: {list(data.keys())}")
            raise Exception("No valid discovery data returned from discover_workload")
        
        # DEBUG: Log data structure
        logger.info(f"✓ Data extraction successful - Keys: {list(data.keys())}")
        logger.info(f"✓ OS Info present: {'os_info' in data}")
        logger.info(f"✓ Applications present: {'applications' in data}")
        if 'applications' in data:
            logger.info(f"✓ Applications count: {len(data.get('applications', []))}")
        
        logger.info(f"Comprehensive discovery completed for {resource.host}")
        logger.info(f"Found {len(data.get('applications', []))} applications")
        
        # Helper functions to clean dictionaries before model creation
        def clean_port_dict(port_dict: dict) -> dict:
            """Ensure port dict has valid values for PortInfo model."""
            cleaned = port_dict.copy()
            if cleaned.get("state") is None:
                cleaned["state"] = "open"
            return cleaned
        
        def clean_process_dict(proc_dict: dict) -> dict:
            """Ensure process dict has valid values for ProcessInfo model."""
            cleaned = proc_dict.copy()
            if "user" not in cleaned or cleaned["user"] is None:
                cleaned["user"] = "unknown"
            if "cmdline" not in cleaned or cleaned["cmdline"] is None:
                cleaned["cmdline"] = ""
            return cleaned
        
        # Convert to WorkloadDiscoveryResult - preserve OS info
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[
                PortInfo(**clean_port_dict(port)) if isinstance(port, dict) else port
                for port in data.get("ports", [])
            ],
            processes=[
                ProcessInfo(**clean_process_dict(proc)) if isinstance(proc, dict) else proc
                for proc in data.get("processes", [])
            ],
            applications=[
                ApplicationDetection(**app) if isinstance(app, dict) else app
                for app in data.get("applications", [])
            ],
            os_info=data.get("os_info"),  # Preserve OS information
            discovery_time=datetime.now()
        )
    
    async def _execute_individual_discovery(
        self,
        resource: ResourceInfo,
        plan: DiscoveryPlan
    ) -> WorkloadDiscoveryResult:
        """Execute discovery using individual tools (discover_os_only + discover_applications).
        
        Args:
            resource: Resource information
            plan: Discovery plan
        
        Returns:
            WorkloadDiscoveryResult
        """
        # Find tools dynamically
        os_tool = next(
            (tool for tool in self._mcp_tools if tool.name == "discover_os_only"),
            None
        )
        app_tool = next(
            (tool for tool in self._mcp_tools if tool.name == "discover_applications"),
            None
        )
        
        if not os_tool or not app_tool:
            logger.warning(
                f"Individual discovery tools not found. "
                f"Available: {[t.name for t in self._mcp_tools]}"
            )
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[],
                processes=[],
                applications=[],
                os_info=None,
                discovery_time=datetime.now()
            )
        
        # Prepare tool arguments
        tool_args = {
            "host": resource.host,
        }
        
        # Add SSH credentials if available
        if hasattr(resource, 'ssh_user') and resource.ssh_user:
            tool_args["ssh_user"] = resource.ssh_user
        if hasattr(resource, 'ssh_password') and resource.ssh_password:
            tool_args["ssh_password"] = resource.ssh_password
        if hasattr(resource, 'ssh_key_path') and resource.ssh_key_path:
            tool_args["ssh_key_path"] = resource.ssh_key_path
        
        try:
            import json
            
            # Step 1: Discover OS
            logger.info(f"Calling discover_os_only tool for {resource.host}")
            os_result_output = await os_tool.run(input=tool_args)
            
            # Parse OS result
            if isinstance(os_result_output.result, str):
                os_result = json.loads(os_result_output.result)
            else:
                os_result = os_result_output.result
            
            logger.debug(f"OS discovery result: {os_result}")
            
            # Step 2: Discover Applications
            logger.info(f"Calling discover_applications tool for {resource.host}")
            app_result_output = await app_tool.run(input=tool_args)
            
            # Parse application result
            if isinstance(app_result_output.result, str):
                app_result = json.loads(app_result_output.result)
            else:
                app_result = app_result_output.result

            # MCP responses can be either:
            # 1) {"ok": true, ...payload fields...}
            # 2) {"ok": true, "data": {...payload fields...}}
            # Normalize both shapes so downstream parsing is consistent.
            app_payload = app_result.get("data") if isinstance(app_result.get("data"), dict) else app_result
            os_payload = os_result.get("data") if isinstance(os_result.get("data"), dict) else os_result
            
            # DEBUG: Log full application discovery response
            logger.info("=" * 60)
            logger.info("APPLICATION DISCOVERY RESPONSE")
            logger.info("=" * 60)
            logger.info(f"Full response: {json.dumps(app_result, indent=2)[:1000]}")
            logger.info(f"Response keys: {list(app_result.keys())}")
            logger.info(f"Normalized payload keys: {list(app_payload.keys())}")
            logger.info(f"Applications key exists: {'applications' in app_payload}")
            logger.info(f"Ports key exists: {'ports' in app_payload}")
            logger.info(f"Processes key exists: {'processes' in app_payload}")
            if 'applications' in app_payload:
                logger.info(f"Applications count: {len(app_payload.get('applications', []))}")
            if 'ports' in app_payload:
                logger.info(f"Ports count: {len(app_payload.get('ports', []))}")
            if 'processes' in app_payload:
                logger.info(f"Processes count: {len(app_payload.get('processes', []))}")
            logger.info("=" * 60)
            
            # Check for success
            os_success = os_result.get("success") or os_result.get("ok")
            app_success = app_result.get("success") or app_result.get("ok")
            
            if not os_success or not app_success:
                error_msg = os_result.get('error') or app_result.get('error', 'Unknown error')
                logger.error(f"Discovery failed: {error_msg}")
                return WorkloadDiscoveryResult(
                    host=resource.host,
                    ports=[],
                    processes=[],
                    applications=[],
                    os_info=None,
                    discovery_time=datetime.now()
                )
            
            # Extract data from both results
            os_data = os_payload
            applications = app_payload.get("applications") or []

            # Prefer explicit ports/processes from tool payload when present.
            ports = app_payload.get("ports") or []
            processes = app_payload.get("processes") or []

            # Backward compatibility: older tool responses did not expose
            # ports/processes at top level. Derive them from applications.
            if not ports or not processes:
                extracted_ports = []
                extracted_processes = []

                for app in applications:
                    if not isinstance(app, dict):
                        continue

                    # Extract network bindings (ports)
                    if "network_bindings" in app and app["network_bindings"]:
                        for binding in app["network_bindings"]:
                            port_info = {
                                "port": binding.get("port"),
                                "protocol": binding.get("protocol", "tcp"),
                                "service": app.get("name"),  # Use app name as service
                                "state": binding.get("state") or "open",  # Ensure not None
                                "banner": None
                            }
                            extracted_ports.append(port_info)

                    # Extract process info
                    if "process_info" in app and app["process_info"]:
                        proc_info = app["process_info"]
                        if proc_info.get("pid") is not None:
                            process = {
                                "pid": proc_info.get("pid"),
                                "name": app.get("name"),  # Use app name
                                "cmdline": proc_info.get("command", ""),
                                "user": proc_info.get("user", "unknown"),
                                "cpu_percent": None,
                                "memory_mb": None
                            }
                            extracted_processes.append(process)

                if not ports:
                    ports = extracted_ports
                if not processes:
                    processes = extracted_processes

            logger.info(f"Extracted {len(ports)} ports and {len(processes)} processes from {len(applications)} applications")
            
            # Combine results
            logger.info(f"Discovery completed successfully for {resource.host}")
            logger.info(f"Found {len(applications)} applications")
            
            # Helper function to convert confidence string to float
            def convert_confidence(conf):
                """Convert confidence string to float (0-1)."""
                if isinstance(conf, (int, float)):
                    return float(conf)
                conf_map = {
                    "high": 0.9,
                    "medium": 0.7,
                    "low": 0.5,
                    "uncertain": 0.3
                }
                return conf_map.get(str(conf).lower(), 0.5)
            
            # Convert applications, fixing confidence field
            converted_apps = []
            for app in applications:
                if isinstance(app, dict):
                    # Convert confidence from string to float
                    app_copy = app.copy()
                    if "confidence" in app_copy:
                        app_copy["confidence"] = convert_confidence(app_copy["confidence"])
                    converted_apps.append(ApplicationDetection(**app_copy))
                else:
                    converted_apps.append(app)
            
            # ============================================================
            # LLM-BASED AGGREGATION
            # ============================================================
            # Use LLM aggregator to intelligently correlate discovery data
            logger.info("=" * 60)
            logger.info("ATTEMPTING LLM-BASED AGGREGATION")
            logger.info("=" * 60)
            
            try:
                # Import LLM aggregator from agents (correct location)
                from agents.llm_aggregator import LLMAggregator
                
                # Create aggregator
                aggregator = LLMAggregator(llm_model=self.llm_model)
                
                # Prepare data for aggregation
                ports_dict = [p if isinstance(p, dict) else p.model_dump() for p in ports]
                processes_dict = [p if isinstance(p, dict) else p.model_dump() for p in processes]
                apps_dict = [a if isinstance(a, dict) else a.model_dump() for a in converted_apps]
                
                logger.info(f"Calling LLM aggregator with {len(ports_dict)} ports, "
                          f"{len(processes_dict)} processes, {len(apps_dict)} applications")
                
                # Call LLM aggregator
                aggregated = await aggregator.aggregate(
                    ports=ports_dict,
                    processes=processes_dict,
                    applications=apps_dict,
                    os_info=os_data
                )
                
                logger.info(f"✓ LLM aggregation successful (method: {aggregated.get('aggregation_method')})")
                logger.info(f"  Correlations found: {len(aggregated.get('correlations', []))}")
                logger.info(f"  Dependencies found: {len(aggregated.get('dependencies', []))}")
                logger.info(f"  LLM insights: {len(aggregated.get('llm_insights', []))}")
                
                # Log insights
                for insight in aggregated.get('llm_insights', [])[:3]:
                    logger.info(f"  💡 {insight}")
                
                # Use enhanced applications from aggregator
                enhanced_apps = aggregated.get('applications', apps_dict)
                
                # Convert enhanced apps back to ApplicationDetection objects
                final_apps = []
                for app in enhanced_apps:
                    if isinstance(app, dict):
                        app_copy = app.copy()
                        if "confidence" in app_copy:
                            app_copy["confidence"] = convert_confidence(app_copy["confidence"])
                        final_apps.append(ApplicationDetection(**app_copy))
                    else:
                        final_apps.append(app)
                
                logger.info(f"✓ Using LLM-enhanced applications ({len(final_apps)} total)")
                
            except Exception as e:
                logger.warning(f"✗ LLM aggregation failed: {e}")
                logger.warning("  Falling back to deterministic aggregation")
                final_apps = converted_apps
            
            # Convert to WorkloadDiscoveryResult
            # Helper function to clean port dictionaries
            def clean_port_dict(port_dict):
                """Ensure port dict has valid values for PortInfo model."""
                cleaned = port_dict.copy()
                # Ensure state is never None
                if cleaned.get("state") is None:
                    cleaned["state"] = "open"
                return cleaned
            
            # Helper function to clean process dictionaries
            def clean_process_dict(proc_dict):
                """Ensure process dict has valid values for ProcessInfo model."""
                cleaned = proc_dict.copy()
                # Ensure required fields are present
                if "user" not in cleaned or cleaned["user"] is None:
                    cleaned["user"] = "unknown"
                if "cmdline" not in cleaned or cleaned["cmdline"] is None:
                    cleaned["cmdline"] = ""
                return cleaned
            
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[
                    PortInfo(**clean_port_dict(port)) if isinstance(port, dict) else port
                    for port in ports
                ],
                processes=[
                    ProcessInfo(**clean_process_dict(proc)) if isinstance(proc, dict) else proc
                    for proc in processes
                ],
                applications=final_apps,
                os_info=os_data,  # Preserve OS information from discover_os_only
                discovery_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Discovery execution failed: {e}", exc_info=True)
            # Return empty result on failure
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[],
                processes=[],
                applications=[],
                os_info=None,
                discovery_time=datetime.now()
            )
    
    async def _execute_raw_data_discovery(
        self,
        resource: ResourceInfo,
        plan: DiscoveryPlan
    ) -> WorkloadDiscoveryResult:
        """Execute discovery using raw data collection (fallback strategy).
        
        Args:
            resource: Resource information
            plan: Discovery plan
        
        Returns:
            WorkloadDiscoveryResult
        """
        # Find the tool dynamically
        raw_data_tool = next(
            (tool for tool in self._mcp_tools if tool.name == "get_raw_server_data"),
            None
        )
        
        if not raw_data_tool:
            raise Exception("get_raw_server_data tool not found")
        
        # Prepare arguments
        tool_args = {
            "host": resource.host,
            "collect_processes": plan.scan_processes,
            "collect_ports": plan.scan_ports,
            "collect_configs": False,
            "collect_packages": False,
            "collect_services": False
        }
        
        # Add SSH credentials
        if hasattr(resource, 'ssh_user') and resource.ssh_user:
            tool_args["ssh_user"] = resource.ssh_user
        if hasattr(resource, 'ssh_password') and resource.ssh_password:
            tool_args["ssh_password"] = resource.ssh_password
        if hasattr(resource, 'ssh_key_path') and resource.ssh_key_path:
            tool_args["ssh_key_path"] = resource.ssh_key_path
        
        logger.info(f"Calling get_raw_server_data for {resource.host}")
        result_output = await raw_data_tool.run(input=tool_args)
        
        # Parse result
        import json
        if isinstance(result_output.result, str):
            result = json.loads(result_output.result)
        else:
            result = result_output.result
        
        # Check success
        if not result.get("success") and not result.get("ok"):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Raw data collection failed: {error_msg}")
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[],
                processes=[],
                applications=[],
                os_info=None,
                discovery_time=datetime.now()
            )
        
        # Extract raw data
        raw_data = result.get("data", {})
        
        # Extract OS info if available
        os_info = raw_data.get("os_info")
        
        # TODO: Use LLM to analyze raw data and detect applications
        # For now, return basic structure
        logger.info(f"Raw data collected for {resource.host}")
        logger.warning("LLM-based analysis not yet implemented, returning empty applications")
        logger.info(f"✓ Raw data collection successful - returning result")
        
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],  # TODO: Parse from raw data
            processes=[],  # TODO: Parse from raw data
            applications=[],  # TODO: LLM-based detection
            os_info=os_info,  # Preserve OS information from raw data
            discovery_time=datetime.now()
        )


# Backward compatibility alias
DiscoveryAgent = BeeAIDiscoveryAgent

# Made with Bob
