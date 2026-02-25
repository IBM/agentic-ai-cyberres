# Phase 4 Week 3: MCP-Centric Workflow Implementation

## Overview
Week 3 implements the core MCP best practice: **minimal user input + automatic discovery**. User provides only hostname + SSH credentials, then MCP tools discover everything automatically.

## Key Principle

**Before (Weeks 1-2):**
```
User → Specify resource type → Provide credentials → Provide service details → Validate
```

**After (Week 3):**
```
User → Hostname + SSH → Auto-discover everything → Auto-validate → Report
```

## Architecture Changes

### 1. Simplified Conversation Flow

#### New File: `conversation_simple.py`
```python
class SimpleConversationHandler:
    """Only asks for hostname + SSH credentials."""
    
    async def parse_minimal_input(user_input):
        """Extract: hostname, ssh_user, ssh_password/ssh_key"""
        # Uses LLM to parse natural language
        return {
            "hostname": "192.168.1.100",
            "ssh_user": "admin",
            "ssh_password": "secret"
        }
```

**Benefits:**
- 70% less user input required
- No need to know what's running on server
- Works for any infrastructure (VM, Oracle, MongoDB, etc.)
- User-friendly for non-technical users

### 2. MCP-Based Discovery Workflow

#### Discovery Tools Available
From `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/`:

1. **`discover_os_only`** - Detects OS type, version, distribution
2. **`discover_applications`** - Finds Oracle, MongoDB, web servers, etc.
3. **`get_raw_server_data`** - Collects raw data for LLM analysis
4. **`discover_workload`** - Complete workload discovery

#### New Discovery Flow
```python
# 1. Connect to server via SSH
ssh_creds = {
    "hostname": "192.168.1.100",
    "username": "admin",
    "password": "secret"
}

# 2. Discover OS
os_info = await mcp_client.call_tool("discover_os_only", ssh_creds)
# Returns: {"os_type": "linux", "distribution": "ubuntu", "version": "22.04"}

# 3. Discover applications
apps = await mcp_client.call_tool("discover_applications", ssh_creds)
# Returns: [
#   {"name": "oracle", "version": "19c", "port": 1521, "confidence": "high"},
#   {"name": "mongodb", "version": "6.0", "port": 27017, "confidence": "high"}
# ]

# 4. Select validation tools based on discoveries
validation_tools = select_tools_for_apps(apps, mcp_client.get_available_tools())
# Returns: ["validate_oracle_db", "validate_mongodb", "check_vm_health"]

# 5. Run validations
results = await run_validations(validation_tools, ssh_creds)
```

### 3. Intelligent Tool Selection

#### New Module: `tool_selector.py`
```python
class ToolSelector:
    """Selects validation tools based on discovered applications."""
    
    # Map discovered apps to validation tools
    APP_TO_TOOLS = {
        "oracle": ["validate_oracle_db", "check_oracle_listener"],
        "mongodb": ["validate_mongodb", "check_mongo_replication"],
        "postgresql": ["validate_postgres_db"],
        "nginx": ["validate_nginx_config"],
        "apache": ["validate_apache_config"],
        # ... etc
    }
    
    def select_tools(self, discovered_apps, available_tools):
        """Select tools that are both needed and available."""
        selected = []
        for app in discovered_apps:
            app_name = app["name"].lower()
            if app_name in self.APP_TO_TOOLS:
                for tool in self.APP_TO_TOOLS[app_name]:
                    if tool in available_tools:
                        selected.append({
                            "tool": tool,
                            "app": app,
                            "priority": self._calculate_priority(app)
                        })
        return sorted(selected, key=lambda x: x["priority"], reverse=True)
```

### 4. Updated Orchestrator

