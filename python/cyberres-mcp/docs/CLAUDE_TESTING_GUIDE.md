# Testing MCP Server with Claude Desktop - Step-by-Step Guide

This guide provides exact steps to test your MCP server with Claude Desktop.

---

## 📋 Pre-Test Checklist

Before starting, ensure:
- [ ] Claude Desktop is installed
- [ ] `uv` is installed at `/Users/himanshusharma/.local/bin/uv`
- [ ] MCP server code is at `/Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp`
- [ ] You have test infrastructure accessible (or will use mock data)

---

## 🚀 Step 1: Configure Claude Desktop

### 1.1 Open Claude Desktop Config File

```bash
# Open the config file in your editor
code ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or use nano
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 1.2 Add MCP Server Configuration

Replace the entire contents with:

```json
{
  "mcpServers": {
    "cyberres-recovery-validation": {
      "command": "/Users/himanshusharma/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp",
        "run",
        "cyberres-mcp"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "SECRETS_FILE": "demo-secrets.json",
        "ENVIRONMENT": "demo"
      }
    }
  }
}
```

### 1.3 Save and Close

- Save the file (Cmd+S in VS Code, Ctrl+O then Enter in nano)
- Close the editor

---

## 🔄 Step 2: Restart Claude Desktop

### 2.1 Quit Claude Desktop Completely

```bash
# Option 1: Use keyboard shortcut
# Press Cmd+Q while Claude Desktop is active

# Option 2: Use terminal
killall Claude
```

### 2.2 Wait 2-3 Seconds

Give the system time to fully close the application.

### 2.3 Relaunch Claude Desktop

- Open Claude Desktop from Applications folder
- Or use Spotlight: Cmd+Space, type "Claude", press Enter

---

## ✅ Step 3: Verify Connection

### 3.1 Check for MCP Indicator

Look for the **hammer icon (🔨)** in Claude Desktop:
- Usually appears in the bottom-left or near the input box
- Indicates MCP tools are available

### 3.2 Check Server Logs (Optional)

```bash
# View Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

Look for:
- ✅ "Server started and connected successfully"
- ✅ No "Failed to spawn process" errors

---

## 🧪 Step 4: Test Basic Functionality

### Test 1: Discover Available Tools

**Ask Claude:**
```
What MCP tools are available?
```

**Expected Response:**
Claude should list approximately 13 tools including:
- server_health
- tcp_portcheck
- vm_linux_uptime_load_mem
- vm_linux_fs_usage
- vm_linux_services
- db_oracle_connect
- db_oracle_tablespaces
- db_mongo_connect
- db_mongo_rs_status
- And more...

---

### Test 2: Check Server Health

**Ask Claude:**
```
Can you check the health of the recovery validation server?
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

Claude should confirm the server is healthy and show the capabilities.

---

### Test 3: Test Network Connectivity Tool

**Ask Claude:**
```
Can you check if port 22 is open on host 10.0.1.5?
```

**Expected Response:**
Claude will call `tcp_portcheck` and report whether the port is reachable.

---

## 🎯 Step 5: Test with Configured Credentials

### Test 4: VM Validation (Using Configured Credentials)

**Ask Claude:**
```
Please validate the demo VM using the configured credentials. 
Check system health, disk usage, and verify that sshd is running.
```

**What Claude Will Do:**
1. Use credentials from `demo-secrets.json` (demo environment)
2. Call `vm_linux_uptime_load_mem` to check system health
3. Call `vm_linux_fs_usage` to check disk space
4. Call `vm_linux_services` to verify sshd is running
5. Provide a comprehensive summary

**Expected Response:**
Claude will provide a summary like:
```
I've validated the demo VM at 10.0.1.5:

✅ System Health:
- Uptime: 45 days
- Load average: 0.15, 0.20, 0.18
- Memory: 8GB free out of 16GB total (50% free)

✅ Disk Usage:
- Root filesystem: 53% used (within 85% threshold)
- Data volume: 74% used (acceptable)

