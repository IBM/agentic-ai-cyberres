# 🚀 Run Production Demo - Quick Start

## What You Want: Production-Like Demo

You want to:
1. **Start the agent system**
2. **Give it a natural language prompt** (like "validate this Oracle database")
3. **Watch it run the complete end-to-end workflow automatically**

This is exactly what `production_demo.py` does!

---

## 🎯 Quick Start (3 Steps)

### Step 1: Start Prerequisites

```bash
# Terminal 1: Start Ollama (for free local AI)
ollama serve

# Terminal 2: Start MCP Server (for validation tools)
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Step 2: Pull AI Model (One Time)

```bash
ollama pull llama3
```

### Step 3: Run Demo with Your Prompt

```bash
cd python/src

# Example: Validate Oracle Database
python production_demo.py "Validate the Oracle database at db-server-01"
```

**That's it!** The system will:
- Parse your prompt
- Initialize all agents
- Run complete workflow (Discovery → Classification → Validation → Evaluation)
- Generate professional report
- Show you the results

---

## 📝 Example Prompts You Can Use

### Database Servers
```bash
python production_demo.py "Validate the Oracle database at db-server-01"
python production_demo.py "Check MongoDB at mongo-cluster-01"
python production_demo.py "Validate PostgreSQL server pg-prod-01"
```

### Web Servers
```bash
python production_demo.py "Check the web server at web-server-01"
python production_demo.py "Validate Nginx server nginx-prod-01"
python production_demo.py "Check Apache at apache-01"
```

### Application Servers
```bash
python production_demo.py "Validate app-server-01"
python production_demo.py "Check Tomcat server tomcat-prod-01"
python production_demo.py "Validate JBoss at jboss-01"
```

### Any Server
```bash
python production_demo.py "Discover and validate server-01"
python production_demo.py "Check production server prod-app-01"
```

---

## 🎬 What You'll See

### 1. System Initialization
```
🚀 PRODUCTION DEMO - Agentic Validation Workflow
⚙️  Initializing system with model: ollama:llama3
📡 Connecting to MCP server...
   ✅ MCP server connected
🤖 Initializing AI agents...
   ✅ Discovery agent ready
   ✅ Validation agent ready
   ✅ Evaluation agent ready
✅ System ready!
```

### 2. Prompt Parsing
```
📝 PARSING PROMPT
Prompt: "Validate the Oracle database at db-server-01"
🔍 Detected: Oracle Database
   Host: db-server-01
✅ Request created
```

### 3. Workflow Execution
```
🔄 EXECUTING WORKFLOW
📋 Workflow Phases:
   1️⃣  Workload Discovery (AI-powered)
   2️⃣  Resource Classification
   3️⃣  Validation Planning
   4️⃣  Validation Execution
   5️⃣  AI Evaluation
   6️⃣  Report Generation
🚀 Starting workflow execution...
```

### 4. Results
```
📊 WORKFLOW RESULTS
⏱️  Execution Time: 45.23s
📈 Workflow Status: SUCCESS

🔍 Discovery Results:
   Applications Detected: 2
   • Oracle Database 19c (confidence: 95%)
   • Oracle Enterprise Manager (confidence: 85%)

🏷️  Classification:
   Category: DATABASE_SERVER
   Confidence: 95%

✅ Validation Results:
   Overall Status: PASS
   Score: 92/100
   Checks Passed: 11

🤖 AI Evaluation:
   Overall Health: HEALTHY
   Risk Level: LOW
   💡 Key Findings: [AI-generated insights]
   📋 Recommendations: [AI-generated recommendations]

📄 Report saved: validation_report_db-server-01_20260223_153045.md
```

---

## 🎯 What Gets Validated Automatically

The demo runs a **complete production workflow**:

### Phase 1: AI-Powered Discovery
- Scans ports and processes
- Detects running applications
- Identifies services and versions

### Phase 2: Intelligent Classification
- Determines resource type (Web Server, Database, App Server, etc.)
- Identifies primary application
- Calculates confidence score

### Phase 3: Smart Validation Planning
- Selects appropriate validation checks
- Prioritizes critical validations
- Customizes based on resource type

### Phase 4: Validation Execution
- Connectivity checks
- Configuration validation
- Health status verification
- Security checks

### Phase 5: AI Evaluation
- Analyzes all results
- Identifies key findings
- Assesses risk level
- Generates recommendations

### Phase 6: Professional Report
- Executive summary
- Detailed findings
- Actionable recommendations
- Markdown format

---

## 🔧 Using Different AI Models

### Free Local (Ollama) - Recommended for Testing

```bash
# Default: Llama 3
python production_demo.py "Validate server-01"

# Faster: Mistral
ollama pull mistral
python production_demo.py "Validate server-01" --model ollama:mistral
```

### Cloud (OpenAI) - Best Quality

```bash
export OPENAI_API_KEY=your_key_here
python production_demo.py "Validate server-01" --model openai:gpt-4
```

---

## 📊 Generated Reports

Each run generates a professional Markdown report:

**Filename**: `validation_report_<hostname>_<timestamp>.md`

**Contents**:
- Executive Summary (AI-generated)
- Discovery Results
- Classification Details
- Validation Results (Pass/Fail/Warning)
- AI Evaluation (Health, Risk, Findings)
- Recommendations (AI-generated)
- Technical Details

**Example**: `validation_report_db-server-01_20260223_153045.md`

---

## 🎓 How It Works

```
Your Prompt: "Validate the Oracle database at db-server-01"
     ↓
Parse Intent (extract hostname, detect resource type)
     ↓
Initialize System (MCP client, AI agents, orchestrator)
     ↓
Execute Workflow:
  ├─ Discovery Agent (AI) → Scan ports/processes
  ├─ Classification Agent → Determine resource type
  ├─ Validation Agent (AI) → Plan and execute checks
  ├─ Evaluation Agent (AI) → Analyze results
  └─ Report Generator → Create professional report
     ↓
Display Results + Save Report
```

---

## 🐛 Troubleshooting

### MCP Server Not Running
```bash
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Ollama Not Running
```bash
ollama serve
ollama pull llama3
```

### Dependencies Missing
```bash
cd python/src
uv pip install -r requirements.txt
```

---

## 🚀 Ready to Run?

**Just 3 commands:**

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start MCP Server
cd python/cyberres-mcp && uv run mcp dev src/cyberres_mcp/server.py

# Terminal 3: Run Demo
cd python/src
python production_demo.py "Validate your-server-01"
```

---

## 📚 More Information

- **Full Guide**: See `PRODUCTION_DEMO_GUIDE.md` for detailed documentation
- **Architecture**: See `AGENTIC_WORKFLOW_REVIEW.md` for design details
- **Phase 2 Features**: See `PHASE2_IMPLEMENTATION_COMPLETE.md` for all enhancements

---

## ✨ Key Features

✅ **Natural Language Interface** - Just describe what you want  
✅ **Complete Automation** - End-to-end workflow  
✅ **AI-Powered** - Intelligent discovery, classification, evaluation  
✅ **Production-Ready** - Real validation with MCP tools  
✅ **Professional Reports** - Ready for stakeholders  
✅ **Free Local Testing** - Use Ollama (no API costs)  
✅ **Multiple Models** - OpenAI or Ollama  

---

**Start your production demo now!** 🎉

```bash
python production_demo.py "Validate the Oracle database at db-server-01"
```

---

*Made with Bob - AI Assistant*