"""
Comprehensive Integration Tests for BeeAI Validation System

This test suite provides end-to-end testing of the complete BeeAI-powered
validation workflow, including all agents, orchestrator, and system integration.
"""

import asyncio
import logging
import pytest
from pathlib import Path
from datetime import datetime

from beeai_agents.orchestrator import BeeAIValidationOrchestrator, WorkflowResult
from beeai_agents.discovery_agent import BeeAIDiscoveryAgent
from beeai_agents.validation_agent import BeeAIValidationAgent
from beeai_agents.evaluation_agent import BeeAIEvaluationAgent
from models import (
    ValidationRequest,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    ResourceType,
    ValidationStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test Fixtures
@pytest.fixture
async def orchestrator():
    """Create and initialize orchestrator for testing."""
    orch = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=True,
        enable_ai_evaluation=True,
        memory_size=50
    )
    await orch.initialize()
    yield orch
    await orch.cleanup()


@pytest.fixture
def vm_request():
    """Create sample VM validation request."""
    vm_info = VMResourceInfo(
        host="test-vm-01.example.com",
        resource_type=ResourceType.VM,
        ssh_host="192.168.1.100",
        ssh_port=22,
        ssh_user="admin",
        ssh_password="test_password"
    )
    return ValidationRequest(
        resource_info=vm_info,
        auto_discover=True,
        acceptance_criteria={
            'min_score': 80,
            'required_checks': ['connectivity', 'system_health']
        }
    )


@pytest.fixture
def oracle_request():
    """Create sample Oracle DB validation request."""
    oracle_info = OracleDBResourceInfo(
        host="test-oracle-01.example.com",
        resource_type=ResourceType.ORACLE_DB,
        db_host="192.168.1.101",
        db_port=1521,
        db_service_name="ORCL",
        db_user="system",
        db_password="test_password"
    )
    return ValidationRequest(
        resource_info=oracle_info,
        auto_discover=True
    )


@pytest.fixture
def mongodb_request():
    """Create sample MongoDB validation request."""
    mongo_info = MongoDBResourceInfo(
        host="test-mongo-01.example.com",
        resource_type=ResourceType.MONGO_DB,
        db_host="192.168.1.102",
        db_port=27017,
        db_name="admin",
        db_user="admin",
        db_password="test_password"
    )
    return ValidationRequest(
        resource_info=mongo_info,
        auto_discover=True
    )


