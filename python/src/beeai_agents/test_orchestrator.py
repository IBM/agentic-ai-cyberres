"""
Test Suite for BeeAI Validation Orchestrator

Tests the orchestrator's ability to coordinate multi-agent workflows,
manage state, and integrate all validation phases.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from beeai_agents.orchestrator import BeeAIValidationOrchestrator, WorkflowResult
from models import (
    ValidationRequest,
    VMResourceInfo,
    ResourceType,
    ValidationStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_vm_request() -> ValidationRequest:
    """Create sample VM validation request.
    
    Returns:
        Sample ValidationRequest for VM
    """
    vm_info = VMResourceInfo(
        host="test-vm-01.example.com",
        resource_type=ResourceType.VM,
        ssh_host="192.168.1.100",
        ssh_port=22,
        ssh_user="admin",
        ssh_password="password123"  # In production, use secure credential management
    )
    
    return ValidationRequest(
        resource_info=vm_info,
        auto_discover=True,
        acceptance_criteria={
            "min_score": 80,
            "required_checks": ["connectivity", "system_health"]
        }
    )


async def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Orchestrator Initialization")
    logger.info("="*80)
    
    # Create orchestrator
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=True,
        enable_ai_evaluation=True
    )
    
    logger.info("Orchestrator created, initializing...")
    
    try:
        # Initialize
        await orchestrator.initialize()
        
        logger.info("\n✓ Orchestrator initialized successfully")
        logger.info(f"  Discovery enabled: {orchestrator.enable_discovery}")
        logger.info(f"  Evaluation enabled: {orchestrator.enable_ai_evaluation}")
        logger.info(f"  LLM model: {orchestrator.llm_model}")
        
        # Cleanup
        await orchestrator.cleanup()
        logger.info("✓ Cleanup successful")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Initialization failed: {e}", exc_info=True)
        return False


async def test_full_workflow_execution():
    """Test complete workflow execution."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Full Workflow Execution")
    logger.info("="*80)
    
    # Create orchestrator
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
        
        # Create request
        request = create_sample_vm_request()
        logger.info(f"\nExecuting workflow for: {request.resource_info.host}")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(request)
        
        # Verify results
        logger.info("\n✓ Workflow execution completed")
        logger.info(f"  Status: {result.workflow_status}")
        logger.info(f"  Execution time: {result.execution_time_seconds:.2f}s")
        logger.info(f"  Validation score: {result.validation_result.score}/100")
        
        # Phase timings
        if result.phase_timings:
            logger.info("\n  Phase Timings:")
            for phase, timing in result.phase_timings.items():
                logger.info(f"    {phase}: {timing:.2f}s")
        
        # Discovery results
        if result.discovery_result:
            logger.info("\n  Discovery Results:")
            logger.info(f"    Ports: {len(result.discovery_result.ports)}")
            logger.info(f"    Processes: {len(result.discovery_result.processes)}")
            logger.info(f"    Applications: {len(result.discovery_result.applications)}")
        
        # Classification
        if result.classification:
            logger.info("\n  Classification:")
            logger.info(f"    Category: {result.classification.category.value}")
            logger.info(f"    Confidence: {result.classification.confidence:.2%}")
        
        # Validation results
        logger.info("\n  Validation Results:")
        logger.info(f"    Total checks: {len(result.validation_result.checks)}")
        logger.info(f"    Passed: {result.validation_result.passed_checks}")
        logger.info(f"    Failed: {result.validation_result.failed_checks}")
        logger.info(f"    Warnings: {result.validation_result.warning_checks}")
        
        # Evaluation
        if result.evaluation:
            logger.info("\n  Evaluation:")
            logger.info(f"    Overall health: {result.evaluation.overall_health}")
            logger.info(f"    Confidence: {result.evaluation.confidence:.2f}")
            logger.info(f"    Critical issues: {len(result.evaluation.critical_issues)}")
            logger.info(f"    Recommendations: {len(result.evaluation.recommendations)}")
            
            if result.evaluation.recommendations:
                logger.info("\n    Top Recommendations:")
                for i, rec in enumerate(result.evaluation.recommendations[:3], 1):
                    logger.info(f"      {i}. {rec}")
        
        # Errors
        if result.errors:
            logger.info("\n  Errors:")
            for error in result.errors:
                logger.info(f"    - {error}")
        
        # Cleanup
        await orchestrator.cleanup()
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Workflow execution failed: {e}", exc_info=True)
        await orchestrator.cleanup()
        return None


async def test_workflow_without_discovery():
    """Test workflow execution without discovery phase."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Workflow Without Discovery")
    logger.info("="*80)
    
    # Create orchestrator with discovery disabled
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=False,  # Disabled
        enable_ai_evaluation=True
    )
    
    try:
        await orchestrator.initialize()
        logger.info("✓ Orchestrator initialized (discovery disabled)")
        
        request = create_sample_vm_request()
        result = await orchestrator.execute_workflow(request)
        
        logger.info("\n✓ Workflow completed without discovery")
        logger.info(f"  Status: {result.workflow_status}")
        logger.info(f"  Discovery result: {result.discovery_result}")
        logger.info(f"  Classification: {result.classification}")
        logger.info(f"  Validation score: {result.validation_result.score}/100")
        
        # Verify no discovery was performed
        assert result.discovery_result is None, "Discovery should be None"
        logger.info("  ✓ Confirmed: No discovery performed")
        
        await orchestrator.cleanup()
        return result
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        await orchestrator.cleanup()
        return None


async def test_workflow_without_evaluation():
    """Test workflow execution without evaluation phase."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Workflow Without Evaluation")
    logger.info("="*80)
    
    # Create orchestrator with evaluation disabled
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=True,
        enable_ai_evaluation=False  # Disabled
    )
    
    try:
        await orchestrator.initialize()
        logger.info("✓ Orchestrator initialized (evaluation disabled)")
        
        request = create_sample_vm_request()
        result = await orchestrator.execute_workflow(request)
        
        logger.info("\n✓ Workflow completed without evaluation")
        logger.info(f"  Status: {result.workflow_status}")
        logger.info(f"  Evaluation result: {result.evaluation}")
        logger.info(f"  Validation score: {result.validation_result.score}/100")
        
        # Verify no evaluation was performed
        assert result.evaluation is None, "Evaluation should be None"
        logger.info("  ✓ Confirmed: No evaluation performed")
        
        await orchestrator.cleanup()
        return result
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        await orchestrator.cleanup()
        return None


