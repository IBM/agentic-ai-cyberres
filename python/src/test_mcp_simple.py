#!/usr/bin/env python3
"""Simple MCP connection test with detailed error output."""

import asyncio
import traceback
from mcp.client.sse import sse_client
from mcp import ClientSession


async def test_connection():
    """Test MCP server connection with detailed error reporting."""
    server_url = "http://localhost:3000/mcp/"
    
    print(f"Attempting to connect to: {server_url}")
    print("=" * 60)
    
    try:
        print("\n1. Creating SSE client...")
        async with sse_client(server_url) as (read, write):
            print("✅ SSE client created")
            
            print("\n2. Creating MCP session...")
            async with ClientSession(read, write) as session:
                print("✅ MCP session created")
                
                print("\n3. Initializing session...")
                await session.initialize()
                print("✅ Session initialized")
                
                print("\n4. Listing tools...")
                tools_result = await session.list_tools()
                print(f"✅ Found {len(tools_result.tools)} tools")
                
                print("\n5. Calling tcp_portcheck tool...")
                result = await session.call_tool("tcp_portcheck", {
                    "host": "localhost",
                    "ports": [22, 80, 443],
                    "timeout_s": 1.0
                })
                print(f"✅ Tool call successful!")
                print(f"   Result type: {type(result)}")
                
        print("\n" + "=" * 60)
        print("🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\nError type: {type(e).__name__}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)

# Made with Bob
