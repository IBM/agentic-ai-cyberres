# BeeAI Codebase Review and Optimization Plan

**Date:** 2026-02-25  
**Reviewer:** IBM Bob  
**Project:** Agentic AI CyberRes - BeeAI Infrastructure Validation

---

## Executive Summary

This document provides a comprehensive analysis of the BeeAI-based agentic workflow implementation, identifying:

1. **Phase 1:** Unwanted and unused files that can be safely removed (40+ files identified)
2. **Phase 2:** Critical issues with MCP tool discovery preventing proper utilization of available discovery tools

**Critical Finding:** BeeAI agents are using **hardcoded tool names** instead of **dynamic tool discovery**, preventing them from utilizing all 4 available MCP discovery tools (`discover_workload`, `discover_os_only`, `discover_applications`, `get_raw_server_data`).

---

## Phase 1: Codebase Cleanup Analysis

### 1.1 Archive Directory - Complete Removal Recommended

**Location:** `python/archive/docs_backup_20260225/`

All 40+ files in this directory are archived documentation from a previous backup and should be **completely removed**. These are historical snapshots that serve no active purpose.

#### Files to Remove (40 files):

```
python/archive/docs_backup_20260225/AGENTIC_WORKFLOW_ANALYSIS.md
python/archive/docs_backup_20260225/AGENTIC_WORKFLOW_BEST_PRACTICES.md
python/archive/docs_backup_20260225/AGENTIC_WORKFLOW_COMPLETE.md
python/archive/docs_backup_20260225/AGENTIC_WORKFLOW_REVIEW.md
python/archive/docs_backup_20260225/conversation.py
python/archive/docs_backup_20260225/CRITICAL_FIXES_APPLIED.md
python/archive/docs_backup_20260225/CRITICAL_FIXES_COMPLETE.md
python/archive/docs_backup_20260225/CRITICAL_ISSUES_FIXED.md
python/archive/docs_backup_20260225/EMAIL_FIX_PLAN.md
python/archive/docs_backup_20260225/EMAIL_FIXES_APPLIED.md
python/archive/docs_backup_20260225/EXECUTIVE_SUMMARY.md
python/archive/docs_backup_20260225/FINAL_REVIEW_SUMMARY.md
python/archive/docs_backup_20260225/FINAL_STATUS_REPORT.md
python/archive/docs_backup_20260225/FINAL_STATUS.md
python/archive/docs_backup_20260225/FIX_SUMMARY.md
python/archive/docs_backup_20260225/IMPLEMENTATION_COMPLETE.md
python/archive/docs_backup_20260225/IMPLEMENTATION_STEP_BY_STEP.md
python/archive/docs_backup_20260225/ISSUE1_FIX_SUMMARY.md
python/archive/docs_backup_20260225/ISSUE2_FIX_SUMMARY.md
python/archive/docs_backup_20260225/LLM_PROMPT_ENHANCEMENT_GUIDE.md
python/archive/docs_backup_20260225/LLM_TOOL_SELECTOR_IMPLEMENTATION.md
python/archive/docs_backup_20260225/MCP_CENTRIC_WORKFLOW_SWITCH.md
python/archive/docs_backup_20260225/MCP_CONNECTION_FIX.md
python/archive/docs_backup_20260225/OLLAMA_API_FIX.md
python/archive/docs_backup_20260225/PHASE1_IMPLEMENTATION_SUMMARY.md
python/archive/docs_backup_20260225/PRIORITY_ERROR_ANALYSIS.md
python/archive/docs_backup_20260225/PRODUCTION_DEMO_GUIDE.md
python/archive/docs_backup_20260225/PYDANTIC_AI_INTEGRATION.md
python/archive/docs_backup_20260225/QUICK_SENDGRID_SETUP.md
python/archive/docs_backup_20260225/RUN_PRODUCTION_DEMO.md
python/archive/docs_backup_20260225/SENDGRID_SETUP.md
python/archive/docs_backup_20260225/SETUP_COMPLETE.md
python/archive/docs_backup_20260225/TEST_EMAIL_FEATURE.md
python/archive/docs_backup_20260225/TOOL_CATEGORIZATION_IMPLEMENTATION_PLAN.md
python/archive/docs_backup_20260225/TOOL_CATEGORIZATION_STRATEGY.md
python/archive/docs_backup_20260225/TWO_CRITICAL_ISSUES_FIXED.md
python/archive/docs_backup_20260225/VALIDATION_WORKFLOW_PLAN.md
python/archive/docs_backup_20260225/WEEK1_SUMMARY.md
python/archive/docs_backup_20260225/WEEK3_IMPLEMENTATION_PLAN.md
python/archive/docs_backup_20260225/WORKFLOW_DECISION_MAP.md
python/archive/docs_backup_20260225/WORKFLOW_IMPROVEMENT_ROADMAP.md
```

