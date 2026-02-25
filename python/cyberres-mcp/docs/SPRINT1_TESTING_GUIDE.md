# Sprint 1 Testing Guide - Workload Discovery

This guide provides step-by-step instructions to test the Sprint 1 implementation of the workload discovery tool.

## Prerequisites

1. **Python Environment**: Ensure you have Python 3.13+ and `uv` installed
2. **Test Server**: Access to a Linux server for testing (can be localhost, VM, or remote server)
3. **SSH Access**: Valid SSH credentials (password or key-based)

## Testing Methods

### Method 1: Using MCP Inspector (Recommended)

#### Step 1: Start the MCP Server

```bash
cd python/cyberres-mcp
uv run cyberres-mcp
```

The server should start on `http://0.0.0.0:8000` by default.

#### Step 2: Open MCP Inspector

In a new terminal:

```bash
npx @modelcontextprotocol/inspector
```

This opens the inspector UI at `http://localhost:6274`

#### Step 3: Connect to Server

1. Set transport to **`streamable-http`**
2. Enter server URL: `http://localhost:8000/mcp`
3. Click **Connect**

#### Step 4: Verify Tools Available

You should see **21 tools** including:
- `discover_os_only` ✅ (NEW - Sprint 1)
- `discover_workload` ✅ (NEW - Sprint 1, placeholder)
- `server_health`
- All existing tools (vm_linux_*, db_oracle_*, db_mongo_*, tcp_portcheck, etc.)

#### Step 5: Test `server_health` Tool

Execute:
```json
{
  "tool": "server_health",
  "args": {}
}
```

Expected response:
```json
{
  "ok": true,
  "status": "healthy",
  "version": "0.1.0",
  "plugins": ["network", "vm_linux", "oracle_db", "mongodb", "workload_discovery"],
  "capabilities": {
    "tools": 21,
    "resources": 3,
    "prompts": 3
  }
}
```

#### Step 6: Test `discover_os_only` Tool

**Test on localhost (if Linux):**
```json
{
  "tool": "discover_os_only",
  "args": {
    "host": "localhost",
    "ssh_user": "your_username",
    "ssh_password": "your_password"
  }
}
```

**Test on remote server:**
```json
{
  "tool": "discover_os_only",
  "args": {
    "host": "10.0.1.5",
    "ssh_user": "admin",
    "ssh_password": "secret123"
  }
}
```

**Test with SSH key:**
```json
{
  "tool": "discover_os_only",
  "args": {
    "host": "10.0.1.5",
    "ssh_user": "admin",
    "ssh_key_path": "/home/user/.ssh/id_rsa"
  }
}
```

Expected response structure:
```json
{
  "ok": true,
  "os_type": "linux",
  "distribution": "ubuntu",
  "version": "22.04",
  "kernel_version": "5.15.0-91-generic",
  "architecture": "x86_64",
  "hostname": "test-server",
  "uptime_seconds": 123456,
  "confidence": "high",
  "detection_methods": ["file_system"],
  "raw_data": {
    "os_release": {...},
    "kernel_version": "5.15.0-91-generic",
    ...
  }
}
```

---

### Method 2: Using Python Script

Create a test script to verify the implementation:

```python
# test_sprint1.py
import sys
sys.path.insert(0, 'python/cyberres-mcp/src')

from cyberres_mcp.server import create_app
from cyberres_mcp.models import (
    OSType, OSDistribution, ConfidenceLevel,
    DiscoveryRequest
)
from cyberres_mcp.plugins.workload_discovery import OSDetector

def test_server_creation():
    """Test 1: Server creates successfully"""
    print("Test 1: Creating MCP server...")
    try:
        app = create_app()
        print("✅ Server created successfully")
        return True
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        return False

def test_models():
    """Test 2: Data models work correctly"""
    print("\nTest 2: Testing data models...")
    try:
        # Test enums
        os_type = OSType.LINUX
        dist = OSDistribution.UBUNTU
        conf = ConfidenceLevel.HIGH
        
        # Test DiscoveryRequest
        request = DiscoveryRequest(
            host="test-host",
            ssh_user="testuser",
            ssh_password="testpass"
        )
        
        print(f"✅ Models working: OS={os_type.value}, Dist={dist.value}, Conf={conf.value}")
        return True
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def test_os_detector_import():
    """Test 3: OS Detector imports correctly"""
    print("\nTest 3: Testing OS Detector import...")
    try:
        detector = OSDetector()
        print("✅ OS Detector imported and instantiated")
        return True
    except Exception as e:
        print(f"❌ OS Detector import failed: {e}")
        return False

def test_os_detector_parsing():
    """Test 4: OS Detector parsing logic"""
    print("\nTest 4: Testing OS Detector parsing...")
    try:
        detector = OSDetector()
        
        # Test os-release parsing
        os_release_content = '''
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
VERSION_ID="22.04"
'''
        parsed = detector._parse_os_release(os_release_content)
        assert parsed['ID'] == 'ubuntu'
        assert parsed['VERSION_ID'] == '22.04'
        
        print("✅ OS Detector parsing works correctly")
        return True
    except Exception as e:
        print(f"❌ OS Detector parsing failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Sprint 1 Testing Suite")
    print("=" * 60)
    
    results = []
    results.append(("Server Creation", test_server_creation()))
    results.append(("Data Models", test_models()))
    results.append(("OS Detector Import", test_os_detector_import()))
    results.append(("OS Detector Parsing", test_os_detector_parsing()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Sprint 1 is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
```

Run the test:
```bash
cd python/cyberres-mcp
uv run python test_sprint1.py
```

---

### Method 3: Manual Command-Line Testing

#### Test 1: Verify Server Starts

```bash
cd python/cyberres-mcp
uv run python -c "from cyberres_mcp.server import create_app; app = create_app(); print('✅ Server OK')"
```

Expected output:
```
2026-02-11 XX:XX:XX,XXX INFO mcp.server No secrets file found
✅ Server OK
```

#### Test 2: Verify Models Import

```bash
uv run python -c "from cyberres_mcp.models import OSType, OSDistribution, DiscoveryRequest; print('✅ Models OK')"
```

#### Test 3: Verify OS Detector

```bash
uv run python -c "from cyberres_mcp.plugins.workload_discovery import OSDetector; d = OSDetector(); print('✅ OS Detector OK')"
```

#### Test 4: Test OS Detection (requires SSH access)

```bash
uv run python -c "
from cyberres_mcp.models import DiscoveryRequest
from cyberres_mcp.plugins.workload_discovery import OSDetector

request = DiscoveryRequest(
    host='localhost',
    ssh_user='your_username',
    ssh_password='your_password'
)

detector = OSDetector()
result = detector.detect(request)
print(f'OS Type: {result.os_type.value}')
print(f'Distribution: {result.distribution.value if result.distribution else \"unknown\"}')
print(f'Version: {result.version}')
print(f'Confidence: {result.confidence.value}')
"
```

---

### Method 4: Using Claude Desktop (if configured)

If you have Claude Desktop configured with the MCP server:

1. **Start a conversation with Claude**

2. **Ask Claude to check server health:**
   ```
   Can you check the health of the cyberres MCP server?
   ```

3. **Ask Claude to discover OS on a server:**
   ```
   Please discover the operating system on server 10.0.1.5 
   using SSH credentials: user=admin, password=secret123
   ```

4. **Verify the response includes:**
   - OS type (linux/windows/unix)
   - Distribution (ubuntu/rhel/centos/etc.)
   - Version number
   - Kernel version
   - Architecture
   - Confidence level

---

## Expected Test Results

### ✅ Success Criteria

1. **Server Starts**: No errors when starting the MCP server
2. **Tools Registered**: 21 tools available (19 existing + 2 new)
3. **Plugin Loaded**: `workload_discovery` appears in plugins list
4. **OS Detection Works**: Successfully detects OS on test server
5. **Confidence Scoring**: Returns appropriate confidence level (high/medium/low)
6. **Error Handling**: Gracefully handles SSH failures and returns error messages

