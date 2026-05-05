"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Result aggregation module."""

from datetime import datetime, timezone
from typing import List, Optional, Any
import logging
import time

logger = logging.getLogger("mcp.workload_discovery.aggregator")


class ResultAggregator:
    """Aggregates and formats discovery results."""
    
    def __init__(self):
        """Initialize result aggregator."""
        pass
    
    def aggregate(
        self,
        request: Any,
        os_info: Any,
        applications: List[Any],
        container_info: Optional[Any],
        start_time: float
    ) -> Any:
        """
        Aggregate discovery results into final output.
        
        Args:
            request: DiscoveryRequest
            os_info: OSInfo object
            applications: List of ApplicationInstance objects
            container_info: Optional ContainerInfo object
            start_time: Discovery start timestamp
            
        Returns:
            WorkloadDiscoveryResult object
        """
        from ...models import ConfidenceLevel, OSInfo, OSType, WorkloadDiscoveryResult

        if os_info is None:
            os_info = OSInfo(os_type=OSType.UNKNOWN, confidence=ConfidenceLevel.UNCERTAIN)

        applications_by_category: dict[str, int] = {}
        confidence_counts = {
            ConfidenceLevel.HIGH.value: 0,
            ConfidenceLevel.MEDIUM.value: 0,
            ConfidenceLevel.LOW.value: 0,
        }

        for app in applications:
            category = getattr(app, "category", "unknown")
            category_value = getattr(category, "value", str(category))
            applications_by_category[category_value] = applications_by_category.get(category_value, 0) + 1

            confidence = getattr(app, "confidence", ConfidenceLevel.UNCERTAIN)
            confidence_value = getattr(confidence, "value", str(confidence))
            if confidence_value in confidence_counts:
                confidence_counts[confidence_value] += 1

        duration = round(max(0.0, time.time() - start_time), 3)
        return WorkloadDiscoveryResult(
            target_host=request.host,
            target_ip=request.ip,
            discovery_timestamp=datetime.now(timezone.utc).isoformat(),
            discovery_duration_seconds=duration,
            os_info=os_info,
            applications=applications,
            container_info=container_info,
            total_applications=len(applications),
            applications_by_category=applications_by_category,
            high_confidence_count=confidence_counts[ConfidenceLevel.HIGH.value],
            medium_confidence_count=confidence_counts[ConfidenceLevel.MEDIUM.value],
            low_confidence_count=confidence_counts[ConfidenceLevel.LOW.value],
            warnings=[] if container_info is not None or not request.detect_containers else [
                {
                    "code": "CONTAINER_DISCOVERY_NOT_IMPLEMENTED",
                    "message": "Container discovery is not implemented yet.",
                }
            ],
            raw_detection_data={
                "detect_os": request.detect_os,
                "detect_applications": request.detect_applications,
                "detect_containers": request.detect_containers,
                "scan_ports": request.scan_ports,
                "port_range": request.port_range,
                "min_confidence": getattr(request.min_confidence, "value", str(request.min_confidence)),
            },
        )

# Made with Bob
