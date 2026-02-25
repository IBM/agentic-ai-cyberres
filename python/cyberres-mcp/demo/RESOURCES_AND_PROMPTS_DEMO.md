# Demonstrating Resources and Prompts in Recovery Validation MCP

## Overview

The Recovery Validation MCP Server provides **3 resources** and **3 prompts** in addition to the 15 validation tools. To make them accessible via Claude, we've added **4 new tools** that expose resources and prompts.

**Total Tools: 19**
- 15 validation tools (network, VM, Oracle, MongoDB)
- 4 resource/prompt access tools (NEW!)

---

## What Are Resources and Prompts?

### Resources
**Resources** are JSON configuration files that define acceptance criteria and thresholds for validation. They allow you to customize what "healthy" means for your infrastructure.

**Available Resources:**
1. `resource://acceptance/vm-core` - VM health thresholds
2. `resource://acceptance/db-oracle` - Oracle database criteria
3. `resource://acceptance/db-mongo` - MongoDB cluster criteria

### Prompts
**Prompts** are markdown templates that guide AI assistants in performing complex validation workflows.

**Available Prompts:**
1. `planner` - Plans validation steps
2. `evaluator` - Evaluates validation results
3. `summarizer` - Generates summary reports

---

## Method 1: Using Claude Desktop (Easiest) ⭐

### New Tools for Accessing Resources and Prompts

We've added 4 new tools that Claude can use:

1. **`list_resources`** - Lists all available acceptance criteria resources
2. **`get_resource`** - Gets the content of a specific resource
3. **`list_prompts`** - Lists all available prompt templates
4. **`get_prompt`** - Gets the content of a specific prompt

### Accessing Resources

**Step 1: List all resources**
```
Use the list_resources tool to show me all available acceptance criteria
```

**Expected Response:**
```json
{
  "ok": true,
  "resources": [
    {
      "uri": "resource://acceptance/vm-core",
      "name": "VM Core Acceptance Criteria",
      "description": "Defines thresholds for Linux VM health validation..."
    },
    {
      "uri": "resource://acceptance/db-oracle",
      "name": "Oracle Database Acceptance Criteria",
      "description": "Defines criteria for Oracle database validation..."
    },
    {
      "uri": "resource://acceptance/db-mongo",
      "name": "MongoDB Acceptance Criteria",
      "description": "Defines criteria for MongoDB cluster validation..."
    }
  ]
}
```

**Step 2: Get a specific resource**
```
Use the get_resource tool to show me the VM acceptance criteria (resource://acceptance/vm-core)
```

**Expected Response:**
```json
{
  "ok": true,
  "uri": "resource://acceptance/vm-core",
  "content": {
    "fs_max_pct": 85,
    "mem_min_free_pct": 10,
    "required_services": ["sshd.service"]
  }
}
```

### Accessing Prompts

**Step 1: List all prompts**
```
Use the list_prompts tool to show me all available prompt templates
```

**Expected Response:**
```json
{
  "ok": true,
  "prompts": [
    {
      "name": "planner",
      "description": "Creates structured validation plans with phases, steps, and time estimates"
    },
    {
      "name": "evaluator",
      "description": "Evaluates validation results against acceptance criteria..."
    },
    {
      "name": "summarizer",
      "description": "Generates executive summaries of validation results..."
    }
  ]
}
```

**Step 2: Get a specific prompt**
```
Use the get_prompt tool to show me the planner prompt template
```

**Expected Response:**
```json
{
  "ok": true,
  "name": "planner",
  "content": "# Validation Planning Prompt\n\nYou are a validation planner..."
}
```

**Step 3: Use the prompt**
```
Now use that planner prompt template to create a validation plan for 3 VMs and 1 Oracle database
```

**What Happens:**
- Claude reads the prompt template
- Applies it to your specific context
- Generates a structured validation plan

---

## Method 2: Using MCP Inspector (For Testing)

### Setup
```bash
cd python/cyberres-mcp
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

Open browser to: http://localhost:5173

### Accessing Resources

1. **Click on "Resources" tab** in the inspector
2. **You'll see 3 resources listed:**
   - `resource://acceptance/vm-core`
   - `resource://acceptance/db-oracle`
   - `resource://acceptance/db-mongo`

3. **Click on any resource** to view its content

**Example: VM Core Resource**
```json
{
  "fs_max_pct": 85,
  "mem_min_free_pct": 10,
  "required_services": ["sshd.service"],
  "load_avg_threshold": 5.0,
  "description": "Core acceptance criteria for Linux VM validation"
}
```

### Accessing Prompts

1. **Click on "Prompts" tab** in the inspector
2. **You'll see 3 prompts listed:**
   - `planner`
   - `evaluator`
   - `summarizer`

3. **Click on any prompt** to view its template

**Example: Planner Prompt**
```markdown
# Validation Planning Prompt

You are a validation planner. Given a validation request, create a detailed plan...
```

---

## Method 3: Direct API Access (Advanced)