#### Modified: `recovery_validation_agent.py`
```python
async def run_mcp_centric_validation(self, ssh_creds, reader):
    """New MCP-centric validation workflow."""
    
    # 1. Discover OS
    write_progress("🔍 Discovering operating system...")
    os_info = await self.mcp_client.call_tool("discover_os_only", ssh_creds)
    write_progress(f"✓ Detected: {os_info['distribution']} {os_info['version']}")
    
    # 2. Discover applications
    write_progress("🔍 Discovering applications...")
    apps = await self.mcp_client.call_tool("discover_applications", ssh_creds)
    write_progress(f"✓ Found {len(apps)} applications:")
    for app in apps:
        write_progress(f"  - {app['name']} {app['version']} (confidence: {app['confidence']})")
    
    # 3. Select validation tools
    write_progress("🔧 Selecting validation tools...")
    tool_selector = ToolSelector()
    selected_tools = tool_selector.select_tools(apps, self.mcp_client.get_available_tools())
    write_progress(f"✓ Selected {len(selected_tools)} validation tools")
    
    # 4. Run validations
    write_progress(f"⚡ Running {len(selected_tools)} validations...")
    results = []
    for tool_info in selected_tools:
        result = await self.mcp_client.call_tool(
            tool_info["tool"],
            {**ssh_creds, "app_info": tool_info["app"]}
        )
        results.append(result)
    
    # 5. Evaluate and report
    write_progress("📊 Evaluating results...")
    report = self.generate_report(os_info, apps, results)
    return report
```

## Implementation Tasks

### Task 1: Create Simplified Conversation Handler ✅
**File:** `conversation_simple.py`
- [x] Only ask for hostname + SSH credentials
- [x] Use LLM to parse natural language input
- [x] Validate required fields
- [x] Support both password and key-based auth

### Task 2: Create Tool Selector
**File:** `tool_selector.py`
- [ ] Map applications to validation tools
- [ ] Filter by available tools
- [ ] Prioritize critical validations
- [ ] Handle unknown applications gracefully

### Task 3: Update Recovery Validation Agent
**File:** `recovery_validation_agent.py`
- [ ] Add `run_mcp_centric_validation()` method
- [ ] Use `discover_applications` MCP tool
- [ ] Integrate tool selector
- [ ] Update `gather_information_interactive()` to use simple conversation

### Task 4: Update Models
**File:** `models.py`
- [ ] Add `DiscoveredApplication` model
- [ ] Add `ToolSelectionResult` model
- [ ] Update `ValidationRequest` to support auto-discovery mode

### Task 5: Create Integration Tests
**File:** `test_mcp_workflow.py`
- [ ] Test simplified conversation
- [ ] Test application discovery
- [ ] Test tool selection
- [ ] Test end-to-end workflow

## Workflow Comparison

### Old Workflow (Weeks 1-2)
```
1. User: "I have an Oracle database"
2. Agent: "What's the hostname?"
3. User: "192.168.1.100"
4. Agent: "What's the SSH username?"
5. User: "oracle"
6. Agent: "What's the SSH password?"
7. User: "secret"
8. Agent: "What's the Oracle username?"
9. User: "system"
10. Agent: "What's the Oracle password?"
11. User: "oracle123"
12. Agent: "What's the service name?"
13. User: "ORCL"
14. Agent: *validates Oracle*
```

### New Workflow (Week 3)
```
1. User: "192.168.1.100, user: oracle, password: secret"
2. Agent: *discovers OS, finds Oracle + MongoDB*
3. Agent: "Found Oracle 19c and MongoDB 6.0, validating both..."
4. Agent: *validates everything automatically*
5. Agent: "Report ready!"
```

**Improvement:** 13 steps → 2 steps (85% reduction)

## Benefits

### 1. User Experience
- **Minimal Input**: Only 3 fields instead of 10+
- **No Technical Knowledge**: Don't need to know what's running
- **Natural Language**: "Connect to server.local as admin"
- **Faster**: 2 minutes instead of 10 minutes

