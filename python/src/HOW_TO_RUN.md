# 🚀 How to Run the Agentic Workflow

## You Already Have It! Just Run main.py

The agentic workflow is **already built and ready to use**. You don't need any new scripts!

---

## Quick Start (2 Steps)

### Step 1: Start MCP Server (Terminal 1)

```bash
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

Keep this running.

### Step 2: Start the Agent (Terminal 2)

```bash
cd python/src
python main.py
```

**That's it!** The agent will start and ask you for prompts.

---

## What You'll See

### Welcome Screen

```
================================================================================
  🔍 RECOVERY VALIDATION AGENT
  Validate recovered infrastructure resources
================================================================================

Agent 🤖: Hello! I'm your recovery validation assistant.

I can help you validate recovered infrastructure resources including:
- Virtual Machines (VMs)
- Oracle Databases
- MongoDB Databases

Please describe what you'd like to validate. For example:
- "I want to validate a VM at 192.168.1.100"
- "Validate Oracle database at db-server-01"
- "Check MongoDB at mongo-cluster-01"

What would you like to validate?
```

### Enter Your Prompt

```
You 👤: Validate the Oracle database at db-server-01
```

### Agent Responds

```
Agent 🤖: Great! I'll help you validate an ORACLE_DB at db-server-01.

Now I need some additional information:
- Oracle service name (e.g., ORCL)
- Database username
- Port (default: 1521)

Please provide these details.
```

### Continue the Conversation

```
You 👤: Service name is ORCL, username is system, port 1521

Agent 🤖: Perfect! I have all the information I need.

Starting validation workflow...

[The agent will automatically:]
1. Discover workload (scan ports, processes, applications)
2. Classify the resource
3. Plan validation checks
4. Execute validations using MCP tools
5. Evaluate results with AI
6. Generate professional report

[Results will be displayed and saved]
```

---

## Example Prompts

### Oracle Database

```
You 👤: Validate the Oracle database at db-server-01
Agent 🤖: [asks for service name, username, port]
You 👤: Service name ORCL, username system, port 1521
Agent 🤖: [runs complete workflow]
```

### MongoDB

```
You 👤: Check MongoDB at mongo-cluster-01
Agent 🤖: [asks for database name, username, port]
You 👤: Database admin, username admin, port 27017
Agent 🤖: [runs complete workflow]
```

### Virtual Machine

```
You 👤: Validate VM at 192.168.1.100
Agent 🤖: [asks for SSH user, port]
You 👤: SSH user admin, port 22
Agent 🤖: [runs complete workflow]
```

---

## What the Agent Does Automatically

Once you provide the information, the agent automatically:

### 1. **Workload Discovery** (AI-Powered)
- Scans ports and processes
- Detects running applications
- Identifies services

### 2. **Resource Classification**
- Determines resource category
- Identifies primary application
- Calculates confidence score

### 3. **Validation Planning** (AI-Powered)
- Selects appropriate checks
- Prioritizes critical validations
- Customizes based on resource type

### 4. **Validation Execution**
- Runs connectivity checks
- Validates configurations
- Checks health status
- Uses MCP server tools

### 5. **AI Evaluation**
- Analyzes results
- Identifies key findings
- Assesses risk level
- Generates recommendations

### 6. **Report Generation**
- Creates executive summary
- Documents findings
- Provides recommendations
- Saves as Markdown file

---

## Commands

While interacting with the agent:

- **Type your prompt** - Describe what you want to validate
- **Answer questions** - Provide requested information
- **Type `exit`, `quit`, or `cancel`** - Stop the agent

---

## Configuration

### Using Ollama (Free Local AI)

The agent uses Ollama by default for free local AI:

```bash
# Install Ollama
brew install ollama  # macOS

# Start Ollama
ollama serve

# Pull model
ollama pull llama3
```

### Using OpenAI (Cloud)

To use OpenAI instead:

```bash
# Set API key
export OPENAI_API_KEY=your_key_here

# Or create .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```

Then modify the agent configuration in the code to use OpenAI.

---

## Generated Reports

Each validation generates a professional report:

**Location**: Current directory  
**Format**: Markdown (`.md`)  
**Filename**: `validation_report_<hostname>_<timestamp>.md`

**Contents**:
- Executive Summary
- Discovery Results
- Classification
- Validation Results
- AI Evaluation
- Recommendations
- Technical Details

---

## Troubleshooting

### Issue: MCP Server Not Running

```
❌ Error: Cannot connect to MCP server

Solution:
Terminal 1:
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Issue: Ollama Not Running

```
❌ Error: Ollama not available

Solution:
ollama serve
ollama pull llama3
```

### Issue: Dependencies Missing

```
❌ Error: Module not found

Solution:
cd python/src
uv pip install -r requirements.txt
```

---

## Advanced Usage

### Multiple Validations

The agent stays running after each validation. Just enter another prompt:

```
Agent 🤖: Validation complete! What would you like to validate next?

You 👤: Check the web server at web-server-01

Agent 🤖: [starts new validation]
```

### Batch Mode

For automated batch validation, you can modify `main.py` to read from a file instead of interactive input.

---

## Architecture

The agent uses a sophisticated multi-agent architecture:

```
main.py
  ↓
RecoveryValidationAgent (Orchestrator)
  ├─ ConversationHandler (Parse prompts)
  ├─ DiscoveryAgent (AI-powered discovery)
  ├─ ValidationPlanner (AI-powered planning)
  ├─ ValidationExecutor (Execute checks via MCP)
  ├─ ResultEvaluator (AI-powered evaluation)
  └─ ReportGenerator (Create reports)
```

All agents use:
- **MCP Server** for validation tools
- **Pydantic AI** for intelligent behavior
- **Ollama/OpenAI** for LLM capabilities

---

## Summary

✅ **No new scripts needed** - Use existing `main.py`  
✅ **Interactive prompts** - Natural language interface  
✅ **Complete automation** - End-to-end workflow  
✅ **AI-powered** - Intelligent discovery and evaluation  
✅ **Professional reports** - Ready for stakeholders  
✅ **Free local testing** - Use Ollama (no API costs)  

---

## Ready to Run!

```bash
# Terminal 1: Start MCP Server
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py

# Terminal 2: Start Agent
cd python/src
python main.py

# Then enter your prompts!
```

---

*The agentic workflow is already built and ready to use!*