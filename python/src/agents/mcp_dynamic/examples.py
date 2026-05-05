"""
Dynamic MCP Integration - Usage Examples

Comprehensive examples showing how to use the dynamic MCP client
for runtime tool discovery and invocation.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .client import DynamicMCPClient, create_client
from .models import ToolInvocation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Usage - Connect, Discover, Invoke
# ============================================================================

async def example_basic_usage():
    """Basic usage: connect, discover tools, invoke one."""
    print("\n" + "="*70)
    print("Example 1: Basic Usage")
    print("="*70)
    
    # Create client
    client = DynamicMCPClient(
        server_path="python/cyberres-mcp",
        transport="stdio",
        auto_discover=True
    )
    
    try:
        # Connect to server
        print("\n1. Connecting to MCP server...")
        await client.connect()
        print(f"   ✓ Connected: {client.is_connected()}")
        
        # List discovered tools
        print("\n2. Listing discovered tools...")
        tools = client.list_tools()
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5
            print(f"     - {tool.name}: {tool.description[:60]}...")
        
        # Get tool info
        print("\n3. Getting tool information...")
        tool_info = client.get_tool_info("discover_workload")
        if tool_info:
            print(f"   ✓ Tool: {tool_info['name']}")
            print(f"     Description: {tool_info['description']}")
            print(f"     Parameters: {len(tool_info['parameters'])} required")
        
        # Invoke a tool
        print("\n4. Invoking tool...")
        result = await client.invoke_tool(
            "discover_workload",
            {
                "host": "9.11.69.88",
                "ssh_user": "admin",
                "ssh_password": "password123"
            }
        )
        print(f"   ✓ Success: {result.success}")
        print(f"     Duration: {result.execution_time_ms}ms")
        if result.result:
            print(f"     Result type: {type(result.result).__name__}")
        
    finally:
        # Disconnect
        print("\n5. Disconnecting...")
        await client.disconnect()
        print("   ✓ Disconnected")


# ============================================================================
# Example 2: Context Manager Usage
# ============================================================================

async def example_context_manager():
    """Using async context manager for automatic cleanup."""
    print("\n" + "="*70)
    print("Example 2: Context Manager Usage")
    print("="*70)
    
    async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
        print("\n✓ Connected via context manager")
        
        # Discover tools
        tools = await client.discover_tools()
        print(f"✓ Discovered {len(tools)} tools")
        
        # Search for specific tools
        db_tools = client.search_tools("database")
        print(f"✓ Found {len(db_tools)} database-related tools")
        
        # Invoke tool
        result = await client.invoke_tool(
            "check_port",
            {"host": "9.11.69.88", "port": 27017}
        )
        print(f"✓ Port check result: {result.success}")
    
    print("✓ Automatically disconnected")


# ============================================================================
# Example 3: Batch Tool Invocation
# ============================================================================

async def example_batch_invocation():
    """Invoke multiple tools in batch."""
    print("\n" + "="*70)
    print("Example 3: Batch Tool Invocation")
    print("="*70)
    
    async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
        # Prepare batch invocations
        invocations = [
            ToolInvocation(
                tool_name="check_port",
                parameters={"host": "9.11.69.88", "port": 27017}
            ),
            ToolInvocation(
                tool_name="check_port",
                parameters={"host": "9.11.69.88", "port": 1521}
            ),
            ToolInvocation(
                tool_name="check_port",
                parameters={"host": "9.11.69.88", "port": 22}
            ),
        ]
        
        print(f"\nInvoking {len(invocations)} tools in batch...")
        results = await client.invoke_tool_batch(invocations)
        
        print(f"✓ Completed {len(results)} invocations:")
        for i, result in enumerate(results, 1):
            status = "✓" if result.success else "✗"
            print(f"  {status} Tool {i}: {result.success} ({result.execution_time_ms}ms)")


# ============================================================================
# Example 4: LLM Integration
# ============================================================================

async def example_llm_integration():
    """Get tool descriptions for LLM context."""
    print("\n" + "="*70)
    print("Example 4: LLM Integration")
    print("="*70)
    
    async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
        # Get LLM-friendly tool descriptions
        llm_tools = client.get_llm_tool_descriptions()
        
        print(f"\n✓ Generated {len(llm_tools)} LLM tool descriptions")
        print("\nExample tool description for LLM:")
        print("-" * 70)
        
        # Show first tool
        if llm_tools:
            tool = llm_tools[0]
            print(f"Name: {tool['name']}")
            print(f"Description: {tool['description']}")
            print(f"Parameters:")
            for param in tool['parameters']:
                required = "required" if param['required'] else "optional"
                print(f"  - {param['name']} ({param['type']}, {required})")
                print(f"    {param['description']}")


# ============================================================================
# Example 5: Hot-Reload and Tool Changes
# ============================================================================

async def example_hot_reload():
    """Monitor tool changes with hot-reload."""
    print("\n" + "="*70)
    print("Example 5: Hot-Reload Monitoring")
    print("="*70)
    
    client = DynamicMCPClient(
        server_path="python/cyberres-mcp",
        enable_hot_reload=True  # Enable hot-reload
    )
    
    try:
        await client.connect()
        print("✓ Connected with hot-reload enabled")
        
        # Initial tool count
        initial_tools = client.list_tool_names()
        print(f"✓ Initial tools: {len(initial_tools)}")
        
        # Simulate monitoring (in real usage, this would run continuously)
        print("\nMonitoring for tool changes...")
        print("(In production, this would detect when MCP server adds/removes tools)")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Check for changes
        current_tools = client.list_tool_names()
        if set(current_tools) != set(initial_tools):
            print("✓ Tool changes detected!")
        else:
            print("✓ No changes detected (as expected in this example)")
        
    finally:
        await client.disconnect()


# ============================================================================
# Example 6: Error Handling
# ============================================================================

async def example_error_handling():
    """Demonstrate error handling."""
    print("\n" + "="*70)
    print("Example 6: Error Handling")
    print("="*70)
    
    async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
        # 1. Invalid tool name
        print("\n1. Testing invalid tool name...")
        result = await client.invoke_tool(
            "nonexistent_tool",
            {"param": "value"}
        )
        print(f"   Result: success={result.success}, error={result.error}")
        
        # 2. Invalid parameters
        print("\n2. Testing invalid parameters...")
        result = await client.invoke_tool(
            "discover_workload",
            {"invalid_param": "value"}  # Missing required params
        )
        print(f"   Result: success={result.success}, error={result.error}")
        
        # 3. Tool execution failure
        print("\n3. Testing tool execution failure...")
        result = await client.invoke_tool(
            "check_port",
            {"host": "invalid.host.name", "port": 9999}
        )
        print(f"   Result: success={result.success}")
        if not result.success:
            print(f"   Error: {result.error}")


# ============================================================================
# Example 7: Statistics and Monitoring
# ============================================================================

async def example_statistics():
    """Get client statistics."""
    print("\n" + "="*70)
    print("Example 7: Statistics and Monitoring")
    print("="*70)
    
    async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
        # Perform some operations
        await client.discover_tools()
        await client.invoke_tool(
            "check_port",
            {"host": "9.11.69.88", "port": 22}
        )
        
        # Get statistics
        stats = client.get_statistics()
        
        print("\n✓ Client Statistics:")
        print(f"  Connected: {stats['connected']}")
        print(f"  Connection State: {stats['connection_state']}")
        print(f"\n  Registry:")
        print(f"    Total Tools: {stats['registry']['total_tools']}")
        print(f"    Categories: {stats['registry']['categories']}")
        print(f"\n  Invoker:")
        print(f"    Total Invocations: {stats['invoker']['total_invocations']}")
        print(f"    Successful: {stats['invoker']['successful_invocations']}")
        print(f"    Failed: {stats['invoker']['failed_invocations']}")


# ============================================================================
# Example 8: Agent Integration Pattern
# ============================================================================

async def example_agent_integration():
    """
    Example of how an agent would use dynamic MCP client.
    
    This shows the pattern for integrating with BeeAI agents.
    """
    print("\n" + "="*70)
    print("Example 8: Agent Integration Pattern")
    print("="*70)
    
    class MyAgent:
        """Example agent using dynamic MCP."""
        
        def __init__(self):
            self.mcp_client: Optional[DynamicMCPClient] = None
        
        async def initialize(self):
            """Initialize agent with MCP client."""
            self.mcp_client = await create_client(
                server_path="python/cyberres-mcp",
                auto_discover=True
            )
            print("✓ Agent initialized with MCP client")
        
        async def execute_task(self, task: Dict[str, Any]):
            """Execute a task using available tools."""
            print(f"\n📋 Executing task: {task['description']}")
            
            if not self.mcp_client:
                raise RuntimeError("MCP client not initialized")
            
            # Get available tools
            tools = self.mcp_client.get_llm_tool_descriptions()
            print(f"   Available tools: {len(tools)}")
            
            # In real usage, LLM would select appropriate tool
            # For this example, we'll use a specific tool
            tool_name = task.get('tool', 'discover_workload')
            parameters = task.get('parameters', {})
            
            print(f"   Using tool: {tool_name}")
            
            # Invoke tool
            result = await self.mcp_client.invoke_tool(tool_name, parameters)
            
            print(f"   ✓ Result: success={result.success}")
            return result
        
        async def cleanup(self):
            """Cleanup agent resources."""
            if self.mcp_client:
                await self.mcp_client.disconnect()
            print("✓ Agent cleaned up")
    
    # Use the agent
    agent = MyAgent()
    try:
        await agent.initialize()
        
        # Execute a task
        result = await agent.execute_task({
            'description': 'Discover workload on host',
            'tool': 'check_port',
            'parameters': {'host': '9.11.69.88', 'port': 22}
        })
        
        print(f"\n✓ Task completed: {result.success}")
        
    finally:
        await agent.cleanup()


# ============================================================================
# Main - Run All Examples
# ============================================================================

async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("DYNAMIC MCP INTEGRATION - USAGE EXAMPLES")
    print("="*70)
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Context Manager", example_context_manager),
        ("Batch Invocation", example_batch_invocation),
        ("LLM Integration", example_llm_integration),
        ("Hot-Reload", example_hot_reload),
        ("Error Handling", example_error_handling),
        ("Statistics", example_statistics),
        ("Agent Integration", example_agent_integration),
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n✗ Example '{name}' failed: {e}")
            logger.exception(f"Example {name} failed")
        
        # Pause between examples
        await asyncio.sleep(1)
    
    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob