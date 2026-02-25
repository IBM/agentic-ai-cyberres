# MCP Inspector Testing Guide

## 🎯 What is MCP Inspector?

MCP Inspector is a web-based tool for testing MCP servers. It provides:
- Interactive UI to test all tools
- Real-time request/response viewing
- No need for Claude Desktop
- Perfect for demos and debugging

## 🚀 Quick Start

### Step 1: Start MCP Inspector

```bash
cd python/cyberres-mcp
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

**What happens:**
- MCP Inspector starts on http://localhost:5173
- Your MCP server starts in stdio mode
- Inspector connects to the server
- Web UI opens automatically

### Step 2: Open in Browser

If it doesn't open automatically:
```
Open: http://localhost:5173
```

### Step 3: Verify Connection

You should see:
- ✅ "Connected" status indicator
- ✅ List of 13 tools in the sidebar
- ✅ 3 resources available
- ✅ 3 prompts available

## 📋 Testing Workflow

### Test 1: Server Health Check

**Tool:** `server_health`

**Steps:**
1. Click "Tools" in left sidebar
2. Find and click `server_health`
3. Click "Run Tool" (no arguments needed)

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

### Test 2: VM Health Validation

**Tool:** `vm_linux_ssh_validate_health`

**Steps:**
1. Click `vm_linux_ssh_validate_health` in tools list
2. Fill in arguments:
   ```json
   {
     "host": "9.11.68.67",
     "username": "defsensor",
     "password": "Lash@78snubflip"
   }
   ```
3. Click "Run Tool"

**Expected Response:**
```json
{
  "ok": true,
  "health": {
    "uptime": "...",
    "load_avg": [...],
    "memory": {...},
    "disk": {...},
    "services": {...}
  }
}
```

### Test 3: Disk Usage Check

**Tool:** `vm_linux_fs_usage`

**Steps:**
1. Click `vm_linux_fs_usage`
2. Fill in arguments:
   ```json
   {
     "host": "9.11.68.67",
     "username": "defsensor",
     "password": "Lash@78snubflip"
   }
   ```
3. Click "Run Tool"

**Expected Response:**
```json
{
  "ok": true,
  "rc": 0,
  "filesystems": [
    {
      "filesystem": "/dev/sda1",
      "blocks_k": 10485760,
      "used_k": 4718592,
      "avail_k": 5767168,
      "use_pct": 45,
      "mountpoint": "/"
    }
  ]
}
```

### Test 4: Service Check (SSHD)

**Tool:** `vm_linux_services`

**Steps:**
1. Click `vm_linux_services`
2. Fill in arguments:
   ```json
   {
     "host": "9.11.68.67",
     "username": "defsensor",
     "password": "Lash@78snubflip",
     "required": ["sshd"]
   }
   ```
3. Click "Run Tool"

**Expected Response:**
```json
{
  "ok": true,
  "rc": 0,
  "services": {
    "sshd": "active"
  }
}
```

### Test 5: Memory and Load

**Tool:** `vm_linux_uptime_load_mem`

**Steps:**
1. Click `vm_linux_uptime_load_mem`
2. Fill in arguments:
   ```json
   {
     "host": "9.11.68.67",
     "username": "defsensor",
     "password": "Lash@78snubflip"
   }
   ```
3. Click "Run Tool"

**Expected Response:**
```json
{
  "ok": true,
  "rc": 0,
  "stdout": "uptime output and memory info..."
}
```

### Test 6: Network Connectivity

**Tool:** `vm_linux_ssh_validate_network`

**Steps:**
1. Click `vm_linux_ssh_validate_network`
2. Fill in arguments:
   ```json
   {
     "host": "9.11.68.67",
     "username": "defsensor",
     "password": "Lash@78snubflip",
     "targets": ["8.8.8.8", "google.com"]
   }
   ```
3. Click "Run Tool"

**Expected Response:**
```json
{
  "ok": true,
  "reachable": ["8.8.8.8", "google.com"],
  "unreachable": []
}
```

### Test 7: Simple Ping

**Tool:** `net_ping`

**Steps:**
1. Click `net_ping`
2. Fill in arguments:
   ```json
   {
     "host": "8.8.8.8",
     "count": 3
   }
   ```
3. Click "Run Tool"

**Expected Response:**
```json
{
  "ok": true,
  "reachable": true,
  "packets_sent": 3,
  "packets_received": 3,
  "packet_loss": 0
}
```

## 🎬 Demo Scenario with MCP Inspector

### Scenario: Complete VM Validation

**Duration:** 5 minutes

**Steps:**

1. **Start Inspector** (30 seconds)
   ```bash
   cd python/cyberres-mcp
   npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
   ```

2. **Show Server Health** (30 seconds)
   - Run `server_health` tool
   - Show 13 tools available
   - Explain MCP architecture

3. **VM Health Check** (1 minute)
   - Run `vm_linux_ssh_validate_health`
   - Show comprehensive health metrics
   - Explain validation criteria

4. **Disk Usage** (1 minute)
   - Run `vm_linux_fs_usage`
   - Show filesystem usage
   - Highlight threshold checking

5. **Service Verification** (1 minute)
   - Run `vm_linux_services` with `["sshd"]`
   - Show service status
   - Explain critical services

6. **Network Validation** (1 minute)
   - Run `vm_linux_ssh_validate_network`
   - Show connectivity to multiple targets
   - Explain network requirements

7. **Q&A** (30 seconds)
   - Answer questions
   - Show other available tools

## 📊 Inspector Features

### Left Sidebar
- **Tools** - List of all 13 validation tools
- **Resources** - 3 acceptance profiles (VM, Oracle, MongoDB)
- **Prompts** - 3 agent prompts (planner, evaluator, summarizer)

### Main Panel
- **Tool Details** - Description and parameters
- **Arguments** - JSON input form
- **Run Tool** - Execute button
- **Response** - JSON output display

### Bottom Panel
- **Request** - Shows the MCP request sent
- **Response** - Shows the MCP response received
- **Logs** - Server logs and errors

## 🔍 Troubleshooting

### Issue: Inspector Won't Start

**Error:** "Failed to start server"

**Solution:**
```bash
# Check if port 5173 is in use
lsof -i :5173