### 2. Accuracy
- **No Human Error**: Can't forget to mention a service
- **Complete Discovery**: Finds everything automatically
- **Confidence Scores**: Knows how certain it is
- **Version Detection**: Automatically detects versions

### 3. Flexibility
- **Works for Any Infrastructure**: VM, Oracle, MongoDB, mixed
- **Handles Unknown Apps**: Gracefully handles unrecognized services
- **Extensible**: Easy to add new application signatures
- **Future-Proof**: New apps automatically discovered

### 4. MCP Best Practices
- **Dynamic Tool Discovery**: Uses `get_available_tools()`
- **Tool-Driven**: MCP tools do the heavy lifting
- **Intelligent Selection**: Only uses relevant tools
- **Efficient**: Parallel execution where possible

## Testing Strategy

### Unit Tests
```python
# Test simplified conversation
async def test_parse_minimal_input():
    handler = SimpleConversationHandler()
    result = await handler.parse_minimal_input(
        "Connect to 192.168.1.100 as admin with password secret"
    )
    assert result["hostname"] == "192.168.1.100"
    assert result["ssh_user"] == "admin"
    assert result["ssh_password"] == "secret"

# Test tool selection
def test_select_tools_for_oracle():
    selector = ToolSelector()
    apps = [{"name": "oracle", "version": "19c"}]
    tools = ["validate_oracle_db", "validate_mongodb", "check_vm_health"]
    selected = selector.select_tools(apps, tools)
    assert "validate_oracle_db" in [t["tool"] for t in selected]
    assert "validate_mongodb" not in [t["tool"] for t in selected]
```

### Integration Tests
```python
# Test end-to-end workflow
async def test_mcp_centric_workflow():
    agent = RecoveryValidationAgent()
    await agent.connect_mcp()
    
    ssh_creds = {
        "hostname": "test-server",
        "username": "admin",
        "password": "secret"
    }
    
    report = await agent.run_mcp_centric_validation(ssh_creds, None)
    
    assert report.discovered_apps is not None
    assert len(report.validation_results) > 0
    assert report.overall_status in ["pass", "fail", "warning"]
```

## Timeline

### Day 1 (2 hours)
- [x] Create `conversation_simple.py`
- [ ] Create `tool_selector.py`
- [ ] Write unit tests

### Day 2 (2 hours)
- [ ] Update `recovery_validation_agent.py`
- [ ] Add `run_mcp_centric_validation()` method
- [ ] Update `gather_information_interactive()`

### Day 3 (1 hour)
- [ ] Integration testing
- [ ] Bug fixes
- [ ] Documentation

### Day 4 (1 hour)
- [ ] Create demo script
- [ ] Record demo video
- [ ] Update README

**Total: 6 hours** (within 4-hour estimate with buffer)

## Success Criteria

- [ ] User can validate infrastructure with only hostname + SSH
- [ ] Agent automatically discovers all applications
- [ ] Tool selection works for Oracle, MongoDB, and VMs
- [ ] End-to-end workflow completes successfully
- [ ] Documentation is complete and clear
- [ ] Demo shows the simplified workflow

## Next Steps (Week 4)

1. **Comprehensive Testing**
   - Test with real Oracle database
   - Test with real MongoDB cluster
   - Test with mixed infrastructure

2. **Performance Optimization**
   - Parallel discovery where possible
   - Cache discovery results
   - Optimize tool execution order

3. **Documentation**
   - User guide with examples
   - Developer guide for adding new apps
   - Troubleshooting guide

4. **Demo Preparation**
   - Create demo environment
   - Write demo script
   - Record demo video

## References

- `WEEK1_SUMMARY.md` - Import fixes and compatibility wrapper
- `WEEK2_SUMMARY.md` - Direct MCPStdioClient integration
- `PHASE3_MCP_BEST_PRACTICES.md` - MCP best practices
- `PHASE4_IMPLEMENTATION_PLAN.md` - Overall implementation plan
- `conversation_simple.py` - Simplified conversation handler