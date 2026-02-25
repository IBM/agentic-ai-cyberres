# Implementation Guide: Infrastructure Validation Workflow

## Quick Start

This guide provides step-by-step instructions for implementing the new validation workflow with workload discovery integration.

## Prerequisites

1. **MCP Server Running**: Ensure cyberres-mcp server is running with workload discovery tools
2. **Python Environment**: Python 3.9+ with required dependencies
3. **Secrets Configuration**: Set up `secrets.json` with resource credentials

## Implementation Order

### Step 1: Update Data Models (models.py)

Add new data structures for workload discovery:

```python
# Add to models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

@dataclass
class PortInfo:
    """Information about an open port."""
    port: int
    protocol: str  # tcp, udp
    service: Optional[str] = None
    state: str = "open"
    banner: Optional[str] = None

@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    name: str
    cmdline: str
    user: str
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None

@dataclass
class ApplicationDetection:
    """Detected application information."""
    name: str
    version: Optional[str] = None
    confidence: float = 0.0  # 0.0 to 1.0
    detection_method: str = "signature"  # signature, port, process, manual
    evidence: Dict[str, Any] = field(default_factory=dict)
    category: Optional[str] = None  # database, web_server, app_server, etc.

@dataclass
class WorkloadDiscoveryResult:
    """Complete workload discovery results."""
    host: str
    ports: List[PortInfo] = field(default_factory=list)
    processes: List[ProcessInfo] = field(default_factory=list)
    applications: List[ApplicationDetection] = field(default_factory=list)
    discovery_time: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    
    def get_primary_application(self) -> Optional[ApplicationDetection]:
        """Get the application with highest confidence."""
        if not self.applications:
            return None
        return max(self.applications, key=lambda a: a.confidence)

class ResourceCategory(Enum):
    """Resource category based on primary application."""
    DATABASE_SERVER = "database_server"
    WEB_SERVER = "web_server"
    APPLICATION_SERVER = "application_server"
    MESSAGE_QUEUE = "message_queue"
    CACHE_SERVER = "cache_server"
    MIXED = "mixed"
    UNKNOWN = "unknown"

@dataclass
class ResourceClassification:
    """Classification of a resource based on discovered workloads."""
    category: ResourceCategory
    primary_application: Optional[ApplicationDetection] = None
    secondary_applications: List[ApplicationDetection] = field(default_factory=list)
    confidence: float = 0.0
    recommended_validations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "primary_application": self.primary_application.name if self.primary_application else None,
            "secondary_applications": [app.name for app in self.secondary_applications],
            "confidence": self.confidence,
            "recommended_validations": self.recommended_validations
        }

@dataclass
class ValidationStrategy:
    """Validation strategy for a classified resource."""
    name: str
    description: str
    validation_types: List[str]  # network, database, web, application
    acceptance_criteria: Dict[str, Any] = field(default_factory=dict)
    priority_checks: List[str] = field(default_factory=list)
```

### Step 2: Enhance MCP Client (mcp_client.py)

Add workload discovery tool methods:

