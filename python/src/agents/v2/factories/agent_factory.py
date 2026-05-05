"""
Agent Factory - Standardized RequirementAgent Creation

This module provides factory methods for creating RequirementAgent instances
with consistent configuration and setup.

Key Features:
- Standardized agent creation
- Consistent configuration
- Type-safe artifact schemas
- Reduced boilerplate
- Easier testing

Example:
    >>> factory = AgentFactory()
    >>> discovery_agent = factory.create_discovery_agent(
    ...     llm_model="ollama:llama3.2",
    ...     mcp_tools=mcp_tools,
    ...     artifact_store=store
    ... )
"""

import logging
from typing import List, Optional

from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig
from beeai_framework.tools.mcp import MCPTool

from ..artifact_store import ArtifactStore
from ..artifacts.discovery_artifact import DiscoveryArtifact
from ..artifacts.validation_artifact import ValidationArtifact

logger = logging.getLogger(__name__)


class AgentConfig:
    """Base configuration for RequirementAgent."""
    
    def __init__(
        self,
        name: str,
        llm_model: str,
        temperature: float = 0.1,
        max_iterations: int = 10,
        memory_size: int = 50
    ):
        self.name = name
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.memory_size = memory_size


class DiscoveryAgentConfig(AgentConfig):
    """Configuration for Discovery Agent."""
    
    def __init__(self, llm_model: str, **kwargs):
        super().__init__(
            name="Discovery Agent V2",
            llm_model=llm_model,
            temperature=0.1,  # Low temperature for consistent discovery
            **kwargs
        )


class ValidationAgentConfig(AgentConfig):
    """Configuration for Validation Agent."""
    
    def __init__(self, llm_model: str, **kwargs):
        super().__init__(
            name="Validation Agent V2",
            llm_model=llm_model,
            temperature=0.2,  # Slightly higher for creative planning
            **kwargs
        )


