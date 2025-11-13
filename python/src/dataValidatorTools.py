#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
import subprocess
import re
from typing import Dict, Any
from agent import DynamicTool, StringToolOutput, SafetyViolationError

class ExecutionGuardrails:
    @staticmethod
    def validate_command(command: str) -> None:
        """Validate shell commands for safety"""
        dangerous_commands = [
            'rm', 'chmod', 'chown', 'chgrp', 'dd', 'mkfs', 'fdisk',
            'shutdown', 'reboot', 'halt', 'poweroff', 'init', 'kill',
            'pkill', 'killall', 'useradd', 'userdel', 'groupadd',
            'visudo', 'passwd', 'crontab', 'iptables', 'ufw'
        ]
        
        blocked_patterns = [
            r'rm\s+.*-r.*-f', r'chmod\s+[0-7][0-7][0-7]', 
            r'>\s+/dev/', r'|\s*sh', r'|\s*bash',
            r'curl\s.*\|', r'wget\s.*\|', r'\.\/.*',
            r'/etc/passwd', r'/etc/shadow', r'/root',
            r'~/.ssh', r'*.pem', r'*.key'
        ]
        
        # Check for dangerous commands
        for cmd in dangerous_commands:
            if command.strip().startswith(cmd + ' ') or command == cmd:
                raise SafetyViolationError(f"Dangerous command blocked: {cmd}")
        
        # Check for dangerous patterns
        for pattern in blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise SafetyViolationError(f"Dangerous pattern blocked: {pattern}")
    
    @staticmethod
    def safe_shell_execute(command: str, input_data: str = None, timeout: int = 30) -> str:
        """Safely execute shell commands with validation and timeouts"""
        ExecutionGuardrails.validate_command(command)
        
        try:
            result = subprocess.run(
                command.split(),
                input=input_data,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise SafetyViolationError(f"Command timed out: {command}")
        except subprocess.CalledProcessError as e:
            return f"Command failed: {e.stderr}"

async def find_running_processes_handler(input_data: Dict[str, Any]) -> str:
    min_val = input_data.get("min", 0)
    
    try:
        result = ExecutionGuardrails.safe_shell_execute(
            "ps --ppid 2 -p 2 --deselect"
        )
        print(f"stdout: {result}")
        return result
    except SafetyViolationError as e:
        return f"Security violation: {str(e)}"
    except Exception as error:
        print(f"Error: {error}")
        return f"Execution Failed. Details:\n{str(error)}"

async def mongodb_data_validator_handler(input_data: Dict[str, Any]) -> str:
    argument = input_data.get("argument", "")
    workload_to_validate = "mongodb"
    
    print(f"argument: {argument}")
    
    if argument != workload_to_validate:
        print(f"{argument} is not a MongoDB workload. This tool cannot be used to validate {argument}")
        return f"Validation Failed. Reason: {argument} cannot be used to validate {workload_to_validate}"
    else:
        print(f"Validating MongoDB workload: {argument}")
        
        try:
            result = ExecutionGuardrails.safe_shell_execute(
                "mongosh --file scripts/mongoDBValidator.js"
            )
            print(f"stdout: {result}")
            return result
        except SafetyViolationError as e:
            return f"Security violation: {str(e)}"
        except Exception as error:
            print(f"Error: {error}")
            return f"Validation Failed. Details:\n{str(error)}"

async def send_email_handler(input_data: Dict[str, Any]) -> str:
    argument = input_data.get("argument", "")
    email = os.getenv("USER_EMAIL")
    
    if not email:
        return "Error: USER_EMAIL environment variable not set"
    
    if len(argument) > 10000:
        return "Error: Email content too large (max 10,000 characters)"
    
    sanitized_content = re.sub(r'[<>|&;`$]', '', argument[:10000])
    
    email_content = f"""Subject: Data Validation

{sanitized_content}
."""
    
    try:
        result = ExecutionGuardrails.safe_shell_execute(
            f"sendmail -t {email}",
            input_data=email_content,
            timeout=60
        )
        print(f"stdout: {result}")
        return result
    except SafetyViolationError as e:
        return f"Security violation: {str(e)}"
    except Exception as error:
        print(f"Error: {error}")
        return f"Email Failed. Details:\n{str(error)}"

async def find_whats_running_by_ports_handler(input_data: Dict[str, Any]) -> str:
    min_val = input_data.get("min", 0)
    max_val = input_data.get("max", 65535)
    
    try:
        result = ExecutionGuardrails.safe_shell_execute("netstat -al")
        print(f"stdout: {result}")
        return result
    except SafetyViolationError as e:
        return f"Security violation: {str(e)}"
    except Exception as error:
        print(f"Error: {error}")
        return f"Execution Failed. Details:\n{str(error)}"

# Create tool instances for export
FindRunningProcessesTool = DynamicTool(
    name="FindRunningProcesses",
    description="Determine what applications are running on the system by looking at running processes. Disregard processes that are used by typical Linux system processes",
    handler=find_running_processes_handler
)

MongoDBDataValidatorTool = DynamicTool(
    name="MongoDBDataValidator",
    description="This tool validates a MongoDB database to ensure the database is not corrupted. Do not use this tool to validate anything that is not MongoDB. It can only be used if MongoDB is currently running.",
    handler=mongodb_data_validator_handler
)

SendEmailTool = DynamicTool(
    name="SendEmail",
    description="Send an email.",
    handler=send_email_handler
)

FindWhatsRunningByPortsTool = DynamicTool(
    name="FindWhatsRunningByPorts",
    description="Determine what applications are running on the system by looking at open listening ports. Disregard ports that are used by typical Linux system processes.",
    handler=find_whats_running_by_ports_handler
)

# Export the tools
__all__ = [
    'FindRunningProcessesTool',
    'MongoDBDataValidatorTool', 
    'SendEmailTool',
    'FindWhatsRunningByPortsTool',
    'ExecutionGuardrails'
]