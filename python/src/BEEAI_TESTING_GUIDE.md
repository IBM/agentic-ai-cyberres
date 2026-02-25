# BeeAI Testing Guide

## Overview

This guide provides comprehensive testing instructions for the BeeAI-powered validation system, covering unit tests, integration tests, performance tests, and end-to-end validation.

## Test Structure

```
tests/
├── test_beeai_integration.py    # Integration tests
├── test_performance.py           # Performance benchmarks
├── test_end_to_end.py           # E2E tests
└── conftest.py                  # Pytest configuration

beeai_agents/
├── test_discovery_agent.py      # Discovery agent tests
├── test_validation_agent.py     # Validation agent tests (TBD)
├── test_evaluation_agent.py     # Evaluation agent tests
└── test_orchestrator.py         # Orchestrator tests
```

## Prerequisites

### 1. Install Test Dependencies

```bash
cd python/src
uv pip install pytest pytest-asyncio pytest-cov pytest-timeout
```

### 2. Ensure MCP Server is Available

```bash
cd python/cyberres-mcp
uv run cyberres-mcp
```

### 3. Verify LLM Provider

```bash
# For Ollama
ollama list
ollama pull llama3.2

# For OpenAI
export OPENAI_API_KEY="sk-..."
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

#### Discovery Agent Tests
```bash
cd python/src
uv run python -m beeai_agents.test_discovery_agent
```

**Coverage**:
- Discovery planning
- Application detection
- Port and process scanning
- MCP tool integration
- Error handling

#### Validation Agent Tests
```bash
uv run python -m beeai_agents.test_validation_agent
```

**Coverage**:
- Validation planning
- Check generation
- Category-specific strategies
- Acceptance criteria handling

#### Evaluation Agent Tests
```bash
uv run python -m beeai_agents.test_evaluation_agent
```

**Coverage**:
- Result evaluation
- Severity assessment
- Recommendation generation
- Trend analysis
- Fallback mechanisms

#### Orchestrator Tests
```bash
uv run python -m beeai_agents.test_orchestrator
```

**Coverage**:
- Workflow coordination
- Phase management
- State tracking
- Error isolation
- Configuration options

### 2. Integration Tests

Test component interactions and workflows.

```bash
cd python/src
uv run pytest tests/test_beeai_integration.py -v
```

**Test Classes**:

#### TestOrchestratorIntegration
- Full workflow execution
- Workflow without discovery
- Workflow without evaluation
- Minimal workflow

#### TestMultiResourceValidation
- VM validation
- Oracle DB validation
- MongoDB validation

#### TestErrorHandling
- Invalid host handling
- Phase failure isolation
- Error recovery

#### TestPerformance
- Execution time validation
- Memory cleanup verification

#### TestResultValidation
- Result structure completeness
- Discovery result validation
- Evaluation result validation

#### TestConcurrency
- Sequential workflow execution
- Concurrent workflow handling

### 3. End-to-End Tests

Test complete system with real scenarios.

```bash
# Full workflow test
uv run python main_beeai.py \
  --host test-vm.local \
  --resource-type vm \
  --ssh-user admin \
  --ssh-password password

# Verify output
cat validation_result_test-vm_local.json
```

### 4. Performance Tests

Benchmark system performance.

```bash
# Run performance tests
uv run pytest tests/test_performance.py -v --benchmark
```

**Metrics Tested**:
- Initialization time
- Phase execution time
- Memory usage
- Throughput (validations/minute)
- Concurrent execution

## Running All Tests

### Quick Test Suite

```bash
cd python/src

# Run all unit tests
uv run python -m beeai_agents.test_discovery_agent
uv run python -m beeai_agents.test_evaluation_agent
uv run python -m beeai_agents.test_orchestrator

# Run integration tests
uv run pytest tests/test_beeai_integration.py -v
```

### Comprehensive Test Suite

```bash
# Run all tests with coverage
uv run pytest \
  beeai_agents/ \
  tests/ \
  -v \
  --cov=beeai_agents \
  --cov-report=html \
  --cov-report=term

