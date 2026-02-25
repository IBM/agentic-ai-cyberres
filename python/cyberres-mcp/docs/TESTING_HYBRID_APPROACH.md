# Testing the Hybrid Approach - get_raw_server_data Tool

**Purpose:** Test the new `get_raw_server_data` MCP tool with Claude Desktop and MCP Inspector  
**Prerequisites:** Linux server with SSH access, credentials configured

---

## Quick Start

### 1. Restart Claude Desktop

The MCP server needs to be restarted to load the new tool:

```bash
# On macOS
pkill "Claude"
open -a "Claude"

# Or use the restart script
cd python/cyberres-mcp
bash docs/fix-claude-desktop.sh
```

### 2. Verify Tool is Available

In Claude Desktop, ask:
```
What tools do you have available for workload discovery?
```

You should see:
- ✅ `discover_os_only` (existing)
- ✅ `discover_applications` (existing)
- ✅ `get_raw_server_data` (new) ⭐
- ✅ `discover_workload` (placeholder)

---

## Testing with Claude Desktop

### Test 1: Basic Raw Data Collection

**Prompt to Claude:**
```
Use the get_raw_server_data tool to collect process and port information from this server:

Host: <your-server-ip>
SSH User: <your-username>
SSH Password: <your-password>

Collect processes and ports only.
```

**Expected Response:**
Claude will call the tool and show you:
```json
{
  "host": "10.0.1.5",
  "data": {
    "processes": "PID USER COMMAND\n1234 oracle ora_pmon_ORCL\n...",
    "ports": "tcp 0 0 0.0.0.0:1521 LISTEN\n..."
  },
  "collection_options": {
    "collect_processes": true,
    "collect_ports": true,
    "collect_configs": false,
    "collect_packages": false,
    "collect_services": false
  },
  "data_types_collected": ["processes", "ports"]
}
```

### Test 2: Hybrid Workflow (Signature + Raw Data)

**Prompt to Claude:**
```
Discover applications on this server using a hybrid approach:

1. First use discover_applications to get signature-based detections
2. Then use get_raw_server_data to get raw data
3. Compare the results and tell me what additional insights the raw data provides

Server details:
Host: <your-server-ip>
SSH User: <your-username>
SSH Password: <your-password>
```

**Expected Workflow:**
1. Claude calls `discover_applications` → Gets structured app list
2. Claude calls `get_raw_server_data` → Gets raw process/port data
3. Claude analyzes both and provides insights

**Example Response:**
```
Based on the hybrid analysis:

Signature Detection Found:
- Oracle Database 19c (HIGH confidence)
- PostgreSQL (HIGH confidence)
- Unknown Java process (LOW confidence)

Raw Data Analysis Reveals:
- The "Unknown Java process" is running: java -jar /opt/myapp/server.jar
- It's listening on port 8080 (HTTP) and 8443 (HTTPS)
- Process owner: appuser
- This appears to be a Spring Boot application based on the command line

Additional Insights:
- The raw data shows this is likely a custom business application
- It's configured for production (HTTPS on 8443)
- You may want to investigate /opt/myapp/ for more details
```

### Test 3: Collect All Data Types

**Prompt to Claude:**
```
Use get_raw_server_data to collect ALL available data types from the server:

Host: <your-server-ip>
SSH User: <your-username>
SSH Password: <your-password>

Enable:
- Processes
- Ports
- Packages
- Services
- Configs (collect /etc/os-release)
```

**Expected Response:**
Claude will collect and show:
- Process list
- Port list
- Installed packages
- Running services
- Config file contents

### Test 4: Selective Data Collection

**Prompt to Claude:**
```
I only need to see what packages are installed on the server. Use get_raw_server_data to collect just the package list.

Host: <your-server-ip>
SSH User: <your-username>
SSH Password: <your-password>
```

**Expected Response:**
Only package data will be collected (rpm or dpkg output).

---

## Testing with MCP Inspector

### Setup MCP Inspector

