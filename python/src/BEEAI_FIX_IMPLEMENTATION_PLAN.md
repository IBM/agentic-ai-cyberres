# BeeAI Implementation Fix Plan

## Overview

This document provides a detailed, step-by-step plan to fix the incomplete BeeAI implementation in `python/src/beeai_agents/`. The plan focuses on implementing real tool execution, discovery, and validation functionality.

## Implementation Strategy

**Approach**: Fix existing implementation (Option 1 from review)
**Estimated Effort**: 2-3 days
**Risk Level**: Low (architecture is solid, just needs completion)

## Phase 1: Tool Execution Layer (Priority 1 - Critical)

### 1.1 Create Tool Executor Module

**File**: `python/src/beeai_agents/tool_executor.py`

```python
"""
Tool execution layer for BeeAI agents.
Handles MCP tool execution, result parsing, and error handling.
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from beeai_framework.tools.mcp import MCPTool
from models import CheckResult, ValidationStatus

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class ToolExecutor:
    """Executes MCP tools with proper error handling and retry logic."""
    
    def __init__(self, mcp_tools: List[MCPTool], max_retries: int = 3):
        """Initialize tool executor.
        
        Args:
            mcp_tools: List of available MCP tools
            max_retries: Maximum retry attempts for failed executions
        """
        self.mcp_tools = mcp_tools
        self.max_retries = max_retries
        self._tool_map = {tool.name: tool for tool in mcp_tools}
        
        logger.info(f"Tool executor initialized with {len(mcp_tools)} tools")
    
    def find_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Find tool by name.
        
        Args:
            tool_name: Name of the tool to find
        
        Returns:
            MCPTool or None if not found
        """
        return self._tool_map.get(tool_name)
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute MCP tool with arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If tool execution fails
        """
        tool = self.find_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool not found: {tool_name}")
        
        logger.info(f"Executing tool: {tool_name}")
        logger.debug(f"Tool arguments: {tool_args}")
        
        try:
            # Execute the tool using BeeAI's MCPTool interface
            result = await tool.execute(**tool_args)
            
            logger.info(f"Tool {tool_name} executed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {tool_name} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ToolExecutionError(error_msg) from e
    
    async def execute_with_retry(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool with exponential backoff retry.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If all retry attempts fail
        """
        import asyncio
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retry attempt {attempt} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                
                return await self.execute_tool(tool_name, tool_args)
                
            except ToolExecutionError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        raise ToolExecutionError(
            f"Tool execution failed after {self.max_retries} attempts: {last_error}"
        )
    
    def parse_check_result(
        self,
        tool_result: Dict[str, Any],
        check_def: Any,
        expected_value: Optional[str] = None
    ) -> CheckResult:
        """Parse tool result into CheckResult.
        
        Args:
            tool_result: Raw tool execution result
            check_def: Check definition with expected criteria
            expected_value: Optional expected value for comparison
        
        Returns:
            CheckResult with status and details
        """
        # Extract status from tool result
        # MCP tools typically return: {"success": bool, "data": {...}, "error": str}
        
        success = tool_result.get("success", False)
        data = tool_result.get("data", {})
        error = tool_result.get("error")
        
        if not success:
            return CheckResult(
                check_id=check_def.check_id,
                check_name=check_def.check_name,
                status=ValidationStatus.FAIL,
                message=error or "Tool execution failed",
                expected=expected_value or check_def.expected_result,
                actual="Execution failed"
            )
        
        # Compare actual vs expected if criteria provided
        if expected_value:
            actual_value = self._extract_value(data, check_def)
            matches = self._compare_values(actual_value, expected_value)
            
            if matches:
                return CheckResult(
                    check_id=check_def.check_id,
                    check_name=check_def.check_name,
                    status=ValidationStatus.PASS,
                    message="Check passed successfully",
                    expected=expected_value,
                    actual=str(actual_value),
                    details=data
                )
            else:
                return CheckResult(
                    check_id=check_def.check_id,
                    check_name=check_def.check_name,
                    status=ValidationStatus.FAIL,
                    message="Value does not match expected criteria",
                    expected=expected_value,
                    actual=str(actual_value),
                    details=data
                )
        
        # No expected value - just report success
        return CheckResult(
            check_id=check_def.check_id,
            check_name=check_def.check_name,
            status=ValidationStatus.PASS,
            message="Tool executed successfully",
            details=data
        )
    
    def _extract_value(self, data: Dict[str, Any], check_def: Any) -> Any:
        """Extract relevant value from tool result data."""
        # This would be customized based on check type
        # For now, return the whole data
        return data
    
    def _compare_values(self, actual: Any, expected: str) -> bool:
        """Compare actual value against expected criteria.
        
        Args:
            actual: Actual value from tool execution
            expected: Expected value or criteria string
        
        Returns:
            True if values match criteria
        """
        # Simple string comparison for now
        # In production, this would handle:
        # - Numeric comparisons (>, <, >=, <=)
        # - Range checks
        # - Pattern matching
        # - Complex criteria
        
        return str(actual) == expected
```

