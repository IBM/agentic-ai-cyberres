# Tool Selection Issues & Fixes

## 🐛 Problem Identified

From your test run, I can see **two critical issues**:

### Issue 1: Wrong Tools Being Selected
```
[6/7] db_mongo_ssh_ping
  Reason: Infrastructure validation tool (fallback selection)
  
ERROR: Command failed with exit code 127
ERROR: TypeError: 'str' object is not callable
Result: ✓ Success (WRONG!)
```

**Problem**: MongoDB tools are being called even though MongoDB is NOT installed on the VM.

### Issue 2: Failed Tools Marked as Success
```
ERROR: Error calling tool 'db_mongo_ssh_ping'
Agent 🤖 ✓ Success
```

**Problem**: Tools fail but are still marked as successful, hiding real issues.

### Issue 3: No Detailed Report
```
VALIDATION SUMMARY
Validations: 7/7 passed
Overall Status: PASS
Score: 100/100
```

**Problem**: Basic summary only, no detailed findings or metrics despite our enhancements.

---

## 🔍 Root Cause Analysis

### 1. Tool Selection Logic

The current workflow has this decision flow:

```
Discovery → Classification → Tool Selection → Validation
```

**The Problem**:
- Discovery finds ports/processes
- Classification identifies resource type (e.g., DATABASE_SERVER)
- Tool selection uses **fallback logic** instead of **AI-based selection**
- Fallback selects ALL database tools (Oracle, MongoDB, etc.) regardless of what's actually installed

**From your logs**:
```
Reason: Infrastructure validation tool (fallback selection)
```

This means the AI classification is NOT being used for tool selection!

### 2. Error Handling

**The Problem**:
- Tools fail with exit code 127 (command not found)
- Error is caught but not properly propagated
- Validation marked as "Success" despite failures

**From your logs**:
```python
TypeError: 'str' object is not callable
# This is a bug in mongo_db.py line 141:
return err("ssh exec failed", ...)  # err is a string, not a function!
```

### 3. Reporting

**The Problem**:
- Enhanced reporting agent is not being invoked
- Only basic summary is shown
- No findings, metrics, or action items

---

## ✅ Solutions

### Solution 1: Fix Tool Selection Logic

**Current (Broken)**:
```python
# In tool_coordinator.py or validation_agent.py
def select_tools(self, classification):
    # Fallback logic - selects ALL tools for category
    if classification.category == ResourceCategory.DATABASE_SERVER:
        return ["oracle_db_validation", "mongo_db_validation", "postgres_validation"]
```

**Fixed (AI-Based)**:
```python
def select_tools(self, classification, discovery_result):
    """Select tools based on ACTUAL detected applications."""
    tools = []
    
    # Use detected applications from discovery
    detected_apps = [app.name.lower() for app in discovery_result.applications]
    
    # Only select tools for detected applications
    if any('oracle' in app for app in detected_apps):
        tools.append("oracle_db_validation")
    
    if any('mongo' in app for app in detected_apps):
        tools.append("mongo_db_validation")
    
    if any('postgres' in app for app in detected_apps):
        tools.append("postgres_validation")
    
    # If no specific apps detected, use basic validation only
    if not tools:
        tools.append("vm_validation")  # Basic checks only
    
    return tools
```

### Solution 2: Fix Error Handling

**Current (Broken)**:
```python
# In mongo_db.py line 141
return err("ssh exec failed", ...)  # err is a string!
```

**Fixed**:
```python
# In mongo_db.py
from cyberres_mcp.plugins.error_codes import error_response

# Line 141:
return error_response(
    "ssh exec failed",
    code="SSH_ERROR",
    rc=rc,
    stderr=err,
    stdout=out,
    via="ssh_exec"
)
```

**Also fix validation result handling**:
```python
# In validation_agent.py
async def validate(self, ...):
    results = []
    for tool in selected_tools:
        try:
            result = await self.tool_coordinator.call_tool(tool, params)
            
            # Check if tool actually succeeded
            if result.get('error') or result.get('rc', 0) != 0:
                results.append(ValidationResult(
                    tool_name=tool,
                    is_valid=False,  # Mark as failed!
                    errors=[result.get('error', 'Tool execution failed')]
                ))
            else:
                results.append(ValidationResult(
                    tool_name=tool,
                    is_valid=True,
                    data=result
                ))
        except Exception as e:
            results.append(ValidationResult(
                tool_name=tool,
                is_valid=False,
                errors=[str(e)]
            ))
    
    return results
```

