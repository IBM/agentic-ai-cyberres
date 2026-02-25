# Quick Test Guide - Hybrid Approach

**5-Minute Testing Guide for get_raw_server_data**

---

## Step 1: Restart Claude Desktop (30 seconds)

```bash
# macOS
pkill "Claude" && open -a "Claude"

# Or use restart script
cd python/cyberres-mcp && bash docs/fix-claude-desktop.sh
```

---

## Step 2: Verify Tool is Available (30 seconds)

**Ask Claude:**
```
List all workload discovery tools you have available
```

**Expected Response:**
- discover_os_only ✅
- discover_applications ✅
- get_raw_server_data ✅ (NEW)
- discover_workload ✅

---

## Step 3: Test Basic Collection (1 minute)

**Ask Claude:**
```
Use get_raw_server_data to collect processes and ports from:
Host: <your-server-ip>
User: <your-username>
Password: <your-password>
```

**Expected:** Raw process and port data returned

---

## Step 4: Test Hybrid Workflow (2 minutes)

**Ask Claude:**
```
Discover applications on <server-ip> using both methods:
1. discover_applications (signature-based)
2. get_raw_server_data (raw data)

Then compare and tell me what additional insights the raw data provides.

Credentials: <user>/<password>
```

**Expected:** Claude shows both results and provides analysis

---

## Step 5: Test with MCP Inspector (1 minute)

```bash
# Start MCP Inspector
cd python/cyberres-mcp
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

1. Open http://localhost:5173
2. Click "Tools" tab
3. Find `get_raw_server_data`
4. Click "Test" and enter:
```json
{
  "host": "your-server-ip",
  "ssh_user": "your-username",
  "ssh_password": "your-password"
}
```

**Expected:** JSON response with raw data

---

## Common Test Prompts for Claude

### Test 1: Basic Collection
```
Get raw server data from 10.0.1.5 (user: admin, pass: secret)
```

### Test 2: Selective Collection
```
Get only the package list from 10.0.1.5 using get_raw_server_data
```

### Test 3: Hybrid Analysis
```
Compare signature detection vs raw data for server 10.0.1.5
```

### Test 4: Unknown App Investigation
```
There's an unknown Java app on 10.0.1.5. Use raw data to investigate it.
```

### Test 5: Complete Inventory
```
Create a complete inventory of 10.0.1.5 using all available data
```

---

## Success Checklist

- [ ] Tool appears in Claude's tool list
- [ ] Can collect processes and ports
- [ ] Can collect packages and services
- [ ] Can collect config files
- [ ] Error handling works (wrong password)
- [ ] Performance is acceptable (<15 sec)
- [ ] Claude can analyze raw data
- [ ] Hybrid workflow works end-to-end

---

## Troubleshooting

**Tool not found?**
→ Restart Claude Desktop

**SSH fails?**
→ Test manually: `ssh user@server-ip`

**Empty data?**
→ Check user permissions

**Slow response?**
→ Collect fewer data types

---

## Next Steps

After successful testing:
1. ✅ Document findings
2. ✅ Test with real servers
3. ✅ Ready for Phase 2 (Agent enhancement)

---

## Quick Commands

```bash
# Restart Claude
pkill "Claude" && open -a "Claude"

# Run tests
cd python/cyberres-mcp
uv run python test_raw_data_collector.py

# Start MCP Inspector
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp

# Check server health
uv run cyberres-mcp
```

---

**Total Testing Time: ~5 minutes**  
**Ready to test? Start with Step 1!**