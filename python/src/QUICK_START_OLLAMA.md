# Quick Start Guide - Interactive Agent with Ollama

## 🚀 Run the Interactive Agent with Local LLM

This guide shows you how to test the agentic validation workflow manually using natural language prompts with Ollama (local LLM).

## Prerequisites

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from: https://ollama.com/download
```

### 2. Start Ollama and Pull Model
```bash
# Start Ollama service
ollama serve

# In another terminal, pull a model (choose one)
ollama pull llama3.2        # Recommended: Fast and good
ollama pull llama3.1        # Larger, more capable
ollama pull mistral         # Alternative option
ollama pull qwen2.5         # Another good option
```

### 3. Start MCP Server
```bash
# Terminal 1: Start MCP server
cd python/cyberres-mcp
source .venv/bin/activate
uv run mcp dev src/cyberres_mcp/server.py

# Server will start on http://localhost:3000
# Keep this terminal running
```

## 🎯 Run the Interactive Agent

```bash
# Terminal 2: Start interactive agent
cd python/src
source .venv/bin/activate

# Run with Ollama (default)
python interactive_agent.py

# Or specify a different Ollama model
python interactive_agent.py --ollama-model llama3.1

# Or use cloud LLM instead
export OPENAI_API_KEY="sk-..."
python interactive_agent.py --cloud
```

## 💬 Example Prompts

Once the agent starts, you can enter natural language prompts:

### Example 1: Validate a VM
```
Validate VM at 192.168.1.100 with user admin password secret
```

### Example 2: Validate Oracle Database
```
Validate Oracle at db-server:1521 service ORCL 
with db user system password oracle123 
and ssh user oracle password oracle123
```

### Example 3: Validate MongoDB
```
Check MongoDB at mongo-server:27017 
with mongo user admin password mongo123 
and ssh user ubuntu password ubuntu123
```

### Example 4: VM with SSH Key
```
Validate server at 10.0.0.5 with user ubuntu key ~/.ssh/id_rsa
```

## 📊 What Happens

When you enter a prompt, the agent will:

1. **Parse** your natural language request
2. **Connect** to the MCP server
3. **Discover** workloads on the target (ports, processes, applications)
4. **Classify** the resource (database, web server, etc.)
5. **Plan** appropriate validation checks using AI
6. **Execute** validations via MCP tools
7. **Evaluate** results with AI analysis
8. **Display** comprehensive results with recommendations

## 🎨 Interactive Commands

- `help` - Show help and examples
- `quit` or `exit` - Exit the agent
- `Ctrl+C` - Interrupt current operation

## 🔧 Configuration Options

### Use Different Ollama Model
```bash
python interactive_agent.py --ollama-model mistral
```

### Use Different MCP Server
```bash
python interactive_agent.py --mcp-url http://remote-server:3000
```

### Use Cloud LLM Instead of Ollama
```bash
export OPENAI_API_KEY="sk-..."
python interactive_agent.py --cloud
```

## 📝 Full Example Session

```bash
$ python interactive_agent.py

======================================================================
🤖 AGENTIC VALIDATION WORKFLOW - Interactive Mode
======================================================================

📡 Connecting to MCP server at http://localhost:3000...
✅ Connected to MCP server

🦙 Using Ollama (local LLM)
   Make sure Ollama is running: ollama serve
   Default model: llama3.2 (you can change this)
✅ Orchestrator initialized

======================================================================
📝 PROMPT EXAMPLES:
======================================================================

1. "Validate VM at 192.168.1.100 with user admin and password secret"

2. "Check Oracle database at db-server:1521 service ORCL 
    with db user system password oracle123
    and ssh user oracle password oracle123"

3. "Validate MongoDB at mongo-server:27017
    with mongo user admin password mongo123
    and ssh user ubuntu password ubuntu123"

Type 'help' for more examples, 'quit' to exit

----------------------------------------------------------------------

🎯 Enter your validation request (or 'quit'): Validate VM at 192.168.1.100 with user admin password secret

🔍 Processing: Validate VM at 192.168.1.100 with user admin password secret

✅ Parsed request:
   Resource Type: vm
   Host: 192.168.1.100

🚀 Executing validation workflow...
   This may take 30-120 seconds...

======================================================================
📊 VALIDATION RESULTS
======================================================================

⏱️  Execution Time: 45.23s
📈 Workflow Status: SUCCESS

🔍 WORKLOAD DISCOVERY:
   Ports Found: 5
   Processes Found: 23
   Applications Detected: 3

   📱 Detected Applications:
      • Nginx (confidence: 92%)
      • PostgreSQL (confidence: 88%)
      • Redis (confidence: 75%)

🏷️  RESOURCE CLASSIFICATION:
   Category: mixed
   Confidence: 88%
   Primary App: Nginx

📋 VALIDATION PLAN:
   Strategy: mixed_fallback
   Total Checks: 8
   Priority Checks: 3

✅ VALIDATION RESULTS:
   Overall Score: 85/100
   Status: WARNING
   ✓ Passed: 7
   ✗ Failed: 0
   ⚠ Warnings: 1

   Failed Checks:
      ⚠ Disk Usage: /var partition at 87% (threshold: 85%)

🤖 AI EVALUATION:
   Overall Health: GOOD
   Confidence: 85%
   Critical Issues: 0
   Warnings: 1

   Summary:
   System is generally healthy with minor disk space concern on /var partition.
   All critical services are running and responsive.

   💡 Top Recommendations:
      1. Monitor /var partition disk usage and plan for cleanup or expansion
      2. Consider implementing automated log rotation
      3. Review application logs for any errors or warnings
      4. Schedule regular disk space monitoring
      5. Verify backup processes are running correctly

======================================================================

----------------------------------------------------------------------

🎯 Enter your validation request (or 'quit'): quit

👋 Goodbye!
```

## 🐛 Troubleshooting

### Issue: "Cannot connect to MCP server"
**Solution**: Make sure MCP server is running
```bash
cd python/cyberres-mcp
source .venv/bin/activate
uv run mcp dev src/cyberres_mcp/server.py
```

### Issue: "Ollama connection failed"
**Solution**: Make sure Ollama is running
```bash
ollama serve
```

Verify it's working:
```bash
ollama list
curl http://localhost:11434/api/tags
```

### Issue: "Model not found"
**Solution**: Pull the model
```bash
ollama pull llama3.2
```

### Issue: "Could not parse the prompt"
**Solution**: Use the format shown in examples. Type `help` for more examples.

## 🎓 Tips

1. **Start Simple**: Test with localhost first
2. **Use Valid Credentials**: The agent will actually try to connect
3. **Be Patient**: First run may take longer as Ollama loads the model
4. **Check Logs**: Both MCP server and agent show detailed logs
5. **Try Different Models**: Some models work better than others

## 🔐 Security Note

The interactive agent accepts credentials in plain text for testing. In production:
- Use SSH keys instead of passwords
- Integrate with secrets managers (Vault, AWS Secrets Manager)
- Never commit credentials to version control

## 📚 Next Steps

1. Test with your actual infrastructure
2. Try different Ollama models
3. Customize the prompts
4. Review the generated validation plans
5. Analyze AI recommendations

Happy Testing! 🚀