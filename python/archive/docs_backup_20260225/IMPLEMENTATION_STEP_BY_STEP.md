# Step-by-Step Implementation Guide

**Purpose**: Practical, actionable steps to implement all improvements  
**Timeline**: 3 weeks  
**Approach**: Incremental, testable, production-safe

---

## Overview

This guide provides exact steps to implement all improvements identified in the analysis. Each step includes:
- ✅ What to do
- 📝 Exact code changes
- 🧪 How to test
- 🚀 How to deploy

---

## Week 1: Foundation & Quick Wins

### Day 1: Enhanced Reporting Models (4 hours)

#### Step 1.1: Add New Models to `models.py`

**File**: `python/src/models.py`

**Action**: Add these models at the end of the file:

```python
# Add after existing models

from typing import Literal

class Finding(BaseModel):
    """Individual finding with detailed context."""
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: Literal["security", "performance", "availability", "compliance", "configuration"]
    description: str
    impact: str
    evidence: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    affected_components: List[str] = Field(default_factory=list)

class MetricValue(BaseModel):
    """Metric with trend information."""
    name: str
    current: float
    previous: Optional[float] = None
    baseline: Optional[float] = None
    trend: Literal["improving", "stable", "degrading", "unknown"]
    change_percentage: Optional[float] = None
    unit: str
    threshold: Optional[float] = None
    status: Literal["good", "warning", "critical"]

class Action(BaseModel):
    """Actionable item with details."""
    title: str
    priority: Literal["critical", "high", "medium", "low"]
    description: str
    effort: str
    impact: str
    owner: Optional[str] = None
    timeline: str
    dependencies: List[str] = Field(default_factory=list)
```

**Test**:
```bash
cd python/src
python -c "from models import Finding, MetricValue, Action; print('Models imported successfully')"
```

---

#### Step 1.2: Update Reporting Agent

**File**: `python/src/agents/reporting_agent.py`

**Action 1**: Import new models (add at top):

```python
from models import Finding, MetricValue, Action
```

**Action 2**: Add method to calculate key metrics (add after `_generate_with_template`):

```python
def _calculate_key_metrics(
    self,
    validation_result: ResourceValidationResult,
    historical_results: Optional[List[ResourceValidationResult]] = None
) -> List[MetricValue]:
    """Calculate key metrics with trends."""
    metrics = []
    
    # Health Score Metric
    current_score = validation_result.score
    previous_score = historical_results[-1].score if historical_results else None
    
    trend = "unknown"
    change_pct = None
    if previous_score is not None:
        change_pct = ((current_score - previous_score) / previous_score) * 100
        if change_pct > 5:
            trend = "improving"
        elif change_pct < -5:
            trend = "degrading"
        else:
            trend = "stable"
    
    status = "good" if current_score >= 80 else "warning" if current_score >= 60 else "critical"
    
    metrics.append(MetricValue(
        name="Health Score",
        current=current_score,
        previous=previous_score,
        trend=trend,
        change_percentage=change_pct,
        unit="points",
        threshold=80.0,
        status=status
    ))
    
    # Failed Checks Metric
    metrics.append(MetricValue(
        name="Failed Checks",
        current=float(validation_result.failed_checks),
        previous=float(historical_results[-1].failed_checks) if historical_results else None,
        trend="improving" if historical_results and validation_result.failed_checks < historical_results[-1].failed_checks else "stable",
        unit="checks",
        threshold=0.0,
        status="critical" if validation_result.failed_checks > 0 else "good"
    ))
    
    return metrics
```

**Action 3**: Add method to extract findings:

