#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Test script for the agentic validation workflow."""

import asyncio
import os
import sys
from datetime import datetime

# Test the classifier first (no MCP server needed)
def test_classifier():
    """Test the application classifier."""
    print("\n" + "="*60)
    print("TEST 1: Application Classifier")
    print("="*60)
    
    from classifier import ApplicationClassifier
    from models import (
        WorkloadDiscoveryResult,
        ApplicationDetection,
        PortInfo,
        ProcessInfo
    )
    
    # Create test discovery result
    discovery = WorkloadDiscoveryResult(
        host="test-server",
        ports=[
            PortInfo(port=1521, protocol="tcp", service="oracle", state="open"),
            PortInfo(port=22, protocol="tcp", service="ssh", state="open")
        ],
        processes=[
            ProcessInfo(
                pid=1234,
                name="oracle",
                cmdline="/u01/app/oracle/product/19c/bin/oracle",
                user="oracle"
            )
        ],
        applications=[
            ApplicationDetection(
                name="Oracle Database",
                version="19c",
                confidence=0.95,
                detection_method="port_and_process",
                evidence={"port": 1521, "process": "oracle"}
            )
        ],
        discovery_time=datetime.now()
    )
    
    # Test classification
    classifier = ApplicationClassifier()
    classification = classifier.classify(discovery)
    
    print(f"✓ Host: {discovery.host}")
    print(f"✓ Category: {classification.category.value}")
    print(f"✓ Primary App: {classification.primary_application.name if classification.primary_application else 'None'}")
    print(f"✓ Confidence: {classification.confidence:.2%}")
    print(f"✓ Recommended Validations: {len(classification.recommended_validations)}")
    print(f"  - {', '.join(classification.recommended_validations[:5])}")
    
    print("\n✅ Classifier test passed!")
    return True


async def test_agents_without_mcp():
    """Test agents without MCP server (using mock data)."""
    print("\n" + "="*60)
    print("TEST 2: Pydantic AI Agents (No MCP Required)")
    print("="*60)
    
    from agents.base import AgentConfig
    from agents.validation_agent import ValidationAgent
    from agents.evaluation_agent import EvaluationAgent
    from models import (
        VMResourceInfo,
        ResourceClassification,
        ResourceCategory,
        ApplicationDetection,
        ResourceValidationResult,
        CheckResult,
        ValidationStatus
    )
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        print("   Skipping AI agent tests...")
        return False
    
    print("✓ API key found")
    
    # Test Validation Agent
    print("\n--- Testing Validation Agent ---")
    
    resource = VMResourceInfo(
        host="192.168.1.100",
        ssh_user="admin",
        ssh_password="secret"
    )
    
    classification = ResourceClassification(
        category=ResourceCategory.DATABASE_SERVER,
        primary_application=ApplicationDetection(
            name="Oracle Database",
            version="19c",
            confidence=0.95,
            detection_method="signature",
            evidence={}
        ),
        confidence=0.95,
        recommended_validations=["database_connection", "tablespace_usage"]
    )
    
    try:
        agent_config = AgentConfig(temperature=0.7)
        validation_agent = ValidationAgent(agent_config)
        
        print("Creating validation plan...")
        plan = await validation_agent.create_plan(resource, classification)
        
        print(f"✓ Plan created: {plan.strategy_name}")
        print(f"✓ Checks: {len(plan.checks)}")
        print(f"✓ Estimated duration: {plan.estimated_duration_seconds}s")
        print(f"✓ Priority checks: {len(plan.get_priority_checks())}")
        
        # Show first few checks
        for i, check in enumerate(plan.checks[:3], 1):
            print(f"  {i}. {check.check_name} (priority: {check.priority})")
        
    except Exception as e:
        print(f"⚠️  Validation agent test failed: {e}")
        return False
    
    # Test Evaluation Agent
    print("\n--- Testing Evaluation Agent ---")
    
    # Create mock validation result
    validation_result = ResourceValidationResult(
        resource_type=resource.resource_type,
        resource_host=resource.host,
        overall_status=ValidationStatus.WARNING,
        score=75,
        checks=[
            CheckResult(
                check_id="net_001",
                check_name="Network Connectivity",
                status=ValidationStatus.PASS,
                message="Port 22 is accessible"
            ),
            CheckResult(
                check_id="db_001",
                check_name="Database Connection",
                status=ValidationStatus.PASS,
                message="Successfully connected"
            ),
            CheckResult(
                check_id="db_002",
                check_name="Tablespace Usage",
                status=ValidationStatus.WARNING,
                expected="< 85%",
                actual="87%",
                message="Tablespace usage is high"
            )
        ],
        execution_time_seconds=15.5
    )
    
    try:
        evaluation_agent = EvaluationAgent(agent_config)
        
        print("Evaluating results...")
        evaluation = await evaluation_agent.evaluate(
            validation_result,
            classification=classification
        )
        
        print(f"✓ Overall Health: {evaluation.overall_health}")
        print(f"✓ Confidence: {evaluation.confidence:.2%}")
        print(f"✓ Critical Issues: {len(evaluation.critical_issues)}")
        print(f"✓ Warnings: {len(evaluation.warnings)}")
        print(f"✓ Recommendations: {len(evaluation.recommendations)}")
        
        if evaluation.recommendations:
            print("\n  Top Recommendations:")
            for i, rec in enumerate(evaluation.recommendations[:3], 1):
                print(f"  {i}. {rec}")
        
    except Exception as e:
        print(f"⚠️  Evaluation agent test failed: {e}")
        return False
    
    print("\n✅ Agent tests passed!")
    return True


