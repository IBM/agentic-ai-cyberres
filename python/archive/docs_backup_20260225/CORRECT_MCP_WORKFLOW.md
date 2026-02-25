# ✅ Correct MCP-Based Agentic Workflow

## The Right Way: Dynamic Tool Discovery

### Key Principle
**The agent should discover available MCP tools dynamically at runtime, not hardcode them.**

---

## Correct Workflow

### 1. User Input (Minimal)
```
User provides:
  - Hostname/IP: "db-server-01"
  - SSH Username: "admin"
  - SSH Password: "secret123"
```

### 2. Agent Discovers MCP Tools (Automatic)
```python
# Agent connects to MCP server
mcp_client.connect()

# Agent discovers available tools dynamically
available_tools = await mcp_client.list_tools()

# Agent sees:
# - discover_os_only
# - discover_applications
# - get_raw_server_data
# - validate_vm_linux
# - validate_oracle_db
# - validate_mongodb
# - etc.
```

### 3. Agent Uses Tools Intelligently (Automatic)
```
Agent workflow:
  1. Call discover_os_only(host, ssh_user, ssh_password)
     → Detects: Linux, Ubuntu 20.04
  
  2. Call discover_applications(host, ssh_user, ssh_password)
     → Detects: Oracle Database 19c, Oracle EM
  
  3. Agent classifies: "This is an Oracle Database Server"
  
  4. Agent selects validation tools:
     - validate_oracle_db (found in available tools)
     - validate_vm_linux (for OS checks)
  
  5. Call validate_oracle_db(host, ...)
     → Runs Oracle-specific validations
  
  6. Call validate_vm_linux(host, ...)
     → Runs OS-level validations
  
  7. Generate report with AI evaluation
```

---

## MCP Best Practices

### ✅ DO: Dynamic Tool Discovery

```python
class AgenticWorkflow:
    async def initialize(self):
        # Connect to MCP server
        await self.mcp_client.connect()
        
        # Discover available tools dynamically
        self.available_tools = await self.mcp_client.list_tools()
        
        # Agent now knows what tools it can use
        logger.info(f"Discovered {len(self.available_tools)} MCP tools")
    
    async def execute(self, host, ssh_user, ssh_password):
        # 1. Discover what's on the server
        if "discover_applications" in self.available_tools:
            apps = await self.mcp_client.call_tool(
                "discover_applications",
                {
                    "host": host,
                    "ssh_user": ssh_user,
                    "ssh_password": ssh_password
                }
            )
        
        # 2. Classify based on discoveries
        classification = self.classify(apps)
        
        # 3. Select appropriate validation tools
        validation_tools = self.select_validation_tools(
            classification,
            self.available_tools  # Use discovered tools
        )
        
        # 4. Execute validations
        for tool in validation_tools:
            result = await self.mcp_client.call_tool(tool, {...})
```

### ❌ DON'T: Hardcode Tool Names

```python
# BAD: Hardcoded tool names
async def execute(self, host):
    # What if tool doesn't exist?
    # What if tool name changes?
    result = await self.mcp_client.call_tool(
        "validate_oracle_db",  # Hardcoded!
        {...}
    )
```

---

## Complete Workflow Example

### User Experience

```
🤖 Agent: Hello! I can validate any server. Just provide SSH credentials.

👤 User: Validate db-server-01

🤖 Agent: I'll need SSH credentials to access db-server-01.
          SSH Username: 

👤 User: admin

🤖 Agent: SSH Password: 

👤 User: ********

🤖 Agent: Got it! Starting validation...

          [Agent automatically:]
          ✅ Connected to MCP server
          ✅ Discovered 15 available tools
          ✅ Discovering OS... Found: Linux Ubuntu 20.04
          ✅ Discovering applications... Found: Oracle Database 19c, Oracle EM
          ✅ Classification: Oracle Database Server (95% confidence)
          ✅ Selected validation tools: validate_oracle_db, validate_vm_linux
          ✅ Running Oracle validations... 11 checks passed
          ✅ Running VM validations... 8 checks passed
          ✅ AI Evaluation: HEALTHY, LOW risk
          ✅ Report generated: validation_report_db-server-01.md

          Validation complete! Score: 92/100
```

---

## Architecture

### MCP-Centric Design

```
User Input (host + SSH creds)
         ↓
    Agent Starts
         ↓
Connect to MCP Server
         ↓
Discover Available Tools (list_tools)
         ↓
Call: discover_os_only(host, user, pass)
         ↓
Call: discover_applications(host, user, pass)
         ↓
AI Classification (based on discoveries)
         ↓
Select Validation Tools (from discovered tools)
         ↓
Execute Validations (call selected tools)
         ↓
AI Evaluation (analyze results)
         ↓
Generate Report
         ↓
Present Results to User
```

---

## Key Benefits

### 1. **Flexibility**
- MCP server can add new tools
- Agent automatically discovers and uses them
- No code changes needed in agent

