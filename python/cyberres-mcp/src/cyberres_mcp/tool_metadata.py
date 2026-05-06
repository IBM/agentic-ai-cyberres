"""
Tool metadata for LLM-driven tool selection.

Provides structured metadata about tool compatibility, priorities, and validation layers
to help LLMs make better tool selection decisions.
"""

from typing import Dict, List, Any

# Tool Categories - groups tools by functionality
TOOL_CATEGORIES = {
    "network": ["tcp_portcheck"],
    "system": ["vm_linux_uptime_load_mem", "vm_linux_fs_usage", "vm_linux_services", "vm_validator"],
    "mongodb": ["db_mongo_connect", "db_mongo_rs_status", "db_mongo_ssh_ping", "db_mongo_ssh_rs_status", "validate_collection"],
    "oracle": ["db_oracle_connect", "db_oracle_tablespaces", "db_oracle_data_validation", "db_oracle_discover_and_validate", "db_oracle_discover_config"],
    "discovery": ["discover_os_only", "discover_applications", "get_raw_server_data", "discover_workload"],
}

# Tool Priorities - indicates importance of each tool
TOOL_PRIORITIES = {
    "critical": [
        "tcp_portcheck",           # Network connectivity is fundamental
        "db_mongo_connect",        # MongoDB connectivity check
        "db_oracle_connect",       # Oracle connectivity check
    ],
    "high": [
        "vm_linux_uptime_load_mem",  # System health is important
        "db_mongo_rs_status",        # Replica set status for MongoDB
        "db_oracle_tablespaces",     # Tablespace check for Oracle
    ],
    "medium": [
        "vm_linux_fs_usage",         # Disk space monitoring
        "vm_linux_services",         # Service status
        "validate_collection",       # MongoDB data validation
        "db_oracle_data_validation", # Oracle data validation
    ],
    "low": [
        "vm_validator",              # Legacy validator
        "discover_os_only",          # OS discovery
        "get_raw_server_data",       # Raw data collection
    ],
}

# Validation Layers - execution order for validation
TOOL_VALIDATION_LAYERS = {
    "network": ["tcp_portcheck"],
    "system": ["vm_linux_uptime_load_mem", "vm_linux_fs_usage", "vm_linux_services", "vm_validator"],
    "application": ["db_mongo_connect", "db_mongo_rs_status", "db_oracle_connect", "db_oracle_tablespaces"],
    "data": ["validate_collection", "db_oracle_data_validation"],
    "discovery": ["discover_os_only", "discover_applications", "get_raw_server_data", "discover_workload"],
}

# Resource-Tool Compatibility Matrix
RESOURCE_TOOL_COMPATIBILITY = {
    "mongodb": {
        "required": ["tcp_portcheck", "db_mongo_connect"],
        "recommended": [
            "vm_linux_uptime_load_mem",
            "vm_linux_fs_usage",
            "vm_linux_services",
            "db_mongo_rs_status",
        ],
        "optional": ["validate_collection"],
        "forbidden": ["db_oracle_*", "db_postgres_*"],
    },
    "oracle": {
        "required": ["tcp_portcheck", "db_oracle_connect"],
        "recommended": [
            "vm_linux_uptime_load_mem",
            "vm_linux_fs_usage",
            "vm_linux_services",
            "db_oracle_tablespaces",
        ],
        "optional": ["db_oracle_data_validation"],
        "forbidden": ["db_mongo_*", "db_postgres_*"],
    },
    "database_server": {
        "required": ["tcp_portcheck"],
        "recommended": [
            "vm_linux_uptime_load_mem",
            "vm_linux_fs_usage",
            "vm_linux_services",
        ],
        "optional": [],
        "forbidden": [],
    },
    "vm": {
        "required": ["tcp_portcheck", "vm_linux_uptime_load_mem"],
        "recommended": ["vm_linux_fs_usage", "vm_linux_services"],
        "optional": ["discover_os_only"],
        "forbidden": [],
    },
    "web_server": {
        "required": ["tcp_portcheck", "vm_linux_uptime_load_mem"],
        "recommended": ["vm_linux_fs_usage", "vm_linux_services"],
        "optional": [],
        "forbidden": ["db_mongo_*", "db_oracle_*"],
    },
    "application_server": {
        "required": ["tcp_portcheck", "vm_linux_uptime_load_mem"],
        "recommended": ["vm_linux_fs_usage", "vm_linux_services"],
        "optional": [],
        "forbidden": ["db_mongo_*", "db_oracle_*"],
    },
}

