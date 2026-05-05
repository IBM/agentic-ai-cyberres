"""
Validation Agent V2 - RequirementAgent-based Implementation

This module provides the V2 implementation of the Validation Agent using
BeeAI's RequirementAgent pattern with artifact handoff.

Key Improvements over V1:
- Schema-driven output (ValidationArtifact)
- Reads from DiscoveryArtifact (artifact handoff)
- Simplified planning logic
- Better separation of concerns
- Reduced complexity

Example:
    >>> agent = ValidationAgentV2(
    ...     llm_model="ollama:llama3.2",
    ...     mcp_tools=mcp_tools,
    ...     artifact_store=store
    ... )
    >>> result = await agent.validate(discovery_artifact)
"""

import logging
from typing import List, Optional
from datetime import datetime

from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.tools.mcp import MCPTool

from .artifact_store import ArtifactStore
from .artifacts.discovery_artifact import DiscoveryArtifact
from .artifacts.validation_artifact import ValidationArtifact, ValidationCheck
from .factories.agent_factory import AgentFactory, ValidationAgentConfig

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation operation failed."""
    pass


class ValidationAgentV2:
    """
    RequirementAgent-based validation agent (V2).
    
    This agent creates validation plans based on discovery results and
    executes them using MCP tools. It demonstrates the artifact handoff
    pattern by reading DiscoveryArtifact and producing ValidationArtifact.
    
    Key Improvements:
    - Reads from DiscoveryArtifact (clean input)
    - Outputs ValidationArtifact (schema-enforced)
    - Simplified planning logic (framework handles complexity)
    - Better error handling (framework retries)
    - Reduced code complexity
    
    Architecture:
    - Uses AgentFactory for creation
    - Reads discovery artifact from ArtifactStore
    - Creates validation plan using LLM reasoning
    - Executes checks using MCP tools
    - Saves ValidationArtifact to store
    
    Example:
        >>> # Create agent
        >>> agent = ValidationAgentV2(
        ...     llm_model="openai:gpt-4",
        ...     mcp_tools=mcp_tools,
        ...     artifact_store=store
        ... )
        >>> 
        >>> # Validate based on discovery
        >>> discovery = store.load("discovery_vm-01", DiscoveryArtifact)
        >>> result = await agent.validate(discovery)
        >>> 
        >>> # Result is type-safe ValidationArtifact
        >>> print(f"Success rate: {result.get_success_rate():.1f}%")
        >>> print(f"Checks passed: {result.checks_passed}/{result.checks_executed}")
    """
    
    def __init__(
        self,
        llm_model: str,
        mcp_tools: List[MCPTool],
        artifact_store: ArtifactStore,
        config: Optional[ValidationAgentConfig] = None
    ):
        """
        Initialize Validation Agent V2.
        
        Args:
            llm_model: LLM model identifier (e.g., "openai:gpt-4")
            mcp_tools: List of MCP tools for validation operations
            artifact_store: Shared artifact store for communication
            config: Optional custom configuration
        """
        self.llm_model = llm_model
        self.mcp_tools = mcp_tools
        self.artifact_store = artifact_store
        self.config = config or ValidationAgentConfig(llm_model=llm_model)
        
        # Create agent using factory
        factory = AgentFactory()
        self._agent = factory.create_validation_agent(
            llm_model=llm_model,
            mcp_tools=mcp_tools,
            artifact_store=artifact_store,
            config=self.config
        )
        
        logger.info(
            f"Initialized ValidationAgentV2 with model: {llm_model}, "
            f"tools: {len(mcp_tools)}"
        )
    
    async def validate(
        self,
        discovery_artifact: DiscoveryArtifact,
        save_artifact: bool = True
    ) -> ValidationArtifact:
        """
        Create and execute validation plan based on discovery results.
        
        This method orchestrates the validation process:
        1. Formats discovery results as input
        2. Runs RequirementAgent to create validation plan
        3. Executes validation checks (simulated in POC)
        4. Extracts ValidationArtifact from result
        5. Optionally saves to ArtifactStore
        6. Returns typed artifact
        
        Args:
            discovery_artifact: Discovery results to validate
            save_artifact: Whether to save artifact to store (default: True)
            
        Returns:
            ValidationArtifact with plan and execution results
            
        Raises:
            ValidationError: If validation fails
            
        Example:
            >>> discovery = DiscoveryArtifact(...)
            >>> result = await agent.validate(discovery)
            >>> if result.is_successful():
            ...     print("All checks passed!")
        """
        logger.info(
            f"Starting validation for resource: {discovery_artifact.resource_id}"
        )
        start_time = datetime.utcnow()
        
        try:
            # Format input for agent
            user_input = self._format_validation_input(discovery_artifact)
            
            logger.debug(f"Formatted input for agent: {user_input[:200]}...")
            
            # Run RequirementAgent
            # The agent will:
            # 1. Analyze discovery results
            # 2. Create validation strategy
            # 3. Define validation checks
            # 4. Execute checks using MCP tools
            # 5. Return ValidationArtifact
            result = await self._agent.run(
                user_input=user_input,
                final_answer_schema=ValidationArtifact
            )
            
            # Extract artifact from result
            validation_artifact = result.final_answer
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update execution time in artifact
            validation_artifact.execution_time_seconds = execution_time
            
            # Save to artifact store if requested
            if save_artifact:
                artifact_id = self.artifact_store.save(
                    key=f"validation_{discovery_artifact.resource_id}",
                    value=validation_artifact,
                    metadata={
                        "resource_id": discovery_artifact.resource_id,
                        "resource_type": discovery_artifact.resource_type,
                        "discovery_artifact_id": f"discovery_{discovery_artifact.resource_id}:v1",
                        "llm_model": self.llm_model,
                        "execution_time_seconds": execution_time,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Validation artifact saved: {artifact_id}")
            
            # Log summary
            logger.info(
                f"Validation complete for {discovery_artifact.resource_id}: "
                f"checks={validation_artifact.checks_executed}, "
                f"passed={validation_artifact.checks_passed}, "
                f"failed={validation_artifact.checks_failed}, "
                f"success_rate={validation_artifact.get_success_rate():.1f}%, "
                f"time={execution_time:.2f}s"
            )
            
            return validation_artifact
            
        except Exception as e:
            logger.error(
                f"Validation failed for {discovery_artifact.resource_id}: {e}",
                exc_info=True
            )
            raise ValidationError(
                f"Validation failed for {discovery_artifact.resource_id}: {e}"
            ) from e
    
    def _format_validation_input(self, discovery_artifact: DiscoveryArtifact) -> str:
        """
        Format discovery artifact into validation agent input.
        
        This creates a clear, structured prompt that includes all
        relevant discovery information for validation planning.
        
        Args:
            discovery_artifact: Discovery results to validate
            
        Returns:
            Formatted input string for the agent
        """
        input_parts = [
            "Create a comprehensive validation plan based on the following discovery results:",
            "",
            "## Discovery Summary",
            f"**Resource ID:** {discovery_artifact.resource_id}",
            f"**Resource Type:** {discovery_artifact.resource_type}",
            f"**Discovery Method:** {discovery_artifact.discovery_method}",
            f"**Confidence Score:** {discovery_artifact.confidence_score:.2f}",
            f"**Data Quality:** {discovery_artifact.data_quality}",
            "",
            "## Findings",
        ]
        
        # Add discovered applications
        if discovery_artifact.detected_applications:
            input_parts.append("\n**Detected Applications:**")
            for app in discovery_artifact.detected_applications:
                input_parts.append(
                    f"- {app.name} {app.version or ''} "
                    f"(confidence: {app.confidence:.2f})"
                )
        
        # Add open ports
        if discovery_artifact.open_ports:
            input_parts.append("\n**Open Ports:**")
            for port in discovery_artifact.open_ports[:10]:  # Limit to 10
                input_parts.append(
                    f"- Port {port.port}/{port.protocol}: {port.service}"
                )
            if len(discovery_artifact.open_ports) > 10:
                input_parts.append(
                    f"- ... and {len(discovery_artifact.open_ports) - 10} more"
                )
        
        # Add running processes
        if discovery_artifact.running_processes:
            input_parts.append("\n**Running Processes:**")
            for proc in discovery_artifact.running_processes[:5]:  # Limit to 5
                input_parts.append(f"- {proc.name} (PID: {proc.pid})")
            if len(discovery_artifact.running_processes) > 5:
                input_parts.append(
                    f"- ... and {len(discovery_artifact.running_processes) - 5} more"
                )
        
        # Add discovery reasoning
        input_parts.extend([
            "",
            "## Discovery Reasoning",
            discovery_artifact.discovery_reasoning,
            "",
            "## Validation Objectives",
            "Create a validation plan that:",
            "1. Verifies all detected applications are functioning correctly",
            "2. Validates network connectivity and port accessibility",
            "3. Checks service health and status",
            "4. Confirms configuration correctness",
            "5. Assesses overall resource health",
            "",
            "## Instructions",
            "- Base validation checks on discovery findings",
            "- Prioritize checks based on application criticality",
            "- Define clear success criteria for each check",
            "- Use appropriate MCP tools for validation",
            "- Provide reasoning for your validation strategy",
            "- Assess plan quality and coverage honestly",
            "",
            "Please provide a complete ValidationArtifact with:",
            "- Comprehensive list of validation checks",
            "- Clear reasoning for the validation strategy",
            "- Quality assessment of the plan",
            "- Coverage percentage estimate"
        ])
        
        return "\n".join(input_parts)
    
    def get_agent_info(self) -> dict:
        """
        Get information about the agent configuration.
        
        Returns:
            Dictionary with agent configuration details
        """
        return {
            "agent_type": "ValidationAgentV2",
            "llm_model": self.llm_model,
            "num_tools": len(self.mcp_tools),
            "config": {
                "name": self.config.name,
                "temperature": self.config.temperature,
                "max_iterations": self.config.max_iterations,
                "memory_size": self.config.memory_size
            }
        }

# Made with Bob
