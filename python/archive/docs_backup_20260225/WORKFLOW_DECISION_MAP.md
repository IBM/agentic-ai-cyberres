# Agentic Workflow Decision Map

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC WORKFLOW PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   DISCOVERY  │────▶│CLASSIFICATION│────▶│  VALIDATION  │
│              │     │              │     │              │
│  🤖 LLM      │     │  🤖 LLM      │     │  ⚙️  Rules   │
│  Planning    │     │  Analysis    │     │  Execution   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                   │
                                                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   REPORTING  │◀────│  EVALUATION  │◀────│              │
│              │     │              │     │              │
│  🤖 LLM      │     │  🤖 LLM      │     │              │
│  Synthesis   │     │  Assessment  │     │              │
└──────────────┘     └──────────────┘     └──────────────┘

Legend:
🤖 = LLM-Based Decision Making (AI-Powered)
⚙️  = Condition-Based Logic (Rule-Based)
```

---

## Decision Points Breakdown

### 1️⃣ DISCOVERY AGENT

**Decision**: What discovery methods to use?

```
Input: ResourceInfo (host, type, ssh_user, ssh_port)
       ↓
┌─────────────────────────────────────┐
│  Is it a simple VM?                 │
│  (no special requirements)          │
└─────────────────────────────────────┘
       │
       ├─ YES → ⚙️  FAST PATH (No LLM)
       │         Return: scan_ports=true
       │                 scan_processes=true
       │                 detect_applications=true
       │
       └─ NO  → 🤖 LLM DECISION
                 Prompt: Chain-of-Thought
                 Steps: 1. Analyze resource
                        2. Define goals
                        3. Select methods
                        4. Consider efficiency
                        5. Make decision
                 Return: DiscoveryPlan with reasoning
```

**Cost**: 
- Fast Path: $0.00 (40% of cases)
- LLM Path: $0.015 per resource (60% of cases)

---

### 2️⃣ CLASSIFICATION AGENT

**Decision**: What category is this resource?

```
Input: WorkloadDiscoveryResult (ports, processes, applications)
       ↓
┌─────────────────────────────────────┐
│  Is AI classification enabled?      │
│  (feature flag: ai_classification)  │
└─────────────────────────────────────┘
       │
       ├─ YES → 🤖 LLM DECISION
       │         ┌──────────────────────────┐
       │         │ Check cache first        │
       │         │ (Day 4 optimization)     │
       │         └──────────────────────────┘
       │              │
       │              ├─ CACHE HIT → Return cached result (50-70%)
       │              │
       │              └─ CACHE MISS → Call LLM
       │                   Prompt: Few-shot examples + data
       │                   Examples: Oracle DB, Web Server,
       │                             MongoDB, K8s, Unknown
       │                   Return: ClassificationAnalysis
       │                   Cache: Store result for reuse
       │
       └─ NO  → ⚙️  RULE-BASED FALLBACK
                 Logic: Port mapping (1521→Oracle)
                        Process matching (mongod→MongoDB)
                        Signature detection
                 Return: ResourceClassification
```

**Cost**:
- Cache Hit: $0.00 (50-70% after Day 4)
- LLM Call: $0.045 per resource (30-50%)
- Rule-Based: $0.00 (fallback)

---

### 3️⃣ VALIDATION AGENT

**Decision**: Which tools to execute?

```
Input: ResourceClassification
       ↓
┌─────────────────────────────────────┐
│  ⚙️  TOOL SELECTION (Rule-Based)    │
│  Map category → tool names          │
└─────────────────────────────────────┘
       │
       ├─ DATABASE_SERVER → oracle_db_validation
       │                    mongo_db_validation
       │
       ├─ WEB_SERVER → web_server_validation
       │
       ├─ VM → vm_validation
       │
       └─ etc.
       ↓
┌─────────────────────────────────────┐
│  ⚙️  TOOL EXECUTION (Rule-Based)    │
│  For each selected tool:            │
│    1. Call MCP tool                 │
│    2. Handle errors/timeouts        │
│    3. Aggregate results             │
└─────────────────────────────────────┘
       ↓
Output: List[ValidationResult]
```

**Cost**: $0.00 (no LLM, pure execution)

---

### 4️⃣ EVALUATION AGENT

**Decision**: Are validation results acceptable?

```
Input: ValidationResult + AcceptanceCriteria
       ↓
┌─────────────────────────────────────┐
│  Is AI evaluation enabled?          │
│  (feature flag: ai_evaluation)      │
└─────────────────────────────────────┘
       │
       ├─ YES → 🤖 LLM DECISION
       │         Prompt: Results + Criteria
       │         Analysis: - Compare actual vs expected
       │                   - Identify issues
       │                   - Assess risks
       │                   - Provide recommendations
       │         Return: EvaluationResult
       │                 (is_valid, confidence, issues)
       │
       └─ NO  → ⚙️  BASIC LOGIC
                 Check: error_count == 0
                 Return: Simple pass/fail
