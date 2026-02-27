<!--
Copyright contributors to the agentic-ai-cyberres project
-->

# CyberRes MCP Server

MCP server for post-recovery validation of Linux VMs, Oracle databases, and MongoDB deployments.

## What This Server Does

- Validates connectivity and runtime health
- Performs recovery-readiness checks for Oracle and Mongo workloads
- Supports SSH-first operation for environments where DB ports are not externally reachable
- Provides acceptance resources and prompt templates for agent workflows

## Tool Count

- 24 tools
- 3 resources
- 3 prompts

## Quick Start

1. Install dependencies:

```bash
cd python/cyberres-mcp
uv add . --dev
```

2. Configure:

```bash
cp .env.example .env
cp secrets.example.json secrets.json
# Edit secrets.json for your environment
```

3. Start server:

```bash
uv run cyberres-mcp
```

Default endpoint (streamable-http): `http://0.0.0.0:8000/mcp`

## Configuration

Environment variables from `.env`:

```bash
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_TRANSPORT=streamable-http
SECRETS_FILE=secrets.json

# SSH host-key security
SSH_STRICT_HOST_KEY_CHECKING=true
SSH_TRUST_UNKNOWN_HOSTS=false
# SSH_KNOWN_HOSTS_FILE=/Users/you/.ssh/known_hosts
```

### SSH Security Behavior

- Loads system host keys by default
- Uses strict host-key checking by default (`RejectPolicy`)
- Optional TOFU only when `SSH_TRUST_UNKNOWN_HOSTS=true`
- Optional explicit known_hosts file via `SSH_KNOWN_HOSTS_FILE`

## Credentials and `credential_id`

Most SSH/DB tools support either:

- Direct parameters (`ssh_user`, `ssh_password`, etc.), or
- `credential_id` resolved from `secrets.json`

Example `secrets.json`:

```json
{
  "vm-prod": {
    "ssh": {
      "username": "admin",
      "password": "REDACTED",
      "key_path": "/home/admin/.ssh/id_rsa"
    }
  },
  "oracle-ssh-prod": {
    "ssh": {
      "username": "root",
      "password": "REDACTED"
    },
    "oracle": {
      "username": "system",
      "password": "REDACTED"
    }
  },
  "mongo-prod": {
    "ssh": {
      "username": "admin",
      "password": "REDACTED"
    },
    "mongo": {
      "username": "mongo_admin",
      "password": "REDACTED"
    }
  }
}
```

## Response Envelope

Success:

```json
{
  "ok": true,
  "...": "tool-specific payload"
}
```

Error:

```json
{
  "ok": false,
  "error": {
    "message": "Descriptive error",
    "code": "ERROR_CODE"
  }
}
```

## Tool Catalog

### Network

- `tcp_portcheck`

### VM Linux

- `vm_linux_uptime_load_mem`
- `vm_linux_fs_usage`
- `vm_linux_services`
- `vm_validator` (legacy)

### Oracle

- `db_oracle_connect`
- `db_oracle_tablespaces`
- `db_oracle_data_validation`
- `db_oracle_discover_and_validate`
- `db_oracle_discover_config`

### MongoDB

- `db_mongo_connect`
- `db_mongo_rs_status`
- `db_mongo_ssh_ping` (alias)
- `db_mongo_ssh_rs_status` (alias)
- `validate_collection`

### Workload Discovery

- `discover_os_only`
- `discover_applications`
- `get_raw_server_data`
- `discover_workload` (currently pending implementation)

### Server Utilities

- `server_health`
- `list_resources`
- `get_resource`
- `list_prompts`
- `get_prompt`

## How Each Tool Is Implemented

## 1. Network Tool

### `tcp_portcheck`

Implementation:
- Uses Python `socket.create_connection((host, port), timeout)` per requested port
- Measures latency in milliseconds for each attempt
- Returns per-port status and aggregate `all_ok`

## 2. VM Linux Tools

All VM tools run remote commands via shared SSH utility (`ssh_utils.SSHExecutor`) and support `credential_id`.

### `vm_linux_uptime_load_mem`

Implementation:
- Executes:
  - `uptime`
  - `cat /proc/meminfo | egrep 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree'`