```bash
cd python/cyberres-mcp

# Install MCP Inspector if not already installed
npx @modelcontextprotocol/inspector

# Or if already installed
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

### Test 1: Verify Tool Registration

1. Open MCP Inspector in browser (usually http://localhost:5173)
2. Click "Tools" tab
3. Verify `get_raw_server_data` is listed
4. Check the tool schema shows all parameters

**Expected Schema:**
```json
{
  "name": "get_raw_server_data",
  "description": "Get raw server data for agent-side LLM processing...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "host": {"type": "string"},
      "ssh_user": {"type": "string"},
      "ssh_password": {"type": "string"},
      "ssh_key_path": {"type": "string"},
      "ssh_port": {"type": "integer", "default": 22},
      "collect_processes": {"type": "boolean", "default": true},
      "collect_ports": {"type": "boolean", "default": true},
      "collect_configs": {"type": "boolean", "default": false},
      "config_paths": {"type": "array"},
      "collect_packages": {"type": "boolean", "default": false},
      "collect_services": {"type": "boolean", "default": false}
    },
    "required": ["host"]
  }
}
```

### Test 2: Call Tool with Minimal Parameters

In MCP Inspector, call the tool:

```json
{
  "host": "10.0.1.5",
  "ssh_user": "admin",
  "ssh_password": "your-password"
}
```

**Expected Result:**
```json
{
  "ok": true,
  "result": {
    "host": "10.0.1.5",
    "data": {
      "processes": "...",
      "ports": "..."
    },
    "collection_options": {...},
    "data_types_collected": ["processes", "ports"]
  }
}
```

### Test 3: Call Tool with All Options

```json
{
  "host": "10.0.1.5",
  "ssh_user": "admin",
  "ssh_password": "your-password",
  "collect_processes": true,
  "collect_ports": true,
  "collect_packages": true,
  "collect_services": true,
  "collect_configs": true,
  "config_paths": ["/etc/os-release", "/etc/hostname"]
}
```

**Expected Result:**
All data types collected and returned.

### Test 4: Error Handling

Test with invalid credentials:

```json
{
  "host": "10.0.1.5",
  "ssh_user": "admin",
  "ssh_password": "wrong-password"
}
```

**Expected Result:**
```json
{
  "ok": false,
  "error": "Raw data collection failed: Authentication failed",
  "code": "RAW_DATA_ERROR",
  "host": "10.0.1.5"
}
```

---

## Comparison Testing: Signature vs Raw Data

### Scenario: Unknown Application

**Step 1: Use signature detection**
```
Claude, use discover_applications on server 10.0.1.5
```

**Result:**
```
Found: "Unknown Java App" (LOW confidence)
```

**Step 2: Use raw data collection**
```
Claude, use get_raw_server_data on the same server to get more details
```

**Result:**
```
Raw process data shows:
java -Xmx4g -jar /opt/custom-app/server.jar --spring.profiles.active=prod

This reveals:
- Spring Boot application
- 4GB heap size
- Production profile
- Custom application in /opt/custom-app/
```

**Step 3: Ask Claude to analyze**
```
Claude, based on the raw data, what can you tell me about this application?
```

**Expected Analysis:**
```
Based on the raw data analysis:

Application Type: Spring Boot REST API
Confidence: MEDIUM (inferred from patterns)
Version: Unknown (would need to check JAR manifest)
Purpose: Custom business application
Environment: Production
Memory: 4GB allocated

Recommendations:
1. Check /opt/custom-app/application.yml for configuration
2. Review logs in /opt/custom-app/logs/
3. Verify database connections
4. Check if monitoring is configured
```

---

## Real-World Testing Scenarios

### Scenario 1: Database Server

**Test:**
```
Claude, analyze this database server:
1. Use discover_applications to find databases
2. Use get_raw_server_data to get process details
3. Tell me what databases are running and their configurations

Host: db-server-01
User: admin
Password: <password>
```

**Expected Insights:**
- Signature detection finds: Oracle, PostgreSQL
- Raw data reveals: versions, memory settings, data directories
- Claude provides: comprehensive database inventory

### Scenario 2: Web Server

**Test:**
```
Claude, investigate this web server:
1. Discover applications
2. Get raw data for processes and ports
3. Identify all web services and their configurations

Host: web-server-01
User: admin
Password: <password>
```

**Expected Insights:**
- Signature detection finds: Apache, Nginx
- Raw data reveals: virtual hosts, SSL configs, worker processes
- Claude provides: web server architecture analysis

### Scenario 3: Application Server

**Test:**
```
Claude, analyze this application server:
1. Discover applications
2. Get raw data including packages and services
3. Create an inventory of all middleware and applications