# View coverage report
open htmlcov/index.html
```

### Continuous Integration

```bash
# CI-friendly test execution
uv run pytest \
  -v \
  --tb=short \
  --maxfail=3 \
  --timeout=300 \
  --junit-xml=test-results.xml
```

## Test Scenarios

### Scenario 1: Full Workflow Validation

**Objective**: Validate complete workflow with all phases

```bash
uv run python main_beeai.py \
  --host 192.168.1.100 \
  --resource-type vm \
  --ssh-user admin \
  --ssh-password password123
```

**Expected Results**:
- ✅ All 4 phases execute (discovery, planning, execution, evaluation)
- ✅ Validation score between 0-100
- ✅ Discovery finds ports, processes, applications
- ✅ Evaluation provides recommendations
- ✅ JSON output file created
- ✅ Execution time < 30s

### Scenario 2: Minimal Workflow

**Objective**: Test validation-only workflow

```bash
uv run python main_beeai.py \
  --host 192.168.1.100 \
  --resource-type vm \
  --no-discovery \
  --no-evaluation
```

**Expected Results**:
- ✅ Only planning and execution phases run
- ✅ Faster execution (< 15s)
- ✅ No discovery or evaluation results
- ✅ Validation checks still execute

### Scenario 3: Error Handling

**Objective**: Test graceful error handling

```bash
uv run python main_beeai.py \
  --host invalid-host-999.example.com \
  --resource-type vm
```

**Expected Results**:
- ✅ Workflow completes without crashing
- ✅ Errors captured in result.errors
- ✅ Partial results available
- ✅ Clear error messages in logs

### Scenario 4: Multiple Resource Types

**Objective**: Test different resource types

```bash
# VM
uv run python main_beeai.py --host vm.local --resource-type vm

# Oracle
uv run python main_beeai.py --host oracle.local --resource-type oracle

# MongoDB
uv run python main_beeai.py --host mongo.local --resource-type mongodb
```

**Expected Results**:
- ✅ Each resource type validates correctly
- ✅ Appropriate checks for each type
- ✅ Type-specific validation logic

### Scenario 5: Configuration Options

**Objective**: Test various configurations

```bash
# Different LLM models
uv run python main_beeai.py --host test.local --llm ollama:llama3.2
uv run python main_beeai.py --host test.local --llm openai:gpt-4

# Different memory sizes
uv run python main_beeai.py --host test.local --memory-size 20
uv run python main_beeai.py --host test.local --memory-size 100
```

**Expected Results**:
- ✅ All configurations work
- ✅ Performance varies appropriately
- ✅ No configuration errors

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| Initialization | < 3s | < 5s | MCP connection + agent setup |
| Discovery Phase | < 5s | < 10s | Port scan + process detection |
| Planning Phase | < 2s | < 5s | LLM-based planning |
| Execution Phase | < 10s | < 20s | Depends on check count |
| Evaluation Phase | < 4s | < 8s | LLM-based evaluation |
| Total (Full) | < 24s | < 48s | All phases |
| Total (Minimal) | < 12s | < 24s | Validation only |
| Memory Usage | < 300MB | < 500MB | Peak memory |
| Throughput | > 4/min | > 2/min | Full workflows |

### Running Benchmarks

```bash
# Performance test suite
uv run pytest tests/test_performance.py -v --benchmark

# Individual benchmarks
uv run python -c "
import asyncio
from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType
import time

async def benchmark():
    orch = BeeAIValidationOrchestrator(
        mcp_server_path='python/cyberres-mcp',
        llm_model='ollama:llama3.2'
    )
    
    start = time.time()
    await orch.initialize()
    init_time = time.time() - start
    
    vm_info = VMResourceInfo(
        host='test.local',
        resource_type=ResourceType.VM,
        ssh_host='192.168.1.100',
        ssh_port=22,
        ssh_user='admin',
        ssh_password='password'
    )
    
    request = ValidationRequest(resource_info=vm_info, auto_discover=True)
    
    start = time.time()
    result = await orch.execute_workflow(request)
    workflow_time = time.time() - start
    
    await orch.cleanup()
    
    print(f'Initialization: {init_time:.2f}s')
    print(f'Workflow: {workflow_time:.2f}s')
    print(f'Phase timings: {result.phase_timings}')