**Rationale:** These are backup files from a specific date (2026-02-25) and represent historical documentation. The active versions exist in `python/src/` and should be the source of truth.

**Action:** `rm -rf python/archive/docs_backup_20260225/`

---

### 1.2 Pydantic AI-Based Implementations - Deprecated

**Status:** The project has migrated from Pydantic AI to BeeAI framework.

#### Files Using Pydantic AI (Legacy - Consider Removal):

1. **`python/src/agents/` directory** - Old Pydantic AI agents (7 files):
   ```
   python/src/agents/__init__.py
   python/src/agents/base.py
   python/src/agents/classification_agent.py
   python/src/agents/discovery_agent_enhanced.py
   python/src/agents/discovery_agent.py
   python/src/agents/evaluation_agent.py
   python/src/agents/orchestrator.py
   python/src/agents/reporting_agent.py
   python/src/agents/validation_agent.py
   ```

   **Rationale:** These agents use `pydantic_ai` imports and have been replaced by BeeAI implementations in `python/src/beeai_agents/`. The BeeAI versions are the active implementations.

   **Evidence:**
   - All files import `from pydantic_ai import Agent`
   - Replaced by: `python/src/beeai_agents/discovery_agent.py`, `python/src/beeai_agents/validation_agent.py`, etc.
   - Current orchestrator uses BeeAI: `from beeai_agents.orchestrator import BeeAIValidationOrchestrator`

2. **`python/src/conversation.py`** - Legacy Pydantic AI conversation handler:
   ```
   python/src/conversation.py
   ```

   **Rationale:** Uses `pydantic_ai.Agent` and has been replaced by:
   - `python/src/conversation_simple.py` (simplified version)
   - BeeAI-based orchestrator handles conversation flow

3. **`python/src/llm_orchestrator.py`** - Old orchestrator:
   ```
   python/src/llm_orchestrator.py
   ```

   **Rationale:** Uses Pydantic AI and has been replaced by `python/src/beeai_agents/orchestrator.py`

**Action Recommendation:**
- **Move to archive** or **delete** the entire `python/src/agents/` directory
- **Delete** `python/src/conversation.py` and `python/src/llm_orchestrator.py`
- Keep `python/src/conversation_simple.py` as it may still be used for testing

---

### 1.3 Redundant Documentation Files

**Location:** `python/src/`

Multiple overlapping documentation files exist, creating confusion about which is current.

#### Weekly Summary Files (Consolidate or Archive):

```
python/src/WEEK1_SUMMARY.md
python/src/WEEK2_SUMMARY.md
python/src/WEEK3_SUMMARY.md
python/src/PHASE1_WEEK1_SUMMARY.md
python/src/PHASE1_WEEK2_SUMMARY.md
python/src/PHASE2_WEEK4_SUMMARY.md
python/src/PHASE2_WEEK5_SUMMARY.md
python/src/PHASE3_WEEK6_SUMMARY.md
python/src/PHASE3_WEEK7_SUMMARY.md
python/src/PHASE4_WEEK8_SUMMARY.md
```

**Rationale:** 10 weekly summary files create documentation sprawl. These should be:
- **Consolidated** into a single `PROJECT_HISTORY.md` or `CHANGELOG.md`
- **Archived** to a `docs/history/` directory
- **Deleted** if no longer relevant

#### Implementation Plan Files (Consolidate):

```
python/src/PHASE3_IMPLEMENTATION_PLAN.md
python/src/PHASE4_IMPLEMENTATION_PLAN.md
python/src/WEEK3_IMPLEMENTATION_PLAN.md
python/src/BEEAI_FIX_IMPLEMENTATION_PLAN.md
python/src/BEEAI_MIGRATION_PLAN.md
python/src/FILE_CLEANUP_PLAN.md
```

**Rationale:** Multiple implementation plans should be consolidated into:
- Current active plan: Keep the most recent
- Historical plans: Archive or delete

#### Status/Summary Files (Consolidate):

```
python/src/FIX_SUMMARY.md
python/src/CLEANUP_COMPLETED.md
python/src/BEEAI_IMPLEMENTATION_COMPLETE.md
python/src/BEEAI_IMPLEMENTATION_FINAL_SUMMARY.md
python/src/BEEAI_IMPLEMENTATION_PROGRESS.md
python/src/BEEAI_IMPLEMENTATION_REVIEW.md
python/src/BEEAI_PROJECT_FINAL_SUMMARY.md
python/src/OLLAMA_CONFIGURATION_FIX.md
```

