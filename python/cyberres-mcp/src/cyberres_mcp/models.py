
#
# Copyright contributors to the agentic-ai-cyberres project
#

from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List, Optional, Literal


class Target(BaseModel):
    """Represents a generic infrastructure target.

    Attributes
    ----------
    hostname : str
        Fully qualified host name or resolvable DNS name.
    ip : Optional[str]
        IP address of the target if known. If provided, tools may
        prefer to connect via IP rather than DNS lookup.
    os : Optional[str]
        Operating system family. Defaults to ``linux``. Can also
        indicate ``windows`` for future expansion.
    """

    hostname: str
    ip: Optional[str] = None
    os: Optional[str] = Field(default="linux", description="linux|windows")


class OracleInfo(BaseModel):
    """Connection info for an Oracle database instance.

    Tools accept either a full DSN or discrete host/port/service
    parameters. Credentials are represented via username/password
    fields, using Pydantic's SecretStr type for minimal protection.
    """

    dsn: Optional[str] = None  # e.g., "10.0.2.20/ORCLCDB"
    host: Optional[str] = None
    port: int = 1521
    service: Optional[str] = None
    user: Optional[str] = None
    password: Optional[SecretStr] = None


class MongoInfo(BaseModel):
    """Connection info for a MongoDB server or cluster.

    You can supply a full URI or discrete host/port/credentials.
    The database name defaults to ``admin`` which is suitable for
    administrative commands like ``ping``.
    """

    uri: Optional[str] = None  # e.g., "mongodb://user:pwd@host:27017/admin"
    host: Optional[str] = None
    port: int = 27017
    user: Optional[str] = None
    password: Optional[SecretStr] = None
    database: str = "admin"


class Acceptance(BaseModel):
    """Criteria that define a passing validation.

    For VMs, ``fs_max_pct`` caps maximum allowed disk usage
    percentage, and ``mem_min_free_pct`` defines minimum free memory.
    ``required_services`` lists systemd units that must be running.
    ``synthetic_txn`` signals whether destructive synthetic
    transactions should be attempted (disabled by default).
    """

    fs_max_pct: int = 85
    mem_min_free_pct: int = 10
    required_services: List[str] = Field(default_factory=list)
    synthetic_txn: bool = False


class ValidationRequest(BaseModel):
    """Top-level payload accepted by a hypothetical validator.

    The ``resourceType`` drives tool selection. Additional sections
    under ``target``, ``oracle``, or ``mongo`` contain all details
    necessary to establish connectivity. ``acceptance`` overrides
    profile defaults defined in the acceptance resources.
    """

    resourceType: Literal["vm", "oracle", "mongo"] = Field(description="vm|oracle|mongo")
    target: Optional[Target] = None
    oracle: Optional[OracleInfo] = None
    mongo: Optional[MongoInfo] = None
    acceptance: Optional[Acceptance] = None
    safeMode: bool = True


class CheckResult(BaseModel):
    """Represents the outcome of a single validation check."""

    id: str
    status: str  # PASS|FAIL|ERROR
    details: dict


class ValidationResult(BaseModel):
    """Aggregate result returned from a validator."""

    status: str
    score: Optional[int] = None
    checks: List[CheckResult]
    summary: Optional[str] = None
    remediation: Optional[List[dict]] = None


class MCPMessage(BaseModel):
    protocol_version: str
    message_type: str
    source_agent: str
    target_agent: str


# ============================================================================
# Workload Discovery Models
# ============================================================================

from enum import Enum


class OSType(str, Enum):
    """Operating system types."""
    LINUX = "linux"
    WINDOWS = "windows"
    UNIX = "unix"
    UNKNOWN = "unknown"


class OSDistribution(str, Enum):
    """Linux distributions."""
    RHEL = "rhel"
    CENTOS = "centos"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    SUSE = "suse"
    ORACLE_LINUX = "oracle_linux"
    AMAZON_LINUX = "amazon_linux"
    ROCKY = "rocky"
    ALMA = "alma"
    UNKNOWN = "unknown"


class ApplicationCategory(str, Enum):
    """Application categories."""
    DATABASE = "database"
    WEB_SERVER = "web_server"
    APP_SERVER = "app_server"
    MIDDLEWARE = "middleware"
    CONTAINER = "container"
    ORCHESTRATION = "orchestration"
    MESSAGE_QUEUE = "message_queue"
    CACHE = "cache"
    SEARCH_ENGINE = "search_engine"
    MONITORING = "monitoring"
    SECURITY = "security"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class DetectionMethod(str, Enum):
    """Detection methodology used."""
    PROCESS_SCAN = "process_scan"
    PORT_SCAN = "port_scan"
    PACKAGE_MANAGER = "package_manager"
    CONFIG_FILE = "config_file"
    SERVICE_ENUMERATION = "service_enumeration"
    REGISTRY = "registry"
    FILE_SYSTEM = "file_system"
    NETWORK_BINDING = "network_binding"