✅ Services:
- sshd.service: Active and running

Overall: VM is healthy and operational.
```

---

### Test 5: Oracle Database Validation

**Ask Claude:**
```
Please validate the demo Oracle database. 
Check connectivity and tablespace usage.
```

**What Claude Will Do:**
1. Use Oracle credentials from `demo-secrets.json`
2. Call `db_oracle_connect` to verify connectivity
3. Call `db_oracle_tablespaces` to check space usage
4. Summarize the results

**Expected Response:**
```
I've validated the demo Oracle database:

✅ Connectivity:
- Instance: ORCLCDB
- Version: 19.0.0.0.0
- Open Mode: READ WRITE
- Role: PRIMARY

✅ Tablespace Usage:
- SYSTEM: 75% used, 512MB free
- SYSAUX: 68% used, 1024MB free
- USERS: 45% used, 2048MB free

All tablespaces have adequate free space (>15% threshold).
Database is healthy and operational.
```

---

### Test 6: MongoDB Validation

**Ask Claude:**
```
Please validate the demo MongoDB instance. 
Check connectivity and replica set status if applicable.
```

**What Claude Will Do:**
1. Use MongoDB credentials from `demo-secrets.json`
2. Call `db_mongo_connect` to verify connectivity
3. Optionally call `db_mongo_rs_status` if it's a replica set
4. Summarize the results

---

### Test 7: Comprehensive Multi-Resource Validation

**Ask Claude:**
```
Please perform a comprehensive validation of our demo infrastructure:

1. VM at the configured host
   - System health (uptime, memory, disk)
   - Verify sshd and nginx services

2. Oracle database
   - Connectivity test
   - Tablespace usage

3. MongoDB
   - Connectivity test
   - Replica set status

Use the demo environment credentials that are configured.
Provide an executive summary with pass/fail status for each component.
```

**What Claude Will Do:**
1. Validate all three components systematically
2. Use credentials from `demo-secrets.json` automatically
3. Chain multiple tool calls
4. Provide comprehensive executive summary

**Expected Response:**
```
Infrastructure Validation Report - Demo Environment

Executive Summary:
✅ VM: PASS - System healthy, all services running
✅ Oracle: PASS - Database accessible, adequate space
✅ MongoDB: PASS - Connected successfully

Detailed Results:

1. VM (10.0.1.5):
   ✅ Uptime: 45 days, 3 hours
   ✅ Memory: 50% free (8GB/16GB)
   ✅ Disk: Root 53%, Data 74% (within thresholds)
   ✅ Services: sshd ✓, nginx ✓

2. Oracle Database (ORCLCDB):
   ✅ Status: PRIMARY, READ WRITE
   ✅ Version: 19c
   ✅ Tablespaces: All >15% free
   
3. MongoDB (10.0.2.30):
   ✅ Connectivity: Successful
   ✅ Version: 6.0.5
   ✅ Ping: OK

