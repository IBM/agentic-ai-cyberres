<!--
Copyright contributors to the agentic-ai-cyberres project
-->

# CyberRes MCP Server


## 🚀 Quick Start

Get up and running in 3 steps:

### 1. Install Dependencies

```bash
cd python/cyberres-mcp/
uv add . --dev
```

### 2. Configure Environment

```bash
# Copy example files
cp .env.example .env
cp secrets.example.json secrets.json

# Edit secrets.json with your infrastructure credentials
```

### 3. Start the Server

```bash
# Run the MCP server
uv run cyberres-mcp
```

The server will start on `http://0.0.0.0:8000` by default.

## 📋 Prerequisites

- Python 3.13 or higher installed on your system
- Network access to target infrastructure (VMs, databases)
- Node.js and npm (for MCP inspector client)

## 🏗️ Architecture

```
┌─────────────────┐
│   MCP Client    │  (AI Agent, Inspector, Custom App)
│  (Claude, etc)  │
└────────┬────────┘
         │ MCP Protocol (HTTP/SSE)
         │
┌────────▼────────┐
│   MCP Server    │
│  (FastMCP)      │
├─────────────────┤
│  • Tools        │  13 validation tools
│  • Resources    │  3 acceptance profiles
│  • Prompts      │  3 agent prompts
└────────┬────────┘
         │
    ┌────┴────┬────────┬─────────┐
    │         │        │         │
┌───▼───┐ ┌──▼──┐ ┌───▼────┐ ┌──▼────┐
│Network│ │ VM  │ │Oracle  │ │MongoDB│
│Plugin │ │Plugin│ │Plugin  │ │Plugin │
└───┬───┘ └──┬──┘ └───┬────┘ └──┬────┘
    │        │        │         │
    └────────┴────────┴─────────┘
              │
    ┌─────────▼──────────┐
    │  Infrastructure    │
    │  • VMs (SSH)       │
    │  • Oracle DBs      │
    │  • MongoDB Clusters│
    └────────────────────┘
```

## 🛠️ Available Tools

### Network Tools
- `tcp_portcheck` - Check TCP connectivity to ports

### VM Linux Tools
- `vm_linux_uptime_load_mem` - Get uptime, load, and memory info
- `vm_linux_fs_usage` - Get filesystem usage statistics
- `vm_linux_services` - Check systemd services status
- `vm_validator` - Legacy VM validation (backwards compatible)

### Oracle Database Tools
- `db_oracle_connect` - Connect and get instance info
- `db_oracle_tablespaces` - Get tablespace usage
- `db_oracle_discover_and_validate` - Discover and validate via SSH

### MongoDB Tools
- `db_mongo_connect` - Connect and verify connectivity
- `db_mongo_rs_status` - Get replica set status
- `db_mongo_ssh_ping` - SSH-based ping command
- `db_mongo_ssh_rs_status` - SSH-based replica set status
- `validate_collection` - Validate collection integrity

### Server Tools
- `server_health` - Check server health and capabilities

## 📚 Resources

The server exposes acceptance criteria profiles:
- `resource://acceptance/vm-core` - VM validation thresholds
- `resource://acceptance/db-oracle` - Oracle DB thresholds
- `resource://acceptance/db-mongo` - MongoDB thresholds

## 🤖 Prompts

Agent orchestration prompts:
- `planner` - Generate validation plan from request
- `evaluator` - Evaluate results against acceptance criteria
- `summarizer` - Generate executive summary

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
MCP_HOST=0.0.0.0          # Host to bind server
MCP_PORT=8000             # Port to listen on
MCP_TRANSPORT=streamable-http  # Transport protocol
SECRETS_FILE=secrets.json # Path to secrets file
```

### Secrets File

Create `secrets.json` with infrastructure credentials:

```json
{
  "vm.example": {
    "ssh": {"username": "admin", "password": "secret"}
  },
  "oracle.example": {
    "dsn": "10.0.2.20/ORCLCDB",
    "user": "system",
    "password": "oracle123"
  },
  "mongo.example": {
    "uri": "mongodb://admin:pass@10.0.2.30:27017/admin"
  }
}
```

**Security Notes:**
- Secrets file is loaded at startup
- Sensitive data is automatically redacted in logs
- Use environment-specific secrets files
- Consider encrypting secrets at rest for production

## 📖 Response Format

All tools return a standardized envelope:

**Success:**
```json
{
  "ok": true,
  "...": "tool-specific data"
}
```

**Error:**
```json
{
  "ok": false,
  "error": {
    "message": "Descriptive error message",
    "code": "ERROR_CODE"
  }
}


### How to Provide Credentials

Credentials are passed as parameters in each tool call:

```json
{
  "tool": "vm_linux_uptime_load_mem",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123"
  }
}
```


---

## 🖥️ Claude Desktop Integration

### Quick Setup

1. **Add to Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cyberres-recovery-validation": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/cyberres-mcp",
        "run",
        "cyberres-mcp"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

