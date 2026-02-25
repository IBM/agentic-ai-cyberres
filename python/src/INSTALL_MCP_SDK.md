# Installing MCP SDK for Agentic Workflow

## Overview

The agentic validation workflow now uses the official **MCP Python SDK** to communicate with the cyberres-mcp server via SSE (Server-Sent Events) transport.

## Installation Steps

### 1. Install Dependencies

```bash
cd python/src
source .venv/bin/activate  # or create new venv if needed
pip install -r requirements.txt
```

This will install:
- `mcp>=0.9.0` - Official MCP Python SDK
- `httpx>=0.27.0` - HTTP client (used by MCP SDK)
- `pydantic-ai>=0.0.13` - AI agent framework
- All other dependencies

### 2. Verify Installation

```bash
python -c "from mcp import ClientSession; from mcp.client.sse import sse_client; print('MCP SDK installed successfully!')"
```

Expected output:
```
MCP SDK installed successfully!
```

### 3. Test MCP Connection

```bash
# Terminal 1: Start MCP server
cd python/cyberres-mcp
source .venv/bin/activate
MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp

# Terminal 2: Test connection
cd python/src
source .venv/bin/activate
python test_mcp_connection.py
```

Expected output:
```
Testing MCP server connection...
============================================================
Using URL: http://localhost:3000/mcp

1. Connecting to MCP server...
✅ Connected successfully!
Available tools: 21

2. Testing tool call (tcp_portcheck)...
✅ Tool call successful!

3. Disconnecting...
✅ Disconnected successfully!

============================================================
🎉 All tests passed! MCP server is working correctly.
```

## How It Works

### MCP SDK Architecture

```
┌─────────────────────────────────────────┐
│     Interactive Agent / Orchestrator    │
│                                         │
│  Uses: MCPClient (python/src)          │
└──────────────┬──────────────────────────┘
               │
               │ Uses MCP SDK
               ▼
┌─────────────────────────────────────────┐
│         MCP Python SDK                  │
│                                         │
│  - ClientSession                        │
│  - sse_client (SSE transport)          │
│  - JSON-RPC protocol handling          │
└──────────────┬──────────────────────────┘
               │
               │ SSE Connection
               ▼
┌─────────────────────────────────────────┐
│      cyberres-mcp Server                │
│                                         │
│  FastMCP with streamable-http transport │
│  http://localhost:3000/mcp/             │
└─────────────────────────────────────────┘
```

### Key Components

1. **sse_client** - Establishes SSE connection to MCP server
2. **ClientSession** - Manages MCP protocol communication
3. **call_tool** - Sends JSON-RPC requests and parses responses

### Connection Flow

```python
# 1. Create SSE connection
async with sse_client(server_url) as (read, write):
    # 2. Create MCP session
    async with ClientSession(read, write) as session:
        # 3. Initialize session
        await session.initialize()
        
        # 4. Call tools
        result = await session.call_tool(tool_name, arguments)
```

## Troubleshooting

### Issue: Import errors for mcp package

**Solution:**
```bash
pip install --upgrade mcp
```

### Issue: Connection timeout

**Check:**
1. MCP server is running with streamable-http transport
2. Server URL is correct: `http://localhost:3000/mcp`
3. No firewall blocking port 3000

### Issue: Tool call fails

**Check:**
1. Tool name is correct (use `session.list_tools()` to verify)
2. Arguments match tool schema
3. Server has necessary permissions (SSH keys, credentials)

## Benefits of MCP SDK

✅ **Proper SSE Protocol** - Handles streaming correctly  
✅ **Connection Management** - Automatic reconnection and error handling  
✅ **Type Safety** - Pydantic models for requests/responses  
✅ **Official Support** - Maintained by Anthropic  
✅ **Future Proof** - Compatible with MCP specification updates  

## Next Steps

Once MCP SDK is installed and tested:

1. **Run Interactive Agent:**
   ```bash
   python interactive_agent.py
   ```

2. **Enter Validation Prompts:**
   ```
   Validate VM at 192.168.1.100 with user admin password secret
   ```

3. **View Results:**
   - Workload discovery
   - Resource classification
   - Validation execution
   - AI-powered evaluation

The agentic workflow is now ready to use! 🚀