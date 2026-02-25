# How to Run BeeAI Interactive Validation

## Quick Start

### 1. Start the Interactive CLI

```bash
cd python/src
uv run python beeai_interactive.py
```

### 2. Wait for Initialization

You'll see:
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
```

### 3. Enter Natural Language Prompts

The system accepts natural language prompts to validate infrastructure resources.

## Example Prompts

### VM Validation

```
Validate VM at 192.168.1.100 with SSH user admin password secret
```

```
Check server at myserver.example.com user root password mypass
```

```
Validate Linux VM at 10.0.0.50 port 22 user ubuntu
```

### Oracle Database Validation

```
Check Oracle database at db.example.com port 1521 user system password oracle
```

```
Validate Oracle at 192.168.1.200 service ORCL user admin password secret
```

### MongoDB Validation

```
Validate MongoDB at mongo-server:27017
```

```
Check MongoDB at 192.168.1.150:27017 user admin password mongopass
```

## Prompt Format

### VM Resources
```
Validate VM at <host> [port <port>] user <username> [password <password>]
```

**Parameters**:
- `host`: IP address or hostname (required)
- `port`: SSH port (optional, default: 22)
- `user`: SSH username (optional, default: root)
- `password`: SSH password (optional)

### Oracle Database
```
Check Oracle [database] at <host> [port <port>] user <username> [password <password>] [service <service_name>]
```

**Parameters**:
- `host`: Database host (required)
- `port`: Database port (optional, default: 1521)
- `user`: Database username (optional, default: system)
- `password`: Database password (optional)
- `service`: Service name (optional, default: ORCL)

### MongoDB
```
Validate MongoDB at <host>:<port> [user <username>] [password <password>]
```

**Parameters**:
- `host:port`: MongoDB host and port (required)
- `user`: MongoDB username (optional)
- `password`: MongoDB password (optional)

## What Happens During Validation

### Phase 1: Discovery (for VMs)
- Scans open ports
- Lists running processes
- Detects installed applications
- Identifies workload type

### Phase 2: Classification
- Categorizes the resource (web server, database, app server, etc.)
- Determines confidence level
- Recommends validation checks

### Phase 3: Validation
- Executes MCP tools for validation
- Checks connectivity
- Verifies system health
- Validates configurations

### Phase 4: AI Evaluation
- Analyzes validation results
- Identifies critical issues
- Provides recommendations
- Suggests next steps

## Sample Output

```
============================================================
📊 VALIDATION RESULTS
============================================================

✅ Status: SUCCESS
📈 Score: 85/100
⏱️  Execution Time: 12.34s

📋 Checks Summary:
  ✅ Passed: 8
  ❌ Failed: 1
  ⚠️  Warnings: 2

🔍 Discovery Results:
  Ports: 5
  Processes: 23
  Applications: 3

  Detected Applications:
    - nginx (confidence: 95%)
    - postgresql (confidence: 90%)
    - redis (confidence: 85%)

🏷️  Classification:
  Category: web_server
  Confidence: 92%

🎯 AI Evaluation:
  Overall Health: GOOD
  Confidence: 88%

  💡 Recommendations (3):
    - Update nginx to latest version
    - Enable SSL/TLS for PostgreSQL
    - Configure Redis persistence

⏱️  Phase Timings:
  discovery: 3.45s
  planning: 1.23s
  execution: 5.67s
  evaluation: 1.99s

============================================================
```

## Commands

- **Enter prompt**: Type your validation request
- **quit** or **exit** or **q**: Exit the program
- **Ctrl+C**: Interrupt and exit

## Troubleshooting

### MCP Server Not Running

If you see connection errors:

```bash
# Start MCP server in another terminal
cd python/cyberres-mcp
uv run cyberres-mcp
```

### Ollama Not Running

If you see LLM errors:

```bash
# Start Ollama
ollama serve

# Pull the model (if not already downloaded)
ollama pull llama3.2
```

### SSH Connection Issues

- Verify SSH credentials are correct
- Check if SSH port is accessible
- Ensure firewall allows SSH connections
- Try with SSH key instead of password

### Database Connection Issues

- Verify database is running
- Check connection credentials
- Ensure database port is accessible
- Verify service name (for Oracle)

## Advanced Usage

### Using SSH Keys

For VM validation with SSH keys, you'll need to modify the prompt parser or use the programmatic API:

```python
from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType

async def validate_with_key():
    orchestrator = BeeAIValidationOrchestrator()
    await orchestrator.initialize()
    
    vm = VMResourceInfo(
        host="192.168.1.100",
        resource_type=ResourceType.VM,
        ssh_user="admin",
        ssh_key_path="/path/to/key.pem"
    )
    
    request = ValidationRequest(resource_info=vm, auto_discover=True)
    result = await orchestrator.execute_workflow(request)
    
    print(f"Score: {result.validation_result.score}/100")
```

### Customizing LLM Model

Edit `beeai_interactive.py` line 59:

```python
llm_model="ollama:llama3.2",  # Change to your preferred model
```

Supported models:
- `ollama:llama3.2` (default)
- `ollama:llama3.2:latest`
- `ollama:mistral`
- `openai:gpt-4` (requires API key)
- `groq:llama3-70b` (requires API key)

### Disabling Discovery or Evaluation

Edit `beeai_interactive.py` lines 60-61:

```python
enable_discovery=False,      # Disable workload discovery
enable_ai_evaluation=False,  # Disable AI evaluation
```

## What's Working vs. What's Not

### ✅ Currently Working
- Real MCP tool execution
- Workload discovery
- Dynamic tool discovery
- Multi-agent coordination
- Error handling and retries
- Natural language prompt parsing

### ⚠️ Partially Working
- Validation checks (executes tools but no acceptance criteria yet)
- Result evaluation (works but with limited context)

### ❌ Not Yet Implemented
- Acceptance criteria comparison
- Expected vs actual value validation
- Comprehensive integration tests

## Next Steps

To complete the implementation:

1. **Add Acceptance Criteria** (Phase 3)
   - Load criteria from JSON files
   - Compare actual vs expected values
   - Provide detailed pass/fail reasons

2. **Add Testing** (Phase 4)
   - Integration tests
   - Unit tests for components
   - End-to-end workflow tests

3. **Improve Documentation** (Phase 5)
   - API reference
   - Architecture guide
   - Troubleshooting guide

## Support

For issues or questions:
1. Check `BEEAI_IMPLEMENTATION_REVIEW.md` for known issues
2. Review `BEEAI_FIX_IMPLEMENTATION_PLAN.md` for implementation details
3. See `BEEAI_IMPLEMENTATION_PROGRESS.md` for current status

---

**Created**: 2026-02-25
**Status**: Phase 1 & 2 Complete, Phase 3-5 Pending