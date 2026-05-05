"""
Discovery Artifact Schema

This module defines the artifact schema produced by the Discovery Agent.
It represents the complete output of workload discovery operations.

The DiscoveryArtifact is used for:
- Agent-to-agent communication (Discovery → Validation)
- Type-safe data transfer
- Validation and quality assurance
- Historical tracking and auditing
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Import from parent models module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from models import PortInfo, ProcessInfo, ApplicationDetection


class DiscoveryArtifact(BaseModel):
    """
    Artifact produced by Discovery Agent.
    
    This artifact contains the complete results of workload discovery,
    including ports, processes, applications, and quality metrics.
    
    It serves as the input for the Validation Agent, enabling clean
    agent-to-agent communication via artifact handoff.
    
    Attributes:
        resource_id: Unique identifier for the resource
        resource_type: Type of resource (vm, oracle_db, mongo_db)
        open_ports: List of discovered open ports
        running_processes: List of discovered running processes
        detected_applications: List of identified applications
        discovery_timestamp: When discovery was performed
        discovery_method: Method used (full, ports_only, processes_only)
        confidence_score: Overall confidence in discovery results (0.0-1.0)
        discovery_reasoning: LLM reasoning for discovery approach
        findings_summary: Human-readable summary of findings
        scan_completeness: How complete the scan was (0.0-1.0)
        data_quality: Quality assessment (high, medium, low)
        errors: Any errors encountered during discovery
    
    Example:
        >>> artifact = DiscoveryArtifact(
        ...     resource_id="vm-prod-web-01",
        ...     resource_type="vm",
        ...     open_ports=[
        ...         PortInfo(port=80, protocol="tcp", service="http"),
        ...         PortInfo(port=443, protocol="tcp", service="https")
        ...     ],
        ...     detected_applications=[
        ...         ApplicationDetection(
        ...             name="nginx",
        ...             version="1.18.0",
        ...             confidence=0.95
        ...         )
        ...     ],
        ...     confidence_score=0.92,
        ...     discovery_reasoning="Performed full scan...",
        ...     findings_summary="Web server running nginx with SSL",
        ...     scan_completeness=1.0,
        ...     data_quality="high"
        ... )
    """
    
    # Core identification
    resource_id: str = Field(
        description="Unique resource identifier"
    )
    resource_type: str = Field(
        description="Type: vm, oracle_db, mongo_db"
    )
    
    # Discovery results
    open_ports: List[PortInfo] = Field(
        default_factory=list,
        description="List of discovered open ports"
    )
    running_processes: List[ProcessInfo] = Field(
        default_factory=list,
        description="List of discovered running processes"
    )
    detected_applications: List[ApplicationDetection] = Field(
        default_factory=list,
        description="List of identified applications"
    )
    
    # Metadata
    discovery_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When discovery was performed"
    )
    discovery_method: str = Field(
        description="Method used: full, ports_only, processes_only, minimal"
    )
    
    # Quality metrics
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in discovery results"
    )
    scan_completeness: float = Field(
        ge=0.0,
        le=1.0,
        description="How complete the scan was (1.0 = fully complete)"
    )
    data_quality: str = Field(
        description="Quality assessment: high, medium, low"
    )
    
    # Reasoning and summary
    discovery_reasoning: str = Field(
        description="LLM reasoning for discovery approach and decisions"
    )
    findings_summary: str = Field(
        description="Human-readable summary of key findings"
    )
    
    # Error tracking
    errors: List[str] = Field(
        default_factory=list,
        description="Any errors encountered during discovery"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "resource_id": "vm-prod-web-01",
                "resource_type": "vm",
                "open_ports": [
                    {
                        "port": 80,
                        "protocol": "tcp",
                        "service": "http",
                        "state": "open"
                    },
                    {
                        "port": 443,
                        "protocol": "tcp",
                        "service": "https",
                        "state": "open"
                    }
                ],
                "running_processes": [
                    {
                        "pid": 1234,
                        "name": "nginx",
                        "command": "/usr/sbin/nginx -g daemon off;",
                        "user": "www-data"
                    }
                ],
                "detected_applications": [
                    {
                        "name": "nginx",
                        "version": "1.18.0",
                        "confidence": 0.95,
                        "detection_method": "port_analysis",
                        "evidence": ["Port 80 open", "Port 443 open", "Process nginx running"]
                    }
                ],
                "discovery_timestamp": "2026-03-17T18:00:00Z",
                "discovery_method": "full",
                "confidence_score": 0.92,
                "scan_completeness": 1.0,
                "data_quality": "high",
                "discovery_reasoning": "Performed comprehensive scan including port scanning and process analysis. High confidence due to clear port signatures and running processes.",
                "findings_summary": "Web server running nginx 1.18.0 with SSL enabled on ports 80 and 443",
                "errors": []
            }
        }
    
    def get_application_names(self) -> List[str]:
        """Get list of detected application names."""
        return [app.name for app in self.detected_applications]
    
    def get_high_confidence_applications(self, threshold: float = 0.8) -> List[ApplicationDetection]:
        """Get applications with confidence above threshold."""
        return [
            app for app in self.detected_applications
            if app.confidence >= threshold
        ]
    
    def has_errors(self) -> bool:
        """Check if any errors were encountered."""
        return len(self.errors) > 0
    
    def is_high_quality(self) -> bool:
        """Check if discovery is high quality."""
        return (
            self.data_quality == "high" and
            self.confidence_score >= 0.8 and
            self.scan_completeness >= 0.9
        )

# Made with Bob
