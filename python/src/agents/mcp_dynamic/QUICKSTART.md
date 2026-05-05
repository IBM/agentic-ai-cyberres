# Dynamic MCP Integration - Quick Start Guide

## Prerequisites

1. **MCP Server Running**
   ```bash
   cd python/cyberres-mcp
   uv run src/cyberres_mcp/server.py
   ```

2. **Python Environment**
   ```bash
   cd python/src
   # Install dependencies if needed
   pip install -r requirements.txt
   ```

3. **Environment Variables** (if needed)
   ```bash
   # Create .env file or export
   export SSH_PASSWORD="your-password"
   ```

## Testing Options

### Option 1: Run All Examples (Recommended)

```bash
cd python/src/beeai_agents/mcp_dynamic
python examples.py
```

This will run 8 comprehensive examples demonstrating all features.

### Option 2: Quick Interactive Test

Create a test file `test_quick.py`:

```python
import asyncio
from beeai_agents.mcp_dynamic import DynamicMCPClient

async def main():
    print("🚀 Testing Dynamic MCP Integration\n")
    
    # 1. Connect
    print("1️⃣ Connecting to MCP server...")
    client = DynamicMCPClient(
        server_path="python/cyberres-mcp",
        auto_discover=True
    )
    
    connected = await client.connect()
    if not connected:
        print("❌ Failed to connect")
        return
    
    print(f"✅ Connected: {client.is_connected()}\n")
    
    # 2. List tools
    print("2️⃣ Listing discovered tools...")
    tools = client.list_tool_names()
    print(f"✅ Found {len(tools)} tools:")
    for tool in tools[:10]:  # Show first 10
        print(f"   - {tool}")
    print()
    
    # 3. Get tool info
    print("3️⃣ Getting tool information...")
    if "check_port" in tools:
        info = client.get_tool_info("check_port")
        print(f"✅ Tool: {info['name']}")
        print(f"   Description: {info['description']}")
        print(f"   Required params: {info['required_parameters']}")
        print()
    
    # 4. Invoke a tool
    print("4️⃣ Invoking tool...")
    result = await client.invoke_tool(
        "check_port",
        {"host": "127.0.0.1", "port": 22}
    )
    print(f"✅ Result: success={result.success}")
    print(f"   Execution time: {result.execution_time_ms}ms")
    if result.error:
        print(f"   Error: {result.error}")
    print()
    
    # 5. Statistics
    print("5️⃣ Getting statistics...")
    stats = client.get_statistics()
    print(f"✅ Statistics:")
    print(f"   Connected: {stats['connected']}")
    print(f"   Total tools: {stats['registry']['total_tools']}")
    print(f"   Total invocations: {stats['invoker']['total_invocations']}")
    print()
    
    # 6. Disconnect
    print("6️⃣ Disconnecting...")
    await client.disconnect()
    print(f"✅ Disconnected: {not client.is_connected()}\n")
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
cd python/src
python -m beeai_agents.mcp_dynamic.test_quick
```

### Option 3: Test with Existing BeeAI Flow

Modify `beeai_interactive.py` to use dynamic MCP:

```python
from beeai_agents.mcp_dynamic import create_client

async def main():
    # Initialize dynamic MCP client
    mcp_client = await create_client(
        server_path="python/cyberres-mcp",
        auto_discover=True
    )
    
    print(f"✅ MCP Client connected")
    print(f"   Available tools: {len(mcp_client.list_tool_names())}")
    
    # Use in your existing flow
    # ... rest of your code
    
    await mcp_client.disconnect()
```

## Testing the LLM Fixes

### Test Validation Agent Fix

```bash
cd python/src
python test_validation_agent_llm.py
```

This will test the validation agent with the emitter error fix.

### Test LLM Aggregator Fix

```bash
cd python/src
python test_llm_aggregator_fix.py
```

This will test the LLM aggregator with improved JSON extraction.

### Test Full Flow

```bash
cd python/src
python beeai_interactive.py
```