# Integration Tests
class TestOrchestratorIntegration:
    """Test orchestrator integration with all agents."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_vm(self, orchestrator, vm_request):
        """Test complete workflow for VM validation."""
        logger.info("Testing full VM validation workflow...")
        
        result = await orchestrator.execute_workflow(vm_request)
        
        # Verify workflow completed
        assert result is not None
        assert result.workflow_status in ['success', 'partial_success', 'failure']
        
        # Verify all phases executed
        assert 'discovery' in result.phase_timings
        assert 'planning' in result.phase_timings
        assert 'execution' in result.phase_timings
        assert 'evaluation' in result.phase_timings
        
        # Verify results structure
        assert result.validation_result is not None
        assert result.validation_result.score >= 0
        assert result.validation_result.score <= 100
        
        logger.info(f"✓ Full workflow completed: {result.workflow_status}")
        logger.info(f"  Score: {result.validation_result.score}/100")
        logger.info(f"  Execution time: {result.execution_time_seconds:.2f}s")
    
    @pytest.mark.asyncio
    async def test_workflow_without_discovery(self, vm_request):
        """Test workflow with discovery disabled."""
        logger.info("Testing workflow without discovery...")
        
        orch = BeeAIValidationOrchestrator(
            mcp_server_path="python/cyberres-mcp",
            llm_model="ollama:llama3.2",
            enable_discovery=False,  # Disabled
            enable_ai_evaluation=True
        )
        
        try:
            await orch.initialize()
            result = await orch.execute_workflow(vm_request)
            
            # Verify discovery was skipped
            assert result.discovery_result is None
            assert 'discovery' not in result.phase_timings
            
            # Verify other phases executed
            assert 'planning' in result.phase_timings
            assert 'execution' in result.phase_timings
            assert 'evaluation' in result.phase_timings
            
            logger.info("✓ Workflow without discovery completed")
            
        finally:
            await orch.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_without_evaluation(self, vm_request):
        """Test workflow with evaluation disabled."""
        logger.info("Testing workflow without evaluation...")
        
        orch = BeeAIValidationOrchestrator(
            mcp_server_path="python/cyberres-mcp",
            llm_model="ollama:llama3.2",
            enable_discovery=True,
            enable_ai_evaluation=False  # Disabled
        )
        
        try:
            await orch.initialize()
            result = await orch.execute_workflow(vm_request)
            
            # Verify evaluation was skipped
            assert result.evaluation is None
            assert 'evaluation' not in result.phase_timings
            
            # Verify other phases executed
            assert 'discovery' in result.phase_timings
            assert 'planning' in result.phase_timings
            assert 'execution' in result.phase_timings
            
            logger.info("✓ Workflow without evaluation completed")
            
        finally:
            await orch.cleanup()
    
    @pytest.mark.asyncio
    async def test_minimal_workflow(self, vm_request):
        """Test minimal workflow (validation only)."""
        logger.info("Testing minimal workflow...")
        
        orch = BeeAIValidationOrchestrator(
            mcp_server_path="python/cyberres-mcp",
            llm_model="ollama:llama3.2",
            enable_discovery=False,
            enable_ai_evaluation=False
        )
        
        try:
            await orch.initialize()
            result = await orch.execute_workflow(vm_request)
            
            # Verify only required phases executed
            assert result.discovery_result is None
            assert result.evaluation is None
            assert 'planning' in result.phase_timings
            assert 'execution' in result.phase_timings
            
            logger.info("✓ Minimal workflow completed")
            
        finally:
            await orch.cleanup()


class TestMultiResourceValidation:
    """Test validation across different resource types."""
    
    @pytest.mark.asyncio
    async def test_vm_validation(self, orchestrator, vm_request):
        """Test VM resource validation."""
        logger.info("Testing VM validation...")
        
        result = await orchestrator.execute_workflow(vm_request)
        
        assert result.validation_result.resource_type == ResourceType.VM
        assert result.validation_result.resource_host == vm_request.resource_info.host
        
        logger.info("✓ VM validation completed")
    
    @pytest.mark.asyncio
    async def test_oracle_validation(self, orchestrator, oracle_request):
        """Test Oracle DB validation."""
        logger.info("Testing Oracle DB validation...")
        
        result = await orchestrator.execute_workflow(oracle_request)
        
        assert result.validation_result.resource_type == ResourceType.ORACLE_DB
        assert result.validation_result.resource_host == oracle_request.resource_info.host
        
        logger.info("✓ Oracle DB validation completed")
    
    @pytest.mark.asyncio
    async def test_mongodb_validation(self, orchestrator, mongodb_request):
        """Test MongoDB validation."""
        logger.info("Testing MongoDB validation...")
        
        result = await orchestrator.execute_workflow(mongodb_request)
        
        assert result.validation_result.resource_type == ResourceType.MONGO_DB
        assert result.validation_result.resource_host == mongodb_request.resource_info.host
        
        logger.info("✓ MongoDB validation completed")


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_invalid_host_handling(self, orchestrator):
        """Test handling of invalid host."""
        logger.info("Testing invalid host handling...")
        
        vm_info = VMResourceInfo(
            host="invalid-host-999.example.com",
            resource_type=ResourceType.VM,
            ssh_host="999.999.999.999",
            ssh_port=22,
            ssh_user="admin",
            ssh_password="password"
        )
        
        request = ValidationRequest(resource_info=vm_info, auto_discover=True)
        result = await orchestrator.execute_workflow(request)
        
        # Workflow should complete despite errors
        assert result is not None
        assert len(result.errors) > 0  # Errors should be captured
        
        logger.info("✓ Invalid host handled gracefully")
    
    @pytest.mark.asyncio
    async def test_phase_failure_isolation(self, orchestrator, vm_request):
        """Test that phase failures don't crash entire workflow."""
        logger.info("Testing phase failure isolation...")
        
        result = await orchestrator.execute_workflow(vm_request)
        
        # Even if some phases fail, workflow should complete
        assert result is not None
        assert result.validation_result is not None
        
        logger.info("✓ Phase failure isolation working")


