"""
Copyright contributors to the agentic-ai-cyberres project
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
import json
import logging
import os
from pathlib import Path


def ok(data: Optional[Dict[str, Any]] = None, **extra: Any) -> Dict[str, Any]:
    resp: Dict[str, Any] = {"ok": True}
    if data:
        resp.update(data)
    if extra:
        resp.update(extra)
    return resp


def err(message: str, *, code: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    resp: Dict[str, Any] = {"ok": False, "error": {"message": message}}
    if code:
        resp["error"]["code"] = code
    if extra:
        resp.update(extra)
    return resp


def load_secrets_data(logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """Load configured secrets JSON and return as dict."""
    try:
        from ..settings import SETTINGS
    except Exception:
        try:
            from cyberres_mcp.settings import SETTINGS  # type: ignore
        except Exception:
            return {}

    configured = Path(SETTINGS.secrets_file)
    package_dir = Path(__file__).resolve().parents[1]  # .../src/cyberres_mcp
    project_dir = Path(__file__).resolve().parents[3]  # .../python/cyberres-mcp

    candidates: List[Path] = []
    if configured.is_absolute():
        candidates.append(configured)
    else:
        candidates.extend(
            [
                package_dir / configured,  # package-relative
                project_dir / configured,  # project root
                Path.cwd() / configured,   # process cwd
                Path.cwd() / "python" / "cyberres-mcp" / configured,  # repo root cwd
            ]
        )
        # Walk up from CWD to handle varied launch directories (Claude Desktop / uv)
        for parent in [Path.cwd(), *Path.cwd().parents]:
            candidates.append(parent / configured)
            candidates.append(parent / "python" / "cyberres-mcp" / configured)

    seen = set()
    tried_paths: List[str] = []
    for path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        tried_paths.append(key)
        if not resolved.exists():
            continue
        try:
            with open(resolved, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except Exception as ex:
            if logger:
                logger.warning("failed to load secrets file", extra={"path": str(resolved), "error": str(ex)})

    if logger:
        logger.info("no secrets file found in candidate paths", extra={"candidates": tried_paths[:10], "candidate_count": len(tried_paths)})
    return {}


def get_credential_entry(
    credential_id: Optional[str],
    logger: Optional[logging.Logger] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return credential entry by id and optional error message."""
    if not credential_id:
        return None, "credential_id is required when password/key is not provided"

    secrets = load_secrets_data(logger=logger)
    entry = secrets.get(credential_id)
    if not isinstance(entry, dict):
        return None, f"credential_id '{credential_id}' not found in secrets file"
    return entry, None


def resolve_ssh_auth(
    ssh_user: Optional[str],
    ssh_password: Optional[str],
    ssh_key_path: Optional[str],
    credential_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Resolve SSH auth from direct inputs first, then credential_id.

    Returns: (ssh_user, ssh_password, ssh_key_path, error_message)
    """
    resolved_user = ssh_user
    resolved_password = ssh_password
    resolved_key_path = ssh_key_path

    if (resolved_password or resolved_key_path) and resolved_user:
        return resolved_user, resolved_password, resolved_key_path, None

    if credential_id:
        entry, cred_err = get_credential_entry(credential_id, logger=logger)
        if cred_err:
            return resolved_user, resolved_password, resolved_key_path, cred_err
        scope = entry.get("ssh") if isinstance(entry.get("ssh"), dict) else entry
        entry_user = scope.get("username") or scope.get("user") or scope.get("ssh_user")
        entry_password = scope.get("password") or scope.get("ssh_password")
        entry_key_path = scope.get("key_path") or scope.get("ssh_key_path")

        if not resolved_user and entry_user:
            resolved_user = entry_user
        if not resolved_password and entry_password:
            resolved_password = entry_password
        if not resolved_key_path and entry_key_path:
            resolved_key_path = entry_key_path

    if not resolved_user:
        return resolved_user, resolved_password, resolved_key_path, "ssh_user (or credential entry username) is required"
    if not resolved_password and not resolved_key_path:
        return (
            resolved_user,
            resolved_password,
            resolved_key_path,
            "Provide ssh_password or ssh_key_path, or set credential_id",
        )
    return resolved_user, resolved_password, resolved_key_path, None


def resolve_scoped_auth(
    username: Optional[str],
    password: Optional[str],
    credential_id: Optional[str],
    *,
    scope_name: str,
    user_keys: Optional[List[str]] = None,
    password_keys: Optional[List[str]] = None,
    logger: Optional[logging.Logger] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolve username/password from direct inputs first, then credential_id scope.

    Returns: (username, password, error_message)
    """
    resolved_user = username
    resolved_password = password
    if resolved_user and resolved_password:
        return resolved_user, resolved_password, None

    if not credential_id:
        if resolved_user and not resolved_password:
            return resolved_user, resolved_password, f"{scope_name} password is required"
        return resolved_user, resolved_password, None

    entry, cred_err = get_credential_entry(credential_id, logger=logger)
    if cred_err:
        return resolved_user, resolved_password, cred_err

    scope = entry.get(scope_name) if isinstance(entry.get(scope_name), dict) else entry
    u_keys = user_keys or ["username", "user", f"{scope_name}_user"]
    p_keys = password_keys or ["password", f"{scope_name}_password"]

    for key in u_keys:
        val = scope.get(key)
        if val and not resolved_user:
            resolved_user = val
            break
    for key in p_keys:
        val = scope.get(key)
        if val and not resolved_password:
            resolved_password = val
            break

    if resolved_user and not resolved_password:
        return resolved_user, resolved_password, f"credential_id '{credential_id}' does not contain {scope_name} password"
    return resolved_user, resolved_password, None


def resolve_scoped_value(
    value: Optional[str],
    credential_id: Optional[str],
    *,
    scope_name: str,
    keys: List[str],
    logger: Optional[logging.Logger] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a single scoped value from direct input, then credential entry."""
    if value:
        return value, None
    if not credential_id:
        return value, None

    entry, cred_err = get_credential_entry(credential_id, logger=logger)
    if cred_err:
        return value, cred_err
    scope = entry.get(scope_name) if isinstance(entry.get(scope_name), dict) else entry
    for key in keys:
        val = scope.get(key)
        if val:
            return str(val), None
    return value, None