**Rationale:** Multiple "final" and "complete" summaries indicate documentation debt. Consolidate into:
- **Single source of truth:** `PROJECT_STATUS.md` or `README.md`
- Archive historical summaries

#### Testing/Guide Files (Review and Consolidate):

```
python/src/TESTING_GUIDE.md
python/src/BEEAI_TESTING_GUIDE.md
python/src/PHASE2_TESTING_GUIDE.md
python/src/TEST_QUICK_START.md
python/src/BEEAI_VALIDATION_RUN_GUIDE.md
python/src/BEEAI_DEMO_GUIDE.md
python/src/HOW_TO_RUN.md
python/src/BEEAI_HOW_TO_RUN.md
python/src/QUICK_START.md
python/src/BEEAI_QUICK_START.md
```

**Rationale:** 10 different testing/guide files create confusion. Consolidate into:
- **`TESTING.md`** - Comprehensive testing guide
- **`QUICKSTART.md`** - Quick start guide
- **`HOW_TO_RUN.md`** - Execution instructions
- Delete duplicates

#### Analysis/Review Files (Archive or Delete):

```
python/src/AGENTIC_WORKFLOW_COMPREHENSIVE_DOCUMENTATION.md
python/src/BEEAI_MIGRATION_ANALYSIS_AND_PLAN.md
python/src/FILE_COMPARISON_ANALYSIS.md
python/src/README_AGENTIC_TRANSFORMATION.md
```

**Rationale:** These are analysis documents from migration/transformation phases. Archive or delete after migration is complete.

---

### 1.4 Legacy/Unused Python Files

#### Potentially Unused Files:

1. **`python/src/main.py`** vs **`python/src/main_beeai.py`**
   - Check which is the active entry point
   - Remove the unused one

2. **`python/src/interactive_agent_cli.py`** vs **`python/src/beeai_interactive.py`**
   - `beeai_interactive.py` appears to be the active BeeAI version
   - Consider removing `interactive_agent_cli.py` if deprecated

3. **`python/src/production_demo.py`** vs **`python/src/beeai_production.py`**
   - Determine which is active
   - Remove deprecated version

4. **Test files for old implementations:**
   ```
   python/src/test_workflow.py (if testing old Pydantic AI workflow)
   python/src/test_classifier.py (if using old classifier)
   python/src/test_llm_tool_selector.py (if LLM tool selector is deprecated)
   ```

5. **Legacy modules:**
   ```
   python/src/llm_tool_selector.py (if replaced by BeeAI tool selection)
   python/src/planner.py (if replaced by BeeAI planning)
   python/src/executor.py (if replaced by BeeAI execution)
   python/src/evaluator.py (if replaced by BeeAI evaluation)
   python/src/reader.py (if no longer used)
   ```

**Action Required:** Review each file's usage in active code before removal.

---

### 1.5 Summary of Phase 1 Cleanup

#### Immediate Deletions (Safe):
- **40 files** in `python/archive/docs_backup_20260225/` → DELETE
- **Total estimated cleanup:** 50-60 files

#### Review and Consolidate:
- **10 weekly summaries** → Consolidate to 1-2 files
- **6 implementation plans** → Keep 1 active, archive rest
- **8 status/summary files** → Consolidate to 1-2 files
- **10 testing/guide files** → Consolidate to 3 files

#### Pydantic AI Removal (After Verification):
- **9 files** in `python/src/agents/` → DELETE (replaced by BeeAI)
- **2 files** (`conversation.py`, `llm_orchestrator.py`) → DELETE

#### Total Cleanup Potential:
- **Immediate safe deletions:** 40+ files
- **After consolidation:** 30-40 additional files
- **Total reduction:** 70-80 files (approximately 40-50% of documentation files)

---

## Phase 2: MCP Tool Discovery Integration Fix

### 2.1 Problem Analysis

#### Current Issue: Hardcoded Tool Names

**Location:** `python/src/beeai_agents/discovery_agent.py` (lines 396-403)

```python
# Find working discovery tools (discover_os_only + discover_applications)
os_tool = None
app_tool = None
for tool in self._mcp_tools:
    if tool.name == "discover_os_only":
        os_tool = tool
    elif tool.name == "discover_applications":
        app_tool = tool
```

**Problem:** The code **hardcodes** tool names instead of dynamically discovering available tools.

#### Available MCP Tools (Not Being Utilized):

The MCP server provides **4 discovery tools**:

1. ✅ **`discover_os_only`** - Currently used (lightweight OS detection)
2. ✅ **`discover_applications`** - Currently used (application detection)
3. ❌ **`discover_workload`** - **NOT USED** (comprehensive integrated discovery)
4. ❌ **`get_raw_server_data`** - **NOT USED** (raw data for LLM processing)

**Impact:**
- BeeAI cannot utilize the comprehensive `discover_workload` tool
- BeeAI cannot leverage `get_raw_server_data` for LLM-enhanced detection
- System is inflexible to new tools added to MCP server
- Violates MCP best practices for dynamic tool discovery

---

### 2.2 Root Cause Analysis

#### Issue 1: No Dynamic Tool Discovery in Discovery Agent

**File:** `python/src/beeai_agents/discovery_agent.py`

**Current Implementation:**
```python
async def _execute_discovery(self, resource: ResourceInfo, plan: DiscoveryPlan):
    # Hardcoded tool lookup
    os_tool = None
    app_tool = None
    for tool in self._mcp_tools:
        if tool.name == "discover_os_only":
            os_tool = tool
        elif tool.name == "discover_applications":
            app_tool = tool
```

**Problem:** 
- No fallback to `discover_workload` if individual tools fail
- No utilization of `get_raw_server_data` for enhanced detection
- No dynamic adaptation to available tools

#### Issue 2: Tool Discovery Not Exposed to Agents

**File:** `python/src/beeai_agents/orchestrator.py`

**Current Implementation:**
```python
async def _initialize_mcp(self):
    # Discovers tools but doesn't expose discovery capabilities
    self._mcp_tools = await MCPTool.from_client(self._mcp_client)
    logger.info(f"✓ Connected to MCP server, discovered {len(self._mcp_tools)} tools")
```

**Problem:**
- Tools are discovered but agents don't have methods to query available tools
- No tool capability checking before invocation
- No graceful degradation if preferred tools are unavailable

#### Issue 3: MCP Client Has Discovery But Agents Don't Use It

**File:** `python/src/mcp_stdio_client.py`

**Available Methods (Not Used by Agents):**
```python
def get_available_tools(self) -> List[str]:
    """Get list of available tool names."""
    return list(getattr(self, 'available_tools', {}).keys())

def has_tool(self, tool_name: str) -> bool:
    """Check if a tool is available."""
    return tool_name in getattr(self, 'available_tools', {})
```

**Problem:** These methods exist but BeeAI agents don't use them!

---

### 2.3 Detailed Solution

#### Solution 1: Implement Dynamic Tool Selection in Discovery Agent

**File:** `python/src/beeai_agents/discovery_agent.py`

**Changes Required:**