class AgentFactory:
    """
    Factory for creating standardized RequirementAgent instances.
    
    This factory provides consistent configuration and setup for all agents
    in the workflow, reducing boilerplate and ensuring standardization.
    
    Features:
    - Consistent agent configuration
    - Standardized memory setup
    - Type-safe artifact schemas
    - Logging and error handling
    - Easy testing and mocking
    
    Example:
        >>> factory = AgentFactory()
        >>> 
        >>> # Create discovery agent
        >>> discovery_agent = factory.create_discovery_agent(
        ...     llm_model="ollama:llama3.2",
        ...     mcp_tools=mcp_tools,
        ...     artifact_store=store
        ... )
        >>> 
        >>> # Create validation agent
        >>> validation_agent = factory.create_validation_agent(
        ...     llm_model="openai:gpt-4",
        ...     mcp_tools=mcp_tools,
        ...     artifact_store=store
        ... )
    """
    
    @staticmethod
    def create_discovery_agent(
        llm_model: str,
        mcp_tools: List[MCPTool],
        artifact_store: ArtifactStore,
        config: Optional[DiscoveryAgentConfig] = None
    ) -> RequirementAgent:
        """
        Create discovery agent with standard configuration.
        
        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2", "openai:gpt-4")
            mcp_tools: List of MCP tools for discovery operations
            artifact_store: Shared artifact store for communication
            config: Optional custom configuration
            
        Returns:
            Configured RequirementAgent for discovery operations
            
        Example:
            >>> agent = AgentFactory.create_discovery_agent(
            ...     llm_model="ollama:llama3.2",
            ...     mcp_tools=[port_scanner, process_scanner],
            ...     artifact_store=store
            ... )
        """
        config = config or DiscoveryAgentConfig(llm_model=llm_model)
        
        # Create LLM backend
        llm = ChatModel.from_name(llm_model)
        
        # Create memory
        memory = SlidingMemory(
            config=SlidingMemoryConfig(size=config.memory_size)
        )
        
        # Discovery role and instructions
        role = "Workload Discovery Agent"
        description = "Expert workload discovery agent specializing in infrastructure analysis"
        
        # System instructions (replaces system_prompt)
        system_instructions = """You are an expert workload discovery agent specializing in infrastructure analysis.

Your mission is to discover and analyze workloads running on target infrastructure resources.

## Your Capabilities

1. **Port Scanning**: Identify open ports and listening services
2. **Process Analysis**: Examine running processes and their characteristics  
3. **Application Detection**: Correlate data to identify applications and versions

## Available Tools

You have access to MCP tools for:
- `scan_ports`: Scan for open ports on a target
- `scan_processes`: List running processes (requires SSH)
- `detect_applications`: Identify applications from ports/processes
- `get_os_info`: Retrieve operating system information

## Your Approach

1. **Analyze the Target**: Understand resource type and available information
2. **Plan Discovery**: Choose appropriate discovery methods based on resource type
3. **Execute Systematically**: Use tools in logical order (ports first, then processes)
4. **Aggregate Results**: Combine findings into comprehensive discovery
5. **Assess Quality**: Evaluate completeness and confidence of results

## Output Requirements

You MUST provide a complete DiscoveryArtifact with:
- All discovery results (ports, processes, applications)
- Confidence scores for findings (0.0-1.0)
- Clear reasoning for your discovery approach
- Quality assessment of the discovery (high/medium/low)
- Human-readable summary of findings

## Guidelines

- Start with less invasive methods (port scanning) before more invasive ones (process scanning)
- For databases, focus on connectivity and service detection
- For VMs, perform comprehensive discovery including processes
- Always explain your reasoning step-by-step
- Assess data quality and completeness honestly
- Handle errors gracefully and report them in the artifact
- Provide confidence scores based on evidence quality"""
        
        # Instructions for the agent
        instructions = [
            "Analyze the target resource information provided",
            "Determine the most appropriate discovery strategy based on resource type",
            "Execute discovery using available MCP tools systematically",
            "Aggregate and correlate all findings into a comprehensive view",
            "Assess confidence and data quality based on evidence",
            "Provide complete DiscoveryArtifact with all required fields"
        ]
        
        # Create RequirementAgent (using V1-compatible parameters)
        agent = RequirementAgent(
            name=config.name,
            llm=llm,
            memory=memory,
            tools=mcp_tools,
            role=role,
            description=description,
            instructions=instructions,
            notes=[
                "Use MCP tools systematically for discovery",
                "Provide confidence scores based on evidence quality",
                "Handle errors gracefully and report them"
            ],
            final_answer_as_tool=DiscoveryArtifact
        )
        
        logger.info(f"Created {config.name} with model: {llm_model}")
        return agent
    
    @staticmethod
    def create_validation_agent(
        llm_model: str,
        mcp_tools: List[MCPTool],
        artifact_store: ArtifactStore,
        config: Optional[ValidationAgentConfig] = None
    ) -> RequirementAgent:
        """
        Create validation agent with standard configuration.
        
        Args:
            llm_model: LLM model identifier
            mcp_tools: List of MCP tools for validation operations
            artifact_store: Shared artifact store for communication
            config: Optional custom configuration
            
        Returns:
            Configured RequirementAgent for validation planning and execution
        """
        config = config or ValidationAgentConfig(llm_model=llm_model)
        
        # Create LLM backend
        llm = ChatModel.from_name(llm_model)
        
        # Create memory
        memory = SlidingMemory(
            config=SlidingMemoryConfig(size=config.memory_size)
        )
        
        # Validation role and instructions
        role = "Validation Planning Agent"
        description = "Expert validation planning agent specializing in infrastructure validation"
        
        # System instructions (replaces system_prompt)
        system_instructions = """You are an expert validation planning agent specializing in infrastructure validation.

Your mission is to create comprehensive validation plans based on discovery results and execute them systematically.

## Your Capabilities

1. **Plan Creation**: Design optimal validation strategies based on discovery findings
2. **Check Definition**: Define specific validation checks with clear success criteria
3. **Tool Selection**: Choose appropriate MCP tools for each validation check
4. **Execution**: Execute validation checks and assess results

## Available Tools

You have access to MCP tools for:
- `check_service_status`: Verify service status and health
- `check_port_connectivity`: Test port accessibility
- `validate_database_connection`: Test database connectivity
- `check_application_health`: Verify application health endpoints
- `verify_configuration`: Check configuration files and settings

## Your Approach

1. **Analyze Discovery**: Review discovery artifact to understand what was found
2. **Plan Strategy**: Choose validation strategy (comprehensive, targeted, minimal)
3. **Define Checks**: Create specific validation checks with clear criteria
4. **Execute Plan**: Run validation checks systematically
5. **Assess Results**: Evaluate validation outcomes and quality

## Output Requirements

You MUST provide a complete ValidationArtifact with:
- Reference to discovery artifact used
- Complete list of validation checks
- Execution results for all checks
- Clear reasoning for validation strategy
- Quality assessment of the validation plan
- Coverage percentage and success metrics

## Guidelines

- Base validation plan on discovery findings
- Prioritize checks based on criticality and confidence
- Define clear success criteria for each check
- Execute checks in logical order (dependencies first)
- Handle failures gracefully and continue where possible
- Provide detailed reasoning for all decisions
- Assess plan quality and coverage honestly"""
        
        # Instructions for the agent
        instructions = [
            "Analyze the discovery artifact provided as input",
            "Design an appropriate validation strategy based on findings",
            "Create specific validation checks with clear success criteria",
            "Execute validation checks using available MCP tools",
            "Assess results and calculate success metrics",
            "Provide complete ValidationArtifact with all execution results"
        ]
        
        # Create RequirementAgent (using V1-compatible parameters)
        agent = RequirementAgent(
            name=config.name,
            llm=llm,
            memory=memory,
            tools=mcp_tools,
            role=role,
            description=description,
            instructions=instructions,
            notes=[
                "Base validation plan on discovery findings",
                "Define clear success criteria for each check",
                "Handle failures gracefully and continue where possible"
            ],
            final_answer_as_tool=ValidationArtifact
        )
        
        logger.info(f"Created {config.name} with model: {llm_model}")
        return agent
    
    @staticmethod
    def create_evaluation_agent(
        llm_model: str,
        artifact_store: ArtifactStore,
        config: Optional[AgentConfig] = None
    ) -> RequirementAgent:
        """
        Create evaluation agent with standard configuration.
        
        Args:
            llm_model: LLM model identifier
            artifact_store: Shared artifact store for communication
            config: Optional custom configuration
            
        Returns:
            Configured RequirementAgent for result evaluation
        """
        config = config or AgentConfig(
            name="Evaluation Agent V2",
            llm_model=llm_model,
            temperature=0.3  # Higher for nuanced evaluation
        )
        
        # Create LLM backend
        llm = ChatModel.from_name(llm_model)
        
        # Create memory
        memory = SlidingMemory(
            config=SlidingMemoryConfig(size=config.memory_size)
        )
        
        # Evaluation role and instructions
        role = "Evaluation Agent"
        description = "Expert evaluation agent specializing in infrastructure validation assessment"
        
        # System instructions (replaces system_prompt)
        system_instructions = """You are an expert evaluation agent specializing in infrastructure validation assessment.

Your mission is to evaluate validation results and provide comprehensive assessments with recommendations.

## Your Capabilities

1. **Result Analysis**: Analyze validation results for completeness and quality
2. **Risk Assessment**: Identify potential risks and issues
3. **Recommendation Generation**: Provide actionable recommendations
4. **Quality Scoring**: Assess overall validation quality and confidence

## Your Approach

1. **Review Results**: Analyze validation artifact and execution results
2. **Assess Quality**: Evaluate validation completeness and reliability
3. **Identify Issues**: Find potential problems or gaps
4. **Generate Recommendations**: Provide specific, actionable advice
5. **Score Overall**: Provide overall assessment and confidence

## Output Requirements

You MUST provide a complete evaluation with:
- Overall assessment of validation quality
- Specific findings and recommendations
- Risk assessment and mitigation suggestions
- Confidence score in validation results
- Summary for stakeholders

## Guidelines

- Be thorough but practical in assessments
- Focus on actionable recommendations
- Consider business impact of findings
- Provide clear confidence levels
- Highlight both successes and areas for improvement"""
        
        # Instructions for the agent
        instructions = [
            "Analyze the validation artifact and results provided",
            "Assess the quality and completeness of validation",
            "Identify any issues, gaps, or risks",
            "Generate specific, actionable recommendations",
            "Provide overall assessment with confidence score"
        ]
        
        # Import evaluation artifact (would be defined separately)
        from ..artifacts.validation_artifact import ValidationArtifact as EvaluationResult
        
        # Create RequirementAgent (using V1-compatible parameters, evaluation doesn't need tools)
        agent = RequirementAgent(
            name=config.name,
            llm=llm,
            memory=memory,
            tools=[],  # Evaluation doesn't need MCP tools
            role=role,
            description=description,
            instructions=instructions,
            notes=[
                "Analyze validation results objectively",
                "Provide actionable recommendations",
                "Assess confidence based on evidence quality"
            ],
            final_answer_as_tool=EvaluationResult  # Reuse for now
        )
        
        logger.info(f"Created {config.name} with model: {llm_model}")
        return agent

# Made with Bob
