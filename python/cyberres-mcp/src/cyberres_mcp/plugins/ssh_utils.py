"""
Unified SSH utilities for cyberres-mcp.

This module provides a consolidated SSH execution interface to eliminate
code duplication across the codebase. It supports multiple authentication
methods, all SSH key types, and provides both direct and callable patterns.

Copyright contributors to the agentic-ai-cyberres project
"""

from typing import Tuple, Callable, Optional
import paramiko
import logging
import os

logger = logging.getLogger("mcp.ssh_utils")

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _ssh_security_config() -> Tuple[bool, bool, Optional[str]]:
    """
    Return SSH host-key security settings.

    Returns:
        (strict_host_key_checking, trust_unknown_hosts, known_hosts_file)
    """
    strict = _env_bool("SSH_STRICT_HOST_KEY_CHECKING", True)
    trust_unknown = _env_bool("SSH_TRUST_UNKNOWN_HOSTS", False)
    known_hosts_file: Optional[str] = os.getenv("SSH_KNOWN_HOSTS_FILE")
    try:
        try:
            from ..settings import SETTINGS
        except Exception:
            from cyberres_mcp.settings import SETTINGS  # type: ignore
        strict = bool(getattr(SETTINGS, "ssh_strict_host_key_checking", strict))
        trust_unknown = bool(getattr(SETTINGS, "ssh_trust_unknown_hosts", trust_unknown))
        configured_known_hosts = getattr(SETTINGS, "ssh_known_hosts_file", "")
        if configured_known_hosts:
            known_hosts_file = configured_known_hosts
    except Exception:
        pass

    if known_hosts_file:
        known_hosts_file = known_hosts_file.strip() or None
    return strict, trust_unknown, known_hosts_file


