# BeeAI Framework Migration Plan
## CyberRes Recovery Validation Agent

**Project**: CyberRes Recovery Validation Agent  
**Date**: 2026-02-25  
**Version**: 1.0  
**Migration Target**: IBM Bee Agent Framework (Python)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [BeeAI Framework Overview](#beeai-framework-overview)
4. [Component Mapping](#component-mapping)
5. [Migration Strategy](#migration-strategy)
6. [Agent Architecture Design](#agent-architecture-design)
7. [Tool Integration Plan](#tool-integration-plan)
8. [Memory and State Management](#memory-and-state-management)
9. [Reasoning and Decision Flow](#reasoning-and-decision-flow)
10. [Error Handling and Resilience](#error-handling-and-resilience)
11. [Implementation Roadmap](#implementation-roadmap)
12. [Code Examples](#code-examples)
13. [Performance Considerations](#performance-considerations)
14. [Risk Assessment](#risk-assessment)

---

## Executive Summary

### Migration Overview

This document outlines a comprehensive plan to migrate the CyberRes Recovery Validation Agent from **Pydantic AI** to the **IBM Bee Agent Framework**. The migration aims to leverage BeeAI's production-grade features while maintaining or enhancing the existing workflow's functionality.

### Key Benefits of Migration

1. **Production Optimization**: Built-in caching, memory optimization, and resource management
2. **Agent Constraints**: Enforce deterministic rules while preserving reasoning abilities
3. **Dynamic Workflows**: Advanced patterns for parallelism, retries, and replanning
4. **Declarative Orchestration**: YAML-based agent system definitions for maintainability
5. **Native MCP Support**: First-class MCP and A2A agent interoperability
6. **Observability**: OpenTelemetry support for monitoring and tracing
7. **Multi-Agent Coordination**: Better support for complex agent interactions

### Migration Scope

- **4 Specialized Agents**: Discovery, Validation, Evaluation, Classification
- **1 Orchestrator**: Central workflow coordinator
- **15+ MCP Tools**: Network, VM, Database, and Workload Discovery tools
- **Structured Data Models**: Pydantic models for type safety
- **Multi-Phase Workflow**: Discovery → Planning → Execution → Evaluation

### Estimated Timeline

- **Phase 1**: Foundation (2 weeks)
- **Phase 2**: Core Agents (3 weeks)
- **Phase 3**: Integration (2 weeks)
- **Phase 4**: Testing & Optimization (2 weeks)
- **Total**: 9 weeks

---

## Current State Analysis

### Architecture Overview

The current system uses **Pydantic AI** with the following architecture:

```
User Interface Layer
    ↓
ValidationOrchestrator (Coordinator)
    ↓
Agent Layer (Pydantic AI)
    ├─ DiscoveryAgent
    ├─ ValidationAgent
    ├─ EvaluationAgent
    └─ ApplicationClassifier (Rule-based)
    ↓
MCP Integration Layer
    ├─ MCPClient (HTTP)
    └─ MCPStdioClient (stdio)
    ↓
Tool Layer (MCP Server)
    ├─ Network Tools
    ├─ VM Tools
    ├─ Database Tools
    └─ Workload Discovery Tools
```

### Current Components

#### 1. **ValidationOrchestrator** ([`agents/orchestrator.py`](python/src/agents/orchestrator.py))
- **Role**: Central coordinator
- **Responsibilities**:
  - Manages workflow phases
  - Coordinates all agents
  - Handles errors and retries
  - Aggregates results
- **Key Methods**:
  - `execute_workflow()`: Main entry point
  - `_execute_discovery()`: Discovery phase
  - `_create_validation_plan()`: Planning phase
  - `_execute_validations()`: Execution phase
  - `_evaluate_results()`: Evaluation phase

#### 2. **DiscoveryAgent** ([`agents/discovery_agent.py`](python/src/agents/discovery_agent.py))
- **Framework**: Pydantic AI
- **Result Type**: `DiscoveryPlan`
- **Capabilities**:
  - AI-powered discovery planning with Chain-of-Thought
  - Fast-path optimization for simple resources
  - Port scanning, process analysis, application detection
- **Decision Making**:
  - Determines which discovery methods to use
  - Balances thoroughness with efficiency

#### 3. **ValidationAgent** ([`agents/validation_agent.py`](python/src/agents/validation_agent.py))
- **Framework**: Pydantic AI
- **Result Type**: `ValidationPlan`
- **Capabilities**:
  - Creates comprehensive validation plans
  - Selects appropriate MCP tools
  - Prioritizes checks (1-5 scale)
  - Provides fallback plans
- **Decision Making**:
  - Resource-specific validation strategies
  - Priority-based check ordering

#### 4. **EvaluationAgent** ([`agents/evaluation_agent.py`](python/src/agents/evaluation_agent.py))
- **Framework**: Pydantic AI
- **Result Type**: `OverallEvaluation`
- **Capabilities**:
  - AI-powered result analysis
  - Root cause identification
  - Remediation recommendations
  - Trend analysis
- **Decision Making**:
  - Health assessment (excellent → critical)
  - Severity assignment (critical → info)
  - Recommendation prioritization

#### 5. **ApplicationClassifier** ([`classifier.py`](python/src/classifier.py))
- **Type**: Rule-based (no AI)
- **Capabilities**:
  - Application signature matching
  - Confidence-based filtering
  - Multi-application detection
- **Categories**: Database, Web, App Server, Message Queue, Cache, Mixed, Unknown

### Current Workflow Phases

```
Phase 1: Workload Discovery (Optional, 30-60s)
    ├─ Create discovery plan (AI or fast-path)
    ├─ Scan ports, processes, applications
    └─ Classify resource type
    
Phase 2: Validation Planning (2-5s)
    ├─ Build context from discovery
    ├─ Generate AI-powered validation plan
    └─ Select MCP tools and prioritize checks
    
Phase 3: Validation Execution (15-30s)
    ├─ Execute each check via MCP
    ├─ Interpret results
    └─ Calculate overall status
    
Phase 4: AI Evaluation (Optional, 5-10s)
    ├─ Analyze results in context
    ├─ Identify root causes
    └─ Generate recommendations
```

### Technology Stack

- **AI Framework**: Pydantic AI
- **Data Models**: Pydantic v2
- **MCP Integration**: Custom clients (HTTP + stdio)
- **LLM Providers**: Ollama, OpenAI, Groq, Anthropic
- **Language**: Python 3.11+

### Strengths of Current Implementation

1. ✅ **Structured Outputs**: Pydantic AI ensures type-safe responses
2. ✅ **MCP Integration**: Well-designed MCP client architecture
3. ✅ **Multi-Phase Workflow**: Clear separation of concerns
4. ✅ **Flexible LLM Support**: Works with multiple providers
5. ✅ **Error Handling**: Fallback mechanisms for AI failures
6. ✅ **Fast-Path Optimization**: Skips AI for simple cases

### Limitations and Gaps

1. ❌ **No Built-in Caching**: Manual implementation required
2. ❌ **Limited Observability**: No native tracing/monitoring
3. ❌ **Manual Orchestration**: Complex coordination logic
4. ❌ **No Constraint System**: Cannot enforce deterministic rules
5. ❌ **Limited Parallelism**: Sequential execution only
6. ❌ **No Memory Management**: Stateless agents
7. ❌ **Manual Retry Logic**: Custom implementation needed

---

## BeeAI Framework Overview

### Core Capabilities

Based on research of the IBM Bee Agent Framework, here are the key features:

#### 1. **Production Optimization**
- Built-in caching for LLM responses
- Memory optimization and resource management
- Scalable deployment support

#### 2. **Agents with Constraints**
- Preserve reasoning abilities
- Enforce deterministic rules
- Balance flexibility with control

#### 3. **Dynamic Workflows**
- Decorators for multi-agent patterns
- Built-in parallelism support
- Automatic retries and replanning

#### 4. **Declarative Orchestration**
- YAML-based agent definitions
- Predictable and maintainable
- Version-controlled configurations

#### 5. **Pluggable Observability**
- Native OpenTelemetry support
- Real-time monitoring
- Detailed tracing and auditing

#### 6. **MCP and A2A Native**
- First-class MCP tool support
- Agent-to-Agent communication
- Interoperability with MCP/A2A agents

#### 7. **Built-in Tools**
- Handoff: Delegate to expert agents
- OpenAPI: Consume external APIs
- Python/Sandbox: Execute custom code
- Wikipedia, DuckDuckGo, etc.

#### 8. **Memory System**
- Message-based memory (USER, ASSISTANT, SYSTEM roles)
- Context preservation across interactions
- Conversation history management

### BeeAI Architecture Pattern

```
┌─────────────────────────────────────────┐
│         BeeAI Agent Framework           │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Agent (with LLM + Tools)        │ │
│  │   ├─ System Prompt                │ │
│  │   ├─ Memory (Messages)            │ │
│  │   ├─ Tools (MCP, Custom)          │ │
│  │   ├─ Constraints (Rules)          │ │
│  │   └─ Observability (Telemetry)    │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Orchestration Layer             │ │
│  │   ├─ Workflow Decorators          │ │
│  │   ├─ Parallelism                  │ │
│  │   ├─ Retries                      │ │
│  │   └─ Agent Handoff                │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Tool Integration                │ │
│  │   ├─ MCP Tools (Native)           │ │
│  │   ├─ Custom Tools                 │ │
│  │   ├─ OpenAPI Tools                │ │
│  │   └─ Python Sandbox               │ │
│  └───────────────────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

---

## Component Mapping

### Pydantic AI → BeeAI Mapping

| Current Component | Pydantic AI Pattern | BeeAI Equivalent | Migration Approach |
|-------------------|---------------------|------------------|-------------------|
| **DiscoveryAgent** | `Agent[DiscoveryContext, DiscoveryPlan]` | `BeeAgent` with discovery tools | Direct replacement with enhanced memory |
| **ValidationAgent** | `Agent[ValidationContext, ValidationPlan]` | `BeeAgent` with planning tools | Direct replacement with constraints |
| **EvaluationAgent** | `Agent[EvaluationContext, OverallEvaluation]` | `BeeAgent` with analysis tools | Direct replacement with structured output |
| **ApplicationClassifier** | Rule-based Python class | Custom BeeAI Tool | Wrap as tool for agent use |
| **ValidationOrchestrator** | Manual coordination | BeeAI Workflow with decorators | Declarative orchestration |
| **MCP Tools** | Custom MCP clients | Native MCP integration | Simplified integration |
| **AgentConfig** | Custom configuration | BeeAI Agent configuration | Use framework config |
| **Memory/State** | Stateless | BeeAI Memory system | Add conversation memory |
| **Error Handling** | Manual try/catch | BeeAI retry decorators | Use framework retries |
| **Observability** | Custom logging | OpenTelemetry | Native tracing |

### Data Model Mapping

| Current Model | Purpose | BeeAI Approach |
|---------------|---------|----------------|
| `DiscoveryPlan` | Discovery strategy | Structured output from agent |
| `ValidationPlan` | Validation strategy | Structured output from agent |
| `OverallEvaluation` | AI evaluation | Structured output from agent |
| `WorkloadDiscoveryResult` | Discovery findings | Agent memory + structured output |
| `ResourceClassification` | Resource categorization | Tool output |
| `ValidationRequest` | User input | Agent input message |
| `WorkflowResult` | Complete result | Orchestrator output |

---

## Migration Strategy

### Approach: Phased Incremental Migration

We will use a **phased incremental approach** to minimize risk and ensure continuous functionality:

1. **Phase 1: Foundation** - Set up BeeAI infrastructure alongside existing system
2. **Phase 2: Core Agents** - Migrate agents one at a time with parallel testing
3. **Phase 3: Integration** - Replace orchestrator and integrate components
4. **Phase 4: Optimization** - Leverage BeeAI advanced features

### Migration Principles

1. **Maintain Functionality**: Existing features must work identically or better
2. **Backward Compatibility**: Support existing MCP tools without changes
3. **Incremental Testing**: Test each component before moving to next
4. **Parallel Operation**: Run old and new systems side-by-side during transition
5. **Data Model Preservation**: Keep Pydantic models for type safety
6. **Gradual Enhancement**: Add BeeAI features progressively

### What to Keep vs. Replace

#### ✅ **Keep (Minimal Changes)**

- **Pydantic Data Models**: Continue using for type safety
- **MCP Server**: No changes needed
- **MCP Tools**: Existing tools work with BeeAI
- **Business Logic**: Validation rules, classification logic
- **Test Suite**: Adapt tests, don't rewrite

#### 🔄 **Replace (Direct Migration)**

- **Pydantic AI Agents** → **BeeAI Agents**
- **Manual Orchestration** → **BeeAI Workflow Decorators**
- **Custom MCP Clients** → **BeeAI Native MCP Integration**
- **Manual Retry Logic** → **BeeAI Retry Decorators**
- **Custom Logging** → **OpenTelemetry Tracing**

#### ➕ **Add (New Capabilities)**

- **Memory System**: Add conversation history
- **Constraints**: Enforce validation rules
- **Caching**: LLM response caching
- **Parallelism**: Concurrent validation checks
- **Observability**: Real-time monitoring

---

## Agent Architecture Design

### BeeAI Agent Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│              ValidationOrchestrator                      │
│              (BeeAI Workflow Coordinator)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Workflow Phases:                                │   │
│  │  1. Discovery (optional)                         │   │
│  │  2. Classification                               │   │
│  │  3. Planning                                     │   │
│  │  4. Execution (parallel)                         │   │
│  │  5. Evaluation (optional)                        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    Agent Layer                           │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ DiscoveryAgent   │  │ ValidationAgent  │            │
│  │ (BeeAgent)       │  │ (BeeAgent)       │            │
│  │                  │  │                  │            │
│  │ Tools:           │  │ Tools:           │            │
│  │ - scan_ports     │  │ - classifier     │            │
│  │ - scan_processes │  │ - tool_selector  │            │
│  │ - detect_apps    │  │ - mcp_tools      │            │
│  │                  │  │                  │            │
│  │ Memory: Yes      │  │ Memory: Yes      │            │
│  │ Constraints: Yes │  │ Constraints: Yes │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ EvaluationAgent  │  │ ExecutionAgent   │            │
│  │ (BeeAgent)       │  │ (BeeAgent)       │            │
│  │                  │  │                  │            │
│  │ Tools:           │  │ Tools:           │            │
│  │ - analyze_results│  │ - mcp_tools      │            │
│  │ - root_cause     │  │ - parallel_exec  │            │
│  │ - recommend      │  │                  │            │
│  │                  │  │                  │            │
│  │ Memory: Yes      │  │ Memory: No       │            │
│  │ Constraints: Yes │  │ Constraints: Yes │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    Tool Layer                            │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ MCP Tools        │  │ Custom Tools     │            │
│  │ (Native BeeAI)   │  │ (BeeAI Tools)    │            │
│  │                  │  │                  │            │
│  │ - Network tools  │  │ - Classifier     │            │
│  │ - VM tools       │  │ - Aggregator     │            │
│  │ - DB tools       │  │ - Validator      │            │
│  │ - Discovery tools│  │                  │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### Agent Specifications

#### 1. **DiscoveryAgent (BeeAI)**

```python
# Agent Configuration
name: "DiscoveryAgent"
description: "Intelligent workload discovery using AI-powered planning"
llm: configurable (Ollama, OpenAI, etc.)

# System Prompt
You are a workload discovery expert. Analyze resources and create optimal 
discovery plans. Use available tools to scan ports, processes, and detect 
applications. Balance thoroughness with efficiency.

# Tools
- workload_scan_ports: Scan for open ports
- workload_scan_processes: Analyze running processes
- workload_detect_applications: Identify applications
- workload_aggregate: Combine discovery results

# Memory
- Enabled: Yes
- Type: Conversation history
- Retention: Per-workflow session

# Constraints
- Must use at least one discovery method
- Port scanning required for network resources
- Process scanning required for VMs
- Confidence threshold: 0.6 for application detection

# Output
Structured: DiscoveryPlan (Pydantic model)
```

#### 2. **ValidationAgent (BeeAI)**

```python
# Agent Configuration
name: "ValidationAgent"
description: "Creates intelligent validation plans based on resource classification"
llm: configurable

# System Prompt
You are a validation planning expert. Create comprehensive validation plans 
with prioritized checks. Select appropriate MCP tools for each validation. 
Consider resource type, discovered applications, and criticality.

# Tools
- application_classifier: Classify resource type
- tool_selector: Select appropriate MCP tools
- mcp_tool_*: All available MCP tools

# Memory
- Enabled: Yes
- Type: Conversation history
- Retention: Per-workflow session

# Constraints
- Priority range: 1-5 (1=highest)
- Must include at least 3 checks
- Network connectivity check always priority 1
- Estimated time must be realistic

# Output
Structured: ValidationPlan (Pydantic model)
```

#### 3. **EvaluationAgent (BeeAI)**

```python
# Agent Configuration
name: "EvaluationAgent"
description: "AI-powered evaluation with actionable insights"
llm: configurable

# System Prompt
You are an evaluation expert. Analyze validation results in context, assess 
severity, identify root causes, and provide specific remediation steps. 
Generate prioritized recommendations.

# Tools
- analyze_results: Deep analysis of validation results
- identify_root_cause: Root cause analysis
- generate_recommendations: Create actionable recommendations

# Memory
- Enabled: Yes
- Type: Conversation history
- Retention: Per-workflow session

# Constraints
- Health levels: excellent, good, fair, poor, critical
- Severity levels: critical, high, medium, low, info
- Must provide at least 3 recommendations
- Recommendations must be specific and actionable

# Output
Structured: OverallEvaluation (Pydantic model)
```

#### 4. **ExecutionAgent (BeeAI)**

```python
# Agent Configuration
name: "ExecutionAgent"
description: "Executes validation checks with parallel execution support"
llm: minimal (tool execution focused)

# System Prompt
You execute validation checks efficiently. Use MCP tools to perform checks, 
interpret results, and handle errors gracefully. Support parallel execution 
for independent checks.

# Tools
- All MCP tools (network, VM, database, discovery)
- parallel_executor: Execute independent checks concurrently

# Memory
- Enabled: No (stateless execution)
- Type: N/A

# Constraints
- Timeout per check: 30 seconds
- Max parallel checks: 5
- Retry failed checks: 2 attempts
- Must handle tool errors gracefully

# Output
Structured: List[CheckResult] (Pydantic model)
```

### Agent Communication Patterns

#### Pattern 1: Sequential Handoff
```
DiscoveryAgent → ValidationAgent → ExecutionAgent → EvaluationAgent
```
- Each agent completes before next starts
- Results passed via structured outputs
- Memory preserved across handoffs

#### Pattern 2: Parallel Execution
```
ValidationAgent → [ExecutionAgent (Check 1), ExecutionAgent (Check 2), ...]
```
- Independent checks run concurrently
- Results aggregated by orchestrator
- Faster overall execution

#### Pattern 3: Conditional Flow
```
Orchestrator → DiscoveryAgent (if auto_discover=True)
            → ValidationAgent (always)
            → ExecutionAgent (always)
            → EvaluationAgent (if enable_ai_evaluation=True)
```
- Conditional agent invocation
- Configuration-driven workflow
- Flexible execution paths

---

## Tool Integration Plan

### MCP Tool Integration Strategy

BeeAI has native MCP support, simplifying our integration:

#### Current Approach (Custom MCP Clients)
```python
# Current: Manual MCP client management
mcp_client = MCPStdioClient(server_path, server_args)
await mcp_client.connect()
tools = await mcp_client.list_tools()
result = await mcp_client.call_tool(tool_name, args)
```

#### BeeAI Approach (Native Integration)
```python
# BeeAI: Native MCP tool integration
from bee_agent_framework.tools import MCPTool

# Automatic tool discovery and registration
mcp_tools = MCPTool.from_server(
    server_path="path/to/mcp/server",
    server_args=["--mode", "stdio"]
)

# Agent automatically uses tools
agent = BeeAgent(
    llm=llm,
    tools=[*mcp_tools],  # All MCP tools available
    system_prompt="..."
)
```

### Tool Categories and Mapping

#### 1. **Network Tools**
| Current MCP Tool | BeeAI Integration | Notes |
|------------------|-------------------|-------|
| `tcp_portcheck` | Native MCP | Direct integration |

#### 2. **VM Tools**
| Current MCP Tool | BeeAI Integration | Notes |
|------------------|-------------------|-------|
| `vm_linux_uptime_load_mem` | Native MCP | Direct integration |
| `vm_linux_fs_usage` | Native MCP | Direct integration |
| `vm_linux_services` | Native MCP | Direct integration |

#### 3. **Oracle Database Tools**
| Current MCP Tool | BeeAI Integration | Notes |
|------------------|-------------------|-------|
| `db_oracle_connect` | Native MCP | Direct integration |
| `db_oracle_tablespaces` | Native MCP | Direct integration |
| `db_oracle_discover_and_validate` | Native MCP | Direct integration |

#### 4. **MongoDB Tools**
| Current MCP Tool | BeeAI Integration | Notes |
|------------------|-------------------|-------|
| `db_mongo_connect` | Native MCP | Direct integration |
| `db_mongo_rs_status` | Native MCP | Direct integration |
| `db_mongo_ssh_ping` | Native MCP | Direct integration |
| `validate_collection` | Native MCP | Direct integration |

#### 5. **Workload Discovery Tools**
| Current MCP Tool | BeeAI Integration | Notes |
|------------------|-------------------|-------|
| `workload_scan_ports` | Native MCP | Direct integration |
| `workload_scan_processes` | Native MCP | Direct integration |
| `workload_detect_applications` | Native MCP | Direct integration |
| `workload_aggregate_results` | Native MCP | Direct integration |

### Custom Tool Development

For non-MCP functionality, we'll create custom BeeAI tools:

#### ApplicationClassifier Tool
```python
from bee_agent_framework.tools import Tool

class ApplicationClassifierTool(Tool):
    """Classify resources based on discovered applications."""
    
    name = "application_classifier"
    description = "Classify resource type based on discovered applications"
    
    async def run(self, applications: List[Dict]) -> ResourceClassification:
        """Execute classification logic."""
        classifier = ApplicationClassifier()
        return classifier.classify(applications)
```

#### ValidationPlanBuilder Tool
```python
class ValidationPlanBuilderTool(Tool):
    """Build validation plans with rule-based fallback."""
    
    name = "validation_plan_builder"
    description = "Create validation plan with appropriate checks"
    
    async def run(
        self, 
        resource_type: str,
        classification: ResourceClassification,
        available_tools: List[str]
    ) -> ValidationPlan:
        """Build validation plan."""
        # Rule-based plan generation
        return self._build_plan(resource_type, classification, available_tools)
```

---

## Memory and State Management

### Current State: Stateless Agents

The current implementation is **stateless**:
- Each agent invocation is independent
- No conversation history
- Context passed explicitly via parameters
- No learning from previous interactions

### BeeAI Memory System

BeeAI provides a **message-based memory system**:

```python
# Memory structure
Memory = List[Message]

Message = {
    "role": "USER" | "ASSISTANT" | "SYSTEM",
    "content": str,
    "metadata": Dict[str, Any]
}
```

### Memory Strategy for Migration

#### 1. **Workflow-Level Memory**

Each workflow execution maintains its own memory:

```python
# Workflow memory lifecycle
workflow_memory = Memory()

# Phase 1: Discovery
workflow_memory.add(Message(
    role="USER",
    content=f"Discover workloads on {resource.host}"
))
discovery_result = await discovery_agent.run(memory=workflow_memory)
workflow_memory.add(Message(
    role="ASSISTANT",
    content=f"Discovery complete: {discovery_result}"
))

# Phase 2: Validation Planning
workflow_memory.add(Message(
    role="USER",
    content=f"Create validation plan for {classification.category}"
))
validation_plan = await validation_agent.run(memory=workflow_memory)
workflow_memory.add(Message(
    role="ASSISTANT",
    content=f"Plan created: {validation_plan}"
))

# Memory persists across phases
```

#### 2. **Agent-Specific Memory**

Each agent maintains context within its scope:

```python
# DiscoveryAgent memory
discovery_memory = [
    {"role": "SYSTEM", "content": "You are a discovery expert..."},
    {"role": "USER", "content": "Analyze VM at 192.168.1.100"},
    {"role": "ASSISTANT", "content": "Scanning ports..."},
    {"role": "ASSISTANT", "content": "Found: SSH, HTTP, MySQL"}
]

# ValidationAgent memory (includes discovery context)
validation_memory = [
    {"role": "SYSTEM", "content": "You are a validation expert..."},
    {"role": "USER", "content": "Resource has SSH, HTTP, MySQL"},
    {"role": "ASSISTANT", "content": "Creating plan for web+database..."}
]
```

#### 3. **Persistent Memory (Optional)**

For trend analysis and learning:

```python
# Store workflow results for future reference
persistent_memory = PersistentMemory(storage="redis")

# After workflow completion
await persistent_memory.store(
    key=f"workflow_{resource.host}_{timestamp}",
    value={
        "discovery": discovery_result,
        "validation": validation_result,
        "evaluation": evaluation_result
    }
)

# Retrieve for trend analysis
historical_results = await persistent_memory.retrieve(
    pattern=f"workflow_{resource.host}_*"
)
```

### Memory Benefits

1. **Context Preservation**: Agents understand previous steps
2. **Better Reasoning**: LLMs make informed decisions with history
3. **Debugging**: Full conversation trace for troubleshooting
4. **Trend Analysis**: Learn from historical patterns
5. **Personalization**: Adapt to specific environments

---

## Reasoning and Decision Flow

### Current Decision-Making

The current system uses **explicit decision trees**:

```python
# Orchestrator decision tree
if request.auto_discover:
    discovery_result = await self._execute_discovery()
    classification = self.classifier.classify(discovery_result)
else:
    classification = self._default_classification()

# Discovery agent decision
if resource_type == "vm" and not complex_requirements:
    # Fast-path: Skip LLM
    plan = self._default_discovery_plan()
else:
    # AI-powered planning
    plan = await self.planning_agent.run(context)
```

### BeeAI Decision Flow

BeeAI uses **agent-driven reasoning** with constraints:

#### 1. **Constraint-Based Decisions**

```python
# Define constraints for agent behavior
discovery_constraints = {
    "must_scan_ports": True,
    "min_confidence": 0.6,
    "max_scan_time": 60,
    "required_methods": ["ports", "processes"]
}

# Agent respects constraints while reasoning
agent = BeeAgent(
    llm=llm,
    tools=discovery_tools,
    constraints=discovery_constraints,
    system_prompt="..."
)
```

#### 2. **Tool Selection Reasoning**

```python
# Agent decides which tools to use based on context
# Example: ValidationAgent reasoning

System: You have these tools: tcp_portcheck, vm_linux_uptime, 
        db_oracle_connect, workload_scan_ports

User: Create validation plan for VM with MySQL database

Agent Reasoning:
1. Resource is VM → need VM tools
2. Has MySQL → need database tools
3. Network connectivity critical → need network tools

Agent Decision:
- Use tcp_portcheck (priority 1)
- Use vm_linux_uptime (priority 1)
- Use db_oracle_connect (priority 2)
- Skip workload_scan_ports (already discovered)
```

#### 3. **Adaptive Replanning**

```python
# BeeAI supports dynamic replanning on failures

@workflow_with_retry(max_attempts=3)
async def execute_validation_check(check: ValidationCheck):
    try:
        result = await agent.run_tool(check.mcp_tool, check.tool_args)
        return result
    except ToolError as e:
        # Agent can replan with alternative approach
        alternative_plan = await agent.replan(
            failed_check=check,
            error=e,
            available_tools=remaining_tools
        )
        return await execute_validation_check(alternative_plan)
```

### Decision Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  User Request                            │
│         "Validate VM at 192.168.1.100"                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Orchestrator Decision                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ IF auto_discover:                                │   │
│  │   → Invoke DiscoveryAgent                        │   │
│  │ ELSE:                                            │   │
│  │   → Use default classification                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           DiscoveryAgent Reasoning                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Analyze: VM resource, no prior knowledge         │   │
│  │ Decide: Need comprehensive discovery             │   │
│  │ Tools: scan_ports, scan_processes, detect_apps   │   │
│  │ Constraints: min_confidence=0.6, max_time=60s    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         ApplicationClassifier Decision                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Input: nginx (0.95), MySQL (0.92)                │   │
│  │ Decide: MIXED category (web + database)          │   │
│  │ Output: ResourceClassification                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          ValidationAgent Reasoning                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Analyze: MIXED (web + database)                  │   │
│  │ Decide: Need web AND database checks             │   │
│  │ Tools: tcp_portcheck, vm_tools, db_tools         │   │
│  │ Priority: Network (P1), DB (P1), System (P2)     │   │
│  │ Constraints: min_checks=3, realistic_time        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          ExecutionAgent Decisions                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Analyze: 5 checks, 3 independent                 │   │
│  │ Decide: Parallel execution for independent       │   │
│  │ Execute: [Check1, Check2, Check3] in parallel    │   │
│  │          [Check4, Check5] sequentially           │   │
│  │ Constraints: max_parallel=5, timeout=30s         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         EvaluationAgent Reasoning                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Analyze: 4 passed, 1 warning (disk usage)        │   │
│  │ Decide: Overall health = GOOD                    │   │
│  │ Root Cause: High disk usage on /var              │   │
│  │ Recommendations: Clean logs, monitor, expand     │   │
│  │ Constraints: min_recommendations=3, actionable   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Error Handling and Resilience

### Current Error Handling

The current system uses **manual error handling**:

```python
# Manual try-catch blocks
try:
    result = await agent.run(context)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    result = self._create_fallback_result()

# Manual retry logic
for attempt in range(max_retries):
    try:
        result = await execute_check()
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        await asyncio.sleep(retry_delay)
```

### BeeAI Error Handling

BeeAI provides **declarative error handling**:

#### 1. **Retry Decorators**

```python
from bee_agent_framework.decorators import retry

@retry(max_attempts=3, backoff=exponential, exceptions=[ToolError])
async def execute_discovery(agent, resource):
    """Automatically retries on ToolError with exponential backoff."""
    return await agent.run(f"Discover workloads on {resource.host}")
```

#### 2. **Fallback Mechanisms**

```python
from bee_agent_framework.decorators import fallback

@fallback(fallback_fn=create_default_plan)
async def create_validation_plan(agent, classification):
    """Falls back to default plan if agent fails."""
    return await agent.run(f"Create plan for {classification.category}")

def create_default_plan(classification):
    """Fallback function for validation planning."""
    return ValidationPlan(
        strategy_name="default",
        checks=get_default_checks(classification.category),
        reasoning="Fallback to rule-based plan due to agent failure"
    )
```

#### 3. **Circuit Breaker**

```python
from bee_agent_framework.resilience import CircuitBreaker

# Prevent cascading failures
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    recovery_timeout=300
)

@circuit_breaker.protect
async def call_external_service(service_url):
    """Protected by circuit breaker."""
    return await http_client.get(service_url)
```

#### 4. **Timeout Management**

```python
from bee_agent_framework.decorators import timeout

@timeout(seconds=30)
async def execute_validation_check(check):
    """Automatically times out after 30 seconds."""
    return await mcp_client.call_tool(check.mcp_tool, check.tool_args)
```

### Error Handling Strategy

#### Level 1: Tool-Level Errors
```python
# Individual tool failures
@retry(max_attempts=2)
@timeout(seconds=30)
async def execute_mcp_tool(tool_name, args):
    try:
        return await mcp_client.call_tool(tool_name, args)
    except MCPToolError as e:
        logger.warning(f"Tool {tool_name} failed: {e}")
        return CheckResult(
            status=ValidationStatus.ERROR,
            message=f"Tool execution failed: {e}"
        )
```

#### Level 2: Agent-Level Errors
```python
# Agent failures with fallback
@fallback(fallback_fn=rule_based_planning)
@retry(max_attempts=2)
async def agent_create_plan(agent, context):
    try:
        return await agent.run(context)
    except AgentError as e:
        logger.error(f"Agent failed: {e}")
        raise  # Trigger fallback
```

#### Level 3: Workflow-Level Errors
```python
# Workflow failures with graceful degradation
async def execute_workflow(request):
    try:
        # Phase 1: Discovery (optional)
        if request.auto_discover:
            try:
                discovery_result = await execute_discovery()
            except Exception as e:
                logger.warning(f"Discovery failed: {e}")
                discovery_result = None  # Continue without discovery
        
        # Phase 2: Validation (required)
        validation_result = await execute_validation()
        
        # Phase 3: Evaluation (optional)
        if request.enable_ai_evaluation:
            try:
                evaluation = await execute_evaluation()
            except Exception as e:
                logger.warning(f"Evaluation failed: {e}")
                evaluation = None  # Continue without evaluation
        
        return WorkflowResult(
            validation_result=validation_result,
            discovery_result=discovery_result,
            evaluation=evaluation,
            workflow_status="success" if validation_result.status == "PASS" else "partial_success"
        )
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return WorkflowResult(
            workflow_status="failure",
            errors=[str(e)]
        )
```

### Error Categories and Responses

| Error Type | Severity | Response Strategy |
|------------|----------|-------------------|
| **Tool Timeout** | Medium | Retry with increased timeout |
| **Tool Not Found** | High | Skip check, log warning |
| **Tool Execution Error** | Medium | Retry, then mark as ERROR |
| **Agent LLM Failure** | High | Fallback to rule-based |
| **Agent Timeout** | Medium | Retry with simplified prompt |
| **MCP Connection Lost** | Critical | Reconnect, retry workflow |
| **Invalid Input** | High | Return validation error immediately |
| **Resource Unreachable** | High | Mark as FAIL, continue workflow |

---

## Implementation Roadmap

### Phase 1: Foundation (2 weeks)

**Goal**: Set up BeeAI infrastructure and validate basic functionality

#### Week 1: Setup and Configuration
- [ ] Install BeeAI framework (`pip install bee-agent-framework`)
- [ ] Create BeeAI project structure
- [ ] Configure LLM providers (Ollama, OpenAI)
- [ ] Set up development environment
- [ ] Create basic agent template
- [ ] Test MCP tool integration

**Deliverables**:
- BeeAI project initialized
- Basic agent running with MCP tools
- Configuration files created

#### Week 2: Tool Integration
- [ ] Integrate all MCP tools with BeeAI
- [ ] Create custom tools (Classifier, Aggregator)
- [ ] Test tool discovery and execution
- [ ] Implement tool error handling
- [ ] Create tool documentation

**Deliverables**:
- All MCP tools working with BeeAI
- Custom tools implemented
- Tool integration tests passing

### Phase 2: Core Agents (3 weeks)

**Goal**: Migrate all agents to BeeAI framework

#### Week 3: DiscoveryAgent Migration
- [ ] Create BeeAI DiscoveryAgent
- [ ] Implement discovery planning logic
- [ ] Add memory management
- [ ] Implement constraints
- [ ] Create unit tests
- [ ] Parallel testing with Pydantic AI version

**Deliverables**:
- DiscoveryAgent fully migrated
- Tests passing
- Performance benchmarks

#### Week 4: ValidationAgent Migration
- [ ] Create BeeAI ValidationAgent
- [ ] Implement validation planning logic
- [ ] Add memory management
- [ ] Implement constraints
- [ ] Create unit tests
- [ ] Parallel testing with Pydantic AI version

**Deliverables**:
- ValidationAgent fully migrated
- Tests passing
- Performance benchmarks

#### Week 5: EvaluationAgent Migration
- [ ] Create BeeAI EvaluationAgent
- [ ] Implement evaluation logic
- [ ] Add memory management
- [ ] Implement constraints
- [ ] Create unit tests
- [ ] Parallel testing with Pydantic AI version

**Deliverables**:
- EvaluationAgent fully migrated
- Tests passing
- Performance benchmarks

### Phase 3: Integration (2 weeks)

**Goal**: Replace orchestrator and integrate all components

#### Week 6: Orchestrator Migration
- [ ] Create BeeAI workflow orchestrator
- [ ] Implement workflow decorators
- [ ] Add parallel execution support
- [ ] Implement error handling
- [ ] Create integration tests

**Deliverables**:
- Orchestrator fully migrated
- Workflow tests passing
- End-to-end tests created

#### Week 7: System Integration
- [ ] Integrate all agents with orchestrator
- [ ] Test complete workflow
- [ ] Add observability (OpenTelemetry)
- [ ] Performance optimization
- [ ] Documentation updates

**Deliverables**:
- Complete system integrated
- All tests passing
- Observability dashboard

### Phase 4: Testing & Optimization (2 weeks)

**Goal**: Comprehensive testing and performance optimization

#### Week 8: Testing
- [ ] Comprehensive integration testing
- [ ] Load testing
- [ ] Error scenario testing
- [ ] Regression testing
- [ ] User acceptance testing

**Deliverables**:
- Test suite complete
- All tests passing
- Test coverage > 80%

#### Week 9: Optimization & Deployment
- [ ] Performance optimization
- [ ] Caching implementation
- [ ] Memory optimization
- [ ] Production deployment preparation
- [ ] Final documentation

**Deliverables**:
- System optimized
- Production-ready
- Complete documentation

### Migration Checklist

#### Pre-Migration
- [ ] Backup current codebase
- [ ] Document current behavior
- [ ] Create test baseline
- [ ] Set up parallel environment

#### During Migration
- [ ] Maintain backward compatibility
- [ ] Run parallel systems
- [ ] Compare outputs
- [ ] Monitor performance

#### Post-Migration
- [ ] Validate all functionality
- [ ] Performance benchmarking
- [ ] Update documentation
- [ ] Train team on BeeAI


AI

---

## Code Examples

### Example 1: DiscoveryAgent with BeeAI

```python
# File: agents/beeai_discovery_agent.py

from bee_agent_framework import BeeAgent
from bee_agent_framework.tools import MCPTool, Tool
from pydantic import BaseModel, Field
from typing import List, Optional

class DiscoveryPlan(BaseModel):
    """Discovery plan structure."""
    scan_ports: bool = Field(default=True)
    scan_processes: bool = Field(default=True)
    detect_applications: bool = Field(default=True)
    reasoning: str = Field(...)

class BeeAIDiscoveryAgent:
    """BeeAI-powered discovery agent."""
    
    SYSTEM_PROMPT = """You are a workload discovery expert. Your role is to:
1. Analyze the resource information provided
2. Create an optimal discovery plan
3. Execute discovery using available MCP tools
4. Return comprehensive workload discovery results

You have access to these discovery capabilities:
- Port scanning: Identify open ports and services
- Process scanning: Analyze running processes
- Application detection: Identify applications based on ports and processes

Consider the resource type and available information to create an efficient 
discovery plan. Be thorough but efficient - only scan what's necessary."""
    
    def __init__(self, llm_config, mcp_server_path):
        """Initialize BeeAI discovery agent."""
        
        # Load MCP tools
        self.mcp_tools = MCPTool.from_server(
            server_path=mcp_server_path,
            server_args=["--mode", "stdio"]
        )
        
        # Create BeeAI agent
        self.agent = BeeAgent(
            llm=llm_config,
            tools=self.mcp_tools,
            system_prompt=self.SYSTEM_PROMPT,
            memory_enabled=True,
            constraints={
                "must_scan_ports": True,
                "min_confidence": 0.6,
                "max_scan_time": 60
            }
        )
    
    async def discover(self, resource_info) -> dict:
        """Execute discovery workflow."""
        
        # Create discovery request
        request = f"""Discover workloads on resource:
- Host: {resource_info.host}
- Type: {resource_info.resource_type}
- SSH User: {resource_info.ssh_user}

Create a discovery plan and execute it using available tools."""
        
        # Run agent
        result = await self.agent.run(request)
        
        # Parse structured output
        discovery_plan = DiscoveryPlan.model_validate(result.output)
        
        return {
            "plan": discovery_plan,
            "results": result.tool_outputs,
            "reasoning": discovery_plan.reasoning
        }
```

### Example 2: ValidationAgent with BeeAI

```python
# File: agents/beeai_validation_agent.py

from bee_agent_framework import BeeAgent
from bee_agent_framework.tools import Tool
from pydantic import BaseModel, Field
from typing import List

class ValidationCheck(BaseModel):
    """Individual validation check."""
    check_id: str
    check_name: str
    check_type: str
    priority: int = Field(ge=1, le=5)
    mcp_tool: str
    tool_args: dict
    expected_result: str
    failure_impact: str

class ValidationPlan(BaseModel):
    """Complete validation plan."""
    strategy_name: str
    checks: List[ValidationCheck]
    estimated_duration_seconds: int
    reasoning: str

class ApplicationClassifierTool(Tool):
    """Custom tool for application classification."""
    
    name = "application_classifier"
    description = "Classify resource based on discovered applications"
    
    def __init__(self, classifier):
        super().__init__()
        self.classifier = classifier
    
    async def run(self, applications: List[dict]) -> dict:
        """Execute classification."""
        return self.classifier.classify(applications)

class BeeAIValidationAgent:
    """BeeAI-powered validation agent."""
    
    SYSTEM_PROMPT = """You are a validation planning expert. Your role is to:
1. Analyze the resource classification and discovered applications
2. Create a comprehensive validation plan with appropriate checks
3. Prioritize checks based on criticality and resource type
4. Select the right MCP tools for each validation

Create validation plans that are:
- Comprehensive: Cover all critical aspects
- Prioritized: Most important checks first (1=highest, 5=lowest)
- Efficient: Avoid redundant checks
- Actionable: Clear expected results and failure impacts"""
    
    def __init__(self, llm_config, mcp_tools, classifier):
        """Initialize BeeAI validation agent."""
        
        # Create custom classifier tool
        classifier_tool = ApplicationClassifierTool(classifier)
        
        # Create BeeAI agent
        self.agent = BeeAgent(
            llm=llm_config,
            tools=[*mcp_tools, classifier_tool],
            system_prompt=self.SYSTEM_PROMPT,
            memory_enabled=True,
            constraints={
                "min_checks": 3,
                "priority_range": (1, 5),
                "must_include_network_check": True
            }
        )
    
    async def create_plan(
        self, 
        resource_info, 
        classification
    ) -> ValidationPlan:
        """Create validation plan."""
        
        request = f"""Create a validation plan for:
- Resource Type: {resource_info.resource_type}
- Host: {resource_info.host}
- Classification: {classification.category}
- Primary Apps: {classification.primary_applications}
- Secondary Apps: {classification.secondary_applications}

Select appropriate MCP tools and prioritize checks."""
        
        # Run agent
        result = await self.agent.run(request)
        
        # Parse structured output
        plan = ValidationPlan.model_validate(result.output)
        
        return plan
```

### Example 3: Orchestrator with BeeAI Workflow

```python
# File: agents/beeai_orchestrator.py

from bee_agent_framework import BeeAgent, Workflow
from bee_agent_framework.decorators import retry, fallback, timeout
from bee_agent_framework.observability import trace
import asyncio

class BeeAIOrchestrator:
    """BeeAI-powered workflow orchestrator."""
    
    def __init__(
        self,
        discovery_agent,
        validation_agent,
        evaluation_agent,
        execution_agent
    ):
        """Initialize orchestrator with BeeAI agents."""
        self.discovery_agent = discovery_agent
        self.validation_agent = validation_agent
        self.evaluation_agent = evaluation_agent
        self.execution_agent = execution_agent
    
    @trace(name="validation_workflow")
    async def execute_workflow(self, request):
        """Execute complete validation workflow with BeeAI."""
        
        workflow_memory = []
        
        # Phase 1: Discovery (optional)
        discovery_result = None
        if request.auto_discover:
            discovery_result = await self._execute_discovery(
                request.resource_info,
                workflow_memory
            )
        
        # Phase 2: Classification
        classification = await self._classify_resource(
            discovery_result,
            workflow_memory
        )
        
        # Phase 3: Validation Planning
        validation_plan = await self._create_validation_plan(
            request.resource_info,
            classification,
            workflow_memory
        )
        
        # Phase 4: Parallel Execution
        validation_results = await self._execute_validations(
            validation_plan,
            workflow_memory
        )
        
        # Phase 5: Evaluation (optional)
        evaluation = None
        if request.enable_ai_evaluation:
            evaluation = await self._evaluate_results(
                validation_results,
                workflow_memory
            )
        
        return {
            "discovery": discovery_result,
            "classification": classification,
            "plan": validation_plan,
            "results": validation_results,
            "evaluation": evaluation,
            "memory": workflow_memory
        }
    
    @retry(max_attempts=2, backoff="exponential")
    @timeout(seconds=60)
    async def _execute_discovery(self, resource_info, memory):
        """Execute discovery phase with retry."""
        result = await self.discovery_agent.discover(resource_info)
        memory.append({
            "phase": "discovery",
            "result": result
        })
        return result
    
    @fallback(fallback_fn=lambda: {"category": "UNKNOWN"})
    async def _classify_resource(self, discovery_result, memory):
        """Classify resource with fallback."""
        if not discovery_result:
            return {"category": "UNKNOWN"}
        
        classification = await self.validation_agent.agent.run_tool(
            "application_classifier",
            {"applications": discovery_result.get("applications", [])}
        )
        
        memory.append({
            "phase": "classification",
            "result": classification
        })
        return classification
    
    @retry(max_attempts=2)
    async def _create_validation_plan(
        self, 
        resource_info, 
        classification, 
        memory
    ):
        """Create validation plan with retry."""
        plan = await self.validation_agent.create_plan(
            resource_info,
            classification
        )
        memory.append({
            "phase": "planning",
            "result": plan
        })
        return plan
    
    async def _execute_validations(self, plan, memory):
        """Execute validations with parallel support."""
        
        # Group checks by priority
        priority_groups = {}
        for check in plan.checks:
            if check.priority not in priority_groups:
                priority_groups[check.priority] = []
            priority_groups[check.priority].append(check)
        
        # Execute by priority (parallel within priority)
        all_results = []
        for priority in sorted(priority_groups.keys()):
            checks = priority_groups[priority]
            
            # Execute checks in parallel
            tasks = [
                self._execute_single_check(check)
                for check in checks
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(results)
        
        memory.append({
            "phase": "execution",
            "result": all_results
        })
        return all_results
    
    @retry(max_attempts=2)
    @timeout(seconds=30)
    async def _execute_single_check(self, check):
        """Execute single validation check."""
        return await self.execution_agent.execute_check(check)
    
    @fallback(fallback_fn=lambda results: {
        "health": "unknown",
        "summary": "Evaluation unavailable"
    })
    async def _evaluate_results(self, results, memory):
        """Evaluate results with fallback."""
        evaluation = await self.evaluation_agent.evaluate(results)
        memory.append({
            "phase": "evaluation",
            "result": evaluation
        })
        return evaluation
```

### Example 4: MCP Tool Integration

```python
# File: tools/mcp_integration.py

from bee_agent_framework.tools import MCPTool

class MCPToolManager:
    """Manage MCP tools for BeeAI agents."""
    
    def __init__(self, mcp_server_path, mcp_server_args):
        """Initialize MCP tool manager."""
        self.server_path = mcp_server_path
        self.server_args = mcp_server_args
        self.tools = None
    
    async def initialize(self):
        """Initialize and discover MCP tools."""
        
        # Automatic tool discovery
        self.tools = MCPTool.from_server(
            server_path=self.server_path,
            server_args=self.server_args
        )
        
        # Categorize tools
        self.network_tools = [
            t for t in self.tools 
            if t.name.startswith("tcp_")
        ]
        
        self.vm_tools = [
            t for t in self.tools 
            if t.name.startswith("vm_")
        ]
        
        self.db_tools = [
            t for t in self.tools 
            if t.name.startswith("db_")
        ]
        
        self.discovery_tools = [
            t for t in self.tools 
            if t.name.startswith("workload_")
        ]
        
        return self.tools
    
    def get_tools_for_agent(self, agent_type: str):
        """Get relevant tools for specific agent type."""
        
        if agent_type == "discovery":
            return self.discovery_tools
        elif agent_type == "validation":
            return self.tools  # All tools
        elif agent_type == "execution":
            return self.tools  # All tools
        else:
            return []
```

---

## Performance Considerations

### Current Performance Baseline

Based on the existing implementation:

| Phase | Current Time | Target Time (BeeAI) | Improvement |
|-------|--------------|---------------------|-------------|
| Discovery | 30-60s | 20-40s | 33% faster (caching) |
| Planning | 2-5s | 1-3s | 40% faster (caching) |
| Execution | 15-30s | 10-20s | 33% faster (parallel) |
| Evaluation | 5-10s | 3-7s | 30% faster (caching) |
| **Total** | **52-105s** | **34-70s** | **35% faster** |

### Performance Optimization Strategies

#### 1. **LLM Response Caching**

```python
# BeeAI built-in caching
agent = BeeAgent(
    llm=llm_config,
    tools=tools,
    cache_config={
        "enabled": True,
        "ttl": 3600,  # 1 hour
        "max_size": 1000,
        "strategy": "lru"
    }
)

# Cache similar requests
# Request 1: "Create plan for VM with MySQL"
# Request 2: "Create plan for VM with MySQL" → Cache hit!
```

**Expected Impact**: 40-50% reduction in LLM calls for similar resources

#### 2. **Parallel Execution**

```python
# Current: Sequential execution
for check in validation_plan.checks:
    result = await execute_check(check)  # 5s each
# Total: 5 checks × 5s = 25s

# BeeAI: Parallel execution
tasks = [execute_check(check) for check in validation_plan.checks]
results = await asyncio.gather(*tasks)
# Total: max(5s) = 5s (5x faster!)
```

**Expected Impact**: 3-5x faster for independent checks

#### 3. **Memory Optimization**

```python
# BeeAI memory management
agent = BeeAgent(
    llm=llm_config,
    memory_config={
        "max_messages": 50,  # Limit history
        "compression": True,  # Compress old messages
        "summarization": True  # Summarize long conversations
    }
)
```

**Expected Impact**: 50% reduction in memory usage

#### 4. **Tool Call Optimization**

```python
# Batch tool calls when possible
results = await agent.run_tools_batch([
    ("workload_scan_ports", {"host": "192.168.1.100"}),
    ("workload_scan_processes", {"host": "192.168.1.100"}),
    ("workload_detect_applications", {"host": "192.168.1.100"})
])
```

**Expected Impact**: 30% reduction in tool execution time

### Performance Monitoring

```python
# OpenTelemetry integration
from bee_agent_framework.observability import setup_telemetry

setup_telemetry(
    service_name="cyberres-validation",
    endpoint="http://localhost:4318",
    metrics_enabled=True,
    traces_enabled=True
)

# Automatic metrics collection:
# - Agent execution time
# - Tool call duration
# - LLM response time
# - Cache hit rate
# - Memory usage
```

### Scalability Considerations

#### Horizontal Scaling

```python
# Multiple orchestrator instances
orchestrators = [
    BeeAIOrchestrator(...) for _ in range(num_workers)
]

# Load balancing
async def process_requests(requests):
    tasks = []
    for i, request in enumerate(requests):
        orchestrator = orchestrators[i % len(orchestrators)]
        tasks.append(orchestrator.execute_workflow(request))
    
    return await asyncio.gather(*tasks)
```

#### Resource Limits

```python
# Configure resource limits
agent = BeeAgent(
    llm=llm_config,
    resource_limits={
        "max_concurrent_tools": 5,
        "max_memory_mb": 512,
        "max_execution_time": 300
    }
)
```

---

## Risk Assessment

### Migration Risks and Mitigation

| Risk | Severity | Probability | Mitigation Strategy |
|------|----------|-------------|---------------------|
| **Breaking Changes** | High | Medium | Parallel operation, comprehensive testing |
| **Performance Regression** | Medium | Low | Benchmarking, optimization phase |
| **Learning Curve** | Medium | High | Training, documentation, gradual adoption |
| **Tool Compatibility** | High | Low | BeeAI native MCP support, early testing |
| **Data Loss** | High | Low | Backup, version control, rollback plan |
| **Timeline Overrun** | Medium | Medium | Phased approach, buffer time |
| **LLM Provider Issues** | Medium | Low | Multi-provider support maintained |
| **Memory Leaks** | Medium | Low | Monitoring, testing, BeeAI memory management |

### Rollback Strategy

```python
# Feature flag for gradual rollout
USE_BEEAI = os.getenv("USE_BEEAI_AGENTS", "false").lower() == "true"

if USE_BEEAI:
    from agents.beeai_orchestrator import BeeAIOrchestrator
    orchestrator = BeeAIOrchestrator(...)
else:
    from agents.orchestrator import ValidationOrchestrator
    orchestrator = ValidationOrchestrator(...)

# Easy rollback by changing environment variable
```

### Success Criteria

1. ✅ **Functional Parity**: All existing features work identically
2. ✅ **Performance**: 30%+ improvement in execution time
3. ✅ **Reliability**: 99.9% success rate maintained
4. ✅ **Test Coverage**: 80%+ code coverage
5. ✅ **Documentation**: Complete migration guide
6. ✅ **Team Adoption**: All team members trained

---

## Conclusion

### Summary

This migration plan provides a comprehensive roadmap for transitioning the CyberRes Recovery Validation Agent from Pydantic AI to the IBM Bee Agent Framework. The migration will:

1. **Enhance Production Readiness**: Built-in caching, memory optimization, and observability
2. **Improve Performance**: 35% faster execution through parallelism and caching
3. **Simplify Architecture**: Declarative orchestration and native MCP support
4. **Increase Reliability**: Built-in retry logic, circuit breakers, and error handling
5. **Enable Scalability**: Better resource management and horizontal scaling support

### Key Takeaways

- **Phased Approach**: 9-week migration with incremental testing
- **Minimal Disruption**: Parallel operation during transition
- **Backward Compatible**: Existing MCP tools work without changes
- **Enhanced Capabilities**: Memory, constraints, and observability
- **Production Ready**: Enterprise-grade features from day one

### Next Steps

1. **Review and Approve**: Stakeholder review of migration plan
2. **Resource Allocation**: Assign team members to migration phases
3. **Environment Setup**: Prepare development and testing environments
4. **Phase 1 Kickoff**: Begin foundation setup (Week 1)
5. **Regular Check-ins**: Weekly progress reviews and adjustments

### References

- **BeeAI Framework**: https://github.com/i-am-bee/bee-agent-framework
- **BeeAI Documentation**: https://framework.beeai.dev
- **Current Implementation**: [`python/src/AGENTIC_WORKFLOW_COMPREHENSIVE_DOCUMENTATION.md`](python/src/AGENTIC_WORKFLOW_COMPREHENSIVE_DOCUMENTATION.md)
- **MCP Specification**: https://modelcontextprotocol.io

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-25  
**Author**: IBM Bob (Plan Mode)  
**Status**: Ready for Review
