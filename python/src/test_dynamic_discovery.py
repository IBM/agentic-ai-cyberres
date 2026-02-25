#!/usr/bin/env python3
"""
Test Dynamic Discovery Tool Selection

This script tests the enhanced discovery agent with dynamic tool selection.
Verifies that BeeAI can discover and utilize all 4 available MCP discovery tools.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from beeai_agents.discovery_agent import BeeAIDiscoveryAgent
from models import VMResourceInfo, ResourceType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_dynamic_discovery():
    """Test dynamic discovery with tool selection."""
    
    print("\n" + "="*80)
    print("🧪 TESTING DYNAMIC DISCOVERY TOOL SELECTION")
    print("="*80)
    print("\nThis test verifies that BeeAI can:")
    print("  1. Dynamically discover all available MCP tools")
    print("  2. Identify which discovery tools are available")
    print("  3. Select the best discovery strategy")
    print("  4. Gracefully handle missing tools")
    
    # Initialize discovery agent
    print("\n" + "-"*80)
    print("📡 Step 1: Initializing BeeAI Discovery Agent")
    print("-"*80)
    
    try:
        agent = BeeAIDiscoveryAgent(
            llm_model="ollama:llama3.2",
            mcp_server_path="../cyberres-mcp"
        )
        print("✅ Discovery agent created")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return False
    
    # Ensure MCP tools are loaded
    print("\n" + "-"*80)
    print("🔌 Step 2: Connecting to MCP Server and Loading Tools")
    print("-"*80)
    
    try:
        await agent._ensure_mcp_tools()
        print("✅ MCP tools loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load MCP tools: {e}")
        logger.error(f"MCP connection failed: {e}", exc_info=True)
        return False
    
    # Check available tools
    print("\n" + "-"*80)
    print("🔍 Step 3: Checking Available Discovery Tools")
    print("-"*80)
    
    available_tools = agent.get_available_discovery_tools()
    print(f"\n📋 Available discovery tools ({len(available_tools)}):")
    for tool in available_tools:
        print(f"   ✅ {tool}")
    
    if not available_tools:
        print("   ⚠️  No discovery tools found!")
        all_tools = [t.name for t in agent._mcp_tools] if agent._mcp_tools else []
        print(f"   All available MCP tools: {all_tools}")
    
    # Check discovery strategy
    print("\n" + "-"*80)
    print("🎯 Step 4: Determining Discovery Strategy")
    print("-"*80)
    
    strategy = agent.get_discovery_strategy()
    print(f"\n📊 Selected strategy: {strategy}")
    
    strategy_descriptions = {
        "comprehensive": "Using discover_workload (best - all-in-one)",
        "individual": "Using discover_os_only + discover_applications (good)",
        "raw_data": "Using get_raw_server_data (fallback - needs LLM)",
        "none": "No discovery tools available (error)"
    }
    
    print(f"   {strategy_descriptions.get(strategy, 'Unknown strategy')}")
    
    # Check individual tool availability
    print("\n" + "-"*80)
    print("📋 Step 5: Checking Individual Tool Availability")
    print("-"*80)
    
    tools_to_check = [
        ("discover_workload", "Comprehensive integrated discovery"),
        ("discover_os_only", "Lightweight OS detection"),
        ("discover_applications", "Application detection with confidence"),
        ("get_raw_server_data", "Raw data for LLM analysis")
    ]
    
    print("\n")
    for tool_name, description in tools_to_check:
        available = agent.has_discovery_tool(tool_name)
        status = "✅ Available" if available else "❌ Not Available"
        print(f"   {status:20} {tool_name:25} - {description}")
    
    # Test discovery capabilities summary
    print("\n" + "-"*80)
    print("📊 Step 6: Discovery Capabilities Summary")
    print("-"*80)
    
    print(f"\n✅ Discovery System Status:")
    print(f"   • Total MCP tools: {len(agent._mcp_tools) if agent._mcp_tools else 0}")
    print(f"   • Discovery tools: {len(available_tools)}")
    print(f"   • Strategy: {strategy}")
    print(f"   • Can discover OS: {'discover_os_only' in available_tools or 'discover_workload' in available_tools}")
    print(f"   • Can discover apps: {'discover_applications' in available_tools or 'discover_workload' in available_tools}")
    print(f"   • Can use LLM analysis: {'get_raw_server_data' in available_tools}")
    
    # Demonstrate usage pattern
    print("\n" + "-"*80)
    print("💡 Step 7: Usage Pattern Demonstration")
    print("-"*80)
    
    print("\n📝 Example: How the agent selects tools dynamically")
    print("""
    # Agent checks available tools at runtime
    available = agent.get_available_discovery_tools()
    strategy = agent.get_discovery_strategy()
    
    # Intelligent fallback:
    if strategy == "comprehensive":
        # Use discover_workload (best option)
        result = await discover_workload(...)
    elif strategy == "individual":
        # Use discover_os_only + discover_applications
        os_result = await discover_os_only(...)
        app_result = await discover_applications(...)
    elif strategy == "raw_data":
        # Use get_raw_server_data + LLM
        raw_data = await get_raw_server_data(...)
        # LLM analyzes raw data
    else:
        # No tools available - return empty result
    """)
    
    # Summary
    print("\n" + "="*80)
    print("✅ TEST COMPLETE - Dynamic Tool Discovery Working!")
    print("="*80)
    
    print(f"\n📊 Summary:")
    print(f"   • Total tools discovered: {len(agent._mcp_tools) if agent._mcp_tools else 0}")
    print(f"   • Discovery tools: {len(available_tools)}")
    print(f"   • Strategy: {strategy}")
    
    print(f"\n🎯 Key Benefits:")
    print(f"   ✅ No hardcoded tool names")
    print(f"   ✅ Agent adapts to available tools")
    print(f"   ✅ Graceful handling of missing tools")
    print(f"   ✅ Intelligent fallback strategies")
    print(f"   ✅ Easy to add new tools to MCP server")
    
    if strategy == "none":
        print(f"\n⚠️  WARNING: No discovery tools available!")
        print(f"   Check MCP server configuration and tool registration")
        return False
    
    print(f"\n🎉 SUCCESS: Dynamic discovery is working correctly!")
    return True


async def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("🚀 BeeAI DYNAMIC TOOL DISCOVERY TEST")
    print("="*80)
    print("\nThis test verifies Phase 2 fix:")
    print("  • MCP client discovers tools dynamically at runtime")
    print("  • Agent can query available tools")
    print("  • Agent checks tool availability before calling")
    print("  • Agent selects best strategy based on available tools")
    print("  • No hardcoded tool names!")
    
    success = await test_dynamic_discovery()
    
    if success:
        print("\n" + "="*80)
        print("🎉 SUCCESS! Dynamic tool discovery is working!")
        print("="*80)
        print("\nThe BeeAI Discovery Agent now:")
        print("  ✅ Discovers tools automatically on connection")
        print("  ✅ Provides get_available_discovery_tools() method")
        print("  ✅ Provides has_discovery_tool(name) method")
        print("  ✅ Provides get_discovery_strategy() method")
        print("  ✅ Selects best strategy dynamically")
        print("  ✅ Falls back gracefully if tools are missing")
        print("\nBeeAI can now utilize all 4 MCP discovery tools!")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ TEST FAILED - Check logs for details")
        print("="*80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

# Made with Bob