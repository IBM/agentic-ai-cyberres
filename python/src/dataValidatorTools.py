#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
import subprocess
from typing import Dict, Any
from agent import DynamicTool, StringToolOutput

async def find_running_processes_handler(input_data: Dict[str, Any]) -> str:
    min_val = input_data.get("min", 0)
    
    try:
        result = subprocess.run(
            ["ps", "--ppid", "2", "-p", "2", "--deselect"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"stdout: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as error:
        print(f"Error: {error}")
        if error.stderr:
            print(f"stderr: {error.stderr}")
        return f"Validation Failed. Details:\n{error.stderr}"

FindRunningProcessesTool = DynamicTool(
    name="FindRunningProcesses",
    description="Determine what applications are running on the system by looking at running processes. Disregard processes that are used by typical Linux system processes",
    handler=find_running_processes_handler
)

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
            result = subprocess.run(
                ["mongosh", "--file", "scripts/mongoDBValidator.js"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"stdout: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as error:
            print(f"Error: {error}")
            if error.stderr:
                print(f"stderr: {error.stderr}")
            return f"Validation Failed. Details:\n{error.stderr}"

MongoDBDataValidatorTool = DynamicTool(
    name="MongoDBDataValidator",
    description="This tool validates a MongoDB database to ensure the database is not corrupted. Do not use this tool to validate anything that is not MongoDB. It can only be used if MongoDB is currently running.",
    handler=mongodb_data_validator_handler
)

async def send_email_handler(input_data: Dict[str, Any]) -> str:
    argument = input_data.get("argument", "")
    email = os.getenv("USER_EMAIL")
    
    if not email:
        return "Error: USER_EMAIL environment variable not set"
    
    email_content = f"""Subject: Data Validation

{argument}
."""
    
    try:
        result = subprocess.run(
            ["sendmail", "-t", email],
            input=email_content,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"stdout: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as error:
        print(f"Error: {error}")
        if error.stderr:
            print(f"stderr: {error.stderr}")
        return f"Validation Failed. Details:\n{error.stderr}"

SendEmailTool = DynamicTool(
    name="SendEmail",
    description="Send an email.",
    handler=send_email_handler
)

async def find_whats_running_by_ports_handler(input_data: Dict[str, Any]) -> str:
    min_val = input_data.get("min", 0)
    max_val = input_data.get("max", 65535)
    
    try:
        result = subprocess.run(
            ["netstat", "-al"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"stdout: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as error:
        print(f"Error: {error}")
        if error.stderr:
            print(f"stderr: {error.stderr}")
        return f"Validation Failed. Details:\n{error.stderr}"

FindWhatsRunningByPortsTool = DynamicTool(
    name="FindWhatsRunningByPorts",
    description="Determine what applications are running on the system by looking at open listening ports. Disregard ports that are used by typical Linux system processes.",
    handler=find_whats_running_by_ports_handler
)