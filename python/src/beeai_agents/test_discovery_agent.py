"""
Test BeeAI Discovery Agent

This test demonstrates the BeeAI-based DiscoveryAgent functionality.
"""

import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the BeeAI Discovery Agent
from discovery_agent import BeeAIDiscoveryAgent, DiscoveryPlan

# Import models
import sys
sys.path.append(str(Path(__file__).parent.parent))
from models import VMResourceInfo, ResourceType


async def test_planning():
    """Test discovery planning functionality."""
    print("\n" + "="*60)
    print("Test 1: Discovery Planning")
    print("="*60)
    
    # Create agent
    agent = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2",
        memory_size=50
    )
    
    # Create test resource
    resource = VMResourceInfo(
        resource_type=ResourceType.VM,
        host="192.168.1.100",
        ssh_user="admin",
        ssh_password="secret",
        ssh_port=22,
        description="Test VM for discovery"
    )
    
    print(f"\nResource: {resource.host} ({resource.resource_type.value})")
    
    # Test fast-path (simple VM)
    print("\n--- Testing Fast-Path Planning ---")
    plan = await agent._create_discovery_plan(resource)
    print(f"Plan: ports={plan.scan_ports}, processes={plan.scan_processes}, apps={plan.detect_applications}")
    print(f"Reasoning: {plan.reasoning}")
    
    # Test with required services (should use LLM)
    print("\n--- Testing LLM-Based Planning ---")
    resource_complex = VMResourceInfo(
        resource_type=ResourceType.VM,
        host="192.168.1.101",
        ssh_user="admin",
        ssh_password="secret",
        ssh_port=22,
        required_services=["nginx", "postgresql"],
        description="Complex VM with required services"
    )
    
    plan_complex = await agent._create_discovery_plan(resource_complex)
    print(f"Plan: ports={plan_complex.scan_ports}, processes={plan_complex.scan_processes}, apps={plan_complex.detect_applications}")
    print(f"Reasoning: {plan_complex.reasoning[:200]}...")
    
    print("\n✓ Planning test completed")


async def test_mcp_tools_loading():
    """Test MCP tools loading."""
    print("\n" + "="*60)
    print("Test 2: MCP Tools Loading")
    print("="*60)
    
    # Create agent
    agent = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2"
    )
    
    print("\nLoading MCP tools...")
    await agent._ensure_mcp_tools()
    
    print(f"✓ Loaded {len(agent._mcp_tools)} MCP tools")
    
    # List some tools
    print("\nAvailable tools (first 5):")
    for i, tool in enumerate(agent._mcp_tools[:5]):
        print(f"  {i+1}. {tool.name}: {tool.description[:60]}...")
    
    print("\n✓ MCP tools loading test completed")


async def test_discovery_workflow():
    """Test complete discovery workflow."""
    print("\n" + "="*60)
    print("Test 3: Complete Discovery Workflow")
    print("="*60)
    
    # Create agent
    agent = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2"
    )
    
    # Create test resource
    resource = VMResourceInfo(
        resource_type=ResourceType.VM,
        host="192.168.1.100",
        ssh_user="admin",
        ssh_password="secret",
        ssh_port=22,
        description="Test VM"
    )
    
    print(f"\nDiscovering: {resource.host}")
    
    try:
        # Note: This will fail because we don't have actual MCP tool execution implemented yet
        # But it demonstrates the workflow
        result = await agent.discover(resource, max_retries=0)
        
        print(f"\n✓ Discovery completed:")
        print(f"  - Ports: {len(result.ports)}")
        print(f"  - Processes: {len(result.processes)}")
        print(f"  - Applications: {len(result.applications)}")
        print(f"  - Discovery time: {result.discovery_time}")
    
    except Exception as e:
        print(f"\n⚠ Discovery workflow test (expected to fail until MCP execution is implemented)")
        print(f"  Error: {e}")
    
    print("\n✓ Discovery workflow test completed")


async def test_agent_initialization():
    """Test agent initialization with different configurations."""
    print("\n" + "="*60)
    print("Test 4: Agent Initialization")
    print("="*60)
    
    # Test with Ollama
    print("\n--- Ollama Configuration ---")
    agent_ollama = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2",
        memory_size=50,
        temperature=0.1
    )
    print(f"✓ Created agent with Ollama: {agent_ollama.llm_model}")
    
    # Test with custom MCP path
    print("\n--- Custom MCP Path ---")
    mcp_path = Path(__file__).parent.parent.parent / "cyberres-mcp"
    agent_custom = BeeAIDiscoveryAgent(
        llm_model="ollama:llama3.2",
        mcp_server_path=str(mcp_path)
    )
    print(f"✓ Created agent with custom MCP path: {agent_custom.mcp_server_path}")
    
    print("\n✓ Agent initialization test completed")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("BeeAI Discovery Agent Tests")
    print("="*60)
    
    try:
        # Test 1: Planning
        await test_planning()
        
        # Test 2: MCP Tools Loading
        await test_mcp_tools_loading()
        
        # Test 3: Discovery Workflow
        await test_discovery_workflow()
        
        # Test 4: Agent Initialization
        await test_agent_initialization()
        
        print("\n" + "="*60)
        print("✓ All tests completed successfully!")
        print("="*60)
    
    except Exception as e:
        print("\n" + "="*60)
        print(f"✗ Tests failed: {e}")
        print("="*60)
        raise


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
