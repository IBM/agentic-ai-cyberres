# Helpers - Data Validator Tools

This folder contains Python helper modules for system validation tools, primarily implemented in `data_validator_tools.py`. These tools perform system checks such as process inspection, MongoDB validation, email sending, and port scanning.

## Tools Overview

- **FindRunningProcessesTool**: Determines what applications are running on the system by inspecting running processes, excluding typical Linux system processes.
- **MongoDBDataValidatorTool**: Validates a MongoDB database to ensure it is not corrupted. Requires MongoDB to be running.
- **SendEmailTool**: Sends an email using the system's `sendmail` command. Requires the `USER_EMAIL` environment variable to be set.
- **FindWhatsRunningByPortsTool**: Determines what applications are running by inspecting open listening ports.


## Requirements

- Python 3.x
- System commands: `ps`, `mongosh`, `sendmail`, `netstat` (must be installed and available in PATH)
- Environment variable `USER_EMAIL` set for `SendEmailTool`
- Run agent.py to execute the functionality

## Notes

- The tools use Python's `subprocess` module to execute system commands.
- Error handling is included for command execution failures.
- The MongoDB validator requires the `mongosh` shell and a JavaScript validation script at `src/helpers/mongoDBDataValidator.js`.

## License

This code is part of the agentic-ai-cyberres project and is subject to its license.