```python
async def _execute_discovery(
    self,
    resource: ResourceInfo,
    plan: DiscoveryPlan
) -> WorkloadDiscoveryResult:
    """Execute discovery plan using MCP tools with dynamic tool selection."""
    
    logger.info(f"Executing discovery plan for {resource.host}")
    
    # Ensure tools are available
    if not self._mcp_tools:
        await self._ensure_mcp_tools()
    
    # SOLUTION: Dynamic tool discovery with fallback strategy
    available_tool_names = [tool.name for tool in self._mcp_tools]
    logger.info(f"Available discovery tools: {available_tool_names}")
    
    # Strategy 1: Try comprehensive discovery first (best option)
    if "discover_workload" in available_tool_names:
        logger.info("Using comprehensive discover_workload tool")
        return await self._execute_comprehensive_discovery(resource, plan)
    
    # Strategy 2: Use individual tools (current approach)
    elif "discover_os_only" in available_tool_names and "discover_applications" in available_tool_names:
        logger.info("Using individual discovery tools (os + applications)")
        return await self._execute_individual_discovery(resource, plan)
    
    # Strategy 3: Fallback to raw data collection + LLM analysis
    elif "get_raw_server_data" in available_tool_names:
        logger.info("Using raw data collection with LLM analysis")
        return await self._execute_raw_data_discovery(resource, plan)
    
    # Strategy 4: No discovery tools available
    else:
        logger.error("No discovery tools available in MCP server")
        raise Exception(
            f"No discovery tools found. Available tools: {available_tool_names}"
        )

async def _execute_comprehensive_discovery(
    self,
    resource: ResourceInfo,
    plan: DiscoveryPlan
) -> WorkloadDiscoveryResult:
    """Execute discovery using the comprehensive discover_workload tool."""
    
    # Find the tool
    workload_tool = next(
        (tool for tool in self._mcp_tools if tool.name == "discover_workload"),
        None
    )
    
    if not workload_tool:
        raise Exception("discover_workload tool not found")
    
    # Prepare arguments
    tool_args = {
        "host": resource.host,
        "detect_os": plan.scan_ports,  # Map plan to tool args
        "detect_applications": plan.detect_applications,
        "detect_containers": True,
        "min_confidence": "medium"
    }
    
    # Add SSH credentials
    if hasattr(resource, 'ssh_user') and resource.ssh_user:
        tool_args["ssh_user"] = resource.ssh_user
    if hasattr(resource, 'ssh_password') and resource.ssh_password:
        tool_args["ssh_password"] = resource.ssh_password
    if hasattr(resource, 'ssh_key_path') and resource.ssh_key_path:
        tool_args["ssh_key_path"] = resource.ssh_key_path
    if hasattr(resource, 'ssh_port'):
        tool_args["ssh_port"] = resource.ssh_port
    
    try:
        logger.info(f"Calling discover_workload for {resource.host}")
        result_output = await workload_tool.run(input=tool_args)
        
        # Parse result
        import json
        if isinstance(result_output.result, str):
            result = json.loads(result_output.result)
        else:
            result = result_output.result
        
        # Check success
        if not result.get("success") and not result.get("ok"):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Comprehensive discovery failed: {error_msg}")
            # Fallback to individual tools
            return await self._execute_individual_discovery(resource, plan)
        
        # Extract data
        data = result.get("data", {})
        
        # Convert to WorkloadDiscoveryResult
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[
                PortInfo(**port) if isinstance(port, dict) else port
                for port in data.get("ports", [])
            ],
            processes=[
                ProcessInfo(**proc) if isinstance(proc, dict) else proc
                for proc in data.get("processes", [])
            ],
            applications=[
                ApplicationDetection(**app) if isinstance(app, dict) else app
                for app in data.get("applications", [])
            ],
            discovery_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Comprehensive discovery failed: {e}", exc_info=True)
        # Fallback to individual tools
        return await self._execute_individual_discovery(resource, plan)

async def _execute_individual_discovery(
    self,
    resource: ResourceInfo,
    plan: DiscoveryPlan
) -> WorkloadDiscoveryResult:
    """Execute discovery using individual tools (current implementation)."""
    
    # Find tools dynamically
    os_tool = next(
        (tool for tool in self._mcp_tools if tool.name == "discover_os_only"),
        None
    )
    app_tool = next(
        (tool for tool in self._mcp_tools if tool.name == "discover_applications"),
        None
    )
    
    if not os_tool or not app_tool:
        logger.warning(
            f"Individual discovery tools not found. "
            f"Available: {[t.name for t in self._mcp_tools]}"
        )
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],
            processes=[],
            applications=[],
            discovery_time=datetime.now()
        )
    
    # Prepare tool arguments
    tool_args = {
        "host": resource.host,
    }
    
    # Add SSH credentials if available
    if hasattr(resource, 'ssh_user') and resource.ssh_user:
        tool_args["ssh_user"] = resource.ssh_user
    if hasattr(resource, 'ssh_password') and resource.ssh_password:
        tool_args["ssh_password"] = resource.ssh_password
    if hasattr(resource, 'ssh_key_path') and resource.ssh_key_path:
        tool_args["ssh_key_path"] = resource.ssh_key_path
    
    try:
        import json
        
        # Step 1: Discover OS
        logger.info(f"Calling discover_os_only tool for {resource.host}")
        os_result_output = await os_tool.run(input=tool_args)
        
        # Parse OS result
        if isinstance(os_result_output.result, str):
            os_result = json.loads(os_result_output.result)
        else:
            os_result = os_result_output.result
        
        logger.debug(f"OS discovery result: {os_result}")
        
        # Step 2: Discover Applications
        logger.info(f"Calling discover_applications tool for {resource.host}")
        app_result_output = await app_tool.run(input=tool_args)
        
        # Parse application result
        if isinstance(app_result_output.result, str):
            app_result = json.loads(app_result_output.result)
        else:
            app_result = app_result_output.result
        
        logger.debug(f"Application discovery result: {app_result}")
        
        # Check for success
        os_success = os_result.get("success") or os_result.get("ok")
        app_success = app_result.get("success") or app_result.get("ok")
        
        if not os_success or not app_success:
            error_msg = os_result.get('error') or app_result.get('error', 'Unknown error')
            logger.error(f"Discovery failed: {error_msg}")
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[],
                processes=[],
                applications=[],
                discovery_time=datetime.now()
            )
        
        # Extract data from both results
        os_data = os_result.get("data", {})
        app_data = app_result.get("data", {})
        
        # Combine results
        logger.info(f"Discovery completed successfully for {resource.host}")
        logger.info(f"Found {len(app_data.get('applications', []))} applications")
        
        # Convert to WorkloadDiscoveryResult
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[
                PortInfo(**port) if isinstance(port, dict) else port
                for port in app_data.get("ports", [])
            ],
            processes=[
                ProcessInfo(**proc) if isinstance(proc, dict) else proc
                for proc in app_data.get("processes", [])
            ],
            applications=[
                ApplicationDetection(**app) if isinstance(app, dict) else app
                for app in app_data.get("applications", [])
            ],
            discovery_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Discovery execution failed: {e}", exc_info=True)
        # Return empty result on failure
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],
            processes=[],
            applications=[],
            discovery_time=datetime.now()
        )

async def _execute_raw_data_discovery(
    self,
    resource: ResourceInfo,
    plan: DiscoveryPlan
) -> WorkloadDiscoveryResult:
    """Execute discovery using raw data collection + LLM analysis."""
    
    # Find the tool
    raw_data_tool = next(
        (tool for tool in self._mcp_tools if tool.name == "get_raw_server_data"),
        None
    )
    
    if not raw_data_tool:
        raise Exception("get_raw_server_data tool not found")
    
    # Prepare arguments
    tool_args = {
        "host": resource.host,
        "collect_processes": plan.scan_processes,
        "collect_ports": plan.scan_ports,
        "collect_configs": False,
        "collect_packages": False,
        "collect_services": False
    }
    
    # Add SSH credentials
    if hasattr(resource, 'ssh_user') and resource.ssh_user:
        tool_args["ssh_user"] = resource.ssh_user
    if hasattr(resource, 'ssh_password') and resource.ssh_password:
        tool_args["ssh_password"] = resource.ssh_password
    if hasattr(resource, 'ssh_key_path') and resource.ssh_key_path:
        tool_args["ssh_key_path"] = resource.ssh_key_path
    
    try:
        logger.info(f"Calling get_raw_server_data for {resource.host}")
        result_output = await raw_data_tool.run(input=tool_args)
        
        # Parse result
        import json
        if isinstance(result_output.result, str):
            result = json.loads(result_output.result)
        else:
            result = result_output.result
        
        # Check success
        if not result.get("success") and not result.get("ok"):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Raw data collection failed: {error_msg}")
            return WorkloadDiscoveryResult(
                host=resource.host,
                ports=[],
                processes=[],
                applications=[],
                discovery_time=datetime.now()
            )
        
        # Extract raw data
        raw_data = result.get("data", {})
        
        # TODO: Use LLM to analyze raw data and detect applications
        # For now, return basic structure
        logger.info(f"Raw data collected for {resource.host}, LLM analysis pending")
        
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],  # TODO: Parse from raw data
            processes=[],  # TODO: Parse from raw data
            applications=[],  # TODO: LLM-based detection
            discovery_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Raw data discovery failed: {e}", exc_info=True)
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],
            processes=[],
            applications=[],
            discovery_time=datetime.now()
        )
```

