# MCP Tool Usage Examples

This document provides practical examples for using each tool in the CyberRes MCP server.

## Network Tools

### tcp_portcheck

Check TCP connectivity to one or more ports on a target host.

**Example 1: Check SSH port**
```json
{
  "tool": "tcp_portcheck",
  "args": {
    "host": "10.0.1.5",
    "ports": [22],
    "timeout_s": 2.0
  }
}
```

**Example 2: Check multiple database ports**
```json
{
  "tool": "tcp_portcheck",
  "args": {
    "host": "db-server.example.com",
    "ports": [1521, 27017, 5432],
    "timeout_s": 3.0
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "host": "10.0.1.5",
  "results": [
    {
      "port": 22,
      "ok": true,
      "latency_ms": 12.45,
      "error": null
    }
  ],
  "all_ok": true
}
```

## VM Linux Tools

### vm_linux_uptime_load_mem

Get system uptime, load averages, and memory information.

**Example with password authentication:**
```json
{
  "tool": "vm_linux_uptime_load_mem",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123"
  }
}
```

**Example with SSH key:**
```json
{
  "tool": "vm_linux_uptime_load_mem",
  "args": {
    "host": "vm-prod-01.example.com",
    "username": "ec2-user",
    "key_path": "/home/user/.ssh/id_rsa"
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "rc": 0,
  "stdout": "10:30:15 up 45 days, 3:22, 2 users, load average: 0.15, 0.20, 0.18\nMemTotal: 16384000 kB\nMemFree: 8192000 kB\nMemAvailable: 12288000 kB\nSwapTotal: 4096000 kB\nSwapFree: 4096000 kB",
  "stderr": ""
}
```

### vm_linux_fs_usage

Get filesystem usage statistics for all mounted filesystems.

**Example:**
```json
{
  "tool": "vm_linux_fs_usage",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123"
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "rc": 0,
  "filesystems": [
    {
      "filesystem": "/dev/sda1",
      "blocks_k": 51475068,
      "used_k": 25737534,
      "avail_k": 23099950,
      "use_pct": 53,
      "mountpoint": "/"
    },
    {
      "filesystem": "/dev/sdb1",
      "blocks_k": 103886028,
      "used_k": 72770220,
      "avail_k": 25815808,
      "use_pct": 74,
      "mountpoint": "/data"
    }
  ],
  "stderr": ""
}
```

### vm_linux_services

Check running systemd services and verify required services are active.

**Example:**
```json
{
  "tool": "vm_linux_services",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123",
    "required": ["sshd.service", "nginx.service", "postgresql.service"]
  }
}
```

**Expected Response (all services running):**
```json
{
  "ok": true,
  "rc": 0,
  "running": [
    "sshd.service",
    "nginx.service",
    "postgresql.service",
    "systemd-journald.service",
    "dbus.service"
  ],
  "required": ["sshd.service", "nginx.service", "postgresql.service"],
  "missing": [],
  "stderr": ""
}
```

**Expected Response (service missing):**
```json
{
  "ok": false,
  "error": {
    "message": "service(s) missing or ssh error",
    "code": "SERVICE_CHECK_FAILED"
  },
  "rc": 0,
  "running": ["sshd.service", "nginx.service"],
  "required": ["sshd.service", "nginx.service", "postgresql.service"],
  "missing": ["postgresql.service"],
  "stderr": ""
}
```

### vm_validator (Legacy)

Backwards-compatible VM validation tool.

**Example:**
```json
{
  "tool": "vm_validator",
  "args": {
    "vm_ip": "10.0.1.5",
    "ssh_user": "admin",
    "ssh_password": "secret123"
  }
}
```

## Oracle Database Tools

### db_oracle_connect

Connect to Oracle database and retrieve basic instance information via SSH.

**Example:**
```json
{
  "tool": "db_oracle_connect",
  "args": {
    "ssh_host": "10.0.2.20",
    "ssh_user": "oracle",
    "ssh_password": "ssh-secret",
    "sudo_oracle": false
  }
}
```

**Example using credential_id (no password in tool args):**
```json
{
  "tool": "db_oracle_connect",
  "args": {
    "ssh_host": "10.0.2.20",
    "ssh_user": "oracle",
    "credential_id": "oracle-ssh-prod",
    "sudo_oracle": true
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "instance_name": "ORCLCDB",
  "version": "19.0.0.0.0",
  "open_mode": "READ WRITE",
  "database_role": "PRIMARY"
}
```