```python
# Add to MCPClient class in mcp_client.py

async def workload_scan_ports(
    self,
    host: str,
    ssh_user: str,
    ssh_password: Optional[str] = None,
    ssh_key_path: Optional[str] = None,
    port_range: str = "1-65535",
    scan_type: str = "common"  # common, full, custom
) -> Dict[str, Any]:
    """Scan ports on remote host using workload discovery.
    
    Args:
        host: Target host
        ssh_user: SSH username
        ssh_password: SSH password (optional)
        ssh_key_path: SSH key path (optional)
        port_range: Port range to scan (default: common ports)
        scan_type: Type of scan (common, full, custom)
    
    Returns:
        Port scan results with detected services
    """
    args = {
        "host": host,
        "ssh_user": ssh_user,
        "scan_type": scan_type
    }
    if ssh_password:
        args["ssh_password"] = ssh_password
    if ssh_key_path:
        args["ssh_key_path"] = ssh_key_path
    if scan_type == "custom":
        args["port_range"] = port_range
    
    return await self.call_tool("workload_scan_ports", args)

async def workload_scan_processes(
    self,
    host: str,
    ssh_user: str,
    ssh_password: Optional[str] = None,
    ssh_key_path: Optional[str] = None
) -> Dict[str, Any]:
    """Scan running processes on remote host.
    
    Args:
        host: Target host
        ssh_user: SSH username
        ssh_password: SSH password (optional)
        ssh_key_path: SSH key path (optional)
    
    Returns:
        Process scan results
    """
    args = {
        "host": host,
        "ssh_user": ssh_user
    }
    if ssh_password:
        args["ssh_password"] = ssh_password
    if ssh_key_path:
        args["ssh_key_path"] = ssh_key_path
    
    return await self.call_tool("workload_scan_processes", args)

async def workload_detect_applications(
    self,
    host: str,
    ports: List[Dict[str, Any]],
    processes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Detect applications from port and process data.
    
    Args:
        host: Target host
        ports: Port scan results
        processes: Process scan results
    
    Returns:
        Application detection results with confidence scores
    """
    return await self.call_tool("workload_detect_applications", {
        "host": host,
        "ports": ports,
        "processes": processes
    })

async def workload_aggregate_results(
    self,
    host: str,
    port_results: Dict[str, Any],
    process_results: Dict[str, Any],
    app_detections: Dict[str, Any]
) -> Dict[str, Any]:
    """Aggregate all workload discovery results.
    
    Args:
        host: Target host
        port_results: Port scan results
        process_results: Process scan results
        app_detections: Application detection results
    
    Returns:
        Aggregated workload discovery results
    """
    return await self.call_tool("workload_aggregate_results", {
        "host": host,
        "port_results": port_results,
        "process_results": process_results,
        "app_detections": app_detections
    })
```

### Step 3: Create Application Classifier (classifier.py)

New file to classify resources based on discovered applications:

```python
# Create python/src/classifier.py

import logging
from typing import Dict, Any, List
from models import (
    WorkloadDiscoveryResult,
    ResourceClassification,
    ResourceCategory,
    ApplicationDetection
)

logger = logging.getLogger(__name__)


class ApplicationClassifier:
    """Classify resources based on discovered applications."""
    
    # Application category mappings
    DATABASE_APPS = {
        "oracle", "mongodb", "postgresql", "mysql", "mariadb",
        "mssql", "db2", "cassandra", "redis", "memcached"
    }
    
    WEB_SERVER_APPS = {
        "apache", "nginx", "iis", "lighttpd", "caddy"
    }
    
    APP_SERVER_APPS = {
        "tomcat", "jboss", "wildfly", "weblogic", "websphere",
        "glassfish", "jetty"
    }
    
    MESSAGE_QUEUE_APPS = {
        "rabbitmq", "kafka", "activemq", "artemis", "zeromq"
    }
    
    def __init__(self):
        """Initialize classifier."""
        self.confidence_threshold = 0.6
    
    def classify(
        self,
        discovery_result: WorkloadDiscoveryResult
    ) -> ResourceClassification:
        """Classify resource based on discovered applications.
        
        Args:
            discovery_result: Workload discovery results
        
        Returns:
            ResourceClassification with category and recommendations
        """
        if not discovery_result.applications:
            logger.warning(f"No applications detected on {discovery_result.host}")
            return ResourceClassification(
                category=ResourceCategory.UNKNOWN,
                confidence=0.0,
                recommended_validations=["basic_connectivity", "system_health"]
            )
        
        # Sort applications by confidence
        sorted_apps = sorted(
            discovery_result.applications,
            key=lambda a: a.confidence,
            reverse=True
        )
        
        primary_app = sorted_apps[0]
        secondary_apps = sorted_apps[1:3]  # Top 3 secondary apps
        
        # Determine category
        category = self._determine_category(primary_app)
        
        # Get recommended validations
        recommended_validations = self._get_recommended_validations(
            category,
            primary_app,
            secondary_apps
        )
        
        classification = ResourceClassification(
            category=category,
            primary_application=primary_app,
            secondary_applications=secondary_apps,
            confidence=primary_app.confidence,
            recommended_validations=recommended_validations
        )
        
        logger.info(
            f"Classified {discovery_result.host} as {category.value}",
            extra={
                "primary_app": primary_app.name,
                "confidence": primary_app.confidence
            }
        )
        
        return classification
    
    def _determine_category(
        self,
        primary_app: ApplicationDetection
    ) -> ResourceCategory:
        """Determine resource category from primary application."""
        app_name_lower = primary_app.name.lower()
        
        if any(db in app_name_lower for db in self.DATABASE_APPS):
            return ResourceCategory.DATABASE_SERVER
        elif any(web in app_name_lower for web in self.WEB_SERVER_APPS):
            return ResourceCategory.WEB_SERVER
        elif any(app in app_name_lower for app in self.APP_SERVER_APPS):
            return ResourceCategory.APPLICATION_SERVER
        elif any(mq in app_name_lower for mq in self.MESSAGE_QUEUE_APPS):
            return ResourceCategory.MESSAGE_QUEUE
        else:
            return ResourceCategory.UNKNOWN
    
    def _get_recommended_validations(
        self,
        category: ResourceCategory,
        primary_app: ApplicationDetection,
        secondary_apps: List[ApplicationDetection]
    ) -> List[str]:
        """Get recommended validation checks based on classification."""
        validations = ["network_connectivity", "system_health"]
        
        if category == ResourceCategory.DATABASE_SERVER:
            validations.extend([
                "database_connection",
                "database_health",
                "storage_usage",
                "replication_status"
            ])
        elif category == ResourceCategory.WEB_SERVER:
            validations.extend([
                "http_endpoint_check",
                "ssl_certificate_validation",
                "response_time_check"
            ])
        elif category == ResourceCategory.APPLICATION_SERVER:
            validations.extend([
                "application_health",
                "thread_pool_status",
                "memory_usage"
            ])
        elif category == ResourceCategory.MESSAGE_QUEUE:
            validations.extend([
                "queue_health",
                "message_flow_check",
                "cluster_status"
            ])
        
        # Add validations for secondary applications
        for app in secondary_apps:
            if app.confidence > 0.7:
                app_category = self._determine_category(app)
                if app_category == ResourceCategory.DATABASE_SERVER:
                    validations.append("secondary_database_check")
                elif app_category == ResourceCategory.WEB_SERVER:
                    validations.append("secondary_web_check")
        
        return list(set(validations))  # Remove duplicates
```