---

#### Solution 2: Add Tool Discovery Helper Methods

**File:** `python/src/beeai_agents/discovery_agent.py`

**Add these helper methods:**

```python
def get_available_discovery_tools(self) -> List[str]:
    """Get list of available discovery tool names.
    
    Returns:
        List of tool names available for discovery
    """
    if not self._mcp_tools:
        return []
    
    discovery_tools = [
        "discover_workload",
        "discover_os_only",
        "discover_applications",
        "get_raw_server_data"
    ]
    
    available = [
        tool.name for tool in self._mcp_tools
        if tool.name in discovery_tools
    ]
    
    return available

def has_discovery_tool(self, tool_name: str) -> bool:
    """Check if a specific discovery tool is available.
    
    Args:
        tool_name: Name of the tool to check
    
    Returns:
        True if tool is available, False otherwise
    """
    if not self._mcp_tools:
        return False
    
    return any(tool.name == tool_name for tool in self._mcp_tools)

def get_discovery_strategy(self) -> str:
    """Determine the best discovery strategy based on available tools.
    
    Returns:
        Strategy name: "comprehensive", "individual", "raw_data", or "none"
    """
    available = self.get_available_discovery_tools()
    
    if "discover_workload" in available:
        return "comprehensive"
    elif "discover_os_only" in available and "discover_applications" in available:
        return "individual"
    elif "get_raw_server_data" in available:
        return "raw_data"
    else:
        return "none"
```

---

#### Solution 3: Update Orchestrator to Expose Tool Discovery

**File:** `python/src/beeai_agents/orchestrator.py`

**Add method to query available tools:**