### db_oracle_tablespaces

Get tablespace usage information via SSH.

**Example:**
```json
{
  "tool": "db_oracle_tablespaces",
  "args": {
    "ssh_host": "10.0.2.20",
    "ssh_user": "oracle",
    "ssh_password": "ssh-secret",
    "sudo_oracle": false
  }
}
```

**Example using credential_id (no password in tool args):**
```json
{
  "tool": "db_oracle_tablespaces",
  "args": {
    "ssh_host": "10.0.2.20",
    "ssh_user": "oracle",
    "credential_id": "oracle-ssh-prod",
    "sudo_oracle": true
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "tablespaces": [
    {
      "tablespace_name": "SYSTEM",
      "used_pct": 75.23,
      "free_mb": 512.45
    },
    {
      "tablespace_name": "SYSAUX",
      "used_pct": 68.91,
      "free_mb": 1024.78
    },
    {
      "tablespace_name": "USERS",
      "used_pct": 45.12,
      "free_mb": 2048.33
    }
  ]
}
```

### db_oracle_data_validation

Validate Oracle data integrity and post-recovery production readiness via SSH.

**Example using credential_id (recommended):**
```json
{
  "tool": "db_oracle_data_validation",
  "args": {
    "ssh_host": "10.0.2.20",
    "ssh_user": "oracle",
    "credential_id": "oracle-ssh-prod",
    "sudo_oracle": true
  }
}
```

**Expected Response (shape):**
```json
{
  "ok": true,
  "production_ready": true,
  "overall_status": "PASS_WITH_WARNINGS",
  "summary": {
    "total_checks": 12,
    "passed": 10,
    "warnings": 2,
    "failed": 0
  },
  "checks": [
    {
      "name": "database_block_corruption",
      "status": "PASS",
      "observed": 0,
      "expected": "0"
    }
  ],
  "metrics": {
    "corrupted_blocks": 0,
    "recover_file_count": 0,
    "critical_tablespace_count_95_pct": 0
  }
}
```

### db_oracle_discover_and_validate

Discover Oracle instances via SSH and optionally validate connectivity.

**Example:**
```json
{
  "tool": "db_oracle_discover_and_validate",
  "args": {
    "ssh_host": "10.0.2.20",
    "ssh_user": "oracle",
    "ssh_password": "oracle123",
    "oracle_user": "system",
    "oracle_password": "oracle123",
    "sudo_oracle": false
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "discoveries": {
    "sids": ["ORCLCDB", "ORCLPDB1"],
    "services": ["ORCLCDB", "ORCLPDB1"],
    "ports": [1521]
  },
  "candidate_dsns": [
    "10.0.2.20/ORCLCDB",
    "10.0.2.20/ORCLPDB1"
  ],
  "validation": {
    "dsn": "10.0.2.20/ORCLCDB",
    "instance_name": "ORCLCDB",
    "version": "19.0.0.0.0",
    "open_mode": "READ WRITE",
    "database_role": "PRIMARY"
  }
}
```

### db_oracle_discover_config

Discover comprehensive Oracle database configuration using direct connection (no SSH required).

**Example with service name:**
```json
{
  "tool": "db_oracle_discover_config",
  "args": {
    "host": "oracle-prod.example.com",
    "user": "system",
    "password": "oracle123",
    "service": "ORCL"
  }
}
```

**Example with SID:**
```json
{
  "tool": "db_oracle_discover_config",
  "args": {
    "host": "192.168.1.100",
    "user": "sys",
    "password": "syspass456",
    "port": 1521,
    "sid": "ORCL"
  }
}
```

