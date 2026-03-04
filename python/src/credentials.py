#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Credential management for the BeeAI recovery-validation agent.

Two classes are provided:

CredentialManager  — legacy env-var based manager (kept for backward compat)
CredentialResolver — new secrets.json based resolver used by beeai_interactive.py

Credential resolution order (CredentialResolver):
  1. config/secrets.json  — by hostname/IP as the top-level key (exact match)
  2. Environment variables — SSH_USER / SSH_PASSWORD / SSH_KEY_PATH
  3. CredentialNotFoundError — no silent empty-string fallback

secrets.json schema (host-keyed):
  {
    "192.168.1.100": {
      "ssh": {
        "username": "root",
        "password": "secret",
        "key_path": "/home/admin/.ssh/id_rsa"      // optional
      },
      "oracle": {                                  // optional
        "username": "system",
        "password": "oracle_pass"
      },
      "mongo": {                                   // optional
        "username": "admin",
        "password": "mongo_pass"
      }
    },
    "prod-db-01": {
      "ssh": { "username": "admin", "password": "secret" },
      "oracle": { "username": "system", "password": "oracle_pass" }
    }
  }

The top-level key is the host identifier (IP address or hostname).
The agent resolves credentials by looking up the exact host string from the prompt.

Extension point — SecretsBackend protocol:
  Swap LocalFileBackend for a cloud secrets manager backend
  without changing any agent code.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────

class CredentialNotFoundError(Exception):
    """Raised when no credential can be found for a host or credential ID."""


# ── SecretsBackend protocol ───────────────────────────────────────────────────

class SecretsBackend(ABC):
    """
    Abstract base for secrets storage backends.

    Implement this to swap LocalFileBackend for a cloud secrets manager:
      - AWSSecretsBackend   (boto3 get_secret_value)
      - VaultBackend        (hvac client)
      - IBMSecretsBackend   (IBM Secrets Manager SDK)
    """

    @abstractmethod
    def load_all(self) -> Dict[str, Any]:
        """
        Return the full secrets dictionary keyed by credential ID.

        Returns:
            dict mapping credential_id → credential entry dict
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the backend is reachable / configured."""


