# Credentials Management Guide

## 🔒 Security-First Approach

**Important**: The CyberRes MCP server follows security best practices by **NOT storing credentials**. All credentials must be provided by the client (Claude Desktop, MCP Inspector, or custom agents) at request time.

---

## 🎯 Why Client-Side Credentials?

### Security Benefits

1. **No Credentials at Rest**: Credentials are never stored on disk
2. **Principle of Least Privilege**: Each request uses only necessary credentials
3. **Audit Trail**: Clear record of who accessed what and when
4. **Credential Rotation**: Easy to change credentials without updating server
5. **Multi-Tenancy**: Different clients can use different credentials
6. **Compliance**: Meets security standards for credential handling

### Operational Benefits

1. **Flexibility**: Use different credentials for dev/staging/prod
2. **No Secret Management**: No need for encrypted secrets files
3. **Reduced Attack Surface**: Compromised server doesn't expose credentials
4. **Easy Testing**: Use test credentials without affecting production

---

## 📋 How It Works

### Traditional Approach (❌ Not Recommended)

```json
// secrets.json on server
{
  "vm.prod": {
    "ssh": {"username": "admin", "password": "secret123"}
  }
}
```

**Problems**:
- Credentials stored on disk
- All clients share same credentials
- Hard to rotate credentials
- Security risk if server is compromised

### Our Approach (✅ Recommended)

```
Client (Claude/Agent) → Provides credentials → MCP Server → Uses credentials → Target Infrastructure
                                                    ↓
                                            Credentials discarded after use
```

**Benefits**:
- Credentials only in memory during request
- Each client provides their own credentials
- Easy credential rotation
- Minimal security risk

---

## 🛠️ Providing Credentials

### Method 1: Claude Desktop (Natural Language)

Claude Desktop users provide credentials in natural language:

```
Please validate the VM at 10.0.1.5 using:
- Username: admin
- Password: secret123
```

Claude extracts the credentials and passes them to the appropriate tool.

### Method 2: MCP Inspector (JSON)

When using MCP Inspector, provide credentials in tool arguments:

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

### Method 3: Custom MCP Client (Programmatic)

```python
from mcp import ClientSession

async with ClientSession(server_url) as session:
    result = await session.call_tool(
        "vm_linux_uptime_load_mem",
        {
            "host": "10.0.1.5",
            "username": "admin",
            "password": "secret123"
        }
    )
```

---

## 🔐 Credential Types Supported

### SSH Credentials

**Password Authentication**:
```json
{
  "host": "10.0.1.5",
  "username": "admin",
  "password": "secret123"
}
```

**SSH Key Authentication** (Recommended):
```json
{
  "host": "10.0.1.5",
  "username": "admin",
  "key_path": "/home/user/.ssh/id_rsa"
}
```

### Oracle Database Credentials

**With DSN**:
```json
{
  "dsn": "10.0.2.20/ORCLCDB",
  "user": "system",
  "password": "oracle123"
}
```

**With Discrete Parameters**:
```json
{
  "host": "oracle-prod.example.com",
  "port": 1521,
  "service": "ORCLCDB",
  "user": "system",
  "password": "oracle123"
}
```

### MongoDB Credentials

**With URI**:
```json
{
  "uri": "mongodb://admin:mongo123@10.0.2.30:27017/admin"
}
```

**With Discrete Parameters**:
```json
{
  "host": "mongo-prod.example.com",
  "port": 27017,
  "user": "admin",
  "password": "mongo123",
  "database": "admin"
}
```

---

## 🎯 Best Practices

### DO ✅

1. **Use SSH Keys Instead of Passwords**
   ```json
   {
     "host": "10.0.1.5",
     "username": "admin",
     "key_path": "/home/user/.ssh/id_rsa"
   }
   ```

2. **Use Read-Only Accounts**
   - For VMs: Use accounts with minimal sudo privileges
   - For databases: Use accounts with SELECT-only permissions
   - For MongoDB: Use read-only roles

3. **Rotate Credentials Regularly**
   - Change passwords every 90 days
   - Regenerate SSH keys periodically
   - Update database passwords quarterly

4. **Use Environment-Specific Credentials**
   - Development: Use dev credentials
   - Staging: Use staging credentials
   - Production: Use production credentials

5. **Implement Credential Vaults**
   - Store credentials in HashiCorp Vault
   - Use AWS Secrets Manager
   - Use Azure Key Vault
   - Retrieve credentials at request time

6. **Log Credential Usage**
   - Log which credentials were used
   - Log when they were used
   - Log what they accessed
   - (But never log the actual credentials!)

### DON'T ❌

1. **Don't Store Credentials in Code**
   ```python
   # ❌ BAD
   password = "secret123"
   ```

2. **Don't Commit Credentials to Git**
   ```bash
   # ❌ BAD
   git add secrets.json
   ```

3. **Don't Share Credentials**
   - Each user should have their own credentials
   - Don't share passwords via email/chat
   - Don't use shared accounts

4. **Don't Use Overly Privileged Accounts**
   - Don't use root/admin accounts
   - Don't use DBA accounts for read-only operations
   - Follow principle of least privilege

5. **Don't Hardcode Credentials**
   ```json
   // ❌ BAD
   {
     "default_password": "admin123"
   }
   ```