**Example with auto-discovery:**
```json
{
  "tool": "db_oracle_discover_config",
  "args": {
    "host": "oracle-dev.local",
    "user": "system",
    "password": "devpass789"
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "instance": {
    "instance_name": "ORCL",
    "host_name": "oracle-prod-01",
    "version": "19.0.0.0.0",
    "status": "OPEN",
    "startup_time": "2024-01-15 08:30:00",
    "database_status": "ACTIVE",
    "instance_role": "PRIMARY_INSTANCE"
  },
  "database": {
    "name": "ORCL",
    "db_unique_name": "ORCL",
    "dbid": 1234567890,
    "open_mode": "READ WRITE",
    "log_mode": "ARCHIVELOG",
    "database_role": "PRIMARY",
    "platform_name": "Linux x86 64-bit"
  },
  "tablespaces": [
    {
      "tablespace_name": "SYSTEM",
      "total_mb": 1024.0,
      "used_mb": 850.5,
      "free_mb": 173.5,
      "used_pct": 83.06,
      "status": "ONLINE"
    }
  ],
  "memory": {
    "sga_target": {
      "value": "2147483648",
      "display_value": "2G"
    },
    "pga_aggregate_target": {
      "value": "536870912",
      "display_value": "512M"
    }
  },
  "datafiles": [
    {
      "file_name": "/u01/app/oracle/oradata/ORCL/system01.dbf",
      "tablespace_name": "SYSTEM",
      "size_mb": 1024.0,
      "status": "AVAILABLE",
      "autoextensible": "YES"
    }
  ],
  "redo_logs": [
    {
      "group#": 1,
      "thread#": 1,
      "sequence#": 1234,
      "size_mb": 200.0,
      "members": 2,
      "status": "CURRENT",
      "file_path": "/u01/app/oracle/oradata/ORCL/redo01.log"
    }
  ],
  "archive_destinations": [
    {
      "dest_name": "LOG_ARCHIVE_DEST_1",
      "status": "VALID",
      "destination": "/u01/app/oracle/archive",
      "space_limit_mb": 10240.0,
      "space_used_mb": 2048.5
    }
  ],
  "parameters": {
    "db_block_size": {
      "value": "8192",
      "display_value": "8192",
      "description": "Size of database block in bytes"
    },
    "processes": {
      "value": "300",
      "display_value": "300",
      "description": "user processes"
    }
  },
  "control_files": [
    {
      "name": "/u01/app/oracle/oradata/ORCL/control01.ctl",
      "status": null
    }
  ],
  "connection": {
    "host": "oracle-prod.example.com",
    "port": 1521,
    "service_name": "ORCL",
    "sid": null,
    "dsn": "oracle-prod.example.com:1521/ORCL",
    "user": "system"
  }
}
```

**Key Features:**
- No SSH access required - connects directly to Oracle database
- Comprehensive configuration discovery in a single call
- Auto-discovers service name if not provided (tries ORCL, XE, ORCLPDB1)
- Returns instance, database, tablespace, memory, datafile, redo log, and parameter information
- Useful for initial assessment, capacity planning, and documentation

## MongoDB Tools

### db_mongo_connect

Connect to MongoDB and verify connectivity via SSH.

**Example:**
```json
{
  "tool": "db_mongo_connect",
  "args": {
    "ssh_host": "10.0.2.30",
    "ssh_user": "mongodb",
    "ssh_password": "mongo123"
  }
}
```

**Example using credential_id (no password in tool args):**
```json
{
  "tool": "db_mongo_connect",
  "args": {
    "ssh_host": "10.0.2.30",
    "ssh_user": "mongodb",
    "credential_id": "mongo-prod"
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "ping": {"ok": 1},
  "version": "6.0.5",
  "connection": {
    "via": "ssh_mongo_shell",
    "mode": "ssh_local_noauth"
  }
}
```

### db_mongo_rs_status

Get replica set status via SSH.

**Example:**
```json
{
  "tool": "db_mongo_rs_status",
  "args": {
    "ssh_host": "10.0.2.30",
    "ssh_user": "mongodb",
    "credential_id": "mongo-prod"
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "set": "rs0",
  "myState": 1,
  "members": [
    {
      "name": "mongo-rs-01.example.com:27017",
      "health": 1,
      "state": 1,
      "stateStr": "PRIMARY"
    },
    {
      "name": "mongo-rs-02.example.com:27017",
      "health": 1,
      "state": 2,
      "stateStr": "SECONDARY"
    },
    {
      "name": "mongo-rs-03.example.com:27017",
      "health": 1,
      "state": 2,
      "stateStr": "SECONDARY"
    }
  ]
}
```

### db_mongo_ssh_ping

Backward-compatible alias for SSH MongoDB connectivity check.

