"""
BeeAI-based Validation Orchestrator

This module provides a BeeAI-powered orchestrator that coordinates the complete
validation workflow, integrating Discovery, Validation, and Evaluation agents.

Key Features:
- Coordinates multi-agent workflow
- Manages state and context across agents
- Handles MCP tool integration
- Provides comprehensive error handling
- Supports flexible workflow configuration
"""

import logging
import time
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from pathlib import Path

# Import AgentTracker for structured console output
try:
    from agent_logging.agent_logger import AgentTracker as _AgentTrackerClass
    _TRACKER_AVAILABLE = True
except ImportError:
    _AgentTrackerClass = None  # type: ignore[assignment,misc]
    _TRACKER_AVAILABLE = False

from pydantic import BaseModel, Field

# BeeAI imports
from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig
from beeai_framework.tools.mcp import MCPTool
from mcp.client.stdio import StdioServerParameters, stdio_client

# Local imports
from models import (
    ValidationRequest,
    ResourceValidationResult,
    CheckResult,
    ValidationStatus,
    WorkloadDiscoveryResult,
    ResourceClassification,
    ResourceCategory,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo
)
from classifier import ApplicationClassifier

# Import BeeAI agents
from beeai_agents.discovery_agent import BeeAIDiscoveryAgent
from beeai_agents.validation_agent import BeeAIValidationAgent, ValidationPlan
from beeai_agents.evaluation_agent import BeeAIEvaluationAgent, OverallEvaluation

logger = logging.getLogger(__name__)

# Type aliases
ResourceInfo = Union[VMResourceInfo, OracleDBResourceInfo, MongoDBResourceInfo]


class WorkflowResult(BaseModel):
    """Complete workflow execution result with all phase outputs."""
    request: ValidationRequest
    discovery_result: Optional[WorkloadDiscoveryResult] = None
    classification: Optional[ResourceClassification] = None
    validation_plan: Optional[ValidationPlan] = None
    validation_result: ResourceValidationResult
    evaluation: Optional[OverallEvaluation] = None
    execution_time_seconds: float
    workflow_status: str = Field(..., description="success, partial_success, or failure")
    errors: list[str] = Field(default_factory=list)
    phase_timings: Dict[str, float] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """Tracks workflow execution state."""
    current_phase: str
    completed_phases: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    start_time: float
    phase_start_time: float


