# Tool Categorization Implementation Plan

## Overview

This document provides a step-by-step implementation plan for the Tool Categorization Strategy to fix the Oracle validation issue and improve the overall MCP-based validation workflow.

## Current State

### What's Working ✅
- MCP server connection via STDIO transport
- Dynamic tool discovery (14 tools found for Oracle)
- Oracle Database successfully discovered via `discover_applications` tool
- Parameter mapping for SSH credentials

### What's Not Working ❌
- Tool selector choosing Oracle tools that require database credentials
- Validation failing with "Unexpected keyword argument" errors
- No differentiation between SSH-based and direct-access tools

## Implementation Steps

### Step 1: Update `tool_selector.py` - Add Tool Categorization

**File**: `python/src/tool_selector.py`

**Changes**:

1. Add `ToolAccessMethod` enum:
```python
class ToolAccessMethod(Enum):
    """Categorizes tools by their access requirements."""
    SSH_DISCOVERY = "ssh_discovery"      # Discovers via SSH (e.g., db_oracle_discover_and_validate)
    SSH_VALIDATION = "ssh_validation"    # Validates via SSH (e.g., vm_validate_core)
    DIRECT_ACCESS = "direct_access"      # Requires app credentials (e.g., db_oracle_connect)
```

2. Add `categorize_tool()` method:
```python
def categorize_tool(self, tool_name: str) -> ToolAccessMethod:
    """Categorize tool by analyzing its name and purpose."""
    tool_lower = tool_name.lower()
    
    # SSH-based discovery tools (highest priority)
    if "discover" in tool_lower and ("validate" in tool_lower or "and" in tool_lower):
        return ToolAccessMethod.SSH_DISCOVERY
    
    # SSH-based validation tools (infrastructure)
    if any(pattern in tool_lower for pattern in self.VM_CORE_PATTERNS):
        return ToolAccessMethod.SSH_VALIDATION
    
    # Direct-access tools (require app credentials)
    return ToolAccessMethod.DIRECT_ACCESS
```

3. Update `select_tools()` signature to accept optional app credentials:
```python
def select_tools(
    self,
    discovered_apps: List[Dict[str, Any]],
    available_tools: List[str],
    ssh_creds: Dict[str, str],
    app_creds: Optional[Dict[str, Dict[str, str]]] = None  # NEW: app_name -> credentials
) -> List[ToolSelection]:
```

4. Update tool selection logic to prioritize SSH-based tools:
```python
# For each discovered app
for app in discovered_apps:
    app_name = app.get("name", "").lower()
    normalized_name = app_name.split()[0] if app_name else ""
    
    # Find matching tools
    matched_tools = []
    for tool_name in available_tools:
        if normalized_name in tool_name.lower():
            matched_tools.append(tool_name)
    
    # Categorize and prioritize
    for tool_name in matched_tools:
        category = self.categorize_tool(tool_name)
        
        # SSH-based discovery tools (CRITICAL - always include)
        if category == ToolAccessMethod.SSH_DISCOVERY:
            priority = ValidationPriority.CRITICAL
            reason = "SSH-based discovery (no app credentials needed)"
            params = self._build_ssh_parameters(tool_name, ssh_creds)
            selections.append(ToolSelection(...))
        
        # SSH-based validation tools (HIGH - always include)
        elif category == ToolAccessMethod.SSH_VALIDATION:
            priority = ValidationPriority.HIGH
            reason = "Infrastructure validation via SSH"
            params = self._build_ssh_parameters(tool_name, ssh_creds)
            selections.append(ToolSelection(...))
        
        # Direct-access tools (MEDIUM - only if credentials available)
        elif category == ToolAccessMethod.DIRECT_ACCESS:
            if app_creds and normalized_name in app_creds:
                priority = ValidationPriority.MEDIUM
                reason = "Direct validation with app credentials"
                params = self._build_direct_parameters(tool_name, ssh_creds, app_creds[normalized_name])
                selections.append(ToolSelection(...))
            else:
                logger.info(f"Skipping {tool_name} - requires {normalized_name} credentials")
```