---

## 🔍 Credential Security in the MCP Server

### What the Server Does

1. **Receives Credentials**: Gets credentials from client in tool arguments
2. **Uses Credentials**: Passes them to SSH/database connections
3. **Discards Credentials**: Removes from memory after request completes
4. **Redacts in Logs**: Automatically redacts sensitive data in logs

### What the Server Doesn't Do

1. ❌ Store credentials on disk
2. ❌ Cache credentials in memory
3. ❌ Share credentials between requests
4. ❌ Log actual credential values

### Log Redaction Example

**Before Redaction**:
```
Connecting to mongodb://admin:mongo123@10.0.2.30:27017/admin
```

**After Redaction**:
```
Connecting to mongodb://admin:***@10.0.2.30:27017/admin
```

---

## 🎬 Demo Scenarios

### Scenario 1: Claude Desktop with Inline Credentials

**User says to Claude**:
```
Please validate the VM at 10.0.1.5 with username "admin" and password "secret123"
```

**Claude calls**:
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

### Scenario 2: Claude Desktop with Credential Reference

**User says to Claude**:
```
Use my VM credentials (stored in my password manager) to validate 10.0.1.5
```

**User then provides**:
```
The credentials are:
- Username: admin
- Password: secret123
```

### Scenario 3: Programmatic Client with Vault

```python
import hvac  # HashiCorp Vault client

# Retrieve credentials from vault
vault = hvac.Client(url='https://vault.example.com')
creds = vault.secrets.kv.v2.read_secret_version(path='vm/prod')

# Use credentials in MCP call
result = await session.call_tool(
    "vm_linux_uptime_load_mem",
    {
        "host": "10.0.1.5",
        "username": creds['data']['username'],
        "password": creds['data']['password']
    }
)
```

---

## 🔄 Credential Rotation Workflow

### Step 1: Generate New Credentials

```bash
# For SSH keys
ssh-keygen -t ed25519 -f ~/.ssh/id_rsa_new

# For database passwords
openssl rand -base64 32
```

### Step 2: Update Target Systems

```bash
# Add new SSH key to authorized_keys
ssh-copy-id -i ~/.ssh/id_rsa_new.pub user@host

# Update database password
ALTER USER system IDENTIFIED BY 'new_password';
```

### Step 3: Test New Credentials

```
Ask Claude: "Test the new credentials for VM 10.0.1.5 with username admin and the new SSH key"
```

### Step 4: Update Credential Store

```bash
# Update in vault
vault kv put secret/vm/prod username=admin password=new_password
```

### Step 5: Remove Old Credentials

```bash
# Remove old SSH key from authorized_keys
# Revoke old database password
```

---

## 📊 Credential Audit Trail

### What to Log

1. **Who**: Which user/client made the request
2. **What**: Which tool was called
3. **When**: Timestamp of the request
4. **Where**: Which infrastructure was accessed
5. **Result**: Success or failure

### What NOT to Log

1. ❌ Actual passwords
2. ❌ SSH private keys
3. ❌ Database connection strings with passwords
4. ❌ API tokens

### Example Log Entry

```json
{
  "timestamp": "2026-02-05T10:30:15Z",
  "user": "alice@example.com",
  "tool": "vm_linux_uptime_load_mem",
  "target": "10.0.1.5",
  "username": "admin",
  "auth_method": "ssh_key",
  "result": "success",
  "duration_ms": 234
}
```

---

## 🚀 Integration Examples

### Example 1: CI/CD Pipeline

```yaml
# .github/workflows/validate.yml
name: Infrastructure Validation

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate Infrastructure
        env:
          VM_USER: ${{ secrets.VM_USER }}
          VM_PASSWORD: ${{ secrets.VM_PASSWORD }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          # Call MCP tools with credentials from secrets
          python validate.py
```

### Example 2: Monitoring System

```python
import os
from mcp import ClientSession

async def validate_infrastructure():
    # Get credentials from environment
    vm_user = os.getenv('VM_USER')
    vm_password = os.getenv('VM_PASSWORD')
    
    async with ClientSession(server_url) as session:
        result = await session.call_tool(
            "vm_linux_uptime_load_mem",
            {
                "host": "10.0.1.5",
                "username": vm_user,
                "password": vm_password
            }
        )
        
        if not result['ok']:
            send_alert(f"VM validation failed: {result['error']}")
```

---

## 📝 Summary

### Key Takeaways

1. ✅ **Client provides credentials** at request time
2. ✅ **Server never stores credentials** on disk
3. ✅ **Credentials are discarded** after use
4. ✅ **Logs are automatically redacted**
5. ✅ **Use SSH keys** instead of passwords when possible
6. ✅ **Rotate credentials** regularly
7. ✅ **Use credential vaults** for production
8. ✅ **Follow principle of least privilege**

### Security Checklist

- [ ] Credentials provided per-request
- [ ] No credentials stored on server
- [ ] SSH keys used instead of passwords
- [ ] Read-only accounts used where possible
- [ ] Credentials rotated regularly
- [ ] Credential vault integrated
- [ ] Audit logging enabled
- [ ] Log redaction verified

---

**Remember**: The most secure credential is one that's never stored! 🔒