# Testing Guide: Running main.py with Enhanced Workflow

## Quick Start

### 1. Basic Run
```bash
cd python/src
uv run python main.py
```

This starts the interactive Recovery Validation Agent with all the enhancements we implemented.

---

## 🧪 Test Scenarios

### Scenario 1: Simple VM Validation (Fast-Path Test)

**What it tests**: Fast-path discovery optimization (Day 2)

**Prompt to use**:
```
I want to validate a VM at 192.168.1.100 with SSH user admin
```

**Expected behavior**:
- Discovery agent uses fast-path (no LLM call)
- Classification may use cache if similar VM was validated before
- Simple report uses template (no LLM call)

**Look for in logs**:
```
INFO - Using fast-path discovery plan (simple VM)
INFO - Simple report detected - using template (no LLM needed)
```

---

### Scenario 2: Oracle Database Validation (Full AI Test)

**What it tests**: Full AI workflow with Chain-of-Thought and few-shot learning

**Prompt to use**:
```
I need to validate an Oracle database server at 10.0.1.50 running on port 1521
```

**Expected behavior**:
- Discovery agent uses LLM with Chain-of-Thought reasoning
- Classification uses few-shot examples to identify Oracle DB
- May hit cache if similar Oracle DB was validated before
- Complex report uses AI synthesis

**Look for in logs**:
```
INFO - Using AI-powered discovery planning with Chain-of-Thought
INFO - Using AI-powered classification
INFO - Classification: DATABASE_SERVER (confidence: 0.95)
INFO - Using AI-powered report generation
```

---

### Scenario 3: MongoDB Cluster Validation (Cache Test)

**What it tests**: Classification caching (Day 4)

**First run prompt**:
```
Validate a MongoDB cluster at 10.0.2.100 with ports 27017, 27018, 27019
```

**Second run prompt** (same or similar):
```
Validate another MongoDB server at 10.0.2.101 with port 27017
```

**Expected behavior**:
- First run: Cache miss, calls LLM
- Second run: Cache hit, returns cached classification

**Look for in logs**:
```
# First run:
DEBUG - Cache MISS for 10.0.2.100
INFO - Using AI-powered classification
INFO - Cached classification result (cache size: 1)

# Second run:
DEBUG - Cache HIT for 10.0.2.101
INFO - Using cached classification (hit rate: 50.0%)
```

---

### Scenario 4: Web Server with Application (Few-Shot Test)

**What it tests**: Few-shot learning examples (Day 2)

**Prompt to use**:
```
Validate a web server at 10.0.3.50 running Nginx on port 80 and Tomcat on port 8080
```

**Expected behavior**:
- Classification uses few-shot examples
- Identifies as APPLICATION_SERVER (not WEB_SERVER)
- Recognizes Nginx as reverse proxy, Tomcat as primary app

**Look for in logs**:
```
INFO - Classification: APPLICATION_SERVER (confidence: 0.85)
INFO - Primary Application: Apache Tomcat
INFO - Secondary Applications: ['Nginx']
```

---

### Scenario 5: Multiple Resources (Cost Optimization Test)

**What it tests**: Overall cost optimization across all improvements

**Prompts to use in sequence**:
```
1. Validate VM at 192.168.1.10
2. Validate VM at 192.168.1.11
3. Validate Oracle DB at 10.0.1.50
4. Validate MongoDB at 10.0.2.100
5. Validate another VM at 192.168.1.12
```

**Expected behavior**:
- VMs use fast-path (no LLM for discovery)
- Similar resources hit cache (no LLM for classification)
- Simple validations use templates (no LLM for reporting)
- Overall: ~60% reduction in LLM calls

**Check cache stats**:
```python
# After running, check cache statistics
from agents.classification_agent import ClassificationAgent
agent = ClassificationAgent()
stats = agent.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1f}%")
```

---

## 📊 Monitoring During Tests

### Enable Debug Logging
```bash
# Set environment variable for verbose logging
export LOG_LEVEL=DEBUG
cd python/src
uv run python main.py
```

### Watch for Key Indicators

#### 1. Fast-Path Discovery (Day 2)
```
✅ "Using fast-path discovery plan (simple VM)"
❌ "Using AI-powered discovery planning"
```

#### 2. Classification Caching (Day 4)
```
✅ "Cache HIT for <host>"
✅ "Using cached classification (hit rate: X%)"
❌ "Cache MISS for <host>"
```

