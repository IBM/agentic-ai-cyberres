#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Credential management for recovery validation agent."""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class CredentialManager:
    """Manage credentials from environment variables."""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize credential manager.
        
        Args:
            env_file: Path to .env file. If None, uses default .env in current directory.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self._credentials_cache: Dict[str, Any] = {}
    
    def get_ssh_credentials(self, host: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get SSH credentials from environment.
        
        Args:
            host: Optional host-specific credentials (e.g., SSH_USER_192_168_1_10)
        
        Returns:
            Dictionary with ssh_user, ssh_password, ssh_key_path
        """
        prefix = f"SSH_{host.replace('.', '_')}_" if host else "SSH_"
        
        return {
            "ssh_user": os.getenv(f"{prefix}USER") or os.getenv("SSH_USER"),
            "ssh_password": os.getenv(f"{prefix}PASSWORD") or os.getenv("SSH_PASSWORD"),
            "ssh_key_path": os.getenv(f"{prefix}KEY_PATH") or os.getenv("SSH_KEY_PATH"),
        }
    
    def get_oracle_credentials(self, host: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get Oracle database credentials from environment.
        
        Args:
            host: Optional host-specific credentials
        
        Returns:
            Dictionary with db_user, db_password, service_name, port
        """
        prefix = f"ORACLE_{host.replace('.', '_')}_" if host else "ORACLE_"
        
        return {
            "db_user": os.getenv(f"{prefix}USER") or os.getenv("ORACLE_USER"),
            "db_password": os.getenv(f"{prefix}PASSWORD") or os.getenv("ORACLE_PASSWORD"),
            "service_name": os.getenv(f"{prefix}SERVICE") or os.getenv("ORACLE_SERVICE"),
            "port": os.getenv(f"{prefix}PORT") or os.getenv("ORACLE_PORT", "1521"),
        }
    
    def get_mongodb_credentials(self, host: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get MongoDB credentials from environment.
        
        Args:
            host: Optional host-specific credentials
        
        Returns:
            Dictionary with mongo_user, mongo_password, auth_db, port
        """
        prefix = f"MONGO_{host.replace('.', '_')}_" if host else "MONGO_"
        
        return {
            "mongo_user": os.getenv(f"{prefix}USER") or os.getenv("MONGO_USER"),
            "mongo_password": os.getenv(f"{prefix}PASSWORD") or os.getenv("MONGO_PASSWORD"),
            "auth_db": os.getenv(f"{prefix}AUTH_DB") or os.getenv("MONGO_AUTH_DB", "admin"),
            "port": os.getenv(f"{prefix}PORT") or os.getenv("MONGO_PORT", "27017"),
        }
    
    def get_mcp_server_url(self) -> str:
        """Get MCP server URL from environment.
        
        Returns:
            MCP server URL
        """
        return os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
    
    def get_email_config(self) -> Dict[str, Optional[str]]:
        """Get email configuration from environment.
        
        Returns:
            Dictionary with recipient, smtp_server, smtp_port
        """
        return {
            "recipient": os.getenv("USER_EMAIL"),
            "smtp_server": os.getenv("SMTP_SERVER", "localhost"),
            "smtp_port": os.getenv("SMTP_PORT", "25"),
            "from_address": os.getenv("EMAIL_FROM", "recovery-validation@cyberres.com"),
        }
    
    def has_ssh_credentials(self) -> bool:
        """Check if SSH credentials are available in environment."""
        creds = self.get_ssh_credentials()
        return bool(creds["ssh_user"] and (creds["ssh_password"] or creds["ssh_key_path"]))
    
    def has_oracle_credentials(self) -> bool:
        """Check if Oracle credentials are available in environment."""
        creds = self.get_oracle_credentials()
        return bool(creds["db_user"] and creds["db_password"])
    
    def has_mongodb_credentials(self) -> bool:
        """Check if MongoDB credentials are available in environment."""
        creds = self.get_mongodb_credentials()
        return bool(creds["mongo_user"] and creds["mongo_password"])
    
    def merge_with_user_provided(
        self,
        resource_type: str,
        user_provided: Dict[str, Any],
        host: Optional[str] = None
    ) -> Dict[str, Any]:
        """Merge environment credentials with user-provided ones.
        
        User-provided credentials take precedence over environment.
        
        Args:
            resource_type: Type of resource (vm, oracle, mongodb)
            user_provided: User-provided credential dictionary
            host: Optional host for host-specific credentials
        
        Returns:
            Merged credential dictionary
        """
        if resource_type == "vm":
            env_creds = self.get_ssh_credentials(host)
        elif resource_type == "oracle":
            env_creds = self.get_oracle_credentials(host)
        elif resource_type == "mongodb":
            env_creds = self.get_mongodb_credentials(host)
        else:
            return user_provided
        
        # Merge: user-provided takes precedence
        merged = {k: v for k, v in env_creds.items() if v is not None}
        merged.update({k: v for k, v in user_provided.items() if v is not None})
        
        logger.info(
            f"Merged credentials for {resource_type}",
            extra={
                "resource_type": resource_type,
                "has_env_creds": bool(env_creds),
                "has_user_creds": bool(user_provided),
            }
        )
        
        return merged
    
    def validate_credentials(self, resource_type: str, credentials: Dict[str, Any]) -> bool:
        """Validate that required credentials are present.
        
        Args:
            resource_type: Type of resource
            credentials: Credential dictionary to validate
        
        Returns:
            True if valid, False otherwise
        """
        if resource_type == "vm":
            return bool(
                credentials.get("ssh_user") and
                (credentials.get("ssh_password") or credentials.get("ssh_key_path"))
            )
        elif resource_type == "oracle":
            return bool(
                credentials.get("db_user") and
                credentials.get("db_password") and
                (credentials.get("dsn") or credentials.get("service_name"))
            )
        elif resource_type == "mongodb":
            # MongoDB can work without credentials for local connections
            return True
        
        return False


# Global instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager(env_file: Optional[str] = None) -> CredentialManager:
    """Get or create global credential manager instance.
    
    Args:
        env_file: Path to .env file
    
    Returns:
        CredentialManager instance
    """
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager(env_file)
    return _credential_manager

# Made with Bob
