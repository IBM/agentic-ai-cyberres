#!/usr/bin/env python3
"""
Test Dynamic Tool Discovery - MCP Best Practices

This script demonstrates the Phase 3 enhancement: dynamic tool discovery.

Usage:
    python test_tool_discovery.py
"""

import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_stdio_client import MCPStdioClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_tool_discovery():
    """Test dynamic tool discovery."""
    
    print("\n" + "="*80)
    print("🧪 TESTING DYNAMIC TOOL DISCOVERY - MCP Best Practices")
    print("="*80)
    
    # Initialize MCP client
    print("\n📡 Step 1: Initializing MCP client...")
    mcp_client = MCPStdioClient(
        server_command="uv",
        server_args=["run", "mcp", "dev", "../cyberres-mcp/src/cyberres_mcp/server.py"]
    )
    
    try:
        # Connect to MCP server (automatically discovers tools)
        print("\n🔌 Step 2: Connecting to MCP server...")
        await mcp_client.connect()
        print("   ✅ Connected successfully!")
        
        # Get discovered tools
        print("\n🔍 Step 3: Querying discovered tools...")
        available_tools = mcp_client.get_available_tools()
        
        print(f"\n✅ Discovered {len(available_tools)} MCP tools:")
        print("-" * 80)
        
        # Group tools by category
        discovery_tools = []
        validation_tools = []
        network_tools = []
        utility_tools = []
        
        for tool in available_tools:
            if "discover" in tool or "raw" in tool:
                discovery_tools.append(tool)
            elif "validate" in tool:
                validation_tools.append(tool)
            elif "network" in tool or "port" in tool or "tcp" in tool:
                network_tools.append(tool)
            else:
                utility_tools.append(tool)
        
        # Display by category
        if discovery_tools:
            print("\n📦 Discovery Tools:")
            for tool in discovery_tools:
                desc = mcp_client.get_tool_description(tool)
                print(f"   • {tool}")
                if desc:
                    print(f"     {desc[:70]}...")
        
        if validation_tools:
            print("\n✅ Validation Tools:")
            for tool in validation_tools:
                desc = mcp_client.get_tool_description(tool)
                print(f"   • {tool}")
                if desc:
                    print(f"     {desc[:70]}...")
        
        if network_tools:
            print("\n🌐 Network Tools:")
            for tool in network_tools:
                desc = mcp_client.get_tool_description(tool)
                print(f"   • {tool}")
                if desc:
                    print(f"     {desc[:70]}...")
        
        if utility_tools:
            print("\n🔧 Utility Tools:")
            for tool in utility_tools:
                desc = mcp_client.get_tool_description(tool)
                print(f"   • {tool}")
                if desc:
                    print(f"     {desc[:70]}...")
        
        # Test tool availability checking
        print("\n" + "="*80)
        print("🧪 Step 4: Testing tool availability checking...")
        print("-" * 80)
        
        test_tools = [
            "discover_applications",
            "discover_os_only",
            "validate_oracle_db",
            "validate_mongodb",
            "validate_vm_linux",
            "nonexistent_tool"
        ]
        
        for tool in test_tools:
            exists = mcp_client.has_tool(tool)
            status = "✅ Available" if exists else "❌ Not Available"
            print(f"   {tool}: {status}")
        
        # Demonstrate usage pattern
        print("\n" + "="*80)
        print("💡 Step 5: Demonstrating usage pattern...")
        print("-" * 80)
        
        print("\n📝 Example: How an agent would use this")
        print("""
# Agent checks if tool exists before calling
if mcp_client.has_tool("discover_applications"):
    result = await mcp_client.call_tool("discover_applications", {
        "host": "db-server-01",
        "ssh_user": "admin",
        "ssh_password": "secret"
    })
    # Process result...
else:
    # Fallback to alternative method
    print("Tool not available, using fallback...")
        """)
        
        # Summary
        print("\n" + "="*80)
        print("✅ TEST COMPLETE - Dynamic Tool Discovery Working!")
        print("="*80)
        
        print(f"\n📊 Summary:")
        print(f"   • Total tools discovered: {len(available_tools)}")
        print(f"   • Discovery tools: {len(discovery_tools)}")
        print(f"   • Validation tools: {len(validation_tools)}")
        print(f"   • Network tools: {len(network_tools)}")
        print(f"   • Utility tools: {len(utility_tools)}")
        
        print(f"\n🎯 Key Benefits:")
        print(f"   ✅ No hardcoded tool names")
        print(f"   ✅ Agent adapts to available tools")
        print(f"   ✅ Graceful handling of missing tools")
        print(f"   ✅ Easy to add new tools to MCP server")
        
        print(f"\n📚 Next Steps:")
        print(f"   1. Update agents to use get_available_tools()")
        print(f"   2. Add tool selection logic based on classification")
        print(f"   3. Test complete workflow with real server")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        return False
    
    finally:
        # Disconnect
        print("\n🔌 Disconnecting from MCP server...")
        await mcp_client.disconnect()
        print("   ✅ Disconnected")
    
    return True


async def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("🚀 MCP BEST PRACTICES - Dynamic Tool Discovery Test")
    print("="*80)
    print("\nThis test demonstrates Phase 3 enhancement:")
    print("  • MCP client discovers tools dynamically at runtime")
    print("  • Agent can query available tools")
    print("  • Agent checks tool availability before calling")
    print("  • No hardcoded tool names!")
    
    success = await test_tool_discovery()
    
    if success:
        print("\n" + "="*80)
        print("🎉 SUCCESS! Dynamic tool discovery is working!")
        print("="*80)
        print("\nThe MCP client now:")
        print("  ✅ Discovers tools automatically on connection")
        print("  ✅ Provides get_available_tools() method")
        print("  ✅ Provides has_tool(name) method")
        print("  ✅ Provides get_tool_description(name) method")
        print("\nAgents can now adapt to available tools dynamically!")
        print("="*80 + "\n")
    else:
        print("\n" + "="*80)
        print("❌ TEST FAILED - Check logs for details")
        print("="*80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