#### 3. Smart Reporting (Day 3)
```
✅ "Simple report detected - using template"
❌ "Using AI-powered report generation"
```

#### 4. Chain-of-Thought (Day 2)
```
✅ "Step 1: Resource Analysis"
✅ "Step 2: Discovery Goals"
✅ "Step 5: Final Decision"
```

#### 5. Few-Shot Learning (Day 2)
```
✅ "Classification Examples"
✅ "Example 1: Oracle Database Server"
```

---

## 🎯 Expected Results

### Cost Comparison

**Before Optimizations** (5 resources):
```
Resource 1: $0.150 (4 LLM calls)
Resource 2: $0.150 (4 LLM calls)
Resource 3: $0.150 (4 LLM calls)
Resource 4: $0.150 (4 LLM calls)
Resource 5: $0.150 (4 LLM calls)
─────────────────────────────
Total: $0.750 (20 LLM calls)
```

**After Optimizations** (5 resources):
```
Resource 1: $0.095 (2.6 LLM calls) - First run, no cache
Resource 2: $0.045 (1.0 LLM call)  - Fast-path + cache hit + template
Resource 3: $0.095 (2.6 LLM calls) - Different type, cache miss
Resource 4: $0.045 (1.0 LLM call)  - Similar to R3, cache hit
Resource 5: $0.045 (1.0 LLM call)  - Similar to R1, cache hit
─────────────────────────────
Total: $0.325 (8.2 LLM calls)
Savings: $0.425 (57% reduction!)
```

---

## 🔧 Feature Flag Configuration

### Enable All Optimizations (Recommended)
```bash
# Set environment variables
export FEATURE_FLAG_SMART_LLM_USAGE=true
export FEATURE_FLAG_CLASSIFICATION_CACHING=true
export FEATURE_FLAG_FAST_PATH_DISCOVERY=true
export FEATURE_FLAG_TEMPLATE_REPORTING=true
export FEATURE_FLAG_AI_CLASSIFICATION=true
export FEATURE_FLAG_AI_REPORTING=true

# Run with all optimizations
cd python/src
uv run python main.py
```

### Test Without Optimizations (Baseline)
```bash
# Disable optimizations to see the difference
export FEATURE_FLAG_SMART_LLM_USAGE=false
export FEATURE_FLAG_CLASSIFICATION_CACHING=false
export FEATURE_FLAG_FAST_PATH_DISCOVERY=false
export FEATURE_FLAG_TEMPLATE_REPORTING=false

# Run baseline
cd python/src
uv run python main.py
```

---

## 📝 Sample Test Session

### Complete Test Flow

```bash
# 1. Start the agent
cd python/src
uv run python main.py

# You'll see:
# ======================================================================
#   🔍 RECOVERY VALIDATION AGENT
#   Validate recovered infrastructure resources
# ======================================================================

# 2. Test Simple VM (Fast-Path)
> I want to validate a VM at 192.168.1.100

# Expected output:
# ✓ Discovery planning complete (fast-path)
# ✓ Classification complete: VM (confidence: 0.90)
# ✓ Validation complete: 3 checks passed
# ✓ Report generated (template)

# 3. Test Oracle DB (Full AI)
> Validate an Oracle database at 10.0.1.50 on port 1521

# Expected output:
# ✓ Discovery planning complete (AI with CoT)
# ✓ Classification complete: DATABASE_SERVER (confidence: 0.95)
# ✓ Validation complete: 5 checks (2 passed, 3 failed)
# ✓ Report generated (AI synthesis)

# 4. Test Similar Oracle DB (Cache Hit)
> Validate another Oracle database at 10.0.1.51 on port 1521

# Expected output:
# ✓ Discovery planning complete (AI with CoT)
# ✓ Classification complete: DATABASE_SERVER (cached, hit rate: 50%)
# ✓ Validation complete: 5 checks passed
# ✓ Report generated (AI synthesis)

# 5. Check cache statistics
> show cache stats

# Expected output:
# Cache Statistics:
# - Size: 2/1000
# - Hits: 1
# - Misses: 2
# - Hit Rate: 33.3%
# - TTL: 3600s

# 6. Exit
> exit
```

---

## 🐛 Troubleshooting

### Issue: "No LLM configured"
```bash
# Solution: Set up Ollama or OpenAI
export OLLAMA_BASE_URL=http://localhost:11434
# OR
export OPENAI_API_KEY=your-key-here
```

