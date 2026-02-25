# Agentic Workflow - Comprehensive Documentation

**Project**: CyberRes Recovery Validation Agent  
**Date**: 2026-02-25  
**Version**: 1.0  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Agents and Their Roles](#agents-and-their-roles)
4. [MCP Integration](#mcp-integration)
5. [Decision-Making Flow](#decision-making-flow)
6. [End-to-End Workflow](#end-to-end-workflow)
7. [BeeAI Framework Analysis](#beeai-framework-analysis)
8. [Technology Stack](#technology-stack)
9. [Key Components](#key-components)
10. [Workflow Diagrams](#workflow-diagrams)

---

## Executive Summary

The CyberRes Recovery Validation Agent is an **intelligent, multi-agent system** designed to validate recovered infrastructure resources (VMs, Oracle databases, MongoDB clusters) using AI-powered workload discovery and adaptive validation strategies.

### Key Capabilities
- **Intelligent Workload Discovery**: Automatically detects applications and services
- **Adaptive Validation**: Creates resource-specific validation plans
- **AI-Powered Evaluation**: Provides actionable insights and recommendations
- **MCP Integration**: Uses Model Context Protocol for tool execution
- **Multi-LLM Support**: Works with Ollama (local), OpenAI, Groq, and others

### Architecture Pattern
**Multi-Agent Orchestration** with specialized agents coordinated by a central orchestrator, using Pydantic AI for structured outputs and MCP for tool execution.

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ Interactive CLI  │         │  Main Entry      │         │
│  │ (interactive_    │         │  (main.py)       │         │
│  │  agent.py)       │         │                  │         │
│  └──────────────────┘         └──────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         ValidationOrchestrator                        │  │
│  │  - Coordinates all agents                            │  │
│  │  - Manages workflow phases                           │  │
│  │  - Handles errors and retries                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Discovery   │  │  Validation  │  │  Evaluation  │     │
│  │    Agent     │  │    Agent     │  │    Agent     │     │
│  │ (Pydantic AI)│  │ (Pydantic AI)│  │ (Pydantic AI)│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         ↓                  ↓                  ↓             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          ApplicationClassifier                        │  │
│  │  - Rule-based classification                         │  │
│  │  - Application detection                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              MCP Client (stdio/HTTP)                  │  │
│  │  - Tool discovery and execution                      │  │
│  │  - Connection management                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Tool Layer (MCP)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Network    │  │   Database   │  │   Workload   │     │
│  │    Tools     │  │    Tools     │  │   Discovery  │     │
│  │ (tcp_port    │  │ (oracle_db,  │  │   Tools      │     │
│  │  check)      │  │  mongo_db)   │  │ (scan_ports) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Agents and Their Roles

### 1. **ValidationOrchestrator** (`agents/orchestrator.py`)

**Role**: Central coordinator that manages the entire validation workflow

**Responsibilities**:
- Coordinates all specialized agents
- Manages workflow phases (Discovery → Classification → Planning → Validation → Evaluation)
- Handles errors and implements retry logic
- Aggregates results from all phases
- Determines overall workflow status

**Key Methods**:
- `execute_workflow()`: Main entry point for validation
- `_execute_discovery()`: Runs workload discovery phase
- `_create_validation_plan()`: Creates validation strategy
- `_execute_validations()`: Executes validation checks
- `_evaluate_results()`: Performs AI evaluation

**Decision Making**:
- Determines if discovery should run based on `auto_discover` flag
- Decides whether to use AI evaluation based on configuration
- Calculates overall workflow status from validation results

---

### 2. **DiscoveryAgent** (`agents/discovery_agent.py`)

**Role**: Intelligent workload discovery using AI-powered planning

**Responsibilities**:
- Creates optimal discovery plans using Chain-of-Thought reasoning
- Scans ports to identify open services
- Analyzes running processes
- Detects applications based on ports and processes
- Aggregates discovery results

**AI Integration**: Uses Pydantic AI with structured output (`DiscoveryPlan`)

**Key Methods**:
- `discover()`: Main discovery orchestration
- `_create_plan()`: AI-powered discovery planning with CoT
- `_execute_discovery()`: Executes the discovery plan
- `discover_with_retry()`: Implements retry logic

**Decision Making**:
- **Fast-path optimization**: For simple VMs, skips LLM and uses default plan
- **AI-powered planning**: For complex resources, uses LLM with Chain-of-Thought reasoning
- Determines which discovery methods to use (ports, processes, applications)

**Example AI Prompt Structure**:
```
Step 1: Resource Analysis - What do we know?
Step 2: Discovery Goals - What information is valuable?
Step 3: Method Selection - Which methods to use?
Step 4: Efficiency - Balance thoroughness with speed
Step 5: Final Decision - Create the plan
```

---

### 3. **ValidationAgent** (`agents/validation_agent.py`)

**Role**: Creates intelligent validation plans based on resource classification

**Responsibilities**:
- Analyzes resource classification and discovered applications
- Creates comprehensive validation plans with prioritized checks
- Selects appropriate MCP tools for each validation
- Provides fallback plans when AI fails

**AI Integration**: Uses Pydantic AI with structured output (`ValidationPlan`)

**Key Methods**:
- `create_plan()`: Main planning method
- `_build_planning_prompt()`: Constructs context-rich prompts
- `_create_fallback_plan()`: Rule-based fallback
- `_get_database_checks()`: Database-specific validations
- `_get_web_server_checks()`: Web server validations

**Decision Making**:
- Selects validation checks based on resource category
- Prioritizes checks (1=highest, 5=lowest)
- Estimates execution time
- Provides reasoning for each check

**Validation Check Structure**:
```python
ValidationCheck(
    check_id="unique_id",
    check_name="Human-readable name",
    check_type="network|database|system",
    priority=1-5,
    mcp_tool="tool_name",
    tool_args={...},
    expected_result="What should happen",
    failure_impact="What happens if it fails"
)
```

---

### 4. **EvaluationAgent** (`agents/evaluation_agent.py`)

**Role**: AI-powered evaluation of validation results with actionable insights

**Responsibilities**:
- Analyzes validation results in context
- Assesses severity and impact of issues
- Identifies root causes and patterns
- Provides specific remediation steps
- Generates prioritized recommendations

**AI Integration**: Uses Pydantic AI with structured output (`OverallEvaluation`)

**Key Methods**:
- `evaluate()`: Main evaluation method
- `_build_evaluation_prompt()`: Creates comprehensive context
- `_create_fallback_evaluation()`: Rule-based fallback
- `evaluate_trend()`: Trend analysis across multiple runs

**Decision Making**:
- Determines overall health (excellent, good, fair, poor, critical)
- Assigns severity to each issue (critical, high, medium, low, info)
- Prioritizes recommendations by impact
- Identifies recurring issues

**Evaluation Output**:
```python
OverallEvaluation(
    overall_health="good|fair|poor|critical",
    confidence=0.0-1.0,
    summary="Executive summary",
    critical_issues=[...],
    warnings=[...],
    recommendations=[...],
    check_assessments=[...],
    next_steps=[...]
)
```

---

### 5. **ApplicationClassifier** (`classifier.py`)

**Role**: Rule-based classification of resources based on discovered applications

**Responsibilities**:
- Classifies resources into categories (database, web, app server, etc.)
- Identifies primary and secondary applications
- Recommends validation strategies
- Handles mixed environments

**Classification Logic**:
- Uses predefined application signatures
- Confidence-based filtering (default threshold: 0.6)
- Multi-application detection for mixed environments

**Categories**:
- `DATABASE_SERVER`: Oracle, MongoDB, PostgreSQL, MySQL, etc.
- `WEB_SERVER`: Apache, Nginx, IIS, etc.
- `APPLICATION_SERVER`: Tomcat, JBoss, WebLogic, etc.
- `MESSAGE_QUEUE`: RabbitMQ, Kafka, ActiveMQ, etc.
- `CACHE_SERVER`: Redis, Memcached, Varnish, etc.
- `MIXED`: Multiple application types
- `UNKNOWN`: No confident classification

---

## MCP Integration

### Model Context Protocol (MCP)

**Purpose**: Standardized protocol for tool execution and resource access

**Implementation**: Two client types supported
1. **MCPStdioClient** (`mcp_stdio_client.py`): Subprocess-based communication
2. **MCPClient** (`mcp_client.py`): HTTP/SSE-based communication

### MCP Client Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client Layer                      │
│                                                          │
│  ┌────────────────────┐      ┌────────────────────┐   │
│  │  MCPStdioClient    │      │    MCPClient       │   │
│  │  (subprocess)      │      │    (HTTP/SSE)      │   │
│  └────────────────────┘      └────────────────────┘   │
│           ↓                           ↓                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │         MCP Protocol (JSON-RPC 2.0)              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              CyberRes MCP Server                         │
│  (python/cyberres-mcp/src/cyberres_mcp/server.py)      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Network    │  │   Database   │  │   Workload   │ │
│  │   Plugins    │  │   Plugins    │  │   Discovery  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Available MCP Tools

#### Network Tools
- `tcp_portcheck`: Check TCP port connectivity
  - Args: `host`, `ports[]`, `timeout_s`
  - Returns: Port status for each port

#### VM Tools
- `vm_linux_uptime_load_mem`: Get system metrics
  - Args: `host`, `username`, `password/key_path`
  - Returns: Uptime, load averages, memory info

- `vm_linux_fs_usage`: Check filesystem usage
  - Args: `host`, `username`, `password/key_path`
  - Returns: Disk usage for all filesystems

- `vm_linux_services`: Check service status
  - Args: `host`, `username`, `password/key_path`, `required[]`
  - Returns: Running/missing services

#### Oracle Database Tools
- `db_oracle_connect`: Test database connection
  - Args: `host`, `port`, `service`, `user`, `password`
  - Returns: Instance info, version, status

- `db_oracle_tablespaces`: Check tablespace usage
  - Args: `dsn`, `user`, `password`
  - Returns: Tablespace usage and free space

#### MongoDB Tools
- `db_mongo_connect`: Test MongoDB connection
  - Args: `host`, `port`, `user`, `password`, `database`
  - Returns: Server version, connection status

- `db_mongo_rs_status`: Check replica set status
  - Args: `uri`
  - Returns: Replica set health and member status

- `validate_collection`: Validate MongoDB collection
  - Args: `ssh_host`, `ssh_user`, `port`, `mongo_user`, `db_name`, `collection`
  - Returns: Collection validation results

#### Workload Discovery Tools
- `workload_scan_ports`: Scan for open ports
  - Args: `host`, `ssh_user`, `ssh_password/key_path`, `port_range`, `scan_type`
  - Returns: List of open ports with service info

- `workload_scan_processes`: Scan running processes
  - Args: `host`, `ssh_user`, `ssh_password/key_path`
  - Returns: List of processes with CPU/memory usage

- `workload_detect_applications`: Detect applications
  - Args: `host`, `ports[]`, `processes[]`
  - Returns: Detected applications with confidence scores

- `workload_aggregate_results`: Aggregate discovery data
  - Args: `host`, `port_results`, `process_results`, `app_detections`
  - Returns: Comprehensive workload discovery result

### MCP Connection Flow

```
1. Client Initialization
   ├─ MCPStdioClient: Launch subprocess with uv
   └─ MCPClient: Connect to HTTP/SSE endpoint

2. Connection Establishment
   ├─ Create transport (stdio/SSE)
   ├─ Create ClientSession
   └─ Initialize session

3. Tool Discovery
   ├─ List available tools
   └─ Cache tool metadata

4. Tool Execution
   ├─ Validate arguments
   ├─ Call tool via MCP protocol
   ├─ Parse response
   └─ Return structured result

5. Cleanup
   ├─ Close session
   └─ Disconnect transport
```

---

## Decision-Making Flow

### Orchestrator Decision Tree

```
START: execute_workflow(request)
│
├─ Should run discovery?
│  ├─ YES (auto_discover=true AND enable_discovery=true)
│  │  ├─ Execute discovery with retry
│  │  ├─ Classify resource
│  │  └─ Continue to planning
│  └─ NO
│     └─ Create fallback classification
│
├─ Create validation plan
│  ├─ Use classification if available
│  └─ Use fallback if not
│
├─ Execute validation checks
│  ├─ For each check in plan:
│  │  ├─ Call MCP tool
│  │  ├─ Interpret result
│  │  └─ Create CheckResult
│  └─ Calculate overall status and score
│
├─ Should run AI evaluation?
│  ├─ YES (enable_ai_evaluation=true)
│  │  ├─ Execute evaluation agent
│  │  └─ Generate recommendations
│  └─ NO
│     └─ Skip evaluation
│
└─ Determine workflow status
   ├─ SUCCESS: No errors, validations passed
   ├─ PARTIAL_SUCCESS: Some errors but validations ok
   └─ FAILURE: Critical errors or validation failures
```

### Discovery Agent Decision Flow

```
START: discover(resource)
│
├─ Is this a simple VM?
│  ├─ YES (VM with no special requirements)
│  │  └─ Use fast-path (skip LLM)
│  └─ NO (Complex resource or database)
│     └─ Use AI-powered planning
│
├─ Create discovery plan
│  ├─ AI generates plan with reasoning
│  └─ Fallback to default if AI fails
│
├─ Execute discovery steps
│  ├─ Scan ports? (if plan.scan_ports)
│  ├─ Scan processes? (if plan.scan_processes)
│  └─ Detect applications? (if plan.detect_applications)
│
└─ Aggregate and return results
```

### Validation Agent Decision Flow

```
START: create_plan(resource, classification)
│
├─ Build context-rich prompt
│  ├─ Resource information
│  ├─ Classification details
│  ├─ Discovered applications
│  └─ Recommended validations
│
├─ Generate validation plan
│  ├─ AI creates comprehensive plan
│  └─ Fallback to rule-based if AI fails
│
├─ Fallback plan logic
│  ├─ Always include network check
│  ├─ Add category-specific checks
│  │  ├─ DATABASE_SERVER → db checks
│  │  ├─ WEB_SERVER → http checks
│  │  ├─ APPLICATION_SERVER → app checks
│  │  └─ MIXED → combined checks
│  └─ Prioritize checks (1-5)
│
└─ Return ValidationPlan
```

### Evaluation Agent Decision Flow

```
START: evaluate(validation_result, discovery, classification)
│
├─ Build comprehensive evaluation prompt
│  ├─ Resource context
│  ├─ Discovery findings
│  ├─ Classification info
│  ├─ Validation results (passed/failed/warnings)
│  └─ Detailed check information
│
├─ Generate AI evaluation
│  ├─ Analyze each failed/warning check
│  ├─ Assess severity and impact
│  ├─ Identify root causes
│  ├─ Generate remediation steps
│  └─ Prioritize recommendations
│
├─ Fallback evaluation (if AI fails)
│  ├─ Calculate health from score
│  │  ├─ ≥90: excellent
│  │  ├─ ≥75: good
│  │  ├─ ≥60: fair
│  │  ├─ ≥40: poor
│  │  └─ <40: critical
│  ├─ Collect issues and warnings
│  └─ Generate basic recommendations
│
└─ Return OverallEvaluation
```

---

## End-to-End Workflow

### Complete Validation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: WORKLOAD DISCOVERY (Optional)                      │
├─────────────────────────────────────────────────────────────┤
│ 1. DiscoveryAgent.discover()                                │
│    ├─ Create discovery plan (AI or fast-path)              │
│    ├─ Scan ports (MCP: workload_scan_ports)                │
│    ├─ Scan processes (MCP: workload_scan_processes)        │
│    ├─ Detect applications (MCP: workload_detect_apps)      │
│    └─ Aggregate results (MCP: workload_aggregate)          │
│                                                              │
│ 2. ApplicationClassifier.classify()                         │
│    ├─ Analyze discovered applications                       │
│    ├─ Determine resource category                           │
│    ├─ Identify primary/secondary apps                       │
│    └─ Generate recommended validations                      │
│                                                              │
│ Output: WorkloadDiscoveryResult + ResourceClassification    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: VALIDATION PLANNING                                │
├─────────────────────────────────────────────────────────────┤
│ ValidationAgent.create_plan()                               │
│    ├─ Build context from discovery & classification        │
│    ├─ Generate AI-powered validation plan                  │
│    │  ├─ Select appropriate MCP tools                      │
│    │  ├─ Prioritize checks (1-5)                           │
│    │  ├─ Define expected results                           │
│    │  └─ Estimate execution time                           │
│    └─ Fallback to rule-based plan if needed                │
│                                                              │
│ Output: ValidationPlan with prioritized checks              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: VALIDATION EXECUTION                               │
├─────────────────────────────────────────────────────────────┤
│ Orchestrator._execute_validations()                         │
│    ├─ For each check in plan:                              │
│    │  ├─ Call MCP tool with arguments                      │
│    │  ├─ Interpret tool result                             │
│    │  ├─ Create CheckResult                                │
│    │  └─ Handle errors gracefully                          │
│    ├─ Calculate overall status                              │
│    │  ├─ Count passed/failed/warnings                      │
│    │  ├─ Calculate score (0-100)                           │
│    │  └─ Determine overall status                          │
│    └─ Aggregate execution time                             │
│                                                              │
│ Output: ResourceValidationResult                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: AI EVALUATION (Optional)                           │
├─────────────────────────────────────────────────────────────┤
│ EvaluationAgent.evaluate()                                  │
│    ├─ Build comprehensive evaluation context               │
│    │  ├─ Resource information                              │
│    │  ├─ Discovery findings                                │
│    │  ├─ Classification details                            │
│    │  └─ Validation results                                │
│    ├─ Generate AI evaluation                               │
│    │  ├─ Assess overall health                             │
│    │  ├─ Analyze each issue                                │
│    │  ├─ Identify root causes                              │
│    │  ├─ Generate remediation steps                        │
│    │  └─ Prioritize recommendations                        │
│    └─ Fallback to rule-based if needed                     │
│                                                              │
│ Output: OverallEvaluation with insights                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FINAL: WORKFLOW RESULT                                      │
├─────────────────────────────────────────────────────────────┤
│ WorkflowResult                                              │
│    ├─ request: Original ValidationRequest                  │
│    ├─ discovery_result: WorkloadDiscoveryResult            │
│    ├─ classification: ResourceClassification               │
│    ├─ validation_plan: ValidationPlan                      │
│    ├─ validation_result: ResourceValidationResult          │
│    ├─ evaluation: OverallEvaluation                        │
│    ├─ execution_time_seconds: float                        │
│    ├─ workflow_status: success|partial|failure             │
│    └─ errors: List of any errors encountered               │
└─────────────────────────────────────────────────────────────┘
```

### Example: VM Validation Flow

```
User Input:
"Validate VM at 192.168.1.100 with user admin password secret"

↓

1. DISCOVERY (30-60s)
   ├─ Scan ports: Found 22 (SSH), 80 (HTTP), 3306 (MySQL)
   ├─ Scan processes: Found nginx, mysqld, systemd
   └─ Detect apps: nginx (0.95), MySQL (0.92)
   
   Classification: MIXED (web + database)

↓

2. PLANNING (2-5s)
   ├─ Network connectivity check (P1)
   ├─ HTTP endpoint check (P1)
   ├─ MySQL connection check (P1)
   ├─ System resources check (P2)
   └─ Filesystem usage check (P2)

↓

3. EXECUTION (15-30s)
   ├─ ✓ SSH port accessible
   ├─ ✓ HTTP responding (200 OK)
   ├─ ✓ MySQL connected
   ├─ ✓ CPU: 15%, Memory: 45%
   └─ ⚠ Disk: 87% used on /var
   
   Score: 85/100, Status: WARNING

↓

4. EVALUATION (5-10s)
   Overall Health: GOOD
   Critical Issues: None
   Warnings: High disk usage on /var
   Recommendations:
   - Clean up /var/log files
   - Monitor disk usage
   - Consider expanding storage

↓

RESULT: Validation complete in 52s
```

---

## BeeAI Framework Analysis

### Finding: **NO BeeAI Framework Usage**

After comprehensive code analysis, the project **does NOT use the BeeAI framework**. Here's what was found:

#### Evidence

1. **Single Reference Found**:
   - File: `python/src/agent.py`
   - Class: `BeeAgent` (lines 52-121)
   - **Status**: Legacy/unused code

2. **BeeAgent Class Analysis**:
   ```python
   class BeeAgent:
       def __init__(self, llm: ChatLLM, memory: TokenMemory, tools: List[Any]):
           # Simple agent with guardrails
           # NOT the BeeAI framework
   ```

3. **Not Imported or Used**:
   - No imports of `BeeAgent` in any active code
   - Not used in orchestrator or workflow
   - Not in dependencies (`pyproject.toml`, `requirements.txt`)

#### Actual Framework Used: **Pydantic AI**

The project uses **Pydantic AI** (v0.0.13+) for agent implementation:

```python
# From agents/base.py
from pydantic_ai import Agent

# Agent creation pattern
agent = Agent(
    model,  # e.g., "ollama:llama3.2"
    output_type=ResultType,  # Structured output
    system_prompt=prompt  # Agent instructions
)
```

#### Why Pydantic AI?

1. **Structured Outputs**: Guarantees type-safe responses
2. **Multi-LLM Support**: Works with Ollama, OpenAI, Groq, etc.
3. **Validation**: Built-in Pydantic validation
4. **Modern**: Active development, good documentation

#### Recommendation

**Remove `agent.py`** - It contains unused legacy code including:
- `BeeAgent` class (not BeeAI framework, just similar name)
- `OperationalGuardrails` (replaced by Pydantic validation)
- `TokenMemory` (not used in current architecture)
- `DynamicTool` (replaced by MCP tools)

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | ≥3.10 | Core implementation |
| **AI Framework** | Pydantic AI | ≥0.0.13 | Agent orchestration |
| **Data Validation** | Pydantic | ≥2.0.0 | Type safety & validation |
| **Tool Protocol** | MCP | ≥0.9.0 | Tool execution protocol |
| **HTTP Client** | httpx | ≥0.27.0 | Async HTTP requests |
| **SSH** | paramiko | ≥3.4.0 | Remote command execution |
| **MongoDB** | pymongo | ≥4.6.0 | MongoDB connectivity |

### LLM Providers Supported

| Provider | Library | Models | Use Case |
|----------|---------|--------|----------|
| **Ollama** | ollama | llama3.2, llama3.1, etc. | Local, privacy-focused |
| **OpenAI** | openai | gpt-4, gpt-4o, gpt-3.5 | Cloud, high quality |
| **Groq** | groq | llama-3.1-70b, etc. | Fast inference |
| **Google** | google-generativeai | gemini-pro | Google Cloud |
| **Anthropic** | anthropic | claude-3, etc. | Advanced reasoning |

### Development Tools

- **Package Manager**: uv (fast Python package installer)
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: black, ruff, mypy
- **Logging**: Python logging module

---

## Key Components

### Data Models (`models.py`)

#### Resource Information Models
```python
# Base resource info
BaseResourceInfo
├─ VMResourceInfo (ssh_user, ssh_password/key_path)
├─ OracleDBResourceInfo (db_user, db_password, service_name)
└─ MongoDBResourceInfo (mongo_user, mongo_password, port)

# Validation request
ValidationRequest
├─ resource_info: ResourceInfo
├─ credential_source: CredentialSource
├─ auto_discover: bool
└─ custom_acceptance_criteria: Dict
```

#### Discovery Models
```python
# Discovery results
WorkloadDiscoveryResult
├─ host: str
├─ ports: List[PortInfo]
├─ processes: List[ProcessInfo]
├─ applications: List[ApplicationDetection]
└─ errors: List[str]

# Classification
ResourceClassification
├─ category: ResourceCategory
├─ primary_application: ApplicationDetection
├─ secondary_applications: List[ApplicationDetection]
├─ confidence: float
└─ recommended_validations: List[str]
```

#### Validation Models
```python
# Validation results
ResourceValidationResult
├─ resource_type: ResourceType
├─ resource_host: str
├─ overall_status: ValidationStatus
├─ score: int (0-100)
├─ checks: List[CheckResult]
└─ execution_time_seconds: float

# Individual check
CheckResult
├─ check_id: str
├─ check_name: str
├─ status: ValidationStatus (PASS/FAIL/WARNING/ERROR)
├─ expected: str
├─ actual: str
└─ message: str
```

### LLM Integration (`llm.py`)

**Purpose**: Multi-provider LLM abstraction with safety guardrails

**Features**:
- Provider abstraction (Ollama, OpenAI, Groq, etc.)
- Safety validation (blocks dangerous commands)
- Response sanitization
- Error handling

**Guardrails**:
```python
# Blocked patterns
- Dangerous commands: rm -rf, chmod 777, etc.
- Sensitive files: /etc/shadow, /etc/passwd
- Command injection: $(), ${}, backticks
```

### MCP Clients

#### MCPStdioClient (`mcp_stdio_client.py`)
- Subprocess-based communication
- Launches MCP server as child process
- Uses stdin/stdout for JSON-RPC
- Preferred for local development

#### MCPClient (`mcp_client.py`)
- HTTP/SSE-based communication
- Connects to remote MCP server
- Uses Server-Sent Events for streaming
- Preferred for production

---

## Workflow Diagrams

### State Transition Diagram

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ start_workflow()
     ↓
┌─────────────┐
│  DISCOVERY  │ ← Optional phase
└──────┬──────┘
       │ discovery_complete
       ↓
┌──────────────────┐
│ CLASSIFICATION   │
└────────┬─────────┘
         │ classified
         ↓
┌─────────────┐
│  PLANNING   │
└──────┬──────┘
       │ plan_created
       ↓
┌──────────────┐
│ VALIDATION   │
└──────┬───────┘
       │ validations_complete
       ↓
┌──────────────┐
│ EVALUATION   │ ← Optional phase
└──────┬───────┘
       │ evaluation_complete
       ↓
┌──────────────┐
│  COMPLETED   │
└──────────────┘
```

### Agent Interaction Diagram

```
User Request
     │
     ↓
┌────────────────────┐
│  Orchestrator      │
└────────────────────┘
     │
     ├─────────────────────────────────────┐
     │                                     │
     ↓                                     ↓
┌────────────────┐                  ┌──────────────┐
│ Discovery      │                  │ Classifier   │
│ Agent          │──────────────────→│              │
└────────────────┘  WorkloadResult  └──────────────┘
     │                                     │
     │                                     │ Classification
     │                                     ↓
     │                              ┌──────────────┐
     │                              │ Validation   │
     │                              │ Agent        │
     │                              └──────────────┘
     │                                     │
     │                                     │ ValidationPlan
     │                                     ↓
     │                              ┌──────────────┐
     │                              │ MCP Client   │
     │                              │ (Execute)    │
     │                              └──────────────┘
     │                                     │
     │                                     │ Results
     │                                     ↓
     │                              ┌──────────────┐
     │                              │ Evaluation   │
     │                              │ Agent        │
     │                              └──────────────┘
     │                                     │
     └─────────────────────────────────────┘
                    │
                    ↓
              WorkflowResult
```

### Tool Execution Flow

```
Agent
  │
  │ call_tool(name, args)
  ↓
MCP Client
  │
  │ JSON-RPC Request
  ↓
MCP Server
  │
  │ route to plugin
  ↓
Plugin (net/oracle/mongo/workload)
  │
  │ execute operation
  │ ├─ SSH command
  │ ├─ Database query
  │ └─ Network scan
  ↓
Result
  │
  │ JSON-RPC Response
  ↓
MCP Client
  │
  │ parse & validate
  ↓
Agent
  │
  │ interpret result
  ↓
CheckResult
```

---

## Summary

### Architecture Highlights

1. **Multi-Agent System**: Specialized agents for discovery, validation, and evaluation
2. **AI-Powered**: Uses Pydantic AI for intelligent decision-making
3. **MCP Integration**: Standardized tool execution via Model Context Protocol
4. **Adaptive**: Creates resource-specific validation strategies
5. **Extensible**: Easy to add new resource types and validation checks

### Key Strengths

- **Intelligent Discovery**: Automatically detects applications and services
- **Context-Aware**: Uses discovery results to inform validation
- **Structured Outputs**: Type-safe results via Pydantic
- **Multi-LLM**: Works with local (Ollama) and cloud providers
- **Comprehensive**: End-to-end validation with actionable insights

### Technology Choices

- **Pydantic AI**: Modern, type-safe agent framework
- **MCP**: Standardized tool protocol
- **Python 3.10+**: Modern Python features
- **Async/Await**: Efficient concurrent operations

---

## Appendix: File Cleanup Recommendations

### Files to Remove (Redundant/Outdated)

#### Legacy Implementation Files
1. `agent.py` - Contains unused BeeAgent class (not BeeAI framework)
2. `conversation.py` - Replaced by `conversation_simple.py`
3. `mcp_client_compat.py` - Compatibility wrapper, no longer needed

#### Redundant Documentation (50+ MD files)

**Week Summaries** (Keep latest, remove older):
- Remove: `WEEK1_SUMMARY.md`, `WEEK2_SUMMARY.md`
- Keep: `WEEK3_SUMMARY.md`

**Phase Documents** (Consolidate):
- Remove: `PHASE1_IMPLEMENTATION_SUMMARY.md`, `PHASE2_ANALYSIS.md`, `PHASE2_IMPLEMENTATION_COMPLETE.md`, `PHASE2A_IMPLEMENTATION_SUMMARY.md`
- Keep: `PHASE3_MCP_BEST_PRACTICES.md`, `PHASE4_IMPLEMENTATION_PLAN.md`

**Fix Documents** (Archive or consolidate):
- Remove: `CRITICAL_FIXES_APPLIED.md`, `CRITICAL_FIXES_COMPLETE.md`, `CRITICAL_ISSUES_FIXED.md`, `TWO_CRITICAL_ISSUES_FIXED.md`, `ISSUE1_FIX_SUMMARY.md`, `ISSUE2_FIX_SUMMARY.md`, `FIXES_APPLIED.md`, `FIX_SUMMARY.md`
- Keep: `TROUBLESHOOTING.md`

**Workflow Analysis** (Consolidate):
- Remove: `AGENTIC_WORKFLOW_ANALYSIS.md`, `AGENTIC_WORKFLOW_BEST_PRACTICES.md`, `AGENTIC_WORKFLOW_COMPLETE.md`, `AGENTIC_WORKFLOW_REVIEW.md`, `AGENTIC_WORKFLOW_REVIEW_SUMMARY.md`
- Keep: This new comprehensive documentation

**Implementation Guides** (Consolidate):
- Remove: `IMPLEMENTATION_COMPLETE.md`, `IMPLEMENTATION_GUIDE.md`, `IMPLEMENTATION_STEP_BY_STEP.md`
- Keep: `HOW_TO_RUN.md`, `TESTING_GUIDE.md`

**Status Reports** (Archive):
- Remove: `FINAL_STATUS.md`, `FINAL_STATUS_REPORT.md`, `FINAL_REVIEW_SUMMARY.md`, `SETUP_COMPLETE.md`

**Specific Feature Docs** (Consolidate):
- Remove: `EMAIL_CONFIGURATION_GUIDE.md`, `EMAIL_FIX_PLAN.md`, `EMAIL_FIXES_APPLIED.md`, `SENDGRID_SETUP.md`, `QUICK_SENDGRID_SETUP.md`, `TEST_EMAIL_FEATURE.md`
- Keep: Email configuration in main docs

**Tool/LLM Docs** (Consolidate):
- Remove: `LLM_DRIVEN_TOOL_SELECTION.md`, `LLM_TOOL_SELECTOR_IMPLEMENTATION.md`, `LLM_PROMPT_ENHANCEMENT_GUIDE.md`, `TOOL_CATEGORIZATION_IMPLEMENTATION_PLAN.md`, `TOOL_CATEGORIZATION_STRATEGY.md`, `TOOL_SELECTION_ISSUES_AND_FIXES.md`

**Ollama Docs** (Consolidate):
- Remove: `OLLAMA_API_FIX.md`, `OLLAMA_CONFIGURATION_FIX.md`, `OLLAMA_LOCAL_TESTING.md`
- Keep: `QUICK_START_OLLAMA.md`

**MCP Docs** (Consolidate):
- Remove: `MCP_CENTRIC_WORKFLOW_SWITCH.md`, `MCP_CONNECTION_FIX.md`, `MCP_CONNECTION_SUCCESS.md`, `CORRECT_MCP_WORKFLOW.md`
- Keep: `PHASE3_MCP_BEST_PRACTICES.md`

**Other** (Consolidate):
- Remove: `PRIORITY_ERROR_ANALYSIS.md`, `PRIORITY_FIELD_FIX.md`, `PYDANTIC_AI_INTEGRATION.md`, `MIGRATION_STRATEGY.md`, `WORKFLOW_DECISION_MAP.md`, `WORKFLOW_IMPROVEMENT_ROADMAP.md`, `WORKFLOW_SUMMARY.md`, `VALIDATION_WORKFLOW_PLAN.md`, `ARCHITECTURE_RATIONALE.md`, `EXECUTIVE_SUMMARY.md`

#### Keep These Essential Docs
1. `README.md` - Main project documentation
2. `HOW_TO_RUN.md` - Quick start guide
3. `TESTING_GUIDE.md` - Testing instructions
4. `TROUBLESHOOTING.md` - Common issues
5. `QUICK_START.md` - Quick start
6. `QUICK_START_OLLAMA.md` - Ollama setup
7. `RECOVERY_VALIDATION_README.md` - Recovery validation guide
8. `README_AGENTIC_TRANSFORMATION.md` - Transformation overview
9. `PHASE3_MCP_BEST_PRACTICES.md` - MCP best practices
10. `PHASE4_IMPLEMENTATION_PLAN.md` - Implementation plan
11. `AGENTIC_WORKFLOW_COMPREHENSIVE_DOCUMENTATION.md` - This document

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-25  
**Author**: IBM Bob (Agentic AI Analysis)  
**Status**: Complete and Ready for Review