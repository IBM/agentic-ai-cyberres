# Production Demo Guide

## Run End-to-End Workflow with Natural Language Prompts

This guide shows you how to run the production-style demo that accepts natural language prompts and executes the complete validation workflow automatically.

---

## What This Demo Does

```
Natural Language Prompt
         ↓
    Parse Intent
         ↓
  Initialize System
         ↓
Execute Complete Workflow:
  1. Workload Discovery (AI)
  2. Resource Classification
  3. Validation Planning
  4. Validation Execution
  5. AI Evaluation
  6. Report Generation
         ↓
    Display Results
```

---

## Quick Start

### Prerequisites

```bash
# 1. Start Ollama (for free local testing)
ollama serve

# 2. Pull Llama 3 model
ollama pull llama3

# 3. Start MCP server (in separate terminal)
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Run Demo

```bash
cd python/src

# Example 1: Validate Oracle Database
python production_demo.py "Validate the Oracle database at db-server-01"

# Example 2: Check Web Server
python production_demo.py "Check the web server at web-server-01"

# Example 3: Discover and Validate
python production_demo.py "Discover and validate app-server-01"

# Example 4: MongoDB Validation
python production_demo.py "Validate MongoDB at mongo-cluster-01"
```

---

## Demo Output

### Phase 1: Initialization

```
================================================================================
🚀 PRODUCTION DEMO - Agentic Validation Workflow
================================================================================

⚙️  Initializing system with model: ollama:llama3

📡 Connecting to MCP server...
   ✅ MCP server connected

🤖 Initializing AI agents...
   ✅ Orchestrator initialized
   ✅ Discovery agent ready
   ✅ Validation agent ready
   ✅ Evaluation agent ready

✅ System ready!
```

### Phase 2: Prompt Parsing

```
================================================================================
📝 PARSING PROMPT
================================================================================

Prompt: "Validate the Oracle database at db-server-01"

🔍 Detected: Oracle Database
   Host: db-server-01

✅ Request created:
   Resource Type: oracle_db
   Auto Discovery: Enabled
   Validation Level: Comprehensive
```

### Phase 3: Workflow Execution

```
================================================================================
🔄 EXECUTING WORKFLOW
================================================================================

📋 Workflow Phases:
   1️⃣  Workload Discovery (AI-powered)
   2️⃣  Resource Classification
   3️⃣  Validation Planning
   4️⃣  Validation Execution
   5️⃣  AI Evaluation
   6️⃣  Report Generation

🚀 Starting workflow execution...

[Agent logs showing each phase]
```

### Phase 4: Results Display

```
================================================================================
📊 WORKFLOW RESULTS
================================================================================

⏱️  Execution Time: 45.23s
📈 Workflow Status: SUCCESS

🔍 Discovery Results:
   Ports Found: 3
   Processes Found: 8
   Applications Detected: 2

   📦 Detected Applications:
      • Oracle Database 19c (confidence: 95%)
      • Oracle Enterprise Manager (confidence: 85%)

🏷️  Classification:
   Category: DATABASE_SERVER
   Confidence: 95%
   Primary App: Oracle Database 19c

✅ Validation Results:
   Overall Status: PASS
   Score: 92/100
   Checks Passed: 11
   Checks Failed: 0
   Warnings: 1

🤖 AI Evaluation:
   Overall Health: HEALTHY
   Risk Level: LOW

   💡 Key Findings:
      • Database is running and accessible
      • All critical services are operational
      • System resources are within normal range

   📋 Recommendations:
      • Consider enabling automated backups
      • Review security configurations
      • Monitor disk space usage
```

### Phase 5: Report Generation

```
================================================================================
📄 GENERATING REPORT
================================================================================

✅ Report saved: validation_report_db-server-01_20260223_153045.md
   Length: 3542 characters

📄 Report Preview (first 500 chars):
--------------------------------------------------------------------------------
# Validation Report: db-server-01

**Generated**: 2026-02-23 15:30:45
**Resource Type**: Oracle Database
**Overall Score**: 92/100
**Status**: PASS

## Executive Summary

