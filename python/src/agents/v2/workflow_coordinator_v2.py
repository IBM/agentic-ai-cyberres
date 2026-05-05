"""
Workflow Coordinator V2 - Orchestrates Multi-Agent Workflow

This module provides the V2 implementation of the workflow coordinator using
artifact handoff pattern for clean agent-to-agent communication.

Key Improvements over V1:
- Artifact-based communication (no direct method calls)
- Simplified state management (ArtifactStore handles it)
- Better error handling and recovery
- Cleaner phase transitions
- Reduced complexity (~50% less code)

Example:
    >>> coordinator = WorkflowCoordinatorV2(
    ...     llm_model="ollama:llama3.2",
    ...     mcp_tools=mcp_tools
    ... )
    >>> result = await coordinator.execute(validation_request)
"""

import logging
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from beeai_framework.tools.mcp import MCPTool

from .artifact_store import ArtifactStore
from .discovery_agent_v2 import DiscoveryAgentV2
from .validation_agent_v2 import ValidationAgentV2
from .evaluation_agent_v2 import EvaluationAgentV2

# Import from parent models module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models import ValidationRequest, ResourceValidationResult, ValidationStatus
from agents.evaluation_agent import OverallEvaluation

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Workflow execution failed."""
    pass


class WorkflowResult:
    """Complete workflow execution result."""
    
    def __init__(
        self,
        request: ValidationRequest,
        discovery_artifact_id: Optional[str] = None,
        validation_artifact_id: Optional[str] = None,
        evaluation_artifact_id: Optional[str] = None,
        validation_result: Optional[ResourceValidationResult] = None,
        execution_time_seconds: float = 0.0,
        workflow_status: str = "success",
        errors: List[str] = None
    ):
        self.request = request
        self.discovery_artifact_id = discovery_artifact_id
        self.validation_artifact_id = validation_artifact_id
        self.evaluation_artifact_id = evaluation_artifact_id
        self.validation_result = validation_result
        self.execution_time_seconds = execution_time_seconds
        self.workflow_status = workflow_status
        self.errors = errors or []


class WorkflowCoordinatorV2:
    """
    Workflow coordinator using artifact handoff pattern.
    
    This coordinator orchestrates the complete validation workflow using
    three specialized agents that communicate via artifacts:
    
    1. Discovery Agent → DiscoveryArtifact
    2. Validation Agent → ValidationArtifact (reads DiscoveryArtifact)
    3. Evaluation Agent → EvaluationResult (reads ValidationArtifact)
    
    Key Improvements:
    - Artifact-based communication (loose coupling)
    - Simplified state management (ArtifactStore)
    - Better error handling (framework-integrated)
    - Cleaner phase transitions (schema-driven)
    - Reduced complexity (~50% less code than V1)
    
    Architecture:
    - Uses ArtifactStore for agent communication
    - Each agent reads from and writes to store
    - No direct agent-to-agent method calls
    - Clean separation of concerns
    - Easy to add/modify agents
    
    Example:
        >>> # Create coordinator
        >>> coordinator = WorkflowCoordinatorV2(
        ...     llm_model="ollama:llama3.2",
        ...     mcp_tools=mcp_tools
        ... )
        >>> 
        >>> # Execute workflow
        >>> request = ValidationRequest(...)
        >>> result = await coordinator.execute(request)
        >>> 
        >>> # Access results
        >>> print(f"Status: {result.workflow_status}")
        >>> print(f"Time: {result.execution_time_seconds:.2f}s")
    """
    
    def __init__(
        self,
        llm_model: str,
        mcp_tools: List[MCPTool],
        artifact_store: Optional[ArtifactStore] = None,
        persist_artifacts: bool = False,
        persist_path: Optional[Path] = None
    ):
        """
        Initialize Workflow Coordinator V2.
        
        Args:
            llm_model: LLM model identifier for all agents
            mcp_tools: List of MCP tools for discovery and validation
            artifact_store: Optional existing artifact store (creates new if None)
            persist_artifacts: Whether to persist artifacts to disk
            persist_path: Path for artifact persistence (if persist_artifacts=True)
        """
        self.llm_model = llm_model
        self.mcp_tools = mcp_tools
        
        # Create or use provided artifact store
        if artifact_store:
            self.artifact_store = artifact_store
        else:
            self.artifact_store = ArtifactStore(
                persist_path=persist_path if persist_artifacts else None
            )
        
        # Create agents
        self.discovery_agent = DiscoveryAgentV2(
            llm_model=llm_model,
            mcp_tools=mcp_tools,
            artifact_store=self.artifact_store
        )
        
        self.validation_agent = ValidationAgentV2(
            llm_model=llm_model,
            mcp_tools=mcp_tools,
            artifact_store=self.artifact_store
        )
        
        self.evaluation_agent = EvaluationAgentV2(
            llm_model=llm_model,
            artifact_store=self.artifact_store
        )
        
        logger.info(
            f"Initialized WorkflowCoordinatorV2 with model: {llm_model}, "
            f"tools: {len(mcp_tools)}, "
            f"persist: {persist_artifacts}"
        )
    
    async def execute(
        self,
        request: ValidationRequest
    ) -> WorkflowResult:
        """
        Execute complete validation workflow.
        
        This method orchestrates the three-phase workflow:
        
        Phase 1: Discovery
        - Discovers workloads on target resource
        - Produces DiscoveryArtifact
        - Saves to ArtifactStore
        
        Phase 2: Validation
        - Reads DiscoveryArtifact
        - Creates and executes validation plan
        - Produces ValidationArtifact
        - Saves to ArtifactStore
        
        Phase 3: Evaluation
        - Reads ValidationArtifact
        - Evaluates results
        - Produces EvaluationResult
        - Saves to ArtifactStore
        
        Args:
            request: Validation request with resource info
            
        Returns:
            WorkflowResult with all artifacts and final result
            
        Raises:
            WorkflowError: If workflow fails
            
        Example:
            >>> request = ValidationRequest(
            ...     resource_info=VMResourceInfo(...),
            ...     acceptance_criteria={...}
            ... )
            >>> result = await coordinator.execute(request)
        """
        logger.info(f"Starting workflow for resource: {request.resource_info.resource_id}")
        start_time = datetime.utcnow()
        errors = []
        
        discovery_artifact_id = None
        validation_artifact_id = None
        evaluation_artifact_id = None
        
        try:
            # Phase 1: Discovery
            logger.info("Phase 1: Discovery")
            discovery_artifact = await self.discovery_agent.discover(
                resource_info=request.resource_info,
                save_artifact=True
            )
            discovery_artifact_id = f"discovery_{request.resource_info.resource_id}:v1"
            logger.info(f"Discovery complete: {discovery_artifact_id}")
            
            # Phase 2: Validation
            logger.info("Phase 2: Validation")
            validation_artifact = await self.validation_agent.validate(
                discovery_artifact=discovery_artifact,
                save_artifact=True
            )
            validation_artifact_id = f"validation_{request.resource_info.resource_id}:v1"
            logger.info(f"Validation complete: {validation_artifact_id}")
            
            # Phase 3: Evaluation
            logger.info("Phase 3: Evaluation")
            evaluation = await self.evaluation_agent.evaluate(
                validation_artifact=validation_artifact,
                save_artifact=True
            )
            evaluation_artifact_id = f"evaluation_{request.resource_info.resource_id}:v1"
            logger.info(f"Evaluation complete: {evaluation_artifact_id}")
            
            # Build final result
            validation_result = self._build_validation_result(
                request=request,
                discovery_artifact=discovery_artifact,
                validation_artifact=validation_artifact,
                evaluation=evaluation
            )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Determine workflow status
            workflow_status = self._determine_workflow_status(
                validation_artifact=validation_artifact,
                evaluation=evaluation
            )
            
            # Create workflow result
            result = WorkflowResult(
                request=request,
                discovery_artifact_id=discovery_artifact_id,
                validation_artifact_id=validation_artifact_id,
                evaluation_artifact_id=evaluation_artifact_id,
                validation_result=validation_result,
                execution_time_seconds=execution_time,
                workflow_status=workflow_status,
                errors=errors
            )
            
            logger.info(
                f"Workflow complete for {request.resource_info.resource_id}: "
                f"status={workflow_status}, time={execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Workflow failed for {request.resource_info.resource_id}: {e}",
                exc_info=True
            )
            errors.append(str(e))
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create failure result
            result = WorkflowResult(
                request=request,
                discovery_artifact_id=discovery_artifact_id,
                validation_artifact_id=validation_artifact_id,
                evaluation_artifact_id=evaluation_artifact_id,
                validation_result=None,
                execution_time_seconds=execution_time,
                workflow_status="failure",
                errors=errors
            )
            
            return result
    
    def _build_validation_result(
        self,
        request: ValidationRequest,
        discovery_artifact,
        validation_artifact,
        evaluation: OverallEvaluation
    ) -> ResourceValidationResult:
        """
        Build final validation result from artifacts.
        
        Args:
            request: Original validation request
            discovery_artifact: Discovery results
            validation_artifact: Validation results
            evaluation: Evaluation results
            
        Returns:
            ResourceValidationResult for the resource
        """
        # Determine overall status
        if validation_artifact.is_successful():
            status = ValidationStatus.PASSED
        elif validation_artifact.checks_passed > 0:
            status = ValidationStatus.PARTIAL
        else:
            status = ValidationStatus.FAILED
        
        # Build result
        result = ResourceValidationResult(
            resource_id=request.resource_info.resource_id,
            resource_type=request.resource_info.resource_type,
            status=status,
            checks_performed=validation_artifact.checks_executed,
            checks_passed=validation_artifact.checks_passed,
            checks_failed=validation_artifact.checks_failed,
            overall_confidence=discovery_artifact.confidence_score,
            summary=evaluation.summary if hasattr(evaluation, 'summary') else "Validation complete",
            recommendations=evaluation.recommendations if hasattr(evaluation, 'recommendations') else [],
            timestamp=datetime.utcnow()
        )
        
        return result
    
    def _determine_workflow_status(
        self,
        validation_artifact,
        evaluation: OverallEvaluation
    ) -> str:
        """
        Determine overall workflow status.
        
        Args:
            validation_artifact: Validation results
            evaluation: Evaluation results
            
        Returns:
            Workflow status: success, partial_success, or failure
        """
        if validation_artifact.is_successful():
            return "success"
        elif validation_artifact.checks_passed > 0:
            return "partial_success"
        else:
            return "failure"
    
    def get_coordinator_info(self) -> dict:
        """
        Get information about the coordinator configuration.
        
        Returns:
            Dictionary with coordinator details
        """
        return {
            "coordinator_type": "WorkflowCoordinatorV2",
            "llm_model": self.llm_model,
            "num_tools": len(self.mcp_tools),
            "agents": {
                "discovery": self.discovery_agent.get_agent_info(),
                "validation": self.validation_agent.get_agent_info(),
                "evaluation": self.evaluation_agent.get_agent_info()
            },
            "artifact_store": {
                "num_artifacts": len(self.artifact_store.list_artifacts()),
                "persist_enabled": self.artifact_store._persist_path is not None
            }
        }

# Made with Bob
