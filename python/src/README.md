# BeeAI Recovery Validation Agent

An agentic infrastructure validation system built on the [BeeAI Framework](https://github.com/i-am-bee/beeai-framework). It connects to target VMs, Oracle databases, and MongoDB instances over SSH, runs a structured set of health checks via MCP tools, evaluates the results with an LLM, and emails a report — all driven by a single natural-language prompt.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Agents](#agents)
4. [MCP Tools](#mcp-tools)
5. [Workflow Lifecycle](#workflow-lifecycle)
6. [Credential Management](#credential-management)
7. [Observability & Logging](#observability--logging)
8. [Configuration & Setup](#configuration--setup)
9. [Running the Agent](#running-the-agent)
10. [Scaling to Multiple Resources](#scaling-to-multiple-resources)
11. [Design Decisions & Known Issues](#design-decisions--known-issues)

---

## Overview

The system validates that infrastructure resources (VMs, Oracle DBs, MongoDB instances) are healthy after a recovery event. A user types a single prompt such as:

```
Validate VM at 9.11.69.88 and email report to ops@example.com. Use credential vm-prod-01.
```

The agent then:
1. Resolves SSH credentials from `secrets.json` (no passwords in prompts)
2. Discovers what workloads are running on the target (MongoDB, Oracle, plain VM)
3. Builds a deterministic validation plan (no LLM hallucination risk)
4. Executes each check via MCP tools over SSH
5. Evaluates results with an LLM (health rating, root cause, recommendations)
6. Emails a structured HTML report

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Prompt (CLI)                            │
│  "Validate VM at 9.11.69.88, use credential vm-prod-01, email ..."  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CredentialResolver                               │
│  Reads secrets.json → resolves SSH user/password by credential ID  │
│  or by hostname/IP lookup                                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │  VMResourceInfo / OracleDBResourceInfo
                            │  / MongoDBResourceInfo (with SSH creds)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Orchestrator                                   │
│  Coordinates 4 phases; owns MCP connection; holds WorkflowState    │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │
│  │  Phase 1     │  │  Phase 2     │  │  Phase 3     │  │Phase 4 │ │
│  │  Discovery   │→ │  Planning    │→ │  Validation  │→ │  Eval  │ │
│  │  Agent       │  │  Agent       │  │  Agent       │  │ Agent  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───┬────┘ │
└─────────┼─────────────────┼─────────────────┼──────────────┼──────┘
          │                 │                 │              │
          ▼                 ▼                 ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP Server (stdio subprocess)                    │
│  cyberres-mcp — FastMCP server exposing SSH-based tools             │
│                                                                     │
│  discover_workload   discover_os_only   discover_applications       │
│  tcp_portcheck       vm_linux_uptime_load_mem   vm_linux_fs_usage   │
│  vm_linux_services   vm_validator                                   │
│  db_mongo_ssh_ping   db_mongo_ssh_rs_status   validate_collection   │
│  db_oracle_connect   db_oracle_tablespaces   db_oracle_data_valid.  │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Target Infrastructure                            │
│  VM / Oracle DB / MongoDB  (accessed via SSH)                       │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Email Report (SendGrid / SMTP)                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data flow between phases

```
Prompt
  │
  ├─► CredentialResolver ──► VMResourceInfo{host, ssh_user, ssh_password, ...}
  │
  ├─► Phase 1 (Discovery Agent)
  │     Input : VMResourceInfo
  │     Output: WorkloadDiscoveryResult{ports, processes, applications[]}
  │             ResourceClassification{category, confidence}
  │
  ├─► Phase 2 (Planning Agent)
  │     Input : VMResourceInfo + ResourceClassification
  │     Output: ValidationPlan{checks: [ValidationCheck{mcp_tool, tool_args}]}
  │
  ├─► Phase 3 (Validation Agent + ToolExecutor)
  │     Input : ValidationPlan
  │     Output: ResourceValidationResult{check_results[], passed, failed, warnings}
  │
  ├─► Phase 4 (Evaluation Agent)
  │     Input : ResourceValidationResult + WorkloadDiscoveryResult
  │     Output: OverallEvaluation{health, issues[], recommendations[]}
  │
  └─► EmailService ──► HTML report to recipient
```

---

## Agents

### 1. CredentialResolver (`beeai_agents/orchestrator.py`)

Runs before the workflow starts. Parses the user prompt to extract:
- Target host (IP or hostname)
- Credential ID (e.g. `vm-prod-01`)
- Email recipient

Looks up the credential ID in `secrets.json` (located at `python/cyberres-mcp/secrets.json`). Falls back to hostname/IP lookup if no ID is given. Builds a typed `VMResourceInfo`, `OracleDBResourceInfo`, or `MongoDBResourceInfo` object with SSH credentials pre-populated.

**Key design**: credentials are resolved once, stored in the resource object, and injected into every tool call by the deterministic planner — the LLM never sees or handles passwords.

---

### 2. Discovery Agent (`beeai_agents/discovery_agent.py`)

**Mode**: LLM-assisted (BeeAI `RequirementAgent`)

Discovers what workloads are running on the target host. Uses a three-strategy fallback:

| Strategy | Tools used | When |
|---|---|---|
| Comprehensive | `discover_workload` | First attempt |
| Individual | `discover_os_only` + `discover_applications` | If comprehensive returns empty/not-implemented |
| Raw data | `get_raw_server_data` | Last resort |

For simple VMs, a fast-path skips LLM planning and uses a default `scan_ports=True, scan_processes=True, detect_applications=True` plan.

Output: `WorkloadDiscoveryResult` with detected applications (e.g. `MongoDB 90%`, `Oracle Database 50%`).

The LLM is used to interpret raw port/process/application data into a structured workload classification.

---

### 3. Planning Agent (`beeai_agents/validation_agent.py`)

**Mode**: Fully deterministic (no LLM)

Maps `ResourceClassification.category` + detected applications to an exact list of `ValidationCheck` objects. Each check has:
- `mcp_tool`: exact MCP tool name (validated against the live MCP server tool list)
- `tool_args`: pre-populated dict including SSH credentials from the resource object
- `priority`, `check_name`, `expected_result`, `failure_impact`

**Why no LLM here**: LLMs proved unreliable at (a) picking valid tool names and (b) injecting SSH credentials into every tool_args dict. Deterministic mapping eliminates both failure modes.

#### Check plans by resource category

**VM (generic)**
| ID | Tool | What it checks |
|---|---|---|
| vm_001 | `tcp_portcheck` | Port 22 reachable |
| vm_002 | `vm_linux_uptime_load_mem` | CPU load, memory usage |
| vm_003 | `vm_linux_fs_usage` | Filesystem usage |
| vm_004 | `vm_linux_services` | Critical services running |

**VM with MongoDB detected**
| ID | Tool | What it checks |
|---|---|---|
| net_001 | `tcp_portcheck` | Port 22 reachable |
| db_mongo_001 | `db_mongo_ssh_ping` | MongoDB reachable via SSH mongosh |
| db_mongo_002 | `db_mongo_ssh_rs_status` | Replica set status (standalone = warning) |
| db_mongo_003 | `validate_collection` | All collections in admin db pass integrity check |
| db_vm_001 | `vm_linux_uptime_load_mem` | System resources |
| db_vm_002 | `vm_linux_fs_usage` | Filesystem usage |
| db_vm_003 | `vm_linux_services` | mongod.service running |

**VM with Oracle detected**
| ID | Tool | What it checks |
|---|---|---|
| net_001 | `tcp_portcheck` | Port 22 reachable |
| db_oracle_001 | `db_oracle_connect` | Oracle listener reachable |
| db_oracle_002 | `db_oracle_tablespaces` | Tablespace usage |
| db_oracle_003 | `db_oracle_data_validation` | Data integrity |
| db_vm_001 | `vm_linux_uptime_load_mem` | System resources |
| db_vm_002 | `vm_linux_fs_usage` | Filesystem usage |
| db_vm_003 | `vm_linux_services` | oracle.service running |

---

### 4. Validation Agent (`beeai_agents/validation_agent.py` + `tool_executor.py`)

**Mode**: Deterministic

Executes each `ValidationCheck` in the plan sequentially. For each check:
1. Calls `ToolExecutor.execute_with_retry()` (up to 3 attempts with exponential backoff)
2. Parses the raw MCP tool result into a `CheckResult`
3. Determines `ValidationStatus` (PASS / WARNING / FAIL) using tool-specific rules
4. Generates a human-readable one-line summary

**Special result parsing rules** (in `tool_executor.py`):

| Tool | Special handling |
|---|---|
| `vm_linux_services` | If `ok=False` and `code=SERVICE_CHECK_FAILED`, surfaces missing service names as WARNING (not generic FAIL) |
| `validate_collection` (auto-discover) | Reads `summary.passed/failed` from multi-collection response |
| `validate_collection` (single) | Reads `validate.valid` field |
| `db_mongo_ssh_ping` | Extracts MongoDB version from response |
| `db_mongo_ssh_rs_status` | Shows replica set name, member count, node state |

---

### 5. Evaluation Agent (`beeai_agents/evaluation_agent.py`)

**Mode**: LLM (BeeAI `RequirementAgent`)

Takes the full `ResourceValidationResult` and produces an `OverallEvaluation`:
- `overall_health`: excellent / good / fair / poor / critical
- `confidence`: 0.0–1.0
- `critical_issues[]`: issues requiring immediate attention
- `recommendations[]`: prioritised actionable steps
- `check_assessments[]`: per-check severity, root cause, remediation steps
- `next_steps[]`: for the operations team

The LLM is given the full check results, discovery data, and resource classification as context.

---

### 6. AgentTracker (`agent_logging/agent_logger.py`)

Not an agent per se — a structured console output helper used by all agents. Provides a ChatGPT/Claude-style display:

```
  ┌─ 🔍  Discovery Agent
     ↳ Scanning ports, processes and applications on the target host
  └──────────────────────────────────────────────────

  💭 Thinking: Detected 2 application(s) — classifying resource type...
  ✓ Classified as database_server (confidence: 90%)

  ┌─ 📋  Planning Agent
     ↳ Mapping detected workloads to the right validation checks
  └──────────────────────────────────────────────────

  ✓ Plan: 7 checks → tcp_portcheck, db_mongo_ssh_ping, ...

  ┌─ ✅  Validation Agent
     ↳ Running checks and collecting results from the target host
  └──────────────────────────────────────────────────

  ▶ Using: db_mongo_ssh_ping  ssh_host=9.11.69.88  ssh_user=vikas
  ✅  db_mongo_ssh_ping  →  MongoDB 7.0.30 reachable via ssh_mongo_shell
  ▶ Using: vm_linux_services  host=9.11.69.88  username=vikas
  ✅  vm_linux_services  →  ⚠️  WARN: Required service(s) not running: mongod.service
```

All console output is clean and role-focused. System-level logs (DEBUG, WARNING, full JSON) go to `logs/beeai_YYYYMMDD_HHMMSS.log`. Noisy third-party loggers (MCP, paramiko, httpx) are suppressed on console but captured in the log file.

---

## MCP Tools

The MCP server (`python/cyberres-mcp`) is a [FastMCP](https://github.com/jlowin/fastmcp) server that exposes all tools over stdio transport. It is launched as a subprocess by the orchestrator.

### Discovery tools

| Tool | Description |
|---|---|
| `discover_workload` | Full integrated workload discovery (Sprint 4 — currently falls back) |
| `discover_os_only` | Detects OS type, version, distribution via SSH |
| `discover_applications` | Detects running applications via SSH process/port scan |
| `get_raw_server_data` | Collects raw system data for LLM interpretation |

### VM health tools

| Tool | Parameters | Description |
|---|---|---|
| `tcp_portcheck` | `host`, `ports[]` | TCP port reachability check |
| `vm_linux_uptime_load_mem` | `host`, `username`, `password` | Uptime, load average, memory usage |
| `vm_linux_fs_usage` | `host`, `username`, `password` | Filesystem usage per mount point |
| `vm_linux_services` | `host`, `username`, `password`, `required[]` | Checks systemd services are active |
| `vm_validator` | `host`, `username`, `password` | General VM health validator |

### MongoDB tools (all via SSH)

All MongoDB tools connect via SSH and run `mongosh` locally on the target — MongoDB does not need to be exposed on the network.

| Tool | Parameters | Description |
|---|---|---|
| `db_mongo_ssh_ping` | `ssh_host`, `ssh_user`, `ssh_password`, `ssh_key_path` | Connects via SSH, runs `db.runCommand({ping:1})` |
| `db_mongo_ssh_rs_status` | `ssh_host`, `ssh_user`, `ssh_password`, `ssh_key_path` | Runs `rs.status()` — returns warning on standalone |
| `validate_collection` | `ssh_host`, `ssh_user`, `ssh_password`, `ssh_key_path`, `db_name`, `collection`, `full` | Validates collection integrity. `collection=""` auto-discovers all collections in the db |
| `db_mongo_connect` | `ssh_host`, `ssh_user`, `ssh_password` | Basic connectivity check |
| `db_mongo_rs_status` | `ssh_host`, `ssh_user`, `ssh_password` | Replica set status (direct TCP) |

### Oracle tools

| Tool | Parameters | Description |
|---|---|---|
| `db_oracle_connect` | `ssh_host`, `ssh_user`, `ssh_password`, `oracle_user`, `oracle_password`, `service_name` | Oracle listener connectivity |
| `db_oracle_tablespaces` | `ssh_host`, `ssh_user`, `ssh_password`, `oracle_user`, `oracle_password` | Tablespace usage |
| `db_oracle_data_validation` | `ssh_host`, `ssh_user`, `ssh_password`, `oracle_user`, `oracle_password` | Data integrity checks |
| `db_oracle_discover_and_validate` | `ssh_host`, `ssh_user`, `ssh_password` | Auto-discover Oracle SIDs and validate |
| `db_oracle_discover_config` | `ssh_host`, `ssh_user`, `ssh_password` | Discover Oracle configuration |

---

## Workflow Lifecycle

```
User types prompt
       │
       ▼
1. PROMPT PARSING
   ├── Extract host IP/hostname
   ├── Extract credential ID (e.g. "vm-prod-01")
   └── Extract email recipient

       │
       ▼
2. CREDENTIAL RESOLUTION
   ├── Load secrets.json
   ├── Look up credential by ID or hostname
   └── Build VMResourceInfo{host, ssh_user, ssh_password, ssh_key_path}

       │
       ▼
3. PHASE 1 — DISCOVERY (🔍 Discovery Agent)
   ├── Try discover_workload (comprehensive)
   ├── Fallback: discover_os_only + discover_applications
   ├── Fallback: get_raw_server_data
   └── Classify: DATABASE_SERVER / WEB_SERVER / GENERIC_VM

       │
       ▼
4. PHASE 2 — PLANNING (📋 Planning Agent, deterministic)
   ├── Map category + apps → check list
   ├── Inject SSH credentials into every tool_args
   ├── Validate all tool names against live MCP server
   └── Return ValidationPlan{checks[]}

       │
       ▼
5. PHASE 3 — VALIDATION (✅ Validation Agent)
   ├── For each check:
   │   ├── Call MCP tool via ToolExecutor (retry x3)
   │   ├── Parse result → CheckResult
   │   ├── Determine PASS / WARNING / FAIL
   │   └── Generate one-line summary
   └── Return ResourceValidationResult{passed, failed, warnings, score}

       │
       ▼
6. PHASE 4 — EVALUATION (🎯 Evaluation Agent, LLM)
   ├── LLM analyses all check results
   ├── Identifies root causes and critical issues
   ├── Generates prioritised recommendations
   └── Returns OverallEvaluation{health, confidence, recommendations[]}

       │
       ▼
7. REPORTING
   ├── Generate HTML report
   ├── Send via SMTP / SendGrid
   └── Print summary to console
```

---

## Credential Management

### secrets.json

Credentials are stored in `python/cyberres-mcp/secrets.json` (gitignored). The format is:

```json
{
  "<credential-id>": {
    "ssh": {
      "username": "root",
      "password": "secret",
      "key_path": "/path/to/key.pem"
    },
    "oracle": {
      "username": "system",
      "password": "oracle_pass"
    },
    "mongo": {
      "username": "admin",
      "password": "mongo_pass"
    }
  },
  "9.11.69.88": {
    "ssh": {
      "username": "vikas",
      "password": "vikas1234"
    }
  }
}
```

The key can be:
- A logical credential ID (e.g. `vm-prod-01`, `mongo-staging`) — referenced in the prompt as `use credential vm-prod-01`
- A hostname or IP address — the agent looks up by the target host automatically

See `python/cyberres-mcp/secrets.example.json` for a full example.

### Lookup priority

1. Explicit credential ID from prompt (e.g. `use credential vm-prod-01`)
2. Exact hostname/IP match in secrets.json
3. Partial hostname match
4. Environment variables (`SSH_USER`, `SSH_PASSWORD`, `SSH_KEY_PATH`)

### Extending to a secrets manager

The `CredentialResolver` in `orchestrator.py` loads `secrets.json` via a simple JSON read. To integrate with AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault, replace the `_load_secrets_file()` method with an API call to your secrets manager. The rest of the system is unchanged — credentials flow through the same `VMResourceInfo` object.

---

## Observability & Logging

### Console output

Clean, role-focused output using `AgentTracker`:

```
════════════════════════════════════════════════════════════
  [Orchestrator]
  Validation workflow for 9.11.69.88 [vm]
────────────────────────────────────────────────────────────

  ┌─ 🔍  Discovery Agent
     ↳ Scanning ports, processes and applications on the target host
  └──────────────────────────────────────────────────

  ▶ Using: discover_workload  host=9.11.69.88  ssh_user=vikas
  ✅  discover_workload  →  Found 2 apps: MongoDB (90%), Oracle (50%)
  💭 Thinking: Detected 2 application(s) — classifying resource type...
  ✓ Classified as database_server (confidence: 90%)

  ┌─ 📋  Planning Agent
     ↳ Mapping detected workloads to the right validation checks
  └──────────────────────────────────────────────────

  ✓ Plan: 7 checks → tcp_portcheck, db_mongo_ssh_ping, ...

  ┌─ ✅  Validation Agent
     ↳ Running checks and collecting results from the target host
  └──────────────────────────────────────────────────

  ▶ Using: db_mongo_ssh_ping  ssh_host=9.11.69.88  ssh_user=vikas  ssh_password=***
  ✅  db_mongo_ssh_ping  →  [2/7] MongoDB SSH Ping — ✅ PASS: MongoDB 7.0.30 reachable

  ┌─ 🎯  Evaluation Agent
     ↳ Analysing results, identifying issues and generating recommendations
  └──────────────────────────────────────────────────

  💭 Thinking: Analysing check results, identifying root causes...
  ✓ Health: FAIR  Issues: 1  Recommendations: 3

────────────────────────────────────────────────────────────
  ✅ Workflow PARTIAL_SUCCESS — score: 72/100 (90.3s)
════════════════════════════════════════════════════════════
```

### Log file

Full structured JSON logs are written to `logs/beeai_YYYYMMDD_HHMMSS.log`. Each line is a JSON object:

```json
{"ts": "2026-02-28T02:08:26Z", "level": "INFO", "logger": "agents.ValidationAgent",
 "msg": "Tool db_mongo_ssh_ping executed successfully", "agent": "ValidationAgent",
 "tool": "db_mongo_ssh_ping", "resource": "9.11.69.88"}
```

Noisy loggers (`mcp.*`, `paramiko.*`, `httpx`, `asyncio`) are suppressed on console but captured in the log file at DEBUG level.

---

## Configuration & Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- [Ollama](https://ollama.ai) running locally with `llama3.2` model pulled
- SSH access to target VMs

### 1. Install dependencies

```bash
cd python/src
uv sync
```

```bash
cd python/cyberres-mcp
uv sync
```

### 2. Configure environment

```bash
cp python/src/.env.example python/src/.env
```

Edit `python/src/.env`:

```bash
# LLM (Ollama local)
LLM_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Email (SendGrid example)
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.your_api_key_here
SMTP_USE_TLS=true
EMAIL_FROM=noreply@yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### 3. Configure credentials

Create `python/cyberres-mcp/secrets.json`:

```json
{
  "vm-prod-01": {
    "ssh": {
      "username": "root",
      "password": "your_password"
    }
  },
  "mongo-staging": {
    "ssh": {
      "username": "vikas",
      "password": "vikas1234"
    }
  }
}
```

### 4. Pull Ollama model

```bash
ollama pull llama3.2
```

### 5. Verify MCP server

```bash
cd python/cyberres-mcp
uv run cyberres-mcp
# Should print: MCP server starting on stdio transport
```

---

## Running the Agent

### Interactive CLI (recommended)

```bash
cd python/src
uv run python run_beeai_validation.py
```

You will see a prompt:

```
💬 Enter your validation request:
```

Example prompts:

```
# Validate a VM using a named credential
Validate VM at 9.11.69.88 and email report to ops@example.com. Use credential vm-prod-01.

# Validate using IP lookup (no explicit credential ID)
Validate the server at 192.168.1.100 and send results to admin@company.com

# Validate MongoDB specifically
Check MongoDB health on 9.11.69.88, use credential mongo-staging, email himanshu@ibm.com
```

### Programmatic usage

```python
import asyncio
from beeai_agents.orchestrator import BeeAIOrchestrator

async def main():
    orchestrator = BeeAIOrchestrator(
        mcp_server_path="../cyberres-mcp",
        llm_model="ollama:llama3.2"
    )
    await orchestrator.initialize()

    result = await orchestrator.run_from_prompt(
        "Validate VM at 9.11.69.88, use credential vm-prod-01, email ops@example.com"
    )
    print(f"Score: {result.validation_result.score}/100")
    print(f"Health: {result.evaluation.overall_health}")

asyncio.run(main())
```

---

## Scaling to Multiple Resources

The current architecture validates one resource per workflow run. To validate multiple VMs/resources in parallel:

### Option 1: Batch orchestrator (built-in)

The `BatchOrchestrator` (planned) accepts a list of credential IDs and runs workflows concurrently:

```python
resources = ["vm-prod-01", "vm-prod-02", "mongo-staging", "oracle-prod"]
results = await batch_orchestrator.run_batch(resources, max_concurrent=4)
```

### Option 2: Multiple prompts

Run the CLI in a loop or script:

```bash
for cred in vm-prod-01 vm-prod-02 mongo-staging; do
  echo "Validate using credential $cred, email ops@example.com" | \
    uv run python run_beeai_validation.py
done
```

### Option 3: Extend secrets.json for bulk runs

```json
{
  "batch-prod": {
    "targets": ["9.11.69.88", "9.11.69.89", "9.11.69.90"],
    "ssh": { "username": "root", "password": "pass" }
  }
}
```

The orchestrator can be extended to expand `targets[]` into parallel `ValidationRequest` objects.

---

## Design Decisions & Known Issues

### Why no LLM in the planning phase?

Early versions used the LLM to generate the validation plan. This caused two recurring failures:
1. **Hallucinated tool names** — the LLM invented tool names that didn't exist in the MCP server
2. **Missing SSH credentials** — the LLM forgot to include `ssh_password` in tool_args for some checks

The fix was to make planning fully deterministic: a hard-coded mapping from `ResourceCategory` + detected applications to exact tool names and pre-populated tool_args. The LLM is only used where it adds genuine value: interpreting raw discovery data (Phase 1) and writing health assessments (Phase 4).

### Why SSH-based MongoDB tools?

MongoDB typically listens on `127.0.0.1:27017` only (not exposed on the network). All MongoDB MCP tools (`db_mongo_ssh_ping`, `db_mongo_ssh_rs_status`, `validate_collection`) connect via SSH and run `mongosh` locally on the target VM. This means no MongoDB port needs to be open to the validation host.

### validate_collection uses auto-discover mode

`collection=""` (empty string) tells the tool to discover and validate all collections in the specified database. This works on both standalone and replica-set MongoDB without needing to know collection names in advance. The previous approach (`collection="system.users"`) failed on standalone instances because `admin.system.users` only exists on replica sets.

---

## File Structure

```
python/src/
├── run_beeai_validation.py      # Main entry point (interactive CLI)
├── models.py                    # Pydantic data models (ResourceInfo, CheckResult, etc.)
├── credentials.py               # Legacy env-var credential manager
├── email_service.py             # SMTP / SendGrid email sender
├── .env.example                 # Environment variable template
│
├── beeai_agents/
│   ├── orchestrator.py          # Main workflow coordinator (4 phases)
│   ├── discovery_agent.py       # Phase 1: workload discovery
│   ├── validation_agent.py      # Phase 2 (planning) + Phase 3 (execution)
│   ├── tool_executor.py         # MCP tool execution + result parsing
│   ├── evaluation_agent.py      # Phase 4: LLM health assessment
│   ├── base_agent.py            # Abstract base class for all agents
│   └── config.py                # BeeAIConfig (LLM, memory, MCP settings)
│
├── agent_logging/
│   └── agent_logger.py          # Dual-stream logging (console + JSON file)
│
└── logs/                        # Auto-created; beeai_YYYYMMDD_HHMMSS.log

python/cyberres-mcp/
├── secrets.json                 # Credentials (gitignored — create from secrets.example.json)
├── secrets.example.json         # Credential format reference
├── src/cyberres_mcp/
│   ├── server.py                # FastMCP server entry point
│   ├── settings.py              # Server configuration
│   ├── models.py                # MCP data models
│   └── plugins/
│       ├── ssh_utils.py         # SSH connection utilities
│       ├── mongo_db.py          # MongoDB MCP tools
│       ├── oracle_db.py         # Oracle MCP tools
│       ├── net.py               # Network tools (tcp_portcheck)
│       ├── vms_validator.py     # VM health tools
│       └── workload_discovery/  # Discovery tools
│           ├── os_detector.py
│           ├── app_detector.py
│           ├── port_scanner.py
│           └── process_scanner.py