```python
def _extract_findings(
    self,
    validation_result: ResourceValidationResult,
    evaluation: Optional[OverallEvaluation] = None
) -> List[Finding]:
    """Extract findings from validation results."""
    findings = []
    
    for check in validation_result.checks:
        if check.status == ValidationStatus.FAIL:
            severity = "high" if validation_result.failed_checks <= 2 else "medium"
            
            finding = Finding(
                title=check.check_name,
                severity=severity,
                category="configuration",
                description=check.message or "Check failed",
                impact=f"Check '{check.check_name}' failed, which may impact system reliability",
                evidence=[
                    f"Expected: {check.expected}" if check.expected else "",
                    f"Actual: {check.actual}" if check.actual else ""
                ],
                recommendations=[
                    f"Investigate {check.check_name}",
                    "Review system logs",
                    "Verify configuration"
                ],
                affected_components=[check.check_name]
            )
            findings.append(finding)
    
    return findings
```

**Test**:
```bash
cd python/src
python -c "from agents.reporting_agent import ReportingAgent; print('Updated reporting agent imported')"
```

---

### Day 2: Chain-of-Thought Prompts (6 hours)

#### Step 2.1: Update Discovery Agent Prompt

**File**: `python/src/agents/discovery_agent.py`

**Action**: Replace `_create_plan` method:

```python
async def _create_plan(self, resource: ResourceInfo) -> DiscoveryPlan:
    """Create discovery plan using AI with Chain-of-Thought."""
    
    prompt = f"""# Discovery Planning Task with Chain-of-Thought Reasoning

## Resource Context
- **Host**: {resource.host}
- **Type**: {resource.resource_type.value}
- **SSH Access**: {resource.ssh_user}@{resource.host}:{resource.ssh_port}

## Available Discovery Methods
1. **Port Scanning**: Identify open ports and services (fast, non-invasive)
2. **Process Scanning**: List running processes (requires SSH, more detailed)
3. **Application Detection**: Identify applications from ports/processes (intelligent analysis)

## Your Task: Create Discovery Plan with Step-by-Step Reasoning

Please think through this step-by-step:

### Step 1: Resource Analysis
What do we know about this resource? What type of workload might it run?

### Step 2: Discovery Goals
What specific information would be most valuable to discover?

### Step 3: Method Selection
Which discovery methods should we use and why?

### Step 4: Efficiency Considerations
How can we balance thoroughness with execution time?

### Step 5: Final Decision
Based on the above reasoning, what's your discovery plan?

## Example Reasoning:
```
Step 1: This is a VM with SSH access. General-purpose server.
Step 2: Need to identify running applications and services.
Step 3: Use all three methods for comprehensive discovery.
Step 4: Run port scan first (fast), then processes, then detection.
Step 5: Plan: scan_ports=true, scan_processes=true, detect_applications=true
Reasoning: Comprehensive discovery needed for unknown VM.
```

Now provide YOUR reasoning and plan."""

    try:
        result = await self.planning_agent.run(prompt)
        return result.data
    except Exception as e:
        logger.warning(f"Failed to create AI plan, using default: {e}")
        return DiscoveryPlan(
            scan_ports=True,
            scan_processes=True,
            detect_applications=True,
            reasoning="Default plan: comprehensive discovery (AI failed)"
        )
```

**Test**:
```bash
cd python/src
python -c "
from agents.discovery_agent import DiscoveryAgent
from models import VMResourceInfo, ResourceType
import asyncio

async def test():
    agent = DiscoveryAgent()
    resource = VMResourceInfo(
        resource_type=ResourceType.VM,
        host='test.example.com',
        ssh_user='admin'
    )
    plan = await agent._create_plan(resource)
    print(f'Plan created: {plan.reasoning[:100]}...')

asyncio.run(test())
"
```

---

#### Step 2.2: Update Classification Agent Prompt

**File**: `python/src/agents/classification_agent.py`

**Action**: Add few-shot examples constant at top of file:

```python
CLASSIFICATION_EXAMPLES = """
## Example Classifications for Reference

### Example 1: Oracle Database Server
**Input**:
- Ports: 1521 (Oracle), 22 (SSH)
- Processes: oracle, pmon, smon, tnslsnr
- Applications: Oracle Database 19c (confidence: 0.95)

**Reasoning**:
1. Port 1521 is Oracle's default listener port
2. Multiple Oracle-specific processes (pmon, smon, tnslsnr)
3. High-confidence application detection
4. No web server indicators

**Output**:
- Category: DATABASE_SERVER
- Confidence: 0.95
- Primary: Oracle Database 19c
- Risk Level: medium

### Example 2: Web Server
**Input**:
- Ports: 80 (HTTP), 443 (HTTPS), 22 (SSH)
- Processes: nginx, nginx worker
- Applications: Nginx (0.92)

**Reasoning**:
1. Standard HTTP/HTTPS ports
2. Nginx processes running
3. No database or application server indicators
4. Clear web server pattern

**Output**:
- Category: WEB_SERVER
- Confidence: 0.92
- Primary: Nginx
- Risk Level: low
"""
```

**Action**: Update `_build_classification_prompt` method:

```python
def _build_classification_prompt(
    self,
    discovery_result: WorkloadDiscoveryResult
) -> str:
    """Build prompt with few-shot examples and CoT."""
    
    prompt_parts = [
        CLASSIFICATION_EXAMPLES,
        "\n## Your Classification Task",
        "\nNow classify this NEW resource using the same reasoning approach:",
        f"\n### Resource Information",
        f"Host: {discovery_result.host}",
        f"\n### Open Ports ({len(discovery_result.ports)})"
    ]
    
    # Add port information
    if discovery_result.ports:
        for port in discovery_result.ports[:10]:
            service = port.service or "unknown"
            prompt_parts.append(f"- Port {port.port}/{port.protocol}: {service}")
    
    # Add process information
    if discovery_result.processes:
        prompt_parts.append(f"\n### Running Processes ({len(discovery_result.processes)})")
        for proc in discovery_result.processes[:10]:
            prompt_parts.append(f"- {proc.name}")
    
    # Add applications
    if discovery_result.applications:
        prompt_parts.append(f"\n### Detected Applications ({len(discovery_result.applications)})")
        for app in discovery_result.applications:
            prompt_parts.append(f"- {app.name} (confidence: {app.confidence:.0%})")
    
    prompt_parts.extend([
        "\n## Your Analysis (Step-by-Step)",
        "\n### Step 1: Initial Observations",
        "What stands out about this resource?",
        "\n### Step 2: Pattern Matching",
        "Does this match any known patterns?",
        "\n### Step 3: Confidence Assessment",
        "How confident are we? Why?",
        "\n### Step 4: Final Classification",
        "Provide your structured classification with reasoning."
    ])
    
    return "\n".join(prompt_parts)
```

**Test**:
```bash
cd python/src
python -c "from agents.classification_agent import ClassificationAgent, CLASSIFICATION_EXAMPLES; print('Examples loaded:', len(CLASSIFICATION_EXAMPLES), 'chars')"
```

---

### Day 3: Smart LLM Usage (4 hours)

#### Step 3.1: Add Feature Flag

**File**: `python/src/feature_flags.py`

**Action**: Update `DEFAULT_FLAGS` dictionary:

```python
DEFAULT_FLAGS = {
    # ... existing flags ...
    'smart_llm_usage': True,  # NEW: Use LLM only when beneficial
    'llm_cost_optimization': True,  # NEW: Optimize token usage
}
```

**Test**:
```bash
cd python/src
python -c "from feature_flags import FeatureFlags; ff = FeatureFlags(); print('smart_llm_usage:', ff.is_enabled('smart_llm_usage'))"
```

---

#### Step 3.2: Add Fast-Path to Discovery Agent

**File**: `python/src/agents/discovery_agent.py`

**Action**: Update `_create_plan` method to add fast-path:

