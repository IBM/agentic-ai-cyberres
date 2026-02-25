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
from classification_cache import ClassificationCache

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
    
    # Few-shot examples for better classification accuracy
    CLASSIFICATION_EXAMPLES = """
# Classification Examples (Few-Shot Learning)

## Example 1: Oracle Database Server
**Input:**
- Ports: 1521 (Oracle), 5500 (Enterprise Manager)
- Processes: oracle, tnslsnr, ora_pmon, ora_smon
- Applications: Oracle Database 19c

**Output:**
- Category: DATABASE_SERVER
- Confidence: 0.95
- Primary Application: Oracle Database 19c
- Reasoning: Port 1521 is Oracle's default listener port, multiple Oracle-specific processes (pmon, smon) are running, and Oracle Database is explicitly detected.
- Recommended Validations: ["oracle_db_validation", "connection_test", "schema_validation"]
- Risk Level: high (database contains critical data)
- Key Indicators: ["port_1521", "oracle_processes", "tnslsnr_listener"]

## Example 2: Web Server with Application
**Input:**
- Ports: 80 (HTTP), 443 (HTTPS), 8080 (Alt HTTP)
- Processes: nginx, java, tomcat
- Applications: Nginx 1.18, Apache Tomcat 9.0

**Output:**
- Category: APPLICATION_SERVER
- Confidence: 0.85
- Primary Application: Apache Tomcat 9.0
- Secondary Applications: ["Nginx 1.18"]
- Reasoning: While Nginx is present on standard web ports, Tomcat on 8080 indicates this is primarily an application server with Nginx as reverse proxy.
- Recommended Validations: ["web_server_validation", "application_health_check", "ssl_certificate_check"]
- Risk Level: medium (public-facing application)
- Key Indicators: ["tomcat_process", "nginx_reverse_proxy", "port_8080"]

## Example 3: MongoDB Cluster Node
**Input:**
- Ports: 27017 (MongoDB), 27018 (Shard), 27019 (Config)
- Processes: mongod, mongos
- Applications: MongoDB 4.4

**Output:**
- Category: DATABASE_SERVER
- Confidence: 0.92
- Primary Application: MongoDB 4.4
- Reasoning: Multiple MongoDB ports indicate a cluster configuration. Presence of mongod and mongos processes confirms MongoDB deployment.
- Recommended Validations: ["mongo_db_validation", "cluster_health_check", "replication_status"]
- Risk Level: high (distributed database system)
- Key Indicators: ["port_27017", "mongod_process", "cluster_ports"]

## Example 4: Container Host
**Input:**
- Ports: 2375 (Docker), 6443 (Kubernetes API), 10250 (Kubelet)
- Processes: dockerd, kubelet, containerd
- Applications: Docker 20.10, Kubernetes 1.21

**Output:**
- Category: CONTAINER_HOST
- Confidence: 0.98
- Primary Application: Kubernetes 1.21
- Secondary Applications: ["Docker 20.10"]
- Reasoning: Kubernetes API port and kubelet process indicate K8s cluster node. Docker is the container runtime.
- Recommended Validations: ["container_health_check", "pod_validation", "cluster_connectivity"]
- Risk Level: critical (orchestration platform)
- Key Indicators: ["port_6443", "kubelet_process", "k8s_api"]

## Example 5: Unknown/Mixed Workload
**Input:**
- Ports: 22 (SSH), 3000 (Custom), 9090 (Custom)
- Processes: sshd, node, python3
- Applications: Node.js, Python

**Output:**
- Category: UNKNOWN
- Confidence: 0.45
- Primary Application: Node.js
- Secondary Applications: ["Python"]
- Reasoning: Custom ports and generic processes don't match known patterns. Could be development server or custom application.
- Recommended Validations: ["basic_connectivity", "process_validation"]
- Risk Level: low (unclear purpose, needs investigation)
- Key Indicators: ["custom_ports", "generic_processes", "no_clear_pattern"]
"""
    
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
        
        # Day 4: Initialize classification cache
        self.cache = ClassificationCache(ttl=3600, max_size=1000)
        
        self.log_step("Classification agent initialized with caching")
    
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
        
        # Day 4: Check cache first if caching is enabled
        if (self.feature_flags and
            self.feature_flags.is_enabled("classification_caching")):
            
            cached_result = self.cache.get(discovery_result)
            if cached_result:
                self.log_step(f"Using cached classification (hit rate: {self.cache.get_hit_rate():.1f}%)")
                
                self.record_execution(
                    action="classification_complete",
                    result={
                        "host": discovery_result.host,
                        "category": cached_result.category.value,
                        "confidence": cached_result.confidence,
                        "method": "cache"
                    }
                )
                
                return cached_result
        
        # Check if AI classification is enabled
        use_ai = (
            self.feature_flags and
            self.feature_flags.is_enabled("ai_classification")
        )
        
        if use_ai:
            try:
                self.log_step("Using AI-powered classification")
                classification = await self._classify_with_ai(discovery_result)
                
                # Day 4: Cache the result
                if (self.feature_flags and
                    self.feature_flags.is_enabled("classification_caching")):
                    self.cache.set(discovery_result, classification)
                    self.log_step(f"Cached classification result (cache size: {len(self.cache._cache)})")
                
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
            "\n## Classification Examples",
            "Here are examples of how to classify different resource types:",
            self.CLASSIFICATION_EXAMPLES,
            "\n## Your Task",
            "Now analyze the resource data above and provide:",
            "1. Resource category classification",
            "2. Confidence score (0.0-1.0)",
            "3. Primary and secondary applications",
            "4. Clear reasoning for your classification",
            "5. Recommended validation types",
            "6. Risk level assessment",
            "7. Key indicators that led to your classification",
            "\nUse the examples above as a guide for your analysis format and reasoning depth."
        ])
        
        return "\n".join(prompt_parts)
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get classification cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache.get_stats()
    
    def clear_cache(self):
        """Clear classification cache."""
        self.cache.clear()
        self.log_step("Classification cache cleared")
    
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