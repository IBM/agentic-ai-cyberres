
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
    context: Dict[str, Any]