### 1.2 Update Orchestrator to Use Real Tool Execution

**File**: `python/src/beeai_agents/orchestrator.py`

**Changes Required**:

1. Add tool executor initialization (after line 215):

```python
# After _initialize_mcp() method
async def _initialize_mcp(self):
    """Initialize MCP client and discover tools."""
    logger.info(f"Connecting to MCP server at {self.mcp_server_path}...")
    
    # ... existing code ...
    
    # Discover tools
    self._mcp_tools = await MCPTool.from_client(self._mcp_client)
    logger.info(f"✓ Connected to MCP server, discovered {len(self._mcp_tools)} tools")
    
    # NEW: Initialize tool executor
    from beeai_agents.tool_executor import ToolExecutor
    self._tool_executor = ToolExecutor(self._mcp_tools, max_retries=3)
    logger.info("✓ Tool executor initialized")
```

2. Replace mock execution (lines 560-563) with real execution:

```python
# REPLACE THIS (lines 560-563):
# Execute tool (simplified - in production, use proper tool execution)
# For now, create mock results
check_result = self._create_mock_check_result(check_def)

# WITH THIS:
try:
    # Execute tool with retry logic
    tool_result = await self._tool_executor.execute_with_retry(
        check_def.mcp_tool,
        check_def.tool_args
    )
    
    # Parse result into CheckResult
    check_result = self._tool_executor.parse_check_result(
        tool_result,
        check_def,
        expected_value=check_def.expected_result
    )
    
except Exception as e:
    logger.error(f"Tool execution failed: {e}")
    check_result = CheckResult(
        check_id=check_def.check_id,
        check_name=check_def.check_name,
        status=ValidationStatus.ERROR,
        message=f"Tool execution error: {str(e)}"
    )
```

3. Remove mock method (lines 641-683) - no longer needed

## Phase 2: Discovery Implementation (Priority 1 - Critical)

### 2.1 Update Discovery Agent

**File**: `python/src/beeai_agents/discovery_agent.py`

**Changes Required**:

1. Pass MCP tools to discovery agent (modify `__init__`):

```python
def __init__(
    self,
    llm_model: str = "ollama:llama3.2",
    mcp_tools: Optional[List[MCPTool]] = None,  # NEW parameter
    memory_size: int = 50,
    temperature: float = 0.1
):
    """Initialize BeeAI Discovery Agent.
    
    Args:
        llm_model: LLM model identifier
        mcp_tools: List of MCP tools (if None, will auto-load)
        memory_size: Size of sliding memory window
        temperature: LLM temperature for planning
    """
    self.llm_model = llm_model
    self.mcp_tools = mcp_tools  # Store tools
    self.memory_size = memory_size
    self.temperature = temperature
    
    # ... rest of init ...
```

2. Replace placeholder discovery (lines 380-400) with real implementation:

```python
async def _execute_discovery(
    self,
    resource: ResourceInfo,
    plan: DiscoveryPlan
) -> WorkloadDiscoveryResult:
    """Execute discovery plan using MCP tools.
    
    Args:
        resource: Resource information
        plan: Discovery plan
    
    Returns:
        WorkloadDiscoveryResult
    """
    logger.info(f"Executing discovery plan for {resource.host}")
    
    # Ensure tools are available
    if not self.mcp_tools:
        await self._ensure_mcp_tools()
    
    # Find discover_workload tool
    discovery_tool = None
    for tool in self.mcp_tools:
        if tool.name == "discover_workload":
            discovery_tool = tool
            break
    
    if not discovery_tool:
        raise Exception("discover_workload tool not found")
    
    # Prepare tool arguments
    tool_args = {
        "host": resource.host,
        "ssh_user": resource.ssh_user if hasattr(resource, 'ssh_user') else None,
        "ssh_password": resource.ssh_password if hasattr(resource, 'ssh_password') else None,
        "ssh_key_path": resource.ssh_key_path if hasattr(resource, 'ssh_key_path') else None,
        "scan_ports": plan.scan_ports,
        "scan_processes": plan.scan_processes,
        "detect_applications": plan.detect_applications
    }
    
    # Remove None values
    tool_args = {k: v for k, v in tool_args.items() if v is not None}
    
    try:
        # Execute discovery tool
        logger.info(f"Calling discover_workload tool for {resource.host}")
        result = await discovery_tool.execute(**tool_args)
        
        # Parse result
        if not result.get("success"):
            raise Exception(f"Discovery failed: {result.get('error', 'Unknown error')}")
        
        data = result.get("data", {})
        
        # Convert to WorkloadDiscoveryResult
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[
                PortInfo(**port) for port in data.get("ports", [])
            ],
            processes=[
                ProcessInfo(**proc) for proc in data.get("processes", [])
            ],
            applications=[
                ApplicationDetection(**app) for app in data.get("applications", [])
            ],
            discovery_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Discovery execution failed: {e}", exc_info=True)
        # Return empty result on failure
        return WorkloadDiscoveryResult(
            host=resource.host,
            ports=[],
            processes=[],
            applications=[],
            discovery_time=datetime.now()
        )
```

3. Update orchestrator to pass tools to discovery agent (orchestrator.py, line 169):

```python
# REPLACE:
self._discovery_agent = BeeAIDiscoveryAgent(
    llm_model=self.llm_model,
    memory_size=self.memory_size
)

# WITH:
self._discovery_agent = BeeAIDiscoveryAgent(
    llm_model=self.llm_model,
    mcp_tools=self._mcp_tools,  # Pass tools
    memory_size=self.memory_size
)
```

## Phase 3: Acceptance Criteria Integration (Priority 2)

### 3.1 Create Acceptance Criteria Loader

**File**: `python/src/beeai_agents/acceptance_loader.py`

```python
"""
Acceptance criteria loader for validation checks.
Loads and manages acceptance criteria from JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class AcceptanceCriteriaLoader:
    """Loads and manages acceptance criteria for validation."""
    
    def __init__(self, criteria_dir: Optional[Path] = None):
        """Initialize acceptance criteria loader.
        
        Args:
            criteria_dir: Directory containing acceptance JSON files
                         (defaults to cyberres-mcp/resources/acceptance)
        """
        if criteria_dir is None:
            # Auto-detect criteria directory
            current_file = Path(__file__)
            # Assume we're in python/src/beeai_agents
            # Go to python/cyberres-mcp/src/cyberres_mcp/resources/acceptance
            criteria_dir = (
                current_file.parent.parent.parent / 
                "cyberres-mcp" / "src" / "cyberres_mcp" / 
                "resources" / "acceptance"
            )
        
        self.criteria_dir = Path(criteria_dir)
        self._cache = {}
        
        logger.info(f"Acceptance criteria loader initialized: {self.criteria_dir}")
    
    @lru_cache(maxsize=10)
    def load_criteria(self, resource_type: str) -> Dict[str, Any]:
        """Load acceptance criteria for resource type.
        
        Args:
            resource_type: Type of resource (vm, db-oracle, db-mongo)
        
        Returns:
            Dictionary of acceptance criteria
        """
        # Map resource types to file names
        file_map = {
            "vm": "vm-core.json",
            "oracle": "db-oracle.json",
            "mongodb": "db-mongo.json"
        }
        
        filename = file_map.get(resource_type)
        if not filename:
            logger.warning(f"No acceptance criteria file for: {resource_type}")
            return {}
        
        filepath = self.criteria_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Acceptance criteria file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r') as f:
                criteria = json.load(f)
            
            logger.info(f"Loaded acceptance criteria from {filename}")
            return criteria
            
        except Exception as e:
            logger.error(f"Failed to load acceptance criteria: {e}")
            return {}
    
    def get_check_criteria(
        self,
        resource_type: str,
        check_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get criteria for specific check.
        
        Args:
            resource_type: Type of resource
            check_id: Check identifier
        
        Returns:
            Check criteria or None if not found
        """
        criteria = self.load_criteria(resource_type)
        
        # Acceptance files typically have structure:
        # {"checks": [{"id": "...", "expected": "...", ...}]}
        checks = criteria.get("checks", [])
        
        for check in checks:
            if check.get("id") == check_id:
                return check
        
        return None
    
    def get_expected_value(
        self,
        resource_type: str,
        check_id: str
    ) -> Optional[str]:
        """Get expected value for check.
        
        Args:
            resource_type: Type of resource
            check_id: Check identifier
        
        Returns:
            Expected value or None
        """
        check_criteria = self.get_check_criteria(resource_type, check_id)
        if check_criteria:
            return check_criteria.get("expected")
        return None
```