class ConfidenceLevel(str, Enum):
    """Confidence in detection accuracy."""
    HIGH = "high"        # 90-100%
    MEDIUM = "medium"    # 70-89%
    LOW = "low"          # 50-69%
    UNCERTAIN = "uncertain"  # <50%


class OSInfo(BaseModel):
    """Operating system information."""
    os_type: OSType
    distribution: Optional[OSDistribution] = None
    version: Optional[str] = None
    kernel_version: Optional[str] = None
    architecture: Optional[str] = None  # x86_64, aarch64, etc.
    hostname: Optional[str] = None
    uptime_seconds: Optional[int] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    detection_methods: List[DetectionMethod] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class NetworkBinding(BaseModel):
    """Network port binding information."""
    port: int
    protocol: str = "tcp"  # tcp, udp
    address: str = "0.0.0.0"  # listening address
    state: Optional[str] = None  # LISTEN, ESTABLISHED, etc.


class ApplicationInstance(BaseModel):
    """Discovered application instance."""
    name: str
    category: ApplicationCategory
    version: Optional[str] = None
    vendor: Optional[str] = None
    
    # Detection metadata
    confidence: ConfidenceLevel
    detection_methods: List[DetectionMethod]
    
    # Process information (stored as dict for flexibility)
    process_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Network information
    network_bindings: List[NetworkBinding] = Field(default_factory=list)
    
    # Installation details
    install_path: Optional[str] = None
    config_files: List[str] = Field(default_factory=list)
    
    # Optional fields
    detection_timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ContainerInfo(BaseModel):
    """Container/orchestration information."""
    runtime: str  # docker, containerd, cri-o
    version: Optional[str] = None
    orchestrator: Optional[str] = None  # kubernetes, docker-swarm, nomad
    orchestrator_version: Optional[str] = None
    containers_running: Optional[int] = None
    images_count: Optional[int] = None


class WorkloadDiscoveryResult(BaseModel):
    """Complete workload discovery result."""
    target_host: str
    target_ip: Optional[str] = None
    discovery_timestamp: str
    discovery_duration_seconds: float
    
    # OS Information
    os_info: OSInfo
    
    # Discovered Applications
    applications: List[ApplicationInstance] = Field(default_factory=list)
    
    # Container Information
    container_info: Optional[ContainerInfo] = None
    
    # Summary Statistics
    total_applications: int = 0
    applications_by_category: Dict[str, int] = Field(default_factory=dict)
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    
    # Errors and Warnings
    errors: List[Dict[str, str]] = Field(default_factory=list)
    warnings: List[Dict[str, str]] = Field(default_factory=list)
    
    # Raw detection data (for debugging/LLM analysis)
    raw_detection_data: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryRequest(BaseModel):
    """Request parameters for workload discovery."""
    # Target information
    host: str
    ip: Optional[str] = None
    
    # Authentication
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_port: int = 22
    
    # Windows authentication (future)
    windows_user: Optional[str] = None
    windows_password: Optional[str] = None
    windows_domain: Optional[str] = None
    
    # Discovery options
    detect_os: bool = True
    detect_applications: bool = True
    detect_containers: bool = True
    scan_ports: bool = True
    port_range: Optional[str] = "1-65535"  # or specific: "80,443,3306,5432"
    
    # Performance tuning
    timeout_seconds: int = 300
    max_concurrent_checks: int = 10
    
    # Filtering
    include_categories: Optional[List[ApplicationCategory]] = None
    exclude_categories: Optional[List[ApplicationCategory]] = None
    min_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    
    # Optional context for additional metadata
    
    def create_ssh_executor(self):
        """
        Create an SSH executor function for running commands on the target host.
        
        Returns:
            Callable that executes SSH commands and returns (stdout, stderr, exit_code)
        
        Note: This method now uses the unified ssh_utils module for SSH connectivity.
        """
        from .plugins.ssh_utils import SSHExecutor
        
        # Create SSHExecutor instance with credentials from this ServerTarget
        executor = SSHExecutor(
            host=self.host,
            port=self.ssh_port,
            username=self.ssh_user,
            password=self.ssh_password,
            key_path=self.ssh_key_path
        )
        
        # Return the callable executor that matches the expected signature
        # SSHExecutor.create_executor() returns a callable with (stdout, stderr, exit_code)
        return executor.create_executor()
    context: Dict[str, Any] = Field(default_factory=dict)