```python
async def _create_plan(self, resource: ResourceInfo) -> DiscoveryPlan:
    """Create discovery plan with smart LLM usage."""
    
    # Fast-path for simple VM discovery
    if (resource.resource_type == ResourceType.VM and 
        not hasattr(resource, 'required_services') or not resource.required_services):
        
        logger.info("Using fast-path discovery plan (simple VM)")
        return DiscoveryPlan(
            scan_ports=True,
            scan_processes=True,
            detect_applications=True,
            reasoning="Standard VM discovery (fast-path - no LLM needed)"
        )
    
    # Use LLM for complex cases
    logger.info("Using AI-powered discovery planning (complex case)")
    prompt = f"""# Discovery Planning Task with Chain-of-Thought Reasoning
    ... (rest of prompt as before) ...
    """
    
    try:
        result = await self.planning_agent.run(prompt)
        return result.data
    except Exception as e:
        logger.warning(f"Failed to create AI plan, using default: {e}")
        return DiscoveryPlan(
            scan_ports=True,
            scan_processes=True,
            detect_applications=True,
            reasoning="Default plan: comprehensive discovery (AI failed)"
        )
```

**Test**:
```bash
cd python/src
python -c "
from agents.discovery_agent import DiscoveryAgent
from models import VMResourceInfo, ResourceType
import asyncio

async def test():
    agent = DiscoveryAgent()
    
    # Simple VM - should use fast-path
    simple_vm = VMResourceInfo(
        resource_type=ResourceType.VM,
        host='simple.example.com',
        ssh_user='admin'
    )
    plan = await agent._create_plan(simple_vm)
    print('Simple VM plan:', plan.reasoning)
    assert 'fast-path' in plan.reasoning.lower()

asyncio.run(test())
"
```

---

### Day 4: Classification Caching (4 hours)

#### Step 4.1: Add Caching to Classification Agent

**File**: `python/src/agents/classification_agent.py`

**Action 1**: Add imports at top:

```python
import time
import hashlib
import json
```

**Action 2**: Update `__init__` method:

```python
def __init__(
    self,
    mcp_client: Optional[any] = None,
    config: Optional[AgentConfig] = None,
    tool_coordinator: Optional[ToolCoordinator] = None,
    state_manager: Optional[StateManager] = None,
    feature_flags: Optional[FeatureFlags] = None
):
    """Initialize classification agent with caching."""
    super().__init__(
        mcp_client=mcp_client or object(),
        name="classification",
        tool_coordinator=tool_coordinator,
        state_manager=state_manager,
        feature_flags=feature_flags
    )
    
    self.config = config or AgentConfig()
    
    # Create AI classification agent
    self.ai_agent = self.config.create_agent(
        result_type=ClassificationAnalysis,
        system_prompt=self.SYSTEM_PROMPT
    )
    
    # Fallback to rule-based classifier
    self.fallback_classifier = ApplicationClassifier()
    
    # NEW: Add caching
    self.classification_cache = {}
    self.cache_ttl = 3600  # 1 hour
    
    self.log_step("Classification agent initialized with caching")
```

**Action 3**: Add cache methods:

```python
def _get_cache_key(self, discovery_result: WorkloadDiscoveryResult) -> str:
    """Generate cache key from discovery data."""
    # Create deterministic key from applications
    app_names = sorted([app.name for app in discovery_result.applications])
    key_data = {
        'host': discovery_result.host,
        'apps': app_names,
        'port_count': len(discovery_result.ports),
        'process_count': len(discovery_result.processes)
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

def _get_from_cache(self, cache_key: str) -> Optional[ResourceClassification]:
    """Get classification from cache if valid."""
    if cache_key in self.classification_cache:
        entry = self.classification_cache[cache_key]
        if time.time() - entry['timestamp'] < self.cache_ttl:
            self.log_step("Cache hit for classification", level="debug")
            return entry['classification']
        else:
            # Expired - remove
            del self.classification_cache[cache_key]
    return None

def _save_to_cache(self, cache_key: str, classification: ResourceClassification):
    """Save classification to cache."""
    self.classification_cache[cache_key] = {
        'classification': classification,
        'timestamp': time.time()
    }
    self.log_step(f"Cached classification (cache size: {len(self.classification_cache)})", level="debug")
```