```

**Cost**: $0.030 per validation result

---

### 5️⃣ REPORTING AGENT

**Decision**: How to structure the report?

```
Input: All workflow data (discovery, classification, validation, evaluation)
       ↓
┌─────────────────────────────────────┐
│  Is AI reporting enabled?           │
│  (feature flag: ai_reporting)       │
└─────────────────────────────────────┘
       │
       ├─ YES → Check complexity
       │         │
       │         ├─ SIMPLE (< 3 resources, all valid)
       │         │  → ⚙️  TEMPLATE REPORT (No LLM)
       │         │     Use: Pre-defined template
       │         │     Cost: $0.00
       │         │
       │         └─ COMPLEX (many resources or issues)
       │            → 🤖 LLM SYNTHESIS
       │               Step 1: ⚙️  Calculate metrics
       │                       - Health score
       │                       - Failed checks
       │                       - Duration
       │                       - Coverage
       │               Step 2: ⚙️  Extract findings
       │                       - Critical issues
       │                       - Security findings
       │                       - Performance issues
       │               Step 3: 🤖 Generate report
       │                       Prompt: Metrics + Findings
       │                       Output: Executive summary
       │                               Insights
       │                               Recommendations
       │                               Action items
       │               Cost: $0.060
       │
       └─ NO  → ⚙️  TEMPLATE REPORT
                 Basic: Summary + raw data
                 Cost: $0.00
```

**Cost**:
- Simple Template: $0.00 (30% of cases)
- LLM Report: $0.060 (70% of cases)

---

## State Management (All Rule-Based)

```
⚙️  STATE MACHINE (No LLM)

INITIAL
   ↓
DISCOVERY ──────────────────┐
   ↓                        │
CLASSIFICATION              │
   ↓                        │
VALIDATION                  │
   ↓                        │
EVALUATION                  │
   ↓                        │
REPORTING                   │
   ↓                        │
COMPLETED ←─────────────────┘
   ↓
FAILED (if errors)

Transitions: Validated by state machine
Storage: In-memory workflow history
Cost: $0.00
```

---

## Feature Flags (All Rule-Based)

```
⚙️  FEATURE FLAG CHECKS (No LLM)

┌─────────────────────────────────────┐
│  Available Flags:                   │
│  - ai_classification                │
│  - ai_evaluation                    │
│  - ai_reporting                     │
│  - smart_llm_usage (Day 3)          │
│  - llm_cost_optimization (Day 3)    │
└─────────────────────────────────────┘
       ↓
Check: is_enabled(flag_name)
Logic: Dictionary lookup + env override
Cost: $0.00
```

---

## Cost Optimization Strategy

### Current Workflow (No Optimizations)
```
Resource 1: Discovery ($0.015) + Classification ($0.045) + Evaluation ($0.030) + Reporting ($0.060) = $0.150
Resource 2: Discovery ($0.015) + Classification ($0.045) + Evaluation ($0.030) + Reporting ($0.060) = $0.150
Resource 3: Discovery ($0.015) + Classification ($0.045) + Evaluation ($0.030) + Reporting ($0.060) = $0.150
───────────────────────────────────────────────────────────────────────────────────────────────────
Total (3 resources): $0.450
```

### Optimized Workflow (With All Improvements)
```
Resource 1: Discovery (Fast-path $0.00) + Classification (Cache miss $0.045) + Evaluation ($0.030) + Reporting (Template $0.00) = $0.075
Resource 2: Discovery (Fast-path $0.00) + Classification (Cache hit $0.00) + Evaluation ($0.030) + Reporting (Template $0.00) = $0.030
Resource 3: Discovery (LLM $0.015) + Classification (Cache hit $0.00) + Evaluation ($0.030) + Reporting (LLM $0.060) = $0.105
───────────────────────────────────────────────────────────────────────────────────────────────────
Total (3 resources): $0.210
Savings: $0.240 (53% reduction)
```

---

## Improvements Summary

### ✅ Completed (Days 1-2)

1. **Enhanced Reporting Models**
   - Added: Finding, MetricValue, Action models
   - Methods: _calculate_key_metrics(), _extract_findings()
   - Benefit: Structured, actionable reports

2. **Chain-of-Thought Prompting**
   - Location: Discovery Agent
   - Enhancement: 5-step reasoning process
   - Benefit: Better decision quality

3. **Few-Shot Learning**
   - Location: Classification Agent
   - Enhancement: 5 detailed examples
   - Benefit: 20-30% accuracy improvement

4. **Fast-Path Optimization**
   - Location: Discovery Agent
   - Logic: Skip LLM for simple VMs
   - Benefit: 40% cost reduction on discovery

### ⏳ Pending (Days 3-4)

5. **Smart LLM Usage**
   - Location: Reporting Agent
   - Logic: Template for simple cases
   - Benefit: 30% cost reduction on reporting

6. **Classification Caching**
   - Location: Classification Agent
   - Logic: Cache by ports/processes/apps
   - Benefit: 50-70% cost reduction on classification

---

## Testing Commands

### Test Discovery with CoT
```bash
cd python/src
uv run python -c "
from agents.discovery_agent import DiscoveryAgent
from models import ResourceInfo, ResourceType
import asyncio

