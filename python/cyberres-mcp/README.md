<!--
Copyright contributors to the agentic-ai-cyberres project
-->

# Running the MCP Server on RHEL with uv CLI and Connecting from Local Browser

This guide explains how to run the MCP server located in `server.py` on a Red Hat Enterprise Linux (RHEL) system using the `uv` CLI tool, and how to connect to it from a local browser using the Model Context Protocol (MCP) inspector.

## Prerequisites

- Python 3.13 or higher installed on your RHEL system.
- Network access to the RHEL server from your local machine.
- Node.js and npm installed on your local machine (for MCP inspector).

## Setup and Running the Server on RHEL

1. **Navigate to the mcp directory:**

   ```bash
   cd agentic-ai-cyberres/python/cyberres-mcp/
   ```

2. **Add the current directory as a development environment:**

   ```bash
   uv add . --dev
   ```

3. **Run the server:**

   ```bash
   # Preferred (console script)
   uv run cyberres-mcp

   # Or run the module directly
   uv run server.py
   ```

   This will start the MCP server and listen on all interfaces.

### Configuration via environment

The server reads environment variables (via `.env` if present):

```bash
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_TRANSPORT=streamable-http
SECRETS_FILE=secrets.json
```

### Secrets handling

- If a `secrets.json` file exists at startup, it is loaded automatically.
- Log output redacts sensitive data (passwords/tokens, credentials in URIs).

### Tool responses

All tools return a standardized envelope:

```json
{ "ok": true, "...": "..." }
```

Errors follow:

```json
{ "ok": false, "error": { "message": "...", "code": "..." } }
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
