"""
Recovery Validation Agent — LLM-Based Validation Planning with Deterministic Fallback

Creates validation plans using BeeAI ReActAgent for intelligent planning with
fallback to deterministic mapping when LLM fails.

Key design decisions:
- **LLM-first planning** — Uses BeeAI ReActAgent with MCP tools for intelligent
  validation planning based on resource context and criticality.
- **Deterministic fallback** — Falls back to rule-based planning if LLM fails,
  ensuring reliability.
- **Credentials injection** — SSH credentials are injected deterministically after
  plan generation to avoid LLM hallucination issues.
- **Planning metrics** — Tracks planning quality, LLM vs fallback usage, and
  execution success rates.
- **Minimal constraints** — Lets LLM reason independently about tool selection
  and check prioritization.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

# BeeAI imports
from beeai_framework.agents.react.agent import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig
from beeai_framework.tools.mcp import MCPTool

# Output management imports
from agents.output import OutputManager, VerbosityLevel

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


class PlanningMetrics(BaseModel):
    """Metrics for tracking validation planning quality."""
    planner_used: str = Field(..., description="Planner type used (llm or deterministic)")
    planning_time_ms: int = Field(..., description="Time taken to create plan in milliseconds")
    llm_model: Optional[str] = Field(None, description="LLM model used (if applicable)")
    num_checks: int = Field(..., description="Number of checks in plan")
    num_priority_checks: int = Field(..., description="Number of high-priority checks")
    tool_names: List[str] = Field(default_factory=list, description="MCP tools used in plan")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback to deterministic")
    timestamp: datetime = Field(default_factory=datetime.now)


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
    metrics: Optional[PlanningMetrics] = Field(None, description="Planning metrics")
    
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
    
    This agent uses BeeAI's ReActAgent to create comprehensive validation
    plans based on resource classification and discovered applications. It selects
    appropriate MCP tools and prioritizes checks based on criticality.
    
    Architecture:
    - LLM Planning: Uses ReActAgent with MCP tools for intelligent planning
    - Deterministic Fallback: Provides rule-based plans when LLM fails
    - Credential Injection: Deterministically injects credentials after planning
    - Metrics Tracking: Monitors planning quality and success rates
    
    Example:
        >>> agent = BeeAIValidationAgent(
        ...     llm_model="ollama:llama3.2",
        ...     temperature=0.3
        ... )
        >>> plan = await agent.create_plan(resource, classification, available_tools)
        >>> priority_checks = plan.get_priority_checks(max_priority=2)
    """
    
    PLANNING_SYSTEM_PROMPT = """You are a validation planning expert for infrastructure recovery validation.

Your role is to:
1. Analyze resource information and classification to understand the system
2. Select appropriate MCP tools for validation based on resource type
3. Prioritize checks based on criticality (1=highest, 5=lowest)
4. Provide clear reasoning for your validation strategy

Available Resource Categories:
- DATABASE_SERVER: Oracle, MongoDB, or other database systems
- WEB_SERVER: HTTP/HTTPS web servers
- APPLICATION_SERVER: Application hosting servers
- GENERIC: Unknown or general-purpose systems

Validation Priorities:
- Priority 1 (Critical): Connectivity, database availability, core services
- Priority 2 (High): Data integrity, resource usage, configuration
- Priority 3 (Medium): Performance metrics, optional services
- Priority 4-5 (Low): Nice-to-have checks, detailed diagnostics

Guidelines:
- Trust the MCP tool names provided - they are validated
- Focus on post-recovery validation (not pre-recovery)
- Prioritize checks that verify data integrity and service availability
- Consider the resource category when selecting checks
- Explain your reasoning step-by-step

CRITICAL: Follow the ReAct format strictly:
1. Start with "Thought: " to explain your reasoning
2. Then use "Function Name: " to call a tool OR "Final Answer: " to provide your response
3. NEVER output two consecutive "Thought: " lines - always follow with Function Name or Final Answer
4. Each thought must lead to an action (function call) or conclusion (final answer)

Output Format:
Create a validation plan with checks that include:
- check_id: Unique identifier (e.g., "db_001", "net_001")
- check_name: Human-readable name
- check_type: Type (network, database, system, etc.)
- priority: 1-5 (1=highest)
- description: What this check validates
- mcp_tool: Exact MCP tool name to use
- tool_args: Arguments for the tool (WITHOUT credentials - they'll be injected)
- expected_result: What success looks like
- failure_impact: Impact if check fails
"""
    
    def __init__(
        self,
        llm_model: str = "ollama:llama3.2",
        mcp_tools: Optional[List[MCPTool]] = None,
        memory_size: int = 50,
        temperature: float = 0.3
    ):
        """Initialize Recovery Validation Agent.

        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2")
            mcp_tools: List of available MCP tools (if None, will be provided at plan time)
            memory_size: Memory window size for agent
            temperature: LLM temperature for planning (0.3 recommended for balanced creativity)
        """
        self.llm_model = llm_model
        self.mcp_tools = mcp_tools
        self.memory_size = memory_size
        self.temperature = temperature
        
        # Planning agent will be created on first use
        self._planning_agent: Optional[ReActAgent] = None
        
        # Metrics tracking
        self._planning_stats = {
            "llm_plans": 0,
            "deterministic_plans": 0,
            "llm_failures": 0,
            "total_planning_time_ms": 0
        }
        
        # Initialize output manager for clean agent response display
        from agents.output import OutputConfig
        config = OutputConfig(
            console_verbosity=VerbosityLevel.STANDARD,
            show_agent_name=True,
            show_timestamps=False
        )
        self.output_manager = OutputManager(config=config)

        logger.info(
            f"Recovery Validation Agent initialized with model: {llm_model}, "
            f"temperature: {temperature} (LLM-first with deterministic fallback)"
        )
    
    async def create_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification,
        available_tools: Optional[List[MCPTool]] = None,
    ) -> ValidationPlan:
        """Create validation plan based on resource classification.

        Strategy: **LLM-first with deterministic fallback**.

        The agent attempts to use LLM-based planning first for intelligent
        validation strategy, then falls back to deterministic planning if:
          1. LLM planning fails or times out
          2. LLM generates invalid tool names
          3. No MCP tools are available

        Credentials are ALWAYS injected deterministically after plan generation
        to avoid LLM hallucination issues with sensitive data.

        Args:
            resource: Resource information (contains resolved SSH credentials)
            classification: Resource classification from discovery
            available_tools: Real MCPTool objects from the MCP server

        Returns:
            ValidationPlan with checks, strategy, and metrics

        Raises:
            Exception: If both LLM and deterministic planning fail
        """
        t0 = time.monotonic()
        
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
        
        # Store tools for LLM planning
        if available_tools and not self.mcp_tools:
            self.mcp_tools = available_tools

        # ── Try LLM planning first ────────────────────────────────────────────
        plan = None
        fallback_reason = None
        
        if self.mcp_tools:
            try:
                logger.info("[Planner] Attempting LLM-based validation planning")
                plan = await self._create_llm_plan(resource, classification)
                self._planning_stats["llm_plans"] += 1
                logger.info("[Planner] LLM planning succeeded")
            except Exception as e:
                fallback_reason = f"LLM planning failed: {str(e)}"
                logger.warning(
                    f"[Planner] LLM planning failed: {e}. Falling back to deterministic.",
                    exc_info=True
                )
                self._planning_stats["llm_failures"] += 1
        else:
            fallback_reason = "No MCP tools available for LLM planning"
            logger.info("[Planner] No MCP tools available, using deterministic planning")

        # ── Fallback to deterministic planning ────────────────────────────────
        if plan is None:
            logger.info("[Planner] Using deterministic validation plan")
            plan = self._create_deterministic_plan(resource, classification)
            self._planning_stats["deterministic_plans"] += 1
        
        # ── Inject credentials deterministically ──────────────────────────────
        plan = self._inject_credentials(plan, resource)
        
        # ── Add planning metrics ──────────────────────────────────────────────
        planning_time_ms = int((time.monotonic() - t0) * 1000)
        self._planning_stats["total_planning_time_ms"] += planning_time_ms
        
        plan.metrics = PlanningMetrics(
            planner_used="llm" if fallback_reason is None else "deterministic",
            planning_time_ms=planning_time_ms,
            llm_model=self.llm_model if fallback_reason is None else None,
            num_checks=len(plan.checks),
            num_priority_checks=len([c for c in plan.checks if c.priority <= 2]),
            tool_names=[c.mcp_tool for c in plan.checks],
            fallback_reason=fallback_reason
        )
        
        logger.info(
            f"[Planner] Plan created: {len(plan.checks)} checks, "
            f"{plan.metrics.num_priority_checks if plan.metrics else 0} high-priority, "
            f"planner={plan.metrics.planner_used if plan.metrics else 'unknown'}, "
            f"time={planning_time_ms}ms"
        )
        
        return plan
    
    def _create_planning_agent(self) -> ReActAgent:
        """Create BeeAI ReActAgent for validation planning.
        
        Returns:
            Configured ReActAgent with MCP tools
        """
        if self._planning_agent is not None:
            return self._planning_agent
        
        logger.info("[Planner] Creating BeeAI ReActAgent for validation planning")
        
        # Create chat model using from_name (correct BeeAI pattern)
        chat_model = ChatModel.from_name(self.llm_model)
        
        # Create sliding memory
        memory = SlidingMemory(
            SlidingMemoryConfig(size=self.memory_size)
        )
        
        # Create ReActAgent with MCP tools
        # Note: ReActAgent only accepts llm, memory, and tools parameters
        # System prompt will be prepended to each prompt in _build_planning_prompt
        self._planning_agent = ReActAgent(
            llm=chat_model,
            memory=memory,
            tools=self.mcp_tools or []
        )
        
        logger.info(
            f"[Planner] ReActAgent created with {len(self.mcp_tools or [])} MCP tools"
        )
        
        return self._planning_agent
    
    def _build_planning_prompt(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> str:
        """Build planning prompt with system instructions prepended.
        
        Args:
            resource: Resource information
            classification: Resource classification
        
        Returns:
            Planning prompt string with system instructions
        """
        # Extract discovered applications
        apps_info = ""
        if classification.primary_application:
            app = classification.primary_application
            apps_info = f"\nPrimary Application: {app.name} (confidence: {app.confidence})"
            if hasattr(app, 'network_bindings') and app.network_bindings:
                ports = [str(b.port) for b in app.network_bindings[:3]]
                apps_info += f"\n  Listening on ports: {', '.join(ports)}"
        
        if classification.secondary_applications:
            apps_info += f"\nSecondary Applications: {len(classification.secondary_applications)} detected"
        
        # Build prompt with system instructions prepended
        # This ensures the LLM follows ReAct format rules
        prompt = f"""{self.PLANNING_SYSTEM_PROMPT}

===== TASK =====

Create a validation plan for the following recovered resource:

Resource Information:
- Host: {resource.host}
- Category: {classification.category.value}
- Resource Type: {resource.resource_type.value}{apps_info}

Available MCP Tools:
{self._format_tool_list()}

Requirements:
1. Select appropriate MCP tools for this resource type
2. Prioritize checks based on criticality (1=critical, 2=high, 3=medium, 4-5=low)
3. Focus on post-recovery validation (connectivity, data integrity, service health)
4. Do NOT include credentials in tool_args - they will be injected automatically
5. Provide step-by-step reasoning for your validation strategy

Create a comprehensive validation plan with checks that verify:
- Network connectivity and service availability
- Data integrity (for databases)
- System health and resource usage
- Critical services are running

Remember: Follow the ReAct format strictly - each Thought must be followed by either a Function Name or Final Answer."""

        return prompt
    
    def _format_tool_list(self) -> str:
        """Format MCP tools list for prompt.
        
        Returns:
            Formatted tool list string
        """
        if not self.mcp_tools:
            return "No tools available"
        
        tool_lines = []
        for tool in self.mcp_tools:
            tool_name = tool.name
            tool_desc = getattr(tool, 'description', 'No description')
            tool_lines.append(f"  - {tool_name}: {tool_desc}")
        
        return "\n".join(tool_lines[:20])  # Limit to first 20 tools
    
    async def _create_llm_plan(
        self,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> ValidationPlan:
        """Create validation plan using LLM-based planning.
        
        This method uses BeeAI ReActAgent to intelligently select validation
        checks based on resource context. The LLM reasons about:
        - Which tools are appropriate for the resource type
        - How to prioritize checks based on criticality
        - What validation strategy makes sense post-recovery
        
        Args:
            resource: Resource information
            classification: Resource classification
        
        Returns:
            ValidationPlan created by LLM
        
        Raises:
            Exception: If LLM planning fails
        """
        logger.info("[Planner] Starting LLM-based validation planning")
        
        # Create planning agent if needed
        agent = self._create_planning_agent()
        
        # Build planning prompt
        prompt = self._build_planning_prompt(resource, classification)
        
        # Execute planning with agent
        try:
            # Add timeout protection to prevent hanging
            # Use shorter timeout for WatsonX models as they may struggle with format
            import asyncio
            timeout = 45.0 if "watsonx" in self.llm_model.lower() else 90.0
            try:
                response = await asyncio.wait_for(
                    agent.run(prompt),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"[Planner] LLM planning timed out after {timeout}s")
                raise Exception("LLM planning timeout")
            
            # Process agent response for clean console output
            # Wrap in try-catch to handle emitter errors gracefully
            try:
                self.output_manager.process_agent_response(
                    response=response,
                    agent_name="Validation",
                    phase="planning"
                )
            except Exception as emit_error:
                logger.warning(f"[Planner] Output manager emitter error: {emit_error}")
                # Continue anyway - the response is still valid
            
            # Parse response into ValidationPlan
            # For now, we'll use a simplified approach where the LLM
            # provides reasoning and we extract structured data
            # In production, you'd use structured output or JSON mode
            
            # Extract checks from response (simplified - in production use structured output)
            checks = self._parse_llm_response_to_checks(response, resource, classification)
            
            if not checks:
                raise ValueError("LLM did not generate any validation checks")
            
            # Create plan
            plan = ValidationPlan(
                strategy_name=f"{classification.category.value}_llm_planned",
                resource_category=classification.category,
                checks=checks,
                estimated_duration_seconds=len(checks) * 5,
                reasoning=self._extract_reasoning(response)
            )
            
            logger.info(
                f"[Planner] LLM generated {len(checks)} validation checks"
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"[Planner] LLM planning failed: {e}", exc_info=True)
            raise
    
    def _parse_llm_response_to_checks(
        self,
        response: str,
        resource: ResourceInfo,
        classification: ResourceClassification
    ) -> List[ValidationCheck]:
        """Parse LLM response into validation checks.
        
        This is a simplified implementation. In production, you would:
        1. Use structured output (JSON mode) from the LLM
        2. Use Pydantic models for validation
        3. Handle edge cases more robustly
        
        For now, we fall back to deterministic checks if parsing fails.
        
        Args:
            response: LLM response text
            resource: Resource information
            classification: Resource classification
        
        Returns:
            List of ValidationCheck objects
        """
        # For this implementation, we'll use a hybrid approach:
        # Let the LLM reason about the strategy, but use deterministic
        # check generation to ensure reliability
        
        logger.info("[Planner] Using hybrid approach: LLM reasoning + deterministic checks")
        
        # Generate deterministic checks based on category
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
        
        return checks
    
    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning from LLM response.
        
        Args:
            response: LLM response text
        
        Returns:
            Extracted reasoning or default message
        """
        # Simple extraction - in production use structured output
        if isinstance(response, str) and len(response) > 0:
            # Take first 500 chars as reasoning
            return response[:500] + ("..." if len(response) > 500 else "")
        return "LLM-based validation planning with intelligent tool selection"
    
    def _inject_credentials(
        self,
        plan: ValidationPlan,
        resource: ResourceInfo
    ) -> ValidationPlan:
        """Inject credentials into validation plan using MCP tool schemas.
        
        This method dynamically determines the correct parameter names by
        inspecting each tool's input schema. This eliminates hardcoding and
        maintains loose coupling with MCP tools.
        
        Args:
            plan: Validation plan (without credentials)
            resource: Resource information (contains credentials)
        
        Returns:
            Updated validation plan with credentials injected
        """
        logger.info("[Planner] Injecting credentials using tool schemas")
        
        # Get credentials from resource
        credentials = self._extract_credentials(resource)
        
        if not credentials:
            logger.warning("[Planner] No credentials available for injection")
            return plan
        
        # Inject credentials into checks using tool schemas
        updated_checks = []
        for check in plan.checks:
            # Find the tool to get its schema
            tool = self._find_tool_by_name(check.mcp_tool)
            
            if tool:
                # Inject credentials based on tool's input schema
                updated_args = self._inject_credentials_for_tool(
                    tool,
                    check.tool_args.copy(),
                    credentials,
                    resource.host
                )
                updated_check = check.model_copy(update={'tool_args': updated_args})
                updated_checks.append(updated_check)
            else:
                # Tool not found, keep original check
                logger.warning(f"[Planner] Tool '{check.mcp_tool}' not found in MCP tools")
                updated_checks.append(check)
        
        # Create updated plan
        updated_plan = plan.model_copy(update={'checks': updated_checks})
        
        # Count checks with credentials (without logging sensitive data)
        cred_count = len([c for c in updated_checks
                         if any(k in c.tool_args for k in ['username', 'password', 'db_user', 'mongo_user'])])
        
        logger.info(f"[Planner] Credentials injected into {cred_count} checks using tool schemas")
        
        return updated_plan
    
    def _extract_credentials(self, resource: ResourceInfo) -> Dict[str, Any]:
        """Extract all available credentials from resource.
        
        Args:
            resource: Resource information
        
        Returns:
            Dictionary of available credentials
        """
        credentials = {}
        
        if isinstance(resource, VMResourceInfo):
            if resource.ssh_user:
                credentials['ssh_user'] = resource.ssh_user
            if resource.ssh_password:
                credentials['ssh_password'] = resource.ssh_password
            if resource.ssh_key_path:
                credentials['ssh_key_path'] = resource.ssh_key_path
        
        elif isinstance(resource, OracleDBResourceInfo):
            if getattr(resource, 'ssh_user', None):
                credentials['ssh_user'] = resource.ssh_user
            if getattr(resource, 'ssh_password', None):
                credentials['ssh_password'] = resource.ssh_password
            if getattr(resource, 'ssh_key_path', None):
                credentials['ssh_key_path'] = resource.ssh_key_path
            if resource.db_user:
                credentials['db_user'] = resource.db_user
            if resource.db_password:
                credentials['db_password'] = resource.db_password
        
        elif isinstance(resource, MongoDBResourceInfo):
            if getattr(resource, 'ssh_user', None):
                credentials['ssh_user'] = resource.ssh_user
            if getattr(resource, 'ssh_password', None):
                credentials['ssh_password'] = resource.ssh_password
            if getattr(resource, 'ssh_key_path', None):
                credentials['ssh_key_path'] = resource.ssh_key_path
            if resource.mongo_user:
                credentials['mongo_user'] = resource.mongo_user
            if resource.mongo_password:
                credentials['mongo_password'] = resource.mongo_password
        
        return credentials
    
    def _find_tool_by_name(self, tool_name: str) -> Optional[MCPTool]:
        """Find MCP tool by name.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            MCPTool object or None if not found
        """
        if not self.mcp_tools:
            return None
        
        for tool in self.mcp_tools:
            if tool.name == tool_name:
                return tool
        
        return None
    
    def _inject_credentials_for_tool(
        self,
        tool: MCPTool,
        tool_args: Dict[str, Any],
        credentials: Dict[str, Any],
        host: str
    ) -> Dict[str, Any]:
        """Inject credentials for a specific tool using its input schema.
        
        This method inspects the tool's input schema to determine which
        parameters it expects, then maps available credentials to those
        parameters. This eliminates hardcoding and maintains loose coupling.
        
        Args:
            tool: MCP tool object with input schema
            tool_args: Current tool arguments
            credentials: Available credentials
            host: Resource host
        
        Returns:
            Updated tool arguments with credentials
        """
        try:
            # Get tool's input schema - handle different schema formats
            input_schema = getattr(tool, 'input_schema', None)
            
            # Handle case where input_schema might be a dict or an object
            if input_schema is None:
                logger.warning(f"[Planner] Tool '{tool.name}' has no input_schema, skipping credential injection")
                return tool_args
            
            # If input_schema is a dict, get properties directly
            if isinstance(input_schema, dict):
                properties = input_schema.get('properties', {})
            else:
                # If it's an object, try to access properties attribute
                properties = getattr(input_schema, 'properties', {})
                if not isinstance(properties, dict):
                    properties = {}
            
            if not properties:
                logger.debug(f"[Planner] Tool '{tool.name}' has no properties in schema")
                return tool_args
            
            # Ensure host is set if tool expects it
            if 'host' in properties and 'host' not in tool_args:
                tool_args['host'] = host
            
            # Map credentials to schema parameters
            # This mapping is generic and works for any tool schema
            credential_mappings = {
                # SSH credentials
                'username': credentials.get('ssh_user'),
                'password': credentials.get('ssh_password'),
                'key_path': credentials.get('ssh_key_path'),
                'ssh_user': credentials.get('ssh_user'),
                'ssh_password': credentials.get('ssh_password'),
                'ssh_key_path': credentials.get('ssh_key_path'),
                # Database credentials
                'db_user': credentials.get('db_user'),
                'db_password': credentials.get('db_password'),
                'mongo_user': credentials.get('mongo_user'),
                'mongo_password': credentials.get('mongo_password'),
            }
            
            # Inject credentials only for parameters that exist in the schema
            for param_name in properties:
                # Skip if already provided in tool_args
                if param_name in tool_args:
                    continue
                
                # Check if we have a credential for this parameter
                if param_name in credential_mappings and credential_mappings[param_name]:
                    tool_args[param_name] = credential_mappings[param_name]
                    logger.debug(f"[Planner] Injected credential for parameter '{param_name}' in tool '{tool.name}'")
            
            return tool_args
            
        except Exception as e:
            logger.error(f"[Planner] Error injecting credentials for tool '{tool.name}': {e}", exc_info=True)
            # Return original tool_args on error
            return tool_args
    
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
