# Pydantic AI Integration Plan

## Overview

This document outlines how to integrate [Pydantic AI](https://ai.pydantic.dev/) into the infrastructure validation workflow to create a more intelligent, structured, and maintainable agentic system.

## Why Pydantic AI?

### Key Benefits

1. **Structured Outputs**: Type-safe responses with Pydantic models
2. **Tool Integration**: Native support for function calling and tool use
3. **Multi-LLM Support**: Works with OpenAI, Anthropic, Gemini, Groq, etc.
4. **Dependency Injection**: Clean architecture with context management
5. **Streaming Support**: Real-time progress updates
6. **Validation**: Built-in data validation with Pydantic
7. **Type Safety**: Full type hints and IDE support

### Perfect Fit for Our Use Case

- **Workload Discovery**: Agent can intelligently decide which discovery tools to use
- **Classification**: Structured output ensures consistent resource categorization
- **Validation Planning**: Agent generates validation plans based on context
- **Result Evaluation**: Type-safe evaluation with clear success/failure criteria
- **Recommendations**: LLM-powered insights based on validation results

## Architecture with Pydantic AI

### High-Level Design

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

# Define structured outputs
class WorkloadDiscoveryResult(BaseModel):
    host: str
    applications: list[ApplicationDetection]
    confidence: float
    recommended_validations: list[str]

class ValidationResult(BaseModel):
    overall_status: str
    score: int
    checks: list[CheckResult]
    recommendations: list[str]

# Create specialized agents
discovery_agent = Agent(
    'openai:gpt-4',
    result_type=WorkloadDiscoveryResult,
    system_prompt="You are an infrastructure discovery expert..."
)

validation_agent = Agent(
    'openai:gpt-4',
    result_type=ValidationResult,
    system_prompt="You are an infrastructure validation expert..."
)
```

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│  (Coordinates overall workflow, delegates to specialists)    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Discovery   │   │ Validation   │   │  Evaluation  │
│    Agent     │   │    Agent     │   │    Agent     │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   [MCP Tools]        [MCP Tools]        [Criteria]
```

## Implementation Plan

### Phase 1: Core Agent Setup

#### 1.1 Install Dependencies

```bash
# Add to requirements.txt
pydantic-ai>=0.0.14
pydantic>=2.0.0
openai>=1.0.0  # or anthropic, google-generativeai, etc.
```

#### 1.2 Create Base Agent Configuration

```python
# python/src/agents/base.py

from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
from typing import Optional
import os

class AgentConfig:
    """Configuration for Pydantic AI agents."""
    
    def __init__(
        self,
        model: KnownModelName = "openai:gpt-4",
        api_key: Optional[str] = None
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def create_agent(
        self,
        result_type,
        system_prompt: str,
        tools: list = None
    ) -> Agent:
        """Create a configured agent."""
        return Agent(
            self.model,
            result_type=result_type,
            system_prompt=system_prompt,
            tools=tools or []
        )
```

### Phase 2: Discovery Agent

#### 2.1 Discovery Agent with Tools

```python
# python/src/agents/discovery_agent.py

from pydantic_ai import Agent, RunContext, Tool
from pydantic import BaseModel, Field
from typing import List, Optional
from ..mcp_client import MCPClient

class PortScanResult(BaseModel):
    """Result of port scanning."""
    port: int
    service: Optional[str] = None
    state: str = "open"

class ProcessInfo(BaseModel):
    """Information about a running process."""
    pid: int
    name: str
    cmdline: str

class ApplicationDetection(BaseModel):
    """Detected application."""
    name: str
    version: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    category: str
    evidence: dict = Field(default_factory=dict)

class WorkloadDiscoveryResult(BaseModel):
    """Complete workload discovery result."""
    host: str
    ports: List[PortScanResult]
    processes: List[ProcessInfo]
    applications: List[ApplicationDetection]
    primary_application: Optional[ApplicationDetection] = None
    recommended_validations: List[str]
    confidence: float = Field(ge=0.0, le=1.0)

class DiscoveryContext(BaseModel):
    """Context for discovery operations."""
    mcp_client: MCPClient
    host: str
    ssh_user: str
    ssh_password: Optional[str] = None
    ssh_key_path: Optional[str] = None

# Define tools for the agent
async def scan_ports_tool(
    ctx: RunContext[DiscoveryContext],
    scan_type: str = "common"
) -> dict:
    """Scan ports on the target host.
    
    Args:
        scan_type: Type of scan - 'common' for common ports, 'full' for all ports
    """
    result = await ctx.deps.mcp_client.workload_scan_ports(
        host=ctx.deps.host,
        ssh_user=ctx.deps.ssh_user,
        ssh_password=ctx.deps.ssh_password,
        ssh_key_path=ctx.deps.ssh_key_path,
        scan_type=scan_type
    )
    return result

async def scan_processes_tool(
    ctx: RunContext[DiscoveryContext]
) -> dict:
    """Scan running processes on the target host."""
    result = await ctx.deps.mcp_client.workload_scan_processes(
        host=ctx.deps.host,
        ssh_user=ctx.deps.ssh_user,
        ssh_password=ctx.deps.ssh_password,
        ssh_key_path=ctx.deps.ssh_key_path
    )
    return result

async def detect_applications_tool(
    ctx: RunContext[DiscoveryContext],
    ports: List[dict],
    processes: List[dict]
) -> dict:
    """Detect applications from port and process data."""
    result = await ctx.deps.mcp_client.workload_detect_applications(
        host=ctx.deps.host,
        ports=ports,
        processes=processes
    )
    return result

# Create the discovery agent
discovery_agent = Agent(
    'openai:gpt-4',
    result_type=WorkloadDiscoveryResult,
    system_prompt="""You are an expert infrastructure discovery agent.

Your task is to discover what applications and services are running on a target host.

Process:
1. Scan ports to identify open services
2. Scan processes to identify running applications
3. Detect applications by correlating port and process data
4. Classify the primary application type
5. Recommend appropriate validation strategies

Be thorough but efficient. Use common port scanning first, only do full scans if needed.
Provide confidence scores based on the strength of evidence.
""",
    tools=[scan_ports_tool, scan_processes_tool, detect_applications_tool]
)

async def discover_workload(
    host: str,
    ssh_user: str,
    ssh_password: Optional[str] = None,
    ssh_key_path: Optional[str] = None,
    mcp_client: MCPClient = None
) -> WorkloadDiscoveryResult:
    """Discover workloads on a host using the discovery agent.
    
    Args:
        host: Target host
        ssh_user: SSH username
        ssh_password: SSH password (optional)
        ssh_key_path: SSH key path (optional)
        mcp_client: MCP client instance
    
    Returns:
        WorkloadDiscoveryResult with discovered applications
    """
    context = DiscoveryContext(
        mcp_client=mcp_client,
        host=host,
        ssh_user=ssh_user,
        ssh_password=ssh_password,
        ssh_key_path=ssh_key_path
    )
    
    result = await discovery_agent.run(
        f"Discover all applications and services running on {host}",
        deps=context
    )
    
    return result.data
```

### Phase 3: Validation Agent

#### 3.1 Validation Planning Agent

```python
# python/src/agents/validation_agent.py

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from .discovery_agent import WorkloadDiscoveryResult

class ValidationStep(BaseModel):
    """A single validation step."""
    step_id: str
    tool_name: str
    description: str
    arguments: Dict[str, Any]
    required: bool = True
    priority: int = Field(ge=1, le=10, default=5)

class ValidationPlan(BaseModel):
    """Complete validation plan."""
    resource_type: str
    strategy: str
    steps: List[ValidationStep]
    acceptance_criteria: Dict[str, Any]
    estimated_duration_seconds: int

class ValidationPlanContext(BaseModel):
    """Context for validation planning."""
    discovery_result: WorkloadDiscoveryResult
    user_requirements: Optional[Dict[str, Any]] = None

validation_planner_agent = Agent(
    'openai:gpt-4',
    result_type=ValidationPlan,
    system_prompt="""You are an expert validation planning agent.

Your task is to create comprehensive validation plans based on discovered workloads.

Guidelines:
1. Prioritize checks based on application criticality
2. Include network, application, and system-level validations
3. Set appropriate acceptance criteria for each application type
4. Consider dependencies between checks
5. Optimize for efficiency while being thorough

For databases: Focus on connectivity, health, storage, replication
For web servers: Focus on endpoints, SSL, response times
For application servers: Focus on health endpoints, resource usage
""",
    tools=[]
)

async def create_validation_plan(
    discovery_result: WorkloadDiscoveryResult,
    user_requirements: Optional[Dict[str, Any]] = None
) -> ValidationPlan:
    """Create a validation plan based on discovery results.
    
    Args:
        discovery_result: Workload discovery results
        user_requirements: Optional user-specified requirements
    
    Returns:
        ValidationPlan with ordered validation steps
    """
    context = ValidationPlanContext(
        discovery_result=discovery_result,
        user_requirements=user_requirements
    )
    
    prompt = f"""Create a comprehensive validation plan for a {discovery_result.primary_application.name if discovery_result.primary_application else 'unknown'} server at {discovery_result.host}.

Discovered applications:
{', '.join([app.name for app in discovery_result.applications])}

Recommended validations:
{', '.join(discovery_result.recommended_validations)}
"""
    
    result = await validation_planner_agent.run(prompt, deps=context)
    return result.data
```

### Phase 4: Evaluation Agent

#### 4.1 Result Evaluation Agent

```python
# python/src/agents/evaluation_agent.py

from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum

class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"

class CheckResult(BaseModel):
    """Result of a single validation check."""
    check_id: str
    check_name: str
    status: ValidationStatus
    expected: str
    actual: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ValidationEvaluation(BaseModel):
    """Complete validation evaluation."""
    overall_status: ValidationStatus
    score: int = Field(ge=0, le=100)
    checks: List[CheckResult]
    summary: str
    recommendations: List[str]
    critical_issues: List[str]
    warnings: List[str]

evaluation_agent = Agent(
    'openai:gpt-4',
    result_type=ValidationEvaluation,
    system_prompt="""You are an expert infrastructure evaluation agent.

Your task is to evaluate validation results and provide actionable insights.

Guidelines:
1. Assess each check against acceptance criteria
2. Calculate an overall health score (0-100)
3. Identify critical issues that need immediate attention
4. Provide specific, actionable recommendations
5. Consider the context of the application type

Be clear and concise. Prioritize issues by severity.
""",
    tools=[]
)

async def evaluate_validation_results(
    validation_results: List[Dict[str, Any]],
    acceptance_criteria: Dict[str, Any],
    application_context: str
) -> ValidationEvaluation:
    """Evaluate validation results using the evaluation agent.
    
    Args:
        validation_results: Raw validation results
        acceptance_criteria: Acceptance criteria
        application_context: Context about the application
    
    Returns:
        ValidationEvaluation with scores and recommendations
    """
    prompt = f"""Evaluate the following validation results for a {application_context}:

Results: {validation_results}

Acceptance Criteria: {acceptance_criteria}

Provide a comprehensive evaluation with:
- Overall health score
- Status for each check
- Critical issues
- Actionable recommendations
"""
    
    result = await evaluation_agent.run(prompt)
    return result.data
```

### Phase 5: Orchestrator Agent

#### 5.1 Main Orchestrator

```python
# python/src/agents/orchestrator.py

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Optional
from .discovery_agent import discover_workload, WorkloadDiscoveryResult
from .validation_agent import create_validation_plan, ValidationPlan
from .evaluation_agent import evaluate_validation_results, ValidationEvaluation

class ValidationWorkflowResult(BaseModel):
    """Complete workflow result."""
    host: str
    discovery: WorkloadDiscoveryResult
    validation_plan: ValidationPlan
    evaluation: ValidationEvaluation
    execution_time_seconds: float

class OrchestratorContext(BaseModel):
    """Context for orchestrator."""
    mcp_client: Any
    user_prompt: str

orchestrator_agent = Agent(
    'openai:gpt-4',
    result_type=ValidationWorkflowResult,
    system_prompt="""You are the main orchestrator for infrastructure validation.

Your role is to coordinate the entire validation workflow:
1. Parse user prompts to extract resource information
2. Coordinate workload discovery
3. Generate validation plans
4. Execute validations
5. Evaluate results
6. Provide comprehensive reports

Be efficient and thorough. Provide clear progress updates.
""",
    tools=[]
)

async def run_validation_workflow(
    user_prompt: str,
    mcp_client: Any
) -> ValidationWorkflowResult:
    """Run the complete validation workflow.
    
    Args:
        user_prompt: User's validation request
        mcp_client: MCP client instance
    
    Returns:
        ValidationWorkflowResult with complete results
    """
    import time
    start_time = time.time()
    
    # This would be enhanced with actual orchestration logic
    # For now, showing the structure
    
    # 1. Parse prompt (could use another agent or simple parsing)
    # 2. Discover workloads
    # 3. Create validation plan
    # 4. Execute validations
    # 5. Evaluate results
    
    execution_time = time.time() - start_time
    
    # Return structured result
    # (Implementation details would go here)
```

## Benefits of Pydantic AI Integration

### 1. Type Safety
```python
# Before: Unstructured dictionaries
result = {"status": "pass", "score": 85}  # No validation

# After: Type-safe Pydantic models
result = ValidationEvaluation(
    overall_status=ValidationStatus.PASS,
    score=85,
    checks=[...],
    recommendations=[...]
)  # Validated at runtime
```

### 2. Intelligent Tool Use
```python
# Agent automatically decides which tools to use
result = await discovery_agent.run(
    "Discover applications on 192.168.1.100"
)
# Agent will call scan_ports_tool, scan_processes_tool, detect_applications_tool
# in the optimal order based on the situation
```

### 3. Streaming Progress
```python
# Real-time progress updates
async with discovery_agent.run_stream(
    "Discover applications on 192.168.1.100",
    deps=context
) as stream:
    async for message in stream.stream_text():
        print(f"Progress: {message}")
```

### 4. Multi-Model Support
```python
# Easy to switch between models
discovery_agent = Agent('anthropic:claude-3-5-sonnet-20241022', ...)
validation_agent = Agent('openai:gpt-4', ...)
evaluation_agent = Agent('gemini-1.5-pro', ...)
```

## Migration Strategy

### Phase 1: Parallel Implementation
- Keep existing code functional
- Implement Pydantic AI agents alongside
- Test thoroughly with real workloads

### Phase 2: Gradual Migration
- Start with discovery agent
- Move to validation planning
- Finally, evaluation and orchestration

### Phase 3: Full Integration
- Replace old components
- Remove deprecated code
- Optimize performance

## Configuration

### Environment Variables
```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MCP_SERVER_URL=http://localhost:8000
DEFAULT_MODEL=openai:gpt-4
```

### Agent Configuration
```python
# python/src/config/agents.py

from pydantic import BaseModel

class AgentSettings(BaseModel):
    discovery_model: str = "openai:gpt-4"
    validation_model: str = "openai:gpt-4"
    evaluation_model: str = "openai:gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
```

## Testing Strategy

### Unit Tests
```python
# Test individual agents
async def test_discovery_agent():
    result = await discover_workload(
        host="test.example.com",
        ssh_user="test",
        mcp_client=mock_client
    )
    assert isinstance(result, WorkloadDiscoveryResult)
    assert result.confidence > 0.8
```

### Integration Tests
```python
# Test complete workflow
async def test_validation_workflow():
    result = await run_validation_workflow(
        "Validate 192.168.1.100",
        mcp_client=real_client
    )
    assert result.evaluation.score > 0
```

## Performance Considerations

- **Caching**: Cache discovery results for repeated validations
- **Parallel Execution**: Run independent validations in parallel
- **Model Selection**: Use faster models for simple tasks
- **Streaming**: Use streaming for long-running operations

## Conclusion

Integrating Pydantic AI will transform the validation workflow into a truly intelligent, type-safe, and maintainable agentic system. The structured approach with specialized agents provides:

- **Better code organization**: Clear separation of concerns
- **Type safety**: Catch errors at development time
- **Flexibility**: Easy to extend and modify
- **Intelligence**: LLM-powered decision making
- **Maintainability**: Clean, testable code

This approach aligns perfectly with the workload discovery and validation requirements while providing a solid foundation for future enhancements.