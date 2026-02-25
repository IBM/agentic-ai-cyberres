# BeeAI Validation System - Quick Start Guide

## Overview

The BeeAI-powered validation system provides intelligent, multi-agent infrastructure validation with comprehensive discovery, validation, and evaluation capabilities.

## Prerequisites

1. **Python 3.10+** installed
2. **uv** package manager installed
3. **MCP server** configured (python/cyberres-mcp)
4. **LLM provider** configured (Ollama recommended for local testing)

## Installation

```bash
# Navigate to project directory
cd python/src

# Install dependencies (if not already installed)
uv pip install -r requirements.txt

# Verify BeeAI framework is installed
uv pip list | grep beeai-framework
```

## Quick Start

### 1. Basic VM Validation

```bash
# Validate a VM with full workflow (discovery + validation + evaluation)
uv run python main_beeai.py \
  --host 192.168.1.100 \
  --resource-type vm \
  --ssh-user admin \
  --ssh-password password123
```

### 2. Validation Without Discovery

```bash
# Skip discovery phase (faster, but less context)
uv run python main_beeai.py \
  --host 192.168.1.100 \
  --resource-type vm \
  --ssh-user admin \
  --ssh-password password123 \
  --no-discovery
```

### 3. Validation Without Evaluation

```bash
# Skip AI evaluation (faster, but no recommendations)
uv run python main_beeai.py \
  --host 192.168.1.100 \
  --resource-type vm \
  --ssh-user admin \
  --ssh-password password123 \
  --no-evaluation
```

### 4. Minimal Validation (Validation Only)

```bash
# Only run validation checks (fastest)
uv run python main_beeai.py \
  --host 192.168.1.100 \
  --resource-type vm \
  --ssh-user admin \
  --ssh-password password123 \
  --no-discovery \
  --no-evaluation
```

### 5. Oracle Database Validation

```bash
uv run python main_beeai.py \
  --host oracle-db.example.com \
  --resource-type oracle
```

### 6. MongoDB Validation

```bash
uv run python main_beeai.py \
  --host mongo-db.example.com \
  --resource-type mongodb
```

## Command Line Options

```
usage: main_beeai.py [-h] [--llm LLM] [--mcp-server MCP_SERVER]
                     [--no-discovery] [--no-evaluation]
                     [--memory-size MEMORY_SIZE]
                     [--resource-type {vm,oracle,mongodb}]
                     --host HOST [--ssh-user SSH_USER]
                     [--ssh-password SSH_PASSWORD] [--ssh-port SSH_PORT]

BeeAI-Powered Recovery Validation Agent

optional arguments:
  -h, --help            show this help message and exit
  --llm LLM             LLM model to use (default: ollama:llama3.2)
  --mcp-server MCP_SERVER
                        Path to MCP server directory
  --no-discovery        Disable workload discovery phase
  --no-evaluation       Disable AI evaluation phase
  --memory-size MEMORY_SIZE
                        Memory size for agents (default: 50)
  --resource-type {vm,oracle,mongodb}
                        Resource type to validate (default: vm)
  --host HOST           Resource hostname or IP address
  --ssh-user SSH_USER   SSH username (for VM validation)
  --ssh-password SSH_PASSWORD
                        SSH password (for VM validation)
  --ssh-port SSH_PORT   SSH port (default: 22)
```

## Workflow Phases

### Phase 1: Discovery (Optional)
- Detects open ports
- Identifies running processes
- Discovers applications
- Classifies resource type

### Phase 2: Planning (Required)
- Creates validation plan
- Selects appropriate checks
- Considers acceptance criteria

### Phase 3: Execution (Required)
- Executes validation checks
- Calls MCP tools
- Calculates score and status

### Phase 4: Evaluation (Optional)
- Assesses results with AI
- Identifies root causes
- Generates recommendations
- Provides next steps

## Output

### Console Output
The system provides a comprehensive console output with:
- Workflow status and execution time
- Phase timings
- Discovery results
- Classification
- Validation check results
- AI evaluation and recommendations

### JSON Output
Detailed results are saved to a JSON file:
```
validation_result_<hostname>.json
```

### Log File
Detailed logs are written to:
```
beeai_validation.log
```

## Example Output

