"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Operating system detection module."""

from typing import Dict, Any, Optional, Callable, Tuple
import logging
import re
from datetime import datetime

logger = logging.getLogger("mcp.workload_discovery.os_detector")


class OSDetector:
    """Detects operating system type, version, and distribution."""
    
    # Distribution detection patterns
    DISTRIBUTION_PATTERNS = {
        "rhel": [r"Red Hat Enterprise Linux", r"RHEL"],
        "centos": [r"CentOS"],
        "ubuntu": [r"Ubuntu"],
        "debian": [r"Debian"],
        "suse": [r"SUSE", r"openSUSE"],
        "oracle_linux": [r"Oracle Linux"],
        "amazon_linux": [r"Amazon Linux"],
        "rocky": [r"Rocky Linux"],
        "alma": [r"AlmaLinux"]
    }
    
    def __init__(self):
        """Initialize OS detector."""
        self.detection_methods = []
    
    def detect(self, request: Any) -> Any:
        """
        Detect operating system information.
        
        Args:
            request: DiscoveryRequest containing connection details
            
        Returns:
            OSInfo object with detected OS details
        """
        from ...models import OSInfo, OSType, OSDistribution, DetectionMethod, ConfidenceLevel
        from ..ssh_utils import SSHExecutor
        
        # Create SSH executor using unified ssh_utils
        executor = SSHExecutor(
            host=request.host,
            port=request.ssh_port,
            username=request.ssh_user or "",
            password=request.ssh_password,
            key_path=request.ssh_key_path
        )
        
        # Create SSH execution wrapper that matches expected signature
        def ssh_exec(cmd: str) -> Tuple[int, str, str]:
            exit_code, stdout, stderr = executor.execute(cmd)
            return exit_code, stdout, stderr
        
        try:
            # Detect Linux
            os_info = self._detect_linux(ssh_exec)
            return os_info
            
        except Exception as e:
            logger.error(f"OS detection failed: {str(e)}")
            # Return unknown OS info
            return OSInfo(
                os_type=OSType.UNKNOWN,
                confidence=ConfidenceLevel.UNCERTAIN,
                detection_methods=[],
                raw_data={"error": str(e)}
            )
    
    def _detect_linux(self, ssh_exec: Callable) -> Any:
        """
        Detect Linux operating system details.
        
        Args:
            ssh_exec: Function to execute SSH commands
            
        Returns:
            OSInfo object
        """
        from ...models import OSInfo, OSType, OSDistribution, DetectionMethod, ConfidenceLevel
        
        detection_methods = []
        raw_data = {}
        
        # 1. Try /etc/os-release (most modern systems)
        rc, out, err = ssh_exec("cat /etc/os-release 2>/dev/null || true")
        if rc == 0 and out.strip():
            os_release_data = self._parse_os_release(out)
            raw_data["os_release"] = os_release_data
            detection_methods.append(DetectionMethod.FILE_SYSTEM)
        else:
            os_release_data = {}
        
        # 2. Try lsb_release
        rc, out, err = ssh_exec("lsb_release -a 2>/dev/null || true")
        if rc == 0 and out.strip():
            lsb_data = self._parse_lsb_release(out)
            raw_data["lsb_release"] = lsb_data
            detection_methods.append(DetectionMethod.FILE_SYSTEM)
        else:
            lsb_data = {}
        
        # 3. Try legacy release files
        rc, out, err = ssh_exec("cat /etc/redhat-release /etc/debian_version /etc/system-release 2>/dev/null || true")
        if out.strip():
            raw_data["legacy_release"] = out.strip()
        
        # 4. Get kernel version
        rc, out, err = ssh_exec("uname -r")
        kernel_version = out.strip() if rc == 0 else None
        raw_data["kernel_version"] = kernel_version
        
        # 5. Get full uname
        rc, out, err = ssh_exec("uname -a")
        if rc == 0:
            raw_data["uname"] = out.strip()
        
        # 6. Get architecture
        rc, out, err = ssh_exec("uname -m")
        architecture = out.strip() if rc == 0 else None
        raw_data["architecture"] = architecture
        
        # 7. Get hostname
        rc, out, err = ssh_exec("hostname")
        hostname = out.strip() if rc == 0 else None
        raw_data["hostname"] = hostname
        
        # 8. Get uptime
        rc, out, err = ssh_exec("cat /proc/uptime 2>/dev/null || true")
        uptime_seconds = None
        if rc == 0 and out.strip():
            try:
                uptime_seconds = int(float(out.split()[0]))
                raw_data["uptime_seconds"] = uptime_seconds
            except Exception:
                pass
        
        # Determine distribution
        distribution = self._detect_distribution(os_release_data, lsb_data, raw_data.get("legacy_release", ""))
        
        # Extract version
        version = self._extract_version(os_release_data, lsb_data)
        
        # Calculate confidence
        confidence = self._calculate_os_confidence(
            has_os_release=bool(os_release_data),
            has_lsb=bool(lsb_data),
            distribution_detected=distribution != OSDistribution.UNKNOWN
        )
        
        return OSInfo(
            os_type=OSType.LINUX,
            distribution=distribution,
            version=version,
            kernel_version=kernel_version,
            architecture=architecture,
            hostname=hostname,
            uptime_seconds=uptime_seconds,
            confidence=confidence,
            detection_methods=detection_methods,
            raw_data=raw_data
        )
    
    def _parse_os_release(self, content: str) -> Dict[str, str]:
        """
        Parse /etc/os-release file content.
        
        Args:
            content: Content of /etc/os-release
            
        Returns:
            Dictionary of key-value pairs
        """
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip('"').strip("'")
                result[key] = value
        return result
    
    def _parse_lsb_release(self, content: str) -> Dict[str, str]:
        """
        Parse lsb_release output.
        
        Args:
            content: Output from lsb_release -a
            
        Returns:
            Dictionary of key-value pairs
        """
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        return result
    
    def _detect_distribution(
        self,
        os_release: Dict[str, str],
        lsb_release: Dict[str, str],
        legacy_release: str
    ) -> Any:
        """
        Detect Linux distribution from available data.
        
        Args:
            os_release: Parsed /etc/os-release data
            lsb_release: Parsed lsb_release data
            legacy_release: Content from legacy release files
            
        Returns:
            OSDistribution enum value
        """
        from ...models import OSDistribution
        
        # Try os-release ID field first
        if "ID" in os_release:
            dist_id = os_release["ID"].lower()
            if dist_id in ["rhel", "redhat"]:
                return OSDistribution.RHEL
            elif dist_id == "centos":
                return OSDistribution.CENTOS
            elif dist_id == "ubuntu":
                return OSDistribution.UBUNTU
            elif dist_id == "debian":
                return OSDistribution.DEBIAN
            elif dist_id in ["sles", "opensuse", "suse"]:
                return OSDistribution.SUSE
            elif dist_id in ["ol", "oracle"]:
                return OSDistribution.ORACLE_LINUX
            elif dist_id in ["amzn", "amazon"]:
                return OSDistribution.AMAZON_LINUX
            elif dist_id == "rocky":
                return OSDistribution.ROCKY
            elif dist_id in ["almalinux", "alma"]:
                return OSDistribution.ALMA
        
        # Try NAME field
        if "NAME" in os_release:
            name = os_release["NAME"]
            for dist_key, patterns in self.DISTRIBUTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, name, re.IGNORECASE):
                        return OSDistribution[dist_key.upper()]
        
        # Try lsb_release
        if "Distributor ID" in lsb_release:
            dist_id = lsb_release["Distributor ID"].lower()
            if "ubuntu" in dist_id:
                return OSDistribution.UBUNTU
            elif "debian" in dist_id:
                return OSDistribution.DEBIAN
            elif "redhat" in dist_id or "rhel" in dist_id:
                return OSDistribution.RHEL
            elif "centos" in dist_id:
                return OSDistribution.CENTOS
            elif "suse" in dist_id:
                return OSDistribution.SUSE
        
        # Try legacy release content
        if legacy_release:
            for dist_key, patterns in self.DISTRIBUTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, legacy_release, re.IGNORECASE):
                        return OSDistribution[dist_key.upper()]
        
        return OSDistribution.UNKNOWN
    
    def _extract_version(
        self,
        os_release: Dict[str, str],
        lsb_release: Dict[str, str]
    ) -> Optional[str]:
        """
        Extract OS version from available data.
        
        Args:
            os_release: Parsed /etc/os-release data
            lsb_release: Parsed lsb_release data
            
        Returns:
            Version string or None
        """
        # Try VERSION_ID from os-release
        if "VERSION_ID" in os_release:
            return os_release["VERSION_ID"]
        
        # Try VERSION from os-release
        if "VERSION" in os_release:
            # Extract version number from string like "8.5 (Ootpa)"
            version = os_release["VERSION"]
            match = re.search(r'(\d+\.?\d*)', version)
            if match:
                return match.group(1)
            return version
        
        # Try lsb_release
        if "Release" in lsb_release:
            return lsb_release["Release"]
        
        return None
    
    def _calculate_os_confidence(
        self,
        has_os_release: bool,
        has_lsb: bool,
        distribution_detected: bool
    ) -> Any:
        """
        Calculate confidence level for OS detection.
        
        Args:
            has_os_release: Whether /etc/os-release was found
            has_lsb: Whether lsb_release data was found
            distribution_detected: Whether distribution was identified
            
        Returns:
            ConfidenceLevel enum value
        """
        from ...models import ConfidenceLevel
        
        # High confidence: os-release AND lsb AND distribution detected
        if has_os_release and has_lsb and distribution_detected:
            return ConfidenceLevel.HIGH
        # Medium confidence: os-release OR lsb, AND distribution detected
        elif (has_os_release or has_lsb) and distribution_detected:
            return ConfidenceLevel.MEDIUM
        # Low confidence: distribution detected but no standard files
        elif distribution_detected:
            return ConfidenceLevel.LOW
        # Uncertain: no distribution detected
        else:
            return ConfidenceLevel.UNCERTAIN

# Made with Bob
