# Code Refactoring Plan: SSH Connectivity Consolidation

**Date:** 2026-02-11  
**Status:** Pre-Sprint 3 Review  
**Priority:** HIGH - Must complete before Sprint 3

---

## Executive Summary

Analysis of the codebase reveals **significant duplication** in SSH connectivity implementations across 4 different modules. This refactoring plan consolidates SSH functionality into a unified, reusable utility module to improve maintainability, reduce bugs, and enable consistent error handling.

**Impact:**
- **4 duplicate SSH implementations** → 1 unified implementation
- **114 SSH-related code references** across codebase
- **Estimated effort:** 4-6 hours
- **Risk:** LOW (backward compatible, comprehensive tests)

---

## 1. Current State Analysis

### 1.1 Identified SSH Implementations

| Location | Function | Return Type | Key Features | Lines |
|----------|----------|-------------|--------------|-------|
| `vms_validator.py` | `_ssh_exec()` | `(int, str, str)` | Basic SSH, RSA key only | 25 |
| `mongo_db.py` | `run_ssh_command()` | `(int, str, str)` | Ed25519 + RSA fallback | 47 |
| `models.py` | `create_ssh_executor()` | `Callable` | Returns closure, different signature | 47 |
| `os_detector.py` | Wrapper | Uses `_ssh_exec` | Adapter pattern | 18 |

### 1.2 Signature Differences

**Problem:** Inconsistent return types and parameter orders

```python
# vms_validator.py
_ssh_exec(host, username, password, key_path, cmd, port, timeout)
→ Returns: (exit_code, stdout, stderr)

# mongo_db.py  
run_ssh_command(host, username, password, key_path, command, port, timeout)
→ Returns: (exit_code, stdout, stderr)

# models.py
create_ssh_executor() → Callable
  ssh_exec(command)
  → Returns: (stdout, stderr, exit_code)  # DIFFERENT ORDER!
```

**Impact:** Confusion, bugs, difficult maintenance

### 1.3 Feature Comparison

| Feature | vms_validator | mongo_db | models.py | Needed |
|---------|--------------|----------|-----------|--------|
| Password auth | ✅ | ✅ | ✅ | ✅ |
| RSA key | ✅ | ✅ | ✅ | ✅ |
| Ed25519 key | ❌ | ✅ | ❌ | ✅ |
| Key fallback | ❌ | ✅ | ✅ | ✅ |
| Timeout config | ✅ | ✅ | ✅ | ✅ |
| Error handling | Basic | Basic | Try/catch | ✅ Enhanced |
| Connection reuse | ❌ | ❌ | ❌ | 🔄 Future |
| Logging | ❌ | ❌ | ❌ | ✅ |

### 1.4 Usage Patterns