**Action 4**: Update `classify` method to use cache:

```python
async def classify(
    self,
    discovery_result: WorkloadDiscoveryResult,
    workflow_id: Optional[str] = None
) -> ResourceClassification:
    """Classify resource with caching."""
    self.log_step(f"Classifying resource: {discovery_result.host}")
    
    # NEW: Check cache first
    cache_key = self._get_cache_key(discovery_result)
    cached = self._get_from_cache(cache_key)
    if cached:
        self.log_step("Using cached classification")
        return cached
    
    # ... existing classification logic ...
    
    # Classify (existing code)
    use_ai = (
        self.feature_flags and
        self.feature_flags.is_enabled("ai_classification")
    )
    
    if use_ai:
        try:
            classification = await self._classify_with_ai(discovery_result)
        except Exception as e:
            self.log_step(f"AI classification failed: {e}", level="warning")
            classification = self._classify_with_rules(discovery_result)
    else:
        classification = self._classify_with_rules(discovery_result)
    
    # NEW: Save to cache
    self._save_to_cache(cache_key, classification)
    
    return classification
```

**Test**:
```bash
cd python/src
python -c "
from agents.classification_agent import ClassificationAgent
from models import WorkloadDiscoveryResult, ApplicationDetection
from datetime import datetime
import asyncio

async def test():
    agent = ClassificationAgent()
    
    # Create test discovery result
    discovery = WorkloadDiscoveryResult(
        host='test.example.com',
        ports=[],
        processes=[],
        applications=[
            ApplicationDetection(name='Oracle', confidence=0.9, detection_method='test')
        ],
        discovery_time=datetime.now()
    )
    
    # First call - should classify
    result1 = await agent.classify(discovery)
    print('First call:', result1.category)
    
    # Second call - should use cache
    result2 = await agent.classify(discovery)
    print('Second call (cached):', result2.category)
    
    print('Cache size:', len(agent.classification_cache))

asyncio.run(test())
"
```

---

### Day 5: Testing & Integration (4 hours)

#### Step 5.1: Create Integration Test

**File**: `python/src/test_week1_improvements.py` (NEW FILE)

