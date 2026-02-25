# MCP Server Connection Fix

## Problem

The interactive agent was failing to connect to the MCP server with error:
```
❌ Failed to connect to MCP server: Error connecting to MCP server: MCP server returned status 404
```

Server logs showed:
```
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
INFO:     127.0.0.1:58163 - "GET /health HTTP/1.1" 404 Not Found
```

## Root Cause

The MCP server (FastMCP) runs on the `/mcp/` path, not the root path. The client was:
1. Using wrong default URL: `http://0.0.0.0:3000` instead of `http://localhost:3000/mcp`
2. Trying to connect to `/health` endpoint which doesn't exist

## Solution

### 1. Fixed Default URL in interactive_agent.py

**Before:**
```python
def __init__(self, mcp_url: str = "http://0.0.0.0:3000", use_ollama: bool = True):
```

**After:**
```python
def __init__(self, mcp_url: str = "http://localhost:3000/mcp", use_ollama: bool = True):
```

### 2. Fixed Connection Test in mcp_client.py

**Before:**
```python
async def connect(self) -> None:
    self.client = httpx.AsyncClient(timeout=self.timeout)
    # Test connection
    response = await self.client.get(f"{self.server_url}/health", timeout=5.0)
    if response.status_code == 200:
        self._connected = True
```

**After:**
```python
async def connect(self) -> None:
    self.client = httpx.AsyncClient(timeout=self.timeout)
    # Test connection with a simple MCP request (list tools)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    response = await self.client.post(
        f"{self.server_url}/",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=5.0
    )
    if response.status_code == 200:
        result = response.json()
        if "result" in result or "error" not in result:
            self._connected = True
```

## Testing the Fix

### Quick Test Script

Run the connection test:
```bash
cd python/src
source .venv/bin/activate
python test_mcp_connection.py
```

Expected output:
```
Testing MCP server connection...
============================================================

1. Connecting to MCP server...
✅ Connected successfully!

2. Testing tool call (tcp_portcheck)...
✅ Tool call successful!
   Result: {...}

3. Disconnecting...
✅ Disconnected successfully!

============================================================
🎉 All tests passed! MCP server is working correctly.

You can now run: python interactive_agent.py
```

### Full Workflow Test

**Terminal 1: Start MCP Server**
```bash
cd python/cyberres-mcp
source .venv/bin/activate
MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp
```

**Terminal 2: Start Ollama (optional)**
```bash
ollama serve
ollama pull llama3.2
```

**Terminal 3: Run Interactive Agent**
```bash
cd python/src
source .venv/bin/activate
python interactive_agent.py
```

Expected output:
```
======================================================================
🤖 AGENTIC VALIDATION WORKFLOW - Interactive Mode
======================================================================

📡 Connecting to MCP server at http://localhost:3000/mcp...
✅ Connected to MCP server

🦙 Using Ollama (local LLM)
   Make sure Ollama is running: ollama serve
   Default model: llama3.2 (you can change this)
✅ Orchestrator initialized

======================================================================
📝 PROMPT EXAMPLES:
======================================================================
...
```

## Understanding MCP Server Paths

### FastMCP Server Structure

When running with `streamable-http` transport, FastMCP creates these endpoints:

```
http://localhost:3000/
├── /mcp/              # Main MCP endpoint (JSON-RPC)
│   └── POST /         # Tool calls, list tools, etc.
└── /sse/              # Server-sent events (if enabled)
```

### Correct URLs

✅ **Correct:** `http://localhost:3000/mcp`
- This is the base URL for MCP JSON-RPC requests
- All tool calls go to `http://localhost:3000/mcp/`

❌ **Wrong:** `http://localhost:3000`
- Missing the `/mcp` path
- Will result in 404 errors

❌ **Wrong:** `http://localhost:3000/health`
- FastMCP doesn't provide a health endpoint
- Use `tools/list` method instead for connection testing

### MCP JSON-RPC Protocol

All MCP requests use JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "tcp_portcheck",
    "arguments": {
      "host": "localhost",
      "ports": [22, 80, 443]
    }
  }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Port check results..."
      }
    ]
  }
}
```

## Troubleshooting

### Issue: Still getting 404 errors

**Check:**
1. MCP server is running with HTTP transport:
   ```bash
   MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp
   ```

2. Server logs show the correct path:
   ```
   INFO Starting MCP server 'Recovery_Validation_MCP' with transport 'streamable-http' on http://0.0.0.0:3000/mcp/
   ```

3. Client is using the correct URL with `/mcp` path:
   ```python
   client = MCPClient("http://localhost:3000/mcp")
   ```

### Issue: Connection timeout

**Check:**
1. Server is actually running (check terminal)
2. Port 3000 is not blocked by firewall
3. No other service is using port 3000

### Issue: Tool calls fail

**Check:**
1. Connection test passes first
2. Tool name is correct (use `tools/list` to see available tools)
3. Arguments match tool schema
4. Server has necessary permissions (SSH keys, credentials, etc.)

## Summary

The fix ensures:
- ✅ Correct default URL with `/mcp` path
- ✅ Proper connection testing using MCP protocol
- ✅ Clear error messages
- ✅ Works with FastMCP's streamable-http transport

The interactive agent should now connect successfully to the MCP server!