# Recovery Validation MCP Server - Complete Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Tool Catalog](#tool-catalog)
5. [Use Cases](#use-cases)
6. [Setup Guide](#setup-guide)
7. [Testing & Validation](#testing--validation)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [Value Proposition](#value-proposition)

---

## Overview

The **Recovery Validation MCP Server** is a Model Context Protocol (MCP) server that provides comprehensive infrastructure validation capabilities for disaster recovery, migration validation, and ongoing health monitoring.

### What is MCP?

Model Context Protocol (MCP) is an open protocol that enables AI assistants (like Claude) to securely interact with external tools and data sources. This server exposes infrastructure validation tools through the MCP protocol.

### Key Features

- ✅ **24 Specialized Tools** across network, VM, Oracle, MongoDB, discovery, and server helper workflows
- 🔒 **Flexible Security** - SSH-first validation with optional direct Oracle configuration discovery
- 🌐 **Network-Aware** - Works in firewalled and restricted environments
- 📊 **Comprehensive** - From connectivity checks to data integrity validation
- 🤖 **AI-Ready** - Structured responses perfect for LLM consumption
- 🔍 **Auto-Discovery** - Automatically discovers Oracle and MongoDB configurations

### Supported Infrastructure

| Type | Technologies | Access Methods |
|------|-------------|----------------|
| **Operating Systems** | Linux (systemd-based) | SSH (password/key) |
| **Databases** | Oracle 11g-21c | SSH-based, Direct (config discovery) |
| **NoSQL** | MongoDB 4.x-7.x | SSH-based |
| **Network** | TCP connectivity | Socket-based |

---

## Quick Start

### Prerequisites

- Python 3.10+
- `uv` package manager
- Claude Desktop (for AI integration)

### Installation

```bash
# Clone repository
cd python/cyberres-mcp

# Install dependencies
uv sync

# Configure Claude Desktop
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

### First Test

```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

### Quick Validation Example

Ask Claude:
```
Check if the server at 10.0.1.5 is accessible on port 22 and 1521
```

Claude will use `tcp_portcheck` to verify connectivity.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Desktop (AI)                      │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol
┌────────────────────────┴────────────────────────────────────┐
│              Recovery Validation MCP Server                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastMCP Framework                                    │  │
│  │  - Tool Registration                                  │  │
│  │  - Resource Management                                │  │
│  │  - Prompt Templates                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Network  │  │   VM     │  │  Oracle  │  │ MongoDB  │  │
│  │  Tools   │  │  Tools   │  │  Tools   │  │  Tools   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    TCP Sockets    SSH/Paramiko   sqlplus/oracledb   mongosh via SSH
         │              │              │              │
         ▼              ▼              ▼              ▼
    [Network]      [Linux VMs]   [Oracle DBs]   [MongoDB]
```

### Plugin Architecture

Each plugin is self-contained and registers its tools via the `attach()` function:

```python
# plugins/oracle_db.py
def attach(mcp):
    @mcp.tool()
    def db_oracle_connect(...):
        # Tool implementation
        pass
```

### Security Model

1. **Credential Management**
   - Secrets stored in `secrets.json` (gitignored)
   - Sensitive data filtered from logs
   - No credentials in code

2. **Access Patterns**
   - SSH-based: Client → MCP → SSH → Database command execution on target host
   - Direct Oracle config mode: Client → MCP → Oracle DB (for `db_oracle_discover_config`)

3. **Network Security**
   - Supports firewalled environments
   - SSH tunneling for restricted access
   - Configurable timeouts

---

## Tool Catalog

### Network Tools (1)

#### tcp_portcheck
**Purpose:** Verify TCP connectivity to one or more ports

**Parameters:**
- `host` (str): Target hostname or IP
- `ports` (list[int]): List of ports to check
- `timeout_s` (float): Connection timeout (default: 1.0)

**Example:**
```json
{
  "host": "10.0.1.5",
  "ports": [22, 1521, 27017],
  "timeout_s": 2.0
}
```

**Use Cases:**
- Pre-validation network checks
- Firewall rule verification
- Service availability testing

---

### VM/Linux Tools (4)

#### vm_linux_uptime_load_mem
**Purpose:** Get system uptime, load averages, and memory statistics

**Parameters:**
- `host` (str): Target hostname/IP
- `username` (str): SSH username
- `password` (str, optional): SSH password
- `key_path` (str, optional): SSH private key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH creds

**Returns:** Uptime, load averages, memory info

**Use Cases:**
- System health assessment
- Resource utilization monitoring
- Post-recovery validation

#### vm_linux_fs_usage
**Purpose:** Get filesystem usage for all mounted filesystems

**Parameters:** Same as above

**Returns:** List of filesystems with usage percentages

**Use Cases:**
- Capacity planning
- Disk space validation
- Storage health checks

#### vm_linux_services
**Purpose:** List running services and verify required ones

**Parameters:**
- Same as above, plus:
- `required` (list[str], optional): Required service names

**Returns:** Running services, missing services

**Use Cases:**
- Application health verification
- Service dependency checks
- Post-deployment validation

#### vm_validator
**Purpose:** Legacy compatibility wrapper

**Parameters:**
- `vm_ip` (str): VM IP address
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH creds

**Use Cases:**
- Backward compatibility
- Simple pass/fail validation

---

### Oracle Database Tools (5)

#### db_oracle_connect
**Purpose:** SSH-based Oracle connectivity test and instance metadata check

**Parameters:**
- `ssh_host` (str): SSH target host
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH creds
- `sudo_oracle` (bool): Use sudo to oracle user

**Returns:** Instance name, version, open mode, role

**Use Cases:**
- Quick connectivity verification
- Pre-validation checks
- Connection troubleshooting

#### db_oracle_tablespaces
**Purpose:** SSH-based tablespace usage and free-space reporting

**Parameters:**
- `ssh_host` (str): SSH target host
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH creds
- `sudo_oracle` (bool): Use sudo to oracle user

Tablespace query is executed through SSH OS-auth mode:
`sqlplus -S '/ as sysdba'` on the remote host.

**Returns:** List of tablespaces with usage percentages

**Use Cases:**
- Capacity monitoring
- Storage planning
- Performance analysis

#### db_oracle_data_validation
**Purpose:** Post-recovery Oracle data-integrity and production-readiness validation

**Parameters:**
- `ssh_host` (str): SSH target host
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH creds
- `sudo_oracle` (bool): Use sudo to oracle user

**Returns:** `production_ready` verdict, check-level pass/warn/fail, and core corruption/recovery metrics

**Use Cases:**
- Recovery cutover go/no-go validation
- Corruption detection
- Readiness gating for production traffic

#### db_oracle_discover_and_validate
**Purpose:** SSH-based Oracle discovery and validation

**Parameters:**
- `ssh_host` (str): SSH target host
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `oracle_user` (str, optional): Oracle username
- `oracle_password` (str, optional): Oracle password
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH/Oracle creds
- `lsnrctl_path` (str): Path to lsnrctl (default: "lsnrctl")
- `sudo_oracle` (bool): Use sudo to oracle user

**Returns:** Discovered SIDs, services, ports, optional validation

**Use Cases:**
- Firewalled environments
- Discovery without direct DB access
- Security-restricted networks

#### db_oracle_discover_config ⭐ NEW
**Purpose:** Direct Oracle configuration discovery using DB credentials

**Parameters:**
- `host` (str): Database host
- `user` (str, optional): Database username
- `password` (str, optional): Database password
- `credential_id` (str, optional): Secret key in `secrets.json` for Oracle creds
- `port` (int): Database port (default: 1521)
- `service` (str, optional): Service name
- `sid` (str, optional): SID

**Returns:** Complete configuration including:
- Instance details
- Database information
- Tablespace usage
- Memory configuration
- Datafiles
- Redo logs
- Archive destinations
- Database parameters
- Control files

**Use Cases:**
- Initial environment assessment
- Migration validation
- Configuration documentation
- Capacity planning
- Compliance audits

---

### MongoDB Tools (5)

#### db_mongo_connect
**Purpose:** SSH-based MongoDB connectivity and version check

**Parameters:**
- `ssh_host` (str): SSH target host
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH and optional Mongo creds

**Returns:** Ping response, server version, hello/isMaster data, and discovery metadata

**Use Cases:**
- Quick connectivity check
- Version verification
- SSH-only validation paths

#### db_mongo_rs_status
**Purpose:** SSH-based replica-set status check

**Parameters:**
- `ssh_host` (str): SSH target host
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH and optional Mongo creds

**Returns:** Replica set name, state, member details

**Use Cases:**
- Cluster health monitoring
- Failover validation
- Replication status

#### db_mongo_ssh_ping
**Purpose:** Backward-compatible alias for `db_mongo_connect`

**Parameters:**
- `ssh_host` (str): SSH target
- `ssh_user` (str): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key
- `credential_id` (str, optional): Secret key in `secrets.json` for SSH and optional Mongo creds

**Returns:** Ping response

**Use Cases:**
- Localhost-bound MongoDB
- Firewalled environments
- Security-restricted access

#### db_mongo_ssh_rs_status
**Purpose:** Backward-compatible alias for `db_mongo_rs_status`

**Parameters:** Same as `db_mongo_ssh_ping`

**Returns:** Replica set status

**Use Cases:**
- Cluster health in restricted environments
- SSH-only access scenarios

#### validate_collection
**Purpose:** Validate MongoDB collection integrity over SSH

**Parameters:**
- Same as `db_mongo_ssh_ping`, plus:
- `db_name` (str): Database name
- `collection` (str): Collection name
- `full` (bool): Full validation (default: true)

**Returns:** Validation results, errors, warnings

**Use Cases:**
- Data integrity verification
- Post-migration validation
- Corruption detection

---

### Workload Discovery Tools (4)

#### discover_os_only
**Purpose:** Detect OS and distribution details only (fast path)

**Parameters:**
- `host` (str): Target host
- `ssh_user` (str, optional): SSH username
- `ssh_password` (str, optional): SSH password
- `ssh_key_path` (str, optional): SSH key path
- `credential_id` (str, optional): Secret key in `secrets.json`
- `ssh_port` (int): SSH port (default: 22)

#### discover_applications
**Purpose:** Detect running applications with confidence scoring

**Parameters:** Same SSH parameters as `discover_os_only`, plus:
- `min_confidence` (str): `high|medium|low|uncertain`

#### get_raw_server_data
**Purpose:** Collect raw host/process/port/config data for agent-side analysis

**Parameters:** Same SSH parameters as `discover_os_only`, plus collection toggles:
- `collect_processes`, `collect_ports`, `collect_configs`, `collect_packages`, `collect_services`
- `config_paths` (list, optional)

#### discover_workload
**Purpose:** Entry point for integrated workload discovery workflow

**Parameters:** Same SSH parameters as `discover_os_only`, plus:
- `detect_os`, `detect_applications`, `detect_containers`
- `scan_ports`, `port_range`, `timeout_seconds`, `min_confidence`

---

### Server Tools (5)

#### server_health
**Purpose:** Check MCP server health

**Parameters:** None

**Returns:** Server status, version, plugin list, and capability counts

**Use Cases:**
- Server connectivity verification
- Capability discovery
- Health monitoring

#### list_resources
**Purpose:** List available acceptance criteria resources

#### get_resource
**Purpose:** Get one acceptance criteria resource by URI

#### list_prompts
**Purpose:** List built-in orchestration prompts

#### get_prompt
**Purpose:** Get one orchestration prompt by name

---

## Use Cases

### Use Case 1: Post-Disaster Recovery Validation

**Scenario:** Data center failover completed, need to validate all recovered infrastructure

**Workflow:**
```
1. Network Validation
   └─> tcp_portcheck: Verify all services accessible

2. VM Validation
   ├─> vm_linux_uptime_load_mem: Check system health
   ├─> vm_linux_fs_usage: Verify disk space
   └─> vm_linux_services: Confirm critical services running

3. Oracle Validation
   ├─> db_oracle_discover_config: Full configuration check
   ├─> db_oracle_tablespaces: Verify storage capacity
   └─> db_oracle_data_validation: Production readiness and corruption checks

4. MongoDB Validation
   ├─> db_mongo_rs_status: Verify cluster health
   └─> validate_collection: Ensure data integrity
```

**Time Savings:** 2-3 hours → 10-15 minutes

**Value:** Automated, comprehensive, repeatable validation

---

### Use Case 2: Secure Production Environment

**Scenario:** Production environment with strict firewall rules, databases only accessible via SSH

**Workflow:**
```
1. Network Check
   └─> tcp_portcheck: Verify SSH port (22) accessible

2. Oracle Discovery (SSH-based)
   └─> db_oracle_discover_and_validate:
       - SSH to server
       - Discover Oracle instances
       - Optionally validate connectivity

3. MongoDB Check (SSH-based)
   ├─> db_mongo_ssh_ping: Verify MongoDB running
   └─> db_mongo_ssh_rs_status: Check cluster health
```

**Value:** Works in locked-down environments where direct DB access is prohibited

---

### Use Case 3: Cloud Migration Validation

**Scenario:** Migrated Oracle and MongoDB from on-premise to cloud, need to verify configuration matches

**Workflow:**
```
1. Source Environment (On-Premise)
   ├─> db_oracle_discover_config: Capture source config
   └─> db_mongo_rs_status: Capture source cluster state

2. Target Environment (Cloud)
   ├─> db_oracle_discover_config: Capture target config
   └─> db_mongo_rs_status: Capture target cluster state

3. Comparison
   └─> AI analyzes both configurations and identifies differences
```

**Value:** Automated configuration comparison, reduces migration errors

---

### Use Case 4: Continuous Health Monitoring

**Scenario:** Regular health checks for production infrastructure

**Workflow:**
```
Scheduled Checks (every 15 minutes):
├─> vm_linux_uptime_load_mem: Monitor system load
├─> vm_linux_fs_usage: Track disk usage trends
├─> db_oracle_tablespaces: Monitor tablespace growth
└─> db_mongo_rs_status: Verify cluster health

Alert on:
- Load average > threshold
- Disk usage > 85%
- Tablespace usage > 90%
- Replica set member down
```

**Value:** Proactive issue detection, automated monitoring

---

## Setup Guide

### Step 1: Install Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### Step 2: Clone and Setup

```bash
# Navigate to project
cd python/cyberres-mcp

# Install dependencies
uv sync

# Verify installation
uv run cyberres-mcp --help
```

### Step 3: Configure Secrets

```bash
# Copy example secrets file
cp secrets.example.json secrets.json

# Edit with your credentials
vi secrets.json
```

Example `secrets.json`:
```json
{
  "vm-prod": {
    "ssh": {
      "username": "admin",
      "password": "secret123"
    }
  },
  "oracle-ssh-prod": {
    "ssh": {
      "username": "root",
      "password": "ssh-secret"
    },
    "oracle": {
      "username": "system",
      "password": "oracle123"
    }
  },
  "mongo-prod": {
    "ssh": {
      "username": "mongodb",
      "password": "ssh-secret"
    },
    "mongo": {
      "username": "admin",
      "password": "mongo123"
    }
  }
}
```

### Step 4: Configure Claude Desktop

```bash
# Copy configuration
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
pkill -f "Claude" && open -a "Claude"
```

### Step 5: Verify Setup

Open Claude Desktop and ask:
```
Check the MCP server health
```

Expected response:
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
  }
}
```

---

## Testing & Validation

### Manual Testing with MCP Inspector

```bash
# Start MCP Inspector
npx @modelcontextprotocol/inspector uv --directory python/cyberres-mcp run cyberres-mcp

# Open browser to http://localhost:5173
# Test individual tools through the UI
```

### Automated Testing

```bash
# Run pre-demo tests
cd python/cyberres-mcp/demo
bash pre-demo-test.sh
```

### Test Scenarios

#### 1. Network Connectivity Test
```json
{
  "tool": "tcp_portcheck",
  "args": {
    "host": "10.0.1.5",
    "ports": [22, 1521, 27017],
    "timeout_s": 2.0
  }
}
```

#### 2. VM Health Check
```json
{
  "tool": "vm_linux_uptime_load_mem",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "credential_id": "vm-prod"
  }
}
```

#### 3. Oracle Discovery
```json
{
  "tool": "db_oracle_discover_config",
  "args": {
    "host": "10.0.2.20",
    "service": "ORCL",
    "credential_id": "oracle-ssh-prod"
  }
}
```

#### 4. MongoDB Cluster Check
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

---

## Troubleshooting

### Common Issues

#### 1. Connection Refused

**Error:** `DPY-6005: cannot connect to database. [Errno 61] Connection refused`

**Causes:**
- Oracle listener not running
- Firewall blocking port
- Incorrect host/port
- Network connectivity issue

**Solutions:**
```bash
# Check listener status
lsnrctl status

# Test network connectivity
ping <host>
telnet <host> 1521

# Check firewall
sudo firewall-cmd --list-ports
```

#### 2. SSH Authentication Failed

**Error:** `SSH_ERROR: Authentication failed`

**Solutions:**
- Verify username/password
- Check SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
- Verify SSH service running: `systemctl status sshd`

#### 3. Module Import Error

**Error:** `No module named 'settings'`

**Solution:**
```bash
# Reinstall dependencies
cd python/cyberres-mcp
uv sync --force

# Restart Claude Desktop
pkill -f "Claude" && open -a "Claude"
```

#### 4. Oracle Listener Shows No Services

**Error:** `The listener supports no services`

**Solution:**
```bash
# Start Oracle database
export ORACLE_SID=orcl
export ORACLE_HOME=/u01/app/oracle/homes/OraDB21Home1
sqlplus / as sysdba
SQL> STARTUP;
SQL> ALTER SYSTEM REGISTER;
SQL> EXIT;

# Verify
lsnrctl status
```

### Debug Mode

Enable detailed logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run server
uv run cyberres-mcp
```

### Getting Help

1. Check documentation: `python/cyberres-mcp/README.md`
2. Review tool examples: `python/cyberres-mcp/demo/tool-examples.md`
3. Check troubleshooting guide: `python/cyberres-mcp/TROUBLESHOOTING.md`

---

## Best Practices

### Security

1. **Never commit secrets**
   - Use `secrets.json` (gitignored)
   - Rotate credentials regularly
   - Use SSH keys instead of passwords when possible

2. **Principle of Least Privilege**
   - Use read-only database users
   - Limit SSH user permissions
   - Restrict network access

3. **Secure Communication**
   - Use SSH tunneling for sensitive connections
   - Enable SSL/TLS for database connections
   - Implement network segmentation

### Performance

1. **Connection Timeouts**
   - Set appropriate timeouts for your environment
   - Use shorter timeouts for quick checks
   - Increase timeouts for slow networks

2. **Parallel Execution**
   - Use AI to orchestrate parallel checks
   - Validate multiple systems simultaneously
   - Aggregate results efficiently

3. **Resource Management**
   - Close connections properly
   - Limit concurrent connections
   - Monitor server resource usage

### Reliability

1. **Error Handling**
   - Always check response `ok` field
   - Handle partial failures gracefully
   - Implement retry logic for transient errors

2. **Validation**
   - Verify connectivity before complex operations
   - Use `tcp_portcheck` as pre-validation
   - Validate credentials before bulk operations

3. **Monitoring**
   - Use `server_health` for MCP server monitoring
   - Log all validation activities
   - Track success/failure rates

---

## Value Proposition

### Why Use Recovery Validation MCP?

#### 1. **Time Savings**
- **Manual Process:** 2-3 hours per environment
- **With MCP:** 10-15 minutes per environment
- **ROI:** 85-90% time reduction

#### 2. **Consistency**
- Standardized validation process
- Repeatable checks
- Eliminates human error

#### 3. **Comprehensive**
- Single tool for multiple technologies
- Network, OS, and database validation
- From connectivity to data integrity

#### 4. **Flexible**
- Works in any environment
- Supports multiple access patterns
- Adapts to security requirements

#### 5. **AI-Powered**
- Natural language interface
- Intelligent orchestration
- Automated analysis and reporting

#### 6. **Production-Ready**
- Handles edge cases
- Comprehensive error messages
- Battle-tested in real environments

### Cost-Benefit Analysis

**Scenario:** 10 environments, monthly validation

| Metric | Manual | With MCP | Savings |
|--------|--------|----------|---------|
| Time per environment | 2.5 hours | 15 minutes | 2.25 hours |
| Total monthly time | 25 hours | 2.5 hours | 22.5 hours |
| Annual time savings | - | - | 270 hours |
| Cost savings (@ $100/hr) | - | - | $27,000/year |

**Additional Benefits:**
- Reduced downtime from faster validation
- Fewer errors from automated checks
- Better compliance documentation
- Improved disaster recovery confidence

---

## Conclusion

The Recovery Validation MCP Server provides a comprehensive, flexible, and production-ready solution for infrastructure validation. With 24 specialized tools, support for multiple access patterns, and AI-powered orchestration, it significantly reduces validation time while improving accuracy and consistency.

Whether you're validating disaster recovery, performing migrations, or monitoring production systems, this MCP server provides the tools you need to ensure your infrastructure is healthy and operational.

---

## Next Steps

1. **Setup:** Follow the [Setup Guide](#setup-guide)
2. **Test:** Run through [Testing & Validation](#testing--validation)
3. **Learn:** Review [Tool Catalog](#tool-catalog)
4. **Deploy:** Implement for your use case
5. **Optimize:** Follow [Best Practices](#best-practices)

## Additional Resources

- [Tool Analysis](TOOL_ANALYSIS.md) - Detailed tool comparison
- [Demo Script](demo/DEMO_SCRIPT.md) - Step-by-step demo
- [Tool Examples](demo/tool-examples.md) - Usage examples
- [Oracle Discovery Guide](demo/oracle-discovery-example.md) - Oracle-specific guide
- [MCP Inspector Guide](MCP_INSPECTOR_GUIDE.md) - Testing guide

---

**Version:** 1.0.0  
**Last Updated:** February 2026  
**License:** See LICENSE file