### 📊 Sample Successful Output

```json
{
  "ok": true,
  "os_type": "linux",
  "distribution": "ubuntu",
  "version": "22.04",
  "kernel_version": "5.15.0-91-generic",
  "architecture": "x86_64",
  "hostname": "test-server-01",
  "uptime_seconds": 1234567,
  "confidence": "high",
  "detection_methods": ["file_system"],
  "raw_data": {
    "os_release": {
      "NAME": "Ubuntu",
      "VERSION": "22.04.3 LTS (Jammy Jellyfish)",
      "ID": "ubuntu",
      "VERSION_ID": "22.04",
      "PRETTY_NAME": "Ubuntu 22.04.3 LTS"
    },
    "kernel_version": "5.15.0-91-generic",
    "architecture": "x86_64",
    "hostname": "test-server-01",
    "uptime_seconds": 1234567
  }
}
```

---

## Troubleshooting

### Issue: Server won't start

**Error**: `AttributeError: module 'cyberres_mcp.plugins.workload_discovery' has no attribute 'attach'`

**Solution**: Ensure the standalone `workload_discovery.py` file was deleted and only the package directory exists.

```bash
ls -la python/cyberres-mcp/src/cyberres_mcp/plugins/ | grep workload
# Should show only: drwxr-xr-x workload_discovery/
```

### Issue: SSH connection fails

**Error**: `OS detection failed: [Errno 61] Connection refused`

**Solutions**:
1. Verify SSH service is running on target: `systemctl status sshd`
2. Check firewall allows SSH: `sudo ufw status`
3. Test SSH manually: `ssh user@host`
4. Verify credentials are correct

### Issue: Permission denied

**Error**: `OS detection failed: Permission denied (publickey,password)`

**Solutions**:
1. Verify username and password are correct
2. Check if password authentication is enabled in `/etc/ssh/sshd_config`
3. Try using SSH key instead of password
4. Ensure user has necessary permissions

### Issue: Low confidence score

**Cause**: Missing or incomplete OS detection data

**Solutions**:
1. Check if `/etc/os-release` exists on target
2. Verify SSH user has read permissions
3. Review `raw_data` in response to see what was detected
4. This is expected for some minimal/custom Linux distributions

---

## Test Checklist

Before moving to Sprint 2, verify:

- [ ] Server starts without errors
- [ ] `server_health` tool returns 21 tools
- [ ] `discover_os_only` tool is available
- [ ] `discover_workload` tool is available (placeholder)
- [ ] OS detection works on at least one Linux server
- [ ] Detects correct OS type (linux)
- [ ] Detects correct distribution (ubuntu/rhel/centos/etc.)
- [ ] Returns version number
- [ ] Returns kernel version
- [ ] Returns architecture (x86_64/aarch64)
- [ ] Returns hostname
- [ ] Returns uptime
- [ ] Confidence level is appropriate (high/medium/low)
- [ ] Error handling works (test with invalid credentials)
- [ ] Logs are properly formatted and don't expose passwords

---

## Next Steps

Once all tests pass:

1. **Document any issues found** in a testing log
2. **Note which Linux distributions were tested** (Ubuntu, RHEL, CentOS, etc.)
3. **Proceed to Sprint 2**: Application Detection - Process & Port Scanning

---

## Quick Test Commands

```bash
# Quick validation suite
cd python/cyberres-mcp

# 1. Server creation
uv run python -c "from cyberres_mcp.server import create_app; create_app(); print('✅ Server OK')"

# 2. Models
uv run python -c "from cyberres_mcp.models import OSType, DiscoveryRequest; print('✅ Models OK')"

# 3. OS Detector
uv run python -c "from cyberres_mcp.plugins.workload_discovery import OSDetector; OSDetector(); print('✅ Detector OK')"

# 4. Full server start (Ctrl+C to stop)
uv run cyberres-mcp
```

---

**Testing Time Estimate**: 15-30 minutes  
**Required Resources**: 1 Linux test server with SSH access  
**Success Rate Target**: 100% of tests passing