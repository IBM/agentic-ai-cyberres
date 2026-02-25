# Migration Strategy: Current to Best Practices Architecture

## Overview

This document provides a detailed migration strategy to transition from the current agentic workflow to the recommended best practices architecture with enhanced MCP integration.

**Migration Approach**: Incremental, backward-compatible transformation
**Timeline**: 8 weeks (4 phases)
**Risk Level**: Low (maintains existing functionality throughout)

---

## Table of Contents

1. [Migration Principles](#migration-principles)
2. [Current vs Target Architecture](#current-vs-target-architecture)
3. [Phase-by-Phase Migration](#phase-by-phase-migration)
4. [Backward Compatibility Strategy](#backward-compatibility-strategy)
5. [Testing Strategy](#testing-strategy)
6. [Rollback Plan](#rollback-plan)

---

## Migration Principles

### 1. Incremental Changes
- Small, testable changes at each step
- No "big bang" rewrites
- Maintain working system throughout migration

### 2. Backward Compatibility
- Keep existing APIs functional
- Add new features alongside old ones
- Deprecate gradually with clear timelines

### 3. Test-Driven Migration
- Write tests before refactoring
- Maintain >80% code coverage
- Automated regression testing

### 4. Feature Flags
- Use feature flags for new capabilities
- Enable gradual rollout
- Easy rollback if issues arise

---

## Current vs Target Architecture

### Current Architecture

```
recovery_validation_agent.py (Monolithic)
├── gather_information_interactive()
├── run_validation()
│   ├── ResourceDiscovery
│   ├── ValidationPlanner
│   ├── ValidationExecutor
│   └── ResultEvaluator
└── run_interactive()
```

### Target Architecture

```
WorkflowOrchestrator
├── StateManager
├── DiscoveryAgent
│   └── ToolCoordinator → MCP Tools
├── ClassificationAgent
│   └── ApplicationClassifier
├── ValidationAgent
│   ├── ValidationPlanner
│   └── ValidationExecutor → MCP Tools
└── ReportingAgent
    └── ReportGenerator
```

---

## Phase-by-Phase Migration

### Phase 1: Foundation (Weeks 1-2)

#### Goals
- Establish base agent framework
- Add state management
- Create tool coordinator
- Maintain existing functionality

#### Step 1.1: Create Base Agent Class (Week 1, Day 1-2)

**File**: `python/src/agents/base.py`

```python
"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from datetime import datetime

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, mcp_client, name: str):
        self.mcp_client = mcp_client
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.execution_history = []
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute agent's primary task."""
        pass
    
    def log_step(self, message: str, level: str = "info"):
        """Log agent step with context."""
        log_method = getattr(self.logger, level)
        log_method(f"[{self.name}] {message}")
    
    def record_execution(self, action: str, result: Any):
        """Record execution for audit trail."""
        self.execution_history.append({
            "timestamp": datetime.now(),
            "action": action,
            "result": result
        })
```

**Migration Action**: Create new file, no changes to existing code

#### Step 1.2: Add State Management (Week 1, Day 3-4)

**File**: `python/src/state_manager.py`

```python
"""Workflow state management."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import json
from pathlib import Path

class WorkflowState(Enum):
    """Workflow execution states."""
    INITIALIZED = "initialized"
    DISCOVERING = "discovering"
    CLASSIFYING = "classifying"
    VALIDATING = "validating"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowContext:
    """Context for workflow execution."""
    workflow_id: str
    state: WorkflowState
    resource_info: Dict[str, Any]
    discovery_results: Optional[Dict[str, Any]] = None
    classification: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            WorkflowState.INITIALIZED: [WorkflowState.DISCOVERING],
            WorkflowState.DISCOVERING: [WorkflowState.CLASSIFYING, WorkflowState.FAILED],
            WorkflowState.CLASSIFYING: [WorkflowState.VALIDATING, WorkflowState.FAILED],
            WorkflowState.VALIDATING: [WorkflowState.REPORTING, WorkflowState.FAILED],
            WorkflowState.REPORTING: [WorkflowState.COMPLETED, WorkflowState.FAILED],
        }
        return new_state in valid_transitions.get(self.state, [])

class StateManager:
    """Manages workflow state persistence."""
    
    def __init__(self, state_dir: str = ".workflow_states"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
    
    async def save_state(self, context: WorkflowContext):
        """Save workflow state to disk."""
        state_file = self.state_dir / f"{context.workflow_id}.json"
        with open(state_file, 'w') as f:
            json.dump(self._serialize_context(context), f, indent=2)
    
    async def load_state(self, workflow_id: str) -> Optional[WorkflowContext]:
        """Load workflow state from disk."""
        state_file = self.state_dir / f"{workflow_id}.json"
        if not state_file.exists():
            return None
        
        with open(state_file, 'r') as f:
            data = json.load(f)
        
        return self._deserialize_context(data)
    
    def _serialize_context(self, context: WorkflowContext) -> dict:
        """Serialize context to JSON-compatible dict."""
        return {
            "workflow_id": context.workflow_id,
            "state": context.state.value,
            "resource_info": context.resource_info,
            "discovery_results": context.discovery_results,
            "classification": context.classification,
            "validation_results": context.validation_results,
            "errors": context.errors,
            "metadata": context.metadata
        }
    
    def _deserialize_context(self, data: dict) -> WorkflowContext:
        """Deserialize context from JSON dict."""
        return WorkflowContext(
            workflow_id=data["workflow_id"],
            state=WorkflowState(data["state"]),
            resource_info=data["resource_info"],
            discovery_results=data.get("discovery_results"),
            classification=data.get("classification"),
            validation_results=data.get("validation_results"),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {})
        )
```

**Migration Action**: Create new file, add to existing workflow as optional feature

#### Step 1.3: Create Tool Coordinator (Week 1, Day 5)

**File**: `python/src/tool_coordinator.py`

```python
"""Coordinates MCP tool execution."""

import asyncio
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import hashlib
import json

class RetryPolicy:
    """Retry policy for tool execution."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    @classmethod
    def default(cls):
        return cls(max_retries=3, base_delay=1.0)

class ToolCoordinator:
    """Coordinates MCP tool execution with caching and retry."""
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.tool_cache = {}
        self.execution_history = []
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        retry_policy: Optional[RetryPolicy] = None,
        use_cache: bool = True
    ) -> dict:
        """Execute MCP tool with caching and retry logic."""
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(tool_name, arguments)
            if cache_key in self.tool_cache:
                return self.tool_cache[cache_key]
        
        # Execute with retry
        retry_policy = retry_policy or RetryPolicy.default()
        result = await self._execute_with_retry(
            tool_name,
            arguments,
            retry_policy
        )
        
        # Cache result
        if use_cache:
            self.tool_cache[cache_key] = result
        
        # Record execution
        self.execution_history.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "timestamp": datetime.now()
        })
        
        return result
    
    async def execute_parallel(
        self,
        tool_calls: List[Tuple[str, dict]]
    ) -> List[dict]:
        """Execute multiple tools in parallel."""
        tasks = [
            self.execute_tool(tool_name, args)
            for tool_name, args in tool_calls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _execute_with_retry(
        self,
        tool_name: str,
        arguments: dict,
        retry_policy: RetryPolicy
    ) -> dict:
        """Execute tool with retry logic."""
        last_error = None
        
        for attempt in range(retry_policy.max_retries):
            try:
                return await self.mcp_client.call_tool(tool_name, arguments)
            except Exception as e:
                last_error = e
                if attempt < retry_policy.max_retries - 1:
                    delay = retry_policy.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        raise last_error
    
    def _get_cache_key(self, tool_name: str, arguments: dict) -> str:
        """Generate cache key for tool call."""
        key_data = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
```

**Migration Action**: Create new file, integrate into existing executor

#### Step 1.4: Update Existing Code to Use Tool Coordinator (Week 2)

**File**: `python/src/executor.py` (Modified)

```python
# Add at top of file
from tool_coordinator import ToolCoordinator

class ValidationExecutor:
    """Execute validation plans using MCP client."""
    
    def __init__(self, mcp_client: MCPClient):
        """Initialize validation executor."""
        self.mcp_client = mcp_client
        # NEW: Add tool coordinator
        self.tool_coordinator = ToolCoordinator(mcp_client)
    
    async def execute_step(self, step: ValidationStep) -> ExecutionResult:
        """Execute a single validation step."""
        start_time = time.time()
        
        try:
            logger.info(f"Executing step: {step.step_id} ({step.tool_name})")
            
            # Filter out None values from arguments
            clean_args = {k: v for k, v in step.arguments.items() if v is not None}
            
            # NEW: Use tool coordinator instead of direct call
            result = await self.tool_coordinator.execute_tool(
                step.tool_name, 
                clean_args
            )
            
            # ... rest of existing code
```

**Migration Action**: Modify existing file, add feature flag for tool coordinator

---

### Phase 2: Agent Implementation (Weeks 3-4)

#### Step 2.1: Create Discovery Agent (Week 3, Day 1-2)

**File**: `python/src/agents/discovery_agent.py`

```python
"""Discovery agent for workload discovery."""

from agents.base import BaseAgent
from models import WorkloadDiscoveryResult
from typing import Dict, Any

class DiscoveryAgent(BaseAgent):
    """Discovers workloads and applications on infrastructure resources."""
    
    def __init__(self, mcp_client, tool_coordinator):
        super().__init__(mcp_client, "discovery")
        self.tool_coordinator = tool_coordinator
    
    async def execute(self, context: Dict[str, Any]) -> WorkloadDiscoveryResult:
        """Execute workload discovery workflow."""
        resource_info = context['resource_info']
        
        # Step 1: Scan ports
        self.log_step("Scanning ports...")
        port_results = await self.tool_coordinator.execute_tool(
            "workload_scan_ports",
            {
                "host": resource_info['host'],
                "ssh_user": resource_info['ssh_user'],
                "ssh_password": resource_info.get('ssh_password'),
                "scan_type": "common"
            }
        )
        
        # Step 2: Scan processes
        self.log_step("Scanning processes...")
        process_results = await self.tool_coordinator.execute_tool(
            "workload_scan_processes",
            {
                "host": resource_info['host'],
                "ssh_user": resource_info['ssh_user'],
                "ssh_password": resource_info.get('ssh_password')
            }
        )
        
        # Step 3: Detect applications
        self.log_step("Detecting applications...")
        app_detections = await self.tool_coordinator.execute_tool(
            "workload_detect_applications",
            {
                "host": resource_info['host'],
                "ports": port_results.get('ports', []),
                "processes": process_results.get('processes', [])
            }
        )
        
        # Step 4: Aggregate results
        self.log_step("Aggregating discovery results...")
        aggregated = await self.tool_coordinator.execute_tool(
            "workload_aggregate_results",
            {
                "host": resource_info['host'],
                "port_results": port_results,
                "process_results": process_results,
                "app_detections": app_detections
            }
        )
        
        return WorkloadDiscoveryResult(**aggregated)
```

**Migration Action**: Create new agent, integrate as optional enhancement

#### Step 2.2: Create Classification Agent (Week 3, Day 3-4)

**File**: `python/src/agents/classification_agent.py`

```python
"""Classification agent for resource classification."""

from agents.base import BaseAgent
from classifier import ApplicationClassifier
from models import ResourceClassification
from typing import Dict, Any

class ClassificationAgent(BaseAgent):
    """Classifies resources based on discovered applications."""
    
    def __init__(self, mcp_client, classifier: ApplicationClassifier):
        super().__init__(mcp_client, "classification")
        self.classifier = classifier
    
    async def execute(self, context: Dict[str, Any]) -> ResourceClassification:
        """Classify resource and recommend validation strategy."""
        discovery_results = context['discovery_results']
        
        self.log_step("Classifying resource based on discovered applications...")
        classification = self.classifier.classify(discovery_results)
        
        self.log_step(
            f"Classification complete: {classification.category.value} "
            f"(confidence: {classification.confidence:.2f})"
        )
        
        return classification
```

**Migration Action**: Create new agent, use existing classifier

#### Step 2.3: Refactor Existing Validation Logic into Agent (Week 3, Day 5)

**File**: `python/src/agents/validation_agent.py`

```python
"""Validation agent for executing validation checks."""

from agents.base import BaseAgent
from planner import ValidationPlanner
from executor import ValidationExecutor
from typing import Dict, Any

class ValidationAgent(BaseAgent):
    """Executes validation checks based on resource classification."""
    
    def __init__(
        self, 
        mcp_client,
        planner: ValidationPlanner,
        executor: ValidationExecutor
    ):
        super().__init__(mcp_client, "validation")
        self.planner = planner
        self.executor = executor
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation workflow."""
        resource_info = context['resource_info']
        classification = context.get('classification')
        
        # Generate validation plan
        if classification:
            self.log_step("Generating validation plan from classification...")
            plan = self.planner.generate_plan_from_classification(
                classification,
                resource_info
            )
        else:
            self.log_step("Generating standard validation plan...")
            plan = self.planner.generate_plan(resource_info)
        
        self.log_step(f"Executing {len(plan)} validation steps...")
        
        # Execute validation plan
        results = await self.executor.execute_plan(plan)
        
        self.log_step(f"Validation complete: {len(results)} steps executed")
        
        return {
            "plan": plan,
            "results": results
        }
```

**Migration Action**: Wrap existing logic in agent interface

#### Step 2.4: Create Reporting Agent (Week 4, Day 1-2)

**File**: `python/src/agents/reporting_agent.py`

```python
"""Reporting agent for generating validation reports."""

from agents.base import BaseAgent
from evaluator import ResultEvaluator
from report_generator import ReportGenerator
from models import ValidationReport
from typing import Dict, Any

class ReportingAgent(BaseAgent):
    """Generates comprehensive reports with recommendations."""
    
    def __init__(
        self,
        mcp_client,
        evaluator: ResultEvaluator,
        report_generator: ReportGenerator
    ):
        super().__init__(mcp_client, "reporting")
        self.evaluator = evaluator
        self.report_generator = report_generator
    
    async def execute(self, context: Dict[str, Any]) -> ValidationReport:
        """Generate validation report."""
        self.log_step("Evaluating validation results...")
        
        # Evaluate results
        evaluation = self.evaluator.evaluate(
            context['resource_info']['resource_type'],
            context['validation_results']['results']
        )
        
        self.log_step("Generating recommendations...")
        
        # Generate recommendations
        recommendations = self.report_generator.generate_recommendations(
            evaluation
        )
        
        # Create report
        report = ValidationReport(
            request=context['request'],
            result=evaluation,
            recommendations=recommendations
        )
        
        self.log_step("Report generation complete")
        
        return report
```

**Migration Action**: Wrap existing logic in agent interface

---

### Phase 3: Orchestrator Integration (Weeks 5-6)

#### Step 3.1: Create New Orchestrator (Week 5, Day 1-3)

**File**: `python/src/orchestrator.py`

```python
"""Workflow orchestrator using specialized agents."""

import uuid
from typing import Dict, Any
from state_manager import StateManager, WorkflowContext, WorkflowState
from agents.discovery_agent import DiscoveryAgent
from agents.classification_agent import ClassificationAgent
from agents.validation_agent import ValidationAgent
from agents.reporting_agent import ReportingAgent
from models import ValidationRequest, ValidationReport

class WorkflowOrchestrator:
    """Orchestrates validation workflow using specialized agents."""
    
    def __init__(
        self,
        mcp_client,
        state_manager: StateManager,
        agents: Dict[str, Any]
    ):
        self.mcp_client = mcp_client
        self.state_manager = state_manager
        self.agents = agents
    
    async def execute_workflow(
        self,
        request: ValidationRequest
    ) -> ValidationReport:
        """Execute complete validation workflow."""
        # Initialize workflow context
        workflow_id = str(uuid.uuid4())
        context = WorkflowContext(
            workflow_id=workflow_id,
            state=WorkflowState.INITIALIZED,
            resource_info=request.resource_info.dict()
        )
        context.metadata['request'] = request
        
        try:
            # Phase 1: Discovery
            if request.auto_discover:
                context = await self._transition_to(
                    context,
                    WorkflowState.DISCOVERING
                )
                discovery_results = await self.agents['discovery'].execute({
                    'resource_info': context.resource_info
                })
                context.discovery_results = discovery_results.dict()
            
            # Phase 2: Classification
            if context.discovery_results:
                context = await self._transition_to(
                    context,
                    WorkflowState.CLASSIFYING
                )
                classification = await self.agents['classification'].execute({
                    'discovery_results': context.discovery_results
                })
                context.classification = classification.dict()
            
            # Phase 3: Validation
            context = await self._transition_to(
                context,
                WorkflowState.VALIDATING
            )
            validation_results = await self.agents['validation'].execute({
                'resource_info': context.resource_info,
                'classification': context.classification
            })
            context.validation_results = validation_results
            
            # Phase 4: Reporting
            context = await self._transition_to(
                context,
                WorkflowState.REPORTING
            )
            report = await self.agents['reporting'].execute({
                'request': request,
                'resource_info': context.resource_info,
                'discovery_results': context.discovery_results,
                'classification': context.classification,
                'validation_results': validation_results
            })
            
            # Complete
            context = await self._transition_to(
                context,
                WorkflowState.COMPLETED
            )
            
            return report
            
        except Exception as e:
            context.errors.append(str(e))
            context = await self._transition_to(
                context,
                WorkflowState.FAILED
            )
            raise
    
    async def _transition_to(
        self,
        context: WorkflowContext,
        new_state: WorkflowState
    ) -> WorkflowContext:
        """Transition workflow to new state."""
        if not context.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {context.state} to {new_state}"
            )
        
        context.state = new_state
        await self.state_manager.save_state(context)
        return context
```

**Migration Action**: Create new orchestrator alongside existing one

#### Step 3.2: Add Feature Flag System (Week 5, Day 4)

**File**: `python/src/feature_flags.py`

```python
"""Feature flag system for gradual rollout."""

import os
from typing import Dict, Any

class FeatureFlags:
    """Manage feature flags for gradual rollout."""
    
    def __init__(self):
        self.flags = {
            'use_new_orchestrator': self._get_flag('USE_NEW_ORCHESTRATOR', False),
            'use_tool_coordinator': self._get_flag('USE_TOOL_COORDINATOR', True),
            'use_state_management': self._get_flag('USE_STATE_MANAGEMENT', True),
            'use_discovery_agent': self._get_flag('USE_DISCOVERY_AGENT', True),
            'use_parallel_execution': self._get_flag('USE_PARALLEL_EXECUTION', False),
        }
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if feature flag is enabled."""
        return self.flags.get(flag_name, False)
    
    def _get_flag(self, env_var: str, default: bool) -> bool:
        """Get flag value from environment or use default."""
        value = os.getenv(env_var, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

# Global instance
feature_flags = FeatureFlags()
```

**Migration Action**: Add feature flag checks throughout codebase

#### Step 3.3: Update Main Entry Point (Week 5, Day 5)

**File**: `python/src/recovery_validation_agent.py` (Modified)

```python
# Add imports
from orchestrator import WorkflowOrchestrator
from state_manager import StateManager
from tool_coordinator import ToolCoordinator
from feature_flags import feature_flags
from agents.discovery_agent import DiscoveryAgent
from agents.classification_agent import ClassificationAgent
from agents.validation_agent import ValidationAgent
from agents.reporting_agent import ReportingAgent

class RecoveryValidationAgent:
    """Main orchestrator for recovery validation."""
    
    def __init__(self):
        """Initialize recovery validation agent."""
        self.credential_manager = get_credential_manager()
        self.conversation_handler = ConversationHandler()
        
        # NEW: Check feature flags
        if feature_flags.is_enabled('use_new_orchestrator'):
            self._init_new_orchestrator()
        else:
            self._init_legacy_components()
    
    def _init_new_orchestrator(self):
        """Initialize new orchestrator with agents."""
        self.state_manager = StateManager()
        self.tool_coordinator = ToolCoordinator(None)  # Will be set later
        
        # Initialize agents (will be created after MCP client connection)
        self.agents = {}
    
    def _init_legacy_components(self):
        """Initialize legacy components."""
        self.planner = ValidationPlanner()
        self.evaluator = ResultEvaluator()
        self.report_generator = ReportGenerator()
    
    async def run_validation(
        self,
        validation_request: ValidationRequest,
        reader=None
    ) -> ValidationReport:
        """Run complete validation workflow."""
        # Get MCP server URL
        mcp_server_url = self.credential_manager.get_mcp_server_url()
        
        async with mcp_client_context(mcp_server_url) as mcp_client:
            # NEW: Use new orchestrator if enabled
            if feature_flags.is_enabled('use_new_orchestrator'):
                return await self._run_with_new_orchestrator(
                    validation_request,
                    mcp_client,
                    reader
                )
            else:
                return await self._run_with_legacy(
                    validation_request,
                    mcp_client,
                    reader
                )
    
    async def _run_with_new_orchestrator(
        self,
        validation_request,
        mcp_client,
        reader
    ):
        """Run validation using new orchestrator."""
        # Initialize tool coordinator
        tool_coordinator = ToolCoordinator(mcp_client)
        
        # Initialize agents
        agents = {
            'discovery': DiscoveryAgent(mcp_client, tool_coordinator),
            'classification': ClassificationAgent(
                mcp_client,
                ApplicationClassifier()
            ),
            'validation': ValidationAgent(
                mcp_client,
                ValidationPlanner(),
                ValidationExecutor(mcp_client)
            ),
            'reporting': ReportingAgent(
                mcp_client,
                ResultEvaluator(),
                ReportGenerator()
            )
        }
        
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(
            mcp_client,
            self.state_manager,
            agents
        )
        
        # Execute workflow
        return await orchestrator.execute_workflow(validation_request)
    
    async def _run_with_legacy(
        self,
        validation_request,
        mcp_client,
        reader
    ):
        """Run validation using legacy approach."""
        # ... existing implementation ...
```

**Migration Action**: Add feature flag checks, maintain backward compatibility

---

### Phase 4: Testing & Optimization (Weeks 7-8)

#### Step 4.1: Comprehensive Testing (Week 7)

**Test Strategy**:
1. Unit tests for each agent
2. Integration tests for orchestrator
3. End-to-end tests with feature flags
4. Performance benchmarks

**File**: `python/src/tests/test_agents.py`

```python
"""Tests for specialized agents."""

import pytest
from agents.discovery_agent import DiscoveryAgent
from agents.classification_agent import ClassificationAgent
# ... more imports

@pytest.mark.asyncio
async def test_discovery_agent():
    """Test discovery agent execution."""
    # Setup
    mock_mcp_client = MockMCPClient()
    tool_coordinator = ToolCoordinator(mock_mcp_client)
    agent = DiscoveryAgent(mock_mcp_client, tool_coordinator)
    
    # Execute
    context = {'resource_info': {'host': '192.168.1.100', ...}}
    result = await agent.execute(context)
    
    # Assert
    assert result is not None
    assert len(result.applications) > 0

# ... more tests
```

#### Step 4.2: Performance Optimization (Week 8)

**Optimization Areas**:
1. Parallel tool execution
2. Result caching
3. Connection pooling
4. Memory optimization

---

## Backward Compatibility Strategy

### API Compatibility

```python
# Old API (still works)
agent = RecoveryValidationAgent()
report = await agent.run_validation(request)

# New API (optional)
orchestrator = WorkflowOrchestrator(...)
report = await orchestrator.execute_workflow(request)
```

### Configuration Compatibility

```python
# Old config (still works)
{
    "resource_type": "vm",
    "host": "192.168.1.100"
}

# New config (enhanced)
{
    "resource_type": "vm",
    "host": "192.168.1.100",
    "use_discovery": true,
    "use_classification": true
}
```

---

## Testing Strategy

### Test Levels

1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: Components working together
3. **End-to-End Tests**: Complete workflows
4. **Performance Tests**: Benchmarks and load tests

### Test Coverage Goals

- Unit tests: >90%
- Integration tests: >80%
- E2E tests: Critical paths covered
- Performance: <2 minutes per validation

---

## Rollback Plan

### Rollback Triggers

1. Critical bugs in production
2. Performance degradation >20%
3. Test coverage drops below 70%
4. User-reported issues >5 per day

### Rollback Process

1. Disable feature flags
2. Revert to previous version
3. Investigate issues
4. Fix and re-deploy

### Rollback Commands

```bash
# Disable new orchestrator
export USE_NEW_ORCHESTRATOR=false

# Restart service
systemctl restart validation-agent
```

---

## Success Criteria

### Phase 1 Success
- [ ] Base agent framework created
- [ ] State management working
- [ ] Tool coordinator integrated
- [ ] All existing tests passing

### Phase 2 Success
- [ ] All agents implemented
- [ ] Agents tested independently
- [ ] Integration with existing code
- [ ] No regression in functionality

### Phase 3 Success
- [ ] New orchestrator working
- [ ] Feature flags operational
- [ ] Backward compatibility maintained
- [ ] Performance equivalent or better

### Phase 4 Success
- [ ] Test coverage >80%
- [ ] Performance optimized
- [ ] Documentation complete
- [ ] Production-ready

---

## Conclusion

This migration strategy provides a safe, incremental path from the current architecture to the recommended best practices. By using feature flags, maintaining backward compatibility, and following a phased approach, we can transform the system while minimizing risk and maintaining continuous operation.

**Key Success Factors**:
1. Incremental changes with testing at each step
2. Feature flags for gradual rollout
3. Backward compatibility throughout
4. Comprehensive testing strategy
5. Clear rollback plan
