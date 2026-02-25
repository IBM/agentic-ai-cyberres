# Phase 2 Testing Guide

## How to Test the Enhanced Agentic Workflow

This guide shows you how to test the Phase 2 implementation with the MCP server and enhanced agents.

---

## Prerequisites

### 1. Install Dependencies

```bash
cd python/src

# Install Python dependencies
uv pip install pydantic pydantic-ai openai anthropic

# Or using pip
pip install pydantic pydantic-ai openai anthropic
```

### 2. Set Up Environment Variables

Create a `.env` file in `python/src/`:

```bash
# OpenAI API Key (for AI features)
OPENAI_API_KEY=your_openai_api_key_here

# Or Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Feature Flags (optional, defaults are set)
FEATURE_FLAG_USE_TOOL_COORDINATOR=true
FEATURE_FLAG_PARALLEL_TOOL_EXECUTION=false
FEATURE_FLAG_AI_CLASSIFICATION=true
FEATURE_FLAG_AI_REPORTING=true
```

### 3. Start MCP Server

In a separate terminal:

```bash
cd python/cyberres-mcp

# Start the MCP server
uv run mcp dev src/cyberres_mcp/server.py
```

The server should start on `stdio` mode.

---

## Test 1: Basic Enhanced Discovery Agent

### Create Test Script: `test_enhanced_discovery.py`

```python
#!/usr/bin/env python3
"""Test enhanced discovery agent."""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from models import VMResourceInfo, ResourceType
from mcp_stdio_client import MCPStdioClient
from tool_coordinator import ToolCoordinator
from state_manager import StateManager
from feature_flags import FeatureFlags
from agents.discovery_agent_enhanced import EnhancedDiscoveryAgent
from agents.base import AgentConfig


async def test_enhanced_discovery():
    """Test enhanced discovery agent."""
    print("=" * 80)
    print("Testing Enhanced Discovery Agent")
    print("=" * 80)
    
    # Step 1: Initialize MCP client
    print("\n1. Initializing MCP client...")
    mcp_client = MCPStdioClient(
        server_script_path="../cyberres-mcp/src/cyberres_mcp/server.py"
    )
    
    try:
        await mcp_client.connect()
        print("✅ MCP client connected")
        
        # Step 2: Initialize Phase 1 components
        print("\n2. Initializing Phase 1 components...")
        tool_coordinator = ToolCoordinator(cache_ttl=300)
        state_manager = StateManager(state_file="test_workflow_state.json")
        feature_flags = FeatureFlags({
            "use_tool_coordinator": True,
            "parallel_tool_execution": True,
            "enable_tool_caching": True
        })
        print("✅ Components initialized")
        print(f"   - Tool Coordinator: cache_ttl=300s")
        print(f"   - State Manager: test_workflow_state.json")
        print(f"   - Feature Flags: {feature_flags.get_enabled()}")
        
        # Step 3: Create enhanced discovery agent
        print("\n3. Creating Enhanced Discovery Agent...")
        agent = EnhancedDiscoveryAgent(
            mcp_client=mcp_client,
            config=AgentConfig(
                model="openai:gpt-4",
                temperature=0.1
            ),
            tool_coordinator=tool_coordinator,
            state_manager=state_manager,
            feature_flags=feature_flags
        )
        print("✅ Enhanced Discovery Agent created")
        
        # Step 4: Create test resource
        print("\n4. Creating test resource...")
        resource = VMResourceInfo(
            host="test-server-01",
            resource_type=ResourceType.VM,
            ssh_user="admin",
            ssh_port=22,
            ssh_key_path="~/.ssh/id_rsa"
        )
        print(f"✅ Test resource: {resource.host}")
        
        # Step 5: Run discovery
        print("\n5. Running enhanced discovery...")
        print("   This will:")
        print("   - Create AI-powered discovery plan")
        print("   - Execute scans with retry and caching")
        print("   - Use parallel execution if enabled")
        print("   - Save state for resume capability")
        
        workflow_id = f"test_workflow_{int(datetime.now().timestamp())}"
        
        result = await agent.discover(
            resource=resource,
            workflow_id=workflow_id
        )
        
        print("\n✅ Discovery completed!")
        print(f"   - Workflow ID: {workflow_id}")
        print(f"   - Ports found: {len(result.ports)}")
        print(f"   - Processes found: {len(result.processes)}")
        print(f"   - Applications detected: {len(result.applications)}")
        
        # Step 6: Show execution history
        print("\n6. Execution History:")
        history = agent.get_execution_history()
        for i, record in enumerate(history[-5:], 1):  # Last 5 records
            print(f"   {i}. {record['action']} at {record['timestamp']}")
        
        # Step 7: Show state
        print("\n7. Workflow State:")
        state = await state_manager.get_current_state()
        print(f"   - Current State: {state.current_state}")
        print(f"   - Transitions: {len(state.history)}")
        
        print("\n" + "=" * 80)
        print("✅ Test completed successfully!")
        print("=" * 80)
        
    finally:
        await mcp_client.disconnect()
        print("\n✅ MCP client disconnected")


if __name__ == "__main__":
    asyncio.run(test_enhanced_discovery())
```

