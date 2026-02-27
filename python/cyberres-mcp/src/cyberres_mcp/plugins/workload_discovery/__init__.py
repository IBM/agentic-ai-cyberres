"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Workload discovery package for automated OS and application detection."""

from typing import Dict, Any, Optional
import logging

from .os_detector import OSDetector
from .app_detector import ApplicationDetector
from .aggregator import ResultAggregator

__all__ = [
    "OSDetector",
    "ApplicationDetector",
    "ResultAggregator",
    "attach",
]

logger = logging.getLogger("mcp.workload_discovery")


def attach(mcp):
    """Register workload discovery tools onto the FastMCP instance."""
    
    try:
        from ..utils import ok, err, resolve_ssh_auth
    except Exception:
        from plugins.utils import ok, err, resolve_ssh_auth  # type: ignore
    
    @mcp.tool()
    def discover_os_only(
        host: str,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        ssh_port: int = 22
    ) -> Dict[str, Any]:
        """[Discovery][SSH] Detect operating system and distribution details only.
        
        Quickly identifies operating system type, version, and distribution
        without performing application discovery.
        
        Args:
            host: Target hostname or IP address
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH private key path (optional)
            ssh_port: SSH port (default: 22)
        
        Returns:
            OS information including type, distribution, version, kernel
        
        Example:
            >>> discover_os_only(
            ...     host="10.0.1.5",
            ...     ssh_user="admin",
            ...     ssh_password="secret"
            ... )
        """
        try:
            ssh_user, ssh_password, ssh_key_path, auth_err = resolve_ssh_auth(
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                credential_id=credential_id,
                logger=logger,
            )
            if auth_err:
                return err(auth_err, code="INPUT_ERROR", host=host)

            from ...models import DiscoveryRequest
            from .os_detector import OSDetector
            
            # Create discovery request
            request = DiscoveryRequest(
                host=host,
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                ssh_port=ssh_port,
                detect_os=True,
                detect_applications=False,
                detect_containers=False
            )
            
            # Initialize OS detector
            os_detector = OSDetector()
            
            # Perform OS detection
            logger.info(f"Starting OS detection for {host}")
            os_info = os_detector.detect(request)
            
            logger.info(
                f"OS detection completed for {host}",
                extra={
                    "os_type": os_info.os_type.value,
                    "distribution": os_info.distribution.value if os_info.distribution else None,
                    "confidence": os_info.confidence.value
                }
            )
            
            # Convert to dict for response
            result = os_info.dict()
            return ok(result)
            
        except Exception as e:
            logger.error(f"OS detection failed for {host}", extra={"error": str(e)})
            return err(
                f"OS detection failed: {str(e)}",
                code="OS_DETECTION_ERROR",
                host=host
            )
    
    @mcp.tool()
    def discover_applications(
        host: str,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        ssh_port: int = 22,
        min_confidence: str = "low"
    ) -> Dict[str, Any]:
        """[Discovery][SSH] Detect running applications with confidence scoring.
        
        Uses process scanning and port scanning to identify running applications
        such as databases, web servers, application servers, and more.
        
        Args:
            host: Target hostname or IP address
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH private key path (optional)
            ssh_port: SSH port (default: 22)
            min_confidence: Minimum confidence level: "high", "medium", "low", "uncertain"
        
        Returns:
            List of detected applications with confidence scores
        
        Example:
            >>> discover_applications(
            ...     host="10.0.1.5",
            ...     ssh_user="admin",
            ...     ssh_password="secret",
            ...     min_confidence="medium"
            ... )
        """
        try:
            ssh_user, ssh_password, ssh_key_path, auth_err = resolve_ssh_auth(
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                credential_id=credential_id,
                logger=logger,
            )
            if auth_err:
                return err(auth_err, code="INPUT_ERROR", host=host)

            from ...models import DiscoveryRequest, ConfidenceLevel
            from .app_detector import ApplicationDetector
            
            # Create discovery request
            request = DiscoveryRequest(
                host=host,
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                ssh_port=ssh_port,
                detect_os=False,
                detect_applications=True,
                detect_containers=False
            )
            
            # Initialize application detector
            app_detector = ApplicationDetector()
            
            # Perform application detection
            logger.info(f"Starting application detection for {host}")
            applications = app_detector.detect(request, request.create_ssh_executor())
            
            # Filter by minimum confidence
            min_conf_map = {
                "high": ConfidenceLevel.HIGH,
                "medium": ConfidenceLevel.MEDIUM,
                "low": ConfidenceLevel.LOW,
                "uncertain": ConfidenceLevel.UNCERTAIN
            }
            min_conf = min_conf_map.get(min_confidence.lower(), ConfidenceLevel.LOW)
            
            filtered_apps = app_detector.confidence_scorer.filter_by_confidence(
                applications, min_conf
            )
            
            # Get validation report
            validation = app_detector.validate_detections(filtered_apps)
            
            logger.info(
                f"Application detection completed for {host}",
                extra={
                    "total_detected": len(applications),
                    "after_filter": len(filtered_apps),
                    "valid": validation['valid_applications']
                }
            )
            
            # Convert to dict for response
            result = {
                "host": host,
                "total_applications": len(filtered_apps),
                "applications": [app.dict() for app in filtered_apps],
                "validation": validation,
                "detection_summary": {
                    "total_detected": len(applications),
                    "filtered_by_confidence": len(filtered_apps),
                    "min_confidence_threshold": min_confidence
                }
            }
            
            return ok(result)
            
        except Exception as e:
            logger.error(f"Application detection failed for {host}", extra={"error": str(e)})
            return err(
                f"Application detection failed: {str(e)}",
                code="APP_DETECTION_ERROR",
                host=host
            )
    
    @mcp.tool()
    def get_raw_server_data(
        host: str,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        ssh_port: int = 22,
        collect_processes: bool = True,
        collect_ports: bool = True,
        collect_configs: bool = False,
        config_paths: Optional[list] = None,
        collect_packages: bool = False,
        collect_services: bool = False
    ) -> Dict[str, Any]:
        """[Discovery][SSH] Collect raw host data for agent-side analysis.
        
        This tool collects raw data from the target server without performing
        signature-based detection. Use this when you need to:
        - Analyze unknown applications with LLM
        - Extract version information from complex output
        - Correlate multiple data sources
        - Perform custom detection logic
        
        The raw data can be passed to an LLM for intelligent interpretation
        of ambiguous or unknown applications.
        
        Args:
            host: Target hostname or IP address
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH private key path (optional)
            ssh_port: SSH port (default: 22)
            collect_processes: Collect process list (default: True)
            collect_ports: Collect listening ports (default: True)
            collect_configs: Collect configuration files (default: False)
            config_paths: List of config file paths to collect
            collect_packages: Collect installed packages (default: False)
            collect_services: Collect running services (default: False)
        
        Returns:
            Raw server data as structured dictionary
        
        Example:
            >>> get_raw_server_data(
            ...     host="10.0.1.5",
            ...     ssh_user="admin",
            ...     ssh_password="secret",
            ...     collect_processes=True,
            ...     collect_ports=True
            ... )
        """
        try:
            ssh_user, ssh_password, ssh_key_path, auth_err = resolve_ssh_auth(
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                credential_id=credential_id,
                logger=logger,
            )
            if auth_err:
                return err(auth_err, code="INPUT_ERROR", host=host)

            from ...models import DiscoveryRequest
            from .raw_data_collector import RawDataCollector
            from ..ssh_utils import SSHExecutor
            
            # Create discovery request
            request = DiscoveryRequest(
                host=host,
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                ssh_port=ssh_port,
                detect_os=False,
                detect_applications=False,
                detect_containers=False
            )
            
            # Create SSH executor
            executor = SSHExecutor(
                host=request.host,
                port=request.ssh_port,
                username=request.ssh_user or "",
                password=request.ssh_password,
                key_path=request.ssh_key_path
            )
            
            # Create wrapper for ssh_exec
            def ssh_exec(cmd: str):
                return executor.execute(cmd)
            
            # Prepare collection options
            options = {
                "collect_processes": collect_processes,
                "collect_ports": collect_ports,
                "collect_configs": collect_configs,
                "config_paths": config_paths or [],
                "collect_packages": collect_packages,
                "collect_services": collect_services
            }
            
            # Collect raw data
            logger.info(f"Starting raw data collection for {host}")
            collector = RawDataCollector()
            raw_data = collector.collect(ssh_exec, options)
            
            # Add metadata
            result = {
                "host": host,
                "data": raw_data,
                "collection_options": options,
                "data_types_collected": list(raw_data.keys())
            }
            
            logger.info(
                f"Raw data collection completed for {host}",
                extra={
                    "data_types": len(raw_data),
                    "has_error": "error" in raw_data
                }
            )
            
            return ok(result)
            
        except Exception as e:
            logger.error(f"Raw data collection failed for {host}", extra={"error": str(e)})
            return err(
                f"Raw data collection failed: {str(e)}",
                code="RAW_DATA_ERROR",
                host=host
            )
    
    @mcp.tool()
    def discover_workload(
        host: str,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        ssh_port: int = 22,
        detect_os: bool = True,
        detect_applications: bool = True,
        detect_containers: bool = True,
        scan_ports: bool = False,
        port_range: Optional[str] = None,
        timeout_seconds: int = 300,
        min_confidence: str = "low"
    ) -> Dict[str, Any]:
        """[Discovery][SSH] Entry point for full workload discovery workflow.
        
        This tool executes a multi-stage discovery process:
        1. OS Detection: Identifies operating system, version, and distribution
        2. Application Detection: Discovers enterprise applications using multiple methods
        3. Container Detection: Identifies container runtimes and orchestration
        4. Confidence Scoring: Assigns confidence levels to all discoveries
        
        Args:
            host: Target hostname or IP address
            ssh_user: SSH username for authentication
            ssh_password: SSH password (optional if using key)
            ssh_key_path: Path to SSH private key (optional if using password)
            ssh_port: SSH port (default: 22)
            detect_os: Enable OS detection (default: True)
            detect_applications: Enable application detection (default: True)
            detect_containers: Enable container detection (default: True)
            scan_ports: Enable port scanning (default: False, can be slow)
            port_range: Port range to scan, e.g., "1-1024" or "80,443,3306"
            timeout_seconds: Maximum time for discovery (default: 300)
            min_confidence: Minimum confidence level: "high", "medium", "low", "uncertain"
        
        Returns:
            Comprehensive discovery results with OS info, applications, and metadata
        
        Example:
            >>> discover_workload(
            ...     host="10.0.1.5",
            ...     ssh_user="admin",
            ...     ssh_password="secret",
            ...     detect_applications=True,
            ...     min_confidence="medium"
            ... )
        """
        try:
            ssh_user, ssh_password, ssh_key_path, auth_err = resolve_ssh_auth(
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                credential_id=credential_id,
                logger=logger,
            )
            if auth_err:
                return err(auth_err, code="INPUT_ERROR", host=host)

            # Implementation will be completed in Sprint 4
            return ok({
                "message": "Full workload discovery not yet implemented",
                "host": host,
                "status": "pending_implementation",
                "note": "Use discover_os_only and discover_applications separately. Full integrated discovery coming in Sprint 4."
            })
            
        except Exception as e:
            logger.error(f"Workload discovery failed for {host}", extra={"error": str(e)})
            return err(
                f"Workload discovery failed: {str(e)}",
                code="DISCOVERY_ERROR",
                host=host
            )

# Made with Bob
