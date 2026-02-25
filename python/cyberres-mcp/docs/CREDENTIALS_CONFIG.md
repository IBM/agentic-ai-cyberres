# Credentials Configuration Guide

This guide explains how to configure credentials for the MCP server so you don't have to provide them in plain text with each request.

---

## 🎯 Overview

There are three ways to configure credentials:

1. **Environment Variables** (Recommended for Claude Desktop)
2. **Secrets File** (For programmatic clients)
3. **Claude Desktop Config** (Integrated with environment variables)

---

## Method 1: Environment Variables (Recommended)

### For Claude Desktop

Add credentials as environment variables in the Claude Desktop config:

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
        "MCP_TRANSPORT": "stdio",
        
        "VM_PROD_HOST": "10.0.1.5",
        "VM_PROD_USER": "admin",
        "VM_PROD_PASSWORD": "secret123",
        
        "ORACLE_PROD_DSN": "10.0.2.20/ORCLCDB",
        "ORACLE_PROD_USER": "system",
        "ORACLE_PROD_PASSWORD": "oracle123",
        
        "MONGO_PROD_URI": "mongodb://admin:mongo123@10.0.2.30:27017/admin"
      }
    }
  }
}
```

### Usage with Claude

Once configured, you can ask Claude:

```
Please validate the production VM using the configured credentials
```

Claude will use the environment variables automatically.

### For Terminal/Shell

```bash
# Set environment variables
export VM_PROD_HOST="10.0.1.5"
export VM_PROD_USER="admin"
export VM_PROD_PASSWORD="secret123"

# Start server
uv run cyberres-mcp
```

---

## Method 2: Secrets File

### Create secrets.json

```json
{
  "environments": {
    "production": {
      "vm": {
        "host": "10.0.1.5",
        "username": "admin",
        "password": "secret123"
      },
      "oracle": {
        "dsn": "10.0.2.20/ORCLCDB",
        "user": "system",
        "password": "oracle123"
      },
      "mongo": {
        "uri": "mongodb://admin:mongo123@10.0.2.30:27017/admin"
      }
    },
    "staging": {
      "vm": {
        "host": "10.0.1.10",
        "username": "admin",
        "password": "staging123"
      }
    }
  }
}
```

### Configure in Claude Desktop

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
        "MCP_TRANSPORT": "stdio",
        "SECRETS_FILE": "/path/to/secrets.json"
      }
    }
  }
}
```

### Usage with Claude

```
Please validate the production VM
```

The server will automatically use credentials from `secrets.json` for the "production" environment.

---

## Method 3: Named Credential Profiles

### Create credential profiles

**File: `~/.cyberres/credentials`**

```ini
[vm-prod]
host = 10.0.1.5
username = admin
password = secret123

[oracle-prod]
dsn = 10.0.2.20/ORCLCDB
user = system
password = oracle123

[mongo-prod]
uri = mongodb://admin:mongo123@10.0.2.30:27017/admin
```

### Configure in Claude Desktop

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
        "MCP_TRANSPORT": "stdio",
        "CREDENTIALS_FILE": "~/.cyberres/credentials"
      }
    }
  }
}
```

### Usage with Claude

```
Please validate the VM using the vm-prod profile
```

---

## Security Best Practices

### 1. File Permissions

```bash
# Restrict access to secrets file
chmod 600 secrets.json
chmod 600 ~/.cyberres/credentials
```

### 2. Use SSH Keys Instead of Passwords

```json
{
  "environments": {
    "production": {
      "vm": {
        "host": "10.0.1.5",
        "username": "admin",
        "key_path": "~/.ssh/id_rsa"
      }
    }
  }
}
```

### 3. Encrypt Secrets File

```bash
# Encrypt with GPG
gpg --symmetric --cipher-algo AES256 secrets.json

