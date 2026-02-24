"""
Unit tests for ssh_utils module.

Tests the unified SSH utilities for proper functionality,
error handling, and backward compatibility.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cyberres_mcp.plugins.ssh_utils import SSHExecutor, ssh_exec, create_ssh_executor


def test_init_with_password():
    """Test 1: Initialization with password."""
    print("\n" + "="*80)
    print("TEST 1: SSHExecutor initialization with password")
    print("="*80)
    
    executor = SSHExecutor("host", "user", password="pass")
    assert executor.host == "host"
    assert executor.username == "user"
    assert executor.password == "pass"
    assert executor.key_path is None
    assert executor.port == 22
    assert executor.timeout == 30.0
    
    print("✓ Initialization successful")
    print("✓ All parameters set correctly")
    return True


def test_init_with_key():
    """Test 2: Initialization with SSH key."""
    print("\n" + "="*80)
    print("TEST 2: SSHExecutor initialization with SSH key")
    print("="*80)
    
    executor = SSHExecutor("host", "user", key_path="/path/to/key")
    assert executor.host == "host"
    assert executor.username == "user"
    assert executor.password is None
    assert executor.key_path == "/path/to/key"
    
    print("✓ Initialization with key successful")
    print("✓ Key path set correctly")
    return True


def test_init_without_credentials():
    """Test 3: Initialization fails without credentials."""
    print("\n" + "="*80)
    print("TEST 3: SSHExecutor initialization without credentials (should fail)")
    print("="*80)
    
    try:
        SSHExecutor("host", "user")
        print("❌ Should have raised ValueError")
        return False
    except ValueError as e:
        if "Either password or key_path" in str(e):
            print("✓ Correctly raised ValueError")
            print(f"✓ Error message: {e}")
            return True
        else:
            print(f"❌ Wrong error message: {e}")
            return False


@patch('cyberres_mcp.plugins.ssh_utils.paramiko.SSHClient')
def test_connect_with_password(mock_ssh_client):
    """Test 4: Connection with password."""
    print("\n" + "="*80)
    print("TEST 4: SSH connection with password")
    print("="*80)
    
    mock_client = Mock()
    mock_ssh_client.return_value = mock_client
    
    executor = SSHExecutor("host", "user", password="pass")
    executor.connect()
    
    mock_client.set_missing_host_key_policy.assert_called_once()
    mock_client.connect.assert_called_once()
    
    # Check connect was called with correct parameters
    call_kwargs = mock_client.connect.call_args[1]
    assert call_kwargs['hostname'] == "host"
    assert call_kwargs['username'] == "user"
    assert call_kwargs['password'] == "pass"
    assert call_kwargs['port'] == 22
    
    print("✓ Connection established")
    print("✓ Correct parameters passed to paramiko")
    return True


@patch('cyberres_mcp.plugins.ssh_utils.paramiko.SSHClient')
def test_execute_command(mock_ssh_client):
    """Test 5: Command execution."""
    print("\n" + "="*80)
    print("TEST 5: SSH command execution")
    print("="*80)
    
    # Setup mocks
    mock_client = Mock()
    mock_ssh_client.return_value = mock_client
    
    mock_stdout = Mock()
    mock_stdout.read.return_value = b"output"
    mock_stdout.channel.recv_exit_status.return_value = 0
    
    mock_stderr = Mock()
    mock_stderr.read.return_value = b""
    
    mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
    
    # Execute
    executor = SSHExecutor("host", "user", password="pass")
    exit_code, stdout, stderr = executor.execute("ls -la")
    
    # Verify
    assert exit_code == 0
    assert stdout == "output"
    assert stderr == ""
    mock_client.exec_command.assert_called_once_with("ls -la", timeout=30.0)
    
    print("✓ Command executed successfully")
    print(f"✓ Exit code: {exit_code}")
    print(f"✓ Output: {stdout}")
    return True


@patch('cyberres_mcp.plugins.ssh_utils.paramiko.SSHClient')
def test_execute_command_with_error(mock_ssh_client):
    """Test 6: Command execution with non-zero exit code."""
    print("\n" + "="*80)
    print("TEST 6: SSH command execution with error")
    print("="*80)
    
    mock_client = Mock()
    mock_ssh_client.return_value = mock_client
    
    mock_stdout = Mock()
    mock_stdout.read.return_value = b""
    mock_stdout.channel.recv_exit_status.return_value = 1
    
    mock_stderr = Mock()
    mock_stderr.read.return_value = b"error message"
    
    mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
    
    executor = SSHExecutor("host", "user", password="pass")
    exit_code, stdout, stderr = executor.execute("false")
    
    assert exit_code == 1
    assert stdout == ""
    assert stderr == "error message"
    
    print("✓ Error handled correctly")
    print(f"✓ Exit code: {exit_code}")
    print(f"✓ Error message: {stderr}")
    return True


@patch('cyberres_mcp.plugins.ssh_utils.paramiko.SSHClient')
def test_context_manager(mock_ssh_client):
    """Test 7: Context manager usage."""
    print("\n" + "="*80)
    print("TEST 7: Context manager pattern")
    print("="*80)
    
    mock_client = Mock()
    mock_ssh_client.return_value = mock_client
    
    with SSHExecutor("host", "user", password="pass") as executor:
        assert executor._client is not None
        print("✓ Connection established in context")
    
    mock_client.close.assert_called_once()
    print("✓ Connection closed on exit")
    return True


@patch('cyberres_mcp.plugins.ssh_utils.paramiko.SSHClient')
def test_create_executor_callable(mock_ssh_client):
    """Test 8: create_executor returns callable with correct signature."""
    print("\n" + "="*80)
    print("TEST 8: Callable executor pattern")
    print("="*80)
    
    mock_client = Mock()
    mock_ssh_client.return_value = mock_client
    
    mock_stdout = Mock()
    mock_stdout.read.return_value = b"output"
    mock_stdout.channel.recv_exit_status.return_value = 0
    
    mock_stderr = Mock()
    mock_stderr.read.return_value = b"error"
    
    mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
    
    executor = SSHExecutor("host", "user", password="pass")
    ssh_exec_func = executor.create_executor()
    
    # Call the returned function
    stdout, stderr, exit_code = ssh_exec_func("hostname")
    
    # Verify return order is different (stdout, stderr, exit_code)
    assert stdout == "output"
    assert stderr == "error"
    assert exit_code == 0
    
    print("✓ Callable created successfully")
    print("✓ Return signature correct: (stdout, stderr, exit_code)")
    return True


@patch('cyberres_mcp.plugins.ssh_utils.SSHExecutor')
def test_ssh_exec_function(mock_executor_class):
    """Test 9: ssh_exec convenience function."""
    print("\n" + "="*80)
    print("TEST 9: ssh_exec convenience function")
    print("="*80)
    
    mock_executor = Mock()
    mock_executor_class.return_value.__enter__.return_value = mock_executor
    mock_executor.execute.return_value = (0, "output", "")
    
    exit_code, stdout, stderr = ssh_exec(
        "host", "user", "ls",
        password="pass"
    )
    
    assert exit_code == 0
    assert stdout == "output"
    assert stderr == ""
    
    # Verify SSHExecutor was created correctly
    mock_executor_class.assert_called_once_with(
        "host", "user", "pass", None, 22, 30.0
    )
    
    print("✓ Convenience function works")
    print("✓ Backward compatible signature")
    return True


@patch('cyberres_mcp.plugins.ssh_utils.SSHExecutor')
def test_create_ssh_executor_function(mock_executor_class):
    """Test 10: create_ssh_executor convenience function."""
    print("\n" + "="*80)
    print("TEST 10: create_ssh_executor convenience function")
    print("="*80)
    
    mock_executor = Mock()
    mock_executor_class.return_value = mock_executor
    mock_executor.create_executor.return_value = lambda cmd: ("out", "err", 0)
    
    ssh_exec_func = create_ssh_executor(
        "host", "user",
        password="pass"
    )
    
    # Verify it returns a callable
    assert callable(ssh_exec_func)
    
    # Verify SSHExecutor was created and connected
    mock_executor_class.assert_called_once_with(
        "host", "user", "pass", None, 22, 30.0
    )
    mock_executor.connect.assert_called_once()
    mock_executor.create_executor.assert_called_once()
    
    print("✓ Convenience function works")
    print("✓ Returns callable executor")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("SSH UTILS TEST SUITE")
    print("="*80)
    
    tests = [
        ("Initialization with password", test_init_with_password),
        ("Initialization with key", test_init_with_key),
        ("Initialization without credentials", test_init_without_credentials),
        ("Connection with password", test_connect_with_password),
        ("Command execution", test_execute_command),
        ("Command execution with error", test_execute_command_with_error),
        ("Context manager", test_context_manager),
        ("Callable executor", test_create_executor_callable),
        ("ssh_exec convenience function", test_ssh_exec_function),
        ("create_ssh_executor convenience function", test_create_ssh_executor_function),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"\n❌ {name} test FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ {name} test ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! ssh_utils module is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
