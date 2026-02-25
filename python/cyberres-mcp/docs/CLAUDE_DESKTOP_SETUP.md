# Claude Desktop Integration Guide

This guide explains how to integrate the CyberRes MCP server with Claude Desktop, allowing Claude to directly use the validation tools.

---

## 🎯 Overview

Claude Desktop can connect to MCP servers using the `stdio` transport. This allows Claude to:
- Discover all available tools automatically
- Call tools with appropriate parameters
- Receive and interpret tool responses
- Chain multiple tool calls for complex validations

---

## 📋 Prerequisites

1. **Claude Desktop** installed on your Mac
2. **Python 3.13+** and **uv** installed
3. **MCP server** code in this directory

---

## ⚙️ Configuration Steps

### Step 1: Locate Claude Desktop Config

Claude Desktop configuration is stored at:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Step 2: Add MCP Server Configuration

Open the config file and add the CyberRes MCP server:

```json
{
  "mcpServers": {
    "cyberres-recovery-validation": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/himanshusharma/Documents/mywork/repos/Sangam/agentic-ai-cyberres/python/cyberres-mcp",
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

**Important**: Update the `--directory` path to match your actual installation path.

### Step 3: Restart Claude Desktop

After saving the configuration:
1. Quit Claude Desktop completely
2. Relaunch Claude Desktop
3. The MCP server will start automatically when Claude launches

### Step 4: Verify Connection

In Claude Desktop, you should see:
- A hammer icon (🔨) indicating MCP tools are available
- The server name "cyberres-recovery-validation" in the tools list

---

## 🛠️ Using Tools in Claude Desktop

### Example 1: Check Server Health

Simply ask Claude:
```
Can you check the health of the recovery validation server?
```

Claude will automatically call the `server_health` tool and show you the results.

### Example 2: Validate a VM

Provide credentials in your message to Claude:
```
Please validate the Linux VM at 10.0.1.5 using:
- Username: admin
- Password: secret123

Check uptime, memory, filesystem usage, and verify that sshd and nginx services are running.
```

Claude will:
1. Call `tcp_portcheck` to verify connectivity
2. Call `vm_linux_uptime_load_mem` to check system health
3. Call `vm_linux_fs_usage` to check disk space
4. Call `vm_linux_services` to verify required services
5. Summarize the results for you

### Example 3: Validate Oracle Database

```
Please validate the Oracle database with these credentials:
- DSN: 10.0.2.20/ORCLCDB
- User: system
- Password: oracle123

Check connectivity and tablespace usage.
```

Claude will call the appropriate Oracle tools and provide a summary.

---

## 🔒 Security: Client-Side Credentials

**Important**: The MCP server no longer stores credentials. You must provide them in each request to Claude.

### Why This Approach?

1. **Security**: Credentials are never stored on disk
2. **Flexibility**: Different credentials for different environments
3. **Audit Trail**: Clear record of who accessed what
4. **Best Practice**: Follows principle of least privilege

### How to Provide Credentials

**Option 1: In Natural Language**
```
Validate VM at 10.0.1.5 with username "admin" and password "secret123"
```

**Option 2: Structured Format**
```
Please validate this infrastructure:

VM:
- Host: 10.0.1.5
- Username: admin
- Password: secret123

Oracle DB:
- DSN: 10.0.2.20/ORCLCDB
- User: system
- Password: oracle123
```

**Option 3: Reference Environment Variables**
```
Use the credentials from my environment:
- VM_USER and VM_PASSWORD for the VM
- DB_USER and DB_PASSWORD for the database
```

---

## 🎯 Demo Scenarios with Claude Desktop

### Scenario 1: Comprehensive Infrastructure Validation

**Prompt to Claude:**
```
I need to validate our recovered infrastructure. Here are the details:

1. Linux VM at 10.0.1.5
   - SSH user: admin
   - SSH password: secret123
   - Required services: sshd, nginx, postgresql

2. Oracle Database at 10.0.2.20
   - Service: ORCLCDB
   - User: system
   - Password: oracle123

3. MongoDB at 10.0.2.30
   - Port: 27017
   - User: admin
   - Password: mongo123
   - Database: admin

Please validate all three and provide a summary report.
```

Claude will:
1. Validate each component systematically
2. Check acceptance criteria
3. Provide a comprehensive report
4. Highlight any issues found

### Scenario 2: Troubleshooting a Failed Service

**Prompt to Claude:**
```
The web server VM at 10.0.1.10 (user: webadmin, password: web123) is not responding. 
Can you check:
1. Network connectivity
2. System health (memory, disk, load)
3. Which services are running
4. Specifically check if nginx and postgresql are active
```

### Scenario 3: Database Health Check

**Prompt to Claude:**
```
Check the health of our Oracle database:
- Host: oracle-prod.example.com
- Port: 1521
- Service: PRODDB
- User: system
- Password: oracle123

