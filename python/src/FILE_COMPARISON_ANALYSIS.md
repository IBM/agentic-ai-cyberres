# File Comparison Analysis: Interactive Entry Points

## Overview

This document explains the differences between three similar-looking entry point files in `python/src/`:

1. **`main.py`** - Legacy entry point (OLD WORKFLOW)
2. **`interactive_agent.py`** - Current production entry point (NEW WORKFLOW)
3. **`interactive_agent_cli.py`** - Testing/development tool (PHASE 2 TESTING)

---

## 1. `main.py` - Legacy Entry Point

### Purpose
**LEGACY/DEPRECATED** - Original entry point using the old workflow architecture.

### Key Characteristics
- **Lines**: 60
- **Created**: Early development phase
- **Status**: ⚠️ **DEPRECATED** - Should be removed or archived
- **Workflow**: Uses `RecoveryValidationAgent` with old architecture

### Architecture
```
main.py
  └─> RecoveryValidationAgent (recovery_validation_agent.py)
       ├─> ConversationHandler (conversation.py) - OLD
       ├─> ValidationPlanner (planner.py) - Rule-based
       ├─> ValidationExecutor (executor.py) - Simple execution
       └─> ResultEvaluator (evaluator.py) - Template-based
```

### Usage
```bash
cd python/src
uv run python main.py
```

### What It Does
1. Creates console reader with fallback prompt
2. Initializes `RecoveryValidationAgent`
3. Runs interactive mode with old conversation handler
4. Uses **rule-based planning** (not AI-driven)
5. Uses **template-based evaluation** (not AI-powered)

### Why It Exists
- Original implementation before agentic transformation
- Kept for backward compatibility
- **Should be removed** after migration complete

---

## 2. `interactive_agent.py` - Current Production Entry Point

### Purpose
**CURRENT PRODUCTION** - Main entry point for the new agentic workflow.

### Key Characteristics
- **Lines**: 499
- **Created**: Phase 3 (Agentic Transformation)
- **Status**: ✅ **ACTIVE** - Primary production entry point
- **Workflow**: Uses `ValidationOrchestrator` with multi-agent architecture

### Architecture
```
interactive_agent.py
  └─> InteractiveAgent
       └─> ValidationOrchestrator (agents/orchestrator.py)
            ├─> DiscoveryAgent - AI-powered workload discovery
            ├─> ValidationAgent - Adaptive validation planning
            ├─> EvaluationAgent - AI-powered result evaluation
            └─> ApplicationClassifier - Rule-based classification
```

### Usage
```bash
cd python/src
uv run python interactive_agent.py --ollama  # Local LLM
uv run python interactive_agent.py --cloud   # Cloud LLM
```

### What It Does
1. **Natural Language Parsing**: Accepts conversational prompts
   - "Validate VM at 192.168.1.100 with user admin password secret"
   - "Check Oracle database at db-server:1521..."
   
2. **MCP Integration**: Connects via stdio transport
   ```python
   MCPStdioClient(
       server_command="uv",
       server_args=["--directory", cyberres_mcp_dir, "run", "cyberres-mcp"],
       server_env={"MCP_TRANSPORT": "stdio"}
   )
   ```

3. **Multi-Agent Orchestration**:
   - Discovery: AI-powered workload detection
   - Classification: Intelligent resource categorization
   - Validation: Adaptive plan generation
   - Evaluation: AI-driven result analysis

4. **LLM Support**:
   - Ollama (local): `llama3.2`, `mistral`, etc.
   - Cloud: OpenAI, Anthropic, Groq

5. **Rich Output**: Detailed results with AI insights

### Key Features
- ✅ Natural language prompt parsing
- ✅ Multi-resource support (VM, Oracle, MongoDB)
- ✅ AI-powered discovery and evaluation
- ✅ Ollama and cloud LLM support
- ✅ Comprehensive result display
- ✅ MCP stdio transport

### Example Session
```
🤖 Enter your validation request: Validate VM at 192.168.1.100 with user admin password secret

🔍 Processing: Validate VM at 192.168.1.100 with user admin password secret

✅ Parsed request:
   Resource Type: vm
   Host: 192.168.1.100

🚀 Executing validation workflow...
   This may take 30-120 seconds...

📊 VALIDATION RESULTS
   Overall Score: 85/100
   Status: PASS
   ✓ Passed: 12
   ✗ Failed: 2
   ⚠ Warnings: 1

🤖 AI EVALUATION:
   Overall Health: HEALTHY
   Confidence: 92%
   Summary: System is operational with minor issues...
```

---

## 3. `interactive_agent_cli.py` - Testing/Development Tool

### Purpose
**TESTING TOOL** - Interactive CLI for testing Phase 2 enhanced agents manually.

### Key Characteristics
- **Lines**: 455
- **Created**: Phase 2 (Enhanced Agents Development)
- **Status**: 🧪 **TESTING/DEVELOPMENT** - For manual agent testing
- **Workflow**: Direct agent testing without full orchestration

### Architecture
```
interactive_agent_cli.py
  └─> InteractiveAgentCLI
       ├─> EnhancedDiscoveryAgent (direct testing)
       ├─> ClassificationAgent (direct testing)
       └─> ReportingAgent (direct testing)
```

### Usage
```bash
cd python/src
uv run python interactive_agent_cli.py
```

### What It Does
Provides **step-by-step testing** of individual agents:

1. **Setup Command**: Configure agents
   ```
   🤖 Enter command: setup
   Choose LLM Model:
     1. OpenAI GPT-4
     2. Ollama Llama 3
     3. Ollama Mistral
   ```