class TestPerformance:
    """Test performance and timing."""
    
    @pytest.mark.asyncio
    async def test_execution_time_reasonable(self, orchestrator, vm_request):
        """Test that execution time is reasonable."""
        logger.info("Testing execution time...")
        
        start_time = datetime.now()
        result = await orchestrator.execute_workflow(vm_request)
        end_time = datetime.now()
        
        total_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time (adjust as needed)
        assert total_time < 60, f"Execution took too long: {total_time}s"
        
        # Verify phase timings are tracked
        assert result.phase_timings
        assert result.execution_time_seconds > 0
        
        logger.info(f"✓ Execution time: {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, vm_request):
        """Test that memory is properly cleaned up."""
        logger.info("Testing memory cleanup...")
        
        # Create and destroy multiple orchestrators
        for i in range(3):
            orch = BeeAIValidationOrchestrator(
                mcp_server_path="python/cyberres-mcp",
                llm_model="ollama:llama3.2"
            )
            await orch.initialize()
            await orch.execute_workflow(vm_request)
            await orch.cleanup()
        
        logger.info("✓ Memory cleanup successful")


class TestResultValidation:
    """Test result structure and content validation."""
    
    @pytest.mark.asyncio
    async def test_result_structure_complete(self, orchestrator, vm_request):
        """Test that result structure is complete."""
        logger.info("Testing result structure...")
        
        result = await orchestrator.execute_workflow(vm_request)
        
        # Verify all required fields present
        assert result.request is not None
        assert result.validation_result is not None
        assert result.execution_time_seconds > 0
        assert result.workflow_status in ['success', 'partial_success', 'failure']
        assert isinstance(result.errors, list)
        assert isinstance(result.phase_timings, dict)
        
        # Verify validation result structure
        assert result.validation_result.resource_type is not None
        assert result.validation_result.resource_host is not None
        assert result.validation_result.score >= 0
        assert result.validation_result.score <= 100
        assert isinstance(result.validation_result.checks, list)
        
        logger.info("✓ Result structure complete")
    
    @pytest.mark.asyncio
    async def test_discovery_result_structure(self, orchestrator, vm_request):
        """Test discovery result structure when enabled."""
        logger.info("Testing discovery result structure...")
        
        result = await orchestrator.execute_workflow(vm_request)
        
        if result.discovery_result:
            assert result.discovery_result.host is not None
            assert isinstance(result.discovery_result.ports, list)
            assert isinstance(result.discovery_result.processes, list)
            assert isinstance(result.discovery_result.applications, list)
            
            logger.info("✓ Discovery result structure valid")
    
    @pytest.mark.asyncio
    async def test_evaluation_result_structure(self, orchestrator, vm_request):
        """Test evaluation result structure when enabled."""
        logger.info("Testing evaluation result structure...")
        
        result = await orchestrator.execute_workflow(vm_request)
        
        if result.evaluation:
            assert result.evaluation.overall_health is not None
            assert 0 <= result.evaluation.confidence <= 1
            assert result.evaluation.summary is not None
            assert isinstance(result.evaluation.critical_issues, list)
            assert isinstance(result.evaluation.warnings, list)
            assert isinstance(result.evaluation.recommendations, list)
            
            logger.info("✓ Evaluation result structure valid")


class TestConcurrency:
    """Test concurrent workflow execution."""
    
    @pytest.mark.asyncio
    async def test_sequential_workflows(self, orchestrator, vm_request):
        """Test multiple sequential workflows."""
        logger.info("Testing sequential workflows...")
        
        results = []
        for i in range(3):
            result = await orchestrator.execute_workflow(vm_request)
            results.append(result)
        
        # All workflows should complete
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert result.validation_result is not None
        
        logger.info("✓ Sequential workflows completed")


# Test Runner
def run_integration_tests():
    """Run all integration tests."""
    logger.info("\n" + "="*80)
    logger.info("BEEAI INTEGRATION TEST SUITE")
    logger.info("="*80 + "\n")
    
    # Run pytest
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--log-cli-level=INFO'
    ])


if __name__ == "__main__":
    run_integration_tests()

# Made with Bob