### Solution 3: Enable Enhanced Reporting

**Check if AI reporting is enabled**:
```python
# In your .env or environment
export FEATURE_FLAG_AI_REPORTING=true
export FEATURE_FLAG_SMART_LLM_USAGE=true
```

**Ensure reporting agent is called**:
```python
# In recovery_validation_agent.py or main workflow
async def generate_report(self, validation_results, discovery_result, classification):
    # Use enhanced reporting agent
    report = await self.reporting_agent.generate_report(
        validation_result=validation_results,
        discovery_result=discovery_result,
        classification=classification,
        evaluation=evaluation  # Include evaluation results
    )
    
    # This should return detailed report with:
    # - Executive summary
    # - Key metrics with trends
    # - Detailed findings
    # - Action items
    return report
```

---

## 🔧 Immediate Fixes to Apply

### Fix 1: Update Tool Coordinator

**File**: `python/src/tool_coordinator.py`

```python
def select_tools(
    self,
    classification: ResourceClassification,
    discovery_result: WorkloadDiscoveryResult
) -> List[str]:
    """Select tools based on detected applications, not just category."""
    
    tools = []
    detected_apps = [app.name.lower() for app in discovery_result.applications]
    
    logger.info(f"Detected applications: {detected_apps}")
    
    # Map detected apps to tools
    app_tool_map = {
        'oracle': 'oracle_db_validation',
        'mongodb': 'mongo_db_validation',
        'mongo': 'mongo_db_validation',
        'postgresql': 'postgres_validation',
        'postgres': 'postgres_validation',
        'mysql': 'mysql_validation',
        'nginx': 'web_server_validation',
        'apache': 'web_server_validation',
        'tomcat': 'application_server_validation',
    }
    
    # Select tools for detected apps
    for app in detected_apps:
        for keyword, tool in app_tool_map.items():
            if keyword in app and tool not in tools:
                tools.append(tool)
                logger.info(f"Selected tool {tool} for detected app {app}")
    
    # Fallback to basic validation if no specific tools
    if not tools:
        tools.append('vm_validation')
        logger.info("No specific apps detected, using basic VM validation")
    
    return tools
```

### Fix 2: Update Validation Agent Error Handling

**File**: `python/src/agents/validation_agent.py`

```python
async def validate(self, ...):
    """Validate with proper error handling."""
    
    results = []
    for tool_name in selected_tools:
        logger.info(f"Executing tool: {tool_name}")
        
        try:
            result = await self.tool_coordinator.call_tool(tool_name, params)
            
            # Check for errors in result
            is_valid = True
            errors = []
            
            if isinstance(result, dict):
                if result.get('error'):
                    is_valid = False
                    errors.append(result['error'])
                if result.get('rc', 0) != 0:
                    is_valid = False
                    errors.append(f"Tool exited with code {result['rc']}")
            
            results.append(ValidationResult(
                tool_name=tool_name,
                is_valid=is_valid,
                errors=errors,
                data=result if is_valid else None
            ))
            
            logger.info(f"Tool {tool_name}: {'PASS' if is_valid else 'FAIL'}")
            
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            results.append(ValidationResult(
                tool_name=tool_name,
                is_valid=False,
                errors=[str(e)]
            ))
    
    return results
```

### Fix 3: Fix MongoDB Plugin Error

**File**: `python/cyberres-mcp/src/cyberres_mcp/plugins/mongo_db.py`

**Line 141** (and similar lines):
```python
# BEFORE (BROKEN):
return err("ssh exec failed", code="SSH_ERROR", ...)

# AFTER (FIXED):
from cyberres_mcp.plugins.error_codes import error_response

return error_response(
    message="ssh exec failed",
    code="SSH_ERROR",
    rc=rc,
    stderr=err,
    stdout=out,
    via="ssh_exec"
)
```

---

## 🧪 Testing the Fixes

### Test 1: Verify Tool Selection

