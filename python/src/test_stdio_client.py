#!/usr/bin/env python3
"""Test MCP stdio client - Industry standard approach."""

import asyncio
from mcp_stdio_client import MCPStdioClient


async def test_stdio_connection():
    """Test MCP server connection via stdio transport."""
    print("Testing MCP stdio client (Industry Standard)")
    print("=" * 60)
    
    # Create client with server command
    # The server will be started as a subprocess in stdio mode
    import os
    cyberres_mcp_dir = os.path.join(os.path.dirname(__file__), "..", "cyberres-mcp")
    
    # Force stdio transport via environment variable
    server_env = os.environ.copy()
    server_env["MCP_TRANSPORT"] = "stdio"
    
    client = MCPStdioClient(
        server_command="uv",
        server_args=["--directory", cyberres_mcp_dir, "run", "cyberres-mcp"],
        server_env=server_env,
        timeout=30.0
    )
    
    try:
        print("\n1. Connecting to MCP server via stdio...")
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
        print("🎉 All tests passed! MCP stdio client is working.")
        print("\nThis is the industry-standard approach used by:")
        print("  - Claude Desktop")
        print("  - Bee-AI framework")
        print("  - Production agentic systems")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you're in the correct directory:")
        print("   cd python/src")
        print("   uv run python test_stdio_client.py")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_stdio_connection())
    exit(0 if success else 1)

# Made with Bob
