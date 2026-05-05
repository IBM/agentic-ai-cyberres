# Dynamic MCP Integration

Runtime tool discovery and invocation for MCP servers without hardcoding. Provides a schema-driven, LLM-friendly interface for dynamic tool usage.

## Overview

This package enables BeeAI agents to discover and use MCP tools at runtime without hardcoding tool names or schemas. Similar to how Claude and ChatGPT integrate with MCP servers, agents can:

- **Discover tools dynamically** at runtime from any MCP server
- **Invoke tools** using schema-driven validation
- **Get LLM-friendly descriptions** for tool selection
- **Monitor changes** with hot-reload support
- **Handle errors gracefully** with automatic retries

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DynamicMCPClient                         │
│  (Unified interface for all MCP operations)                 │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Connection   │   │   Tool       │   │   Tool       │
│  Manager     │   │  Discovery   │   │  Registry    │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                   ┌──────────────┐
                   │   Tool       │
                   │  Invoker     │
                   └──────────────┘
```

### Components

1. **DynamicMCPClient**: Main entry point - orchestrates all operations
2. **MCPConnectionManager**: Manages MCP server connection lifecycle
3. **ToolDiscoveryEngine**: Discovers tools at runtime from MCP server
4. **ToolRegistry**: Stores and manages tool schemas
5. **DynamicToolInvoker**: Invokes tools using schema validation

## Quick Start

### Basic Usage

```python
from beeai_agents.mcp_dynamic import DynamicMCPClient

# Create and connect
client = DynamicMCPClient(server_path="python/cyberres-mcp")
await client.connect()

# Discover tools
tools = await client.discover_tools()
print(f"Discovered {len(tools)} tools")

# Invoke a tool
result = await client.invoke_tool(
    "discover_workload",
    {"host": "9.11.69.88", "ssh_user": "admin"}
)

print(f"Success: {result.success}")
print(f"Result: {result.result}")

# Disconnect
await client.disconnect()
```

### Context Manager (Recommended)

```python
from beeai_agents.mcp_dynamic import DynamicMCPClient

async with DynamicMCPClient(server_path="python/cyberres-mcp") as client:
    # Discover tools
    tools = await client.discover_tools()
    
    # Invoke tool
    result = await client.invoke_tool(
        "check_port",
        {"host": "9.11.69.88", "port": 27017}
    )
    
    print(f"Port check: {result.success}")

# Automatically disconnected
```

### Convenience Function

```python
from beeai_agents.mcp_dynamic import create_client

# Create and connect in one step
client = await create_client(
    server_path="python/cyberres-mcp",
    auto_discover=True
)

# Use client...
await client.disconnect()
```

## Features

### 1. Runtime Tool Discovery

Discover all available tools from MCP server without hardcoding:

```python
# Discover all tools
tools = await client.discover_tools()

# List tool names
tool_names = client.list_tool_names()
print(f"Available tools: {tool_names}")

# Search for specific tools
db_tools = client.search_tools("database")
print(f"Database tools: {[t.name for t in db_tools]}")

# Get detailed tool info
info = client.get_tool_info("discover_workload")
print(f"Tool: {info['name']}")
print(f"Description: {info['description']}")
print(f"Parameters: {info['parameters']}")
```

### 2. LLM Integration

Get tool descriptions in format suitable for LLM context:

```python
# Get LLM-friendly tool descriptions
llm_tools = client.get_llm_tool_descriptions()

# Pass to LLM for tool selection
for tool in llm_tools:
    print(f"Tool: {tool['name']}")
    print(f"Description: {tool['description']}")
    print(f"Parameters: {tool['parameters']}")
```

### 3. Schema-Driven Invocation

Tools are invoked with automatic parameter validation:

```python
# Invoke with validation (default)
result = await client.invoke_tool(
    "discover_workload",
    {
        "host": "9.11.69.88",
        "ssh_user": "admin",
        "ssh_password": "password123"
    }
)

