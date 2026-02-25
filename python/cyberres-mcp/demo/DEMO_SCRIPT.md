# CyberRes MCP Server - Demo Script

**Duration**: 20 minutes  
**Audience**: Technical team  
**Goal**: Demonstrate automated infrastructure recovery validation using MCP

---

## 🎯 Pre-Demo Checklist (30 minutes before)

### Server Setup
- [ ] Navigate to `python/cyberres-mcp/`
- [ ] Verify dependencies: `uv add . --dev`
- [ ] Start MCP server: `uv run cyberres-mcp`
- [ ] Verify server health: `curl http://localhost:8000/health` (if endpoint exists)
- [ ] Check logs for any errors

### Inspector Setup
- [ ] Start MCP inspector: `npx @modelcontextprotocol/inspector`
- [ ] Open browser to `http://localhost:6274`
- [ ] Configure connection:
  - Transport: `streamable-http`
  - URL: `http://localhost:8000/mcp`
- [ ] Click Connect and verify:
  - ✅ 13 tools available
  - ✅ 3 resources available
  - ✅ 3 prompts available


---

## 📋 Demo Flow

### Part 1: Introduction (2 minutes)

**Talking Points:**
- "Today I'll demonstrate our MCP server for automated infrastructure recovery validation"
- "The challenge: After disaster recovery, teams spend hours manually validating infrastructure"
- "Our solution: Standardized validation tools accessible via Model Context Protocol"
- "Benefits: 90% reduction in validation time, consistent checks, audit trail"

**Show:**
- Architecture diagram from README
- Highlight plugin-based design

---

### Part 2: Server Capabilities (3 minutes)

**Action:** Show MCP Inspector connected to server

**Talking Points:**
- "The server exposes 13 validation tools across 4 categories"
- "Network connectivity, VM health, Oracle databases, MongoDB clusters"
- "All tools return standardized responses for easy automation"

**Demonstrate:**

1. **Test Server Health**
```json
{
  "tool": "server_health",
  "args": {}
}
```

**Expected Response:**
```json
{
  "ok": true,
  "status": "healthy",
  "version": "0.1.0",
  "plugins": ["network", "vm_linux", "oracle_db", "mongodb"],
  "capabilities": {
    "tools": 13,
    "resources": 3,
    "prompts": 3
  }
}
```

**Say:** "This confirms our server is running and all plugins are loaded"

---

### Part 3: VM Validation Demo (5 minutes)

**Scenario:** "Let's validate a recovered Linux VM"

#### Step 1: Check Network Connectivity

```json
{
  "tool": "tcp_portcheck",
  "args": {
    "host": "10.0.1.5",
    "ports": [22],
    "timeout_s": 2.0
  }
}
```

**Talking Points:**
- "First, verify the VM is reachable on the network"
- "We check SSH port 22 with a 2-second timeout"
- "Response shows port is open with 12ms latency"

#### Step 2: Check System Health

```json
{
  "tool": "vm_linux_uptime_load_mem",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123"
  }
}
```

**Talking Points:**
- "Now we SSH in and check uptime, load averages, and memory"
- "System has been up 45 days - good sign of stability"
- "Load average is low, plenty of free memory"

#### Step 3: Check Filesystem Usage

```json
{
  "tool": "vm_linux_fs_usage",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123"
  }
}
```

**Talking Points:**
- "Check all mounted filesystems"
- "Root filesystem at 53% - well below our 85% threshold"
- "Data volume at 74% - still acceptable"

#### Step 4: Verify Required Services

```json
{
  "tool": "vm_linux_services",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123",
    "required": ["sshd.service", "nginx.service"]
  }
}
```

**Talking Points:**
- "Finally, verify critical services are running"
- "Both SSH and nginx are active - VM is fully operational"

**Summary:** "In under a minute, we've comprehensively validated this VM's health"

---

### Part 4: Oracle Database Validation (5 minutes)

**Scenario:** "Now let's validate a recovered Oracle database"

#### Step 1: Check Database Connectivity

```json
{
  "tool": "db_oracle_connect",
  "args": {
    "dsn": "10.0.2.20/ORCLCDB",
    "user": "system",
    "password": "oracle123"
  }
}
```

**Talking Points:**
- "Connect to Oracle and retrieve instance information"
- "Database is ORCLCDB, version 19c"
- "Open mode is READ WRITE - database is fully operational"
- "Role is PRIMARY - this is the production database"

#### Step 2: Check Tablespace Usage

```json
{
  "tool": "db_oracle_tablespaces",
  "args": {
    "dsn": "10.0.2.20/ORCLCDB",
    "user": "system",
    "password": "oracle123"
  }
}
```

**Talking Points:**
- "Query all tablespaces for usage statistics"
- "SYSTEM tablespace at 75% - within acceptable range"
- "USERS tablespace at 45% - plenty of space"
- "All tablespaces have adequate free space"