Overall Status: ALL SYSTEMS OPERATIONAL ✅
```

---

## 🐛 Troubleshooting

### Issue 1: Tools Not Appearing

**Symptoms:**
- No hammer icon in Claude Desktop
- Claude says "I don't have access to those tools"

**Solutions:**

1. **Check config file location:**
   ```bash
   ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Verify config syntax:**
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python3 -m json.tool
   ```
   Should show no errors.

3. **Check Claude Desktop logs:**
   ```bash
   tail -50 ~/Library/Logs/Claude/mcp*.log
   ```

4. **Restart Claude Desktop again:**
   ```bash
   killall Claude && sleep 2 && open -a Claude
   ```

---

### Issue 2: "Failed to spawn process"

**Symptoms:**
- Error in logs: "Failed to spawn process: No such file or directory"

**Solutions:**

1. **Verify uv path:**
   ```bash
   which uv
   # Should show: /Users/himanshusharma/.local/bin/uv
   ```

2. **Update config with correct path:**
   Edit `claude_desktop_config.json` and use the full path from `which uv`

3. **Test uv command manually:**
   ```bash
   /Users/himanshusharma/.local/bin/uv --version
   ```

---

### Issue 3: "No credentials configured"

**Symptoms:**
- Tools fail with "No credentials configured for environment 'demo'"

**Solutions:**

1. **Verify secrets file exists:**
   ```bash
   ls -la /Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp/demo-secrets.json
   ```

2. **Check secrets file content:**
   ```bash
   cat /Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp/demo-secrets.json | python3 -m json.tool
   ```

3. **Verify SECRETS_FILE env var in config:**
   Should be: `"SECRETS_FILE": "demo-secrets.json"`

---

### Issue 4: Connection Timeout

**Symptoms:**
- Tools timeout when trying to connect to infrastructure

**Solutions:**

1. **Verify target hosts are accessible:**
   ```bash
   ping -c 3 10.0.1.5
   telnet 10.0.1.5 22
   ```

2. **Update demo-secrets.json with accessible hosts:**
   Use hosts you can actually reach for testing

3. **Use mock/test infrastructure:**
   Set up local test VMs or databases

---

## 📊 Success Criteria

Your MCP server is working correctly if:

- ✅ Claude Desktop shows hammer icon (🔨)
- ✅ Claude can list all 13 tools
- ✅ `server_health` tool returns healthy status
- ✅ Network tools (tcp_portcheck) work
- ✅ VM tools can connect (or fail gracefully with clear errors)
- ✅ Database tools can connect (or fail gracefully)
- ✅ Credentials are loaded from demo-secrets.json
- ✅ No plain text credentials needed in requests

---

## 🎬 Demo Script for Presentation

### Opening (1 minute)

**Say to audience:**
"I'll demonstrate our MCP server integrated with Claude Desktop. Claude can discover and use all our validation tools through natural language."

**Show in Claude:**
```
What validation tools are available in the recovery validation server?
```

### Demo 1: Server Health (1 minute)

**Say to Claude:**
```
Can you check the health of the recovery validation server?
```

**Highlight to audience:**
"Notice how Claude automatically calls the server_health tool and interprets the results."

### Demo 2: VM Validation (3 minutes)

**Say to Claude:**
```
Please validate the demo VM. Check system health, disk usage, and verify that sshd and nginx are running. Use the configured demo credentials.
```

**Highlight to audience:**
- "Claude automatically uses credentials from our secure config file"
- "No plain text passwords in the conversation"
- "Claude chains multiple validation tools"
- "Provides intelligent summary of results"

### Demo 3: Database Validation (2 minutes)

**Say to Claude:**
```
Now validate the demo Oracle database. Check connectivity and tablespace usage.
```

**Highlight to audience:**
- "Same secure credential approach"
- "Claude interprets database-specific metrics"
- "Identifies potential issues automatically"

### Demo 4: Comprehensive Validation (3 minutes)

**Say to Claude:**
```
Please perform a comprehensive validation of all demo infrastructure: VM, Oracle database, and MongoDB. Provide an executive summary with pass/fail status for each component.
```

**Highlight to audience:**
- "Claude orchestrates multiple validations"
- "Provides executive-level summary"
- "Reduces hours of manual work to seconds"

### Closing (1 minute)

**Say to audience:**
"This demonstrates how AI agents can automate infrastructure validation using standardized MCP tools, with secure credential management and intelligent result interpretation."

---

## 📝 Quick Reference

### Start Testing
1. Configure Claude Desktop
2. Restart Claude Desktop
3. Ask: "What MCP tools are available?"

### Test Credentials
Ask: "Please validate the demo VM using configured credentials"

### View Logs
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

### Reset Everything
```bash
killall Claude
rm ~/Library/Application\ Support/Claude/claude_desktop_config.json
# Reconfigure and restart
```

---

**You're now ready to test and demo your MCP server with Claude Desktop!** 🚀