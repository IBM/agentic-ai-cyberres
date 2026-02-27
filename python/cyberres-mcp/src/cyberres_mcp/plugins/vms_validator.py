
"""
Copyright contributors to the agentic-ai-cyberres project
"""

from typing import List, Optional, Dict, Any
import logging

# Use unified SSH utilities
from .ssh_utils import ssh_exec as _ssh_exec_impl

def _ssh_exec(host: str,
              username: str,
              password: Optional[str] = None,
              key_path: Optional[str] = None,
              cmd: str = "echo ok",
              port: int = 22,
              timeout: float = 5.0) -> tuple[int, str, str]:
    """
    Execute a command over SSH and return exit code, stdout, stderr.
    
    This is a backward-compatible wrapper around ssh_utils.ssh_exec.
    """
    return _ssh_exec_impl(host, username, cmd, password, key_path, port, timeout)


def _parse_df_posix(df_output: str) -> List[Dict[str, Any]]:
    """Parse POSIX ``df -P -k`` output into a list of dicts."""
    lines = [l for l in df_output.strip().splitlines() if l.strip()]
    if not lines:
        return []
    results = []
    # Skip the header line
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        fs, blocks, used, avail, usep, mnt = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        try:
            pct = int(usep.strip('%'))
        except Exception:
            pct = None
        try:
            blocks_k = int(blocks)
            used_k = int(used)
            avail_k = int(avail)
        except Exception:
            blocks_k = used_k = avail_k = None
        results.append({
            "filesystem": fs,
            "blocks_k": blocks_k,
            "used_k": used_k,
            "avail_k": avail_k,
            "use_pct": pct,
            "mountpoint": mnt,
        })
    return results


def attach(mcp):
    """Register VM-related tools on the given FastMCP instance."""
    logger = logging.getLogger("mcp.vm")
    try:
        from .utils import ok, err, resolve_ssh_auth
    except Exception:
        from plugins.utils import ok, err, resolve_ssh_auth  # type: ignore

    @mcp.tool()
    def vm_linux_uptime_load_mem(
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[VM][SSH] Collect Linux uptime, load averages, and memory/swap metrics."""
        username, password, key_path, auth_err = resolve_ssh_auth(
            ssh_user=username,
            ssh_password=password,
            ssh_key_path=key_path,
            credential_id=credential_id,
            logger=logger,
        )
        if auth_err:
            return err(auth_err, code="INPUT_ERROR")
        cmd = "uptime && cat /proc/meminfo | egrep 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree'"
        rc, out, serr = _ssh_exec(host, username, password=password, key_path=key_path, cmd=cmd)
        if rc != 0:
            logger.warning("uptime_load_mem failed", extra={"host": host, "rc": rc})
        return ok({"rc": rc, "stdout": out, "stderr": serr}) if rc == 0 else err("ssh exec failed", code="SSH_ERROR", rc=rc, stdout=out, stderr=serr)

    @mcp.tool()
    def vm_linux_fs_usage(
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[VM][SSH] Collect filesystem usage from ``df -P -k``."""
        username, password, key_path, auth_err = resolve_ssh_auth(
            ssh_user=username,
            ssh_password=password,
            ssh_key_path=key_path,
            credential_id=credential_id,
            logger=logger,
        )
        if auth_err:
            return err(auth_err, code="INPUT_ERROR")
        rc, out, serr = _ssh_exec(host, username, password=password, key_path=key_path, cmd="df -P -k")
        parsed = _parse_df_posix(out) if rc == 0 else []
        if rc != 0:
            logger.warning("fs_usage failed", extra={"host": host, "rc": rc})
        return ok({"rc": rc, "filesystems": parsed, "stderr": serr}) if rc == 0 else err("ssh exec failed", code="SSH_ERROR", rc=rc, stderr=serr)

    @mcp.tool()
    def vm_linux_services(
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        required: Optional[List[str]] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[VM][SSH] Check running systemd services and validate required services."""
        username, password, key_path, auth_err = resolve_ssh_auth(
            ssh_user=username,
            ssh_password=password,
            ssh_key_path=key_path,
            credential_id=credential_id,
            logger=logger,
        )
        if auth_err:
            return err(auth_err, code="INPUT_ERROR")
        cmd = "systemctl list-units --type=service --state=running --no-legend --no-pager | awk '{print $1}'"
        rc, out, serr = _ssh_exec(host, username, password=password, key_path=key_path, cmd=cmd)
        running = [ln.strip() for ln in out.splitlines() if ln.strip()]
        required = required or []
        missing = [svc for svc in required if svc not in running]
        if rc != 0 or missing:
            logger.info("services check issues", extra={"host": host, "rc": rc, "missing": missing})
        payload = {"rc": rc, "running": running, "required": required, "missing": missing, "stderr": serr}
        return ok(payload) if rc == 0 and not missing else err("service(s) missing or ssh error", code="SERVICE_CHECK_FAILED" if not rc else "SSH_ERROR", **payload)

    @mcp.tool()
    def vm_validator(
        vm_ip: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[VM][SSH][Legacy] Run legacy VM readiness checks (root disk and sshd).

        This tool remains for compatibility with existing clients. It performs
        a root filesystem ``df`` check and verifies that ``sshd`` is active.
        """
        ssh_user, ssh_password, ssh_key_path, auth_err = resolve_ssh_auth(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
            logger=logger,
        )
        if auth_err:
            return err(auth_err, code="INPUT_ERROR")

        disk_rc, disk_out, disk_err = _ssh_exec(vm_ip, ssh_user, password=ssh_password, key_path=ssh_key_path, cmd="df -h /")
        svc_rc, svc_out, svc_err = _ssh_exec(vm_ip, ssh_user, password=ssh_password, key_path=ssh_key_path, cmd="systemctl is-active sshd || true")
        status = "PASS" if disk_rc == 0 and "active" in svc_out else "FAIL"
        return ok({
            "validation_status": status,
            "checks": [
                {"id": "disk_root_df", "rc": disk_rc, "stdout": disk_out, "stderr": disk_err},
                {"id": "svc_sshd_active", "rc": svc_rc, "stdout": svc_out.strip(), "stderr": svc_err},
            ],
            "details": {"vm_ip": vm_ip},
        }) if status == "PASS" else err("vm validation failed", code="VM_VALIDATE_FAILED", validation_status=status, details={"vm_ip": vm_ip})
