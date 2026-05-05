"""
Evaluation Agent V2 - RequirementAgent-based Implementation

This module provides the V2 implementation of the Evaluation Agent using
BeeAI's RequirementAgent pattern with artifact handoff.

Key Improvements over V1:
- Schema-driven output (EvaluationResult)
- Reads from ValidationArtifact (artifact handoff)
- Simplified evaluation logic
- Better recommendations generation
- Reduced complexity

Example:
    >>> agent = EvaluationAgentV2(
    ...     llm_model="openai:gpt-4",
    ...     artifact_store=store
    ... )
    >>> result = await agent.evaluate(validation_artifact)
"""

import logging
from typing import Optional
from datetime import datetime

from beeai_framework.agents.requirement.agent import RequirementAgent

from .artifact_store import ArtifactStore
from .artifacts.validation_artifact import ValidationArtifact
from .factories.agent_factory import AgentFactory, AgentConfig

# Import from parent models module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents.evaluation_agent import OverallEvaluation

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Evaluation operation failed."""
    pass


class EvaluationAgentV2:
    """
    RequirementAgent-based evaluation agent (V2).
    
    This agent evaluates validation results and provides comprehensive
    assessments with recommendations. It demonstrates the artifact handoff
    pattern by reading ValidationArtifact and producing EvaluationResult.
    
    Key Improvements:
    - Reads from ValidationArtifact (clean input)
    - Outputs structured evaluation (schema-enforced)
    - Simplified evaluation logic (framework handles complexity)
    - Better recommendations (LLM-powered)
    - No tools needed (pure analysis)
    
    Architecture:
    - Uses AgentFactory for creation
    - Reads validation artifact from ArtifactStore
    - Analyzes results using LLM reasoning
    - Generates recommendations
    - Saves evaluation to store
    
    Example:
        >>> # Create agent
        >>> agent = EvaluationAgentV2(
        ...     llm_model="openai:gpt-4",
        ...     artifact_store=store
        ... )
        >>> 
        >>> # Evaluate validation results
        >>> validation = store.load("validation_vm-01", ValidationArtifact)
        >>> result = await agent.evaluate(validation)
        >>> 
        >>> # Result contains assessment and recommendations
        >>> print(f"Overall status: {result.overall_status}")
        >>> print(f"Recommendations: {len(result.recommendations)}")
    """
    
    def __init__(
        self,
        llm_model: str,
        artifact_store: ArtifactStore,
        config: Optional[AgentConfig] = None
    ):
        """
        Initialize Evaluation Agent V2.
        
        Args:
            llm_model: LLM model identifier (e.g., "openai:gpt-4")
            artifact_store: Shared artifact store for communication
            config: Optional custom configuration
        """
        self.llm_model = llm_model
        self.artifact_store = artifact_store
        self.config = config or AgentConfig(
            name="Evaluation Agent V2",
            llm_model=llm_model,
            temperature=0.3  # Higher for nuanced evaluation
        )
        
        # Create agent using factory
        factory = AgentFactory()
        self._agent = factory.create_evaluation_agent(
            llm_model=llm_model,
            artifact_store=artifact_store,
            config=self.config
        )
        
        logger.info(f"Initialized EvaluationAgentV2 with model: {llm_model}")
    
    async def evaluate(
        self,
        validation_artifact: ValidationArtifact,
        save_artifact: bool = True
    ) -> OverallEvaluation:
        """
        Evaluate validation results and provide assessment.
        
        This method orchestrates the evaluation process:
        1. Formats validation results as input
        2. Runs RequirementAgent for analysis
        3. Generates recommendations
        4. Extracts evaluation result
        5. Optionally saves to ArtifactStore
        6. Returns typed evaluation
        
        Args:
            validation_artifact: Validation results to evaluate
            save_artifact: Whether to save artifact to store (default: True)
            
        Returns:
            OverallEvaluation with assessment and recommendations
            
        Raises:
            EvaluationError: If evaluation fails
            
        Example:
            >>> validation = ValidationArtifact(...)
            >>> result = await agent.evaluate(validation)
            >>> print(f"Status: {result.overall_status}")
        """
        logger.info(
            f"Starting evaluation for resource: {validation_artifact.resource_id}"
        )
        start_time = datetime.utcnow()
        
        try:
            # Format input for agent
            user_input = self._format_evaluation_input(validation_artifact)
            
            logger.debug(f"Formatted input for agent: {user_input[:200]}...")
            
            # Run RequirementAgent
            # The agent will:
            # 1. Analyze validation results
            # 2. Assess quality and completeness
            # 3. Identify issues and risks
            # 4. Generate recommendations
            # 5. Return evaluation result
            result = await self._agent.run(
                user_input=user_input,
                final_answer_schema=OverallEvaluation
            )
            
            # Extract evaluation from result
            evaluation = result.final_answer
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Save to artifact store if requested
            if save_artifact:
                artifact_id = self.artifact_store.save(
                    key=f"evaluation_{validation_artifact.resource_id}",
                    value=evaluation,
                    metadata={
                        "resource_id": validation_artifact.resource_id,
                        "resource_type": validation_artifact.resource_type,
                        "validation_artifact_id": f"validation_{validation_artifact.resource_id}:v1",
                        "llm_model": self.llm_model,
                        "execution_time_seconds": execution_time,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Evaluation artifact saved: {artifact_id}")
            
            # Log summary
            logger.info(
                f"Evaluation complete for {validation_artifact.resource_id}: "
                f"status={evaluation.overall_status}, "
                f"recommendations={len(evaluation.recommendations)}, "
                f"time={execution_time:.2f}s"
            )
            
            return evaluation
            
        except Exception as e:
            logger.error(
                f"Evaluation failed for {validation_artifact.resource_id}: {e}",
                exc_info=True
            )
            raise EvaluationError(
                f"Evaluation failed for {validation_artifact.resource_id}: {e}"
            ) from e
    
    def _format_evaluation_input(self, validation_artifact: ValidationArtifact) -> str:
        """
        Format validation artifact into evaluation agent input.
        
        This creates a clear, structured prompt that includes all
        relevant validation information for evaluation.
        
        Args:
            validation_artifact: Validation results to evaluate
            
        Returns:
            Formatted input string for the agent
        """
        input_parts = [
            "Evaluate the following validation results and provide a comprehensive assessment:",
            "",
            "## Validation Summary",
            f"**Resource ID:** {validation_artifact.resource_id}",
            f"**Resource Type:** {validation_artifact.resource_type}",
            f"**Validation Strategy:** {validation_artifact.validation_strategy}",
            f"**Plan Quality:** {validation_artifact.plan_quality}",
            f"**Coverage:** {validation_artifact.coverage_percentage:.1f}%",
            "",
            "## Execution Results",
            f"**Total Checks:** {len(validation_artifact.validation_checks)}",
            f"**Executed:** {validation_artifact.checks_executed}",
            f"**Passed:** {validation_artifact.checks_passed}",
            f"**Failed:** {validation_artifact.checks_failed}",
            f"**Skipped:** {validation_artifact.checks_skipped}",
            f"**Success Rate:** {validation_artifact.get_success_rate():.1f}%",
            f"**Execution Time:** {validation_artifact.execution_time_seconds:.2f}s",
            "",
        ]
        
        # Add failed checks if any
        failed_checks = validation_artifact.get_failed_checks()
        if failed_checks:
            input_parts.append("## Failed Checks")
            for check in failed_checks:
                input_parts.append(f"\n**{check.check_name}**")
                input_parts.append(f"- Tool: {check.tool_name}")
                input_parts.append(f"- Expected: {check.expected_outcome}")
                if check.error:
                    input_parts.append(f"- Error: {check.error}")
        
        # Add high priority checks
        high_priority = validation_artifact.get_high_priority_checks()
        if high_priority:
            input_parts.append("\n## High Priority Checks")
            for check in high_priority:
                status = "✓ Passed" if check.passed else "✗ Failed"
                input_parts.append(f"- {check.check_name}: {status}")
        
        # Add validation reasoning
        input_parts.extend([
            "",
            "## Validation Planning Reasoning",
            validation_artifact.planning_reasoning,
            "",
            "## Execution Summary",
            validation_artifact.execution_summary if validation_artifact.execution_summary else "No summary provided",
            "",
            "## Evaluation Objectives",
            "Provide a comprehensive evaluation that includes:",
            "1. Overall assessment of validation quality and completeness",
            "2. Analysis of any failures or issues",
            "3. Risk assessment based on results",
            "4. Specific, actionable recommendations",
            "5. Confidence score in the validation results",
            "",
            "## Instructions",
            "- Be thorough but practical in your assessment",
            "- Focus on actionable recommendations",
            "- Consider business impact of findings",
            "- Provide clear confidence levels",
            "- Highlight both successes and areas for improvement",
            "- Assess whether the resource is ready for production use",
            "",
            "Please provide a complete evaluation with:",
            "- Overall status (success, partial_success, failure)",
            "- Detailed findings and analysis",
            "- Specific recommendations with priorities",
            "- Confidence score (0.0-1.0)",
            "- Summary for stakeholders"
        ])
        
        return "\n".join(input_parts)
    
    def get_agent_info(self) -> dict:
        """
        Get information about the agent configuration.
        
        Returns:
            Dictionary with agent configuration details
        """
        return {
            "agent_type": "EvaluationAgentV2",
            "llm_model": self.llm_model,
            "num_tools": 0,  # Evaluation doesn't use tools
            "config": {
                "name": self.config.name,
                "temperature": self.config.temperature,
                "max_iterations": self.config.max_iterations,
                "memory_size": self.config.memory_size
            }
        }

# Made with Bob