5. Split `_build_parameters()` into two methods:
```python
def _build_ssh_parameters(
    self,
    tool_name: str,
    ssh_creds: Dict[str, str]
) -> Dict[str, Any]:
    """Build parameters for SSH-based tools."""
    return {
        "ssh_host": ssh_creds["hostname"],
        "ssh_user": ssh_creds["username"],
        "ssh_password": ssh_creds.get("password"),
        "ssh_key_path": ssh_creds.get("ssh_key_path"),
        "ssh_port": ssh_creds.get("ssh_port", 22)
    }

def _build_direct_parameters(
    self,
    tool_name: str,
    ssh_creds: Dict[str, str],
    app_creds: Dict[str, str]
) -> Dict[str, Any]:
    """Build parameters for direct-access tools."""
    params = {
        "host": ssh_creds["hostname"],
        "user": app_creds.get("username"),
        "password": app_creds.get("password"),
    }
    
    # Add app-specific parameters
    if "oracle" in tool_name.lower():
        params.update({
            "port": app_creds.get("port", 1521),
            "service": app_creds.get("service"),
            "sid": app_creds.get("sid")
        })
    elif "mongo" in tool_name.lower():
        params.update({
            "port": app_creds.get("port", 27017),
            "database": app_creds.get("database", "admin")
        })
    
    return params
```

**Estimated Time**: 2-3 hours  
**Testing**: Unit tests for categorization logic

---

### Step 2: Update `recovery_validation_agent.py` - Pass App Credentials

**File**: `python/src/recovery_validation_agent.py`

**Changes**:

1. Update `run_mcp_centric_validation()` to get app credentials:
```python
async def run_mcp_centric_validation(
    self,
    ip_address: str,
    resource_type: ResourceType,
    ssh_creds: Dict[str, str]
) -> ValidationReport:
    """Run MCP-centric validation workflow."""
    
    # ... existing discovery code ...
    
    # Get app credentials if available
    app_creds = {}
    for app in discovered_apps:
        app_name = app.get("name", "").lower().split()[0]
        try:
            # Try to get credentials for this app
            creds = self.credential_manager.get_credentials(
                resource_type=f"db_{app_name}",
                hostname=ip_address
            )
            if creds:
                app_creds[app_name] = creds
                logger.info(f"Found credentials for {app_name}")
        except Exception as e:
            logger.debug(f"No credentials found for {app_name}: {e}")
    
    # Select tools with app credentials
    from tool_selector import ToolSelector
    selector = ToolSelector()
    selected_tools = selector.select_tools(
        discovered_apps=discovered_apps,
        available_tools=available_tools,
        ssh_creds=ssh_creds,
        app_creds=app_creds  # NEW: pass app credentials
    )
```

2. Update tool execution to handle None parameters:
```python
for tool_selection in selected_tools:
    if tool_selection.parameters is None:
        logger.info(f"Skipping {tool_selection.tool_name} - missing required credentials")
        continue
    
    # Execute tool
    result = await self.mcp_client.call_tool(
        tool_selection.tool_name,
        tool_selection.parameters
    )
```

**Estimated Time**: 1 hour  
**Testing**: Integration test with SSH-only credentials

---

### Step 3: Update Credential Manager - Support App Credentials

**File**: `python/src/credentials.py`

**Changes** (if needed):

1. Add method to get app-specific credentials:
```python
def get_app_credentials(
    self,
    app_type: str,  # "oracle", "mongo", etc.
    hostname: str
) -> Optional[Dict[str, str]]:
    """Get application-specific credentials.
    
    Args:
        app_type: Type of application (oracle, mongo, etc.)
        hostname: Hostname/IP of the server
    
    Returns:
        Dictionary with app credentials or None if not found
    """
    try:
        # Try to get from credential store
        creds = self.get_credentials(
            resource_type=f"db_{app_type}",
            hostname=hostname
        )
        return creds
    except Exception:
        return None
```