### 3.2 Integrate Acceptance Criteria into Orchestrator

**File**: `python/src/beeai_agents/orchestrator.py`

Add to initialization (after line 165):

```python
# Initialize acceptance criteria loader
from beeai_agents.acceptance_loader import AcceptanceCriteriaLoader
self._acceptance_loader = AcceptanceCriteriaLoader()
logger.info("Acceptance criteria loader initialized")
```

Update validation execution to use criteria (in `_execute_validation_phase`):

```python
# Before executing check, load expected value
expected_value = self._acceptance_loader.get_expected_value(
    resource_type=request.resource_info.resource_type.value,
    check_id=check_def.check_id
)

# Pass to tool executor
check_result = self._tool_executor.parse_check_result(
    tool_result,
    check_def,
    expected_value=expected_value or check_def.expected_result
)
```

## Phase 4: Testing and Validation (Priority 2)

### 4.1 Create Integration Test

**File**: `python/src/beeai_agents/test_integration.py`

```python
"""
Integration test for BeeAI validation workflow.
Tests end-to-end execution with real MCP server.
"""

import asyncio
import logging
from pathlib import Path

from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vm_validation():
    """Test VM validation workflow."""
    
    # Create test VM resource
    vm_resource = VMResourceInfo(
        host="test-vm.example.com",
        resource_type=ResourceType.VM,
        ssh_user="testuser",
        ssh_password="testpass",
        ssh_port=22
    )
    
    # Create validation request
    request = ValidationRequest(
        resource_info=vm_resource,
        auto_discover=True
    )
    
    # Initialize orchestrator
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=True,
        enable_ai_evaluation=True
    )
    
    try:
        # Initialize
        await orchestrator.initialize()
        logger.info("✓ Orchestrator initialized")
        
        # Execute workflow
        logger.info("Starting validation workflow...")
        result = await orchestrator.execute_workflow(request)
        
        # Print results
        logger.info("=" * 60)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 60)
        logger.info(f"Status: {result.workflow_status}")
        logger.info(f"Score: {result.validation_result.score}/100")
        logger.info(f"Passed: {result.validation_result.passed_checks}")
        logger.info(f"Failed: {result.validation_result.failed_checks}")
        logger.info(f"Warnings: {result.validation_result.warning_checks}")
        logger.info(f"Execution time: {result.execution_time_seconds:.2f}s")
        
        if result.evaluation:
            logger.info(f"\nOverall Health: {result.evaluation.overall_health}")
            logger.info(f"Critical Issues: {len(result.evaluation.critical_issues)}")
            logger.info(f"Recommendations: {len(result.evaluation.recommendations)}")
        
        logger.info("=" * 60)
        
        return result
        
    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(test_vm_validation())
```

### 4.2 Create Unit Tests

**File**: `python/src/beeai_agents/test_tool_executor.py`

