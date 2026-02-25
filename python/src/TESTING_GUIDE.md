# Testing Guide: Running main.py for VM Validation

## Prerequisites

### 1. Ollama Setup
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# Pull the model if needed
ollama pull llama3.2
```

### 2. MCP Server Setup
```bash
# In Terminal 1: Start MCP Server
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### 3. Environment Configuration
Verify `.env` file has:
```bash
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Running the Agent

### Terminal 2: Run main.py
```bash
cd python/src
python main.py
```

## Expected Flow

### 1. Welcome Message
```
======================================================================
  🔍 RECOVERY VALIDATION AGENT
  Validate recovered infrastructure resources
======================================================================

Welcome to the Recovery Validation Agent!

I'll help you validate your recovered infrastructure by automatically discovering 
and validating all resources on your server.

To get started, I just need three pieces of information:
1. **Hostname or IP address** of the server
2. **SSH username** to connect
3. **SSH password** (or press Enter to use SSH key)

I'll then automatically:
- Detect the operating system
- Discover all running applications (Oracle, MongoDB, web servers, etc.)
- Validate each discovered resource
- Generate a comprehensive report

Please provide the server details:
```

### 2. Provide VM Details

**Example Input (Natural Language)**:
```
Connect to 192.168.1.100 as admin with password secret123
```

**Or More Structured**:
```
hostname: 192.168.1.100
username: admin
password: secret123
```

**Or Minimal**:
```
192.168.1.100, admin, secret123
```

### 3. Agent Processing

The agent will:
1. ✅ Parse your input using Ollama
2. ✅ Connect to MCP server
3. ✅ Discover OS (Ubuntu, CentOS, etc.)
4. ✅ Discover applications (Oracle, MongoDB, etc.)
5. ✅ Select validation tools
6. ✅ Run validations
7. ✅ Generate report

### 4. Expected Output

```
Agent 🤖: Connecting to MCP server...
Agent 🤖: ✓ Connected to MCP server (15 tools available)

Agent 🤖: 🔍 Discovering operating system on 192.168.1.100...
Agent 🤖: ✓ Detected: Ubuntu 22.04

Agent 🤖: 🔍 Discovering applications and services...
Agent 🤖: ✓ Found 2 applications:
  - oracle 19c (confidence: high)
  - mongodb 6.0 (confidence: high)

Agent 🤖: 🔧 Selecting validation tools...
Agent 🤖: ✓ Selected 6 validation tools:
  - Critical: 2, High: 2, Medium: 2

Agent 🤖: ⚡ Running 6 validations...
  [1/6] ping (Network connectivity)...
  [2/6] check_vm_health (VM health check)...
  [3/6] validate_oracle_db (Database connectivity)...
  [4/6] validate_mongodb (Database connectivity)...
  [5/6] check_oracle_listener (Listener status)...
  [6/6] check_mongo_replication (Replica set status)...

Agent 🤖: ✓ Validations completed: 6/6 successful

Agent 🤖: 📊 Generating validation report...
Agent 🤖: 💡 Generating recommendations...

============================================================
VALIDATION SUMMARY
============================================================
Hostname: 192.168.1.100
OS: Ubuntu 22.04
Applications: 2
Validations: 6/6 passed
Overall Status: pass
Score: 100/100
============================================================

Agent 🤖: ✓ Total execution time: 45.23 seconds
```

## Testing Scenarios

### Scenario 1: VM Only (No Applications)
**Input**: VM with no Oracle/MongoDB
**Expected**: 
- OS detected
- No applications found
- Only VM health checks run
- Score based on VM health

### Scenario 2: VM with Oracle
**Input**: VM with Oracle database
**Expected**:
- OS detected
- Oracle discovered
- Oracle validation tools selected
- Database connectivity validated

### Scenario 3: VM with Multiple Applications
**Input**: VM with Oracle + MongoDB
**Expected**:
- OS detected
- Both applications discovered
- All relevant validation tools selected
- Comprehensive validation

### Scenario 4: Connection Failure
**Input**: Invalid hostname or credentials
**Expected**:
- Clear error message
- Graceful failure
- Suggestions for fixing

## Troubleshooting

### Issue: "OLLAMA_BASE_URL not set"
**Solution**:
```bash
# Check .env file
cat .env | grep OLLAMA

# Should show:
# OLLAMA_BASE_URL=http://localhost:11434
```

### Issue: "MCP server not responding"
**Solution**:
```bash
# Check if MCP server is running
ps aux | grep mcp

# Restart MCP server
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Issue: "SSH connection failed"
**Solution**:
- Verify hostname is reachable: `ping 192.168.1.100`
- Verify SSH credentials are correct
- Check firewall rules
- Try SSH manually: `ssh admin@192.168.1.100`

### Issue: "No applications discovered"
**Solution**:
- This is normal if VM has no Oracle/MongoDB
- Agent will still validate VM health
- Check if applications are actually running on the VM

### Issue: "Import errors"
**Solution**:
```bash
# Ensure you're in the right directory
cd python/src

# Check Python environment
python --version

# Try running with uv
uv run python main.py
```

## Testing with Mock Data

If you don't have a real VM, you can test with mock responses:

### Option 1: Use Test Server
```bash
# Use a test server that responds to SSH
hostname: localhost
username: your_username
password: your_password
```

### Option 2: Modify for Testing
Create a test mode that uses mock MCP responses (Week 4 task)

## Validation Checklist

After running, verify:
- [ ] Ollama parsed input correctly
- [ ] MCP server connected successfully
- [ ] OS discovery worked
- [ ] Application discovery ran (even if none found)
- [ ] Tool selection happened
- [ ] Validations executed
- [ ] Report generated
- [ ] No crashes or unhandled exceptions

## Performance Expectations

- **Connection**: <5 seconds
- **OS Discovery**: <10 seconds
- **Application Discovery**: <30 seconds
- **Validation per tool**: <10 seconds
- **Total time**: <2 minutes for typical VM

## Next Steps After Testing

1. **If successful**: Document results, create demo video
2. **If issues**: Debug, fix, re-test
3. **Gather feedback**: User experience, performance, accuracy
4. **Plan improvements**: Based on test results

## Support

For issues:
1. Check `TROUBLESHOOTING.md`
2. Review `OLLAMA_CONFIGURATION_FIX.md`
3. See `WEEK3_SUMMARY.md` for architecture details
4. Check logs in `recovery_validation.log`