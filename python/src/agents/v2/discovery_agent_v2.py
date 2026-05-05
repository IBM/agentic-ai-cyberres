"""
Discovery Agent V2 - RequirementAgent-based Implementation

This module provides the V2 implementation of the Discovery Agent using
BeeAI's RequirementAgent pattern with artifact handoff.

Key Improvements over V1:
- Schema-driven output (DiscoveryArtifact)
- Simplified error handling
- Better separation of concerns
- Artifact-based communication
- Reduced complexity (~40% less code)

Example:
    >>> agent = DiscoveryAgentV2(
    ...     llm_model="ollama:llama3.2",
    ...     mcp_tools=mcp_tools,
    ...     artifact_store=store
    ... )
    >>> result = await agent.discover(resource_info)
"""

import logging
from typing import List, Optional
from datetime import datetime

from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.tools.mcp import MCPTool

from .artifact_store import ArtifactStore
from .artifacts.discovery_artifact import DiscoveryArtifact
from .factories.agent_factory import AgentFactory, DiscoveryAgentConfig

# Import from parent models module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models import VMResourceInfo, OracleDBResourceInfo, MongoDBResourceInfo

logger = logging.getLogger(__name__)

# Type alias for resource info
ResourceInfo = VMResourceInfo | OracleDBResourceInfo | MongoDBResourceInfo


class DiscoveryError(Exception):
    """Discovery operation failed."""
    pass