### Step 4: Create Validation Strategy Selector (validation_strategy.py)

```python
# Create python/src/validation_strategy.py

import logging
from typing import Dict, Any
from models import (
    ResourceClassification,
    ResourceCategory,
    ValidationStrategy,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo
)

logger = logging.getLogger(__name__)


class ValidationStrategySelector:
    """Select and configure validation strategies based on classification."""
    
    def __init__(self):
        """Initialize strategy selector."""
        pass
    
    def select_strategy(
        self,
        classification: ResourceClassification
    ) -> ValidationStrategy:
        """Select validation strategy based on classification.
        
        Args:
            classification: Resource classification
        
        Returns:
            ValidationStrategy with configured checks
        """
        category = classification.category
        
        if category == ResourceCategory.DATABASE_SERVER:
            return self._database_strategy(classification)
        elif category == ResourceCategory.WEB_SERVER:
            return self._web_server_strategy(classification)
        elif category == ResourceCategory.APPLICATION_SERVER:
            return self._application_server_strategy(classification)
        elif category == ResourceCategory.MESSAGE_QUEUE:
            return self._message_queue_strategy(classification)
        else:
            return self._default_strategy(classification)
    
    def _database_strategy(
        self,
        classification: ResourceClassification
    ) -> ValidationStrategy:
        """Strategy for database servers."""
        primary_app = classification.primary_application
        app_name = primary_app.name.lower() if primary_app else ""
        
        validation_types = ["network", "database", "storage"]
        priority_checks = [
            "database_connection",
            "database_health",
            "storage_usage"
        ]
        
        # Database-specific criteria
        acceptance_criteria = {
            "connection_timeout_s": 10,
            "storage_max_usage_pct": 85,
            "response_time_max_ms": 1000
        }
        
        if "oracle" in app_name:
            priority_checks.extend([
                "tablespace_usage",
                "archive_log_status",
                "listener_status"
            ])
            acceptance_criteria["tablespace_min_free_pct"] = 15
        elif "mongodb" in app_name:
            priority_checks.extend([
                "replica_set_status",
                "oplog_status",
                "collection_validation"
            ])
            acceptance_criteria["replication_lag_max_s"] = 10
        
        return ValidationStrategy(
            name="database_validation",
            description=f"Comprehensive validation for {primary_app.name if primary_app else 'database'} server",
            validation_types=validation_types,
            acceptance_criteria=acceptance_criteria,
            priority_checks=priority_checks
        )
    
    def _web_server_strategy(
        self,
        classification: ResourceClassification
    ) -> ValidationStrategy:
        """Strategy for web servers."""
        return ValidationStrategy(
            name="web_server_validation",
            description="Web server validation with endpoint and SSL checks",
            validation_types=["network", "web", "ssl"],
            acceptance_criteria={
                "http_response_time_max_ms": 500,
                "ssl_cert_expiry_min_days": 30,
                "http_status_code": [200, 301, 302]
            },
            priority_checks=[
                "http_endpoint_check",
                "https_endpoint_check",
                "ssl_certificate_validation",
                "response_time_check"
            ]
        )
    
    def _application_server_strategy(
        self,
        classification: ResourceClassification
    ) -> ValidationStrategy:
        """Strategy for application servers."""
        return ValidationStrategy(
            name="application_server_validation",
            description="Application server health and performance validation",
            validation_types=["network", "application", "performance"],
            acceptance_criteria={
                "thread_pool_usage_max_pct": 80,
                "memory_usage_max_pct": 85,
                "response_time_max_ms": 2000
            },
            priority_checks=[
                "application_health",
                "thread_pool_status",
                "memory_usage",
                "deployment_status"
            ]
        )
    
    def _message_queue_strategy(
        self,
        classification: ResourceClassification
    ) -> ValidationStrategy:
        """Strategy for message queue servers."""
        return ValidationStrategy(
            name="message_queue_validation",
            description="Message queue health and flow validation",
            validation_types=["network", "queue", "cluster"],
            acceptance_criteria={
                "queue_depth_max": 10000,
                "message_age_max_s": 300,
                "consumer_lag_max": 1000
            },
            priority_checks=[
                "queue_health",
                "message_flow_check",
                "cluster_status",
                "consumer_status"
            ]
        )
    
    def _default_strategy(
        self,
        classification: ResourceClassification
    ) -> ValidationStrategy:
        """Default strategy for unknown or mixed resources."""
        return ValidationStrategy(
            name="default_validation",
            description="Basic system health validation",
            validation_types=["network", "system"],
            acceptance_criteria={
                "cpu_usage_max_pct": 90,
                "memory_usage_max_pct": 85,
                "disk_usage_max_pct": 85
            },
            priority_checks=[
                "network_connectivity",
                "system_health",
                "resource_utilization"
            ]
        )
```

