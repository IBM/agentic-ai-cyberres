# 🧪 Quick Start - Test Dynamic Tool Discovery

## How to Test from CLI

### Step 1: Start MCP Server (Terminal 1)

```bash
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

Keep this running.

### Step 2: Run Test Script (Terminal 2)

```bash
cd python/src
python test_tool_discovery.py
```

---

## What You'll See

### Expected Output

```
================================================================================
🚀 MCP BEST PRACTICES - Dynamic Tool Discovery Test
================================================================================

This test demonstrates Phase 3 enhancement:
  • MCP client discovers tools dynamically at runtime
  • Agent can query available tools
  • Agent checks tool availability before calling
  • No hardcoded tool names!

================================================================================
🧪 TESTING DYNAMIC TOOL DISCOVERY - MCP Best Practices
================================================================================

📡 Step 1: Initializing MCP client...

🔌 Step 2: Connecting to MCP server...
   ✅ Connected successfully!

🔍 Step 3: Querying discovered tools...

✅ Discovered 15 MCP tools:
--------------------------------------------------------------------------------

📦 Discovery Tools:
   • discover_os_only
     Perform OS detection only (fast, lightweight)...
   • discover_applications
     Discover enterprise applications on a target server...
   • get_raw_server_data
     Get raw server data for agent-side LLM processing...

✅ Validation Tools:
   • validate_vm_linux
     Validate Linux VM health and configuration...
   • validate_oracle_db
     Validate Oracle database connectivity and health...
   • validate_mongodb
     Validate MongoDB cluster health and replica status...

🌐 Network Tools:
   • check_network_connectivity
     Check network connectivity to a host...
   • check_port_open
     Check if a specific port is open...
   • tcp_portcheck
     Check TCP port connectivity...

🔧 Utility Tools:
   • server_health
     Check MCP server health and list available capabilities...

================================================================================
🧪 Step 4: Testing tool availability checking...
--------------------------------------------------------------------------------
   discover_applications: ✅ Available
   discover_os_only: ✅ Available
   validate_oracle_db: ✅ Available
   validate_mongodb: ✅ Available
   validate_vm_linux: ✅ Available
   nonexistent_tool: ❌ Not Available

================================================================================
💡 Step 5: Demonstrating usage pattern...
--------------------------------------------------------------------------------

📝 Example: How an agent would use this

# Agent checks if tool exists before calling
if mcp_client.has_tool("discover_applications"):
    result = await mcp_client.call_tool("discover_applications", {
        "host": "db-server-01",
        "ssh_user": "admin",
        "ssh_password": "secret"
    })
    # Process result...
else:
    # Fallback to alternative method
    print("Tool not available, using fallback...")

================================================================================
✅ TEST COMPLETE - Dynamic Tool Discovery Working!
================================================================================

📊 Summary:
   • Total tools discovered: 15
   • Discovery tools: 3
   • Validation tools: 3
   • Network tools: 3
   • Utility tools: 1

🎯 Key Benefits:
   ✅ No hardcoded tool names
   ✅ Agent adapts to available tools
   ✅ Graceful handling of missing tools
   ✅ Easy to add new tools to MCP server

📚 Next Steps:
   1. Update agents to use get_available_tools()
   2. Add tool selection logic based on classification
   3. Test complete workflow with real server

🔌 Disconnecting from MCP server...
   ✅ Disconnected

================================================================================
🎉 SUCCESS! Dynamic tool discovery is working!
================================================================================

The MCP client now:
  ✅ Discovers tools automatically on connection
  ✅ Provides get_available_tools() method
  ✅ Provides has_tool(name) method
  ✅ Provides get_tool_description(name) method

Agents can now adapt to available tools dynamically!
================================================================================
```

---

## What This Tests

### 1. **Dynamic Tool Discovery**
- MCP client connects to server
- Automatically discovers all available tools
- Stores tools in memory for querying

### 2. **Tool Querying**
- `get_available_tools()` - List all tools
- `has_tool(name)` - Check if tool exists
- `get_tool_description(name)` - Get tool documentation

### 3. **Tool Categorization**
- Discovery tools (discover_applications, etc.)
- Validation tools (validate_oracle_db, etc.)
- Network tools (check_port_open, etc.)
- Utility tools (server_health, etc.)

### 4. **Usage Pattern**
- Shows how agents should check tool availability
- Demonstrates graceful handling of missing tools
- Provides example code

---

## Troubleshooting

### Issue: MCP Server Not Running

```
❌ Error: Error connecting to MCP server

Solution:
Terminal 1:
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Issue: Import Errors

```
❌ Error: Module not found

Solution:
cd python/src
uv pip install -r requirements.txt
```

### Issue: Connection Timeout

```
❌ Error: Connection timeout

Solution:
1. Check MCP server is running
2. Check server path in test script
3. Increase timeout in MCPStdioClient
```

---

## Next: Test Complete Workflow

After verifying tool discovery works, test the complete workflow:

```bash
cd python/src
python main.py
```

Then enter:
```
You: Validate db-server-01
Agent: SSH Username?
You: admin
Agent: SSH Password?
You: ********
```

The agent will use the discovered tools automatically!

---

## Summary

**This test verifies**:
✅ MCP client can connect to server  
✅ Tools are discovered dynamically  
✅ Tool querying methods work  
✅ Tool availability checking works  
✅ Phase 3 MCP best practices implemented  

**Run it now**:
```bash
python test_tool_discovery.py
```

---

*Made with Bob - AI Assistant*