### Run the Test

```bash
cd python/src
python test_enhanced_discovery.py
```

---

## Test 2: AI-Powered Classification

### Create Test Script: `test_classification.py`

```python
#!/usr/bin/env python3
"""Test AI-powered classification agent."""

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

from models import (
    WorkloadDiscoveryResult, PortInfo, ProcessInfo, 
    ApplicationDetection, ResourceType
)
from agents.classification_agent import ClassificationAgent
from agents.base import AgentConfig
from feature_flags import FeatureFlags


async def test_classification():
    """Test classification agent."""
    print("=" * 80)
    print("Testing AI-Powered Classification Agent")
    print("=" * 80)
    
    # Step 1: Create mock discovery result
    print("\n1. Creating mock discovery result...")
    discovery_result = WorkloadDiscoveryResult(
        host="db-server-01",
        ports=[
            PortInfo(port=22, protocol="tcp", state="open", service="ssh"),
            PortInfo(port=1521, protocol="tcp", state="open", service="oracle"),
            PortInfo(port=5500, protocol="tcp", state="open", service="oracle-em"),
        ],
        processes=[
            ProcessInfo(pid=1234, name="oracle", user="oracle", 
                       command="/u01/app/oracle/product/19c/bin/oracle"),
            ProcessInfo(pid=1235, name="tnslsnr", user="oracle",
                       command="/u01/app/oracle/product/19c/bin/tnslsnr"),
        ],
        applications=[
            ApplicationDetection(
                name="Oracle Database",
                version="19c",
                confidence=0.95,
                detection_method="port_and_process"
            )
        ],
        discovery_time=datetime.now()
    )
    print(f"✅ Mock discovery result created for {discovery_result.host}")
    print(f"   - {len(discovery_result.ports)} ports")
    print(f"   - {len(discovery_result.processes)} processes")
    print(f"   - {len(discovery_result.applications)} applications")
    
    # Step 2: Create classification agent
    print("\n2. Creating Classification Agent...")
    feature_flags = FeatureFlags({"ai_classification": True})
    
    agent = ClassificationAgent(
        config=AgentConfig(
            model="openai:gpt-4",
            temperature=0.1
        ),
        feature_flags=feature_flags
    )
    print("✅ Classification Agent created (AI enabled)")
    
    # Step 3: Classify resource
    print("\n3. Running AI-powered classification...")
    print("   This will:")
    print("   - Analyze ports, processes, and applications")
    print("   - Use AI to determine resource category")
    print("   - Provide confidence score and reasoning")
    print("   - Recommend validation strategies")
    
    classification = await agent.classify(discovery_result)
    
    print("\n✅ Classification completed!")
    print(f"   - Category: {classification.category.value}")
    print(f"   - Confidence: {classification.confidence:.0%}")
    if classification.primary_application:
        print(f"   - Primary App: {classification.primary_application.name}")
    print(f"   - Reasoning: {classification.reasoning}")
    print(f"   - Recommended Validations: {', '.join(classification.recommended_validations)}")
    
    print("\n" + "=" * 80)
    print("✅ Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_classification())
```