# Kill any process using the port
kill -9 <PID>

# Try again
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

### Issue: Server Not Connecting

**Error:** "Connection failed"

**Solution:**
```bash
# Verify server can start standalone
cd python/cyberres-mcp
MCP_TRANSPORT=stdio uv run cyberres-mcp

# If it works, try inspector again
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

### Issue: Tool Execution Fails

**Error:** "Tool execution failed"

**Check:**
1. Verify credentials are correct
2. Check network connectivity to target host
3. Look at server logs in bottom panel
4. Verify SSH access manually:
   ```bash
   ssh defsensor@9.11.68.67
   ```

### Issue: Slow Response

**Cause:** Network latency or SSH timeout

**Solution:**
- Increase timeout in tool arguments
- Check network connectivity
- Verify target host is responsive

## 🎯 Pre-Demo Checklist

Before your demo:

- [ ] Test MCP Inspector starts successfully
- [ ] Verify all 13 tools are listed
- [ ] Test `server_health` tool
- [ ] Test at least one VM validation tool
- [ ] Prepare credentials (have demo-secrets.json ready)
- [ ] Test network connectivity to target hosts
- [ ] Have backup plan (HTTP mode or Claude Desktop)

## 📋 Quick Reference

### Start Inspector
```bash
cd python/cyberres-mcp
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

### Access URL
```
http://localhost:5173
```

### Stop Inspector
```
Press Ctrl+C in terminal
```

### Test Credentials
```json
{
  "host": "9.11.68.67",
  "username": "defsensor",
  "password": "Lash@78snubflip"
}
```

## 🎬 Alternative: HTTP Mode

If Inspector has issues, use HTTP mode:

```bash
cd python/cyberres-mcp
uv run cyberres-mcp
```

Then access:
- **Server:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **OpenAPI:** http://localhost:8000/openapi.json

Use curl or Postman to test tools:
```bash
curl -X POST http://localhost:8000/tools/server_health \
  -H "Content-Type: application/json" \
  -d '{}'
```

## ✅ Success Indicators

You'll know it's working when:
1. ✅ Inspector opens at http://localhost:5173
2. ✅ "Connected" status shows in UI
3. ✅ 13 tools listed in sidebar
4. ✅ `server_health` returns status
5. ✅ VM validation tools return results

## 🎯 Summary

**MCP Inspector is perfect for:**
- ✅ Interactive testing
- ✅ Demo presentations
- ✅ Debugging issues
- ✅ Exploring available tools
- ✅ No Claude Desktop needed

**Start command:**
```bash
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

**Access:** http://localhost:5173

**Ready to demo!**