The validation of db-server-01 has been completed successfully with an
overall score of 92/100. The resource is classified as a DATABASE_SERVER
with high confidence (95%). All critical checks passed, with one warning
related to backup configuration...
--------------------------------------------------------------------------------
```

### Phase 6: Summary

```
================================================================================
✅ DEMO COMPLETE
================================================================================

📊 Summary:
   Workflow Status: success
   Validation Score: 92/100
   Execution Time: 45.23s
   Report: validation_report_db-server-01_20260223_153045.md

🎉 Validation completed successfully!
```

---

## Example Prompts

### Database Servers

```bash
# Oracle
python production_demo.py "Validate the Oracle database at db-server-01"
python production_demo.py "Check Oracle DB on prod-oracle-01"

# MongoDB
python production_demo.py "Validate MongoDB at mongo-cluster-01"
python production_demo.py "Check MongoDB server mongo-prod-01"

# PostgreSQL (detected as VM with database)
python production_demo.py "Validate PostgreSQL at pg-server-01"
```

### Web Servers

```bash
# Generic web server
python production_demo.py "Check the web server at web-server-01"
python production_demo.py "Validate web-prod-01"

# Nginx
python production_demo.py "Validate Nginx server at nginx-01"

# Apache
python production_demo.py "Check Apache server apache-prod-01"
```

### Application Servers

```bash
# Generic app server
python production_demo.py "Validate app-server-01"
python production_demo.py "Check application server at app-prod-01"

# Tomcat
python production_demo.py "Validate Tomcat server tomcat-01"

# JBoss
python production_demo.py "Check JBoss at jboss-prod-01"
```

### Container Hosts

```bash
# Docker
python production_demo.py "Validate Docker host docker-01"
python production_demo.py "Check container server at docker-prod-01"

# Kubernetes
python production_demo.py "Validate Kubernetes node k8s-node-01"
```

---

## Using Different Models

### Ollama Llama 3 (Default - Free)

```bash
python production_demo.py "Validate db-server-01"
# or explicitly
python production_demo.py "Validate db-server-01" --model ollama:llama3
```

### Ollama Mistral (Faster)

```bash
# First pull the model
ollama pull mistral

# Then use it
python production_demo.py "Validate db-server-01" --model ollama:mistral
```

### OpenAI GPT-4 (Best Quality)

```bash
# Set API key
export OPENAI_API_KEY=your_key_here

# Run with GPT-4
python production_demo.py "Validate db-server-01" --model openai:gpt-4
```

---

## What Gets Validated

The demo automatically:

### 1. **Discovers Workload**
- Scans ports and processes
- Detects running applications
- Identifies services

### 2. **Classifies Resource**
- Determines resource category
- Identifies primary application
- Calculates confidence score

### 3. **Plans Validation**
- Selects appropriate checks
- Prioritizes critical validations
- Customizes based on resource type

### 4. **Executes Validations**
- Runs connectivity checks
- Validates configurations
- Checks health status
- Verifies security settings

### 5. **Evaluates Results**
- AI-powered analysis
- Risk assessment
- Key findings identification
- Actionable recommendations

### 6. **Generates Report**
- Executive summary
- Detailed findings
- Recommendations
- Professional formatting

---

## Generated Reports

Reports are saved as Markdown files:

```
validation_report_<hostname>_<timestamp>.md
```

Example: `validation_report_db-server-01_20260223_153045.md`

### Report Contents

```markdown
# Validation Report: db-server-01

**Generated**: 2026-02-23 15:30:45
**Resource Type**: Oracle Database
**Overall Score**: 92/100
**Status**: PASS

## Executive Summary
[AI-generated summary]

## Discovery Results
- Ports: 3
- Processes: 8
- Applications: 2

## Classification
- Category: DATABASE_SERVER
- Confidence: 95%
- Primary Application: Oracle Database 19c

## Validation Results
### Passed Checks (11)
- ✅ Database connectivity
- ✅ Listener status
- ✅ Service availability
...

### Warnings (1)
- ⚠️ Backup configuration needs review

## AI Evaluation
### Overall Health: HEALTHY
### Risk Level: LOW

### Key Findings
1. Database is running and accessible
2. All critical services are operational
3. System resources are within normal range