```python
"""
Integration tests for Week 1 improvements.
"""

import pytest
import asyncio
from datetime import datetime

from agents.discovery_agent import DiscoveryAgent
from agents.classification_agent import ClassificationAgent
from agents.reporting_agent import ReportingAgent
from models import (
    VMResourceInfo,
    ResourceType,
    WorkloadDiscoveryResult,
    ApplicationDetection,
    ResourceValidationResult,
    ValidationStatus,
    CheckResult
)

@pytest.mark.asyncio
async def test_discovery_fast_path():
    """Test fast-path discovery for simple VMs."""
    agent = DiscoveryAgent()
    
    simple_vm = VMResourceInfo(
        resource_type=ResourceType.VM,
        host='simple.example.com',
        ssh_user='admin'
    )
    
    plan = await agent._create_plan(simple_vm)
    
    assert plan.scan_ports == True
    assert plan.scan_processes == True
    assert plan.detect_applications == True
    assert 'fast-path' in plan.reasoning.lower()
    print("✅ Fast-path discovery works")

@pytest.mark.asyncio
async def test_classification_caching():
    """Test classification caching."""
    agent = ClassificationAgent()
    
    discovery = WorkloadDiscoveryResult(
        host='test.example.com',
        ports=[],
        processes=[],
        applications=[
            ApplicationDetection(name='Oracle', confidence=0.9, detection_method='test')
        ],
        discovery_time=datetime.now()
    )
    
    # First call
    result1 = await agent.classify(discovery)
    cache_size_1 = len(agent.classification_cache)
    
    # Second call - should use cache
    result2 = await agent.classify(discovery)
    cache_size_2 = len(agent.classification_cache)
    
    assert result1.category == result2.category
    assert cache_size_1 == cache_size_2 == 1
    print("✅ Classification caching works")

def test_enhanced_reporting_models():
    """Test new reporting models."""
    from models import Finding, MetricValue, Action
    
    finding = Finding(
        title="Test Finding",
        severity="high",
        category="security",
        description="Test description",
        impact="High impact",
        evidence=["Evidence 1"],
        recommendations=["Fix it"],
        affected_components=["Component 1"]
    )
    
    metric = MetricValue(
        name="Health Score",
        current=85.0,
        previous=80.0,
        trend="improving",
        change_percentage=6.25,
        unit="points",
        threshold=80.0,
        status="good"
    )
    
    action = Action(
        title="Fix issue",
        priority="high",
        description="Fix the issue",
        effort="2 hours",
        impact="High",
        timeline="24 hours",
        dependencies=[]
    )
    
    assert finding.severity == "high"
    assert metric.trend == "improving"
    assert action.priority == "high"
    print("✅ Enhanced reporting models work")

def test_reporting_agent_metrics():
    """Test reporting agent metric calculation."""
    agent = ReportingAgent()
    
    validation_result = ResourceValidationResult(
        resource_type=ResourceType.VM,
        resource_host="test.example.com",
        overall_status=ValidationStatus.PASS,
        score=85,
        checks=[
            CheckResult(
                check_id="test_1",
                check_name="Test Check",
                status=ValidationStatus.PASS
            )
        ],
        execution_time_seconds=10.0
    )
    
    metrics = agent._calculate_key_metrics(validation_result)
    
    assert len(metrics) >= 2
    assert metrics[0].name == "Health Score"
    assert metrics[0].current == 85.0
    print("✅ Reporting agent metrics work")

if __name__ == "__main__":
    print("\n🧪 Running Week 1 Integration Tests\n")
    
    # Run async tests
    asyncio.run(test_discovery_fast_path())
    asyncio.run(test_classification_caching())
    
    # Run sync tests
    test_enhanced_reporting_models()
    test_reporting_agent_metrics()
    
    print("\n✅ All Week 1 tests passed!\n")
```

**Run Tests**:
```bash
cd python/src
python test_week1_improvements.py
```

---

## Week 2: Performance & Advanced Features

### Day 6-7: Parallel Execution (2 days)

#### Step 6.1: Update Orchestrator for Parallel Execution

**File**: `python/src/agents/orchestrator.py`

**Action**: Add parallel execution method:

```python
import asyncio

async def _execute_validations_parallel(
    self,
    request: ValidationRequest,
    plan: ValidationPlan,
    discovery_result: Optional[WorkloadDiscoveryResult]
) -> ResourceValidationResult:
    """Execute validation checks in parallel where possible."""
    
    start_time = time.time()
    
    # Group checks by priority
    high_priority = [c for c in plan.checks if c.priority <= 2]
    low_priority = [c for c in plan.checks if c.priority > 2]
    
    results = []
    
    # Execute high-priority checks sequentially (they may have dependencies)
    logger.info(f"Executing {len(high_priority)} high-priority checks sequentially")
    for check_def in high_priority:
        result = await self._execute_single_check(check_def)
        results.append(result)
    
    # Execute low-priority checks in parallel
    if low_priority and self.feature_flags and self.feature_flags.is_enabled('parallel_tool_execution'):
        logger.info(f"Executing {len(low_priority)} low-priority checks in parallel")
        
        tasks = [self._execute_single_check(check_def) for check_def in low_priority]
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in parallel_results:
            if isinstance(result, Exception):
                logger.error(f"Parallel check failed: {result}")
                results.append(self._create_error_result(str(result)))
            else:
                results.append(result)
    else:
        # Fallback to sequential
        for check_def in low_priority:
            result = await self._execute_single_check(check_def)
            results.append(result)
    
    # Calculate overall status
    overall_status, score = self._calculate_overall_status(results)
    execution_time = time.time() - start_time
    
    return ResourceValidationResult(
        resource_type=request.resource_info.resource_type,
        resource_host=request.resource_info.host,
        overall_status=overall_status,
        score=score,
        checks=results,
        discovery_info=discovery_result.model_dump() if discovery_result else None,
        execution_time_seconds=execution_time
    )

async def _execute_single_check(self, check_def) -> CheckResult:
    """Execute a single validation check."""
    try:
        result = await self.mcp_client.call_tool(
            check_def.mcp_tool,
            check_def.tool_args
        )
        return self._interpret_check_result(check_def, result)
    except Exception as e:
        logger.error(f"Check {check_def.check_id} failed: {e}")
        return CheckResult(
            check_id=check_def.check_id,
            check_name=check_def.check_name,
            status=ValidationStatus.ERROR,
            message=f"Check execution failed: {str(e)}"
        )

def _create_error_result(self, error_msg: str) -> CheckResult:
    """Create error result for failed check."""
    return CheckResult(
        check_id="error",
        check_name="Error",
        status=ValidationStatus.ERROR,
        message=error_msg
    )
```

