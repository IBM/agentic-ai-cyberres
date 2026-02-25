# MCP Server - Dual Mode Configuration

## Overview

The cyberres-mcp server supports **two modes** via the `MCP_TRANSPORT` environment variable:

1. **stdio mode** - For Claude Desktop integration (default when running `uv run cyberres-mcp`)
2. **HTTP mode** - For programmatic access via REST API

## Configuration

### Mode 1: stdio (Claude Desktop)

**Use Case**: Integration with Claude Desktop or other MCP clients that use stdio transport.

**Start Command**:
```bash
cd python/cyberres-mcp
source .venv/bin/activate

# Option 1: Using uv (default is stdio)
uv run cyberres-mcp

# Option 2: Explicit stdio mode
MCP_TRANSPORT=stdio uv run cyberres-mcp

# Option 3: Using Python directly
python -m cyberres_mcp.server
```

**Configuration**:
- Transport: `stdio`
- No network port needed
- Communication via standard input/output
- Perfect for Claude Desktop

### Mode 2: HTTP (Programmatic Access)

**Use Case**: REST API access for the interactive agent, scripts, or other applications.

**Start Command**:
```bash
cd python/cyberres-mcp
source .venv/bin/activate

# Set HTTP mode
export MCP_TRANSPORT=streamable-http
export MCP_HOST=0.0.0.0
export MCP_PORT=3000

# Start server
uv run cyberres-mcp

# Or in one line
MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp
```

**Configuration**:
- Transport: `streamable-http`
- Host: `0.0.0.0` (all interfaces) or `127.0.0.1` (localhost only)
- Port: `3000` (or any available port)
- Accessible via HTTP at `http://localhost:3000`

## Environment Variables

All configuration is done via environment variables:

```bash
# Transport mode
MCP_TRANSPORT=stdio              # For Claude Desktop (default)
MCP_TRANSPORT=streamable-http    # For HTTP API

# HTTP mode settings (only used when transport=streamable-http)
MCP_HOST=0.0.0.0                 # Bind address (default: 0.0.0.0)
MCP_PORT=3000                    # Port number (default: 8000)

# Secrets file
SECRETS_FILE=secrets.json        # Path to secrets file (default: secrets.json)

# Oracle settings (optional)
ORACLE_HOME=/u01/app/oracle/product/19c/dbhome_1
```

## Using .env File

Create a `.env` file in `python/cyberres-mcp/` for persistent configuration:

### For HTTP Mode (.env)
```bash
# .env file for HTTP mode
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=3000
SECRETS_FILE=secrets.json
```

### For stdio Mode (.env)
```bash
# .env file for stdio mode (Claude Desktop)
MCP_TRANSPORT=stdio
SECRETS_FILE=secrets.json
```

## Quick Start Examples

### Example 1: Start for Claude Desktop
```bash
cd python/cyberres-mcp
source .venv/bin/activate
uv run cyberres-mcp
```

### Example 2: Start for Interactive Agent
```bash
cd python/cyberres-mcp
source .venv/bin/activate

# Create .env file
cat > .env << EOF
MCP_TRANSPORT=streamable-http
MCP_PORT=3000
EOF

# Start server
uv run cyberres-mcp

# Server will be available at http://localhost:3000
```

### Example 3: Run Both Modes Simultaneously

You can run both modes at the same time using different terminals:

**Terminal 1 - HTTP Mode (for interactive agent)**:
```bash
cd python/cyberres-mcp
source .venv/bin/activate
MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp
```

**Terminal 2 - stdio Mode (for Claude Desktop)**:
```bash
# Configure in Claude Desktop's config file
# The stdio mode will be started automatically by Claude Desktop
```

## Verification

### Verify HTTP Mode
```bash
# Check if server is running
curl http://localhost:3000/health

# Or use the server_health tool
curl -X POST http://localhost:3000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "server_health",
      "arguments": {}
    }
  }'
```

### Verify stdio Mode
```bash
# stdio mode doesn't have HTTP endpoint
# Verify by checking Claude Desktop integration
```

## Integration with Interactive Agent

Once the HTTP server is running, the interactive agent can connect:

```bash
# Terminal 1: Start MCP server in HTTP mode
cd python/cyberres-mcp
MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp

# Terminal 2: Start interactive agent
cd python/src
source .venv/bin/activate
python interactive_agent.py --mcp-url http://localhost:3000
```

## Troubleshooting

### Issue: "Address already in use"
**Solution**: Change the port
```bash
MCP_TRANSPORT=streamable-http MCP_PORT=3001 uv run cyberres-mcp
```

### Issue: "Connection refused" from interactive agent
**Solution**: Make sure HTTP mode is running
```bash
# Check if server is running
curl http://localhost:3000/health

# If not, start it
MCP_TRANSPORT=streamable-http MCP_PORT=3000 uv run cyberres-mcp
```

### Issue: Claude Desktop not connecting
**Solution**: Make sure stdio mode is configured
```bash
# Don't set MCP_TRANSPORT or set it to stdio
uv run cyberres-mcp
```

## Best Practices

1. **Development**: Use HTTP mode for testing with interactive agent
2. **Claude Desktop**: Use stdio mode (default)
3. **Production**: Use HTTP mode with proper authentication
4. **Multiple Users**: Run HTTP mode on a shared server
5. **Local Testing**: Use `127.0.0.1` instead of `0.0.0.0` for security

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  cyberres-mcp Server                    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Core Application (FastMCP)            │   │
│  │  • Tools (21 validation & discovery tools)      │   │
│  │  • Resources (acceptance criteria)              │   │
│  │  • Prompts (planner, evaluator, summarizer)    │   │
│  └────────────────┬────────────────────────────────┘   │
│                   │                                     │
│         ┌─────────┴─────────┐                          │
│         │                   │                          │
│    ┌────▼─────┐      ┌─────▼────┐                     │
│    │  stdio   │      │   HTTP   │                     │
│    │Transport │      │Transport │                     │
│    └────┬─────┘      └─────┬────┘                     │
└─────────┼──────────────────┼──────────────────────────┘
          │                  │
          │                  │
     ┌────▼────┐        ┌────▼────────────────┐
     │ Claude  │        │ Interactive Agent   │
     │ Desktop │        │ REST API Clients    │
     │         │        │ Scripts & Tools     │
     └─────────┘        └─────────────────────┘
```

## Summary

- **Default**: stdio mode (for Claude Desktop)
- **For Interactive Agent**: Use HTTP mode with `MCP_TRANSPORT=streamable-http`
- **Configuration**: Via environment variables or `.env` file
- **Flexible**: Can run both modes simultaneously on different ports
- **Easy Switch**: Just change `MCP_TRANSPORT` environment variable

Now you can use the MCP server in both modes! 🚀