class BeeAIValidationOrchestrator:
    """BeeAI-powered orchestrator for complete validation workflow.
    
    This orchestrator coordinates three specialized BeeAI agents:
    1. DiscoveryAgent: Workload discovery and application detection
    2. ValidationAgent: Resource validation with acceptance criteria
    3. EvaluationAgent: Intelligent result evaluation and recommendations
    
    Architecture:
    - Uses BeeAI RequirementAgent for workflow coordination
    - Integrates MCP tools for infrastructure operations
    - Manages state and context across workflow phases
    - Provides comprehensive error handling and recovery
    
    Workflow Phases:
    1. Discovery: Detect workloads and applications
    2. Classification: Categorize resource type
    3. Planning: Create validation plan
    4. Execution: Run validation checks
    5. Evaluation: Assess results and provide recommendations
    
    Example:
        >>> orchestrator = BeeAIValidationOrchestrator(
        ...     mcp_server_path="python/cyberres-mcp",
        ...     llm_model="ollama:llama3.2"
        ... )
        >>> await orchestrator.initialize()
        >>> result = await orchestrator.execute_workflow(request)
    """
    
    def __init__(
        self,
        mcp_server_path: str = "python/cyberres-mcp",
        llm_model: str = "ollama:llama3.2",
        enable_discovery: bool = True,
        enable_ai_evaluation: bool = True,
        memory_size: int = 50
    ):
        """Initialize BeeAI Validation Orchestrator.
        
        Args:
            mcp_server_path: Path to MCP server directory
            llm_model: LLM model identifier
            enable_discovery: Enable workload discovery phase
            enable_ai_evaluation: Enable AI-powered evaluation phase
            memory_size: Size of memory window for agents
        """
        self.mcp_server_path = Path(mcp_server_path)
        self.llm_model = llm_model
        self.enable_discovery = enable_discovery
        self.enable_ai_evaluation = enable_ai_evaluation
        self.memory_size = memory_size
        
        # Components (initialized on first use)
        self._mcp_client = None
        self._mcp_tools: List[MCPTool] = []
        self._coordinator_agent: Optional[RequirementAgent] = None
        self._discovery_agent: Optional[BeeAIDiscoveryAgent] = None
        self._validation_agent: Optional[BeeAIValidationAgent] = None
        self._evaluation_agent: Optional[BeeAIEvaluationAgent] = None
        self._classifier: Optional[ApplicationClassifier] = None
        
        # State tracking
        self._initialized = False
        
        logger.info(
            f"BeeAI Validation Orchestrator created "
            f"(discovery: {enable_discovery}, evaluation: {enable_ai_evaluation})"
        )
    
    async def initialize(self):
        """Initialize orchestrator and all components.
        
        This must be called before executing workflows.
        """
        if self._initialized:
            logger.info("Orchestrator already initialized")
            return
        
        logger.info("Initializing BeeAI Validation Orchestrator...")
        
        try:
            # Initialize MCP client and tools
            await self._initialize_mcp()
            
            # Initialize classifier
            self._classifier = ApplicationClassifier()
            
            # Initialize agents
            if self.enable_discovery:
                self._discovery_agent = BeeAIDiscoveryAgent(
                    llm_model=self.llm_model,
                    mcp_tools=self._mcp_tools,
                    memory_size=self.memory_size
                )
                logger.info("Discovery agent initialized")
            
            self._validation_agent = BeeAIValidationAgent(
                llm_model=self.llm_model,
                memory_size=self.memory_size
            )
            logger.info("Validation agent initialized")
            
            if self.enable_ai_evaluation:
                self._evaluation_agent = BeeAIEvaluationAgent(
                    llm_model=self.llm_model,
                    memory_size=self.memory_size * 2  # Larger memory for evaluation
                )
                logger.info("Evaluation agent initialized")
            
            # Create coordinator agent
            self._coordinator_agent = self._create_coordinator_agent()
            logger.info("Coordinator agent initialized")
            
            self._initialized = True
            logger.info("✓ Orchestrator initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def _initialize_mcp(self):
        """Initialize MCP client and discover tools."""
        logger.info(f"Connecting to MCP server at {self.mcp_server_path}...")

        # Create server parameters — suppress MCP server subprocess logs.
        # LOG_LEVEL=WARNING is read by server.py's logging.basicConfig() call,
        # which suppresses INFO logs from mcp.*, paramiko.*, ssh_utils, etc.
        # Pass through the current process's PATH so uv/python are found.
        #
        # The MCP server subprocess prints a BrokenPipeError traceback to stderr
        # when the client disconnects after the last tool call (normal stdio MCP
        # lifecycle).  server.py main() now catches BrokenPipeError explicitly,
        # so the traceback is suppressed at source.
        import os as _os
        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", str(self.mcp_server_path), "run", "cyberres-mcp"],
            env={
                **_os.environ,           # inherit PATH, HOME, etc.
                "MCP_TRANSPORT": "stdio",
                "PYTHONUNBUFFERED": "1",
                "LOG_LEVEL": "WARNING",  # read by server.py basicConfig
                "LOGURU_LEVEL": "WARNING",
            },
        )
        
        # Connect to MCP server
        self._mcp_client = stdio_client(server_params)
        
        # Discover tools
        tools = await MCPTool.from_client(self._mcp_client)
        self._mcp_tools = tools if tools is not None else []
        logger.info(f"✓ Connected to MCP server, discovered {len(self._mcp_tools)} tools")
        
        # Initialize tool executor
        from beeai_agents.tool_executor import ToolExecutor
        self._tool_executor = ToolExecutor(self._mcp_tools, max_retries=3)
        logger.info("✓ Tool executor initialized")
    
    def _create_coordinator_agent(self) -> RequirementAgent:
        """Create coordinator agent for workflow management.
        
        Returns:
            Configured RequirementAgent for coordination
        """
        logger.info("Creating workflow coordinator agent...")
        
        llm = ChatModel.from_name(self.llm_model)
        memory = SlidingMemory(SlidingMemoryConfig(size=self.memory_size))
        
        coordinator = RequirementAgent(
            llm=llm,
            memory=memory,
            tools=[],  # Coordinator doesn't use tools directly
            name="Workflow Coordinator",
            description="Coordinates multi-agent validation workflow",
            role="Workflow Orchestrator",
            instructions=[
                "Coordinate execution of discovery, validation, and evaluation phases",
                "Manage state and context across workflow phases",
                "Handle errors gracefully and provide recovery strategies",
                "Ensure data flows correctly between agents",
                "Make intelligent decisions about workflow progression"
            ],
            notes=[
                "Discovery phase is optional but recommended",
                "Validation phase is required",
                "Evaluation phase provides actionable insights",
                "Each phase builds on previous phase outputs"
            ]
        )
        
        logger.info("Coordinator agent created")
        return coordinator  # ← was missing; caused NoneType coordinator

    def get_available_mcp_tools(self) -> List[str]:
        """Get list of available MCP tool names.
        
        Returns:
            List of tool names
        """
        if not self._mcp_tools:
            return []
        
        return [tool.name for tool in self._mcp_tools]
    
    def get_discovery_capabilities(self) -> Dict[str, Any]:
        """Get discovery capabilities based on available tools.
        
        Returns:
            Dictionary describing discovery capabilities
        """
        if not self._discovery_agent:
            return {
                "enabled": False,
                "reason": "Discovery agent not initialized"
            }
        
        available_tools = self._discovery_agent.get_available_discovery_tools()
        strategy = self._discovery_agent.get_discovery_strategy()
        
        return {
            "enabled": True,
            "strategy": strategy,
            "available_tools": available_tools,
            "capabilities": {
                "comprehensive_discovery": "discover_workload" in available_tools,
                "os_detection": "discover_os_only" in available_tools,
                "application_detection": "discover_applications" in available_tools,
                "raw_data_collection": "get_raw_server_data" in available_tools
            }
        }
    
    async def execute_workflow(
        self,
        request: ValidationRequest
    ) -> WorkflowResult:
        """Execute complete validation workflow.
        
        Args:
            request: Validation request with resource information
        
        Returns:
            WorkflowResult with all phase outputs and timing
        
        Raises:
            RuntimeError: If orchestrator not initialized
            Exception: If workflow execution fails critically
        """
        if not self._initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        # Initialize workflow state
        state = WorkflowState(
            current_phase="initialization",
            start_time=time.time(),
            phase_start_time=time.time()
        )
        
        phase_timings = {}
        errors = []

        # ── AgentTracker for structured console output ────────────────────────
        wf_tracker = None
        if _TRACKER_AVAILABLE and _AgentTrackerClass is not None:
            wf_tracker = _AgentTrackerClass(
                "Orchestrator", resource=request.resource_info.host
            )
            wf_tracker.start(
                f"Validation workflow for {request.resource_info.host} "
                f"[{request.resource_info.resource_type.value}]"
            )
        
        logger.info(f"Starting validation workflow for {request.resource_info.host}")
        logger.info(f"Resource type: {request.resource_info.resource_type.value}")
        
        try:
            # Phase 1: Workload Discovery (optional)
            discovery_result = None
            classification = None
            
            if self.enable_discovery and request.auto_discover:
                state.current_phase = "discovery"
                state.phase_start_time = time.time()
                
                try:
                    logger.info("=" * 60)
                    logger.info("PHASE 1: Workload Discovery")
                    logger.info("=" * 60)
                    if wf_tracker:
                        wf_tracker.mode(
                            "discovery",
                            description="Scanning ports, processes and applications on the target host"
                        )
                        wf_tracker.info("Phase 1: Workload Discovery — scanning ports, processes, applications")
                    
                    discovery_result = await self._execute_discovery_phase(
                        request.resource_info
                    )
                    
                    phase_timings["discovery"] = time.time() - state.phase_start_time
                    state.completed_phases.append("discovery")
                    
                    # Classify resource based on discovery
                    if discovery_result and self._classifier is not None:
                        logger.info("Classifying resource based on discovery results...")
                        classification = self._classifier.classify(discovery_result)
                        logger.info(
                            f"✓ Resource classified as: {classification.category.value} "
                            f"(confidence: {classification.confidence:.2%})"
                        )
                        if wf_tracker:
                            wf_tracker.thinking(
                                f"Detected {len(discovery_result.applications) if discovery_result else 0} "
                                f"application(s) — classifying resource type..."
                            )
                            wf_tracker.decision(
                                f"Classified as {classification.category.value} "
                                f"(confidence: {classification.confidence:.0%})",
                                confidence=classification.confidence,
                            )
                    
                except Exception as e:
                    error_msg = f"Discovery phase failed: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if wf_tracker:
                        wf_tracker.warning(f"Discovery failed: {e} — continuing with fallback plan")
                    phase_timings["discovery"] = time.time() - state.phase_start_time
            
            # Phase 2: Validation Planning
            state.current_phase = "planning"
            state.phase_start_time = time.time()
            
            logger.info("=" * 60)
            logger.info("PHASE 2: Validation Planning")
            logger.info("=" * 60)
            if wf_tracker:
                wf_tracker.mode(
                    "planning",
                    description="Mapping detected workloads to the right validation checks"
                )
                wf_tracker.info("Phase 2: Validation Planning — building check list")
            
            validation_plan = await self._execute_planning_phase(
                request.resource_info,
                classification
            )
            
            phase_timings["planning"] = time.time() - state.phase_start_time
            state.completed_phases.append("planning")
            
            logger.info(f"✓ Validation plan created with {len(validation_plan.checks)} checks")
            if wf_tracker:
                check_names = ", ".join(c.mcp_tool for c in validation_plan.checks)
                wf_tracker.decision(
                    f"Plan: {len(validation_plan.checks)} checks → {check_names}"
                )
            
            # Phase 3: Validation Execution
            state.current_phase = "execution"
            state.phase_start_time = time.time()
            
            logger.info("=" * 60)
            logger.info("PHASE 3: Validation Execution")
            logger.info("=" * 60)
            if wf_tracker:
                wf_tracker.mode(
                    "validation",
                    description="Running checks and collecting results from the target host"
                )
                wf_tracker.info(f"Phase 3: Executing {len(validation_plan.checks)} validation checks")
            
            validation_result = await self._execute_validation_phase(
                request,
                validation_plan,
                discovery_result
            )
            
            phase_timings["execution"] = time.time() - state.phase_start_time
            state.completed_phases.append("execution")
            
            logger.info(
                f"✓ Validations complete: {validation_result.passed_checks} passed, "
                f"{validation_result.failed_checks} failed, "
                f"{validation_result.warning_checks} warnings"
            )
            if wf_tracker:
                wf_tracker.info(
                    f"Phase 3 done: ✅ {validation_result.passed_checks} passed  "
                    f"❌ {validation_result.failed_checks} failed  "
                    f"⚠️  {validation_result.warning_checks} warnings"
                )
            
            # Phase 4: AI Evaluation (optional)
            evaluation = None
            
            if self.enable_ai_evaluation:
                state.current_phase = "evaluation"
                state.phase_start_time = time.time()
                
                try:
                    logger.info("=" * 60)
                    logger.info("PHASE 4: AI Evaluation")
                    logger.info("=" * 60)
                    if wf_tracker:
                        wf_tracker.mode(
                            "evaluation",
                            description="Analysing results, identifying issues and generating recommendations"
                        )
                        wf_tracker.info("Phase 4: Evaluation — analysing results and generating recommendations")
                    
                    evaluation = await self._execute_evaluation_phase(
                        validation_result,
                        discovery_result,
                        classification
                    )
                    
                    phase_timings["evaluation"] = time.time() - state.phase_start_time
                    state.completed_phases.append("evaluation")
                    
                    logger.info(f"✓ Evaluation complete: {evaluation.overall_health}")
                    logger.info(f"  Critical issues: {len(evaluation.critical_issues)}")
                    logger.info(f"  Recommendations: {len(evaluation.recommendations)}")
                    if wf_tracker:
                        wf_tracker.thinking("Analysing check results, identifying root causes...")
                        wf_tracker.decision(
                            f"Health: {evaluation.overall_health.upper()}  "
                            f"Issues: {len(evaluation.critical_issues)}  "
                            f"Recommendations: {len(evaluation.recommendations)}"
                        )
                    
                except Exception as e:
                    error_msg = f"Evaluation phase failed: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if wf_tracker:
                        wf_tracker.warning(f"Evaluation failed: {e}")
                    phase_timings["evaluation"] = time.time() - state.phase_start_time
            
            # Determine workflow status
            workflow_status = self._determine_workflow_status(
                validation_result,
                errors
            )
            
            total_time = time.time() - state.start_time
            
            # Create workflow result
            result = WorkflowResult(
                request=request,
                discovery_result=discovery_result,
                classification=classification,
                validation_plan=validation_plan,
                validation_result=validation_result,
                evaluation=evaluation,
                execution_time_seconds=total_time,
                workflow_status=workflow_status,
                errors=errors,
                phase_timings=phase_timings
            )
            
            logger.info("=" * 60)
            logger.info(f"WORKFLOW COMPLETE: {workflow_status.upper()}")
            logger.info(f"Total execution time: {total_time:.2f}s")
            logger.info(f"Completed phases: {', '.join(state.completed_phases)}")
            logger.info("=" * 60)
            if wf_tracker:
                wf_tracker.finish(
                    f"Workflow {workflow_status.upper()} — score: {validation_result.score}/100 "
                    f"({total_time:.1f}s)",
                    success=workflow_status in ("success", "partial_success"),
                )
            
            return result
            
        except Exception as e:
            total_time = time.time() - state.start_time
            error_msg = f"Workflow failed critically: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            # Create minimal failure result
            validation_result = ResourceValidationResult(
                resource_type=request.resource_info.resource_type,
                resource_host=request.resource_info.host,
                overall_status=ValidationStatus.ERROR,
                score=0,
                checks=[],
                execution_time_seconds=total_time,
                timestamp=datetime.now()
            )
            
            return WorkflowResult(
                request=request,
                validation_result=validation_result,
                execution_time_seconds=total_time,
                workflow_status="failure",
                errors=errors,
                phase_timings=phase_timings
            )
    
    async def _execute_discovery_phase(
        self,
        resource: ResourceInfo
    ) -> Optional[WorkloadDiscoveryResult]:
        """Execute workload discovery phase.
        
        Args:
            resource: Resource to discover
        
        Returns:
            WorkloadDiscoveryResult or None on failure
        """
        if not self._discovery_agent:
            logger.warning("Discovery agent not initialized")
            return None
        
        try:
            # Use BeeAI discovery agent
            result = await self._discovery_agent.discover(
                resource,
                self._mcp_tools
            )
            
            if result:
                logger.info(f"✓ Discovery successful:")
                logger.info(f"  Ports: {len(result.ports)}")
                logger.info(f"  Processes: {len(result.processes)}")
                logger.info(f"  Applications: {len(result.applications)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Discovery phase failed: {e}", exc_info=True)
            return None
    
    async def _execute_planning_phase(
        self,
        resource: ResourceInfo,
        classification: Optional[ResourceClassification]
    ) -> ValidationPlan:
        """Execute validation planning phase.

        After the plan is created, every check's ``mcp_tool`` is validated
        against the tools actually available on the MCP server.  Any check that
        references a non-existent tool is removed and a warning is logged so the
        problem is immediately visible in the console output.

        Args:
            resource: Resource information
            classification: Optional classification from discovery

        Returns:
            ValidationPlan with checks to execute (all tools verified)
        """
        # Create fallback classification if needed
        if not classification:
            logger.info("No classification available, using fallback")
            classification = ResourceClassification(
                category=ResourceCategory.UNKNOWN,
                confidence=0.5,
                reasoning="No discovery performed",
                recommended_validations=["basic_connectivity", "system_health"]
            )

        # Use BeeAI validation agent for planning.
        # Pass the live MCP tool catalog so the LLM can only pick tools that
        # actually exist on the server — eliminates hallucinated tool names.
        if self._validation_agent is None:
            raise RuntimeError("Validation agent not initialized. Call initialize() first.")
        plan = await self._validation_agent.create_plan(
            resource,
            classification,
            available_tools=self._mcp_tools if self._mcp_tools else None,
        )

        # ── Second-layer defence: verify every tool name exists on the MCP server ──
        # This catches any future regression where a planner emits a wrong tool name.
        available_tool_names: set[str] = {t.name for t in self._mcp_tools}
        if available_tool_names:
            valid_checks = []
            for chk in plan.checks:
                if chk.mcp_tool in available_tool_names:
                    valid_checks.append(chk)
                else:
                    logger.warning(
                        f"[PlanValidator] Dropping check '{chk.check_name}': "
                        f"tool '{chk.mcp_tool}' not found on MCP server. "
                        f"Available tools: {sorted(available_tool_names)}"
                    )
            if len(valid_checks) < len(plan.checks):
                dropped = len(plan.checks) - len(valid_checks)
                logger.warning(
                    f"[PlanValidator] Dropped {dropped} check(s) with unknown tool names. "
                    f"{len(valid_checks)} check(s) remain."
                )
                # Rebuild plan with only valid checks
                plan = plan.model_copy(update={"checks": valid_checks})

        logger.info(f"✓ Validation plan created:")
        logger.info(f"  Total checks: {len(plan.checks)}")
        logger.info(f"  Priority: {plan.priority}")
        logger.info(f"  Estimated time: {plan.estimated_execution_time}s")

        return plan
    
    async def _execute_validation_phase(
        self,
        request: ValidationRequest,
        plan: ValidationPlan,
        discovery_result: Optional[WorkloadDiscoveryResult]
    ) -> ResourceValidationResult:
        """Execute validation checks phase.
        
        Args:
            request: Validation request
            plan: Validation plan with checks
            discovery_result: Optional discovery context
        
        Returns:
            ResourceValidationResult with check outcomes
        """
        start_time = time.time()
        checks = []
        
        # Create tracker for structured, colour-coded console output
        tracker = None
        if _TRACKER_AVAILABLE and _AgentTrackerClass is not None:
            tracker = _AgentTrackerClass("ValidationAgent", resource=request.resource_info.host)

        logger.info(f"Executing {len(plan.checks)} validation checks...")
        if tracker:
            tracker.info(f"Running {len(plan.checks)} checks for {request.resource_info.host}")

        # Execute each check in the plan
        for i, check_def in enumerate(plan.checks, 1):
            try:
                logger.info(f"  [{i}/{len(plan.checks)}] {check_def.check_name}...")
                if tracker:
                    tracker.tool_call(check_def.mcp_tool, check_def.tool_args)

                # Find matching MCP tool
                tool = self._find_mcp_tool(check_def.mcp_tool)

                if not tool:
                    logger.warning(f"    Tool not found: {check_def.mcp_tool}")
                    if tracker:
                        tracker.warning(f"[{i}/{len(plan.checks)}] {check_def.check_name} — tool not found: {check_def.mcp_tool}")
                    checks.append(CheckResult(
                        check_id=check_def.check_id,
                        check_name=check_def.check_name,
                        status=ValidationStatus.ERROR,
                        message=f"MCP tool not found: {check_def.mcp_tool}"
                    ))
                    continue

                # Execute tool with retry logic
                try:
                    tool_result = await self._tool_executor.execute_with_retry(
                        check_def.mcp_tool,
                        check_def.tool_args
                    )

                    # Parse result into CheckResult
                    check_result = self._tool_executor.parse_check_result(
                        tool_result,
                        check_def,
                        expected_value=check_def.expected_result
                    )
                    checks.append(check_result)

                    # Colour-coded result on console via tracker
                    status_val = check_result.status.value
                    msg = check_result.message or status_val
                    if tracker:
                        if check_result.status == ValidationStatus.PASS:
                            tracker.tool_result(
                                check_def.mcp_tool, tool_result,
                                success=True,
                                summary=f"[{i}/{len(plan.checks)}] {check_def.check_name} — ✅ PASS: {msg}"
                            )
                        elif check_result.status == ValidationStatus.WARNING:
                            tracker.tool_result(
                                check_def.mcp_tool, tool_result,
                                success=True,
                                summary=f"[{i}/{len(plan.checks)}] {check_def.check_name} — ⚠️  WARN: {msg}"
                            )
                        else:
                            tracker.tool_result(
                                check_def.mcp_tool, tool_result,
                                success=False,
                                summary=f"[{i}/{len(plan.checks)}] {check_def.check_name} — ❌ FAIL: {msg}"
                            )
                    else:
                        logger.info(f"    ✓ {status_val}: {msg}")

                except Exception as tool_error:
                    logger.error(f"    ✗ Tool execution error: {tool_error}")
                    if tracker:
                        tracker.error(f"[{i}/{len(plan.checks)}] {check_def.check_name} — tool error: {tool_error}")
                    check_result = CheckResult(
                        check_id=check_def.check_id,
                        check_name=check_def.check_name,
                        status=ValidationStatus.ERROR,
                        message=f"Tool execution error: {str(tool_error)}"
                    )
                    checks.append(check_result)

            except Exception as e:
                logger.error(f"    ✗ Check failed: {e}")
                if tracker:
                    tracker.error(f"[{i}/{len(plan.checks)}] {check_def.check_name} — check failed: {e}")
                checks.append(CheckResult(
                    check_id=check_def.check_id,
                    check_name=check_def.check_name,
                    status=ValidationStatus.ERROR,
                    message=f"Check execution failed: {str(e)}"
                ))
        
        # Calculate overall status and score
        overall_status, score = self._calculate_overall_status(checks)
        
        execution_time = time.time() - start_time
        
        return ResourceValidationResult(
            resource_type=request.resource_info.resource_type,
            resource_host=request.resource_info.host,
            overall_status=overall_status,
            score=score,
            checks=checks,
            passed_checks=sum(1 for c in checks if c.status == ValidationStatus.PASS),
            failed_checks=sum(1 for c in checks if c.status == ValidationStatus.FAIL),
            warning_checks=sum(1 for c in checks if c.status == ValidationStatus.WARNING),
            discovery_info=discovery_result.model_dump() if discovery_result else None,
            execution_time_seconds=execution_time,
            timestamp=datetime.now()
        )
    
    async def _execute_evaluation_phase(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification]
    ) -> OverallEvaluation:
        """Execute AI evaluation phase.
        
        Args:
            validation_result: Validation results to evaluate
            discovery_result: Optional discovery context
            classification: Optional classification context
        
        Returns:
            OverallEvaluation with insights and recommendations
        """
        if not self._evaluation_agent:
            raise RuntimeError("Evaluation agent not initialized")
        
        # Use BeeAI evaluation agent
        evaluation = await self._evaluation_agent.evaluate(
            validation_result,
            discovery_result=discovery_result,
            classification=classification
        )
        
        return evaluation
    
    def _find_mcp_tool(self, tool_name: str):
        """Find MCP tool by name.
        
        Args:
            tool_name: Name of the tool to find
        
        Returns:
            MCPTool or None if not found
        """
        if not self._mcp_tools:
            return None
        
        for tool in self._mcp_tools:
            if tool.name == tool_name:
                return tool
        
        return None
    
    def _calculate_overall_status(
        self,
        checks: list[CheckResult]
    ) -> tuple[ValidationStatus, int]:
        """Calculate overall validation status and score.
        
        Args:
            checks: List of check results
        
        Returns:
            Tuple of (overall_status, score)
        """
        if not checks:
            return ValidationStatus.ERROR, 0
        
        passed = sum(1 for c in checks if c.status == ValidationStatus.PASS)
        failed = sum(1 for c in checks if c.status == ValidationStatus.FAIL)
        warnings = sum(1 for c in checks if c.status == ValidationStatus.WARNING)
        errors = sum(1 for c in checks if c.status == ValidationStatus.ERROR)
        
        total = len(checks)
        
        # Calculate score (0-100)
        score = int((passed / total) * 100)
        
        # Adjust for warnings and errors
        score -= (warnings * 5)  # -5 points per warning
        score -= (errors * 10)   # -10 points per error
        score = max(0, min(100, score))  # Clamp to 0-100
        
        # Determine overall status
        if failed > 0 or errors > 0:
            overall_status = ValidationStatus.FAIL
        elif warnings > 0:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASS
        
        return overall_status, score
    
    def _determine_workflow_status(
        self,
        validation_result: ResourceValidationResult,
        errors: list[str]
    ) -> str:
        """Determine overall workflow status.
        
        Args:
            validation_result: Validation results
            errors: List of workflow errors
        
        Returns:
            Status string: success, partial_success, or failure
        """
        if errors:
            if validation_result.overall_status == ValidationStatus.ERROR:
                return "failure"
            else:
                return "partial_success"
        
        if validation_result.overall_status in [ValidationStatus.PASS, ValidationStatus.WARNING]:
            return "success"
        else:
            return "partial_success"
    
    async def cleanup(self):
        """Cleanup resources and close connections."""
        logger.info("Cleaning up orchestrator resources...")
        
        if self._mcp_client:
            try:
                # Close MCP client if needed
                pass
            except Exception as e:
                logger.warning(f"Error closing MCP client: {e}")
        
        self._initialized = False
        logger.info("✓ Cleanup complete")


# Backward compatibility alias
ValidationOrchestrator = BeeAIValidationOrchestrator

# Made with Bob
