
"""
Copyright contributors to the agentic-ai-cyberres project
"""

from typing import List, Optional, Dict, Any
from paramiko import SSHClient, AutoAddPolicy
import paramiko
import logging

def _ssh_exec(host: str,
              username: str,
              password: Optional[str] = None,
              key_path: Optional[str] = None,
              cmd: str = "echo ok",
              port: int = 22,
              timeout: float = 5.0) -> tuple[int, str, str]:
    """Execute a command over SSH and return exit code, stdout, stderr."""
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        if key_path:
            key = paramiko.RSAKey.from_private_key_file(key_path)
            client.connect(hostname=host, port=port, username=username, pkey=key, timeout=timeout)
        else:
            client.connect(hostname=host, port=port, username=username, password=password, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        rc = stdout.channel.recv_exit_status()
        return rc, out, err
    finally:
        try:
            client.close()
        except Exception:
            pass


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
        from .utils import ok, err
    except Exception:
        from plugins.utils import ok, err  # type: ignore

    @mcp.tool()
    def vm_linux_uptime_load_mem(host: str, username: str, password: Optional[str] = None, key_path: Optional[str] = None) -> Dict[str, Any]:
        """Return uptime, load averages, and memory information from a Linux host."""
        cmd = "uptime && cat /proc/meminfo | egrep 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree'"
        rc, out, serr = _ssh_exec(host, username, password=password, key_path=key_path, cmd=cmd)
        if rc != 0:
            logger.warning("uptime_load_mem failed", extra={"host": host, "rc": rc})
        return ok({"rc": rc, "stdout": out, "stderr": serr}) if rc == 0 else err("ssh exec failed", code="SSH_ERROR", rc=rc, stdout=out, stderr=serr)

    @mcp.tool()
    def vm_linux_fs_usage(host: str, username: str, password: Optional[str] = None, key_path: Optional[str] = None) -> Dict[str, Any]:
        """Return POSIX filesystem usage statistics."""
        rc, out, serr = _ssh_exec(host, username, password=password, key_path=key_path, cmd="df -P -k")
        parsed = _parse_df_posix(out) if rc == 0 else []
        if rc != 0:
            logger.warning("fs_usage failed", extra={"host": host, "rc": rc})
        return ok({"rc": rc, "filesystems": parsed, "stderr": serr}) if rc == 0 else err("ssh exec failed", code="SSH_ERROR", rc=rc, stderr=serr)

    @mcp.tool()
    def vm_linux_services(host: str, username: str, password: Optional[str] = None, key_path: Optional[str] = None, required: Optional[List[str]] = None) -> Dict[str, Any]:
        """List running systemd services and verify required ones are active."""
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
    def vm_validator(vm_ip: str, ssh_user: str, ssh_password: str) -> Dict[str, Any]:
        """Backwards compatible wrapper replicating the original vm_validator.

        This tool remains for compatibility with existing clients. It performs
        a root filesystem ``df`` check and verifies that ``sshd`` is active.
        """
        disk_rc, disk_out, disk_err = _ssh_exec(vm_ip, ssh_user, password=ssh_password, cmd="df -h /")
        svc_rc, svc_out, svc_err = _ssh_exec(vm_ip, ssh_user, password=ssh_password, cmd="systemctl is-active sshd || true")
        status = "PASS" if disk_rc == 0 and "active" in svc_out else "FAIL"
        return ok({
            "validation_status": status,
            "checks": [
                {"id": "disk_root_df", "rc": disk_rc, "stdout": disk_out, "stderr": disk_err},
                {"id": "svc_sshd_active", "rc": svc_rc, "stdout": svc_out.strip(), "stderr": svc_err},
            ],
            "details": {"vm_ip": vm_ip},
        }) if status == "PASS" else err("vm validation failed", code="VM_VALIDATE_FAILED", validation_status=status, details={"vm_ip": vm_ip})