class DiscoveryAgentV2:
    """
    RequirementAgent-based discovery agent (V2).
    
    This is the POC implementation demonstrating the migration from
    ReActAgent to RequirementAgent with artifact handoff pattern.
    
    Key Improvements:
    - Schema-driven output (DiscoveryArtifact enforced by RequirementAgent)
    - Simplified error handling (framework handles retries)
    - Better separation of concerns (factory creates agent)
    - Artifact-based communication (saves to ArtifactStore)
    - Reduced complexity (no custom state management)
    
    Architecture:
    - Uses AgentFactory for standardized creation
    - Outputs DiscoveryArtifact (type-safe)
    - Saves artifacts to ArtifactStore
    - Integrates with MCP tools seamlessly
    
    Example:
        >>> # Create agent
        >>> agent = DiscoveryAgentV2(
        ...     llm_model="ollama:llama3.2",
        ...     mcp_tools=mcp_tools,
        ...     artifact_store=store
        ... )
        >>> 
        >>> # Perform discovery
        >>> resource = VMResourceInfo(
        ...     resource_id="vm-prod-01",
        ...     hostname="web-server.example.com",
        ...     ip_address="192.168.1.100"
        ... )
        >>> result = await agent.discover(resource)
        >>> 
        >>> # Result is type-safe DiscoveryArtifact
        >>> print(f"Found {len(result.detected_applications)} applications")
        >>> print(f"Confidence: {result.confidence_score:.2f}")
    """
    
    def __init__(
        self,
        llm_model: str,
        mcp_tools: List[MCPTool],
        artifact_store: ArtifactStore,
        config: Optional[DiscoveryAgentConfig] = None
    ):
        """
        Initialize Discovery Agent V2.
        
        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2", "openai:gpt-4")
            mcp_tools: List of MCP tools for discovery operations
            artifact_store: Shared artifact store for communication
            config: Optional custom configuration
        """
        self.llm_model = llm_model
        self.mcp_tools = mcp_tools
        self.artifact_store = artifact_store
        self.config = config or DiscoveryAgentConfig(llm_model=llm_model)
        
        # Create agent using factory
        factory = AgentFactory()
        self._agent = factory.create_discovery_agent(
            llm_model=llm_model,
            mcp_tools=mcp_tools,
            artifact_store=artifact_store,
            config=self.config
        )
        
        logger.info(
            f"Initialized DiscoveryAgentV2 with model: {llm_model}, "
            f"tools: {len(mcp_tools)}"
        )
    
    async def discover(
        self,
        resource_info: ResourceInfo,
        save_artifact: bool = True
    ) -> DiscoveryArtifact:
        """
        Perform workload discovery on target resource.
        
        This method orchestrates the discovery process:
        1. Formats input for the RequirementAgent
        2. Runs the agent (which uses MCP tools internally)
        3. Extracts the DiscoveryArtifact from the result
        4. Optionally saves to ArtifactStore
        5. Returns the typed artifact
        
        Args:
            resource_info: Target resource information (VM, Oracle DB, or MongoDB)
            save_artifact: Whether to save artifact to store (default: True)
            
        Returns:
            DiscoveryArtifact with complete discovery results
            
        Raises:
            DiscoveryError: If discovery fails
            
        Example:
            >>> resource = VMResourceInfo(
            ...     resource_id="vm-prod-01",
            ...     hostname="web-server.example.com",
            ...     ip_address="192.168.1.100"
            ... )
            >>> result = await agent.discover(resource)
            >>> print(f"Confidence: {result.confidence_score}")
        """
        logger.info(f"Starting discovery for resource: {resource_info.resource_id}")
        start_time = datetime.utcnow()
        
        try:
            # Format input for agent
            user_input = self._format_discovery_input(resource_info)
            
            logger.debug(f"Formatted input for agent: {user_input[:200]}...")
            
            # Run RequirementAgent
            # The agent will:
            # 1. Analyze the resource
            # 2. Plan discovery strategy
            # 3. Execute MCP tools
            # 4. Aggregate results
            # 5. Return DiscoveryArtifact
            result = await self._agent.run(
                user_input=user_input,
                final_answer_schema=DiscoveryArtifact
            )
            
            # Extract artifact from result
            discovery_artifact = result.final_answer
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Save to artifact store if requested
            if save_artifact:
                artifact_id = self.artifact_store.save(
                    key=f"discovery_{resource_info.resource_id}",
                    value=discovery_artifact,
                    metadata={
                        "resource_id": resource_info.resource_id,
                        "resource_type": resource_info.resource_type,
                        "llm_model": self.llm_model,
                        "execution_time_seconds": execution_time,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Discovery artifact saved: {artifact_id}")
            
            # Log summary
            logger.info(
                f"Discovery complete for {resource_info.resource_id}: "
                f"confidence={discovery_artifact.confidence_score:.2f}, "
                f"applications={len(discovery_artifact.detected_applications)}, "
                f"ports={len(discovery_artifact.open_ports)}, "
                f"time={execution_time:.2f}s"
            )
            
            return discovery_artifact
            
        except Exception as e:
            logger.error(
                f"Discovery failed for {resource_info.resource_id}: {e}",
                exc_info=True
            )
            raise DiscoveryError(
                f"Discovery failed for {resource_info.resource_id}: {e}"
            ) from e
    
    def _format_discovery_input(self, resource_info: ResourceInfo) -> str:
        """
        Format resource info into discovery agent input.
        
        This creates a clear, structured prompt for the RequirementAgent
        that includes all relevant resource information.
        
        Args:
            resource_info: Resource information to format
            
        Returns:
            Formatted input string for the agent
        """
        # Base information
        input_parts = [
            "Perform comprehensive workload discovery on the following resource:",
            "",
            f"**Resource Type:** {resource_info.resource_type}",
            f"**Resource ID:** {resource_info.resource_id}",
        ]
        
        # Add type-specific information
        if isinstance(resource_info, VMResourceInfo):
            input_parts.extend([
                f"**Hostname:** {resource_info.hostname}",
                f"**IP Address:** {resource_info.ip_address}",
                "",
                "**Connection Info:**",
                f"- SSH available: {bool(resource_info.ssh_credentials)}",
            ])
            if resource_info.ssh_credentials:
                input_parts.append(
                    f"- SSH user: {resource_info.ssh_credentials.get('username', 'N/A')}"
                )
        
        elif isinstance(resource_info, OracleDBResourceInfo):
            input_parts.extend([
                f"**Hostname:** {resource_info.hostname}",
                f"**Port:** {resource_info.port}",
                f"**Service Name:** {resource_info.service_name}",
                "",
                "**Connection Info:**",
                f"- Database credentials available: {bool(resource_info.credentials)}",
            ])
        
        elif isinstance(resource_info, MongoDBResourceInfo):
            input_parts.extend([
                f"**Hostname:** {resource_info.hostname}",
                f"**Port:** {resource_info.port}",
                f"**Database:** {resource_info.database}",
                "",
                "**Connection Info:**",
                f"- Database credentials available: {bool(resource_info.credentials)}",
            ])
        
        # Add discovery objectives
        input_parts.extend([
            "",
            "**Discovery Objectives:**",
            "1. Identify all running services and applications",
            "2. Detect open ports and network services",
            "3. Analyze running processes (if SSH available)",
            "4. Determine application versions and configurations",
            "5. Assess overall workload profile",
            "",
            "**Instructions:**",
            "- Use available MCP tools systematically",
            "- Start with less invasive methods (port scanning)",
            "- Progress to more detailed analysis if credentials available",
            "- Provide confidence scores based on evidence quality",
            "- Include clear reasoning for your discovery approach",
            "- Assess data quality and completeness honestly",
            "",
            "Please provide a complete DiscoveryArtifact with all required fields."
        ])
        
        return "\n".join(input_parts)
    
    def get_agent_info(self) -> dict:
        """
        Get information about the agent configuration.
        
        Returns:
            Dictionary with agent configuration details
        """
        return {
            "agent_type": "DiscoveryAgentV2",
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