# Skip validation if needed
result = await client.invoke_tool(
    "discover_workload",
    parameters,
    validate=False
)
```

### 4. Batch Invocation

Invoke multiple tools efficiently:

```python
from beeai_agents.mcp_dynamic import ToolInvocation

# Prepare batch
invocations = [
    ToolInvocation("check_port", {"host": "9.11.69.88", "port": 27017}),
    ToolInvocation("check_port", {"host": "9.11.69.88", "port": 1521}),
    ToolInvocation("check_port", {"host": "9.11.69.88", "port": 22}),
]

# Execute batch
results = await client.invoke_tool_batch(invocations)

for result in results:
    print(f"Tool: {result.tool_name}, Success: {result.success}")
```

### 5. Hot-Reload Support

Monitor tool changes in real-time:

```python
# Enable hot-reload
client = DynamicMCPClient(
    server_path="python/cyberres-mcp",
    enable_hot_reload=True
)

await client.connect()

# Tools are automatically refreshed when MCP server changes
# No need to restart the agent!
```

### 6. Error Handling

Comprehensive error handling with automatic retries:

```python
# Invoke tool - errors are captured in result
result = await client.invoke_tool(
    "discover_workload",
    {"host": "invalid.host"}
)

if not result.success:
    print(f"Error: {result.error}")
    print(f"Tool: {result.tool_name}")
else:
    print(f"Success: {result.result}")
```

### 7. Statistics and Monitoring

Track usage and performance:

```python
# Get comprehensive statistics
stats = client.get_statistics()

print(f"Connected: {stats['connected']}")
print(f"Total Tools: {stats['registry']['total_tools']}")
print(f"Total Invocations: {stats['invoker']['total_invocations']}")
print(f"Success Rate: {stats['invoker']['success_rate']}")
```

## Agent Integration

### Pattern for BeeAI Agents

```python
from beeai_agents.mcp_dynamic import create_client

class MyAgent:
    """Example agent using dynamic MCP."""
    
    def __init__(self):
        self.mcp_client = None
    
    async def initialize(self):
        """Initialize agent with MCP client."""
        self.mcp_client = await create_client(
            server_path="python/cyberres-mcp",
            auto_discover=True
        )
    
    async def execute_task(self, task_description: str):
        """Execute a task using available tools."""
        # Get available tools for LLM
        tools = self.mcp_client.get_llm_tool_descriptions()
        
        # LLM selects appropriate tool based on task
        # (In real usage, pass tools to LLM for selection)
        selected_tool = "discover_workload"
        parameters = {"host": "9.11.69.88", "ssh_user": "admin"}
        
        # Invoke selected tool
        result = await self.mcp_client.invoke_tool(
            selected_tool,
            parameters
        )
        
        return result
    
    async def cleanup(self):
        """Cleanup agent resources."""
        if self.mcp_client:
            await self.mcp_client.disconnect()

# Use the agent
agent = MyAgent()
await agent.initialize()
result = await agent.execute_task("Discover workload on host")
await agent.cleanup()
```

## Configuration

### Connection Options

```python
client = DynamicMCPClient(
    server_path="python/cyberres-mcp",  # Path to MCP server
    transport="stdio",                   # Transport type (stdio/sse)
    command="uv",                        # Command to run server
    auto_discover=True,                  # Auto-discover on connect
    enable_hot_reload=False,             # Enable hot-reload watching
    connection_timeout=30.0,             # Connection timeout (seconds)
    health_check_interval=60.0,          # Health check interval
)
```

### Environment Variables

The MCP server may require environment variables:

```bash
# Set in .env file or environment
export SSH_PASSWORD="your-password"
export API_KEY="your-api-key"
```

## API Reference

### DynamicMCPClient

Main client interface for dynamic MCP integration.

#### Methods

- `connect() -> bool`: Connect to MCP server
- `disconnect() -> None`: Disconnect from MCP server
- `discover_tools(force_refresh=False) -> List[ToolSchema]`: Discover tools
- `refresh_tools() -> List[ToolSchema]`: Force refresh tool list
- `invoke_tool(tool_name, parameters, validate=True) -> ToolResult`: Invoke tool
- `invoke_tool_batch(invocations) -> List[ToolResult]`: Batch invoke
- `get_llm_tool_descriptions() -> List[Dict]`: Get LLM descriptions
- `list_tools() -> List[ToolMetadata]`: List all tools
- `list_tool_names() -> List[str]`: List tool names
- `get_tool_info(tool_name) -> Optional[Dict]`: Get tool info
- `search_tools(query) -> List[ToolMetadata]`: Search tools
- `is_connected() -> bool`: Check connection status
- `get_statistics() -> Dict`: Get statistics

### Data Models

#### ToolSchema

Complete tool specification with JSON Schema validation.

```python
@dataclass
class ToolSchema:
    name: str
    description: str
    input_schema: Dict[str, Any]
    annotations: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
    category: Optional[str] = None