**Test**:
```bash
cd python/src
python -c "from agents.orchestrator import ValidationOrchestrator; print('Parallel execution methods added')"
```

---

### Day 8-9: Self-Consistency (2 days)

#### Step 8.1: Add Self-Consistency to Evaluation Agent

**File**: `python/src/agents/evaluation_agent.py`

**Action**: Add self-consistency method:

```python
async def evaluate_with_consistency(
    self,
    validation_result: ResourceValidationResult,
    discovery_result: Optional[WorkloadDiscoveryResult] = None,
    classification: Optional[ResourceClassification] = None,
    num_samples: int = 3
) -> OverallEvaluation:
    """Evaluate with self-consistency checking."""
    
    logger.info(f"Evaluating with self-consistency (n={num_samples})")
    
    # Generate multiple evaluations
    evaluations = []
    for i in range(num_samples):
        prompt = self._build_evaluation_prompt(
            validation_result,
            discovery_result,
            classification
        )
        
        result = await self.evaluation_agent.run(prompt)
        evaluations.append(result.data)
    
    # Calculate consistency
    consistency_score = self._calculate_consistency(evaluations)
    logger.info(f"Consistency score: {consistency_score:.2f}")
    
    if consistency_score < 0.7:
        logger.warning(f"Low consistency ({consistency_score:.2f}), generating additional sample")
        # One more sample
        result = await self.evaluation_agent.run(prompt)
        evaluations.append(result.data)
        consistency_score = self._calculate_consistency(evaluations)
    
    # Aggregate
    final_evaluation = self._aggregate_evaluations(evaluations)
    final_evaluation.confidence = consistency_score
    
    return final_evaluation

def _calculate_consistency(self, evaluations: List[OverallEvaluation]) -> float:
    """Calculate consistency score."""
    # Health rating consistency
    health_ratings = [e.overall_health for e in evaluations]
    health_consistency = 1.0 - (len(set(health_ratings)) - 1) / len(health_ratings)
    
    # Critical issues consistency
    critical_counts = [len(e.critical_issues) for e in evaluations]
    if max(critical_counts) > 0:
        critical_consistency = 1.0 - (max(critical_counts) - min(critical_counts)) / max(critical_counts)
    else:
        critical_consistency = 1.0
    
    # Weighted average
    return health_consistency * 0.6 + critical_consistency * 0.4

def _aggregate_evaluations(self, evaluations: List[OverallEvaluation]) -> OverallEvaluation:
    """Aggregate multiple evaluations."""
    # Majority vote for health
    from collections import Counter
    health_votes = Counter(e.overall_health for e in evaluations)
    final_health = health_votes.most_common(1)[0][0]
    
    # Union of critical issues
    all_critical = []
    for eval in evaluations:
        all_critical.extend(eval.critical_issues)
    unique_critical = list(set(all_critical))
    
    # Intersection of recommendations
    common_recs = set(evaluations[0].recommendations)
    for eval in evaluations[1:]:
        common_recs &= set(eval.recommendations)
    
    return OverallEvaluation(
        overall_health=final_health,
        confidence=self._calculate_consistency(evaluations),
        summary=evaluations[0].summary,  # Use first
        critical_issues=unique_critical,
        recommendations=list(common_recs),
        check_assessments=evaluations[0].check_assessments,
        next_steps=evaluations[0].next_steps
    )
```

