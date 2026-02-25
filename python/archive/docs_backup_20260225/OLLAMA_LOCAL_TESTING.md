# Ollama Local Testing Guide

## Using Local LLMs with Ollama for Testing

This guide shows you how to use Ollama with local LLMs (like Llama 3, Mistral, etc.) instead of OpenAI/Anthropic APIs for cost-free local testing.

---

## Why Use Ollama?

✅ **Free**: No API costs  
✅ **Private**: Data stays local  
✅ **Fast**: No network latency  
✅ **Offline**: Works without internet  
✅ **Multiple Models**: Llama 3, Mistral, CodeLlama, etc.

---

## Step 1: Install Ollama

### macOS
```bash
# Download and install from https://ollama.ai
# Or use Homebrew
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Download from https://ollama.ai/download

---

## Step 2: Install Local Models

### Recommended Models for Testing

```bash
# Llama 3 (8B) - Best balance of speed and quality
ollama pull llama3

# Mistral (7B) - Fast and efficient
ollama pull mistral

# CodeLlama (7B) - Good for technical content
ollama pull codellama

# Llama 3 (70B) - Highest quality (requires more RAM)
ollama pull llama3:70b
```

### Verify Installation

```bash
# List installed models
ollama list

# Test a model
ollama run llama3 "Hello, how are you?"
```

---

## Step 3: Start Ollama Server

```bash
# Start Ollama server (runs on http://localhost:11434)
ollama serve
```

Keep this running in a separate terminal.

---

## Step 4: Configure Agents for Ollama

### Update AgentConfig to Use Ollama

The `AgentConfig` class already supports Ollama! Just change the model string:

```python
from agents.base import AgentConfig

# For OpenAI (default)
config = AgentConfig(
    model="openai:gpt-4",
    api_key="your_openai_key"
)

# For Ollama (local)
config = AgentConfig(
    model="ollama:llama3",  # or "ollama:mistral", "ollama:codellama"
    api_key=None  # No API key needed!
)
```

### Pydantic AI Ollama Support

Pydantic AI natively supports Ollama with the `ollama:` prefix:

- `ollama:llama3` - Llama 3 8B
- `ollama:llama3:70b` - Llama 3 70B
- `ollama:mistral` - Mistral 7B
- `ollama:codellama` - CodeLlama 7B
- `ollama:mixtral` - Mixtral 8x7B

---

## Step 5: Update Test Scripts for Ollama

### Option 1: Environment Variable

Create `.env` file:

```bash
# Use Ollama instead of OpenAI
AGENT_MODEL=ollama:llama3

# No API key needed for Ollama
# OPENAI_API_KEY=  # Leave empty or remove
```

### Option 2: Direct Configuration

Update test scripts to use Ollama:

```python
# test_classification_ollama.py
from agents.base import AgentConfig
from agents.classification_agent import ClassificationAgent

# Use Ollama
config = AgentConfig(
    model="ollama:llama3",  # Local model
    temperature=0.1,
    max_tokens=4000
)

agent = ClassificationAgent(config=config)
```

---

## Complete Test Scripts for Ollama

### Test 1: Classification with Ollama

```python
#!/usr/bin/env python3
"""Test classification with Ollama."""

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

from models import (
    WorkloadDiscoveryResult, PortInfo, ProcessInfo,
    ApplicationDetection
)
from agents.classification_agent import ClassificationAgent
from agents.base import AgentConfig
from feature_flags import FeatureFlags