### Recommendations
1. Consider enabling automated backups
2. Review security configurations
3. Monitor disk space usage

## Technical Details
[Detailed check results]
```

---

## Troubleshooting

### Issue: MCP Server Not Running

```
❌ Error: Failed to connect to MCP server

Solution:
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Issue: Ollama Not Running

```
❌ Error: Ollama server not responding

Solution:
ollama serve
ollama pull llama3
```

### Issue: Model Not Found

```
❌ Error: Model not available

Solution:
# For Ollama
ollama pull llama3
ollama pull mistral

# For OpenAI
export OPENAI_API_KEY=your_key_here
```

### Issue: Import Errors

```
❌ Error: Module not found

Solution:
cd python/src
uv pip install -r requirements.txt
```

---

## Advanced Usage

### Custom Validation Levels

Modify the demo to support different validation levels:

```python
# In production_demo.py, modify parse_prompt()
if "quick" in prompt_lower:
    validation_level = "basic"
elif "deep" in prompt_lower:
    validation_level = "comprehensive"
else:
    validation_level = "standard"
```

Then use:
```bash
python production_demo.py "Quick check of web-server-01"
python production_demo.py "Deep validation of db-server-01"
```

### Batch Processing

Create a script to validate multiple resources:

```python
# batch_validate.py
import asyncio
from production_demo import ProductionDemo

async def batch_validate():
    demo = ProductionDemo()
    await demo.initialize()
    
    prompts = [
        "Validate db-server-01",
        "Validate web-server-01",
        "Validate app-server-01"
    ]
    
    for prompt in prompts:
        request = await demo.parse_prompt(prompt)
        result = await demo.execute_workflow(request)
        await demo.generate_report(result)
    
    await demo.cleanup()

asyncio.run(batch_validate())
```

### Custom Report Formats

Modify report generation:

```python
# Add to production_demo.py
async def generate_json_report(self, result):
    """Generate JSON report."""
    import json
    
    report_data = {
        "host": result.request.resource_info.host,
        "status": result.workflow_status,
        "score": result.validation_result.score,
        "timestamp": datetime.now().isoformat()
    }
    
    filename = f"report_{result.request.resource_info.host}.json"
    with open(filename, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    return filename
```

---

## Performance Tips

### 1. Use Faster Models for Testing

```bash
# Mistral is faster than Llama 3
python production_demo.py "Validate server" --model ollama:mistral
```

### 2. Disable Discovery for Known Resources

Modify the demo to skip discovery if resource type is known:

```python
request = ValidationRequest(
    resource_info=resource_info,
    auto_discover=False,  # Skip discovery
    validation_level="basic"
)
```

### 3. Parallel Validation

For multiple resources, run validations in parallel:

```python
import asyncio

async def validate_all(hosts):
    tasks = [demo.run(f"Validate {host}") for host in hosts]
    await asyncio.gather(*tasks)
```

---

## Production Deployment

### 1. API Wrapper

Wrap the demo in a REST API:

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/validate")
async def validate(prompt: str):
    demo = ProductionDemo()
    result = await demo.run(prompt)
    return result
```

### 2. CLI Tool

Create a proper CLI:

```bash
# Install as command
pip install -e .

# Use anywhere
cyberres-validate "Check db-server-01"
```

### 3. Scheduled Validation

Run periodic validations:

```python
# cron job or scheduler
import schedule

def validate_critical_servers():
    servers = ["db-prod-01", "web-prod-01", "app-prod-01"]
    for server in servers:
        os.system(f'python production_demo.py "Validate {server}"')

schedule.every().day.at("02:00").do(validate_critical_servers)
```

---

## Summary

The production demo provides:

✅ **Natural language interface** - Just describe what you want  
✅ **Complete automation** - End-to-end workflow execution  
✅ **AI-powered analysis** - Intelligent discovery and evaluation  
✅ **Professional reports** - Ready for stakeholders  
✅ **Multiple models** - OpenAI or free local Ollama  
✅ **Production-ready** - Real validation with MCP tools  

**Start validating now:**

```bash
cd python/src
python production_demo.py "Validate your-server-01"
```

---

*Made with Bob - AI Assistant*