```bash
cd python/src
uv run python -c "
from agents.discovery_agent import DiscoveryAgent
from agents.classification_agent import ClassificationAgent
from tool_coordinator import ToolCoordinator
from models import ResourceInfo, ResourceType
import asyncio

async def test():
    # Discover a VM WITHOUT MongoDB
    discovery_agent = DiscoveryAgent()
    resource = ResourceInfo(
        host='9.11.68.243',
        resource_type=ResourceType.VM,
        ssh_user='root',
        ssh_port=22
    )
    
    discovery_result = await discovery_agent.discover(resource)
    print(f'Detected apps: {[app.name for app in discovery_result.applications]}')
    
    # Classify
    classification_agent = ClassificationAgent()
    classification = await classification_agent.classify(discovery_result)
    print(f'Classification: {classification.category}')
    
    # Select tools
    coordinator = ToolCoordinator()
    tools = coordinator.select_tools(classification, discovery_result)
    print(f'Selected tools: {tools}')
    
    # Should NOT include mongo tools if MongoDB not detected!
    assert 'mongo_db_validation' not in tools, 'MongoDB tool should not be selected!'
    print('✓ Tool selection working correctly!')

asyncio.run(test())
"
```

### Test 2: Verify Error Handling

```bash
cd python/src
uv run python -c "
from agents.validation_agent import ValidationAgent
import asyncio

async def test():
    agent = ValidationAgent()
    
    # This should properly handle tool failures
    results = await agent.validate(...)
    
    # Check that failures are marked as failures
    for result in results:
        if result.errors:
            assert not result.is_valid, 'Failed tool should be marked as invalid!'
            print(f'✓ Tool {result.tool_name} properly marked as FAILED')
        else:
            assert result.is_valid, 'Successful tool should be marked as valid!'
            print(f'✓ Tool {result.tool_name} properly marked as PASSED')

asyncio.run(test())
"
```

### Test 3: Verify Enhanced Reporting

```bash
cd python/src

# Enable AI reporting
export FEATURE_FLAG_AI_REPORTING=true
export FEATURE_FLAG_SMART_LLM_USAGE=true

uv run python main.py

# Then validate a resource
> Validate VM at 9.11.68.243

# Expected output should include:
# - Executive Summary
# - Key Metrics (health score, failed checks, etc.)
# - Detailed Findings (with severity, category, evidence)
# - Action Items (with priority, effort, timeline)
```

---

## 📊 Expected Behavior After Fixes

### Before Fixes:
```
Discovery: Found ports 22, 80, 443
Classification: DATABASE_SERVER (wrong!)
Tool Selection: oracle_db, mongo_db, postgres_db (all of them!)
Validation: 7/7 passed (but 2 actually failed!)
Report: Basic summary only
```

### After Fixes:
```
Discovery: Found ports 22, 80, 443, processes: sshd, nginx
Classification: WEB_SERVER (correct!)
Tool Selection: web_server_validation (only what's detected!)
Validation: 1/1 passed (accurate!)
Report: Detailed with findings, metrics, actions
```

---

## 🎯 Summary

The issues you're seeing are:

1. **Tool Selection**: Using fallback logic instead of AI-based detection
   - **Fix**: Update `tool_coordinator.py` to use detected applications
   
2. **Error Handling**: Failed tools marked as successful
   - **Fix**: Update `validation_agent.py` to properly check tool results
   - **Fix**: Fix `mongo_db.py` error response bug

3. **Reporting**: Enhanced reporting not being used
   - **Fix**: Enable AI reporting flags
   - **Fix**: Ensure reporting agent is properly invoked

**Apply these fixes and the workflow will**:
- ✅ Only call tools for detected applications
- ✅ Properly report tool failures
- ✅ Generate detailed reports with findings and metrics

---

## 🚀 Quick Fix Script

```bash
# 1. Enable feature flags
export FEATURE_FLAG_AI_REPORTING=true
export FEATURE_FLAG_SMART_LLM_USAGE=true
export FEATURE_FLAG_AI_CLASSIFICATION=true

# 2. Apply the code fixes above to:
# - python/src/tool_coordinator.py
# - python/src/agents/validation_agent.py
# - python/cyberres-mcp/src/cyberres_mcp/plugins/mongo_db.py

# 3. Test again
cd python/src
uv run python main.py
```

Let me know if you want me to implement these fixes!