- Returns raw output (`stdout`) plus exit status

### `vm_linux_fs_usage`

Implementation:
- Executes `df -P -k`
- Parses POSIX output into structured fields:
  - `filesystem`, `blocks_k`, `used_k`, `avail_k`, `use_pct`, `mountpoint`

### `vm_linux_services`

Implementation:
- Executes:
  - `systemctl list-units --type=service --state=running --no-legend --no-pager | awk '{print $1}'`
- Compares discovered running services against `required`
- Fails with `SERVICE_CHECK_FAILED` when required services are missing

### `vm_validator` (legacy)

Implementation:
- Executes:
  - `df -h /`
  - `systemctl is-active sshd || true`
- Returns `PASS` only when disk command succeeds and sshd is active

## 3. Oracle Tools

Oracle SSH-based tools use this execution model:

- Discover runtime details from remote host (PMON/listener/config)
- Execute SQL through remote `sqlplus` using OS-auth (`/ as sysdba`)
- Optionally run as oracle OS user (`sudo_oracle=true`)

### Oracle SSH helper behavior

Implementation details:
- Remote discovery steps:
  - PMON process scan (`ps -ef ... ora_pmon_...`) for SID inference
  - `lsnrctl status/services` parsing for services and ports
  - Fallback reads of `listener.ora` and `tnsnames.ora`
- SQLPlus bootstrap on remote host:
  - Finds `sqlplus` in PATH/ORACLE_HOME/common install locations
  - Sets `ORACLE_HOME`, PATH, LD library path
  - Infers `ORACLE_SID` from PMON if not set
  - Sources `oraenv` when available

### `db_oracle_connect`

Implementation:
- Runs SQL on remote host:
  - `v$instance` + `v$database`
- Returns `instance_name`, `version`, `open_mode`, `database_role`
- Includes discovery metadata and candidate DSNs

### `db_oracle_tablespaces`

Implementation:
- Runs SQL aggregating `dba_data_files` and `dba_free_space`
- Computes per-tablespace:
  - `used_pct`
  - `free_mb`
- Orders descending by usage

### `db_oracle_data_validation`

Implementation:
- Core SQL checks collect:
  - `open_mode`, `database_role`, `log_mode`
  - files requiring recovery (`v$recover_file`)
  - block corruption (`v$database_block_corruption`)
  - offline/problem datafiles (`v$datafile`, `v$datafile_header`)
  - invalid objects (`dba_objects`)
  - critical tablespace pressure (`>=95%`)
  - archive destination errors (`v$archive_dest`)
- Additional best-effort checks:
  - backup recency from `v$rman_backup_job_details`
  - archived log freshness from `v$archived_log`
- Produces check list with `PASS|WARN|FAIL`, metrics, and `production_ready`

### `db_oracle_discover_and_validate`

Implementation:
- Performs remote SID/service/port discovery over SSH
- Builds candidate DSNs
- If Oracle credentials are provided, attempts direct DB login (`oracledb.connect`) against discovered DSNs and returns first successful validation

### `db_oracle_discover_config`

Implementation:
- Direct DB login mode (not SSH-shell SQLPlus mode)
- Resolves Oracle auth via args or `credential_id`
- Tries DSN from `service`/`sid` or common service names
- Collects comprehensive configuration:
  - instance/database metadata
  - tablespaces
  - memory
  - parameters
  - datafiles/redo/archive details

## 4. MongoDB Tools

Mongo tools are SSH-first and execute local shell commands (`mongosh`/`mongo`) on the target host.

### Mongo runtime discovery behavior

Implementation details:
- Detects shell binary (`mongosh` then `mongo`)
- Detects runtime command line from `ps -eo args | awk '/[m]ongod/'`
- Infers:
  - port (`--port` or config parse fallback)
  - replSet name (`--replSet` or config parse fallback)
- Config fallback files:
  - `/etc/mongod.conf`
  - `/etc/mongodb.conf`
  - `/usr/local/etc/mongod.conf`

### Mongo auth handling in SSH mode

Implementation details:
- First tries local no-auth execution
- If auth fails and credentials are available, retries in credentialed mode
- Credentialed mode avoids password in command args:
  - passes auth/eval script via SSH stdin
