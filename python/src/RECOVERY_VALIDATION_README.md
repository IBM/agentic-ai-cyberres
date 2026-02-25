# Recovery Validation Agent

An interactive AI agent for validating recovered infrastructure resources including Linux VMs, Oracle databases, and MongoDB clusters.

## Overview

The Recovery Validation Agent provides an intelligent, conversational interface for validating recovered infrastructure. It uses the Model Context Protocol (MCP) to execute validation checks and generates detailed reports with recommendations.

## Features

- 🤖 **Interactive Conversation**: Natural language interface for gathering resource information
- 🔍 **Auto-Discovery**: Automatically discovers resource details using MCP tools
- 📋 **Smart Planning**: Generates validation plans based on resource type
- ✅ **Comprehensive Validation**: Executes multiple checks against acceptance criteria
- 📊 **Detailed Reporting**: HTML and text reports with metrics and recommendations
- 📧 **Email Delivery**: Sends validation reports via email
- 🔐 **Credential Management**: Supports environment-based and user-provided credentials
- 🎯 **Type-Safe**: Uses Pydantic models for data validation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface                            │
│                  (Interactive Console)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              RecoveryValidationAgent                         │
│  (Main Orchestrator - recovery_validation_agent.py)         │
└─┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────┘
  │      │      │      │      │      │      │      │
  ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐
│Con│  │Cre│  │MCP│  │Dis│  │Pla│  │Exe│  │Eva│  │Rep│
│ver│  │den│  │Cli│  │cov│  │nne│  │cut│  │lua│  │ort│
│sat│  │tia│  │ent│  │ery│  │r  │  │or │  │tor│  │Gen│
│ion│  │ls │  │   │  │   │  │   │  │   │  │   │  │   │
└───┘  └───┘  └───┘  └───┘  └───┘  └───┘  └───┘  └───┘
                 │
                 ▼
        ┌────────────────┐
        │  MCP Server    │
        │ (cyberres-mcp) │
        └────────────────┘
```

## Components

### Core Modules

1. **models.py** - Pydantic models for type-safe data structures
   - `ResourceType`, `ValidationStatus` enums
   - `VMResourceInfo`, `OracleDBResourceInfo`, `MongoDBResourceInfo`
   - `ValidationRequest`, `ValidationReport`, `CheckResult`

2. **conversation.py** - Interactive conversation handler
   - Uses PydanticAI to extract structured data from natural language
   - Guides users through information gathering
   - Validates completeness of collected information

3. **credentials.py** - Credential management
   - Loads credentials from environment variables
   - Supports host-specific credentials
   - Merges environment and user-provided credentials

4. **mcp_client.py** - MCP client integration
   - Connects to cyberres-mcp server
   - Provides typed interfaces to MCP tools
   - Handles errors and retries

5. **discovery.py** - Resource auto-discovery
   - Discovers VM details (OS, services, connectivity)
   - Discovers Oracle instances (listeners, services, SIDs)
   - Discovers MongoDB clusters (version, replica sets)

6. **planner.py** - Validation plan generation
   - Creates ordered validation steps based on resource type
   - Follows best practices from planner.md prompt
   - Configures tool parameters

7. **executor.py** - Validation execution
   - Executes validation plans step-by-step
   - Collects results and timing information
   - Handles failures gracefully

8. **evaluator.py** - Result evaluation
   - Loads acceptance criteria from JSON files
   - Evaluates results against thresholds
   - Calculates scores and overall status

9. **report_generator.py** - Report generation
   - Generates HTML reports with styling
   - Creates plain text reports
   - Generates actionable recommendations

10. **email_service.py** - Email delivery
    - Sends HTML and text email reports
    - Configurable SMTP settings
    - Handles delivery errors

11. **recovery_validation_agent.py** - Main orchestrator
    - Coordinates all components
    - Manages workflow execution
    - Provides progress feedback

## Installation

```bash
cd python/src
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the `python/src` directory:

```bash
# MCP Server
MCP_SERVER_URL=http://localhost:8000/mcp

# SSH Credentials (optional)
SSH_USER=admin
SSH_PASSWORD=
SSH_KEY_PATH=/path/to/key.pem

# Oracle Credentials (optional)
ORACLE_USER=system
ORACLE_PASSWORD=oracle_password
ORACLE_SERVICE=ORCL
ORACLE_PORT=1521

# MongoDB Credentials (optional)
MONGO_USER=admin
MONGO_PASSWORD=mongo_password
MONGO_AUTH_DB=admin
MONGO_PORT=27017

# Email Configuration
USER_EMAIL=admin@example.com
SMTP_SERVER=localhost
SMTP_PORT=25
EMAIL_FROM=recovery-validation@cyberres.com

# LLM Configuration
LLM_BACKEND=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
```

## Usage

### Interactive Mode

```bash
python main.py
```

