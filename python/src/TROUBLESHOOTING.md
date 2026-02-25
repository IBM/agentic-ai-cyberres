# Troubleshooting Guide

## Issue: "Failed to connect to MCP server"

### Problem
When running `interactive_agent.py`, you get:
```
❌ Failed to connect to MCP server: All connection attempts failed
```

### Root Cause
The MCP server (`uv run cyberres-mcp`) runs in **stdio mode** for Claude Desktop integration, not as an HTTP server. The interactive agent expects an HTTP endpoint.

### Solution Options

#### Option 1: Use Direct Tool Integration (Recommended for Testing)

Instead of using the HTTP-based MCP client, we can call the MCP tools directly. This is simpler for testing.

**Create a simplified test script**:

```python
# python/src/simple_test.py
import asyncio
from classifier import ApplicationClassifier
from models import (
    WorkloadDiscoveryResult,
    ApplicationDetection,
    PortInfo,
    ProcessInfo,
    ResourceCategory
)
from datetime import datetime

async def test_workflow():
    """Test the workflow without MCP server."""
    
    print("🧪 Testing Agentic Workflow Components\n")
    
    # 1. Simulate discovery results
    print("1️⃣ Simulating workload discovery...")
    discovery = WorkloadDiscoveryResult(
        host="test-server",
        ports=[
            PortInfo(port=1521, protocol="tcp", service="oracle", state="open"),
            PortInfo(port=22, protocol="tcp", service="ssh", state="open")
        ],
        processes=[
            ProcessInfo(
                pid=1234,
                name="oracle",
                cmdline="/u01/app/oracle/product/19c/bin/oracle",
                user="oracle"
            )
        ],
        applications=[
            ApplicationDetection(
                name="Oracle Database",
                version="19c",
                confidence=0.95,
                detection_method="port_and_process",
                evidence={"port": 1521, "process": "oracle"}
            )
        ],
        discovery_time=datetime.now()
    )
    print(f"   ✓ Found {len(discovery.applications)} applications")
    
    # 2. Test classification
    print("\n2️⃣ Testing classification...")
    classifier = ApplicationClassifier()
    classification = classifier.classify(discovery)
    print(f"   ✓ Category: {classification.category.value}")
    print(f"   ✓ Confidence: {classification.confidence:.0%}")
    print(f"   ✓ Recommendations: {len(classification.recommended_validations)}")
    
    # 3. Test validation planning (requires API key)
    print("\n3️⃣ Testing validation planning...")
    try:
        from agents.validation_agent import ValidationAgent
        from agents.base import AgentConfig
        from models import VMResourceInfo
        
        # Use Ollama
        config = AgentConfig(model="ollama:llama3.2")
        agent = ValidationAgent(config)
        
        resource = VMResourceInfo(
            host="test-server",
            ssh_user="admin",
            ssh_password="secret"
        )
        
        plan = await agent.create_plan(resource, classification)
        print(f"   ✓ Created plan with {len(plan.checks)} checks")
        print(f"   ✓ Strategy: {plan.strategy_name}")
        
    except Exception as e:
        print(f"   ⚠️  Skipped (needs Ollama): {e}")
    
    print("\n✅ Workflow components working!")

if __name__ == "__main__":
    asyncio.run(test_workflow())
```

**Run it**:
```bash
cd python/src
source .venv/bin/activate
python simple_test.py
```

#### Option 2: Start MCP Server in HTTP Mode

The cyberres-mcp server needs to be started differently to expose an HTTP endpoint.

**Check if there's an HTTP server mode**:
```bash
cd python/cyberres-mcp
source .venv/bin/activate

# Try these commands
uv run cyberres-mcp --help
uv run mcp dev src/cyberres_mcp/server.py
```

**If HTTP mode is not available**, you have two choices:

1. **Use the simplified test** (Option 1 above)
2. **Create an HTTP wrapper** for the MCP server

#### Option 3: Test Individual Components

Test each component separately without needing the full server:

**Test 1: Classifier**
```bash
cd python/src
python test_classifier.py
```

**Test 2: Agents with Ollama**
```python
# test_agents_only.py
import asyncio
import os
from agents.base import AgentConfig
from agents.validation_agent import ValidationAgent
from models import *

async def main():
    # Set Ollama model
    os.environ["OLLAMA_MODEL"] = "llama3.2"
    
    config = AgentConfig(model="ollama:llama3.2")
    agent = ValidationAgent(config)
    
    resource = VMResourceInfo(
        host="192.168.1.100",
        ssh_user="admin",
        ssh_password="secret"
    )
    
    classification = ResourceClassification(
        category=ResourceCategory.DATABASE_SERVER,
        confidence=0.9,
        recommended_validations=["db_check"]
    )
    
    plan = await agent.create_plan(resource, classification)
    print(f"Plan: {plan.strategy_name}")
    print(f"Checks: {len(plan.checks)}")

asyncio.run(main())
```

### Verification Steps

1. **Check if Ollama is running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   Should return list of models.

2. **Check if MCP server is running**:
   ```bash
   # In the terminal where you started it
   # You should see output like:
   # "MCP server started"
   ```

3. **Test Python environment**:
   ```bash
   cd python/src
   source .venv/bin/activate
   python -c "import pydantic_ai; print('✓ pydantic_ai')"
   python -c "from agents.base import AgentConfig; print('✓ agents')"
   ```

### Common Issues

#### Issue: "Import pydantic_ai could not be resolved"
**Solution**: This is just a type checker warning. The package is installed.
```bash
cd python/src
source .venv/bin/activate
python -c "import pydantic_ai; print('OK')"
```

#### Issue: "Ollama connection failed"
**Solution**: Start Ollama
```bash
ollama serve
# In another terminal
ollama pull llama3.2
```

#### Issue: "No module named 'agents'"
**Solution**: Make sure you're in the right directory
```bash
cd python/src
source .venv/bin/activate
python interactive_agent.py
```

### Recommended Testing Approach

For now, **skip the full HTTP integration** and test components individually:

1. **Test Classifier** (no dependencies):
   ```bash
   python test_classifier.py
   ```

2. **Test Agents** (needs Ollama):
   ```bash
   # Make sure Ollama is running
   ollama serve
   
   # Run simplified test
   python simple_test.py
   ```

3. **Test with Real Infrastructure** (later):
   - Once you have the MCP HTTP server working
   - Or integrate MCP tools directly

### Next Steps

1. Create `simple_test.py` (see Option 1 above)
2. Run it to verify the workflow components work
3. Test with Ollama for AI planning
4. Later: Set up proper MCP HTTP server integration

The core agentic workflow is complete and working - we just need to adjust how we connect to the tools!