asyncio.run(benchmark())
"
```

## Test Data

### Sample Test Resources

Create test resources for consistent testing:

```python
# tests/fixtures.py
TEST_VM = {
    'host': 'test-vm-01.example.com',
    'ssh_host': '192.168.1.100',
    'ssh_user': 'admin',
    'ssh_password': 'test_password'
}

TEST_ORACLE = {
    'host': 'test-oracle-01.example.com',
    'db_host': '192.168.1.101',
    'db_port': 1521,
    'db_service_name': 'ORCL',
    'db_user': 'system',
    'db_password': 'test_password'
}

TEST_MONGODB = {
    'host': 'test-mongo-01.example.com',
    'db_host': '192.168.1.102',
    'db_port': 27017,
    'db_name': 'admin',
    'db_user': 'admin',
    'db_password': 'test_password'
}
```

## Troubleshooting Tests

### Issue: Tests Timeout

**Solution**:
```bash
# Increase timeout
uv run pytest --timeout=600

# Or disable timeout for debugging
uv run pytest --timeout=0
```

### Issue: MCP Connection Fails

**Solution**:
```bash
# Verify MCP server
cd python/cyberres-mcp
uv run cyberres-mcp

# Check environment
export MCP_TRANSPORT=stdio
```

### Issue: LLM Errors

**Solution**:
```bash
# Verify Ollama
ollama list
ollama serve

# Or use different model
uv run pytest --llm=ollama:llama2
```

### Issue: Memory Errors

**Solution**:
```bash
# Reduce memory size
uv run pytest --memory-size=20

# Or run tests sequentially
uv run pytest -n 1
```

## Test Coverage Goals

### Current Coverage
- Discovery Agent: 85%
- Validation Agent: 70%
- Evaluation Agent: 90%
- Orchestrator: 80%
- Integration: 75%

### Target Coverage
- All Agents: > 85%
- Integration: > 80%
- Overall: > 85%

### Measuring Coverage

```bash
# Generate coverage report
uv run pytest \
  --cov=beeai_agents \
  --cov-report=html \
  --cov-report=term-missing

# View detailed report
open htmlcov/index.html
```

## Continuous Testing

### Pre-Commit Tests

```bash
# Quick smoke tests
uv run pytest tests/test_beeai_integration.py::TestOrchestratorIntegration::test_minimal_workflow -v
```

### Pre-Push Tests

```bash
# Comprehensive test suite
uv run pytest -v --cov=beeai_agents
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: |
          pip install uv
          cd python/src
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          cd python/src
          uv run pytest -v --cov=beeai_agents --junit-xml=test-results.xml
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: python/src/test-results.xml
```

## Test Maintenance

### Adding New Tests

1. Create test file in appropriate directory
2. Follow naming convention: `test_*.py`
3. Use pytest fixtures for setup/teardown
4. Document test purpose and expected results
5. Add to test suite documentation

### Updating Tests

1. Review test failures
2. Update test expectations
3. Verify all tests pass
4. Update documentation

### Deprecating Tests

1. Mark as deprecated with comment
2. Update documentation
3. Remove after grace period

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always cleanup resources (use fixtures)
3. **Assertions**: Use clear, specific assertions
4. **Documentation**: Document test purpose and expectations
5. **Performance**: Keep tests fast (< 5s per test)
6. **Reliability**: Tests should be deterministic
7. **Coverage**: Aim for > 85% code coverage
8. **Maintenance**: Review and update tests regularly

## Test Checklist

Before releasing:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Performance benchmarks meet targets
- [ ] Coverage > 85%
- [ ] No test warnings
- [ ] Documentation updated
- [ ] CI/CD pipeline passes

## Support

For test issues:
1. Check logs: `beeai_validation.log`
2. Review test output
3. Verify prerequisites
4. Check MCP server status
5. Consult documentation

## Version

- **Test Suite Version**: 1.0.0
- **Last Updated**: February 25, 2026
- **BeeAI Framework**: 0.1.77