### Issue: "MCP server not found"
```bash
# Solution: Start MCP server first
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### Issue: "Cache not working"
```bash
# Solution: Enable caching flag
export FEATURE_FLAG_CLASSIFICATION_CACHING=true
```

### Issue: "All requests using LLM"
```bash
# Solution: Enable optimization flags
export FEATURE_FLAG_SMART_LLM_USAGE=true
export FEATURE_FLAG_FAST_PATH_DISCOVERY=true
```

---

## 📈 Performance Metrics to Track

### 1. LLM Call Reduction
```python
# Before: 4 calls per resource
# After: 2.6 calls per resource (avg)
# Target: 35% reduction
```

### 2. Cache Hit Rate
```python
# Target: 50-70% after warmup
# Check: agent.get_cache_stats()['hit_rate']
```

### 3. Response Time
```python
# Fast-path: <100ms (no LLM)
# Cache hit: <100ms (no LLM)
# LLM call: 2-5s (depends on model)
```

### 4. Cost Savings
```python
# Per resource: $0.055 savings (37%)
# Per 100 resources: $5.50 savings
# Per 1000 resources: $55 savings
```

---

## 🎓 Understanding the Output

### Discovery Phase
```
✓ Discovery planning complete (fast-path)
  └─ Means: Skipped LLM, used fast-path optimization
  └─ Cost: $0.00 (saved $0.015)

✓ Discovery planning complete (AI with CoT)
  └─ Means: Used LLM with Chain-of-Thought reasoning
  └─ Cost: $0.015
```

### Classification Phase
```
✓ Classification: DATABASE_SERVER (cached, hit rate: 50%)
  └─ Means: Retrieved from cache, no LLM call
  └─ Cost: $0.00 (saved $0.045)

✓ Classification: DATABASE_SERVER (confidence: 0.95)
  └─ Means: Used LLM with few-shot examples
  └─ Cost: $0.045
```

### Reporting Phase
```
✓ Report generated (template)
  └─ Means: Used template, no LLM call
  └─ Cost: $0.00 (saved $0.060)

✓ Report generated (AI synthesis)
  └─ Means: Used LLM for complex report
  └─ Cost: $0.060
```

---

## 🚀 Advanced Testing

### Test with Production Data
```bash
# Use real resource IPs from your environment
cd python/src
uv run python main.py

> Validate VM at <your-vm-ip>
> Validate Oracle DB at <your-db-ip>
> Validate MongoDB at <your-mongo-ip>
```

### Batch Testing Script
```python
# test_batch.py
import asyncio
from recovery_validation_agent import RecoveryValidationAgent

async def test_batch():
    agent = RecoveryValidationAgent()
    
    resources = [
        "VM at 192.168.1.10",
        "VM at 192.168.1.11",
        "Oracle DB at 10.0.1.50",
        "MongoDB at 10.0.2.100",
        "VM at 192.168.1.12"
    ]
    
    for resource in resources:
        print(f"\n{'='*60}")
        print(f"Testing: {resource}")
        print('='*60)
        await agent.process_request(f"Validate {resource}")
    
    # Check final stats
    stats = agent.classification_agent.get_cache_stats()
    print(f"\n\nFinal Cache Stats:")
    print(f"  Hit Rate: {stats['hit_rate']:.1f}%")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Savings: ~${stats['hits'] * 0.045:.2f}")

asyncio.run(test_batch())
```

---

## ✅ Success Indicators

After running tests, you should see:

1. **Fast-Path Usage**: 40-60% of simple VMs skip LLM for discovery
2. **Cache Hits**: 50-70% of classifications use cache after warmup
3. **Template Reports**: 30% of reports use templates instead of LLM
4. **Overall Savings**: 35-40% reduction in LLM costs
5. **Better Decisions**: More accurate classifications with few-shot examples
6. **Detailed Reports**: Structured findings, metrics, and action items

---

## 📞 Need Help?

1. Check logs: `tail -f recovery_validation.log`
2. Enable debug: `export LOG_LEVEL=DEBUG`
3. Review documentation:
   - `AGENTIC_WORKFLOW_ANALYSIS.md` - Complete analysis
   - `WORKFLOW_DECISION_MAP.md` - Visual guides
   - `IMPLEMENTATION_COMPLETE.md` - Implementation summary

**Happy Testing! 🎉**