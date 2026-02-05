"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Standardized error codes for MCP server tools.

This module defines error codes used across all plugins to provide
consistent error reporting and easier troubleshooting.
"""


class ErrorCode:
    """Standardized error codes for all MCP tools."""
    
    # Network errors (NET_xxx)
    NET_CONNECTION_TIMEOUT = "NET_001"
    NET_CONNECTION_REFUSED = "NET_002"
    NET_HOST_UNREACHABLE = "NET_003"
    NET_DNS_RESOLUTION_FAILED = "NET_004"
    
    # SSH errors (SSH_xxx)
    SSH_AUTH_FAILED = "SSH_001"
    SSH_CONNECTION_TIMEOUT = "SSH_002"
    SSH_CONNECTION_REFUSED = "SSH_003"
    SSH_KEY_INVALID = "SSH_004"
    SSH_EXEC_FAILED = "SSH_005"
    SSH_HOST_KEY_VERIFICATION_FAILED = "SSH_006"
    
    # VM validation errors (VM_xxx)
    VM_FILESYSTEM_FULL = "VM_001"
    VM_LOW_MEMORY = "VM_002"
    VM_SERVICE_NOT_RUNNING = "VM_003"
    VM_HIGH_LOAD = "VM_004"
    VM_VALIDATION_FAILED = "VM_005"
    
    # Oracle database errors (ORA_xxx)
    ORA_CONNECTION_FAILED = "ORA_001"
    ORA_AUTH_FAILED = "ORA_002"
    ORA_QUERY_FAILED = "ORA_003"
    ORA_TABLESPACE_FULL = "ORA_004"
    ORA_INSTANCE_DOWN = "ORA_005"
    ORA_THIN_MODE_DSN_REQUIRED = "ORA_006"
    ORA_DISCOVERY_FAILED = "ORA_007"
    
    # MongoDB errors (MONGO_xxx)
    MONGO_CONNECTION_FAILED = "MONGO_001"
    MONGO_AUTH_FAILED = "MONGO_002"
    MONGO_QUERY_FAILED = "MONGO_003"
    MONGO_REPLICA_SET_UNHEALTHY = "MONGO_004"
    MONGO_COLLECTION_VALIDATION_FAILED = "MONGO_005"
    MONGO_PRIMARY_NOT_FOUND = "MONGO_006"
    
    # Input validation errors (INPUT_xxx)
    INPUT_MISSING_REQUIRED = "INPUT_001"
    INPUT_INVALID_FORMAT = "INPUT_002"
    INPUT_OUT_OF_RANGE = "INPUT_003"
    INPUT_INVALID_IP = "INPUT_004"
    INPUT_INVALID_PORT = "INPUT_005"
    
    # Parse errors (PARSE_xxx)
    PARSE_JSON_FAILED = "PARSE_001"
    PARSE_OUTPUT_FAILED = "PARSE_002"
    PARSE_CONFIG_FAILED = "PARSE_003"
    
    # Service check errors (SVC_xxx)
    SVC_NOT_RUNNING = "SVC_001"
    SVC_CHECK_FAILED = "SVC_002"
    SVC_MULTIPLE_MISSING = "SVC_003"
    
    # General errors (GEN_xxx)
    GEN_UNKNOWN_ERROR = "GEN_001"
    GEN_TIMEOUT = "GEN_002"
    GEN_PERMISSION_DENIED = "GEN_003"
    GEN_NOT_IMPLEMENTED = "GEN_004"


# Error code descriptions for documentation and logging
ERROR_DESCRIPTIONS = {
    # Network
    ErrorCode.NET_CONNECTION_TIMEOUT: "Network connection timed out",
    ErrorCode.NET_CONNECTION_REFUSED: "Connection refused by remote host",
    ErrorCode.NET_HOST_UNREACHABLE: "Host is unreachable",
    ErrorCode.NET_DNS_RESOLUTION_FAILED: "DNS resolution failed",
    
    # SSH
    ErrorCode.SSH_AUTH_FAILED: "SSH authentication failed",
    ErrorCode.SSH_CONNECTION_TIMEOUT: "SSH connection timed out",
    ErrorCode.SSH_CONNECTION_REFUSED: "SSH connection refused",
    ErrorCode.SSH_KEY_INVALID: "SSH key is invalid or cannot be read",
    ErrorCode.SSH_EXEC_FAILED: "SSH command execution failed",
    ErrorCode.SSH_HOST_KEY_VERIFICATION_FAILED: "SSH host key verification failed",
    
    # VM
    ErrorCode.VM_FILESYSTEM_FULL: "Filesystem usage exceeds threshold",
    ErrorCode.VM_LOW_MEMORY: "Available memory below threshold",
    ErrorCode.VM_SERVICE_NOT_RUNNING: "Required service is not running",
    ErrorCode.VM_HIGH_LOAD: "System load exceeds threshold",
    ErrorCode.VM_VALIDATION_FAILED: "VM validation failed",
    
    # Oracle
    ErrorCode.ORA_CONNECTION_FAILED: "Oracle database connection failed",
    ErrorCode.ORA_AUTH_FAILED: "Oracle authentication failed",
    ErrorCode.ORA_QUERY_FAILED: "Oracle query execution failed",
    ErrorCode.ORA_TABLESPACE_FULL: "Oracle tablespace usage exceeds threshold",
    ErrorCode.ORA_INSTANCE_DOWN: "Oracle instance is not running",
    ErrorCode.ORA_THIN_MODE_DSN_REQUIRED: "DSN required for thin mode connection",
    ErrorCode.ORA_DISCOVERY_FAILED: "Oracle instance discovery failed",
    
    # MongoDB
    ErrorCode.MONGO_CONNECTION_FAILED: "MongoDB connection failed",
    ErrorCode.MONGO_AUTH_FAILED: "MongoDB authentication failed",
    ErrorCode.MONGO_QUERY_FAILED: "MongoDB query execution failed",
    ErrorCode.MONGO_REPLICA_SET_UNHEALTHY: "MongoDB replica set is unhealthy",
    ErrorCode.MONGO_COLLECTION_VALIDATION_FAILED: "MongoDB collection validation failed",
    ErrorCode.MONGO_PRIMARY_NOT_FOUND: "MongoDB primary node not found",
    
    # Input
    ErrorCode.INPUT_MISSING_REQUIRED: "Required parameter is missing",
    ErrorCode.INPUT_INVALID_FORMAT: "Parameter format is invalid",
    ErrorCode.INPUT_OUT_OF_RANGE: "Parameter value is out of valid range",
    ErrorCode.INPUT_INVALID_IP: "IP address format is invalid",
    ErrorCode.INPUT_INVALID_PORT: "Port number is invalid",
    
    # Parse
    ErrorCode.PARSE_JSON_FAILED: "Failed to parse JSON output",
    ErrorCode.PARSE_OUTPUT_FAILED: "Failed to parse command output",
    ErrorCode.PARSE_CONFIG_FAILED: "Failed to parse configuration file",
    
    # Service
    ErrorCode.SVC_NOT_RUNNING: "Service is not running",
    ErrorCode.SVC_CHECK_FAILED: "Service check failed",
    ErrorCode.SVC_MULTIPLE_MISSING: "Multiple required services are missing",
    
    # General
    ErrorCode.GEN_UNKNOWN_ERROR: "An unknown error occurred",
    ErrorCode.GEN_TIMEOUT: "Operation timed out",
    ErrorCode.GEN_PERMISSION_DENIED: "Permission denied",
    ErrorCode.GEN_NOT_IMPLEMENTED: "Feature not implemented",
}


def get_error_description(code: str) -> str:
    """Get human-readable description for an error code.
    
    Parameters
    ----------
    code : str
        Error code (e.g., "SSH_001")
    
    Returns
    -------
    str
        Human-readable description of the error
    """
    return ERROR_DESCRIPTIONS.get(code, "Unknown error code")


def format_error_message(code: str, details: str = "") -> str:
    """Format a complete error message with code and description.
    
    Parameters
    ----------
    code : str
        Error code
    details : str, optional
        Additional details about the error
    
    Returns
    -------
    str
        Formatted error message
    """
    description = get_error_description(code)
    if details:
        return f"{description}: {details}"
    return description

# Made with Bob
