# Helpers - Data Validator Tools

This folder contains Python helper modules for system validation tools, primarily implemented in `data_validator_tools.py`. These tools perform system checks such as process inspection, MongoDB validation, email sending, and port scanning.

## Tools Overview

- **FindRunningProcessesTool**: Determines what applications are running on the system by inspecting running processes, excluding typical Linux system processes.
- **MongoDBDataValidatorTool**: Validates a MongoDB database to ensure it is not corrupted. Requires MongoDB to be running.
- **SendEmailTool**: Sends an email using the system's `sendmail` command. Requires the `USER_EMAIL` environment variable to be set.
- **FindWhatsRunningByPortsTool**: Determines what applications are running by inspecting open listening ports.


## Requirements

- Python 3.x
create a virtual environment, run the following commands:

```
cd python/src
python3 -m venv venv
. venv/bin/activate
```


Install the relevant requirements:

```
pip3 install -r requirements.txt
```


Execution:
Run python3 main.py