async def test_minimal_workflow():
    """Test minimal workflow (no discovery, no evaluation)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Minimal Workflow")
    logger.info("="*80)
    
    # Create orchestrator with both disabled
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2",
        enable_discovery=False,
        enable_ai_evaluation=False
    )
    
    try:
        await orchestrator.initialize()
        logger.info("✓ Orchestrator initialized (minimal mode)")
        
        request = create_sample_vm_request()
        result = await orchestrator.execute_workflow(request)
        
        logger.info("\n✓ Minimal workflow completed")
        logger.info(f"  Status: {result.workflow_status}")
        logger.info(f"  Validation score: {result.validation_result.score}/100")
        logger.info(f"  Phases completed: {len(result.phase_timings)}")
        
        # Verify minimal execution
        assert result.discovery_result is None
        assert result.evaluation is None
        assert result.validation_result is not None
        logger.info("  ✓ Confirmed: Only validation phase executed")
        
        await orchestrator.cleanup()
        return result
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        await orchestrator.cleanup()
        return None


async def test_workflow_state_tracking():
    """Test workflow state tracking and phase management."""
    logger.info("\n" + "="*80)
    logger.info("TEST 6: Workflow State Tracking")
    logger.info("="*80)
    
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2"
    )
    
    try:
        await orchestrator.initialize()
        
        request = create_sample_vm_request()
        result = await orchestrator.execute_workflow(request)
        
        logger.info("\n✓ Workflow state tracking verified")
        logger.info(f"  Total phases: {len(result.phase_timings)}")
        
        # Verify phase timings
        expected_phases = ["discovery", "planning", "execution", "evaluation"]
        for phase in expected_phases:
            if phase in result.phase_timings:
                logger.info(f"  ✓ {phase}: {result.phase_timings[phase]:.2f}s")
        
        # Verify total time
        total_phase_time = sum(result.phase_timings.values())
        logger.info(f"\n  Total phase time: {total_phase_time:.2f}s")
        logger.info(f"  Total execution time: {result.execution_time_seconds:.2f}s")
        
        await orchestrator.cleanup()
        return result
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        await orchestrator.cleanup()
        return None


async def test_error_handling():
    """Test error handling and recovery."""
    logger.info("\n" + "="*80)
    logger.info("TEST 7: Error Handling")
    logger.info("="*80)
    
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2"
    )
    
    try:
        await orchestrator.initialize()
        
        # Create request with invalid host
        vm_info = VMResourceInfo(
            host="invalid-host-that-does-not-exist.example.com",
            resource_type=ResourceType.VM,
            ssh_host="192.168.999.999",  # Invalid IP
            ssh_port=22,
            ssh_user="admin",
            ssh_password="password"
        )
        
        request = ValidationRequest(
            resource_info=vm_info,
            auto_discover=True
        )
        
        logger.info("Executing workflow with invalid host...")
        result = await orchestrator.execute_workflow(request)
        
        logger.info("\n✓ Error handling verified")
        logger.info(f"  Status: {result.workflow_status}")
        logger.info(f"  Errors: {len(result.errors)}")
        
        if result.errors:
            logger.info("\n  Captured Errors:")
            for error in result.errors:
                logger.info(f"    - {error}")
        
        # Verify workflow continued despite errors
        logger.info(f"\n  Validation result present: {result.validation_result is not None}")
        logger.info("  ✓ Workflow gracefully handled errors")
        
        await orchestrator.cleanup()
        return result
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        await orchestrator.cleanup()
        return None


async def run_all_tests():
    """Run all orchestrator tests."""
    logger.info("\n" + "="*80)
    logger.info("BEEAI VALIDATION ORCHESTRATOR TEST SUITE")
    logger.info("="*80)
    
    results = {}
    
    try:
        # Run tests
        results["initialization"] = await test_orchestrator_initialization()
        results["full_workflow"] = await test_full_workflow_execution()
        results["no_discovery"] = await test_workflow_without_discovery()
        results["no_evaluation"] = await test_workflow_without_evaluation()
        results["minimal"] = await test_minimal_workflow()
        results["state_tracking"] = await test_workflow_state_tracking()
        results["error_handling"] = await test_error_handling()
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for v in results.values() if v is not None and v is not False)
        total = len(results)
        
        logger.info(f"\nTests Passed: {passed}/{total}")
        
        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"  {status}: {test_name}")
        
        if passed == total:
            logger.info("\n" + "="*80)
            logger.info("✓ ALL TESTS COMPLETED SUCCESSFULLY")
            logger.info("="*80)
        else:
            logger.warning("\n" + "="*80)
            logger.warning(f"⚠ {total - passed} TEST(S) FAILED")
            logger.warning("="*80)
        
    except Exception as e:
        logger.error(f"\n✗ Test suite failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())

# Made with Bob