I need to know:
1. Is it accessible?
2. What's the database role (PRIMARY/STANDBY)?
3. Are any tablespaces running low on space?
```

---

## 🔍 Discovering Available Tools

Ask Claude:
```
What validation tools are available in the recovery validation server?
```

Claude will list all 13 tools with descriptions.

---

## 🐛 Troubleshooting

### Claude doesn't show MCP tools

1. **Check config file location**:
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Verify path is correct**:
   - Update the `--directory` path in the config
   - Use absolute path, not relative

3. **Check server can start**:
   ```bash
   cd /path/to/cyberres-mcp
   uv run server.py
   ```

4. **Restart Claude Desktop**:
   - Quit completely (Cmd+Q)
   - Relaunch

5. **Check Claude Desktop logs**:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

### Tools appear but fail to execute

1. **Verify credentials**: Ensure you're providing valid credentials in your prompts
2. **Check network access**: Ensure target infrastructure is reachable
3. **Review error messages**: Claude will show error details from the tools

### Server starts but tools don't work

1. **Check Python version**: Must be 3.13+
2. **Verify dependencies**: Run `uv sync` in the cyberres-mcp directory
3. **Test tools manually**: Use MCP inspector to test tools directly

---

## 📊 Advantages of Claude Desktop Integration

### For Demos

1. **Natural Language Interface**: No need to remember JSON syntax
2. **Intelligent Orchestration**: Claude chains tools automatically
3. **Context Awareness**: Claude remembers previous results
4. **Error Handling**: Claude interprets errors and suggests fixes

### For Production Use

1. **Audit Trail**: All interactions logged in Claude
2. **Flexible Credentials**: Different creds for different environments
3. **No Stored Secrets**: Credentials provided per-request
4. **Easy Troubleshooting**: Natural language error descriptions

---

## 🎬 Demo Script for Claude Desktop

### Opening (2 minutes)

**Say to audience:**
"I'll demonstrate our MCP server integrated with Claude Desktop. Claude can discover and use all our validation tools through natural language."

**Show in Claude:**
```
What validation tools are available?
```

### VM Validation (3 minutes)

**Say to Claude:**
```
Please validate the Linux VM at 10.0.1.5:
- Username: admin
- Password: secret123
- Check that sshd and nginx are running
- Verify disk usage is under 85%
- Ensure at least 10% memory is free
```

**Highlight**: Claude automatically chains multiple tool calls

### Database Validation (3 minutes)

**Say to Claude:**
```
Now check our Oracle database:
- DSN: 10.0.2.20/ORCLCDB
- User: system
- Password: oracle123
- Verify it's accessible and check tablespace usage
```

**Highlight**: Claude interprets results and provides summary

### Complex Scenario (4 minutes)

**Say to Claude:**
```
We just completed disaster recovery. Please validate:

1. Web server VM (10.0.1.5, admin/secret123)
2. Database server (10.0.2.20/ORCLCDB, system/oracle123)
3. MongoDB (10.0.2.30:27017, admin/mongo123)

Provide a comprehensive report with pass/fail status for each.
```

**Highlight**: 
- Claude orchestrates multiple validations
- Provides executive summary
- Identifies issues clearly

---

## 🔐 Security Best Practices

### DO ✅

- Provide credentials per-request in Claude
- Use environment-specific credentials
- Rotate credentials regularly
- Use SSH keys instead of passwords when possible
- Limit credential scope (read-only accounts)

### DON'T ❌

- Store credentials in the MCP server
- Share credentials in the config file
- Use production credentials for demos
- Commit credentials to version control
- Use overly privileged accounts

---

## 📝 Configuration Template

Save this as a template for different environments:

```json
{
  "mcpServers": {
    "cyberres-dev": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/cyberres-mcp",
        "run",
        "server.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "ENVIRONMENT": "development"
      }
    },
    "cyberres-prod": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/cyberres-mcp",
        "run",
        "server.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "ENVIRONMENT": "production"
      }
    }
  }
}
```

---

## 🚀 Next Steps

1. Configure Claude Desktop with the MCP server
2. Test with the demo scenarios above
3. Practice natural language prompts
4. Prepare your infrastructure credentials
5. Run through the demo script

**You're ready to demo with Claude Desktop!** 🎉