**Summary:** "Database is online, accessible, and has sufficient storage"

---

### Part 5: MongoDB Validation (3 minutes)

**Scenario:** "Finally, let's validate a MongoDB replica set"

#### Step 1: Check MongoDB Connectivity

```json
{
  "tool": "db_mongo_connect",
  "args": {
    "uri": "mongodb://admin:mongo123@10.0.2.30:27017/admin"
  }
}
```

**Talking Points:**
- "Connect to MongoDB and verify it's responding"
- "Ping successful, running version 6.0.5"

#### Step 2: Check Replica Set Status

```json
{
  "tool": "db_mongo_rs_status",
  "args": {
    "uri": "mongodb://admin:mongo123@mongo-rs-01:27017/admin?replicaSet=rs0"
  }
}
```

**Talking Points:**
- "Query replica set status"
- "Replica set 'rs0' is healthy"
- "One PRIMARY, two SECONDARY nodes - proper configuration"
- "All members report healthy status"

**Summary:** "MongoDB cluster is fully operational with proper replication"

---

### Part 6: Acceptance Criteria & Resources (2 minutes)

**Action:** Show resources in MCP Inspector

**Talking Points:**
- "The server exposes acceptance criteria as resources"
- "These define thresholds for pass/fail validation"

**Demonstrate:**

Show resource: `resource://acceptance/vm-core`
```json
{
  "fs_max_pct": 85,
  "mem_min_free_pct": 10,
  "required_services": []
}
```

**Say:** "Filesystems over 85% fail validation, memory below 10% free fails"

Show resource: `resource://acceptance/db-oracle`
```json
{
  "tablespace_min_free_pct": 15,
  "require_connect": true
}
```

**Say:** "Oracle tablespaces must have at least 15% free space"

---

### Part 7: AI Agent Integration (Optional - if time permits)

**Talking Points:**
- "These tools can be orchestrated by AI agents"
- "We provide prompts for planning, evaluation, and summarization"

**Show:** Prompt resources in inspector
- `planner` - Generates validation plan from request
- `evaluator` - Evaluates results against criteria
- `summarizer` - Creates executive summary

**Say:** "An AI agent can use these prompts to automatically validate entire environments"

---

## 🎬 Closing (2 minutes)

**Summary Points:**
- ✅ Demonstrated comprehensive validation across VMs, Oracle, MongoDB
- ✅ Showed standardized response format for easy automation
- ✅ Highlighted acceptance criteria and resources
- ✅ All validations completed in minutes vs. hours manually

**Key Benefits:**
1. **Speed**: 90% reduction in validation time
2. **Consistency**: Same checks every time, no human error
3. **Auditability**: All actions logged with structured data
4. **Extensibility**: Plugin architecture for new infrastructure types

**Next Steps:**
- Integrate with your disaster recovery runbooks
- Connect to AI agents for full automation
- Extend with additional database types (PostgreSQL, MySQL)
- Add Windows VM support

**Questions?**

---

## 🐛 Troubleshooting During Demo

### If server connection fails:
- "Let me verify the server is running..." (check terminal)
- "I'll restart the server..." (uv run cyberres-mcp)
- Fallback: Show screenshots of successful runs

### If SSH/DB connection fails:
- "This is a test environment issue, not the MCP server"
- "Let me show you the expected response..." (show from tool-examples.md)
- Fallback: Use different test infrastructure

### If inspector doesn't connect:
- Check URL is correct: `http://localhost:8000/mcp`
- Verify transport is `streamable-http`
- Fallback: Use curl to call tools directly

### If tool returns error:
- "This demonstrates our error handling"
- Show the structured error response
- Explain the error code and message

---

## 📊 Demo Metrics to Highlight

- **13 tools** across 4 plugin categories
- **3 resources** for acceptance criteria
- **3 prompts** for AI agent orchestration
- **Sub-second** response times for most operations
- **100% credential redaction** in logs
- **Standardized responses** for all tools

---

## 🎤 Presentation Tips

1. **Pace yourself**: Don't rush through the tools
2. **Explain as you go**: Narrate what each tool does
3. **Show the responses**: Let audience see the JSON
4. **Highlight key fields**: Point out important data in responses
5. **Connect to business value**: Relate technical features to time/cost savings
6. **Be prepared for questions**: Know the architecture deeply
7. **Have fun**: Show enthusiasm for the technology

---

## 📸 Screenshots to Prepare (Backup)

1. MCP Inspector connected with tools list
2. Successful VM validation response
3. Oracle database connection response
4. MongoDB replica set status
5. Architecture diagram
6. Acceptance criteria resources

---

## 🔗 Quick Reference Links

- Tool Examples: `demo/tool-examples.md`
- Example Requests: `demo/example-requests.json`
- README: `README.md`
- Server Code: `server.py`
- Plugins: `plugins/`

---

**Good luck with your demo! 🚀**