**Estimated Time**: 30 minutes  
**Testing**: Unit tests for credential retrieval

---

### Step 4: Add Logging and Diagnostics

**Files**: `python/src/tool_selector.py`, `python/src/recovery_validation_agent.py`

**Changes**:

1. Add detailed logging for tool selection:
```python
logger.info(f"Tool Selection Summary:")
logger.info(f"  Total tools available: {len(available_tools)}")
logger.info(f"  SSH-based discovery tools: {len([t for t in selections if t.priority == ValidationPriority.CRITICAL])}")
logger.info(f"  SSH-based validation tools: {len([t for t in selections if t.priority == ValidationPriority.HIGH])}")
logger.info(f"  Direct-access tools: {len([t for t in selections if t.priority == ValidationPriority.MEDIUM])}")
logger.info(f"  Skipped tools: {len(matched_tools) - len(selections)}")
```

2. Add tool execution summary:
```python
logger.info(f"Validation Results:")
logger.info(f"  Successful: {len([r for r in results if r.success])}")
logger.info(f"  Failed: {len([r for r in results if not r.success])}")
logger.info(f"  Skipped: {len([t for t in selected_tools if t.parameters is None])}")
```

**Estimated Time**: 30 minutes

---

### Step 5: Create Test Cases

**File**: `python/src/test_tool_categorization.py` (new)

**Test Cases**:

1. Test tool categorization:
```python
def test_categorize_ssh_discovery_tool():
    selector = ToolSelector()
    assert selector.categorize_tool("db_oracle_discover_and_validate") == ToolAccessMethod.SSH_DISCOVERY

def test_categorize_ssh_validation_tool():
    selector = ToolSelector()
    assert selector.categorize_tool("vm_validate_core") == ToolAccessMethod.SSH_VALIDATION

def test_categorize_direct_access_tool():
    selector = ToolSelector()
    assert selector.categorize_tool("db_oracle_connect") == ToolAccessMethod.DIRECT_ACCESS
```

2. Test tool selection with SSH-only credentials:
```python
def test_select_tools_ssh_only():
    selector = ToolSelector()
    discovered_apps = [{"name": "Oracle Database", "version": "19c"}]
    available_tools = [
        "db_oracle_discover_and_validate",
        "db_oracle_connect",
        "vm_validate_core"
    ]
    ssh_creds = {"hostname": "9.11.68.243", "username": "root", "password": "pass"}
    
    selections = selector.select_tools(discovered_apps, available_tools, ssh_creds)
    
    # Should select SSH-based tools only
    assert len(selections) == 2
    assert any(s.tool_name == "db_oracle_discover_and_validate" for s in selections)
    assert any(s.tool_name == "vm_validate_core" for s in selections)
    assert not any(s.tool_name == "db_oracle_connect" for s in selections)
```

3. Test tool selection with full credentials:
```python
def test_select_tools_with_app_creds():
    selector = ToolSelector()
    discovered_apps = [{"name": "Oracle Database", "version": "19c"}]
    available_tools = [
        "db_oracle_discover_and_validate",
        "db_oracle_connect",
        "vm_validate_core"
    ]
    ssh_creds = {"hostname": "9.11.68.243", "username": "root", "password": "pass"}
    app_creds = {
        "oracle": {"username": "sys", "password": "oracle", "service": "ORCL"}
    }
    
    selections = selector.select_tools(discovered_apps, available_tools, ssh_creds, app_creds)
    
    # Should select all tools
    assert len(selections) == 3
```

**Estimated Time**: 2 hours  
**Testing**: Run all test cases

---

### Step 6: Update Documentation

**Files**: 
- `python/src/README.md`
- `python/src/TESTING_GUIDE.md`
- `python/src/HOW_TO_RUN.md`

**Changes**:

1. Document tool categorization in README
2. Add examples of SSH-only vs full credential validation
3. Update testing guide with new test cases
4. Document credential configuration for app-specific validation

**Estimated Time**: 1 hour

---

## Implementation Timeline

