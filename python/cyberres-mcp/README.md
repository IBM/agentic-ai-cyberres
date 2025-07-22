# Running the MCP Server on RHEL with uv CLI and Connecting from Local Browser

This guide explains how to run the MCP server located in `server.py` on a Red Hat Enterprise Linux (RHEL) system using the `uv` CLI tool, and how to connect to it from a local browser using the Model Context Protocol (MCP) inspector.

## Prerequisites

- Python 3.8 or higher installed on your RHEL system.
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

3. **Activate the Python virtual environment:**

   ```bash
   source .venv/bin/activate
   ```

4. **Run the server:**

   ```bash
   uv run server.py
   ```

   This will start the MCP server and listen on all interfaces.

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