# Decrypt when needed
gpg --decrypt secrets.json.gpg > secrets.json
```

### 4. Use Environment-Specific Files

```
~/.cyberres/
├── credentials.dev
├── credentials.staging
└── credentials.prod
```

Set via environment variable:
```bash
CREDENTIALS_FILE=~/.cyberres/credentials.prod
```

---

## Example: Complete Claude Desktop Setup

### 1. Create secrets file

**File: `~/.cyberres/secrets.json`**

```json
{
  "vm": {
    "prod": {
      "host": "10.0.1.5",
      "username": "admin",
      "password": "secret123"
    },
    "staging": {
      "host": "10.0.1.10",
      "username": "admin",
      "password": "staging123"
    }
  },
  "oracle": {
    "prod": {
      "dsn": "10.0.2.20/ORCLCDB",
      "user": "system",
      "password": "oracle123"
    }
  },
  "mongo": {
    "prod": {
      "uri": "mongodb://admin:mongo123@10.0.2.30:27017/admin"
    }
  }
}
```

### 2. Secure the file

```bash
chmod 600 ~/.cyberres/secrets.json
```

### 3. Configure Claude Desktop

**File: `~/Library/Application Support/Claude/claude_desktop_config.json`**

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
        "MCP_TRANSPORT": "stdio",
        "SECRETS_FILE": "/Users/himanshusharma/.cyberres/secrets.json"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

### 5. Use with Claude

**Simple validation:**
```
Please validate the production VM
```

**Specific environment:**
```
Please validate the staging VM and production Oracle database
```

**Multiple resources:**
```
Please validate all production infrastructure:
- VM
- Oracle database
- MongoDB cluster
```

Claude will automatically use the credentials from your secrets file!

---

## Credential Resolution Order

The server looks for credentials in this order:

1. **Explicit parameters** (if provided in the request)
2. **Environment variables** (e.g., `VM_PROD_HOST`)
3. **Secrets file** (specified by `SECRETS_FILE` env var)
4. **Default secrets.json** (in the server directory)

---

## Environment Variable Naming Convention

### For VMs

```bash
VM_{ENV}_HOST=10.0.1.5
VM_{ENV}_USER=admin
VM_{ENV}_PASSWORD=secret123
VM_{ENV}_KEY_PATH=~/.ssh/id_rsa
```

### For Oracle

```bash
ORACLE_{ENV}_DSN=10.0.2.20/ORCLCDB
ORACLE_{ENV}_USER=system
ORACLE_{ENV}_PASSWORD=oracle123
```

### For MongoDB

```bash
MONGO_{ENV}_URI=mongodb://admin:pass@host:27017/admin
```

Where `{ENV}` is: `PROD`, `STAGING`, `DEV`, etc.

---

## Demo-Ready Configuration

For your demo today, use this setup:

### 1. Create demo secrets file

**File: `python/cyberres-mcp/demo-secrets.json`**

```json
{
  "demo": {
    "vm": {
      "host": "10.0.1.5",
      "username": "admin",
      "password": "demo123"
    },
    "oracle": {
      "dsn": "10.0.2.20/ORCLCDB",
      "user": "system",
      "password": "demo123"
    },
    "mongo": {
      "uri": "mongodb://admin:demo123@10.0.2.30:27017/admin"
    }
  }
}
```

### 2. Configure Claude Desktop

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
        "MCP_TRANSPORT": "stdio",
        "SECRETS_FILE": "demo-secrets.json",
        "ENVIRONMENT": "demo"
      }
    }
  }
}
```

### 3. Demo with Claude

```
Please validate our demo infrastructure:
1. Check the VM health
2. Verify Oracle database connectivity
3. Validate MongoDB replica set

Use the demo environment credentials.
```

---

## Troubleshooting

### Credentials not found

**Error:** "No credentials configured for environment 'production'"

**Solution:** Check that:
1. `SECRETS_FILE` environment variable is set
2. The secrets file exists and is readable
3. The environment name matches (case-sensitive)

### Permission denied

**Error:** "Permission denied reading secrets file"

**Solution:**
```bash
chmod 600 /path/to/secrets.json
```

### Wrong credentials used

**Solution:** Check credential resolution order. Explicit parameters override environment variables and secrets file.

---

## Summary

✅ **Configure once, use many times**
✅ **No plain text credentials in requests**
✅ **Secure file permissions**
✅ **Environment-specific configurations**
✅ **Works seamlessly with Claude Desktop**

**Your credentials are now configured securely and ready for demo!** 🔒