Run a full discovery and validation flow to verify all fixes are working.

## Troubleshooting

### Issue: "Connection failed"

**Solution:**
1. Ensure MCP server is running:
   ```bash
   cd python/cyberres-mcp
   uv run src/cyberres_mcp/server.py
   ```

2. Check server path is correct:
   ```python
   client = DynamicMCPClient(
       server_path="python/cyberres-mcp"  # Relative to project root
   )
   ```

### Issue: "No tools discovered"

**Solution:**
1. Check MCP server is responding:
   ```bash
   # In another terminal
   curl http://localhost:8000/health  # If using SSE transport
   ```

2. Force refresh:
   ```python
   tools = await client.refresh_tools()
   ```

### Issue: "Tool invocation failed"

**Solution:**
1. Check tool exists:
   ```python
   tools = client.list_tool_names()
   print(f"Available: {tools}")
   ```

2. Check parameters:
   ```python
   info = client.get_tool_info("tool_name")
   print(f"Required: {info['required_parameters']}")
   ```

3. Validate before invoking:
   ```python
   result = await client.invoke_tool(
       "tool_name",
       parameters,
       validate=True  # This is default
   )
   ```

### Issue: "Import errors"

**Solution:**
1. Ensure you're in the right directory:
   ```bash
   cd python/src
   ```

2. Check Python path:
   ```python
   import sys
   print(sys.path)
   # Should include python/src
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Step-by-Step Testing Guide

### Step 1: Start MCP Server

```bash
# Terminal 1
cd python/cyberres-mcp
uv run src/cyberres_mcp/server.py
```

You should see:
```
INFO: MCP Server started
INFO: Listening on stdio
```

### Step 2: Run Quick Test

```bash
# Terminal 2
cd python/src
python -c "
import asyncio
from beeai_agents.mcp_dynamic import DynamicMCPClient

async def test():
    async with DynamicMCPClient(server_path='python/cyberres-mcp') as client:
        tools = await client.discover_tools()
        print(f'✅ Discovered {len(tools)} tools')
        result = await client.invoke_tool('check_port', {'host': '127.0.0.1', 'port': 22})
        print(f'✅ Tool invocation: {result.success}')

asyncio.run(test())
"
```

Expected output:
```
✅ Discovered 15 tools
✅ Tool invocation: True
```

### Step 3: Run Full Examples

```bash
cd python/src/beeai_agents/mcp_dynamic
python examples.py
```

This will run all 8 examples and show comprehensive output.

### Step 4: Test with Real Workload

```bash
cd python/src
python beeai_interactive.py
```

Follow the prompts to test with a real host.

## Verification Checklist

- [ ] MCP server starts without errors
- [ ] Dynamic client connects successfully
- [ ] Tools are discovered (>0 tools)
- [ ] Tool information is retrieved
- [ ] Tool invocation succeeds
- [ ] Statistics are tracked
- [ ] Client disconnects cleanly
- [ ] LLM errors are fixed (no "Emitter error" or JSON decode errors)

## Next Steps

Once testing is complete:

1. **Integrate with existing agents**
   - Update DiscoveryAgent to use dynamic MCP
   - Update ValidationAgent to use dynamic MCP
   - Update Orchestrator to use dynamic MCP

2. **Add to production flow**
   - Replace hardcoded tool calls
   - Use LLM-friendly descriptions
   - Enable hot-reload for production

3. **Monitor and optimize**
   - Track statistics
   - Optimize slow tools
   - Add caching where needed

## Support

If you encounter issues:

1. Check logs in MCP server terminal
2. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
3. Review documentation:
   - [`README.md`](README.md) - Full documentation
   - [`examples.py`](examples.py) - Usage examples
   - [`DYNAMIC_MCP_IMPLEMENTATION_COMPLETE.md`](../../docs/DYNAMIC_MCP_IMPLEMENTATION_COMPLETE.md) - Implementation details

## Made with Bob