### 2. **Robustness**
- Agent checks if tool exists before calling
- Graceful handling of missing tools
- Fallback strategies

### 3. **Scalability**
- Add new resource types (Kubernetes, Docker, etc.)
- Just add tools to MCP server
- Agent adapts automatically

### 4. **Maintainability**
- Single source of truth (MCP server)
- No hardcoded tool names
- Easy to update and extend

---

## Implementation Pattern

### Phase 1: Tool Discovery

```python
class MCPAwareAgent:
    def __init__(self):
        self.mcp_client = None
        self.available_tools = {}
        self.tool_descriptions = {}
    
    async def initialize(self):
        """Connect and discover tools."""
        await self.mcp_client.connect()
        
        # Get all available tools
        tools_response = await self.mcp_client.list_tools()
        
        for tool in tools_response:
            self.available_tools[tool.name] = tool
            self.tool_descriptions[tool.name] = tool.description
        
        logger.info(f"Discovered tools: {list(self.available_tools.keys())}")
```

### Phase 2: Intelligent Tool Selection

```python
    def select_discovery_tools(self):
        """Select tools for discovery phase."""
        discovery_tools = []
        
        # Look for OS discovery
        if "discover_os_only" in self.available_tools:
            discovery_tools.append("discover_os_only")
        
        # Look for application discovery
        if "discover_applications" in self.available_tools:
            discovery_tools.append("discover_applications")
        elif "get_raw_server_data" in self.available_tools:
            # Fallback to raw data collection
            discovery_tools.append("get_raw_server_data")
        
        return discovery_tools
    
    def select_validation_tools(self, classification):
        """Select validation tools based on classification."""
        validation_tools = []
        
        # Match classification to available tools
        if classification.category == "DATABASE_SERVER":
            if classification.primary_app == "Oracle":
                if "validate_oracle_db" in self.available_tools:
                    validation_tools.append("validate_oracle_db")
            elif classification.primary_app == "MongoDB":
                if "validate_mongodb" in self.available_tools:
                    validation_tools.append("validate_mongodb")
        
        # Always add VM validation if available
        if "validate_vm_linux" in self.available_tools:
            validation_tools.append("validate_vm_linux")
        
        return validation_tools
```

### Phase 3: Tool Execution

```python
    async def execute_tool(self, tool_name, args):
        """Execute tool with error handling."""
        if tool_name not in self.available_tools:
            logger.warning(f"Tool {tool_name} not available")
            return None
        
        try:
            result = await self.mcp_client.call_tool(tool_name, args)
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return None
```

---

## MCP Server Tools (Auto-Discovered)

The agent discovers these tools at runtime:

### Discovery Tools
- **`discover_os_only`** - Fast OS detection
- **`discover_applications`** - Application discovery
- **`get_raw_server_data`** - Raw data for LLM analysis

### Validation Tools
- **`validate_vm_linux`** - Linux VM validation
- **`validate_oracle_db`** - Oracle database validation
- **`validate_mongodb`** - MongoDB validation
- **`check_network_connectivity`** - Network checks
- **`check_port_open`** - Port connectivity

### Utility Tools
- **`server_health`** - MCP server health check

---

## Agent Intelligence

### The agent uses AI to:

1. **Parse user intent**
   - "Validate db-server-01" → Extract hostname
   - Ask for missing credentials

2. **Interpret discoveries**
   - OS: Linux + Apps: Oracle → "Database Server"
   - Confidence scoring

3. **Select appropriate tools**
   - Database Server → Use `validate_oracle_db`
   - Web Server → Use `validate_web_server`

4. **Evaluate results**
   - Analyze validation results
   - Identify key findings
   - Generate recommendations

5. **Generate reports**
   - Executive summary
   - Technical details
   - Actionable recommendations

---

## Summary

### ✅ Correct Approach

**User provides**: Hostname + SSH credentials  
**Agent discovers**: Available MCP tools dynamically  
**Agent uses**: Discovered tools to discover, classify, validate  
**Agent generates**: Professional report with AI insights  

### Key Principles

1. **Dynamic Tool Discovery** - Use `list_tools()` at runtime
2. **Minimal User Input** - Only hostname + SSH credentials
3. **Automatic Discovery** - MCP tools discover everything else
4. **Intelligent Classification** - AI determines resource type
5. **Smart Tool Selection** - Choose validation tools based on classification
6. **AI-Powered Evaluation** - Analyze results and generate insights

---

## Next Steps

The existing codebase already has most of this implemented! The key improvements needed:

1. **Add dynamic tool discovery** to agent initialization
2. **Use discovered tools** instead of hardcoded names
3. **Simplify user input** to just hostname + SSH credentials
4. **Let MCP tools do the discovery** (they already can!)
5. **Agent focuses on** orchestration, classification, evaluation

---

*This is the correct MCP-based agentic workflow!*