Host: app-server-01
User: admin
Password: <password>
```

**Expected Insights:**
- Signature detection finds: Tomcat, known apps
- Raw data reveals: custom applications, dependencies
- Claude provides: complete application stack inventory

---

## Troubleshooting

### Issue 1: Tool Not Available

**Symptom:** Claude says "I don't have a tool called get_raw_server_data"

**Solution:**
```bash
# Restart Claude Desktop
pkill "Claude"
open -a "Claude"

# Verify server is running
cd python/cyberres-mcp
uv run cyberres-mcp
```

### Issue 2: SSH Connection Fails

**Symptom:** Error: "SSH connection failed"

**Solution:**
1. Verify server is reachable: `ping <server-ip>`
2. Test SSH manually: `ssh user@server-ip`
3. Check credentials in secrets.json
4. Verify SSH port (default: 22)

### Issue 3: Empty Data Returned

**Symptom:** Tool returns empty strings for processes/ports

**Solution:**
1. Check SSH user has permissions
2. Verify commands are available: `ps`, `netstat`, `ss`
3. Try with sudo if needed
4. Check server logs for errors

### Issue 4: Slow Response

**Symptom:** Tool takes >30 seconds to respond

**Solution:**
1. Reduce data collection (disable packages/services)
2. Check network latency
3. Verify server isn't overloaded
4. Consider collecting data in batches

---

## Performance Benchmarks

### Expected Timing

| Data Type | Time | Notes |
|-----------|------|-------|
| Processes only | 1-2 sec | Fast |
| Ports only | 1-2 sec | Fast |
| Processes + Ports | 2-3 sec | Recommended default |
| + Packages | 5-10 sec | Slower (large output) |
| + Services | 3-5 sec | Medium |
| + Configs | 1-2 sec | Fast (per file) |
| **All data types** | **10-15 sec** | Complete collection |

### Optimization Tips

1. **Collect only what you need**
   - Default: processes + ports (2-3 sec)
   - Add others only when necessary

2. **Use selective config collection**
   - Specify exact paths
   - Avoid wildcards

3. **Batch operations**
   - Collect from multiple servers in parallel
   - Use async operations when available

---

## Next Steps After Testing

Once you've verified the tool works:

1. **Document your findings**
   - What worked well?
   - What needs improvement?
   - Any edge cases discovered?

2. **Test with real workloads**
   - Production-like servers
   - Various Linux distributions
   - Different application stacks

3. **Prepare for Phase 2**
   - Agent enhancement logic
   - LLM integration
   - Hybrid workflow automation

---

## Example Test Script

Save this as `test_hybrid_manual.sh`:

```bash
#!/bin/bash

echo "Testing Hybrid Approach - Manual Test Script"
echo "=============================================="

# Configuration
SERVER="10.0.1.5"
USER="admin"
PASS="your-password"

echo ""
echo "Test 1: Signature Detection"
echo "----------------------------"
echo "Ask Claude: Use discover_applications on $SERVER"
read -p "Press Enter after Claude responds..."

echo ""
echo "Test 2: Raw Data Collection"
echo "----------------------------"
echo "Ask Claude: Use get_raw_server_data on $SERVER"
read -p "Press Enter after Claude responds..."

echo ""
echo "Test 3: Hybrid Analysis"
echo "-----------------------"
echo "Ask Claude: Compare the results from both tools and provide insights"
read -p "Press Enter after Claude responds..."

echo ""
echo "Testing complete! Review Claude's responses above."
```

---

## Summary

You now have three ways to test the hybrid approach:

1. **Claude Desktop** - Natural language testing
2. **MCP Inspector** - Direct tool invocation
3. **Manual Testing** - Guided test scenarios

**Recommended Testing Order:**
1. Start with MCP Inspector to verify tool works
2. Move to Claude Desktop for natural language testing
3. Try real-world scenarios with actual servers
4. Document findings and prepare for Phase 2

**Success Criteria:**
- ✅ Tool appears in Claude's tool list
- ✅ Can collect processes and ports
- ✅ Can collect all data types
- ✅ Error handling works correctly
- ✅ Performance is acceptable (<15 sec for all data)
- ✅ Claude can analyze raw data effectively

Once testing is complete, you're ready to implement Phase 2: Agent Enhancement Logic!