### Run the Test

```bash
cd python/src
python test_classification.py
```

---

## Test 3: AI-Powered Reporting

### Create Test Script: `test_reporting.py`

```python
#!/usr/bin/env python3
"""Test AI-powered reporting agent."""

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

from models import (
    ResourceValidationResult, CheckResult, ValidationStatus,
    ResourceType, WorkloadDiscoveryResult, ResourceClassification,
    ResourceCategory, ApplicationDetection
)
from agents.reporting_agent import ReportingAgent
from agents.base import AgentConfig
from feature_flags import FeatureFlags


async def test_reporting():
    """Test reporting agent."""
    print("=" * 80)
    print("Testing AI-Powered Reporting Agent")
    print("=" * 80)
    
    # Step 1: Create mock validation result
    print("\n1. Creating mock validation result...")
    validation_result = ResourceValidationResult(
        resource_type=ResourceType.VM,
        resource_host="web-server-01",
        overall_status=ValidationStatus.WARNING,
        score=75,
        checks=[
            CheckResult(
                check_id="net_001",
                check_name="Network Connectivity",
                status=ValidationStatus.PASS,
                message="Port 22 is accessible"
            ),
            CheckResult(
                check_id="web_001",
                check_name="HTTP Port Check",
                status=ValidationStatus.PASS,
                message="Ports 80 and 443 are accessible"
            ),
            CheckResult(
                check_id="sys_001",
                check_name="System Resources",
                status=ValidationStatus.WARNING,
                message="CPU usage is at 85%",
                expected="CPU usage < 80%",
                actual="CPU usage = 85%"
            ),
        ],
        execution_time_seconds=12.5
    )
    print(f"✅ Mock validation result created")
    print(f"   - Score: {validation_result.score}/100")
    print(f"   - Status: {validation_result.overall_status.value}")
    print(f"   - Checks: {len(validation_result.checks)}")
    
    # Step 2: Create reporting agent
    print("\n2. Creating Reporting Agent...")
    feature_flags = FeatureFlags({"ai_reporting": True})
    
    agent = ReportingAgent(
        config=AgentConfig(
            model="openai:gpt-4",
            temperature=0.3,  # Slightly higher for natural writing
            max_tokens=8000
        ),
        feature_flags=feature_flags
    )
    print("✅ Reporting Agent created (AI enabled)")
    
    # Step 3: Generate report
    print("\n3. Generating AI-powered report...")
    print("   This will:")
    print("   - Analyze validation results")
    print("   - Create executive summary")
    print("   - Identify key findings and critical issues")
    print("   - Provide actionable recommendations")
    print("   - Format in professional markdown")
    
    report = await agent.generate_report(
        validation_result=validation_result,
        format="markdown"
    )
    
    print("\n✅ Report generated!")
    print(f"   - Length: {len(report)} characters")
    print(f"   - Format: markdown")
    
    # Step 4: Display report
    print("\n4. Generated Report:")
    print("=" * 80)
    print(report)
    print("=" * 80)
    
    # Step 5: Save report
    report_file = f"validation_report_{int(datetime.now().timestamp())}.md"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\n✅ Report saved to: {report_file}")
    
    print("\n" + "=" * 80)
    print("✅ Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_reporting())
```

### Run the Test

```bash
cd python/src
python test_reporting.py
```

---

## Test 4: Complete Workflow Integration

### Create Test Script: `test_complete_workflow.py`