```python
"""Unit tests for tool executor."""

import pytest
from unittest.mock import Mock, AsyncMock
from beeai_agents.tool_executor import ToolExecutor, ToolExecutionError


@pytest.mark.asyncio
async def test_tool_execution_success():
    """Test successful tool execution."""
    
    # Create mock tool
    mock_tool = Mock()
    mock_tool.name = "test_tool"
    mock_tool.execute = AsyncMock(return_value={
        "success": True,
        "data": {"result": "test_value"}
    })
    
    # Create executor
    executor = ToolExecutor([mock_tool])
    
    # Execute tool
    result = await executor.execute_tool("test_tool", {"arg1": "value1"})
    
    # Verify
    assert result["success"] is True
    assert result["data"]["result"] == "test_value"
    mock_tool.execute.assert_called_once_with(arg1="value1")


@pytest.mark.asyncio
async def test_tool_execution_failure():
    """Test tool execution failure."""
    
    # Create mock tool that fails
    mock_tool = Mock()
    mock_tool.name = "test_tool"
    mock_tool.execute = AsyncMock(side_effect=Exception("Tool failed"))
    
    # Create executor
    executor = ToolExecutor([mock_tool])
    
    # Execute tool - should raise error
    with pytest.raises(ToolExecutionError):
        await executor.execute_tool("test_tool", {})


@pytest.mark.asyncio
async def test_tool_not_found():
    """Test tool not found error."""
    
    executor = ToolExecutor([])
    
    with pytest.raises(ToolExecutionError, match="Tool not found"):
        await executor.execute_tool("nonexistent_tool", {})
```

## Phase 5: Documentation and Cleanup (Priority 3)

### 5.1 Update README

**File**: `python/src/beeai_agents/README.md`

Create comprehensive usage documentation with:
- Installation instructions
- Configuration guide
- Usage examples
- API reference
- Troubleshooting guide

### 5.2 Remove Unnecessary Files

Delete files created during exploration:
- `python/src/beeai_production.py`
- `python/src/run_beeai_validation.py`
- `python/src/quick_start_beeai.py`
- `python/src/test_beeai_basic.py`

## Implementation Checklist

### Phase 1: Tool Execution (Day 1)
- [ ] Create `tool_executor.py` with ToolExecutor class
- [ ] Update orchestrator to initialize tool executor
- [ ] Replace mock execution with real tool calls
- [ ] Test tool execution with simple MCP tool
- [ ] Verify error handling and retry logic

### Phase 2: Discovery (Day 1-2)
- [ ] Update discovery agent to accept MCP tools
- [ ] Implement real discovery execution
- [ ] Update orchestrator to pass tools to discovery agent
- [ ] Test discovery with real VM
- [ ] Verify discovery results parsing

### Phase 3: Acceptance Criteria (Day 2)
- [ ] Create `acceptance_loader.py`
- [ ] Integrate loader into orchestrator
- [ ] Update validation to use acceptance criteria
- [ ] Test with acceptance criteria files
- [ ] Verify expected vs actual comparison

### Phase 4: Testing (Day 2-3)
- [ ] Create integration test
- [ ] Create unit tests for tool executor
- [ ] Test with real MCP server
- [ ] Test with multiple resource types
- [ ] Verify end-to-end workflow

### Phase 5: Documentation (Day 3)
- [ ] Create comprehensive README
- [ ] Document configuration options
- [ ] Add usage examples
- [ ] Create troubleshooting guide
- [ ] Clean up temporary files

## Success Criteria

The implementation is complete when:

1. ✅ Real MCP tools are executed (not mocked)
2. ✅ Discovery returns actual workload data
3. ✅ Validation uses acceptance criteria
4. ✅ All checks produce real results
5. ✅ Integration test passes end-to-end
6. ✅ Documentation is complete
7. ✅ No mock/placeholder code remains

## Risk Mitigation

### Risk 1: MCP Tool Interface Changes
**Mitigation**: Test with actual MCP server early, adjust interface as needed

### Risk 2: Tool Result Format Variations
**Mitigation**: Implement flexible result parsing, handle multiple formats

### Risk 3: Acceptance Criteria Mismatches
**Mitigation**: Validate criteria files, provide clear error messages

### Risk 4: Performance Issues
**Mitigation**: Implement parallel execution, add timeouts, optimize tool calls

## Next Steps After Completion

1. **Performance Optimization**
   - Implement parallel check execution
   - Add caching for repeated tool calls
   - Optimize memory usage

2. **Enhanced Features**
   - Add custom tool wrappers
   - Implement advanced comparison logic
   - Add trend analysis

3. **Production Readiness**
   - Add comprehensive logging
   - Implement metrics collection
   - Add health checks

4. **Migration**
   - Gradually migrate from Pydantic AI system
   - Run both systems in parallel
   - Validate results match
   - Complete cutover

## Conclusion

This plan provides a clear path to completing the BeeAI implementation. The work is straightforward because the architecture is solid - we're just filling in the missing pieces. Following this plan will result in a production-ready BeeAI-based validation system that properly executes MCP tools and validates real infrastructure.