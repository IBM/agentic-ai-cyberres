# ✅ Credentials Are Pre-Configured

## Current Configuration

The MCP server is configured to automatically load credentials from `demo-secrets.json` for the **demo** environment.

### VM Credentials (9.11.68.67)
```json
{
  "host": "9.11.68.67",
  "username": "defsensor",
  "password": "Lash@78snubflip"
}
```

### How It Works

1. **Environment Variable:** `ENVIRONMENT=demo` (set in Claude Desktop config)
2. **Secrets File:** `SECRETS_FILE=demo-secrets.json` (set in Claude Desktop config)
3. **Auto-Loading:** Server automatically loads credentials from the `demo` section

## Using Tools Without Passing Credentials

When you call validation tools, you have **two options**:

### Option 1: Use Pre-Configured Credentials (Recommended)
Simply call the tool without credentials - the server will use the pre-configured ones:

```json
{
  "name": "vm_linux_ssh_validate_health"
}
```

The server will automatically use:
- host: 9.11.68.67
- username: defsensor
- password: Lash@78snubflip

### Option 2: Override with Explicit Credentials
If you need to use different credentials, pass them explicitly:

```json
{
  "name": "vm_linux_ssh_validate_health",
  "arguments": {
    "host": "9.11.68.67",
    "username": "defsensor",
    "password": "Lash@78snubflip"
  }
}
```

## Available Pre-Configured Resources

The server has credentials pre-configured for:

### 1. VM (Linux)
- **Host:** 9.11.68.67
- **Username:** defsensor
- **Password:** Lash@78snubflip
- **Tools:** All `vm_linux_*` tools

### 2. Oracle Database (Demo)
- **DSN:** 10.0.2.20/ORCLCDB
- **User:** system
- **Password:** demo123
- **Tools:** All `db_oracle_*` tools

### 3. MongoDB (Demo)
- **URI:** mongodb://admin:demo123@10.0.2.30:27017/admin
- **Tools:** All `db_mongo_*` tools

## Testing the Configuration

### Test 1: VM Health Check
```
Ask Claude: "Please validate the health of the demo VM"
```

Claude should call:
```json
{
  "name": "vm_linux_ssh_validate_health"
}
```

The server will automatically use the pre-configured credentials.

### Test 2: VM Disk Usage
```
Ask Claude: "Check the disk usage on the demo VM"
```

### Test 3: Verify SSHD
```
Ask Claude: "Verify that sshd is running on the demo VM"
```

## Troubleshooting

### If Claude Says "Unable to Read Credentials"

**Cause:** The server might not be loading the secrets file correctly.

**Solution 1: Verify Secrets File Exists**
```bash
cd python/cyberres-mcp
ls -la demo-secrets.json
```

**Solution 2: Check Server Logs**
Look for "No secrets file found" in the logs. If you see this, the server isn't finding the file.

**Solution 3: Use Absolute Path**
Update Claude Desktop config to use absolute path:
```json
"env": {
  "SECRETS_FILE": "/Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp/demo-secrets.json",
  "ENVIRONMENT": "demo"
}
```

**Solution 4: Restart Claude Desktop**
After any config changes:
1. Quit Claude Desktop completely (Cmd+Q)
2. Wait 10 seconds
3. Relaunch Claude Desktop

### If Tools Still Ask for Credentials

**Workaround:** Pass credentials explicitly in the tool call:

```
Ask Claude: "Please validate the health of the VM at 9.11.68.67 using username 'defsensor' and password 'Lash@78snubflip'"
```

Claude will then pass the credentials in the tool arguments.

## Quick Reference

### VM Validation Commands (No Credentials Needed)

1. **Health Check:** "Validate the demo VM health"
2. **Disk Usage:** "Check disk usage on the demo VM"
3. **SSHD Status:** "Verify sshd is running on the demo VM"
4. **Memory Usage:** "Check memory usage on the demo VM"
5. **CPU Load:** "Check CPU load on the demo VM"

### With Explicit Credentials

If needed, you can always specify:
```
"Please validate the VM at 9.11.68.67 with username 'defsensor' and password 'Lash@78snubflip'"
```

## Current Status

✅ **Credentials File:** `demo-secrets.json` exists
✅ **VM Credentials:** Configured for 9.11.68.67
✅ **Environment:** Set to "demo"
✅ **Server:** Should auto-load credentials

**Next Step:** Restart Claude Desktop (Cmd+Q) to ensure it picks up the configuration, then test with: "Please validate the health of the demo VM"