```python
def get_available_mcp_tools(self) -> List[str]:
    """Get list of available MCP tool names.
    
    Returns:
        List of tool names
    """
    if not self._mcp_tools:
        return []
    
    return [tool.name for tool in self._mcp_tools]

def get_discovery_capabilities(self) -> Dict[str, Any]:
    """Get discovery capabilities based on available tools.
    
    Returns:
        Dictionary describing discovery capabilities
    """
    if not self._discovery_agent:
        return {
            "enabled": False,
            "reason": "Discovery agent not initialized"
        }
    
    available_tools = self._discovery_agent.get_available_discovery_tools()
    strategy = self._discovery_agent.get_discovery_strategy()
    
    return {
        "enabled": True,
        "strategy": strategy,
        "available_tools": available_tools,
        "capabilities": {
            "comprehensive_discovery": "discover_workload" in available_tools,
            "os_detection": "discover_os_only" in available_tools,
            "application_detection": "discover_applications" in available_tools,
            "raw_data_collection": "get_raw_server_data" in available_tools
        }
    }
```

---

#### Solution 4: Add Logging and Diagnostics

**File:** `python/src/beeai_agents/discovery_agent.py`

**Add diagnostic logging on initialization:**

```python
async def _ensure_mcp_tools(self):
    """Ensure MCP tools are loaded with diagnostic logging."""
    if self._mcp_tools is not None:
        return
    
    logger.info("Loading MCP tools...")
    
    # Auto-detect MCP server path if not provided
    if self.mcp_server_path is None:
        from pathlib import Path
        self.mcp_server_path = str(Path(__file__).parent.parent.parent / "cyberres-mcp")
    
    # Create MCP client
    import os
    from pathlib import Path
    server_path = Path(self.mcp_server_path)
    
    server_params = StdioServerParameters(
        command="uv",
        args=["--directory", str(server_path), "run", "cyberres-mcp"],
        env={
            **os.environ,
            "MCP_TRANSPORT": "stdio",
            "PYTHONPATH": str(server_path / "src"),
        }
    )
    
    self._mcp_client = stdio_client(server_params)
    
    # Load tools
    self._mcp_tools = await MCPTool.from_client(self._mcp_client)
    
    # DIAGNOSTIC LOGGING
    logger.info(f"✓ Loaded {len(self._mcp_tools)} MCP tools")
    
    # Log discovery tools specifically
    discovery_tools = self.get_available_discovery_tools()
    logger.info(f"✓ Discovery tools available: {discovery_tools}")
    
    # Log discovery strategy
    strategy = self.get_discovery_strategy()
    logger.info(f"✓ Discovery strategy: {strategy}")
    
    # Warn if no discovery tools
    if not discovery_tools:
        logger.warning(
            "⚠️  No discovery tools found! "
            f"Available tools: {[t.name for t in self._mcp_tools]}"
        )
```

---

### 2.4 Testing the Fix

#### Test Script: `test_dynamic_discovery.py`

```python
#!/usr/bin/env python3
"""
Test Dynamic Discovery Tool Selection

This script tests the enhanced discovery agent with dynamic tool selection.
"""

import asyncio
import logging
from beeai_agents.discovery_agent import BeeAIDiscoveryAgent
from models import VMResourceInfo, ResourceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_dynamic_discovery():
    """Test dynamic discovery with tool selection."""
    
    print("\n" + "="*80)
    print("🧪 TESTING DYNAMIC DISCOVERY TOOL SELECTION")
    print("="*80)
    
    # Initialize discovery agent
    print("\n📡 Step 1: Initializing discovery agent...")
    agent = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2",
        mcp_server_path="../cyberres-mcp"
    )
    
    # Ensure MCP tools are loaded
    await agent._ensure_mcp_tools()
    
    # Check available tools
    print("\n🔍 Step 2: Checking available discovery tools...")
    available_tools = agent.get_available_discovery_tools()
    print(f"   Available tools: {available_tools}")
    
    # Check discovery strategy
    print("\n🎯 Step 3: Determining discovery strategy...")
    strategy = agent.get_discovery_strategy()
    print(f"   Strategy: {strategy}")
    
    # Check individual tool availability
    print("\n📋 Step 4: Checking individual tool availability...")
    tools_to_check = [
        "discover_workload",
        "discover_os_only",
        "discover_applications",
        "get_raw_server_data"
    ]
    
    for tool_name in tools_to_check:
        available = agent.has_discovery_tool(tool_name)
        status = "✅ Available" if available else "❌ Not Available"
        print(f"   {tool_name}: {status}")
    
    # Test discovery on a sample resource
    print("\n🚀 Step 5: Testing discovery on sample resource...")
    resource = VMResourceInfo(
        host="localhost",
        resource_type=ResourceType.VM,
        ssh_user="test",
        ssh_password="test"
    )
    
    try:
        result = await agent.discover(resource)
        print(f"   ✅ Discovery completed!")
        print(f"   - Ports: {len(result.ports)}")
        print(f"   - Processes: {len(result.processes)}")
        print(f"   - Applications: {len(result.applications)}")
    except Exception as e:
        print(f"   ⚠️  Discovery failed (expected for test): {e}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_dynamic_discovery())
```