```

#### ToolResult

Result of tool invocation.

```python
@dataclass
class ToolResult:
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### ToolInvocation

Tool invocation request for batching.

```python
@dataclass
class ToolInvocation:
    tool_name: str
    parameters: Dict[str, Any]
    invocation_id: Optional[str] = None
```

## Examples

See `examples.py` for comprehensive usage examples:

1. Basic Usage - Connect, discover, invoke
2. Context Manager - Automatic cleanup
3. Batch Invocation - Multiple tools at once
4. LLM Integration - Tool descriptions for LLM
5. Hot-Reload - Monitor tool changes
6. Error Handling - Graceful error handling
7. Statistics - Usage monitoring
8. Agent Integration - BeeAI agent pattern

Run examples:

```bash
cd python/src/beeai_agents/mcp_dynamic
python examples.py
```

## Best Practices

### 1. Use Context Manager

Always use async context manager for automatic cleanup:

```python
async with DynamicMCPClient(server_path="...") as client:
    # Use client
    pass
# Automatically disconnected
```

### 2. Enable Auto-Discovery

Let the client discover tools on connection:

```python
client = DynamicMCPClient(
    server_path="...",
    auto_discover=True  # Discover on connect
)
```

### 3. Handle Errors Gracefully

Always check result.success:

```python
result = await client.invoke_tool(tool_name, params)
if not result.success:
    logger.error(f"Tool failed: {result.error}")
    # Handle error
else:
    # Process result
    data = result.result
```

### 4. Use Batch for Multiple Tools

Batch invocation is more efficient:

```python
# Instead of multiple individual calls
results = await client.invoke_tool_batch(invocations)
```

### 5. Monitor Statistics

Track usage for debugging and optimization:

```python
stats = client.get_statistics()
logger.info(f"Success rate: {stats['invoker']['success_rate']}")
```

## Troubleshooting

### Connection Issues

```python
# Check connection status
if not client.is_connected():
    logger.error("Not connected to MCP server")
    
# Check connection state
state = client.get_connection_state()
logger.info(f"Connection state: {state}")
```

### Tool Not Found

```python
# List available tools
tools = client.list_tool_names()
logger.info(f"Available tools: {tools}")

# Search for tool
matches = client.search_tools("workload")
logger.info(f"Matching tools: {[t.name for t in matches]}")
```

### Parameter Validation Errors

```python
# Get tool info to see required parameters
info = client.get_tool_info("discover_workload")
logger.info(f"Required params: {info['required_parameters']}")
logger.info(f"Optional params: {info['optional_parameters']}")
```

## Performance

- **Connection**: ~1-2 seconds for initial connection
- **Discovery**: ~100-500ms for tool discovery (cached)
- **Invocation**: Depends on tool execution time
- **Batch**: Parallel execution for better throughput

## Limitations

- Requires MCP server to be running
- Tools must provide JSON Schema for parameters
- Hot-reload requires server support for change notifications
- Batch invocation limited by server capacity

## Future Enhancements

- [ ] Support for streaming tool results
- [ ] Tool result caching
- [ ] Advanced retry strategies
- [ ] Tool usage analytics
- [ ] Multi-server support
- [ ] Tool composition/chaining

## License

Part of BeeAI Infrastructure Recovery Validation AI project.

## Made with Bob