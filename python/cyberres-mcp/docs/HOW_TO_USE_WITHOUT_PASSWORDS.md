# ✅ Using Tools WITHOUT Providing Passwords

## The Good News

**You don't need to provide passwords!** The credentials are already securely stored in `demo-secrets.json` and the MCP server automatically loads them.

## How It Works

1. **Credentials are stored** in `demo-secrets.json` (already done ✅)
2. **Server loads them automatically** when it starts (configured ✅)
3. **You just ask Claude** to validate without mentioning credentials
4. **Server uses pre-configured credentials** behind the scenes

## ✅ Correct Way to Use (No Passwords Needed)

### Example 1: VM Health Check
**Just ask:**
```
"Please validate the health of the demo VM"
```

**What happens:**
- Claude calls the tool without credentials
- Server automatically uses credentials from demo-secrets.json
- Validation runs with host: 9.11.68.67, username: defsensor, password: (from file)

### Example 2: Check Disk Usage
**Just ask:**
```
"Check the disk usage on the demo VM"
```

### Example 3: Verify SSHD
**Just ask:**
```
"Verify that sshd is running on the demo VM"
```

### Example 4: Check Memory
**Just ask:**
```
"Check memory usage on the demo VM"
```

## 🔒 Security: Credentials Never Exposed

The credentials flow:
1. ✅ Stored in `demo-secrets.json` (file on disk, not in conversation)
2. ✅ Loaded by server at startup (server-side only)
3. ✅ Used automatically by tools (never sent to Claude)
4. ✅ Never appear in conversation or logs (filtered out)

**You never see or type the password!**

## 📋 Available Commands (No Credentials Needed)

### VM Validations
- "Validate the demo VM health"
- "Check disk usage on the demo VM"
- "Verify sshd is running on the demo VM"
- "Check memory usage on the demo VM"
- "Check CPU load on the demo VM"
- "Validate network connectivity from the demo VM"

### Oracle Database Validations
- "Validate the demo Oracle database"
- "Check Oracle database connectivity"
- "Verify Oracle tablespace"

### MongoDB Validations
- "Validate the demo MongoDB"
- "Check MongoDB connectivity"
- "Verify MongoDB collection"

## 🚀 Quick Start

**Step 1: Restart Claude Desktop**
```bash
# Quit completely (Cmd+Q on Mac)
# Wait 10 seconds
# Relaunch Claude Desktop
```

**Step 2: Verify Server is Connected**
Ask Claude:
```
"Can you check the health of the recovery validation server?"
```

Expected response: Server status with 13 tools available

**Step 3: Run Validation (No Password Needed!)**
Ask Claude:
```
"Please validate the health of the demo VM"
```

Claude will call the tool, server will use stored credentials, and you'll get the validation results.

## ❌ What NOT to Do

**Don't say:**
- ❌ "Validate VM with password Lash@78snubflip"
- ❌ "Use username defsensor and password..."
- ❌ "Connect to 9.11.68.67 with credentials..."

**Instead say:**
- ✅ "Validate the demo VM"
- ✅ "Check the demo VM health"
- ✅ "Run validation on the demo VM"

## 🔍 How to Verify It's Working

### Test 1: Server Health (No Credentials)
```
Ask: "Check the recovery validation server health"
```
Should return: Server status, 13 tools, healthy

### Test 2: VM Validation (Auto-Credentials)
```
Ask: "Validate the demo VM health"
```
Should return: VM health metrics (CPU, memory, disk, etc.)

### Test 3: Check Logs (Credentials Filtered)
If you check server logs, passwords are automatically redacted:
```
2026-02-05 13:42:00,001 INFO Connecting to 9.11.68.67 with user defsensor and password ***
```

## 🎯 Why This is Secure

1. **Credentials in file** - Not in conversation history
2. **Server-side only** - Never sent to Claude's API
3. **Automatic filtering** - Passwords redacted in logs
4. **No user input** - You never type passwords
5. **Environment-based** - Different credentials for demo/staging/prod

## 📊 Demo Flow (No Passwords!)

**For your demo today:**

1. **Start:** "Check the recovery validation server health"
   - Shows server is working, 13 tools available

2. **VM Health:** "Validate the demo VM health"
   - Shows CPU, memory, disk, uptime

3. **Disk Check:** "Check disk usage on the demo VM"
   - Shows filesystem usage

4. **Service Check:** "Verify sshd is running on the demo VM"
   - Shows service status

5. **Network:** "Validate network connectivity from the demo VM"
   - Shows network reachability

**At no point do you mention passwords!**

## 🔧 Troubleshooting

### If Claude Says "Unable to read credentials"

**This means the server isn't loading the secrets file.**

**Fix 1: Verify file exists**
```bash
cd python/cyberres-mcp
ls -la demo-secrets.json
```

**Fix 2: Check Claude Desktop config**
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Should have:
```json
"env": {
  "SECRETS_FILE": "demo-secrets.json",
  "ENVIRONMENT": "demo"
}
```

**Fix 3: Restart Claude Desktop**
- Quit completely (Cmd+Q)
- Wait 10 seconds
- Relaunch

**Fix 4: Check server logs**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

Look for "No secrets file found" - if you see this, the server can't find the file.

### If It Still Doesn't Work

**Emergency workaround:** You can reference a "credential profile" instead:
```
"Please validate the demo VM using the demo credential profile"
```

This tells Claude to use the "demo" section from secrets.json without exposing the password.

## ✅ Summary

**What you need to know:**
1. ✅ Credentials are already configured in demo-secrets.json
2. ✅ Server loads them automatically
3. ✅ Just ask Claude to "validate the demo VM"
4. ✅ No passwords in conversation
5. ✅ Secure and demo-ready

**What you DON'T need to do:**
1. ❌ Don't type passwords
2. ❌ Don't mention credentials
3. ❌ Don't pass authentication details

**Just restart Claude Desktop and ask: "Validate the demo VM health"**

That's it! The server handles all credential management securely behind the scenes.