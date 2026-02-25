# Oracle Configuration Discovery Tool

## Overview

The `db_oracle_discover_config` tool provides comprehensive Oracle database configuration discovery using only basic connection credentials (host, user, password). This tool is ideal for quickly understanding an Oracle database environment without requiring SSH access.

## Tool: db_oracle_discover_config

### Description
Discovers Oracle database configuration by connecting directly to the database and retrieving comprehensive information including instance details, database properties, tablespace usage, memory configuration, datafiles, redo logs, and key parameters.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `host` | string | Yes | - | Oracle database host/IP address |
| `user` | string | Yes | - | Database username (typically SYS, SYSTEM, or DBA user) |
| `password` | string | Yes | - | Database password |
| `port` | integer | No | 1521 | Database port |
| `service` | string | No | - | Service name (e.g., ORCL, ORCLPDB1) |
| `sid` | string | No | - | SID (alternative to service name) |

### Features

The tool automatically discovers and returns:

1. **Instance Information**
   - Instance name, host, version
   - Status and startup time
   - Database status and role

2. **Database Information**
   - Database name and unique name
   - DBID, open mode, log mode
   - Database role and platform

3. **Tablespace Details**
   - All tablespaces with usage statistics
   - Total, used, and free space in MB
   - Usage percentage
   - Status information

4. **Memory Configuration**
   - SGA target and max size
   - PGA aggregate target
   - Memory target settings

5. **Datafiles**
   - File paths and tablespace assignments
   - Size in MB
   - Status and autoextensible settings

6. **Redo Log Configuration**
   - Log groups, threads, and sequences
   - Size and member count
   - Status and file paths

7. **Archive Log Destinations**
   - Destination names and paths
   - Space limits and usage

8. **Key Database Parameters**
   - Block size, cache size, pool size
   - Process and session limits
   - Recovery file destinations
   - Control file locations

9. **Control Files**
   - File paths and status

### Usage Examples

#### Example 1: Basic Discovery with Service Name

```json
{
  "host": "oracle-prod-01.example.com",
  "user": "system",
  "password": "SecurePass123",
  "service": "ORCL"
}
```

#### Example 2: Discovery with SID

```json
{
  "host": "192.168.1.100",
  "user": "sys",
  "password": "SysPassword456",
  "port": 1521,
  "sid": "ORCL"
}
```

#### Example 3: Auto-Discovery (tries common service names)

```json
{
  "host": "oracle-dev.local",
  "user": "system",
  "password": "DevPass789"
}
```

The tool will automatically try common service names like ORCL, XE, and ORCLPDB1.

#### Example 4: Non-standard Port

```json
{
  "host": "oracle-test.example.com",
  "user": "system",
  "password": "TestPass321",
  "port": 1522,
  "service": "TESTDB"
}
```

### Response Structure

```json
{
  "success": true,
  "data": {
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
      "host": "oracle-prod-01.example.com",
      "port": 1521,
      "service_name": "ORCL",
      "sid": null,
      "dsn": "oracle-prod-01.example.com:1521/ORCL",
      "user": "system"
    }
  }
}
```

### Error Handling

The tool provides specific error codes for common issues:

#### Authentication Error (ORA-01017)
```json
{
  "success": false,
  "error": "Invalid username/password",
  "code": "ORACLE_AUTH_ERROR"
}
```

#### Connection Error (ORA-12541, ORA-12514)
```json
{
  "success": false,
  "error": "Cannot connect to oracle-prod-01.example.com:1521. Check host, port, and service/SID.",
  "code": "ORACLE_CONNECTION_ERROR"
}
```

#### Missing Service/SID (DPY-3001)
```json
{
  "success": false,
  "error": "DPY-3001: Provide service name or SID for thin mode connection",
  "code": "ORACLE_THIN_MODE_DSN_REQUIRED"
}
```

### Best Practices

1. **Use Appropriate Credentials**: Use a user with sufficient privileges (SYSTEM, SYS, or DBA role) to query system views.

2. **Specify Service Name**: For best results, provide the service name explicitly rather than relying on auto-discovery.

3. **Security**: Never hardcode passwords. Use secure credential management.

4. **Network Access**: Ensure the Oracle listener is accessible from the client machine.

5. **Firewall Rules**: Verify that port 1521 (or custom port) is open.

### Comparison with Other Tools

| Tool | SSH Required | Discovers | Validates Connection |
|------|--------------|-----------|---------------------|
| `db_oracle_connect` | No | Basic info only | Yes |
| `db_oracle_tablespaces` | No | Tablespaces only | Yes |
| `db_oracle_discover_and_validate` | Yes | Services via listener | Optional |
| `db_oracle_discover_config` | No | **Comprehensive config** | Yes |

### Use Cases

1. **Initial Assessment**: Quickly understand a new Oracle environment
2. **Capacity Planning**: Review tablespace usage and memory configuration
3. **Documentation**: Generate comprehensive database configuration reports
4. **Troubleshooting**: Identify configuration issues or resource constraints
5. **Migration Planning**: Gather source database details for migration
6. **Compliance Audits**: Document database configuration for compliance

### Notes

- The tool uses Oracle's thin mode driver (no Oracle client installation required)
- Queries are read-only and do not modify the database
- Some queries require DBA privileges (e.g., dba_data_files, v$parameter)
- For RAC environments, connect to a specific instance or use SCAN listener
- The tool automatically handles different Oracle versions (11g, 12c, 18c, 19c, 21c)

### Troubleshooting

**Problem**: "Could not connect. Please provide service name or SID."
- **Solution**: Explicitly provide the `service` or `sid` parameter

**Problem**: "ORA-00942: table or view does not exist"
- **Solution**: User lacks privileges. Use SYSTEM or SYS user, or grant SELECT_CATALOG_ROLE

**Problem**: Connection timeout
- **Solution**: Check network connectivity, firewall rules, and listener status

**Problem**: "ORA-28040: No matching authentication protocol"
- **Solution**: Oracle version mismatch. Update oracledb driver or adjust SQLNET.ALLOWED_LOGON_VERSION