class SSHExecutor:
    """
    Unified SSH command executor with connection management.
    
    Supports:
    - Password and key-based authentication
    - Multiple key types (RSA, Ed25519, ECDSA, DSS)
    - Connection reuse
    - Context manager pattern
    - Comprehensive logging
    
    Example:
        >>> # Direct usage
        >>> executor = SSHExecutor("host", "user", password="pass")
        >>> exit_code, stdout, stderr = executor.execute("ls -la")
        
        >>> # Context manager
        >>> with SSHExecutor("host", "user", key_path="/path/to/key") as ssh:
        ...     exit_code, stdout, stderr = ssh.execute("uptime")
        
        >>> # Callable pattern (for workload discovery)
        >>> executor = SSHExecutor("host", "user", password="pass")
        >>> ssh_exec = executor.create_executor()
        >>> stdout, stderr, exit_code = ssh_exec("hostname")
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
        """
        Initialize SSH executor with connection parameters.
        
        Args:
            host: Target hostname or IP address
            username: SSH username
            password: SSH password (optional if using key)
            key_path: Path to SSH private key (optional if using password)
            port: SSH port (default: 22)
            timeout: Command execution timeout in seconds (default: 30.0)
            connect_timeout: Connection timeout in seconds (default: 10.0)
            
        Raises:
            ValueError: If neither password nor key_path is provided
        """
        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path
        self.port = port
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self._client: Optional[paramiko.SSHClient] = None
        
        if not password and not key_path:
            raise ValueError("Either password or key_path must be provided")
    
    def connect(self) -> None:
        """
        Establish SSH connection.
        
        Raises:
            paramiko.AuthenticationException: If authentication fails
            paramiko.SSHException: If SSH connection fails
            socket.error: If network connection fails
        """
        if self._client is not None:
            return  # Already connected
        
        self._client = paramiko.SSHClient()
        strict_host_key_checking, trust_unknown_hosts, known_hosts_file = _ssh_security_config()
        self._client.load_system_host_keys()
        if known_hosts_file:
            try:
                self._client.load_host_keys(known_hosts_file)
            except Exception as ex:
                logger.warning(f"Failed to load SSH known_hosts file '{known_hosts_file}': {ex}")
        if trust_unknown_hosts:
            logger.warning(
                "SSH trust_unknown_hosts is enabled; unknown host keys will be accepted (TOFU)."
            )
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        elif strict_host_key_checking:
            self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            logger.warning(
                "SSH strict host-key checking is disabled; unknown host keys may be accepted."
            )
            self._client.set_missing_host_key_policy(paramiko.WarningPolicy())
        
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
                logger.debug(f"Using private key from {self.key_path}")
            else:
                # Fallback: let paramiko auto-detect key type
                connect_kwargs['key_filename'] = self.key_path
                logger.debug(f"Using key_filename fallback for {self.key_path}")
        elif self.password:
            connect_kwargs['password'] = self.password
            logger.debug(f"Using password authentication")
        
        logger.info(f"Connecting to {self.host}:{self.port} as {self.username}")
        self._client.connect(**connect_kwargs)
        logger.info(f"Successfully connected to {self.host}")
    
    def _load_private_key(self, key_path: str) -> Optional[paramiko.PKey]:
        """
        Try loading private key with multiple key types.
        
        Args:
            key_path: Path to private key file
            
        Returns:
            Loaded private key or None if all attempts fail
        """
        key_types = [
            ('Ed25519', paramiko.Ed25519Key),
            ('RSA', paramiko.RSAKey),
            ('ECDSA', paramiko.ECDSAKey),
            ('DSS', paramiko.DSSKey)
        ]
        
        for key_name, KeyClass in key_types:
            try:
                key = KeyClass.from_private_key_file(key_path)
                logger.debug(f"Successfully loaded {key_name} key from {key_path}")
                return key
            except Exception as e:
                logger.debug(f"Failed to load {key_name} key: {e}")
                continue
        
        logger.warning(f"Could not load key {key_path} with any known type")
        return None
    
    def execute(self, command: str, stdin_data: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Execute command and return (exit_code, stdout, stderr).
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
            
        Raises:
            Exception: If command execution fails
        """
        if self._client is None:
            self.connect()
        
        logger.debug(
            "Executing SSH command on %s (command_length=%d, stdin_length=%d)",
            self.host,
            len(command),
            len(stdin_data) if stdin_data else 0,
        )
        
        try:
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=self.timeout
            )
            if stdin_data:
                stdin.write(stdin_data)
                stdin.flush()
                stdin.channel.shutdown_write()
            
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code == 0:
                logger.debug(f"Command completed successfully (exit code: {exit_code})")
            else:
                logger.warning(f"Command failed with exit code {exit_code}")
                if err:
                    logger.debug(f"stderr: {err[:200]}")
            
            return exit_code, out, err
            
        except Exception as e:
            logger.error(f"SSH execution failed on {self.host}: {e}")
            return 1, "", str(e)
    
    def close(self) -> None:
        """Close SSH connection."""
        if self._client:
            try:
                self._client.close()
                logger.debug(f"Closed connection to {self.host}")
            except Exception as e:
                logger.warning(f"Error closing connection to {self.host}: {e}")
            finally:
                self._client = None
    
    def __enter__(self):
        """Context manager entry - establish connection."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()
        return False  # Don't suppress exceptions
    
    def create_executor(self) -> Callable[[str], Tuple[str, str, int]]:
        """
        Create a callable executor for workload discovery pattern.
        
        This returns a function with signature (command) -> (stdout, stderr, exit_code)
        which is different from the direct execute() method's return order.
        
        Returns:
            Callable that takes command and returns (stdout, stderr, exit_code)
            
        Example:
            >>> executor = SSHExecutor("host", "user", password="pass")
            >>> ssh_exec = executor.create_executor()
            >>> stdout, stderr, exit_code = ssh_exec("hostname")
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
    timeout: float = 30.0,
    stdin_data: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Execute single SSH command (backward compatible with existing code).
    
    This is a convenience function that creates an SSHExecutor, executes
    a single command, and closes the connection.
    
    Args:
        host: Target hostname or IP address
        username: SSH username
        command: Command to execute
        password: SSH password (optional if using key)
        key_path: Path to SSH private key (optional if using password)
        port: SSH port (default: 22)
        timeout: Command execution timeout in seconds (default: 30.0)
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
        
    Example:
        >>> exit_code, stdout, stderr = ssh_exec(
        ...     "10.0.1.5", "admin", "uptime",
        ...     password="secret"
        ... )
    """
    with SSHExecutor(host, username, password, key_path, port, timeout) as executor:
        return executor.execute(command, stdin_data=stdin_data)


def create_ssh_executor(
    host: str,
    username: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22,
    timeout: float = 30.0
) -> Callable[[str], Tuple[str, str, int]]:
    """
    Create SSH executor callable (for workload discovery pattern).
    
    This creates a persistent SSHExecutor and returns a callable that
    can be used multiple times. The connection remains open until
    explicitly closed.
    
    Args:
        host: Target hostname or IP address
        username: SSH username
        password: SSH password (optional if using key)
        key_path: Path to SSH private key (optional if using password)
        port: SSH port (default: 22)
        timeout: Command execution timeout in seconds (default: 30.0)
        
    Returns:
        Callable that takes command and returns (stdout, stderr, exit_code)
        
    Example:
        >>> ssh_exec = create_ssh_executor(
        ...     "10.0.1.5", "admin",
        ...     password="secret"
        ... )
        >>> stdout, stderr, exit_code = ssh_exec("hostname")
        >>> stdout, stderr, exit_code = ssh_exec("uptime")
    """
    executor = SSHExecutor(host, username, password, key_path, port, timeout)
    executor.connect()
    return executor.create_executor()


# Made with Bob