async def test_classification_ollama():
    """Test classification with Ollama."""
    print("=" * 80)
    print("Testing Classification with Ollama (Local LLM)")
    print("=" * 80)
    
    # Create mock discovery result
    print("\n1. Creating mock discovery result...")
    discovery_result = WorkloadDiscoveryResult(
        host="web-server-01",
        ports=[
            PortInfo(port=22, protocol="tcp", state="open", service="ssh"),
            PortInfo(port=80, protocol="tcp", state="open", service="http"),
            PortInfo(port=443, protocol="tcp", state="open", service="https"),
        ],
        processes=[
            ProcessInfo(pid=1234, name="nginx", user="www-data",
                       command="/usr/sbin/nginx -g daemon off;"),
            ProcessInfo(pid=1235, name="php-fpm", user="www-data",
                       command="php-fpm: pool www"),
        ],
        applications=[
            ApplicationDetection(
                name="Nginx",
                version="1.18.0",
                confidence=0.95,
                detection_method="port_and_process"
            )
        ],
        discovery_time=datetime.now()
    )
    print(f"✅ Mock discovery result created")
    
    # Create agent with Ollama
    print("\n2. Creating Classification Agent with Ollama...")
    print("   Model: ollama:llama3 (local)")
    print("   No API key required!")
    
    config = AgentConfig(
        model="ollama:llama3",  # Use local Llama 3
        temperature=0.1,
        max_tokens=4000
    )
    
    feature_flags = FeatureFlags({"ai_classification": True})
    
    agent = ClassificationAgent(
        config=config,
        feature_flags=feature_flags
    )
    print("✅ Agent created with Ollama")
    
    # Classify
    print("\n3. Running classification with local LLM...")
    print("   This uses Ollama running on localhost:11434")
    
    classification = await agent.classify(discovery_result)
    
    print("\n✅ Classification completed!")
    print(f"   - Category: {classification.category.value}")
    print(f"   - Confidence: {classification.confidence:.0%}")
    if classification.primary_application:
        print(f"   - Primary App: {classification.primary_application.name}")
    print(f"   - Reasoning: {classification.reasoning}")
    
    print("\n" + "=" * 80)
    print("✅ Ollama test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_classification_ollama())
```

### Test 2: Reporting with Ollama

```python
#!/usr/bin/env python3
"""Test reporting with Ollama."""

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

from models import (
    ResourceValidationResult, CheckResult, ValidationStatus,
    ResourceType
)
from agents.reporting_agent import ReportingAgent
from agents.base import AgentConfig
from feature_flags import FeatureFlags


async def test_reporting_ollama():
    """Test reporting with Ollama."""
    print("=" * 80)
    print("Testing Reporting with Ollama (Local LLM)")
    print("=" * 80)
    
    # Create mock validation result
    print("\n1. Creating mock validation result...")
    validation_result = ResourceValidationResult(
        resource_type=ResourceType.VM,
        resource_host="app-server-01",
        overall_status=ValidationStatus.WARNING,
        score=75,
        checks=[
            CheckResult(
                check_id="net_001",
                check_name="Network Connectivity",
                status=ValidationStatus.PASS,
                message="All ports accessible"
            ),
            CheckResult(
                check_id="sys_001",
                check_name="System Resources",
                status=ValidationStatus.WARNING,
                message="CPU usage at 85%",
                expected="CPU < 80%",
                actual="CPU = 85%"
            ),
        ],
        execution_time_seconds=10.5
    )
    print("✅ Mock validation result created")
    
    # Create agent with Ollama
    print("\n2. Creating Reporting Agent with Ollama...")
    print("   Model: ollama:llama3 (local)")
    
    config = AgentConfig(
        model="ollama:llama3",
        temperature=0.3,  # Slightly higher for natural writing
        max_tokens=8000
    )
    
    feature_flags = FeatureFlags({"ai_reporting": True})
    
    agent = ReportingAgent(
        config=config,
        feature_flags=feature_flags
    )
    print("✅ Agent created with Ollama")
    
    # Generate report
    print("\n3. Generating report with local LLM...")
    
    report = await agent.generate_report(
        validation_result=validation_result,
        format="markdown"
    )
    
    print("\n✅ Report generated!")
    print(f"   - Length: {len(report)} characters")
    
    # Display report
    print("\n4. Generated Report:")
    print("=" * 80)
    print(report)
    print("=" * 80)
    
    # Save report
    report_file = f"ollama_report_{int(datetime.now().timestamp())}.md"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\n✅ Report saved to: {report_file}")
    
    print("\n" + "=" * 80)
    print("✅ Ollama test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_reporting_ollama())
```

### Test 3: Complete Workflow with Ollama

```python
#!/usr/bin/env python3
"""Test complete workflow with Ollama."""

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

from models import VMResourceInfo, ResourceType
from mcp_stdio_client import MCPStdioClient
from tool_coordinator import ToolCoordinator
from state_manager import StateManager
from feature_flags import FeatureFlags
from agents.discovery_agent_enhanced import EnhancedDiscoveryAgent
from agents.classification_agent import ClassificationAgent
from agents.reporting_agent import ReportingAgent
from agents.base import AgentConfig


async def test_complete_workflow_ollama():
    """Test complete workflow with Ollama."""
    print("=" * 80)
    print("Testing Complete Workflow with Ollama (Local LLM)")
    print("=" * 80)
    
    # Initialize components
    print("\n1. Initializing components...")
    
    mcp_client = MCPStdioClient(
        server_script_path="../cyberres-mcp/src/cyberres_mcp/server.py"
    )
    
    tool_coordinator = ToolCoordinator(cache_ttl=300)
    state_manager = StateManager(state_file="ollama_workflow_state.json")
    feature_flags = FeatureFlags({
        "use_tool_coordinator": True,
        "parallel_tool_execution": True,
        "ai_classification": True,
        "ai_reporting": True
    })
    
    # Use Ollama for all agents
    agent_config = AgentConfig(
        model="ollama:llama3",  # Local Llama 3
        temperature=0.1
    )
    
    print("✅ Components initialized with Ollama")
    print("   Model: ollama:llama3 (local)")
    print("   No API costs!")
    
    try:
        await mcp_client.connect()
        print("✅ MCP client connected")
        
        # Create agents
        print("\n2. Creating agents with Ollama...")
        discovery_agent = EnhancedDiscoveryAgent(
            mcp_client=mcp_client,
            config=agent_config,
            tool_coordinator=tool_coordinator,
            state_manager=state_manager,
            feature_flags=feature_flags
        )
        
        classification_agent = ClassificationAgent(
            config=agent_config,
            feature_flags=feature_flags
        )
        
        reporting_agent = ReportingAgent(
            config=agent_config,
            feature_flags=feature_flags
        )
        print("✅ All agents created with Ollama")
        
        # Create test resource
        print("\n3. Creating test resource...")
        resource = VMResourceInfo(
            host="test-server-ollama",
            resource_type=ResourceType.VM,
            ssh_user="admin",
            ssh_port=22
        )
        print(f"✅ Resource: {resource.host}")
        
        # Execute workflow
        workflow_id = f"ollama_test_{int(datetime.now().timestamp())}"
        
        print("\n4. Phase 1: Discovery...")
        discovery_result = await discovery_agent.discover(
            resource=resource,
            workflow_id=workflow_id
        )
        print(f"✅ Discovery complete")
        
        print("\n5. Phase 2: Classification (using Ollama)...")
        classification = await classification_agent.classify(
            discovery_result=discovery_result,
            workflow_id=workflow_id
        )
        print(f"✅ Classification: {classification.category.value}")
        
        print("\n6. Phase 3: Reporting (using Ollama)...")
        from models import ResourceValidationResult, ValidationStatus
        validation_result = ResourceValidationResult(
            resource_type=resource.resource_type,
            resource_host=resource.host,
            overall_status=ValidationStatus.PASS,
            score=95,
            checks=[],
            execution_time_seconds=10.0
        )
        
        report = await reporting_agent.generate_report(
            validation_result=validation_result,
            discovery_result=discovery_result,
            classification=classification,
            format="markdown"
        )
        print(f"✅ Report generated")
        
        # Save report
        report_file = f"ollama_workflow_report_{workflow_id}.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"✅ Report saved: {report_file}")
        
        print("\n" + "=" * 80)
        print("✅ Complete Ollama workflow test successful!")
        print("=" * 80)
        print(f"\nWorkflow ID: {workflow_id}")
        print(f"Report: {report_file}")
        print(f"Model Used: ollama:llama3 (local)")
        print(f"API Cost: $0.00 (free!)")
        
    finally:
        await mcp_client.disconnect()
        print("\n✅ MCP client disconnected")


if __name__ == "__main__":
    asyncio.run(test_complete_workflow_ollama())
```

---

## Model Comparison

### Recommended Models for Different Use Cases

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| **llama3** | 8B | Fast | Good | General testing, development |
| **mistral** | 7B | Very Fast | Good | Quick iterations, prototyping |
| **codellama** | 7B | Fast | Good | Technical content, code analysis |
| **llama3:70b** | 70B | Slow | Excellent | Production-like quality testing |
| **mixtral** | 8x7B | Medium | Excellent | Best balance of speed/quality |

### Performance Comparison

```bash
# Test different models
ollama run llama3 "Classify this server: ports 80,443 open, nginx running"
ollama run mistral "Classify this server: ports 80,443 open, nginx running"
ollama run codellama "Classify this server: ports 80,443 open, nginx running"
```

---

## Configuration Examples

### .env File for Ollama

```bash
# .env file for Ollama testing

# Use Ollama instead of OpenAI
AGENT_MODEL=ollama:llama3

# No API key needed
# OPENAI_API_KEY=  # Leave empty

# Ollama server (default)
OLLAMA_HOST=http://localhost:11434

# Feature flags
FEATURE_FLAG_AI_CLASSIFICATION=true
FEATURE_FLAG_AI_REPORTING=true
```

### Python Configuration

```python
import os
from agents.base import AgentConfig

# Get model from environment or use default
model = os.getenv("AGENT_MODEL", "ollama:llama3")

config = AgentConfig(
    model=model,
    temperature=0.1,
    max_tokens=4000
)

print(f"Using model: {model}")
```

---

## Running Tests with Ollama

### Quick Test Commands

```bash
cd python/src

# Make sure Ollama is running
# In separate terminal: ollama serve

# Test classification with Ollama
python test_classification_ollama.py

# Test reporting with Ollama
python test_reporting_ollama.py

# Test complete workflow with Ollama
python test_complete_workflow_ollama.py
```

### Switching Between Models

```bash
# Test with Llama 3
AGENT_MODEL=ollama:llama3 python test_classification_ollama.py

# Test with Mistral
AGENT_MODEL=ollama:mistral python test_classification_ollama.py

# Test with CodeLlama
AGENT_MODEL=ollama:codellama python test_classification_ollama.py

# Test with Llama 3 70B (requires more RAM)
AGENT_MODEL=ollama:llama3:70b python test_classification_ollama.py
```

---

## Performance Tips

### 1. Model Selection
- **Development**: Use `llama3` or `mistral` (fast)
- **Testing**: Use `llama3` (good balance)
- **Production-like**: Use `llama3:70b` or `mixtral` (best quality)

### 2. Hardware Requirements

| Model | RAM Required | GPU | Speed |
|-------|-------------|-----|-------|
| llama3 (8B) | 8GB | Optional | Fast |
| mistral (7B) | 8GB | Optional | Very Fast |
| llama3:70b | 64GB | Recommended | Slow |
| mixtral (8x7B) | 32GB | Recommended | Medium |

### 3. Optimization

```bash
# Use GPU acceleration (if available)
ollama run llama3 --gpu

# Adjust context window
ollama run llama3 --ctx-size 4096

# Adjust temperature
ollama run llama3 --temperature 0.1
```

---

## Troubleshooting

### Issue: Ollama Not Found

```bash
# Install Ollama
brew install ollama  # macOS
# or
curl -fsSL https://ollama.ai/install.sh | sh  # Linux
```

### Issue: Model Not Found

```bash
# Pull the model
ollama pull llama3

# List available models
ollama list
```

### Issue: Ollama Server Not Running

```bash
# Start Ollama server
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### Issue: Out of Memory

```bash
# Use smaller model
ollama pull mistral  # 7B instead of 70B

# Or increase swap space (Linux)
sudo swapon --show
```

---

## Comparison: OpenAI vs Ollama

| Aspect | OpenAI GPT-4 | Ollama Llama 3 |
|--------|-------------|----------------|
| **Cost** | $0.03/1K tokens | Free |
| **Speed** | Fast (network) | Very Fast (local) |
| **Quality** | Excellent | Good-Very Good |
| **Privacy** | Cloud | Local |
| **Internet** | Required | Not required |
| **Setup** | API key | Install Ollama |

---

## Best Practices

### 1. Development Workflow

```bash
# 1. Develop with Ollama (fast, free)
AGENT_MODEL=ollama:llama3 python test_classification.py

# 2. Test with Ollama (validate logic)
AGENT_MODEL=ollama:llama3 python test_complete_workflow.py

# 3. Final test with OpenAI (production quality)
AGENT_MODEL=openai:gpt-4 python test_complete_workflow.py
```

### 2. Cost Optimization

- **Development**: 100% Ollama (free)
- **Testing**: 90% Ollama, 10% OpenAI
- **Production**: OpenAI/Anthropic (best quality)

### 3. Quality Validation

```python
# Test with both models and compare
models = ["ollama:llama3", "openai:gpt-4"]

for model in models:
    config = AgentConfig(model=model)
    agent = ClassificationAgent(config=config)
    result = await agent.classify(discovery_result)
    print(f"{model}: {result.category.value} ({result.confidence:.0%})")
```

---

## Summary

✅ **Ollama enables free, local testing** of AI-powered agents  
✅ **No API costs** during development  
✅ **Fast iteration** with local models  
✅ **Privacy** - data stays local  
✅ **Easy setup** - just install Ollama and pull models  
✅ **Multiple models** - choose based on speed/quality needs  
✅ **Production-ready** - test locally, deploy with OpenAI  

---

## Quick Start

```bash
# 1. Install Ollama
brew install ollama

# 2. Pull model
ollama pull llama3

# 3. Start server
ollama serve

# 4. Run tests (in another terminal)
cd python/src
AGENT_MODEL=ollama:llama3 python test_classification_ollama.py
```

**You're now ready to test with local LLMs!** 🎉

---

*Made with Bob - AI Assistant*