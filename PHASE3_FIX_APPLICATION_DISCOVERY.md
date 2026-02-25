# Phase 3: Fix Application Discovery - Empty Results Issue

**Date:** 2026-02-25  
**Status:** 🔄 PLANNED  
**Priority:** HIGH - Applications not being discovered

---

## Problem Analysis

### Current Situation

From the logs:
```
2026-02-25 18:33:07,310 - Available discovery tools: ['discover_os_only', 'discover_applications', 'get_raw_server_data', 'discover_workload']
2026-02-25 18:33:07,310 - Selected discovery strategy: comprehensive
2026-02-25 18:33:07,310 - Using comprehensive discover_workload tool
2026-02-25 18:33:07,310 - Calling discover_workload for 9.11.68.243
2026-02-25 18:33:07,321 - Comprehensive discovery completed for 9.11.68.243
2026-02-25 18:33:07,321 - Found 0 applications
```

### Root Causes

1. **`discover_workload` Not Fully Implemented**
   - Location: `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/__init__.py:385-392`
   - Current status: Returns stub message "pending_implementation"
   - Returns empty data structure instead of actual discovery results

2. **Fallback Not Triggering**
   - Phase 2 fix added empty result detection
   - Should fall back to `discover_os_only` + `discover_applications`
   - Need to verify fallback is actually executing

3. **Individual Tools May Have Issues**
   - `discover_os_only` and `discover_applications` are implemented
   - But may have SSH connection or credential issues
   - Need to verify these tools work independently

---

## Phase 3 Implementation Plan

### Step 1: Verify Fallback is Working (IMMEDIATE)

**Test the fallback mechanism:**

```bash
cd python/src
uv run python beeai_interactive.py
```

**Expected log output:**
```
- Using comprehensive discover_workload tool
- Calling discover_workload for X.X.X.X
- Comprehensive discovery returned empty results, falling back to individual tools
- Using individual discovery tools (os + applications)
- Calling discover_os_only tool for X.X.X.X
- Calling discover_applications tool for X.X.X.X
- Found N applications
```

**If fallback is NOT triggering:**
- Check the empty result detection logic
- Verify `discover_os_only` and `discover_applications` are in available tools

### Step 2: Test Individual Tools Directly (DIAGNOSTIC)

**Create test script to verify individual tools work:**

```python
# test_individual_discovery.py
import asyncio
from beeai_agents.discovery_agent import BeeAIDiscoveryAgent
from models import VMResourceInfo, ResourceType

async def test_individual_tools():
    agent = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2",
        mcp_server_path="../cyberres-mcp"
    )
    
    await agent._ensure_mcp_tools()
    
    # Force individual strategy
    resource = VMResourceInfo(
        host="9.11.68.243",
        resource_type=ResourceType.VM,
        ssh_user="your_user",
        ssh_password="your_password"
    )
    
    # Test individual discovery directly
    result = await agent._execute_individual_discovery(resource, plan)
    print(f"Applications found: {len(result.applications)}")
    print(f"Ports found: {len(result.ports)}")
    print(f"Processes found: {len(result.processes)}")

asyncio.run(test_individual_tools())
```

### Step 3: Fix MCP Server Implementation (RECOMMENDED)

**Option A: Implement `discover_workload` Properly**

Update `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/__init__.py`:

```python
@mcp.tool()
def discover_workload(
    host: str,
    ssh_user: Optional[str] = None,
    ssh_password: Optional[str] = None,
    ssh_key_path: Optional[str] = None,
    ssh_port: int = 22,
    detect_os: bool = True,
    detect_applications: bool = True,
    detect_containers: bool = True,
    scan_ports: bool = False,
    port_range: Optional[str] = None,
    timeout_seconds: int = 300,
    min_confidence: str = "low"
) -> Dict[str, Any]:
    """Comprehensive workload discovery."""
    try:
        from ...models import DiscoveryRequest
        from .os_detector import OSDetector
        from .app_detector import ApplicationDetector
        from .aggregator import ResultAggregator
        
        # Create discovery request
        request = DiscoveryRequest(
            host=host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            ssh_port=ssh_port,
            detect_os=detect_os,
            detect_applications=detect_applications,
            detect_containers=detect_containers
        )
        
        results = {}
        
        # Step 1: OS Detection
        if detect_os:
            logger.info(f"Detecting OS for {host}")
            os_detector = OSDetector()
            os_info = os_detector.detect(request)
            results["os_info"] = os_info.dict()
        
        # Step 2: Application Detection
        if detect_applications:
            logger.info(f"Detecting applications for {host}")
            app_detector = ApplicationDetector()
            executor = request.create_ssh_executor()
            applications = app_detector.detect(request, executor)
            
            # Filter by confidence
            min_conf_map = {
                "high": ConfidenceLevel.HIGH,
                "medium": ConfidenceLevel.MEDIUM,
                "low": ConfidenceLevel.LOW,
                "uncertain": ConfidenceLevel.UNCERTAIN
            }
            min_conf = min_conf_map.get(min_confidence.lower(), ConfidenceLevel.LOW)
            filtered_apps = app_detector.confidence_scorer.filter_by_confidence(
                applications, min_conf
            )
            
            results["applications"] = [app.dict() for app in filtered_apps]
            results["total_applications"] = len(filtered_apps)
        
        # Step 3: Aggregate results
        aggregator = ResultAggregator()
        final_result = aggregator.aggregate(results)
        
        logger.info(
            f"Workload discovery completed for {host}",
            extra={
                "applications": len(results.get("applications", [])),
                "has_os_info": "os_info" in results
            }
        )
        
        return ok(final_result)
        
    except Exception as e:
        logger.error(f"Workload discovery failed for {host}", extra={"error": str(e)})
        return err(
            f"Workload discovery failed: {str(e)}",
            code="DISCOVERY_ERROR",
            host=host
        )
```