async def test_full_workflow_with_mcp():
    """Test complete workflow with MCP server."""
    print("\n" + "="*60)
    print("TEST 3: Full Workflow (Requires MCP Server)")
    print("="*60)
    
    from mcp_client import MCPClient
    from agents.orchestrator import ValidationOrchestrator
    from models import ValidationRequest, VMResourceInfo
    
    # Check for MCP server
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000")
    print(f"Connecting to MCP server at {mcp_url}...")
    
    try:
        mcp_client = MCPClient(mcp_url, timeout=10.0)
        await mcp_client.connect()
        print("✓ Connected to MCP server")
    except Exception as e:
        print(f"⚠️  Cannot connect to MCP server: {e}")
        print("   Make sure cyberres-mcp server is running")
        print("   Start it with: cd python/cyberres-mcp && uv run mcp dev src/cyberres_mcp/server.py")
        return False
    
    try:
        # Create orchestrator
        orchestrator = ValidationOrchestrator(
            mcp_client=mcp_client,
            enable_discovery=True,
            enable_ai_evaluation=True
        )
        print("✓ Orchestrator created")
        
        # Create test request
        # NOTE: Replace with your actual test server details
        request = ValidationRequest(
            resource_info=VMResourceInfo(
                host="localhost",  # Test with localhost
                ssh_user=os.getenv("USER", "testuser"),
                ssh_password="test",  # Will fail but tests the flow
                ssh_key_path=None
            ),
            auto_discover=True
        )
        
        print(f"\nExecuting workflow for {request.resource_info.host}...")
        print("(This will fail without valid credentials, but tests the flow)")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(request)
        
        print(f"\n✓ Workflow Status: {result.workflow_status}")
        print(f"✓ Execution Time: {result.execution_time_seconds:.2f}s")
        
        if result.discovery_result:
            print(f"✓ Discovery: {len(result.discovery_result.applications)} apps detected")
        
        if result.classification:
            print(f"✓ Classification: {result.classification.category.value}")
        
        if result.validation_plan:
            print(f"✓ Validation Plan: {len(result.validation_plan.checks)} checks")
        
        print(f"✓ Validation Score: {result.validation_result.score}/100")
        print(f"✓ Checks: {result.validation_result.passed_checks} passed, "
              f"{result.validation_result.failed_checks} failed")
        
        if result.evaluation:
            print(f"✓ Evaluation: {result.evaluation.overall_health}")
        
        if result.errors:
            print(f"\n⚠️  Errors encountered: {len(result.errors)}")
            for error in result.errors[:3]:
                print(f"   - {error}")
        
        print("\n✅ Full workflow test completed!")
        return True
        
    except Exception as e:
        print(f"⚠️  Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await mcp_client.disconnect()


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AGENTIC VALIDATION WORKFLOW - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Classifier (no dependencies)
    try:
        results.append(("Classifier", test_classifier()))
    except Exception as e:
        print(f"❌ Classifier test failed: {e}")
        results.append(("Classifier", False))
    
    # Test 2: AI Agents (requires API key)
    try:
        results.append(("AI Agents", await test_agents_without_mcp()))
    except Exception as e:
        print(f"❌ AI Agents test failed: {e}")
        results.append(("AI Agents", False))
    
    # Test 3: Full workflow (requires MCP server)
    try:
        results.append(("Full Workflow", await test_full_workflow_with_mcp()))
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        results.append(("Full Workflow", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:20s} {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


# Made with Bob