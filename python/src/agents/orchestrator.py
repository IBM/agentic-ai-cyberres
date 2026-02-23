#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Workflow orchestrator that coordinates all agents."""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from models import (
    ValidationRequest,
    ResourceValidationResult,
    CheckResult,
    ValidationStatus,
    WorkloadDiscoveryResult,
    ResourceClassification,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo
)
from mcp_client import MCPClient
from mcp_stdio_client import MCPStdioClient
from typing import Union
from classifier import ApplicationClassifier
from agents.base import AgentConfig
from agents.discovery_agent import DiscoveryAgent
from agents.validation_agent import ValidationAgent, ValidationPlan
from agents.evaluation_agent import EvaluationAgent, OverallEvaluation

logger = logging.getLogger(__name__)

# Type alias for resource info
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo


class WorkflowResult(BaseModel):
    """Complete workflow execution result."""
    request: ValidationRequest
    discovery_result: Optional[WorkloadDiscoveryResult] = None
    classification: Optional[ResourceClassification] = None
    validation_plan: Optional[ValidationPlan] = None
    validation_result: ResourceValidationResult
    evaluation: Optional[OverallEvaluation] = None
    execution_time_seconds: float
    workflow_status: str = Field(..., description="success, partial_success, or failure")
    errors: list[str] = Field(default_factory=list)


# Type alias for MCP client (supports both HTTP and stdio)
MCPClientType = Union[MCPClient, MCPStdioClient]


