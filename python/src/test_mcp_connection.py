#!/usr/bin/env python3
"""Quick test to verify MCP server connection."""

import asyncio
from mcp_client import MCPClient


async def test_connection():
    """Test MCP server connection."""
    print("Testing MCP server connection...")
    print("=" * 60)
    
    # Test with correct URL (with trailing slash for SSE)
    client = MCPClient("http://localhost:3000/mcp/", timeout=10.0)
    print(f"Using URL: http://localhost:3000/mcp/")
    
    try:
        print("\n1. Connecting to MCP server...")
        await client.connect()
        print("✅ Connected successfully!")
        
        print("\n2. Testing tool call (tcp_portcheck)...")
        result = await client.tcp_portcheck(
            host="localhost",
            ports=[22, 80, 443],
            timeout_s=1.0
        )
        print(f"✅ Tool call successful!")
        print(f"   Result: {result}")
        
        print("\n3. Disconnecting...")
        await client.disconnect()
        print("✅ Disconnected successfully!")
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed! MCP server is working correctly.")
        print("\nYou can now run: python interactive_agent.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure MCP server is running:")
        print("   cd python/cyberres-mcp")
        print("   source .venv/bin/activate")
        print("   MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)

# Made with Bob