```python
#!/usr/bin/env python3
"""Test complete enhanced workflow."""

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


async def test_complete_workflow():
    """Test complete enhanced workflow."""
    print("=" * 80)
    print("Testing Complete Enhanced Workflow")
    print("=" * 80)
    
    # Initialize components
    print("\n1. Initializing all components...")
    
    mcp_client = MCPStdioClient(
        server_script_path="../cyberres-mcp/src/cyberres_mcp/server.py"
    )
    
    tool_coordinator = ToolCoordinator(cache_ttl=300)
    state_manager = StateManager(state_file="complete_workflow_state.json")
    feature_flags = FeatureFlags({
        "use_tool_coordinator": True,
        "parallel_tool_execution": True,
        "ai_classification": True,
        "ai_reporting": True
    })
    
    agent_config = AgentConfig(model="openai:gpt-4", temperature=0.1)
    
    print("✅ Components initialized")
    
    try:
        await mcp_client.connect()
        print("✅ MCP client connected")
        
        # Create agents
        print("\n2. Creating agents...")
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
        print("✅ All agents created")
        
        # Create test resource
        print("\n3. Creating test resource...")
        resource = VMResourceInfo(
            host="test-app-server",
            resource_type=ResourceType.VM,
            ssh_user="admin",
            ssh_port=22
        )
        print(f"✅ Resource: {resource.host}")
        
        # Execute workflow
        workflow_id = f"complete_test_{int(datetime.now().timestamp())}"
        
        print("\n4. Phase 1: Discovery...")
        discovery_result = await discovery_agent.discover(
            resource=resource,
            workflow_id=workflow_id
        )
        print(f"✅ Discovery complete: {len(discovery_result.applications)} apps found")
        
        print("\n5. Phase 2: Classification...")
        classification = await classification_agent.classify(
            discovery_result=discovery_result,
            workflow_id=workflow_id
        )
        print(f"✅ Classification: {classification.category.value} ({classification.confidence:.0%})")
        
        print("\n6. Phase 3: Reporting...")
        # Create mock validation result for reporting
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
        print(f"✅ Report generated: {len(report)} characters")
        
        # Save report
        report_file = f"complete_workflow_report_{workflow_id}.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"✅ Report saved: {report_file}")
        
        print("\n" + "=" * 80)
        print("✅ Complete workflow test successful!")
        print("=" * 80)
        print(f"\nWorkflow ID: {workflow_id}")
        print(f"Report: {report_file}")
        print(f"State: complete_workflow_state.json")
        
    finally:
        await mcp_client.disconnect()
        print("\n✅ MCP client disconnected")


if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
```

### Run the Test

```bash
cd python/src
python test_complete_workflow.py
```

---

## Test 5: Feature Flag Testing

### Create Test Script: `test_feature_flags.py`

```python
#!/usr/bin/env python3
"""Test feature flag behavior."""

import asyncio
from feature_flags import FeatureFlags


def test_feature_flags():
    """Test feature flags."""
    print("=" * 80)
    print("Testing Feature Flags")
    print("=" * 80)
    
    # Test 1: Default flags
    print("\n1. Testing default flags...")
    flags = FeatureFlags()
    print(f"   Enabled flags: {flags.get_enabled()}")
    print(f"   Disabled flags: {flags.get_disabled()}")
    
    # Test 2: Custom flags
    print("\n2. Testing custom flags...")
    custom_flags = FeatureFlags({
        "use_tool_coordinator": True,
        "parallel_tool_execution": True,
        "ai_classification": True,
        "ai_reporting": True
    })
    print(f"   Enabled: {custom_flags.get_enabled()}")
    
    # Test 3: Enable/disable
    print("\n3. Testing enable/disable...")
    custom_flags.disable("parallel_tool_execution")
    print(f"   After disable: parallel_tool_execution = {custom_flags.is_enabled('parallel_tool_execution')}")
    
    custom_flags.enable("parallel_tool_execution")
    print(f"   After enable: parallel_tool_execution = {custom_flags.is_enabled('parallel_tool_execution')}")
    
    # Test 4: Check specific flags
    print("\n4. Checking Phase 2 flags...")
    phase2_flags = [
        "parallel_tool_execution",
        "ai_classification",
        "ai_reporting",
        "ai_plan_optimization",
        "auto_resume_workflows"
    ]
    
    for flag in phase2_flags:
        status = "✅ Enabled" if custom_flags.is_enabled(flag) else "❌ Disabled"
        print(f"   {flag}: {status}")
    
    print("\n" + "=" * 80)
    print("✅ Feature flag tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_feature_flags()
```