**Option B: Remove `discover_workload` from MCP Server (QUICK FIX)**

If implementing the full tool is too complex, remove it so BeeAI uses individual tools by default:

```python
# Comment out or remove the discover_workload tool registration
# This will make BeeAI use "individual" strategy by default
```

### Step 4: Verify SSH Credentials (CRITICAL)

**Check if SSH credentials are being passed correctly:**

```python
# In discovery_agent.py, add more logging:
logger.info(f"SSH credentials: user={tool_args.get('ssh_user')}, has_password={bool(tool_args.get('ssh_password'))}")
```

**Common issues:**
- SSH user not provided
- SSH password not provided
- SSH key path incorrect
- SSH port blocked by firewall
- Host not reachable

### Step 5: Test with Known Working Server (VALIDATION)

**Use a test server where you know applications are running:**

```python
resource = VMResourceInfo(
    host="localhost",  # or a known test server
    resource_type=ResourceType.VM,
    ssh_user="your_user",
    ssh_password="your_password"
)
```

**Verify:**
- SSH connection works
- Applications are actually running on the server
- Discovery tools can access the server

---

## Recommended Action Plan

### Immediate (Today)

1. **Verify fallback is triggering**
   - Check logs for "falling back to individual tools" message
   - If not appearing, the empty result detection needs adjustment

2. **Test individual tools directly**
   - Create test script to call `_execute_individual_discovery()` directly
   - Verify SSH credentials are correct
   - Check if applications are actually found

3. **Add more diagnostic logging**
   - Log SSH connection attempts
   - Log tool responses before parsing
   - Log any errors from MCP tools

### Short-term (This Week)

4. **Choose implementation path:**
   - **Path A:** Implement `discover_workload` properly (2-3 hours)
   - **Path B:** Remove `discover_workload` and use individual tools (5 minutes)

5. **Test with multiple servers**
   - Verify discovery works on different OS types
   - Test with different application types
   - Validate confidence scoring

### Long-term (Next Sprint)

6. **Enhance application detection**
   - Add more application signatures
   - Improve confidence scoring
   - Add LLM-based detection for unknown apps

7. **Add monitoring and metrics**
   - Track discovery success rates
   - Monitor tool performance
   - Alert on repeated failures

---

## Quick Fix (5 Minutes)

If you need applications discovered **right now**, do this:

### Option 1: Force Individual Strategy

Edit `python/src/beeai_agents/discovery_agent.py`:

```python
def get_discovery_strategy(self) -> str:
    """Determine the best discovery strategy based on available tools."""
    available = self.get_available_discovery_tools()
    
    # TEMPORARY: Force individual strategy until discover_workload is implemented
    if "discover_os_only" in available and "discover_applications" in available:
        return "individual"
    elif "discover_workload" in available:
        return "comprehensive"
    # ... rest of logic
```

### Option 2: Remove discover_workload from MCP

Comment out the tool in `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/__init__.py`:

```python
# @mcp.tool()  # COMMENTED OUT - not yet implemented
# def discover_workload(...):
#     ...
```

Then restart the MCP server.

---

## Debugging Checklist

When applications are not discovered, check:

- [ ] SSH credentials are correct
- [ ] Host is reachable
- [ ] SSH port (22) is open
- [ ] Applications are actually running on the server
- [ ] MCP server is running
- [ ] MCP tools are registered correctly
- [ ] Fallback logic is executing
- [ ] Individual tools (`discover_os_only`, `discover_applications`) work independently
- [ ] Tool responses are being parsed correctly
- [ ] No errors in MCP server logs
- [ ] No errors in BeeAI agent logs

---

## Expected Outcome

After Phase 3 fixes:

```
2026-02-25 XX:XX:XX - Available discovery tools: [...]
2026-02-25 XX:XX:XX - Selected discovery strategy: individual
2026-02-25 XX:XX:XX - Using individual discovery tools (os + applications)
2026-02-25 XX:XX:XX - Calling discover_os_only tool for 9.11.68.243
2026-02-25 XX:XX:XX - OS discovery completed
2026-02-25 XX:XX:XX - Calling discover_applications tool for 9.11.68.243
2026-02-25 XX:XX:XX - Application discovery completed
2026-02-25 XX:XX:XX - Found 5 applications  ← SUCCESS!
2026-02-25 XX:XX:XX - Discovery completed: 10 ports, 25 processes, 5 applications
```

---

## Next Steps

1. **Run diagnostic test** to verify fallback
2. **Choose quick fix** (force individual strategy OR remove discover_workload)
3. **Test with known working server**
4. **Implement proper `discover_workload`** (if needed)
5. **Add comprehensive error handling**

---

## Summary

**Phase 3 Goal:** Fix empty applications issue by ensuring discovery tools work correctly

**Root Cause:** `discover_workload` not implemented, fallback may not be triggering

**Solution:** 
- Verify fallback works
- Test individual tools
- Implement `discover_workload` OR force individual strategy
- Verify SSH credentials and connectivity

**Timeline:** 
- Quick fix: 5 minutes
- Full fix: 2-3 hours
- Testing: 1 hour

---

*Phase 3 Plan created by Bob - 2026-02-25*