"""
Test MCP Integration with BeeAI Framework

This test demonstrates how to:
1. Connect to MCP servers using BeeAI's built-in MCPTool
2. Create agents with MCP tools
3. Execute agent workflows with MCP tool calls
"""

import asyncio
import os
from pathlib import Path

from mcp.client.stdio import StdioServerParameters, stdio_client

from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig
from beeai_framework.tools.mcp import MCPTool


async def test_mcp_connection():
    """Test basic MCP connection and tool discovery."""
    print("\n=== Testing MCP Connection ===")
    
    # Path to MCP server
    server_path = Path(__file__).parent.parent.parent / "cyberres-mcp"
    
    # Create MCP client using stdio
    server_params = StdioServerParameters(
        command="uv",
        args=["--directory", str(server_path), "run", "cyberres-mcp"],
        env={
            **os.environ,
            "MCP_TRANSPORT": "stdio",  # Force stdio mode
            "PYTHONPATH": str(server_path / "src"),
        }
    )
    
    client = stdio_client(server_params)
    
    print(f"Connecting to MCP server at: {server_path}")
    
    try:
        # Load tools from MCP server
        tools = await MCPTool.from_client(client)
        
        print(f"\n✓ Successfully connected to MCP server")
        print(f"✓ Discovered {len(tools)} tools:")
        
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        return tools
    
    except Exception as e:
        print(f"\n✗ Failed to connect to MCP server: {e}")
        raise


async def test_agent_with_mcp_tools():
    """Test creating and running a BeeAI agent with MCP tools."""
    print("\n=== Testing Agent with MCP Tools ===")
    
    # Get MCP tools
    tools = await test_mcp_connection()
    
    # Create LLM (using Ollama for local testing)
    llm = ChatModel.from_name("ollama:llama3.2")
    
    # Create memory
    memory = SlidingMemory(SlidingMemoryConfig(size=50))
    
    # Create RequirementAgent with MCP tools
    agent = RequirementAgent(
        llm=llm,
        memory=memory,
        tools=tools,
        name="CyberRes Discovery Agent",
        description="Agent for discovering and validating infrastructure resources",
        role="Infrastructure Discovery Specialist",
        instructions=[
            "Use available tools to discover and validate infrastructure resources",
            "Always verify connectivity before attempting detailed discovery",
            "Provide clear, structured responses about discovered resources",
        ],
        notes=[
            "Format responses in a clear, structured manner",
            "Include confidence levels for discoveries",
        ],
    )
    
    print(f"\n✓ Created agent: {agent.meta.name}")
    print(f"✓ Agent has {len(agent.meta.tools)} tools available")
    
    return agent


async def test_simple_tool_execution():
    """Test executing a simple MCP tool through BeeAI agent."""
    print("\n=== Testing Simple Tool Execution ===")
    
    agent = await test_agent_with_mcp_tools()
    
    # Simple test query
    query = "Check if host 192.168.1.1 is reachable using ping"
    
    print(f"\nQuery: {query}")
    print("Executing agent...")
    
    try:
        result = await agent.run(query)
        
        print(f"\n✓ Agent execution completed")
        print(f"✓ Result: {result.output}")
        
        if result.output_structured:
            print(f"✓ Structured output: {result.output_structured}")
        
        return result
    
    except Exception as e:
        print(f"\n✗ Agent execution failed: {e}")
        raise


async def test_discovery_workflow():
    """Test a complete discovery workflow using multiple MCP tools."""
    print("\n=== Testing Discovery Workflow ===")
    
    agent = await test_agent_with_mcp_tools()
    
    # Complex discovery query
    query = """
    Discover information about a VM at 192.168.1.100:
    1. First check if it's reachable
    2. If reachable, scan for open ports
    3. Identify the operating system
    4. Detect running applications
    """
    
    print(f"\nQuery: {query}")
    print("Executing multi-step discovery workflow...")
    
    try:
        result = await agent.run(query)
        
        print(f"\n✓ Discovery workflow completed")
        print(f"✓ Final result: {result.output}")
        
        # Show execution steps
        if hasattr(result, 'iterations'):
            print(f"\n✓ Workflow executed in {len(result.iterations)} iterations")
            for i, iteration in enumerate(result.iterations, 1):
                print(f"  Step {i}: {iteration}")
        
        return result
    
    except Exception as e:
        print(f"\n✗ Discovery workflow failed: {e}")
        raise


async def test_react_agent():
    """Test using ReAct agent pattern with MCP tools."""
    print("\n=== Testing ReAct Agent ===")
    
    from beeai_framework.agents.react.agent import ReActAgent
    
    # Get MCP tools
    tools = await test_mcp_connection()
    
    # Create LLM
    llm = ChatModel.from_name("openai:gpt-4")
    
    # Create memory
    memory = SlidingMemory(SlidingMemoryConfig(size=50))
    
    # Create ReAct agent
    agent = ReActAgent(
        llm=llm,
        tools=tools,
        memory=memory,
        meta={
            "name": "ReAct Discovery Agent",
            "description": "Agent using ReAct pattern for infrastructure discovery",
        },
    )
    
    print(f"\n✓ Created ReAct agent")
    
    # Test query
    query = "Check connectivity to 192.168.1.1 and report the result"
    
    print(f"\nQuery: {query}")
    print("Executing ReAct agent...")
    
    try:
        result = await agent.run(query)
        
        print(f"\n✓ ReAct agent execution completed")
        print(f"✓ Result: {result.output}")
        
        return result
    
    except Exception as e:
        print(f"\n✗ ReAct agent execution failed: {e}")
        raise


async def main():
    """Run all tests."""
    print("=" * 60)
    print("BeeAI MCP Integration Tests")
    print("=" * 60)
    
    try:
        # Test 1: Basic MCP connection
        await test_mcp_connection()
        
        # Test 2: Create agent with MCP tools
        await test_agent_with_mcp_tools()
        
        # Test 3: Simple tool execution
        # await test_simple_tool_execution()
        
        # Test 4: Complex discovery workflow
        # await test_discovery_workflow()
        
        # Test 5: ReAct agent pattern
        # await test_react_agent()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
    
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Tests failed: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