### Run the Test

```bash
cd python/src
python test_feature_flags.py
```

---

## Quick Test Commands

### Test Everything at Once

```bash
cd python/src

# Run all tests
python test_feature_flags.py
python test_classification.py
python test_reporting.py
python test_enhanced_discovery.py
python test_complete_workflow.py
```

### Test with Different Feature Flag Combinations

```bash
# Test with AI disabled
FEATURE_FLAG_AI_CLASSIFICATION=false python test_classification.py

# Test with parallel execution enabled
FEATURE_FLAG_PARALLEL_TOOL_EXECUTION=true python test_enhanced_discovery.py

# Test with all features enabled
FEATURE_FLAG_USE_TOOL_COORDINATOR=true \
FEATURE_FLAG_PARALLEL_TOOL_EXECUTION=true \
FEATURE_FLAG_AI_CLASSIFICATION=true \
FEATURE_FLAG_AI_REPORTING=true \
python test_complete_workflow.py
```

---

## Expected Output

### Successful Test Output

```
================================================================================
Testing Enhanced Discovery Agent
================================================================================

1. Initializing MCP client...
✅ MCP client connected

2. Initializing Phase 1 components...
✅ Components initialized
   - Tool Coordinator: cache_ttl=300s
   - State Manager: test_workflow_state.json
   - Feature Flags: ['use_tool_coordinator', 'parallel_tool_execution', ...]

3. Creating Enhanced Discovery Agent...
✅ Enhanced Discovery Agent created

4. Creating test resource...
✅ Test resource: test-server-01

5. Running enhanced discovery...
   This will:
   - Create AI-powered discovery plan
   - Execute scans with retry and caching
   - Use parallel execution if enabled
   - Save state for resume capability

✅ Discovery completed!
   - Workflow ID: test_workflow_1234567890
   - Ports found: 5
   - Processes found: 12
   - Applications detected: 3

6. Execution History:
   1. tool_execution:workload_scan_ports at 2026-02-23T15:00:00
   2. tool_execution:workload_scan_processes at 2026-02-23T15:00:05
   3. tool_execution:workload_detect_applications at 2026-02-23T15:00:10
   4. tool_execution:workload_aggregate_results at 2026-02-23T15:00:15
   5. discovery_complete at 2026-02-23T15:00:20

7. Workflow State:
   - Current State: DISCOVERY
   - Transitions: 2

================================================================================
✅ Test completed successfully!
================================================================================
```

---

## Troubleshooting

### Issue: Import Errors

```bash
# Install missing dependencies
cd python/src
uv pip install pydantic pydantic-ai openai
```

### Issue: MCP Server Not Starting

```bash
# Check MCP server
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py

# Check for errors in server logs
```

### Issue: API Key Not Found

```bash
# Set API key
export OPENAI_API_KEY=your_key_here

# Or create .env file
echo "OPENAI_API_KEY=your_key_here" > python/src/.env
```

### Issue: Feature Flags Not Working

```python
# Check feature flags
from feature_flags import FeatureFlags
flags = FeatureFlags()
print(flags.get_all())
```

---

## Next Steps

1. **Run Basic Tests**: Start with `test_feature_flags.py` and `test_classification.py`
2. **Test with MCP**: Run `test_enhanced_discovery.py` with MCP server running
3. **Complete Workflow**: Run `test_complete_workflow.py` for end-to-end test
4. **Create Unit Tests**: Add proper unit tests with mocking
5. **Performance Testing**: Measure cache hit rates and execution times

---

## Summary

You now have 5 comprehensive test scripts to validate the Phase 2 implementation:

1. **test_feature_flags.py** - Test feature flag system
2. **test_classification.py** - Test AI-powered classification
3. **test_reporting.py** - Test AI-powered reporting
4. **test_enhanced_discovery.py** - Test enhanced discovery with MCP
5. **test_complete_workflow.py** - Test complete workflow integration

All tests are ready to run and will demonstrate the new capabilities!

---

*Made with Bob - AI Assistant*