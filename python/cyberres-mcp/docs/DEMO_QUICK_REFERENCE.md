# Demo Quick Reference - For Claude

## VM Credentials (Pre-Configured)

When the user asks to validate the demo VM, use these credentials from `demo-secrets.json`:

**VM at 9.11.68.67:**
- Username: `defsensor`
- Password: `Lash@78snubflip`

## How to Call Tools

### VM Health Validation
```json
{
  "name": "vm_linux_ssh_validate_health",
  "arguments": {
    "host": "9.11.68.67",
    "username": "defsensor",
    "password": "Lash@78snubflip"
  }
}
```

### Disk Usage
```json
{
  "name": "vm_linux_fs_usage",
  "arguments": {
    "host": "9.11.68.67",
    "username": "defsensor",
    "password": "Lash@78snubflip"
  }
}
```

### Service Check (SSHD)
```json
{
  "name": "vm_linux_services",
  "arguments": {
    "host": "9.11.68.67",
    "username": "defsensor",
    "password": "Lash@78snubflip",
    "required": ["sshd"]
  }
}
```

### Memory and Load
```json
{
  "name": "vm_linux_uptime_load_mem",
  "arguments": {
    "host": "9.11.68.67",
    "username": "defsensor",
    "password": "Lash@78snubflip"
  }
}
```

## User-Friendly Responses

When user asks "validate the demo VM", automatically use the credentials above without asking the user for them.

The credentials are pre-configured in the demo-secrets.json file, so you should use them directly.