# Tool Dependencies - which tools should run before others
TOOL_DEPENDENCIES = {
    "db_mongo_connect": ["tcp_portcheck"],
    "db_mongo_rs_status": ["tcp_portcheck", "db_mongo_connect"],
    "validate_collection": ["tcp_portcheck", "db_mongo_connect"],
    "db_oracle_connect": ["tcp_portcheck"],
    "db_oracle_tablespaces": ["tcp_portcheck", "db_oracle_connect"],
    "db_oracle_data_validation": ["tcp_portcheck", "db_oracle_connect"],
    "vm_linux_uptime_load_mem": ["tcp_portcheck"],
    "vm_linux_fs_usage": ["tcp_portcheck"],
    "vm_linux_services": ["tcp_portcheck"],
}

# Tool Recommendations - tools that work well together
TOOL_RECOMMENDATIONS = {
    "db_mongo_connect": ["tcp_portcheck", "vm_linux_uptime_load_mem", "db_mongo_rs_status"],
    "db_oracle_connect": ["tcp_portcheck", "vm_linux_uptime_load_mem", "db_oracle_tablespaces"],
    "vm_linux_uptime_load_mem": ["tcp_portcheck", "vm_linux_fs_usage", "vm_linux_services"],
}


def get_tools_for_resource_type(resource_type: str, include_optional: bool = True) -> List[str]:
    """Get recommended tools for a specific resource type.
    
    Args:
        resource_type: Resource type (mongodb, oracle, vm, etc.)
        include_optional: Whether to include optional tools
        
    Returns:
        List of tool names
    """
    if resource_type not in RESOURCE_TOOL_COMPATIBILITY:
        return []
    
    compat = RESOURCE_TOOL_COMPATIBILITY[resource_type]
    tools = compat["required"] + compat["recommended"]
    
    if include_optional:
        tools.extend(compat["optional"])
    
    return tools


def is_tool_compatible(tool_name: str, resource_type: str) -> bool:
    """Check if a tool is compatible with a resource type.
    
    Args:
        tool_name: Name of the tool
        resource_type: Resource type to check against
        
    Returns:
        True if compatible, False otherwise
    """
    if resource_type not in RESOURCE_TOOL_COMPATIBILITY:
        return True  # Unknown resource type, allow all tools
    
    compat = RESOURCE_TOOL_COMPATIBILITY[resource_type]
    
    # Check if tool is forbidden
    for forbidden_pattern in compat["forbidden"]:
        if forbidden_pattern.endswith("*"):
            prefix = forbidden_pattern[:-1]
            if tool_name.startswith(prefix):
                return False
        elif tool_name == forbidden_pattern:
            return False
    
    return True


def get_tool_priority(tool_name: str) -> str:
    """Get priority level for a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Priority level (critical, high, medium, low, unknown)
    """
    for priority, tools in TOOL_PRIORITIES.items():
        if tool_name in tools:
            return priority
    return "unknown"


def get_tool_validation_layer(tool_name: str) -> str:
    """Get validation layer for a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Validation layer (network, system, application, data, discovery, unknown)
    """
    for layer, tools in TOOL_VALIDATION_LAYERS.items():
        if tool_name in tools:
            return layer
    return "unknown"


def get_complete_metadata() -> Dict[str, Any]:
    """Get complete tool metadata for LLM consumption.
    
    Returns:
        Dictionary with all metadata
    """
    return {
        "categories": TOOL_CATEGORIES,
        "priorities": TOOL_PRIORITIES,
        "validation_layers": TOOL_VALIDATION_LAYERS,
        "compatibility": RESOURCE_TOOL_COMPATIBILITY,
        "dependencies": TOOL_DEPENDENCIES,
        "recommendations": TOOL_RECOMMENDATIONS,
    }

# Made with Bob