### Using Python

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to MCP server
server_params = StdioServerParameters(
    command="uv",
    args=["--directory", "python/cyberres-mcp", "run", "cyberres-mcp"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize
        await session.initialize()
        
        # List resources
        resources = await session.list_resources()
        print("Available resources:", resources)
        
        # Read a specific resource
        vm_core = await session.read_resource("resource://acceptance/vm-core")
        print("VM Core criteria:", vm_core)
        
        # List prompts
        prompts = await session.list_prompts()
        print("Available prompts:", prompts)
        
        # Get a prompt
        planner = await session.get_prompt("planner")
        print("Planner prompt:", planner)
```

### Using cURL (if server exposes HTTP)

```bash
# List resources
curl http://localhost:3000/resources

# Read specific resource
curl http://localhost:3000/resources/acceptance/vm-core

# List prompts
curl http://localhost:3000/prompts

# Get specific prompt
curl http://localhost:3000/prompts/planner
```

---

## Demo Script: Resources

### Demo 1: VM Acceptance Criteria

**Say to Claude:**
```
Show me the VM acceptance criteria and explain what each threshold means
```

**Expected Response:**
```
The VM acceptance criteria includes:

1. fs_max_pct: 85%
   - Maximum filesystem usage allowed
   - If any filesystem exceeds 85%, validation fails
   
2. mem_min_free_pct: 10%
   - Minimum free memory required
   - System must have at least 10% memory available
   
3. required_services: ["sshd.service"]
   - Services that must be running
   - SSH daemon is required for remote access

These thresholds ensure VMs have adequate resources and critical services running.
```

### Demo 2: Oracle Acceptance Criteria

**Say to Claude:**
```
What are the acceptance criteria for Oracle databases?
```

**Expected Response:**
```json
{
  "tablespace_min_free_pct": 15,
  "require_connect": true,
  "max_response_time_ms": 1000,
  "required_status": "OPEN",
  "required_role": "PRIMARY"
}
```

**Explanation:**
- Tablespaces must have at least 15% free space
- Database must be connectable
- Response time under 1 second
- Database must be OPEN and PRIMARY

### Demo 3: MongoDB Acceptance Criteria

**Say to Claude:**
```
Show me the MongoDB acceptance criteria
```

**Expected Response:**
```json
{
  "require_connect": true,
  "replication": {
    "allowed_states": [1, 2],
    "min_healthy_members": 2
  },
  "max_lag_seconds": 10
}
```

**Explanation:**
- Must be able to connect
- Replica set members must be PRIMARY (1) or SECONDARY (2)
- At least 2 healthy members required
- Replication lag must be under 10 seconds

---

## Demo Script: Prompts

### Demo 1: Planner Prompt

**Say to Claude:**
```
Use the planner prompt to create a validation plan for:
- 3 Linux VMs
- 1 Oracle database
- 1 MongoDB replica set
```

**What Happens:**
1. Claude loads the planner prompt template
2. Applies it to your specific infrastructure
3. Generates a structured validation plan

**Expected Output:**
```
Validation Plan:

Phase 1: Network Validation (5 minutes)
- Check connectivity to all 3 VMs
- Verify Oracle port 1521 accessible
- Verify MongoDB ports 27017 accessible

Phase 2: VM Validation (10 minutes)
- VM1: Check uptime, memory, disk, services
- VM2: Check uptime, memory, disk, services
- VM3: Check uptime, memory, disk, services

Phase 3: Database Validation (10 minutes)
- Oracle: Connect, check tablespaces, verify configuration
- MongoDB: Connect, check replica set status, validate collections

Phase 4: Summary (5 minutes)
- Aggregate results
- Identify issues
- Generate report

Total estimated time: 30 minutes
```

### Demo 2: Evaluator Prompt

**Say to Claude:**
```
Use the evaluator prompt to assess these validation results:
[paste some validation results]
```

**What Happens:**
1. Claude loads the evaluator prompt
2. Analyzes the results against acceptance criteria
3. Provides pass/fail assessment with reasoning

**Expected Output:**
```
Validation Assessment:

✅ PASS: Network Connectivity
- All ports accessible
- Latency within acceptable range

⚠️  WARNING: VM Disk Usage
- VM2 filesystem at 87% (threshold: 85%)
- Recommendation: Clean up or expand storage

✅ PASS: Oracle Database
- All tablespaces within limits
- Database operational

❌ FAIL: MongoDB Replica Set
- Only 1 of 3 members healthy
- Replication lag: 45 seconds (threshold: 10s)
- Action required: Investigate replica set issues

Overall Status: FAIL
Critical Issues: 1
Warnings: 1
```

### Demo 3: Summarizer Prompt

**Say to Claude:**
```
Use the summarizer prompt to create an executive summary of the validation
```

**What Happens:**
1. Claude loads the summarizer prompt
2. Creates a concise executive summary
3. Highlights key findings and recommendations

**Expected Output:**
```
EXECUTIVE SUMMARY
Validation Date: 2026-02-05
Infrastructure: 3 VMs, 1 Oracle DB, 1 MongoDB Cluster

OVERALL STATUS: PARTIAL SUCCESS

Key Findings:
✅ Network connectivity verified
✅ Oracle database operational
⚠️  VM storage approaching capacity
❌ MongoDB replica set degraded

Critical Actions Required:
1. Restore MongoDB replica set (Priority: HIGH)
2. Expand VM2 storage (Priority: MEDIUM)

Estimated Recovery Time: 2-4 hours

Recommendation: Address MongoDB issue immediately before declaring DR success.
```

---

## Customizing Resources

### How to Modify Acceptance Criteria

**Location:** `python/cyberres-mcp/src/cyberres_mcp/resources/acceptance/`

**Example: Customize VM Criteria**

Edit `vm-core.json`:
```json
{
  "fs_max_pct": 90,
  "mem_min_free_pct": 15,
  "required_services": [
    "sshd.service",
    "nginx.service",
    "postgresql.service"
  ],
  "load_avg_threshold": 3.0,
  "max_uptime_days": 365
}
```

**After editing:**
1. Restart the MCP server
2. Claude will use the new criteria automatically

### Creating New Resources

**Step 1: Create JSON file**
```bash
cd python/cyberres-mcp/src/cyberres_mcp/resources/acceptance
vi custom-criteria.json
```

**Step 2: Register in server.py**
```python
@app.resource("resource://acceptance/custom-criteria")
def acceptance_custom() -> str:
    try:
        with open(os.path.join(resource_dir, "custom-criteria.json"), "r") as f:
            return f.read()
    except Exception as e:
        logger.error("Failed to load custom-criteria.json", extra={"error": str(e)})
        return "{}"
```

**Step 3: Restart server**
```bash
pkill -f "uv run"
# Restart Claude Desktop
```

---

## Customizing Prompts

### How to Modify Prompts

**Location:** `python/cyberres-mcp/src/cyberres_mcp/prompts/`

**Example: Customize Planner Prompt**

Edit `planner.md`:
```markdown
# Custom Validation Planner

You are an expert validation planner specializing in disaster recovery.

## Your Task
Create a detailed, time-bound validation plan that:
1. Prioritizes critical systems
2. Includes rollback procedures
3. Estimates time for each phase
4. Identifies dependencies

## Output Format
Provide a structured plan with:
- Phase name and duration
- Specific validation steps
- Success criteria
- Rollback procedures if validation fails

## Example
[Your example here]
```

**After editing:**
1. Restart the MCP server
2. Claude will use the new prompt template

---

## Demo Tips

### For Live Demos

1. **Start with Resources**
   - Show how acceptance criteria are defined
   - Explain how they can be customized
   - Demonstrate reading different resources

2. **Move to Prompts**
   - Show how prompts guide AI behavior
   - Demonstrate planner creating a validation plan
   - Show evaluator assessing results
   - Use summarizer for executive summary

3. **Show Integration**
   - Use resources in validation
   - Apply prompts to real scenarios
   - Demonstrate end-to-end workflow

### Key Points to Emphasize

✅ **Flexibility** - Resources can be customized per environment  
✅ **Consistency** - Same criteria applied everywhere  
✅ **Intelligence** - Prompts guide AI for complex tasks  
✅ **Automation** - No manual interpretation needed  
✅ **Auditability** - Criteria and logic are documented  

---

## Troubleshooting

### Resources Not Showing

**Problem:** Claude says "No resources available"

**Solution:**
```bash
# Check files exist
ls python/cyberres-mcp/src/cyberres_mcp/resources/acceptance/

# Restart MCP server
pkill -f "uv run"
# Restart Claude Desktop
```

### Prompts Not Working

**Problem:** Claude doesn't use the prompt template

**Solution:**
```bash
# Check files exist
ls python/cyberres-mcp/src/cyberres_mcp/prompts/

# Verify prompt registration in server.py
grep "@app.prompt" python/cyberres-mcp/src/cyberres_mcp/server.py

# Restart server
```

### Can't Modify Resources

**Problem:** Changes to JSON files not reflected

**Solution:**
1. Save the file
2. Restart MCP server (kill and restart Claude Desktop)
3. Resources are loaded at server startup

---

## Summary

### Resources Provide:
- ✅ Customizable acceptance criteria
- ✅ Environment-specific thresholds
- ✅ Consistent validation standards
- ✅ Easy to modify without code changes

### Prompts Provide:
- ✅ Structured AI guidance
- ✅ Complex workflow orchestration
- ✅ Consistent output format
- ✅ Reusable templates

### Together They Enable:
- ✅ Intelligent, automated validation
- ✅ Customizable per environment
- ✅ Consistent, repeatable processes
- ✅ AI-powered analysis and reporting

---

**Next Steps:**
1. Try accessing resources via Claude
2. Experiment with different prompts
3. Customize criteria for your environment
4. Create custom resources and prompts as needed