2. **Discover Command**: Test discovery agent
   ```
   🤖 Enter command: discover
   Enter hostname: 192.168.1.100
   Enter SSH user: admin
   ```

3. **Classify Command**: Test classification agent
   ```
   🤖 Enter command: classify
   🏷️ Classification Agent
   Category: database_server
   Confidence: 85%
   ```

4. **Report Command**: Test reporting agent
   ```
   🤖 Enter command: report
   📊 Reporting Agent
   ✓ AI-powered report generated
   ```

5. **Workflow Command**: Run complete workflow
   ```
   🤖 Enter command: workflow
   This will run: Discovery → Classification → Report
   ```

### Key Features
- ✅ Step-by-step agent testing
- ✅ Individual agent control
- ✅ Feature flag configuration
- ✅ Execution history viewing
- ✅ Report preview and saving
- ✅ Mock data support

### Use Cases
- Testing new agent implementations
- Debugging agent behavior
- Validating feature flags
- Developing new agents
- Training and demonstrations

---

## Comparison Matrix

| Feature | main.py | interactive_agent.py | interactive_agent_cli.py |
|---------|---------|---------------------|-------------------------|
| **Status** | ⚠️ Deprecated | ✅ Production | 🧪 Testing |
| **Architecture** | Old (single agent) | New (multi-agent) | Phase 2 (enhanced) |
| **AI-Powered** | ❌ No | ✅ Yes | ✅ Yes |
| **MCP Integration** | ✅ Yes (old) | ✅ Yes (stdio) | ✅ Yes (stdio) |
| **Natural Language** | ❌ Limited | ✅ Full support | ❌ Structured input |
| **Orchestration** | ❌ Simple | ✅ Full orchestration | ❌ Manual steps |
| **LLM Support** | ❌ No | ✅ Ollama + Cloud | ✅ Ollama + Cloud |
| **Use Case** | Legacy | Production | Testing/Dev |
| **Lines of Code** | 60 | 499 | 455 |
| **Entry Point** | `main()` | `main()` | `main()` |
| **Interactive** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Step-by-Step** | ❌ No | ❌ No | ✅ Yes |

---

## Workflow Comparison

### main.py Workflow (OLD)
```
User Input
  ↓
ConversationHandler (simple parsing)
  ↓
RecoveryValidationAgent
  ├─> Discovery (basic)
  ├─> Planning (rule-based)
  ├─> Execution (simple)
  └─> Evaluation (template)
  ↓
Report (basic)
```

### interactive_agent.py Workflow (NEW)
```
Natural Language Prompt
  ↓
InteractiveAgent (NLP parsing)
  ↓
ValidationOrchestrator
  ├─> DiscoveryAgent (AI-powered)
  │    └─> Chain-of-Thought reasoning
  ├─> ApplicationClassifier (rule-based)
  ├─> ValidationAgent (adaptive)
  │    └─> Context-aware planning
  └─> EvaluationAgent (AI-powered)
       └─> Actionable insights
  ↓
Comprehensive Report (AI-enhanced)
```

### interactive_agent_cli.py Workflow (TESTING)
```
Command Menu
  ↓
User Selects: setup/discover/classify/report/workflow
  ↓
Direct Agent Testing
  ├─> EnhancedDiscoveryAgent (isolated)
  ├─> ClassificationAgent (isolated)
  └─> ReportingAgent (isolated)
  ↓
Results Display + History
```

---

## Recommendations

### 1. For Production Use
**Use `interactive_agent.py`**
- Full agentic workflow
- AI-powered intelligence
- Natural language support
- Production-ready

### 2. For Development/Testing
**Use `interactive_agent_cli.py`**
- Test individual agents
- Debug agent behavior
- Validate new features
- Training demonstrations

### 3. For Legacy Support
**Avoid `main.py`**
- Deprecated architecture
- No AI capabilities
- Should be removed after migration

---

## Migration Path

### Current State
```
main.py (deprecated) ──────────────────┐
                                       ├─> Should be removed
interactive_agent.py (production) ─────┤
                                       └─> Primary entry point
interactive_agent_cli.py (testing) ────┐
                                       └─> Keep for development
```

### Recommended Actions

1. **Remove `main.py`**
   ```bash
   # Archive first
   mv python/src/main.py python/archive/legacy/main.py
   ```

2. **Update Documentation**
   - Update README.md to reference `interactive_agent.py`
   - Remove references to `main.py`
   - Document `interactive_agent_cli.py` as testing tool

3. **Update Scripts**
   - Update any scripts that call `main.py`
   - Point to `interactive_agent.py` instead

---

## Code Examples

### Starting Production Workflow
```bash
# With Ollama (local)
cd python/src
uv run python interactive_agent.py --ollama

# With cloud LLM
cd python/src
export OPENAI_API_KEY="your-key"
uv run python interactive_agent.py --cloud
```

### Testing Individual Agents
```bash
# Start testing CLI
cd python/src
uv run python interactive_agent_cli.py

# Then use commands:
# - setup: Configure agents
# - discover: Test discovery
# - classify: Test classification
# - report: Test reporting
# - workflow: Test complete flow
```

---

## Summary

| File | Purpose | Status | When to Use |
|------|---------|--------|-------------|
| `main.py` | Legacy entry point | ⚠️ Deprecated | Never (remove) |
| `interactive_agent.py` | Production workflow | ✅ Active | Production use |
| `interactive_agent_cli.py` | Testing tool | 🧪 Development | Testing/debugging |

**Bottom Line**: Use `interactive_agent.py` for production, `interactive_agent_cli.py` for testing, and remove `main.py`.