---

## Week 3: Production Deployment

### Day 10: Enable Feature Flags

**Action**: Update `.env` file or environment variables:

```bash
# Add to .env
FEATURE_FLAG_SMART_LLM_USAGE=true
FEATURE_FLAG_AI_CLASSIFICATION=true
FEATURE_FLAG_AI_REPORTING=true
FEATURE_FLAG_PARALLEL_TOOL_EXECUTION=true
```

### Day 11-12: Testing & Monitoring

**Create monitoring script**: `python/src/monitor_improvements.py`

```python
"""Monitor improvement metrics."""

import json
from datetime import datetime
from agents.classification_agent import ClassificationAgent
from agents.reporting_agent import ReportingAgent

def monitor_metrics():
    """Monitor and report metrics."""
    
    # Classification cache stats
    classifier = ClassificationAgent()
    cache_stats = {
        'cache_size': len(classifier.classification_cache),
        'cache_ttl': classifier.cache_ttl
    }
    
    print("\n📊 Improvement Metrics")
    print("=" * 50)
    print(f"Classification Cache Size: {cache_stats['cache_size']}")
    print(f"Cache TTL: {cache_stats['cache_ttl']}s")
    print("=" * 50)

if __name__ == "__main__":
    monitor_metrics()
```

---

## Quick Start Commands

### Setup
```bash
cd python/src

# Install dependencies (if needed)
pip install -r requirements.txt

# Run tests
python test_week1_improvements.py
```

### Deploy Week 1
```bash
# 1. Update models
python -c "from models import Finding, MetricValue, Action; print('✅ Models ready')"

# 2. Test discovery
python -c "from agents.discovery_agent import DiscoveryAgent; print('✅ Discovery ready')"

# 3. Test classification
python -c "from agents.classification_agent import ClassificationAgent; print('✅ Classification ready')"

# 4. Test reporting
python -c "from agents.reporting_agent import ReportingAgent; print('✅ Reporting ready')"

# 5. Run integration tests
python test_week1_improvements.py
```

### Monitor
```bash
# Check metrics
python monitor_improvements.py

# Check logs
tail -f logs/agent.log
```

---

## Rollback Plan

If issues occur:

1. **Disable feature flags**:
```bash
export FEATURE_FLAG_SMART_LLM_USAGE=false
export FEATURE_FLAG_AI_CLASSIFICATION=false
```

2. **Revert code changes**:
```bash
git revert <commit-hash>
```

3. **Clear cache**:
```python
from agents.classification_agent import ClassificationAgent
agent = ClassificationAgent()
agent.classification_cache.clear()
```

---

## Success Criteria

### Week 1
- ✅ Enhanced reporting models working
- ✅ Chain-of-Thought prompts implemented
- ✅ Smart LLM usage reducing costs by 30%
- ✅ Classification caching with 50%+ hit rate

### Week 2
- ✅ Parallel execution 30% faster
- ✅ Self-consistency improving accuracy
- ✅ All tests passing

### Week 3
- ✅ Production deployment successful
- ✅ Monitoring in place
- ✅ User feedback positive

---

## Support & Troubleshooting

### Common Issues

**Issue**: Import errors
**Solution**: Check Python path and installed packages

**Issue**: Cache not working
**Solution**: Check feature flags are enabled

**Issue**: Tests failing
**Solution**: Check MCP client connection

### Get Help

1. Check logs: `tail -f logs/agent.log`
2. Run diagnostics: `python monitor_improvements.py`
3. Review documentation in analysis files

---

**Implementation Status**: Ready to Start  
**Estimated Time**: 3 weeks  
**Confidence**: High