2. **Restart Claude Desktop**

3. **Start using tools** - Claude will discover all 13 tools automatically!

### Example Usage with Claude

Simply ask Claude in natural language:

```
Please validate the VM at 10.0.1.5 
Check uptime, memory, disk usage, and verify sshd and nginx are running.
```

Claude will automatically:
- Call the appropriate tools
- Chain multiple validations
- Provide a comprehensive summary


---

## 🔌 Connecting with MCP Inspector

### 1. Start the MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

This opens the inspector UI at `http://localhost:6274`

### 2. Configure Connection

In the MCP Inspector:
1. Set transport to **`streamable-http`**
2. Enter server URL: `http://<server-ip>:8000/mcp`
   - Local: `http://localhost:8000/mcp`

3. Click **Connect**

### 3. Verify Connection

Once connected, you should see:
- ✅ 13 available tools
- ✅ 3 resources
- ✅ 3 prompts

Test the connection:
```json
{
  "tool": "server_health",
  "args": {}
}
```

## 💡 Usage Examples

### Example 1: Validate a Linux VM

```json
{
  "tool": "vm_linux_uptime_load_mem",
  "args": {
    "host": "10.0.1.5",
    "username": "admin",
    "password": "secret123"
  }
}
```

### Example 2: Check Oracle Database

```json
{
  "tool": "db_oracle_connect",
  "args": {
    "dsn": "10.0.2.20/ORCLCDB",
    "user": "system",
    "password": "oracle123"
  }
}
```

### Example 3: Validate MongoDB Replica Set

```json
{
  "tool": "db_mongo_rs_status",
  "args": {
    "uri": "mongodb://admin:pass@mongo-rs-01:27017/admin?replicaSet=rs0"
  }
}
```


## 🎯 Demo Scenarios

Pre-configured validation scenarios are available in [`demo/example-requests.json`](demo/example-requests.json):

- **VM Validation**: Basic health checks and service verification
- **Oracle Validation**: Database connectivity and tablespace usage
- **MongoDB Validation**: Connectivity and replica set status

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port is already in use
lsof -i :8000

# Try a different port
MCP_PORT=8001 uv run cyberres-mcp
```

### Connection refused from inspector
- Verify server is running: `curl http://localhost:8000/health`
- Check firewall rules allow port 8000
- Ensure correct server URL in inspector

### SSH authentication fails
- Verify credentials in secrets.json
- Test SSH manually: `ssh user@host`
- Check SSH key permissions: `chmod 600 ~/.ssh/id_rsa`

### Database connection fails
- Verify database is accessible: `telnet host port`
- Check credentials and DSN format
- Ensure database listener is running

## 🔒 Security Best Practices

1. **Credentials Management**
   - Never commit `secrets.json` to version control
   - Use environment-specific secrets files
   - Rotate credentials regularly

2. **Network Security**
   - Run server behind firewall
   - Use VPN for remote access
   - Consider TLS/SSL for production

3. **Access Control**
   - Limit SSH key distribution
   - Use least-privilege database accounts
   - Monitor server logs for suspicious activity

## 📊 Monitoring

Server logs include structured information:
```
2024-02-05 10:30:15 INFO mcp.server Loaded secrets file path=/path/to/secrets.json keys=['vm.example', 'oracle.example']
2024-02-05 10:30:20 INFO mcp.vm uptime_load_mem succeeded host=10.0.1.5
2024-02-05 10:30:25 WARNING mcp.oracle oracle_connect failed error=ORA-12154: TNS:could not resolve the connect identifier
```

Sensitive data is automatically redacted in logs.

## 🚀 Next Steps

1. **Review Documentation**
   - Read [`demo/tool-examples.md`](demo/tool-examples.md) for detailed tool usage
   - Check [`prompts/`](prompts/) for agent orchestration patterns

2. **Try Demo Scenarios**
   - Use example requests from [`demo/example-requests.json`](demo/example-requests.json)
   - Test with your own infrastructure

3. **Integrate with AI Agents**
   - Connect Claude or other MCP-compatible clients
   - Build automated validation workflows
   - Create custom orchestration logic

## 📝 Contributing

Contributions are welcome! Areas for improvement:
- Additional database support (PostgreSQL, MySQL)
- Windows VM validation
- Container orchestration (Kubernetes)
- Enhanced monitoring and metrics

## 📄 License

See [LICENSE](../../LICENSE) file for details.
```

## Connecting from Local Browser

1. **Install the MCP inspector tool (if not already installed):**

   ```bash
   npx @modelcontextprotocol/inspector
   ```

2. **Open the MCP inspector UI in your browser.**
    ```
    http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=<TOKEN>
    ```

3. **Set the transport to `streamable-http` in the MCP inspector.**

4. **Add the server URL in the MCP inspector:**

   Use the URL of your  server, for example:

   ```
   http://<server-ip>:8000/mcp
   ```

5. Click **Connect**