class LocalFileBackend(SecretsBackend):
    """
    Default backend — reads credentials from a local JSON file.

    The file is expected at ``secrets_file`` (default: config/secrets.json).
    If the file does not exist the backend returns an empty dict (no error),
    allowing the resolver to fall through to environment variables.
    """

    def __init__(self, secrets_file: str = "config/secrets.json"):
        self._path = Path(secrets_file)
        self._cache: Optional[Dict[str, Any]] = None

    def load_all(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache

        if not self._path.exists():
            logger.debug(f"Secrets file not found: {self._path} — using env vars only")
            self._cache = {}
            return self._cache

        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data: Dict[str, Any] = json.load(fh)
            logger.info(
                f"Loaded {len(data)} credential(s) from {self._path}",
                extra={"agent": "CredentialResolver"},
            )
            self._cache = data
            return data
        except json.JSONDecodeError as exc:
            logger.error(
                f"Invalid JSON in secrets file {self._path}: {exc}",
                extra={"agent": "CredentialResolver"},
            )
            self._cache = {}
            return {}
        except OSError as exc:
            logger.error(
                f"Cannot read secrets file {self._path}: {exc}",
                extra={"agent": "CredentialResolver"},
            )
            self._cache = {}
            return {}

    def is_available(self) -> bool:
        return self._path.exists()

    def invalidate_cache(self) -> None:
        """Force re-read of the secrets file on next load_all() call."""
        self._cache = None


# ── CredentialResolver ────────────────────────────────────────────────────────

class CredentialResolver:
    """
    Resolve credentials for a target host.

    Resolution order:
      1. secrets.json — by credential_id (exact, case-insensitive match)
      2. secrets.json — by hostname/IP appearing in the entry's "hosts" list
      3. Environment variables — SSH_USER / SSH_PASSWORD / SSH_KEY_PATH
      4. CredentialNotFoundError

    Args:
        secrets_file:    Path to secrets.json (default: config/secrets.json)
        fallback_to_env: If True, fall back to env vars when secrets.json has
                         no match.  Set to False to enforce secrets.json only.
        backend:         Optional custom SecretsBackend.  Defaults to
                         LocalFileBackend(secrets_file).

    Example::

        resolver = CredentialResolver(secrets_file="config/secrets.json")
        creds = await resolver.resolve(resource_type="vm", hostname="192.168.1.100")
        ssh_user = creds["ssh"]["username"]
    """

    def __init__(
        self,
        secrets_file: str = "config/secrets.json",
        fallback_to_env: bool = True,
        backend: Optional[SecretsBackend] = None,
    ):
        self._fallback_to_env = fallback_to_env
        self._backend: SecretsBackend = backend or LocalFileBackend(secrets_file)
        load_dotenv()  # ensure env vars are loaded

    # ── Public API ────────────────────────────────────────────────────────────

    async def resolve(
        self,
        resource_type: str = "vm",
        credential_id: Optional[str] = None,   # kept for API compat; ignored (host-keyed schema)
        hostname: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolve credentials for a host using the host-keyed secrets.json schema.

        The top-level key in secrets.json IS the host identifier (IP or hostname).
        Example secrets.json::

            {
              "9.11.68.243": {
                "ssh": { "username": "root", "password": "pass" }
              }
            }

        Args:
            resource_type: "vm" | "oracle" | "mongodb"  (used for env-var fallback)
            credential_id: Ignored — kept for API backward compatibility only.
                           In the host-keyed schema the hostname IS the key.
            hostname:      IP address or hostname to look up in secrets.json.

        Returns:
            dict with keys: "ssh", "oracle", "mongo", "credential_id"
            Each sub-dict contains the fields from secrets.json for that section.

        Raises:
            CredentialNotFoundError: If no credential can be found and
                                     fallback_to_env is False, or env vars are
                                     also empty.
        """
        secrets = self._backend.load_all()

        # ── Step 1: hostname/IP direct lookup (host-keyed schema) ─────────────
        # The top-level key in secrets.json IS the host identifier.
        # e.g. { "9.11.68.243": { "ssh": { "username": "root", "password": "..." } } }
        if hostname:
            entry = self._find_by_host(secrets, hostname)
            if entry is not None:
                logger.info(
                    f"Credential resolved by hostname '{hostname}'",
                    extra={"agent": "CredentialResolver"},
                )
                return self._build_result(entry, hostname)

        # ── Step 2: environment variable fallback ─────────────────────────────
        if self._fallback_to_env:
            env_creds = self._resolve_from_env(resource_type, hostname)
            if env_creds:
                logger.info(
                    f"Credential resolved from environment variables for {hostname or 'default'}",
                    extra={"agent": "CredentialResolver"},
                )
                return env_creds

        # ── Step 3: nothing found ─────────────────────────────────────────────
        target = hostname or "unknown"
        raise CredentialNotFoundError(
            f"No credentials found for '{target}'.\n"
            "  Options:\n"
            "    1. Add an entry to config/secrets.json with the host as the key:\n"
            f'       {{ "{target}": {{ "ssh": {{ "username": "root", "password": "..." }} }} }}\n'
            "    2. Set SSH_USER and SSH_PASSWORD environment variables"
        )

    def list_available_credentials(self) -> List[Dict[str, Any]]:
        """
        Return a summary of all credentials in secrets.json.

        Returns:
            List of dicts with keys: credential_id (= host), type, hosts
        """
        secrets = self._backend.load_all()
        result = []
        for host_key, entry in secrets.items():
            cred_type = self._infer_type(entry)
            result.append({
                "credential_id": host_key,
                "type": cred_type,
                "hosts": [host_key],   # host-keyed: the key IS the host
                "tags": [],
            })
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _find_by_host(
        self, secrets: Dict[str, Any], hostname: str
    ) -> Optional[Dict[str, Any]]:
        """
        Look up credentials by hostname/IP.

        In the host-keyed schema the top-level key IS the host identifier,
        so this is a simple case-insensitive dict lookup.

        Args:
            secrets:  Full secrets dict loaded from secrets.json
            hostname: IP address or hostname to look up

        Returns:
            Credential entry dict, or None if not found.
        """
        hostname_lower = hostname.lower()
        for key, entry in secrets.items():
            if key.lower() == hostname_lower:
                return entry
        return None

    def _resolve_from_env(
        self, resource_type: str, hostname: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Build a credential dict from environment variables."""
        # Host-specific prefix: SSH_192_168_1_100_USER
        prefix = f"SSH_{hostname.replace('.', '_').replace('-', '_')}_" if hostname else "SSH_"

        ssh_user = os.getenv(f"{prefix}USER") or os.getenv("SSH_USER")
        ssh_password = os.getenv(f"{prefix}PASSWORD") or os.getenv("SSH_PASSWORD")
        ssh_key_path = os.getenv(f"{prefix}KEY_PATH") or os.getenv("SSH_KEY_PATH")

        if not ssh_user:
            return None

        result: Dict[str, Any] = {
            "credential_id": "env-fallback",
            "ssh": {
                "username": ssh_user,
                "password": ssh_password,
                "key_path": ssh_key_path,
            },
        }

        # Oracle env vars
        oracle_user = os.getenv("ORACLE_USER")
        oracle_password = os.getenv("ORACLE_PASSWORD")
        if oracle_user:
            result["oracle"] = {
                "username": oracle_user,
                "password": oracle_password,
                "service": os.getenv("ORACLE_SERVICE", "ORCL"),
                "port": int(os.getenv("ORACLE_PORT", "1521")),
            }

        # MongoDB env vars
        mongo_user = os.getenv("MONGO_USER")
        mongo_password = os.getenv("MONGO_PASSWORD")
        if mongo_user:
            result["mongo"] = {
                "username": mongo_user,
                "password": mongo_password,
                "auth_db": os.getenv("MONGO_AUTH_DB", "admin"),
                "port": int(os.getenv("MONGO_PORT", "27017")),
            }

        return result

    @staticmethod
    def _build_result(entry: Dict[str, Any], credential_id: str) -> Dict[str, Any]:
        """Normalise a secrets.json entry into the standard result dict."""
        result: Dict[str, Any] = {"credential_id": credential_id}
        for section in ("ssh", "oracle", "mongo"):
            if section in entry:
                result[section] = dict(entry[section])
        return result

    @staticmethod
    def _infer_type(entry: Dict[str, Any]) -> str:
        """Infer a human-readable type label from the sections present."""
        sections = [s for s in ("ssh", "oracle", "mongo") if s in entry]
        return "+".join(sections) if sections else "unknown"


# ── Legacy CredentialManager (env-var based, kept for backward compat) ────────

class CredentialManager:
    """
    Manage credentials from environment variables.

    .. deprecated::
        Use :class:`CredentialResolver` with ``config/secrets.json`` instead.
        This class is kept for backward compatibility only.
    """

    def __init__(self, env_file: Optional[str] = None):
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        self._credentials_cache: Dict[str, Any] = {}

    def get_ssh_credentials(self, host: Optional[str] = None) -> Dict[str, Optional[str]]:
        prefix = f"SSH_{host.replace('.', '_')}_" if host else "SSH_"
        return {
            "ssh_user": os.getenv(f"{prefix}USER") or os.getenv("SSH_USER"),
            "ssh_password": os.getenv(f"{prefix}PASSWORD") or os.getenv("SSH_PASSWORD"),
            "ssh_key_path": os.getenv(f"{prefix}KEY_PATH") or os.getenv("SSH_KEY_PATH"),
        }

    def get_oracle_credentials(self, host: Optional[str] = None) -> Dict[str, Optional[str]]:
        prefix = f"ORACLE_{host.replace('.', '_')}_" if host else "ORACLE_"
        return {
            "db_user": os.getenv(f"{prefix}USER") or os.getenv("ORACLE_USER"),
            "db_password": os.getenv(f"{prefix}PASSWORD") or os.getenv("ORACLE_PASSWORD"),
            "service_name": os.getenv(f"{prefix}SERVICE") or os.getenv("ORACLE_SERVICE"),
            "port": os.getenv(f"{prefix}PORT") or os.getenv("ORACLE_PORT", "1521"),
        }

    def get_mongodb_credentials(self, host: Optional[str] = None) -> Dict[str, Optional[str]]:
        prefix = f"MONGO_{host.replace('.', '_')}_" if host else "MONGO_"
        return {
            "mongo_user": os.getenv(f"{prefix}USER") or os.getenv("MONGO_USER"),
            "mongo_password": os.getenv(f"{prefix}PASSWORD") or os.getenv("MONGO_PASSWORD"),
            "auth_db": os.getenv(f"{prefix}AUTH_DB") or os.getenv("MONGO_AUTH_DB", "admin"),
            "port": os.getenv(f"{prefix}PORT") or os.getenv("MONGO_PORT", "27017"),
        }

    def get_mcp_server_url(self) -> str:
        return os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

    def get_email_config(self) -> Dict[str, Any]:
        use_tls = os.getenv("SMTP_USE_TLS", "false").lower() in ("true", "1", "yes")
        return {
            "recipient": os.getenv("USER_EMAIL"),
            "smtp_server": os.getenv("SMTP_SERVER", "localhost"),
            "smtp_port": os.getenv("SMTP_PORT", "25"),
            "from_address": os.getenv("EMAIL_FROM", "recovery-validation@cyberres.com"),
            "smtp_username": os.getenv("SMTP_USERNAME"),
            "smtp_password": os.getenv("SMTP_PASSWORD"),
            "use_tls": use_tls,
        }

    def has_ssh_credentials(self) -> bool:
        creds = self.get_ssh_credentials()
        return bool(creds["ssh_user"] and (creds["ssh_password"] or creds["ssh_key_path"]))

    def has_oracle_credentials(self) -> bool:
        creds = self.get_oracle_credentials()
        return bool(creds["db_user"] and creds["db_password"])

    def has_mongodb_credentials(self) -> bool:
        creds = self.get_mongodb_credentials()
        return bool(creds["mongo_user"] and creds["mongo_password"])

    def merge_with_user_provided(
        self,
        resource_type: str,
        user_provided: Dict[str, Any],
        host: Optional[str] = None,
    ) -> Dict[str, Any]:
        if resource_type == "vm":
            env_creds = self.get_ssh_credentials(host)
        elif resource_type == "oracle":
            env_creds = self.get_oracle_credentials(host)
        elif resource_type == "mongodb":
            env_creds = self.get_mongodb_credentials(host)
        else:
            return user_provided
        merged = {k: v for k, v in env_creds.items() if v is not None}
        merged.update({k: v for k, v in user_provided.items() if v is not None})
        return merged

    def validate_credentials(self, resource_type: str, credentials: Dict[str, Any]) -> bool:
        if resource_type == "vm":
            return bool(
                credentials.get("ssh_user")
                and (credentials.get("ssh_password") or credentials.get("ssh_key_path"))
            )
        elif resource_type == "oracle":
            return bool(
                credentials.get("db_user")
                and credentials.get("db_password")
                and (credentials.get("dsn") or credentials.get("service_name"))
            )
        elif resource_type == "mongodb":
            return True  # MongoDB can work without credentials for local connections
        return False


# ── Global singleton (legacy) ─────────────────────────────────────────────────

_credential_manager: Optional[CredentialManager] = None


def get_credential_manager(env_file: Optional[str] = None) -> CredentialManager:
    """Get or create global CredentialManager instance (legacy)."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager(env_file)
    return _credential_manager

# Made with Bob