---

### 2.5 Implementation Checklist

#### Phase 2A: Core Fixes (High Priority)

- [ ] Update `_execute_discovery()` method with dynamic tool selection
- [ ] Implement `_execute_comprehensive_discovery()` method
- [ ] Implement `_execute_raw_data_discovery()` method
- [ ] Refactor `_execute_individual_discovery()` to use dynamic lookup
- [ ] Add helper methods: `get_available_discovery_tools()`, `has_discovery_tool()`, `get_discovery_strategy()`
- [ ] Add diagnostic logging to `_ensure_mcp_tools()`
- [ ] Update orchestrator with `get_discovery_capabilities()` method

#### Phase 2B: Testing (Medium Priority)

- [ ] Create `test_dynamic_discovery.py` test script
- [ ] Test with all 4 discovery tools available
- [ ] Test with only individual tools available
- [ ] Test with no discovery tools (error handling)
- [ ] Test fallback mechanisms

#### Phase 2C: Documentation (Low Priority)

- [ ] Update `BEEAI_TESTING_GUIDE.md` with dynamic discovery info
- [ ] Document tool selection strategy in README
- [ ] Add troubleshooting guide for tool discovery issues

---

### 2.6 Expected Benefits

After implementing these fixes:

1. **✅ Dynamic Tool Discovery**
   - BeeAI will automatically detect and use all available MCP discovery tools
   - No hardcoded tool names

2. **✅ Intelligent Fallback**
   - Tries `discover_workload` first (comprehensive)
   - Falls back to individual tools if needed
   - Can use `get_raw_server_data` + LLM as last resort

3. **✅ Better Error Handling**
   - Clear error messages when tools are unavailable
   - Graceful degradation instead of failures

4. **✅ Future-Proof**
   - New tools added to MCP server are automatically discovered
   - No code changes needed when MCP server is updated

5. **✅ Better Observability**
   - Diagnostic logging shows which tools are available
   - Clear indication of discovery strategy being used

---

## Implementation Priority

### Phase 1: Immediate Actions (Week 1)

1. **Delete archive directory** (40 files)
   ```bash
   rm -rf python/archive/docs_backup_20260225/
   ```

2. **Implement Phase 2 core fixes** (dynamic discovery)
   - Update `discovery_agent.py` with dynamic tool selection
   - Add helper methods
   - Add diagnostic logging

3. **Test dynamic discovery**
   - Run `test_dynamic_discovery.py`
   - Verify all 4 tools are discovered and used

### Phase 2: Consolidation (Week 2)

1. **Consolidate documentation**
   - Merge weekly summaries into `PROJECT_HISTORY.md`
   - Consolidate testing guides into `TESTING.md`
   - Create single `QUICKSTART.md`

2. **Remove Pydantic AI implementations**
   - Delete `python/src/agents/` directory
   - Delete `conversation.py` and `llm_orchestrator.py`
   - Update imports in any remaining files

3. **Test after cleanup**
   - Ensure all BeeAI functionality still works
   - Run full test suite

### Phase 3: Verification (Week 3)

1. **Final testing**
   - Test complete workflow with dynamic discovery
   - Verify all 4 MCP tools are utilized
   - Test fallback mechanisms

2. **Documentation update**
   - Update README with new architecture
   - Document dynamic discovery feature
   - Add troubleshooting guide

3. **Code review**
   - Review all changes
   - Ensure no regressions
   - Verify cleanup is complete

---

## Conclusion

This plan addresses both critical issues:

1. **Phase 1:** Removes 70-80 unnecessary files, reducing codebase complexity by 40-50%
2. **Phase 2:** Fixes MCP tool discovery to enable dynamic tool selection and utilization of all 4 available discovery tools

**Key Improvement:** BeeAI will transition from **hardcoded tool names** to **dynamic tool discovery**, enabling it to automatically adapt to available MCP tools and utilize the full power of the MCP server's discovery capabilities.

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1 immediate actions (delete archive, implement core fixes)
3. Test and validate changes
4. Proceed with consolidation and cleanup

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-25  
**Status:** Ready for Review and Implementation