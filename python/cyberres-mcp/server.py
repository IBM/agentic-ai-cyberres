from mcp.server.fastmcp import FastMCP
import json
import requests
from typing import List
import paramiko

mcp = FastMCP("Infra_Validator", host="9.11.68.67", port=8000)


@mcp.tool()
def vm_validator(vm_ip: str, ssh_user: str, ssh_password: str) -> dict:
    """
    Args:
        vm_ip: The IP address of the VM to validate.
        ssh_user: SSH username.
        ssh_password: SSH password.

    Returns:
        dict: Validation status, checks, and details.
    """
    checks = []
    details = {}

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=vm_ip, username=ssh_user, password=ssh_password, timeout=10)

        # Disk check
        stdin, stdout, stderr = ssh.exec_command('df -h /')
        disk_output = stdout.read().decode()
        checks.append({"name": "disk_check", "status": "passed" if disk_output else "failed"})
        details["disk_output"] = disk_output

        # Service check
        stdin, stdout, stderr = ssh.exec_command('systemctl is-active sshd')
        service_status = stdout.read().decode().strip()
        checks.append({"name": "sshd_service", "status": "passed" if service_status == "active" else "failed"})
        details["service_status"] = service_status

        ssh.close()
        status = "passed" if all(c["status"] == "passed" for c in checks) else "failed"
    except Exception as e:
        status = "failed"
        details["error"] = str(e)

    return {
        "validation_status": status,
        "checks": checks,
        "details": details
    }



if __name__ == "__main__":
    mcp.run(transport="streamable-http")