class ValidationOrchestrator:
    """Orchestrates the complete validation workflow."""
    
    def __init__(
        self,
        mcp_client: MCPClientType,
        agent_config: Optional[AgentConfig] = None,
        enable_discovery: bool = True,
        enable_ai_evaluation: bool = True
    ):
        """Initialize orchestrator.
        
        Args:
            mcp_client: Connected MCP client (MCPClient or MCPStdioClient)
            agent_config: Configuration for AI agents
            enable_discovery: Enable workload discovery
            enable_ai_evaluation: Enable AI-powered evaluation
        """
        self.mcp_client = mcp_client
        self.enable_discovery = enable_discovery
        self.enable_ai_evaluation = enable_ai_evaluation
        
        # Initialize components
        self.classifier = ApplicationClassifier()
        
        # Initialize agents
        if enable_discovery:
            self.discovery_agent = DiscoveryAgent(agent_config)
            logger.info("Discovery agent enabled")
        
        self.validation_agent = ValidationAgent(agent_config)
        
        if enable_ai_evaluation:
            self.evaluation_agent = EvaluationAgent(agent_config)
            logger.info("AI evaluation enabled")
        
        logger.info("Validation orchestrator initialized")
    
    async def execute_workflow(
        self,
        request: ValidationRequest
    ) -> WorkflowResult:
        """Execute complete validation workflow.
        
        Args:
            request: Validation request
        
        Returns:
            WorkflowResult with all execution details
        """
        start_time = time.time()
        errors = []
        
        logger.info(f"Starting validation workflow for {request.resource_info.host}")
        
        try:
            # Phase 1: Workload Discovery (if enabled)
            discovery_result = None
            classification = None
            
            if self.enable_discovery and request.auto_discover:
                try:
                    logger.info("Phase 1: Workload Discovery")
                    discovery_result = await self._execute_discovery(request.resource_info)
                    
                    # Classify the resource
                    if discovery_result:
                        logger.info("Classifying resource based on discovery")
                        classification = self.classifier.classify(discovery_result)
                        logger.info(
                            f"Resource classified as: {classification.category.value} "
                            f"(confidence: {classification.confidence:.2%})"
                        )
                except Exception as e:
                    error_msg = f"Discovery phase failed: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Phase 2: Validation Planning
            logger.info("Phase 2: Validation Planning")
            validation_plan = await self._create_validation_plan(
                request.resource_info,
                classification
            )
            logger.info(f"Validation plan created with {len(validation_plan.checks)} checks")
            
            # Phase 3: Execute Validations
            logger.info("Phase 3: Executing Validations")
            validation_result = await self._execute_validations(
                request,
                validation_plan,
                discovery_result
            )
            logger.info(
                f"Validations complete: {validation_result.passed_checks} passed, "
                f"{validation_result.failed_checks} failed"
            )
            
            # Phase 4: AI Evaluation (if enabled)
            evaluation = None
            if self.enable_ai_evaluation:
                try:
                    logger.info("Phase 4: AI Evaluation")
                    evaluation = await self._evaluate_results(
                        validation_result,
                        discovery_result,
                        classification
                    )
                    logger.info(f"Evaluation complete: {evaluation.overall_health}")
                except Exception as e:
                    error_msg = f"Evaluation phase failed: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Determine workflow status
            workflow_status = self._determine_workflow_status(
                validation_result,
                errors
            )
            
            execution_time = time.time() - start_time
            
            result = WorkflowResult(
                request=request,
                discovery_result=discovery_result,
                classification=classification,
                validation_plan=validation_plan,
                validation_result=validation_result,
                evaluation=evaluation,
                execution_time_seconds=execution_time,
                workflow_status=workflow_status,
                errors=errors
            )
            
            logger.info(
                f"Workflow completed in {execution_time:.2f}s with status: {workflow_status}"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Workflow failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            # Create minimal result on failure
            validation_result = ResourceValidationResult(
                resource_type=request.resource_info.resource_type,
                resource_host=request.resource_info.host,
                overall_status=ValidationStatus.ERROR,
                score=0,
                checks=[],
                execution_time_seconds=execution_time
            )
            
            return WorkflowResult(
                request=request,
                validation_result=validation_result,
                execution_time_seconds=execution_time,
                workflow_status="failure",
                errors=errors
            )
    
    async def _execute_discovery(
        self,
        resource: ResourceInfo
    ) -> Optional[WorkloadDiscoveryResult]:
        """Execute workload discovery phase.
        
        Args:
            resource: Resource to discover
        
        Returns:
            WorkloadDiscoveryResult or None on failure
        """
        try:
            result = await self.discovery_agent.discover_with_retry(
                self.mcp_client,
                resource,
                max_retries=1
            )
            return result
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return None
    
    async def _create_validation_plan(
        self,
        resource: ResourceInfo,
        classification: Optional[ResourceClassification]
    ) -> ValidationPlan:
        """Create validation plan.
        
        Args:
            resource: Resource information
            classification: Optional classification
        
        Returns:
            ValidationPlan
        """
        if classification:
            return await self.validation_agent.create_plan(resource, classification)
        else:
            # Create fallback classification for planning
            from models import ResourceCategory, ApplicationDetection
            fallback_classification = ResourceClassification(
                category=ResourceCategory.UNKNOWN,
                confidence=0.5,
                recommended_validations=["basic_connectivity", "system_health"]
            )
            return await self.validation_agent.create_plan(resource, fallback_classification)
    
    async def _execute_validations(
        self,
        request: ValidationRequest,
        plan: ValidationPlan,
        discovery_result: Optional[WorkloadDiscoveryResult]
    ) -> ResourceValidationResult:
        """Execute validation checks.
        
        Args:
            request: Validation request
            plan: Validation plan
            discovery_result: Optional discovery context
        
        Returns:
            ResourceValidationResult
        """
        start_time = time.time()
        checks = []
        
        # Execute each check in the plan
        for check_def in plan.checks:
            try:
                logger.debug(f"Executing check: {check_def.check_name}")
                
                # Call MCP tool
                result = await self.mcp_client.call_tool(
                    check_def.mcp_tool,
                    check_def.tool_args
                )
                
                # Interpret result
                check_result = self._interpret_check_result(
                    check_def,
                    result
                )
                checks.append(check_result)
                
            except Exception as e:
                logger.error(f"Check {check_def.check_id} failed: {e}")
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
            discovery_info=discovery_result.model_dump() if discovery_result else None,
            execution_time_seconds=execution_time
        )
    
    def _interpret_check_result(
        self,
        check_def,
        mcp_result: Dict[str, Any]
    ) -> CheckResult:
        """Interpret MCP tool result as check result.
        
        Args:
            check_def: Check definition
            mcp_result: MCP tool result
        
        Returns:
            CheckResult
        """
        # Check if MCP call was successful
        success = mcp_result.get("success", False)
        
        if not success:
            return CheckResult(
                check_id=check_def.check_id,
                check_name=check_def.check_name,
                status=ValidationStatus.FAIL,
                expected=check_def.expected_result,
                message=mcp_result.get("error", "Check failed")
            )
        
        # Tool-specific result interpretation
        # This is simplified - in production, you'd have more sophisticated logic
        status = ValidationStatus.PASS
        message = "Check passed"
        actual = str(mcp_result.get("result", ""))
        
        # Basic heuristics for common checks
        if "error" in mcp_result:
            status = ValidationStatus.FAIL
            message = mcp_result["error"]
        elif "warning" in mcp_result:
            status = ValidationStatus.WARNING
            message = mcp_result["warning"]
        
        return CheckResult(
            check_id=check_def.check_id,
            check_name=check_def.check_name,
            status=status,
            expected=check_def.expected_result,
            actual=actual,
            message=message,
            details=mcp_result
        )
    
    def _calculate_overall_status(
        self,
        checks: list[CheckResult]
    ) -> tuple[ValidationStatus, int]:
        """Calculate overall status and score.
        
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
    
    async def _evaluate_results(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification]
    ) -> OverallEvaluation:
        """Evaluate validation results with AI.
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery context
            classification: Classification context
        
        Returns:
            OverallEvaluation
        """
        return await self.evaluation_agent.evaluate(
            validation_result,
            discovery_result,
            classification
        )
    
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


# Made with Bob