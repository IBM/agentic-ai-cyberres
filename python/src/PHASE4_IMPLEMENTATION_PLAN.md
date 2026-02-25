# Phase 4: Implementation Plan - Post Phase 3 Review

## Executive Summary

After implementing Phase 3 (MCP Best Practices with dynamic tool discovery), this document reviews the current state and provides a detailed plan for completing the implementation to achieve a fully functional MCP-centric agentic workflow.

---

## Current State Analysis

### ✅ What's Working

#### 1. MCP Client with Dynamic Tool Discovery (Phase 3)
- File: `mcp_stdio_client.py`
- Status: Complete
- Capabilities: Connects to MCP server, discovers tools dynamically, provides query methods

#### 2. Agent Framework (Phase 1 & 2)
- Files: `agents/base.py`, `tool_coordinator.py`, `state_manager.py`, `feature_flags.py`
- Status: Complete
- Capabilities: Base classes, tool coordination, state management, feature flags

#### 3. AI-Powered Agents (Phase 2)
- Files: Enhanced discovery, classification, and reporting agents
- Status: Complete

#### 4. MCP Server
- Location: `python/cyberres-mcp/`
- Status: Working with 15+ tools available

### ❌ What Needs Fixing

#### 1. Import Error in recovery_validation_agent.py
- Issue: Line 19 tries to import `mcp_client_context` which doesn't exist
- Impact: main.py cannot run

#### 2. Orchestrator Not Using Dynamic Tool Discovery
- File: `agents/orchestrator.py`
- Issue: Doesn't use `mcp_client.get_available_tools()`

#### 3. Conversation Handler Asks for Too Much Info
- File: `conversation.py`
- Issue: Asks for service names, ports, etc.
- Should: Only ask for hostname + SSH credentials

---

## Phase 4: Implementation Plan

### Goal
Create a fully functional MCP-centric agentic workflow where user provides only hostname + SSH credentials, and agent discovers everything automatically using MCP tools.

### Architecture Flow

```
User Input (hostname + SSH creds) → main.py → RecoveryValidationAgent
→ Connect to MCP (with tool discovery) → Call discover_applications
→ AI Classification → Select Validation Tools → Execute Validations
→ AI Evaluation → Generate Report → Present to User
```

---

## Phase 4 Tasks

### Task 1: Fix Import Error (CRITICAL)

File: `recovery_validation_agent.py`

Change line 19 from:
```python
from mcp_client import mcp_client_context, MCPClientError
```

To:
```python
from mcp_stdio_client import MCPStdioClient, MCPClientError
```

### Task 2: Update RecoveryValidationAgent

Initialize MCPStdioClient and use dynamic tool discovery.

### Task 3: Simplify Conversation Handler

Only ask for hostname, SSH username, SSH password. Let MCP tools discover everything else.

### Task 4: Update Orchestrator

Add dynamic tool discovery and selection logic.

### Task 5: Update Discovery Agent

Use MCP discover_applications tool directly.

### Task 6: Add Tool Selection Logic

Select validation tools based on classification and available tools.

### Task 7: Update Models

Ensure SSH password field exists in resource models.

### Task 8: Create Integration Test

Test complete end-to-end workflow.

---

## Implementation Order

### Priority 1: Critical Fixes (Required to Run)
1. Task 1: Fix import error
2. Task 2: Update RecoveryValidationAgent
3. Task 3: Simplify conversation handler

### Priority 2: Core Functionality
4. Task 4: Update orchestrator
5. Task 5: Update discovery agent
6. Task 6: Add tool selection logic

### Priority 3: Polish & Testing
7. Task 7: Update models
8. Task 8: Create integration test

---

## Expected User Experience After Phase 4

```
$ python main.py

Agent: What server would you like to validate?
You: db-server-01

Agent: SSH Username?
You: admin

Agent: SSH Password?
You: ********

Agent: Starting validation...
[Automatically discovers, classifies, validates, and reports]

Validation complete! Score: 92/100
```

---

## Files to Modify

### Critical (Priority 1)
1. recovery_validation_agent.py
2. conversation.py

### Core (Priority 2)
3. agents/orchestrator.py
4. agents/discovery_agent.py
5. models.py

### Testing (Priority 3)
6. test_complete_workflow.py (new)

---

## Success Criteria

Phase 4 Complete When:
- main.py runs without errors
- User only provides hostname + SSH credentials
- Agent discovers MCP tools dynamically
- Agent uses MCP discover_applications tool
- Agent classifies and validates automatically
- Complete workflow test passes

---

## Estimated Effort

- Priority 1 (Critical): 2-3 hours
- Priority 2 (Core): 3-4 hours
- Priority 3 (Testing): 1-2 hours
- Total: 6-9 hours

---

## Summary

Current State: Phase 3 complete (dynamic tool discovery)
Phase 4 Goal: Complete MCP-centric workflow
Key Changes: Fix imports, use MCPStdioClient, simplify user input, use MCP tools
Outcome: Fully functional agentic workflow following MCP best practices

Ready to proceed with Phase 4 implementation!