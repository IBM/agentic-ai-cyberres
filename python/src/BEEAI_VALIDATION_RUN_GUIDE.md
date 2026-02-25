# BeeAI Validation Run Guide

## Quick Start - Run a Successful Validation

### Prerequisites
1. ✅ BeeAI Framework v0.1.77 installed
2. ✅ MCP server running (`python/cyberres-mcp`)
3. ✅ Ollama with llama3.2 model
4. ✅ Target infrastructure accessible (VM, Oracle DB, or MongoDB)

### Option 1: Interactive CLI (Recommended)

```bash
cd python/src
uv run python beeai_interactive.py
```

**Enter a validation prompt:**

```
# VM Validation (MUST include password or key)
Validate VM at 192.168.1.100 with SSH user admin password secret

# Oracle Database Validation
Check Oracle database at db.example.com port 1521 user system password oracle

# MongoDB Validation
Validate MongoDB at mongo-server:27017 user admin password mongo123
```

**⚠️ IMPORTANT**: SSH password or key path is REQUIRED for VM validation. The MCP discovery tools need credentials to connect.

### Option 2: Programmatic Usage

```python
import asyncio
from beeai_agents.orchestrator import BeeAIValidationOrchestrator

async def run_validation():
    # Initialize orchestrator
    orchestrator = BeeAIValidationOrchestrator(
        llm_model="ollama:llama3.2",
        mcp_server_path="../cyberres-mcp",
        enable_discovery=True,
        enable_evaluation=True
    )
    
    # Run VM validation
    result = await orchestrator.validate(
        resource_type="vm",
        resource_info={
            "host": "192.168.1.100",
            "ssh_user": "admin",
            "ssh_password": "secret"
        }
    )
    
    print(f"Validation Status: {result.status}")
    print(f"Checks Passed: {result.checks_passed}/{result.total_checks}")
    
    return result

# Run
asyncio.run(run_validation())
```

## What Happens During Validation

### Phase 1: Discovery (Using Working Tools)
The system now uses **two separate MCP tools** that are fully functional:

1. **`discover_os_only`** - Detects operating system
   - OS type (Linux, Windows, etc.)
   - Distribution (Ubuntu, RHEL, etc.)
   - Version and kernel information
   - Confidence scoring

2. **`discover_applications`** - Discovers applications
   - Running processes
   - Installed applications
   - Application versions
   - Confidence scoring

**Results are automatically combined** into a single WorkloadDiscoveryResult.

### Phase 2: Planning
- Validation agent creates a validation plan
- Identifies required checks based on resource type
- Determines tool execution order

### Phase 3: Execution
- Tool executor runs validation checks
- Uses MCP tools (23 available)
- Implements retry logic with exponential backoff
- Handles errors gracefully

### Phase 4: Evaluation
- Evaluation agent analyzes results
- Compares actual vs expected values
- Generates compliance report
- Provides recommendations

## Expected Output

```
============================================================
🤖 BeeAI Infrastructure Validation System
============================================================

Initializing BeeAI orchestrator...
✅ BeeAI orchestrator initialized successfully!
✅ Connected to MCP server
✅ Discovered 23 MCP tools
✅ LLM: ollama:llama3.2

============================================================
💬 Interactive Mode
============================================================

Enter validation prompts (or 'quit' to exit)

> Validate VM at 192.168.1.100 with SSH user admin password secret

🔍 Starting validation workflow...

📋 Phase 1: Discovery
  ✓ Calling discover_os_only tool for 192.168.1.100
  ✓ OS detected: Linux (Ubuntu 20.04)
  ✓ Calling discover_applications tool for 192.168.1.100
  ✓ Found 15 applications
  ✓ Discovery completed successfully

📝 Phase 2: Planning
  ✓ Created validation plan with 8 checks
  ✓ Priority: high
  ✓ Estimated time: 120 seconds

⚙️  Phase 3: Execution
  ✓ Executing check 1/8: SSH connectivity
  ✓ Executing check 2/8: OS version
  ✓ Executing check 3/8: Disk space
  ... (continues for all checks)

📊 Phase 4: Evaluation
  ✓ Passed: 7/8 checks
  ⚠️  Warning: 1 check needs attention
  ✓ Overall status: PASS

============================================================
✅ Validation Complete
============================================================

Summary:
- Total Checks: 8
- Passed: 7
- Failed: 0
- Warnings: 1
- Duration: 45 seconds

Report saved to: validation_report_20260225_123456.json
```

## Discovery Tool Changes

### Before (Not Working)
```python
# Used unimplemented discover_workload tool
result = await discover_workload(host, user, password)
# Returned: {"status": "pending_implementation"}
```

### After (Working Now)
```python
# Uses two separate working tools
os_result = await discover_os_only(host, user, password)
app_result = await discover_applications(host, user, password)
# Results automatically combined
```

## Troubleshooting

### Issue: "Discovery tools not found"
**Solution**: Ensure MCP server is running
```bash
cd python/cyberres-mcp
uv run cyberres-mcp
```

### Issue: "SSH connection failed"
**Solution**: Verify credentials and network connectivity
- Check SSH user/password
- Verify host is reachable
- Ensure SSH port 22 is open

### Issue: "LLM model not found"
**Solution**: Install Ollama model
```bash
ollama pull llama3.2
```

### Issue: "No applications discovered"
**Possible causes:**
- Target system has no detectable applications
- SSH permissions insufficient
- Application signatures not matching

**This is normal** - the system will continue with OS information only.

## Testing with Mock Data

For testing without real infrastructure:

```python
# Use localhost for testing
result = await orchestrator.validate(
    resource_type="vm",
    resource_info={
        "host": "localhost",
        "ssh_user": "your_username",
        "ssh_password": "your_password"
    }
)
```

## Performance Expectations

- **OS Discovery**: 2-5 seconds
- **Application Discovery**: 10-30 seconds
- **Total Discovery**: 15-35 seconds
- **Validation Execution**: 30-120 seconds (depends on checks)
- **Full Workflow**: 1-3 minutes

## Success Criteria

A successful validation run should:
1. ✅ Connect to MCP server
2. ✅ Discover 23 MCP tools
3. ✅ Execute OS discovery successfully
4. ✅ Execute application discovery successfully
5. ✅ Create validation plan
6. ✅ Execute validation checks
7. ✅ Generate evaluation report
8. ✅ Return validation result

## Next Steps

After successful validation:
1. Review validation report
2. Address any warnings or failures
3. Run additional validations as needed
4. Integrate into CI/CD pipeline (optional)

## Support

For issues or questions:
- Check `BEEAI_IMPLEMENTATION_FINAL_SUMMARY.md` for detailed documentation
- Review `BEEAI_HOW_TO_RUN.md` for usage instructions
- See `TROUBLESHOOTING.md` for common issues

---

**Status**: Ready for validation runs ✅  
**Last Updated**: 2026-02-25  
**Version**: 1.0