## Next Steps

After implementing these core components:

1. **Enhance discovery.py** with workload discovery integration
2. **Update recovery_validation_agent.py** to use the new workflow
3. **Enhance planner.py** to generate plans based on strategies
4. **Update evaluator.py** with application-specific criteria
5. **Enhance report_generator.py** to include discovery insights

## Testing Strategy

1. **Unit Tests**: Test each component independently
2. **Integration Tests**: Test complete workflow end-to-end
3. **Real-world Tests**: Test against actual infrastructure

## Example Usage

```python
# Example: Validate infrastructure with workload discovery

from recovery_validation_agent import RecoveryValidationAgent

agent = RecoveryValidationAgent()

# User prompt
prompt = """
Validate the infrastructure at 192.168.1.100.
SSH user is admin, password from secrets file.
"""

# Run validation workflow
report = await agent.run_validation_workflow(prompt)

# Results include:
# - Discovered applications
# - Resource classification
# - Validation results
# - Recommendations
```

## Troubleshooting

### Common Issues

1. **Workload discovery fails**: Check SSH connectivity and credentials
2. **Low confidence scores**: May need to update application signatures
3. **Validation timeouts**: Adjust timeout settings in MCP client
4. **Missing credentials**: Ensure secrets.json is properly configured

## Support

For questions or issues, refer to:
- Main plan: `VALIDATION_WORKFLOW_PLAN.md`
- MCP server docs: `python/cyberres-mcp/docs/`
- Existing code: `python/src/`