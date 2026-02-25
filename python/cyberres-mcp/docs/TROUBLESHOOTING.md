# Troubleshooting Guide

## Common Issues and Solutions

### 1. "No module named 'plugins'" Error in Claude Desktop

**Symptoms:**
- Claude Desktop shows: "It looks like there's an issue with the CyberRes Recovery Validation MCP server - it's encountering a module error (No module named 'plugins')"
- Server fails to start from Claude Desktop

**Root Cause:**
The package structure was recently updated and Claude Desktop may be using a cached version or the virtual environment needs to be refreshed.

**Solution:**

1. **Reinstall the package:**
   ```bash
   cd python/cyberres-mcp
   uv sync --reinstall
   ```

2. **Verify the server works standalone:**
   ```bash
   cd python/cyberres-mcp
   MCP_TRANSPORT=stdio uv run cyberres-mcp
   ```
   Press Ctrl+C to stop after verifying it starts without errors.

3. **Completely restart Claude Desktop:**
   - Quit Claude Desktop completely (Cmd+Q on Mac, not just close window)
   - Wait 5 seconds
   - Relaunch Claude Desktop
   - Wait for it to fully load (check the status indicator)

4. **Verify Claude Desktop config path:**
   Ensure your `claude_desktop_config.json` is in the correct location:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

5. **Check the config uses absolute paths:**
   ```json
   {
     "mcpServers": {
       "cyberres-recovery-validation": {
         "command": "/Users/himanshusharma/.local/bin/uv",
         "args": [
           "--directory",
           "/Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp",
           "run",
           "cyberres-mcp"
         ],
         "env": {
           "MCP_TRANSPORT": "stdio",
           "SECRETS_FILE": "demo-secrets.json",
           "ENVIRONMENT": "demo"
         }
       }
     }
   }
   ```

6. **Test with MCP Inspector (alternative):**
   If Claude Desktop still has issues, test with MCP Inspector:
   ```bash
   cd python/cyberres-mcp
   npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
   ```

### 2. Server Starts in HTTP Mode Instead of stdio

**Symptoms:**
- Server shows: "Uvicorn running on http://0.0.0.0:8000"
- Claude Desktop can't connect

**Solution:**
Set the `MCP_TRANSPORT` environment variable:
```bash
MCP_TRANSPORT=stdio uv run cyberres-mcp
```

Or in Claude Desktop config:
```json
"env": {
  "MCP_TRANSPORT": "stdio"
}
```

### 3. "Failed to spawn process" Error

**Symptoms:**
- Claude Desktop shows: "Failed to spawn process: No such file or directory"

**Solution:**
Use the full path to `uv` instead of just `uv`:
```bash
which uv
```
Then update the config with the full path (e.g., `/Users/himanshusharma/.local/bin/uv`).

### 4. Credentials Not Found

**Symptoms:**
- Tools fail with "credentials not configured"
- Server can't find `demo-secrets.json`

**Solution:**

1. **Verify secrets file exists:**
   ```bash
   cd python/cyberres-mcp
   ls -la demo-secrets.json
   ```

2. **Check environment variable:**
   ```bash
   echo $SECRETS_FILE
   ```

3. **Use absolute path in Claude Desktop config:**
   ```json
   "env": {
     "SECRETS_FILE": "/full/path/to/python/cyberres-mcp/demo-secrets.json"
   }
   ```

### 5. Tools Not Showing Up in Claude

**Symptoms:**
- Claude says "I don't have access to those tools"
- `server_health()` tool not available

**Solution:**

1. **Check server is connected:**
   Ask Claude: "What MCP servers are connected?"

2. **Verify tools are registered:**
   Ask Claude: "What tools do you have access to?"

3. **Check Claude Desktop logs:**
   - **macOS:** `~/Library/Logs/Claude/mcp*.log`
   - Look for connection errors or tool registration issues

4. **Restart Claude Desktop completely:**
   - Quit (Cmd+Q)
   - Wait 10 seconds
   - Relaunch

### 6. Import Errors in Server Code

**Symptoms:**
- Server fails to start with import errors
- "ModuleNotFoundError" in logs

**Solution:**

1. **Verify package structure:**
   ```bash
   cd python/cyberres-mcp
   tree src/cyberres_mcp
   ```
   Should show:
   ```
   src/cyberres_mcp/
   ├── __init__.py
   ├── server.py
   ├── settings.py
   ├── models.py
   └── plugins/
       ├── __init__.py
       ├── *.py files
   ```

2. **Check imports use relative paths:**
   In `server.py`:
   ```python
   from .settings import SETTINGS
   from .plugins import vms_validator, oracle_db, mongo_db, net
   ```

3. **Reinstall package:**
   ```bash
   cd python/cyberres-mcp
   uv sync --reinstall
   ```

## Quick Diagnostic Commands

### Test Server Standalone
```bash
cd python/cyberres-mcp
MCP_TRANSPORT=stdio uv run cyberres-mcp
```

### Check Package Installation
```bash
cd python/cyberres-mcp
uv run python -c "import cyberres_mcp; print(cyberres_mcp.__file__)"
```

### Verify Dependencies
```bash
cd python/cyberres-mcp
uv pip list
```

### Test with MCP Inspector
```bash
cd python/cyberres-mcp
npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
```

## Getting Help

If issues persist:

1. **Check the logs:**
   - Claude Desktop logs: `~/Library/Logs/Claude/`
   - Server logs: Check terminal output

2. **Verify environment:**
   ```bash
   cd python/cyberres-mcp
   uv run python --version
   which uv
   pwd
   ```

3. **Test basic functionality:**
   ```bash
   cd python/cyberres-mcp
   uv run python -c "from cyberres_mcp.server import create_app; app = create_app(); print('Server created successfully')"
   ```

4. **Review configuration:**
   - Check `pyproject.toml` entry points
   - Verify `claude_desktop_config.json` paths
   - Confirm `demo-secrets.json` exists

## Demo Day Quick Fix

If you're about to demo and things aren't working:

1. **Use MCP Inspector instead of Claude Desktop:**
   ```bash
   cd python/cyberres-mcp
   npx @modelcontextprotocol/inspector uv --directory . run cyberres-mcp
   ```
   This provides a web UI to test all tools.

2. **Use HTTP mode for testing:**
   ```bash
   cd python/cyberres-mcp
   uv run cyberres-mcp
   ```
   Then access at http://localhost:8000

3. **Run pre-demo test script:**
   ```bash
   cd python/cyberres-mcp
   bash demo/pre-demo-test.sh
   ```
   This verifies all components are working.