**Example:**
```json
{
  "tool": "db_mongo_ssh_ping",
  "args": {
    "ssh_host": "10.0.2.30",
    "ssh_user": "mongodb",
    "credential_id": "mongo-prod"
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "ping": {"ok": 1},
  "connection": {
    "via": "ssh_mongo_shell"
  }
}
```

### db_mongo_ssh_rs_status

Backward-compatible alias for SSH replica set status check.

**Example:**
```json
{
  "tool": "db_mongo_ssh_rs_status",
  "args": {
    "ssh_host": "10.0.2.30",
    "ssh_user": "mongodb",
    "credential_id": "mongo-prod"
  }
}
```

### validate_collection

Validate a MongoDB collection's integrity.

**Example:**
```json
{
  "tool": "validate_collection",
  "args": {
    "ssh_host": "10.0.2.30",
    "ssh_user": "mongodb",
    "credential_id": "mongo-prod",
    "db_name": "production",
    "collection": "users",
    "full": true
  }
}
```

**Expected Response:**
```json
{
  "ok": true,
  "via": "ssh_mongo_shell",
  "db": "production",
  "collection": "users",
  "full": true,
  "validate": {
    "valid": true,
    "nIndexes": 5,
    "nrecords": 125000,
    "errors": [],
    "warnings": []
  }
}
```

## Workload Discovery Tools

### discover_os_only

Detect OS and distribution details only (fast path).

```json
{
  "tool": "discover_os_only",
  "args": {
    "host": "10.0.1.5",
    "ssh_user": "admin",
    "credential_id": "vm-prod"
  }
}
```

### discover_applications

Detect running applications with confidence scoring.

```json
{
  "tool": "discover_applications",
  "args": {
    "host": "10.0.1.5",
    "ssh_user": "admin",
    "credential_id": "vm-prod",
    "min_confidence": "medium"
  }
}
```

### get_raw_server_data

Collect raw host data for agent-side correlation.

```json
{
  "tool": "get_raw_server_data",
  "args": {
    "host": "10.0.1.5",
    "ssh_user": "admin",
    "credential_id": "vm-prod",
    "collect_processes": true,
    "collect_ports": true
  }
}
```

### discover_workload

Entry point for full workload discovery workflow.

```json
{
  "tool": "discover_workload",
  "args": {
    "host": "10.0.1.5",
    "ssh_user": "admin",
    "credential_id": "vm-prod",
    "detect_os": true,
    "detect_applications": true
  }
}
```

## Server Tools

### server_health

Check MCP server health and capabilities.

**Example:**
```json
{
  "tool": "server_health",
  "args": {}
}
```

**Expected Response:**
```json
{
  "ok": true,
  "status": "healthy",
  "version": "0.1.0",
  "plugins": ["network", "vm_linux", "oracle_db", "mongodb", "workload_discovery"],
  "capabilities": {
    "tools": 24,
    "resources": 3,
    "prompts": 3
  },
  "description": "Recovery validation MCP server for infrastructure health checks and workload discovery. Includes tools for OS detection and application discovery."
}
```

### list_resources

List available acceptance criteria resources.

```json
{
  "tool": "list_resources",
  "args": {}
}
```

### get_resource

Get one acceptance criteria resource by URI.

```json
{
  "tool": "get_resource",
  "args": {
    "resource_uri": "resource://acceptance/db-oracle"
  }
}
```

### list_prompts

List available orchestration prompts.

```json
{
  "tool": "list_prompts",
  "args": {}
}
```

### get_prompt

Get one orchestration prompt by name.

```json
{
  "tool": "get_prompt",
  "args": {
    "prompt_name": "planner"
  }
}
```

## Error Handling

All tools return a standardized response envelope:

**Success:**
```json
{
  "ok": true,
  "...": "tool-specific data"
}
```

**Failure:**
```json
{
  "ok": false,
  "error": {
    "message": "Descriptive error message",
    "code": "ERROR_CODE"
  },
  "...": "additional context"
}
```

Common error codes:
- `SSH_ERROR`: SSH connection or authentication failed
- `ORACLE_ERROR`: Oracle database error
- `MONGO_ERROR`: MongoDB error
- `INPUT_ERROR`: Invalid input parameters
- `SERVICE_CHECK_FAILED`: Required service not running
- `PARSE_ERROR`: Failed to parse command output