**Direct SSH Execution (3 modules):**
- `vms_validator.py` - VM validation tools
- `mongo_db.py` - MongoDB tools  
- `oracle_db.py` - Oracle tools (uses mongo_db's function)

**Callable Pattern (2 modules):**
- `models.py` - DiscoveryRequest.create_ssh_executor()
- `workload_discovery/*` - Process/port scanners

---

## 2. Duplication Impact Analysis

### 2.1 Maintenance Issues

1. **Bug Fixes Must Be Applied 4 Times**
   - Example: Ed25519 key support added to mongo_db but not vms_validator
   - Security patches need multiple updates

2. **Inconsistent Behavior**
   - Different timeout defaults (5s vs 10s vs 30s vs 60s)
   - Different error handling strategies
   - Different return value orders

3. **Testing Complexity**
   - Must test SSH in 4 different contexts
   - Difficult to ensure consistent behavior

### 2.2 Code Metrics

```
Total SSH-related code: ~137 lines (duplicated logic)
After refactoring: ~80 lines (single implementation)
Reduction: 41% less code to maintain
```

### 2.3 Risk Assessment

| Risk | Current | After Refactoring |
|------|---------|-------------------|
| Bug in SSH code affects multiple tools | HIGH | LOW |
| Inconsistent timeout behavior | HIGH | NONE |
| Missing security features | MEDIUM | LOW |
| Difficult to add new auth methods | HIGH | LOW |
| Test coverage gaps | MEDIUM | LOW |

---

## 3. Proposed Solution

### 3.1 Design Principles

1. **Single Responsibility:** One SSH utility module
2. **Backward Compatibility:** Existing code continues to work
3. **Flexible API:** Support both direct and callable patterns
4. **Enhanced Features:** Logging, better error handling, all key types
5. **Testability:** Easy to mock and test

### 3.2 New Module Structure

```
src/cyberres_mcp/plugins/
├── ssh_utils.py          # NEW: Unified SSH utilities
├── vms_validator.py      # REFACTOR: Use ssh_utils
├── mongo_db.py           # REFACTOR: Use ssh_utils
├── oracle_db.py          # REFACTOR: Use ssh_utils
└── workload_discovery/
    ├── os_detector.py    # REFACTOR: Use ssh_utils
    └── ...
```

### 3.3 Unified SSH API

```python
# ssh_utils.py - NEW MODULE

from typing import Tuple, Callable, Optional
import paramiko
import logging

logger = logging.getLogger("mcp.ssh_utils")


class SSHExecutor:
    """
    Unified SSH command executor with connection management.
    Supports password and key-based authentication (RSA, Ed25519, ECDSA).
    """
    
    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        port: int = 22,
        timeout: float = 30.0,
        connect_timeout: float = 10.0
    ):
        """Initialize SSH executor with connection parameters."""
        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path
        self.port = port
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self._client: Optional[paramiko.SSHClient] = None
    
    def connect(self) -> None:
        """Establish SSH connection."""
        if self._client is not None:
            return  # Already connected
        
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            'hostname': self.host,
            'port': self.port,
            'username': self.username,
            'timeout': self.connect_timeout
        }
        
        if self.key_path:
            # Try multiple key types
            pkey = self._load_private_key(self.key_path)
            if pkey:
                connect_kwargs['pkey'] = pkey
            else:
                # Fallback: let paramiko auto-detect
                connect_kwargs['key_filename'] = self.key_path
        elif self.password:
            connect_kwargs['password'] = self.password
        else:
            raise ValueError("Either password or key_path must be provided")
        
        logger.debug(f"Connecting to {self.host}:{self.port} as {self.username}")
        self._client.connect(**connect_kwargs)
        logger.debug(f"Connected to {self.host}")
    
    def _load_private_key(self, key_path: str) -> Optional[paramiko.PKey]:
        """Try loading private key with multiple key types."""
        key_types = [
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
            paramiko.DSSKey
        ]
        
        for KeyClass in key_types:
            try:
                return KeyClass.from_private_key_file(key_path)
            except Exception:
                continue
        
        logger.warning(f"Could not load key {key_path} with any known type")
        return None
    
    def execute(self, command: str) -> Tuple[int, str, str]:
        """
        Execute command and return (exit_code, stdout, stderr).
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if self._client is None:
            self.connect()
        
        logger.debug(f"Executing: {command[:100]}...")
        
        try:
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=self.timeout
            )
            
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            logger.debug(f"Command completed with exit code {exit_code}")
            return exit_code, out, err
            
        except Exception as e:
            logger.error(f"SSH execution failed: {e}")
            return 1, "", str(e)
    
    def close(self) -> None:
        """Close SSH connection."""
        if self._client:
            try:
                self._client.close()
                logger.debug(f"Closed connection to {self.host}")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._client = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def create_executor(self) -> Callable[[str], Tuple[str, str, int]]:
        """
        Create a callable executor for workload discovery pattern.
        
        Returns:
            Callable that takes command and returns (stdout, stderr, exit_code)
        """
        def executor(command: str) -> Tuple[str, str, int]:
            exit_code, stdout, stderr = self.execute(command)
            return stdout, stderr, exit_code  # Different order for compatibility
        
        return executor


# Convenience functions for backward compatibility

def ssh_exec(
    host: str,
    username: str,
    command: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22,
    timeout: float = 30.0
) -> Tuple[int, str, str]:
    """
    Execute single SSH command (backward compatible).
    
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    with SSHExecutor(host, username, password, key_path, port, timeout) as executor:
        return executor.execute(command)


def create_ssh_executor(
    host: str,
    username: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22,
    timeout: float = 30.0
) -> Callable[[str], Tuple[str, str, int]]:
    """
    Create SSH executor callable (for workload discovery).
    
    Returns:
        Callable that takes command and returns (stdout, stderr, exit_code)
    """
    executor = SSHExecutor(host, username, password, key_path, port, timeout)
    executor.connect()
    return executor.create_executor()
```

---

## 4. Refactoring Steps

### Phase 1: Create Unified Module (1-2 hours)

**Step 1.1:** Create `ssh_utils.py`
- Implement `SSHExecutor` class
- Add convenience functions
- Add comprehensive docstrings
- Add logging

**Step 1.2:** Create unit tests
- Test password authentication
- Test key authentication (RSA, Ed25519)
- Test error handling
- Test context manager
- Test callable pattern

**Acceptance Criteria:**
- ✅ All key types supported
- ✅ Both API patterns work
- ✅ 100% test coverage
- ✅ Logging implemented

### Phase 2: Refactor Existing Modules (2-3 hours)

**Step 2.1:** Update `vms_validator.py`
```python
# BEFORE
def _ssh_exec(host, username, password, key_path, cmd, port, timeout):
    client = SSHClient()
    # ... 25 lines of code ...

# AFTER
from .ssh_utils import ssh_exec

def _ssh_exec(host, username, password, key_path, cmd, port, timeout):
    return ssh_exec(host, username, cmd, password, key_path, port, timeout)
```

**Step 2.2:** Update `mongo_db.py`
```python
# BEFORE
def run_ssh_command(host, username, password, key_path, command, port, timeout):
    import paramiko
    # ... 47 lines of code ...

# AFTER
from .ssh_utils import ssh_exec

def run_ssh_command(host, username, password, key_path, command, port, timeout):
    return ssh_exec(host, username, command, password, key_path, port, timeout)
```

**Step 2.3:** Update `models.py`
```python
# BEFORE
def create_ssh_executor(self):
    import paramiko
    def ssh_exec(command):
        # ... 47 lines of code ...
    return ssh_exec

# AFTER
def create_ssh_executor(self):
    from .plugins.ssh_utils import create_ssh_executor
    return create_ssh_executor(
        self.host,
        self.ssh_user,
        self.ssh_password,
        self.ssh_key_path,
        self.ssh_port,
        timeout=60.0
    )
```

**Step 2.4:** Update `os_detector.py`
```python
# BEFORE
from ..vms_validator import _ssh_exec
def ssh_exec(cmd):
    return _ssh_exec(host, username, password, key_path, cmd, port, timeout)

# AFTER
from ..ssh_utils import SSHExecutor
executor = SSHExecutor(host, username, password, key_path, port, timeout)
ssh_exec = lambda cmd: executor.execute(cmd)
```

**Acceptance Criteria:**
- ✅ All modules use ssh_utils
- ✅ No duplicate SSH code
- ✅ Backward compatible APIs
- ✅ All existing tests pass

### Phase 3: Update Tests (1 hour)

**Step 3.1:** Update existing tests
- Ensure all SSH mocking still works
- Update any hardcoded expectations
- Add tests for new features

**Step 3.2:** Run full test suite
```bash
uv run python test_sprint1.py  # Should pass
uv run python test_sprint2.py  # Should pass
# Add any other test files
```

**Acceptance Criteria:**
- ✅ Sprint 1 tests: 6/6 passing
- ✅ Sprint 2 tests: 6/6 passing
- ✅ No regressions

### Phase 4: Documentation (30 minutes)

**Step 4.1:** Update documentation
- Add ssh_utils.py to architecture docs
- Update IMPROVEMENTS.md
- Add migration guide for future developers

**Step 4.2:** Add code examples
- Show how to use SSHExecutor
- Show backward compatible usage
- Show context manager pattern

---

## 5. Benefits

### 5.1 Immediate Benefits

1. **Single Source of Truth**
   - One place to fix bugs
   - One place to add features
   - Consistent behavior everywhere

2. **Enhanced Features**
   - Support for all key types (Ed25519, RSA, ECDSA, DSS)
   - Comprehensive logging
   - Better error messages
   - Connection reuse capability

3. **Improved Maintainability**
   - 41% less code
   - Clear separation of concerns
   - Easier to test

### 5.2 Long-term Benefits

1. **Future Enhancements**
   - Easy to add connection pooling
   - Easy to add retry logic
   - Easy to add connection caching
   - Easy to add SSH agent support

2. **Better Testing**
   - Single mock point
   - Consistent test patterns
   - Easier integration tests

3. **Security**
   - Centralized security updates
   - Consistent credential handling
   - Audit trail via logging

---

## 6. Risk Mitigation

### 6.1 Backward Compatibility

**Strategy:** Maintain existing function signatures

```python
# Old code continues to work
from plugins.vms_validator import _ssh_exec
rc, out, err = _ssh_exec(host, user, password, key, cmd, port, timeout)

# New code can use enhanced API
from plugins.ssh_utils import SSHExecutor
with SSHExecutor(host, user, password, key, port) as ssh:
    rc, out, err = ssh.execute(cmd)
```

### 6.2 Testing Strategy

1. **Unit Tests:** Test ssh_utils in isolation
2. **Integration Tests:** Test with real SSH (optional)
3. **Regression Tests:** Run all existing tests
4. **Manual Testing:** Test each tool manually

### 6.3 Rollback Plan

If issues arise:
1. Keep old implementations commented out
2. Can revert individual modules
3. Full rollback possible within 15 minutes

---

## 7. Implementation Timeline

| Phase | Duration | Dependencies | Deliverables |
|-------|----------|--------------|--------------|
| Phase 1: Create ssh_utils | 1-2 hours | None | ssh_utils.py, unit tests |
| Phase 2: Refactor modules | 2-3 hours | Phase 1 | Updated 4 modules |
| Phase 3: Update tests | 1 hour | Phase 2 | All tests passing |
| Phase 4: Documentation | 30 min | Phase 3 | Updated docs |
| **Total** | **4.5-6.5 hours** | | **Complete refactoring** |

---

## 8. Success Criteria

### 8.1 Code Quality

- ✅ Single SSH implementation
- ✅ No duplicate SSH code
- ✅ Comprehensive logging
- ✅ All key types supported
- ✅ Context manager pattern
- ✅ Type hints throughout

### 8.2 Testing

- ✅ 100% test coverage for ssh_utils
- ✅ All Sprint 1 tests passing (6/6)
- ✅ All Sprint 2 tests passing (6/6)
- ✅ No regressions in existing functionality

### 8.3 Documentation

- ✅ API documentation complete
- ✅ Migration guide created
- ✅ Code examples provided
- ✅ Architecture docs updated

---

## 9. Post-Refactoring Validation

### 9.1 Validation Checklist

```bash
# 1. Run all tests
cd python/cyberres-mcp
uv run python test_sprint1.py  # Expect: 6/6 passing
uv run python test_sprint2.py  # Expect: 6/6 passing

# 2. Test each tool manually
# - vm_validator tools
# - MongoDB tools
# - Oracle tools
# - Workload discovery tools

# 3. Check code metrics
# - Lines of SSH code reduced by ~40%
# - No duplicate implementations
# - Consistent error handling

# 4. Verify logging
# - SSH connections logged
# - Command execution logged
# - Errors logged with context
```

### 9.2 Performance Validation

- SSH connection time: No degradation
- Command execution time: No degradation
- Memory usage: Slight improvement (connection reuse)

---

## 10. Future Enhancements

After refactoring is complete, these enhancements become trivial:

1. **Connection Pooling** (Sprint 4)
   - Reuse connections for multiple commands
   - Significant performance improvement

2. **Retry Logic** (Sprint 4)
   - Automatic retry on transient failures
   - Exponential backoff

3. **SSH Agent Support** (Sprint 5)
   - Use SSH agent for key management
   - No key files needed

4. **Parallel Execution** (Sprint 5)
   - Execute commands on multiple hosts
   - Thread pool for concurrent SSH

5. **Connection Caching** (Future)
   - Cache connections between tool calls
   - Dramatic performance improvement

---

## 11. Conclusion

This refactoring is **essential** before Sprint 3 to:
- Eliminate technical debt
- Improve code quality
- Enable future enhancements
- Reduce maintenance burden

**Recommendation:** Complete this refactoring before starting Sprint 3 development.

**Estimated ROI:**
- **Time Investment:** 4.5-6.5 hours
- **Time Saved:** 2-3 hours per future SSH-related change
- **Break-even:** After 2-3 SSH-related changes
- **Long-term:** Significant maintenance savings

---

**Status:** ✅ **READY FOR IMPLEMENTATION**

**Next Steps:**
1. Review and approve this plan
2. Create feature branch: `refactor/ssh-consolidation`
3. Implement Phase 1 (ssh_utils.py)
4. Implement Phase 2 (refactor modules)
5. Implement Phase 3 (update tests)
6. Implement Phase 4 (documentation)
7. Merge to main
8. Begin Sprint 3

---

*Document prepared by: IBM Bob*  
*Date: 2026-02-11*  
*Version: 1.0*