async def test():
    agent = DiscoveryAgent()
    
    # Test 1: Simple VM (fast-path)
    simple_vm = ResourceInfo(
        host='simple-vm-01',
        resource_type=ResourceType.VM,
        ssh_user='admin',
        ssh_port=22
    )
    plan1 = await agent._create_plan(simple_vm)
    print(f'Simple VM Plan: {plan1.reasoning}')
    
    # Test 2: Complex resource (LLM)
    complex_vm = ResourceInfo(
        host='oracle-db-01',
        resource_type=ResourceType.VM,
        ssh_user='oracle',
        ssh_port=22,
        required_services=['oracle']
    )
    plan2 = await agent._create_plan(complex_vm)
    print(f'Complex VM Plan: {plan2.reasoning}')

asyncio.run(test())
"
```

### Test Classification with Few-Shot
```bash
cd python/src
uv run python -c "
from agents.classification_agent import ClassificationAgent
from models import WorkloadDiscoveryResult, PortInfo, ProcessInfo, ApplicationDetection
import asyncio

async def test():
    agent = ClassificationAgent()
    
    # Test: Oracle Database
    oracle_result = WorkloadDiscoveryResult(
        host='oracle-prod-01',
        ports=[
            PortInfo(port=1521, state='open', service='oracle'),
            PortInfo(port=5500, state='open', service='em')
        ],
        processes=[
            ProcessInfo(pid=1234, name='oracle', command='oracle'),
            ProcessInfo(pid=1235, name='tnslsnr', command='tnslsnr')
        ],
        applications=[
            ApplicationDetection(name='Oracle Database 19c', confidence=0.95)
        ]
    )
    
    classification = await agent.classify(oracle_result)
    print(f'Category: {classification.category}')
    print(f'Confidence: {classification.confidence:.2%}')
    print(f'Reasoning: {classification.reasoning}')

asyncio.run(test())
"
```

### Test Enhanced Reporting
```bash
cd python/src
uv run python -c "
from agents.reporting_agent import ReportingAgent
from models import ValidationResult
import asyncio

async def test():
    agent = ReportingAgent()
    
    # Test with failed validation
    results = [
        ValidationResult(
            resource_id='oracle-prod-01',
            validation_type='oracle_db_validation',
            is_valid=False,
            errors=['Connection timeout after 30s'],
            warnings=['High memory usage detected'],
            metadata={'port': 1521, 'service': 'oracle'}
        ),
        ValidationResult(
            resource_id='web-server-01',
            validation_type='web_server_validation',
            is_valid=True,
            errors=[],
            warnings=[],
            metadata={'port': 80, 'service': 'nginx'}
        )
    ]
    
    # Test metric calculation
    metrics = agent._calculate_key_metrics(results)
    print(f'Metrics calculated: {len(metrics)}')
    for metric in metrics:
        print(f'  - {metric.name}: {metric.value} {metric.unit} ({metric.status})')
    
    # Test finding extraction
    findings = agent._extract_findings(results)
    print(f'Findings extracted: {len(findings)}')
    for finding in findings:
        print(f'  - [{finding.severity}] {finding.title}')

asyncio.run(test())
"
```

---

## Quick Reference

### When LLM is Used (🤖)
1. **Discovery Planning** - Complex resources only (60% of cases)
2. **Classification** - When AI enabled and cache miss (30-50% of cases)
3. **Evaluation** - When AI enabled (100% of cases if enabled)
4. **Reporting** - Complex reports only (70% of cases)

### When Rules are Used (⚙️)
1. **Tool Selection** - Always (100%)
2. **Tool Execution** - Always (100%)
3. **State Management** - Always (100%)
4. **Feature Flags** - Always (100%)
5. **Fallback Classification** - When AI disabled or fails
6. **Simple Reporting** - Simple cases (30%)

### Cost Optimization Checklist
- [ ] Enable fast-path for simple VMs (40% savings on discovery)
- [ ] Implement classification caching (50-70% savings on classification)
- [ ] Use template reports for simple cases (30% savings on reporting)
- [ ] Monitor cache hit rates (target: 50-70%)
- [ ] Track LLM usage per workflow (target: 2.6 calls vs 4.0)
- [ ] Measure cost per workflow (target: $0.095 vs $0.150)

---

## Next Steps

1. **Complete Day 3**: Smart LLM usage in reporting
2. **Complete Day 4**: Classification caching infrastructure
3. **Test All Improvements**: Run test commands above
4. **Monitor Production**: Track costs and performance
5. **Iterate**: Adjust thresholds based on real data