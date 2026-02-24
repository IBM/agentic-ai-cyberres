#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Classification agent for AI-powered resource classification."""

import logging
from typing import Optional, List
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from models import (
    WorkloadDiscoveryResult,
    ResourceClassification,
    ResourceCategory,
    ApplicationDetection
)
from classifier import ApplicationClassifier
from agents.base import AgentConfig, EnhancedAgent
from tool_coordinator import ToolCoordinator
from state_manager import StateManager, WorkflowState
from feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class ClassificationAnalysis(BaseModel):
    """AI-powered classification analysis."""
    category: ResourceCategory = Field(..., description="Resource category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    primary_application: Optional[str] = Field(None, description="Primary application name")
    secondary_applications: List[str] = Field(default_factory=list, description="Secondary applications")
    reasoning: str = Field(..., description="Reasoning for classification")
    recommended_validations: List[str] = Field(default_factory=list, description="Recommended validation types")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    key_indicators: List[str] = Field(default_factory=list, description="Key indicators for classification")


class ClassificationAgent(EnhancedAgent):
    """AI-powered classification agent with fallback to rule-based classification.
    
    This agent uses AI to analyze workload discovery results and classify resources
    into categories with confidence scores and recommendations.
    """
    
    SYSTEM_PROMPT = """You are a resource classification expert. Your role is to:
1. Analyze workload discovery results (ports, processes, applications)
2. Classify resources into appropriate categories
3. Provide confidence scores and reasoning
4. Recommend appropriate validation strategies

Resource Categories:
- DATABASE_SERVER: Hosts database systems (Oracle, MongoDB, PostgreSQL, MySQL, etc.)
- WEB_SERVER: Hosts web servers (Nginx, Apache, IIS, etc.)
- APPLICATION_SERVER: Hosts application servers (Tomcat, JBoss, WebLogic, etc.)
- CONTAINER_HOST: Hosts container platforms (Docker, Kubernetes, etc.)
- LOAD_BALANCER: Load balancing services (HAProxy, Nginx, F5, etc.)
- CACHE_SERVER: Caching services (Redis, Memcached, etc.)
- MESSAGE_BROKER: Message queuing systems (RabbitMQ, Kafka, etc.)
- FILE_SERVER: File storage and sharing services
- MONITORING_SERVER: Monitoring and observability tools
- UNKNOWN: Cannot determine category with confidence

Consider:
- Open ports and their typical uses
- Running processes and their purposes
- Detected applications and their roles
- Common patterns and configurations
- Security implications

Provide:
- Category with confidence score
- Primary and secondary applications
- Clear reasoning for classification
- Recommended validation types
- Risk assessment
- Key indicators that led to classification"""
    
    def __init__(
        self,
        mcp_client: Optional[any] = None,
        config: Optional[AgentConfig] = None,
        tool_coordinator: Optional[ToolCoordinator] = None,
        state_manager: Optional[StateManager] = None,
        feature_flags: Optional[FeatureFlags] = None
    ):
        """Initialize classification agent.
        
        Args:
            mcp_client: Optional MCP client (not used for classification)
            config: Agent configuration for Pydantic AI
            tool_coordinator: Optional tool coordinator
            state_manager: Optional state manager
            feature_flags: Optional feature flags
        """
        super().__init__(
            mcp_client=mcp_client or object(),  # Dummy client, not used
            name="classification",
            tool_coordinator=tool_coordinator,
            state_manager=state_manager,
            feature_flags=feature_flags
        )
        
        self.config = config or AgentConfig()
        
        # Create AI classification agent
        self.ai_agent = self.config.create_agent(
            result_type=ClassificationAnalysis,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        # Fallback to rule-based classifier
        self.fallback_classifier = ApplicationClassifier()
        
        self.log_step("Classification agent initialized")
    
    async def classify(
        self,
        discovery_result: WorkloadDiscoveryResult,
        workflow_id: Optional[str] = None
    ) -> ResourceClassification:
        """Classify resource based on discovery results.
        
        Args:
            discovery_result: Workload discovery results
            workflow_id: Optional workflow ID for state tracking
        
        Returns:
            ResourceClassification with category and confidence
        """
        self.log_step(f"Classifying resource: {discovery_result.host}")
        
        # Save state if state manager available
        if self.state_manager and workflow_id:
            await self.state_manager.transition_to(
                WorkflowState.CLASSIFICATION,
                {
                    "workflow_id": workflow_id,
                    "resource_host": discovery_result.host,
                    "ports_found": len(discovery_result.ports),
                    "processes_found": len(discovery_result.processes),
                    "applications_found": len(discovery_result.applications)
                }
            )
        
        # Check if AI classification is enabled
        use_ai = (
            self.feature_flags and
            self.feature_flags.is_enabled("ai_classification")
        )
        
        if use_ai:
            try:
                self.log_step("Using AI-powered classification")
                classification = await self._classify_with_ai(discovery_result)
                
                self.record_execution(
                    action="classification_complete",
                    result={
                        "host": discovery_result.host,
                        "category": classification.category.value,
                        "confidence": classification.confidence,
                        "method": "ai"
                    }
                )
                
                return classification
                
            except Exception as e:
                self.log_step(f"AI classification failed: {e}", level="warning")
                self.log_step("Falling back to rule-based classification")
        else:
            self.log_step("Using rule-based classification (AI disabled)")
        
        # Fallback to rule-based classification
        classification = self._classify_with_rules(discovery_result)
        
        self.record_execution(
            action="classification_complete",
            result={
                "host": discovery_result.host,
                "category": classification.category.value,
                "confidence": classification.confidence,
                "method": "rules"
            }
        )
        
        return classification
    
    async def _classify_with_ai(
        self,
        discovery_result: WorkloadDiscoveryResult
    ) -> ResourceClassification:
        """Classify using AI analysis.
        
        Args:
            discovery_result: Discovery results
        
        Returns:
            ResourceClassification
        """
        # Build prompt with discovery data
        prompt = self._build_classification_prompt(discovery_result)
        
        # Get AI analysis
        result = await self.ai_agent.run(prompt)
        analysis = result.data
        
        self.log_step(
            f"AI classification: {analysis.category.value} "
            f"(confidence: {analysis.confidence:.2%})"
        )
        
        # Convert to ResourceClassification
        primary_app = None
        if analysis.primary_application:
            primary_app = ApplicationDetection(
                name=analysis.primary_application,
                confidence=analysis.confidence,
                detection_method="ai_analysis"
            )
        
        secondary_apps = [
            ApplicationDetection(
                name=app,
                confidence=analysis.confidence * 0.8,  # Lower confidence for secondary
                detection_method="ai_analysis"
            )
            for app in analysis.secondary_applications
        ]
        
        return ResourceClassification(
            category=analysis.category,
            confidence=analysis.confidence,
            primary_application=primary_app,
            secondary_applications=secondary_apps,
            recommended_validations=analysis.recommended_validations,
            reasoning=analysis.reasoning
        )
    
    def _classify_with_rules(
        self,
        discovery_result: WorkloadDiscoveryResult
    ) -> ResourceClassification:
        """Classify using rule-based logic.
        
        Args:
            discovery_result: Discovery results
        
        Returns:
            ResourceClassification
        """
        self.log_step("Using rule-based classification")
        return self.fallback_classifier.classify(discovery_result)
    
    def _build_classification_prompt(
        self,
        discovery_result: WorkloadDiscoveryResult
    ) -> str:
        """Build prompt for AI classification.
        
        Args:
            discovery_result: Discovery results
        
        Returns:
            Prompt string
        """
        prompt_parts = [
            "Classify this resource based on the following discovery data:",
            f"\n## Resource Information",
            f"Host: {discovery_result.host}",
            f"Discovery Time: {discovery_result.discovery_time}",
        ]
        
        # Add port information
        if discovery_result.ports:
            prompt_parts.append(f"\n## Open Ports ({len(discovery_result.ports)})")
            for port in discovery_result.ports[:20]:  # Limit to first 20
                service = port.service or "unknown"
                prompt_parts.append(f"- Port {port.port}/{port.protocol}: {service}")
            if len(discovery_result.ports) > 20:
                prompt_parts.append(f"... and {len(discovery_result.ports) - 20} more ports")
        
        # Add process information
        if discovery_result.processes:
            prompt_parts.append(f"\n## Running Processes ({len(discovery_result.processes)})")
            for proc in discovery_result.processes[:15]:  # Limit to first 15
                prompt_parts.append(f"- {proc.name} (PID: {proc.pid})")
                if proc.command:
                    prompt_parts.append(f"  Command: {proc.command[:100]}")
            if len(discovery_result.processes) > 15:
                prompt_parts.append(f"... and {len(discovery_result.processes) - 15} more processes")
        
        # Add detected applications
        if discovery_result.applications:
            prompt_parts.append(f"\n## Detected Applications ({len(discovery_result.applications)})")
            for app in discovery_result.applications:
                prompt_parts.append(
                    f"- {app.name} (confidence: {app.confidence:.0%}, "
                    f"method: {app.detection_method})"
                )
                if app.version:
                    prompt_parts.append(f"  Version: {app.version}")
        
        prompt_parts.extend([
            "\n## Your Task",
            "Analyze the above data and provide:",
            "1. Resource category classification",
            "2. Confidence score (0.0-1.0)",
            "3. Primary and secondary applications",
            "4. Clear reasoning for your classification",
            "5. Recommended validation types",
            "6. Risk level assessment",
            "7. Key indicators that led to your classification"
        ])
        
        return "\n".join(prompt_parts)
    
    async def classify_batch(
        self,
        discovery_results: List[WorkloadDiscoveryResult],
        workflow_id: Optional[str] = None
    ) -> List[ResourceClassification]:
        """Classify multiple resources.
        
        Args:
            discovery_results: List of discovery results
            workflow_id: Optional workflow ID
        
        Returns:
            List of ResourceClassification
        """
        self.log_step(f"Classifying {len(discovery_results)} resources")
        
        classifications = []
        for discovery_result in discovery_results:
            try:
                classification = await self.classify(discovery_result, workflow_id)
                classifications.append(classification)
            except Exception as e:
                self.log_step(
                    f"Failed to classify {discovery_result.host}: {e}",
                    level="error"
                )
                # Add unknown classification on error
                classifications.append(ResourceClassification(
                    category=ResourceCategory.UNKNOWN,
                    confidence=0.0,
                    reasoning=f"Classification failed: {str(e)}"
                ))
        
        self.log_step(f"Classified {len(classifications)} resources")
        return classifications


# Made with Bob