```
================================================================================
  🤖 BEEAI-POWERED RECOVERY VALIDATION AGENT
  Multi-Agent Intelligent Infrastructure Validation
================================================================================

  Configuration:
    LLM Model: ollama:llama3.2
    Resource Type: VM
    Target Host: 192.168.1.100
    Discovery: Enabled
    Evaluation: Enabled
================================================================================

🔧 Initializing orchestrator and agents...
✅ Initialization complete

🚀 Starting validation workflow for 192.168.1.100...

============================================================
PHASE 1: Workload Discovery
============================================================
✓ Discovery successful:
  Ports: 5
  Processes: 12
  Applications: 3

✓ Resource classified as: WEB_SERVER (confidence: 85%)

============================================================
PHASE 2: Validation Planning
============================================================
✓ Validation plan created:
  Total checks: 8
  Priority: high
  Estimated time: 10s

============================================================
PHASE 3: Validation Execution
============================================================
  [1/8] Connectivity Check...
    ✓ pass
  [2/8] System Health Check...
    ✓ pass
  ...

✓ Validations complete: 7 passed, 1 failed, 0 warnings

============================================================
PHASE 4: AI Evaluation
============================================================
✓ Evaluation complete: good
  Critical issues: 1
  Recommendations: 5

============================================================
WORKFLOW COMPLETE: SUCCESS
Total execution time: 15.5s
Completed phases: discovery, planning, execution, evaluation
============================================================

================================================================================
  📊 VALIDATION RESULTS
================================================================================

  ✅ Workflow Status: SUCCESS
  ⏱️  Execution Time: 15.5s
  📈 Validation Score: 87/100

  Phase Timings:
    • Discovery: 2.5s
    • Planning: 1.2s
    • Execution: 8.8s
    • Evaluation: 3.0s

  🔍 Discovery Results:
    • Open Ports: 5
    • Running Processes: 12
    • Detected Applications: 3

    Top Applications:
      - Nginx Web Server (90% confidence)
      - MySQL Database (85% confidence)
      - PHP Application (75% confidence)

  🏷️  Classification:
    • Category: WEB_SERVER
    • Confidence: 85%
    • Primary App: Nginx Web Server

  ✓ Validation Checks:
    • Total: 8
    • Passed: 7 ✅
    • Failed: 1 ❌
    • Warnings: 0 ⚠️

    Failed Checks:
      ❌ SSL Certificate Check
         Certificate expired 5 days ago

  🎯 AI Evaluation:
    • Overall Health: GOOD
    • Confidence: 85%
    • Critical Issues: 1
    • Recommendations: 5

    Critical Issues:
      🔴 SSL certificate has expired

    Top Recommendations:
      1. Renew SSL certificate immediately
      2. Update certificate auto-renewal configuration
      3. Monitor certificate expiration dates
      4. Review security policies
      5. Consider using Let's Encrypt for auto-renewal

    Next Steps:
      → Prioritize SSL certificate renewal
      → Engage security team
      → Schedule follow-up validation

================================================================================

📄 Detailed results saved to: validation_result_192_168_1_100.json

🧹 Cleaning up resources...
✅ Cleanup complete
```

## Programmatic Usage

### Python API

```python
import asyncio
from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType

async def validate_vm():
    # Create orchestrator
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=True,
        enable_ai_evaluation=True
    )
    
    # Initialize
    await orchestrator.initialize()
    
    # Create request
    vm_info = VMResourceInfo(
        host="192.168.1.100",
        resource_type=ResourceType.VM,
        ssh_host="192.168.1.100",
        ssh_port=22,
        ssh_user="admin",
        ssh_password="password"
    )
    
    request = ValidationRequest(
        resource_info=vm_info,
        auto_discover=True
    )
    
    # Execute workflow
    result = await orchestrator.execute_workflow(request)
    
    # Access results
    print(f"Status: {result.workflow_status}")
    print(f"Score: {result.validation_result.score}/100")
    print(f"Health: {result.evaluation.overall_health}")
    
    # Cleanup
    await orchestrator.cleanup()
    
    return result

# Run
result = asyncio.run(validate_vm())
```

## Testing

### Run All Tests

```bash
# Test individual agents
uv run python -m beeai_agents.test_discovery_agent
uv run python -m beeai_agents.test_validation_agent
uv run python -m beeai_agents.test_evaluation_agent

# Test orchestrator
uv run python -m beeai_agents.test_orchestrator
```

### Run Integration Tests

```bash
# Full integration test
uv run python -m pytest tests/test_integration.py -v
```

## Troubleshooting

### Issue: MCP Server Connection Failed

**Solution**: Ensure MCP server is properly configured
```bash
cd python/cyberres-mcp
uv run cyberres-mcp
```

### Issue: LLM Model Not Found

**Solution**: Verify Ollama is running and model is pulled
```bash
ollama list
ollama pull llama3.2
```

### Issue: Import Errors

**Solution**: Reinstall dependencies
```bash
cd python/src
uv pip install -r requirements.txt --force-reinstall
```

### Issue: Memory Errors

**Solution**: Reduce memory size
```bash
uv run python main_beeai.py --host <host> --memory-size 20
```

## Configuration

### Environment Variables

```bash
# Set LLM provider
export LLM_MODEL="ollama:llama3.2"

# Set MCP server path
export MCP_SERVER_PATH="python/cyberres-mcp"

# Set log level
export LOG_LEVEL="INFO"
```

### Configuration File

Create `beeai_config.json`:
```json
{
  "llm_model": "ollama:llama3.2",
  "mcp_server_path": "python/cyberres-mcp",
  "enable_discovery": true,
  "enable_ai_evaluation": true,
  "memory_size": 50,
  "acceptance_criteria": {
    "min_score": 80,
    "required_checks": ["connectivity", "system_health"]
  }
}
```

## Performance Tips

1. **Disable Discovery**: Use `--no-discovery` for faster validation when workload is known
2. **Disable Evaluation**: Use `--no-evaluation` for faster validation without AI insights
3. **Reduce Memory**: Use `--memory-size 20` for lower memory usage
4. **Parallel Execution**: Run multiple validations in parallel (future feature)

## Best Practices

1. **Always Enable Discovery**: For first-time validation of unknown resources
2. **Use Evaluation**: For comprehensive insights and recommendations
3. **Save Results**: Keep JSON output for historical tracking
4. **Monitor Logs**: Check `beeai_validation.log` for detailed information
5. **Secure Credentials**: Use environment variables or secure vaults for passwords

## Next Steps

1. Review the [Migration Guide](BEEAI_MIGRATION_GUIDE.md) for migrating existing workflows
2. Check [API Documentation](BEEAI_API_DOCS.md) for programmatic usage
3. See [Architecture Guide](PHASE3_WEEK6_SUMMARY.md) for system architecture
4. Explore [Testing Guide](TESTING_GUIDE.md) for comprehensive testing

## Support

For issues or questions:
1. Check logs: `beeai_validation.log`
2. Review documentation in `python/src/`
3. Run tests to verify installation
4. Check MCP server status

## Version

- **BeeAI Framework**: 0.1.77
- **System Version**: 1.0.0
- **Last Updated**: February 25, 2026