- Parses JSON from shell output and normalizes errors

### `db_mongo_connect`

Implementation:
- Runs shell JS to fetch:
  - `db.adminCommand({ping:1})`
  - `buildInfo.version`
  - `hello` (fallback `isMaster`)
- Returns ping/version/hello and discovery details

### `db_mongo_rs_status`

Implementation:
- Runs `JSON.stringify(rs.status())`
- Returns set, state, members, raw status
- Error classification includes:
  - `MONGO_NOT_REPLSET` (standalone mongod)
  - `MONGO_REPLSET_UNINITIALIZED`
  - `MONGO_AUTH_ERROR`

### `db_mongo_ssh_ping`

Implementation:
- Backward-compatible alias for `db_mongo_connect`
- Routed to shared internal implementation

### `db_mongo_ssh_rs_status`

Implementation:
- Backward-compatible alias for `db_mongo_rs_status`
- Routed to shared internal implementation

### `validate_collection`

Implementation:
- Runs:
  - `db.getSiblingDB(<db>).getCollection(<collection>).validate({full:<bool>})`
- Returns raw validate payload plus normalized highlights (`errors`, `warnings`, index/record counters when present)

## 5. Workload Discovery Tools

All discovery tools support SSH credentials or `credential_id`.

### `discover_os_only`

Implementation:
- Builds `DiscoveryRequest`
- Uses `OSDetector.detect(...)`
- Returns structured OS profile (type/distribution/version/kernel/confidence)

### `discover_applications`

Implementation:
- Builds `DiscoveryRequest`
- Uses `ApplicationDetector.detect(...)`
- Applies confidence filtering (`high|medium|low|uncertain`)
- Returns app inventory + detection validation summary

### `get_raw_server_data`

Implementation:
- Uses `RawDataCollector` and selected flags:
  - processes (`ps aux`)
  - listening ports (`netstat -tulpn` fallback `ss -tulpn`)
  - configs (`cat -- <quoted_path>`) [shell-quoted path handling]
  - packages (`rpm -qa` fallback `dpkg -l`)
  - services (`systemctl list-units` fallback `service --status-all`)

### `discover_workload`

Implementation status:
- Currently returns `pending_implementation`
- Intended as integrated multi-stage discovery entry point

## 6. Server Utility Tools

### `server_health`

Implementation:
- Returns health, version, plugin list, capability counts

### `list_resources`

Implementation:
- Returns built-in acceptance resource descriptors

### `get_resource`

Implementation:
- Returns JSON content for one acceptance resource URI

### `list_prompts`

Implementation:
- Lists bundled orchestration prompt templates

### `get_prompt`

Implementation:
- Returns content of one named prompt template

## Resources

- `resource://acceptance/vm-core`
- `resource://acceptance/db-oracle`
- `resource://acceptance/db-mongo`

## Prompts

- `planner`
- `evaluator`
- `summarizer`

## Claude Desktop Setup (stdio)

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cyberres-recovery-validation": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/python/cyberres-mcp",
        "run",
        "cyberres-mcp"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

Restart Claude Desktop after changes.

## MCP Inspector Setup

```bash
npx @modelcontextprotocol/inspector
```

- Transport: `streamable-http`
- URL: `http://localhost:8000/mcp` (or remote host)

## Troubleshooting

- SSH host key failures:
  - Add host key to known_hosts, or intentionally set `SSH_TRUST_UNKNOWN_HOSTS=true`
- Oracle SQLPlus errors (`SP2-0667`, `SP2-0750`):
  - Fix `ORACLE_HOME`/message files on remote host; try `sudo_oracle=true`
- Mongo `MONGO_NOT_REPLSET`:
  - Node is standalone; use `db_mongo_connect` and `validate_collection` instead of replica-set status
- `credential_id` not found:
  - Verify `SECRETS_FILE` path and key name in `secrets.json`

## Security Notes

- Do not commit `secrets.json`
- Sensitive fields are redacted in logs
- Mongo credentialed SSH mode avoids passing passwords in command arguments
- Raw config path collection now uses shell-quoted paths

## License

See [LICENSE](../../LICENSE).