The agent will guide you through:
1. Specifying the resource type (VM, Oracle, MongoDB)
2. Providing the host/IP address
3. Entering credentials (or using environment variables)
4. Auto-discovering resource details
5. Executing validation checks
6. Receiving a detailed report via email

### Example Conversation

```
Agent 🤖: Welcome to the Recovery Validation Agent!

I'll help you validate your recovered infrastructure resources...

User: I recovered a VM at 192.168.1.100

Agent 🤖: Great! I'll help you validate a VM at 192.168.1.100.

Now I need some additional information:
- What is the SSH username for this VM?
- Do you have an SSH password or key file?
- Are there any specific services that must be running?

User: SSH user is admin, password is in environment, check for sshd and httpd services

Agent 🤖: Perfect! I have all the information I need.

I will now:
1. Auto-discover resource details
2. Generate a validation plan
3. Execute validation checks
4. Evaluate results
5. Send a detailed report to admin@example.com

Starting validation...

Agent 🤖: Connecting to MCP server at http://localhost:8000/mcp...
Agent 🤖: ✓ Connected to MCP server
Agent 🤖: 🔍 Discovering VM details...
Agent 🤖: ✓ Discovery completed successfully
Agent 🤖: 📋 Generating validation plan...
Agent 🤖: ✓ Validation plan created with 4 steps
Agent 🤖: 🔧 Executing validation (4 checks)...
Agent 🤖: ✓ Validation completed: 4/4 checks passed
Agent 🤖: 📊 Evaluating results against acceptance criteria...
Agent 🤖: ✓ Evaluation complete: PASS (Score: 100/100)
Agent 🤖: 💡 Generating recommendations...
Agent 🤖: ✓ Generated 0 recommendations
Agent 🤖: 📧 Sending report to admin@example.com...
Agent 🤖: ✓ Email report sent successfully

============================================================
VALIDATION SUMMARY
============================================================
Resource Type: VM
Host: 192.168.1.100
Status: PASS
Validation Score: 100/100
Checks: 4 passed, 0 failed, 0 warnings
Execution Time: 12.34s
============================================================

✓ Total execution time: 12.45 seconds
```

## Validation Checks

### VM Validation
- ✅ SSH port connectivity (port 22)
- ✅ Uptime, load averages, and memory usage
- ✅ Filesystem usage for all mounted filesystems
- ✅ Required services status

### Oracle Database Validation
- ✅ Oracle port connectivity (port 1521)
- ✅ Database connection and instance info
- ✅ Tablespace usage and free space

### MongoDB Validation
- ✅ MongoDB port connectivity (port 27017)
- ✅ Database connection and version
- ✅ Replica set status (if applicable)
- ✅ Collection validation (if specified)

## Acceptance Criteria

Acceptance criteria are defined in JSON files:
- `python/cyberres-mcp/resources/acceptance/vm-core.json`
- `python/cyberres-mcp/resources/acceptance/db-oracle.json`
- `python/cyberres-mcp/resources/acceptance/db-mongo.json`

Example (vm-core.json):
```json
{
  "fs_max_pct": 85,
  "mem_min_free_pct": 10,
  "required_services": []
}
```

## Email Reports

Reports include:
- 📊 Executive summary with overall status and score
- 📈 Detailed metrics for each check
- ✅ Pass/fail status with expected vs actual values
- 💡 Actionable recommendations
- 🔍 Discovery information
- ⏱️ Execution timing

## Logging

Logs are written to:
- Console (INFO level)
- `recovery_validation.log` file (INFO level)

## Error Handling

The agent handles:
- ❌ MCP server connection failures
- ❌ SSH/database authentication errors
- ❌ Network connectivity issues
- ❌ Missing credentials
- ❌ Invalid user input
- ❌ Tool execution failures

All errors are logged and reported to the user with helpful messages.

## Extending the Agent

### Adding a New Resource Type

1. Add enum value to `ResourceType` in `models.py`
2. Create resource info model (e.g., `PostgreSQLResourceInfo`)
3. Add discovery logic in `discovery.py`
4. Add planning logic in `planner.py`
5. Add evaluation logic in `evaluator.py`
6. Create acceptance criteria JSON file

### Adding a New Validation Check

1. Add MCP tool wrapper in `mcp_client.py` (if needed)
2. Add step to validation plan in `planner.py`
3. Add evaluation logic in `evaluator.py`
4. Update acceptance criteria JSON

## Troubleshooting

### MCP Server Connection Failed
- Ensure cyberres-mcp server is running
- Check `MCP_SERVER_URL` in `.env`
- Verify network connectivity

### SSH Authentication Failed
- Verify credentials in `.env` or user input
- Check SSH key file permissions (should be 600)
- Ensure SSH service is running on target

### Email Not Sent
- Check SMTP server configuration
- Verify `USER_EMAIL` is set
- Check firewall rules for SMTP port

## Development

### Running Tests
```bash
pytest python/src/tests/
```

### Code Style
```bash
black python/src/
pylint python/src/
```

## License

Copyright contributors to the agentic-ai-cyberres project