### Phase 1: Core Implementation (4-5 hours)
- [ ] Step 1: Update tool_selector.py with categorization
- [ ] Step 2: Update recovery_validation_agent.py
- [ ] Step 3: Update credential manager (if needed)

### Phase 2: Testing & Validation (2-3 hours)
- [ ] Step 4: Add logging and diagnostics
- [ ] Step 5: Create and run test cases
- [ ] Manual testing with Oracle discovery

### Phase 3: Documentation (1-2 hours)
- [ ] Step 6: Update all documentation
- [ ] Create user guide for credential configuration

**Total Estimated Time**: 7-10 hours

---

## Testing Strategy

### Unit Tests
- Tool categorization logic
- Parameter building for each category
- Credential retrieval

### Integration Tests
1. **SSH-only validation**:
   - Input: Oracle discovered, SSH credentials only
   - Expected: SSH-based tools selected and executed
   - Expected: Direct-access tools skipped with clear logging

2. **Full credential validation**:
   - Input: Oracle discovered, SSH + DB credentials
   - Expected: All applicable tools selected and executed
   - Expected: Successful validation with detailed results

3. **Mixed credentials**:
   - Input: Multiple apps, partial credentials
   - Expected: Each app validated with available credentials
   - Expected: Clear logging for skipped validations

### Manual Testing
1. Run with test server (9.11.68.243)
2. Verify Oracle discovery works
3. Verify SSH-based validation succeeds
4. Verify clear logging for skipped tools

---

## Success Criteria

### Must Have ✅
- [ ] Oracle discovered successfully via SSH
- [ ] SSH-based tools (db_oracle_discover_and_validate) selected and executed
- [ ] Direct-access tools (db_oracle_connect) skipped when credentials unavailable
- [ ] Clear logging explaining tool selection decisions
- [ ] No validation failures due to missing credentials

### Should Have 🎯
- [ ] Support for app credential configuration
- [ ] Graceful handling of partial credentials
- [ ] Comprehensive test coverage
- [ ] Updated documentation

### Nice to Have 💡
- [ ] Credential prompting for missing app credentials
- [ ] Multi-stage validation (discovery → prompt → validate)
- [ ] Credential discovery from SSH-based tools

---

## Rollback Plan

If implementation causes issues:

1. **Immediate**: Revert to previous tool_selector.py
2. **Short-term**: Use feature flag to toggle categorization
3. **Long-term**: Fix issues and re-enable

Feature flag approach:
```python
# In settings or environment
USE_TOOL_CATEGORIZATION = os.getenv("USE_TOOL_CATEGORIZATION", "true").lower() == "true"

# In tool_selector.py
if USE_TOOL_CATEGORIZATION:
    category = self.categorize_tool(tool_name)
    # ... new logic
else:
    # ... old logic
```

---

## Next Steps

1. Review this implementation plan
2. Get approval to proceed
3. Start with Step 1 (tool_selector.py updates)
4. Test incrementally after each step
5. Document learnings and issues

---

## Questions to Address

1. **Credential Storage**: Where should app credentials be stored?
   - Answer: Use existing credential manager with app-specific resource types

2. **Credential Prompting**: Should we prompt users for missing credentials?
   - Answer: Phase 2 enhancement, not required for initial implementation

3. **Tool Priority**: Should we adjust priorities based on credential availability?
   - Answer: Yes, SSH-based tools get higher priority when app creds unavailable

4. **Error Handling**: How to handle tools that fail due to missing credentials?
   - Answer: Skip with clear logging, don't fail entire validation

---

## References

- [TOOL_CATEGORIZATION_STRATEGY.md](./TOOL_CATEGORIZATION_STRATEGY.md) - Detailed strategy document
- [oracle_db.py](../cyberres-mcp/src/cyberres_mcp/plugins/oracle_db.py) - Oracle tool implementations
- [tool_selector.py](./tool_selector.py) - Current tool selector implementation
- [recovery_validation_agent.py](./recovery_validation_agent.py) - Main agent implementation