"""
Test Suite for BeeAI Evaluation Agent

Tests the evaluation agent's ability to assess validation results,
provide severity analysis, and generate actionable recommendations.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from beeai_agents.evaluation_agent import BeeAIEvaluationAgent, OverallEvaluation
from models import (
    ResourceValidationResult,
    CheckResult,
    ValidationStatus,
    ResourceType,
    WorkloadDiscoveryResult,
    DetectedApplication,
    ResourceClassification,
    ResourceCategory
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_validation_result(
    score: int = 85,
    failed_checks: int = 1,
    warning_checks: int = 2
) -> ResourceValidationResult:
    """Create sample validation result for testing.
    
    Args:
        score: Overall validation score
        failed_checks: Number of failed checks
        warning_checks: Number of warning checks
    
    Returns:
        Sample ResourceValidationResult
    """
    checks = []
    
    # Add failed checks
    for i in range(failed_checks):
        checks.append(CheckResult(
            check_id=f"fail_{i}",
            check_name=f"Critical Check {i+1}",
            status=ValidationStatus.FAIL,
            message=f"Check failed: Issue detected in component {i+1}",
            expected="Component operational",
            actual="Component not responding",
            details={"error_code": f"ERR_{i+1}", "timestamp": datetime.now().isoformat()}
        ))
    
    # Add warning checks
    for i in range(warning_checks):
        checks.append(CheckResult(
            check_id=f"warn_{i}",
            check_name=f"Warning Check {i+1}",
            status=ValidationStatus.WARNING,
            message=f"Warning: Performance degradation in area {i+1}",
            details={"threshold": "80%", "current": "75%"}
        ))
    
    # Add passed checks
    passed_count = 10 - failed_checks - warning_checks
    for i in range(max(0, passed_count)):
        checks.append(CheckResult(
            check_id=f"pass_{i}",
            check_name=f"Standard Check {i+1}",
            status=ValidationStatus.PASS,
            message="Check passed successfully"
        ))
    
    return ResourceValidationResult(
        resource_host="test-server-01.example.com",
        resource_type=ResourceType.VM,
        checks=checks,
        score=score,
        passed_checks=len([c for c in checks if c.status == ValidationStatus.PASS]),
        failed_checks=len([c for c in checks if c.status == ValidationStatus.FAIL]),
        warning_checks=len([c for c in checks if c.status == ValidationStatus.WARNING]),
        execution_time_seconds=2.5,
        timestamp=datetime.now()
    )


def create_sample_discovery_result() -> WorkloadDiscoveryResult:
    """Create sample discovery result for context.
    
    Returns:
        Sample WorkloadDiscoveryResult
    """
    return WorkloadDiscoveryResult(
        host="test-server-01.example.com",
        ports=[22, 80, 443, 3306, 8080],
        processes=[
            "nginx", "mysqld", "java", "python", "sshd"
        ],
        applications=[
            DetectedApplication(
                name="MySQL Database",
                version="8.0",
                confidence=0.95,
                detection_method="port_and_process"
            ),
            DetectedApplication(
                name="Nginx Web Server",
                version="1.21",
                confidence=0.90,
                detection_method="port_and_process"
            ),
            DetectedApplication(
                name="Java Application",
                version="11",
                confidence=0.75,
                detection_method="process"
            )
        ],
        timestamp=datetime.now()
    )


def create_sample_classification() -> ResourceClassification:
    """Create sample classification for context.
    
    Returns:
        Sample ResourceClassification
    """
    return ResourceClassification(
        category=ResourceCategory.DATABASE,
        confidence=0.90,
        primary_application=DetectedApplication(
            name="MySQL Database",
            version="8.0",
            confidence=0.95,
            detection_method="port_and_process"
        ),
        reasoning="MySQL database detected on standard port 3306 with mysqld process"
    )


async def test_basic_evaluation():
    """Test basic evaluation functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Basic Evaluation")
    logger.info("="*80)
    
    # Create agent
    agent = BeeAIEvaluationAgent(
        llm_model="ollama:llama3.2",
        temperature=0.3
    )
    
    # Create test data
    validation_result = create_sample_validation_result(score=85, failed_checks=1, warning_checks=2)
    
    logger.info(f"Testing evaluation for validation score: {validation_result.score}/100")
    logger.info(f"Failed checks: {validation_result.failed_checks}")
    logger.info(f"Warning checks: {validation_result.warning_checks}")
    
    # Perform evaluation
    evaluation = await agent.evaluate(validation_result)
    
    # Verify results
    logger.info(f"\n✓ Evaluation completed successfully")
    logger.info(f"  Overall Health: {evaluation.overall_health}")
    logger.info(f"  Confidence: {evaluation.confidence:.2f}")
    logger.info(f"  Critical Issues: {len(evaluation.critical_issues)}")
    logger.info(f"  Warnings: {len(evaluation.warnings)}")
    logger.info(f"  Recommendations: {len(evaluation.recommendations)}")
    logger.info(f"  Check Assessments: {len(evaluation.check_assessments)}")
    
    logger.info(f"\n  Summary: {evaluation.summary[:200]}...")
    
    if evaluation.recommendations:
        logger.info(f"\n  Top Recommendations:")
        for i, rec in enumerate(evaluation.recommendations[:3], 1):
            logger.info(f"    {i}. {rec}")
    
    return evaluation


async def test_evaluation_with_context():
    """Test evaluation with discovery and classification context."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Evaluation with Full Context")
    logger.info("="*80)
    
    # Create agent
    agent = BeeAIEvaluationAgent(llm_model="ollama:llama3.2")
    
    # Create test data with context
    validation_result = create_sample_validation_result(score=75, failed_checks=2, warning_checks=3)
    discovery_result = create_sample_discovery_result()
    classification = create_sample_classification()
    
    logger.info(f"Testing evaluation with context:")
    logger.info(f"  Validation Score: {validation_result.score}/100")
    logger.info(f"  Discovered Apps: {len(discovery_result.applications)}")
    logger.info(f"  Classification: {classification.category.value}")
    
    # Perform evaluation
    evaluation = await agent.evaluate(
        validation_result,
        discovery_result=discovery_result,
        classification=classification
    )
    
    # Verify results
    logger.info(f"\n✓ Context-aware evaluation completed")
    logger.info(f"  Overall Health: {evaluation.overall_health}")
    logger.info(f"  Confidence: {evaluation.confidence:.2f}")
    logger.info(f"  Critical Issues: {len(evaluation.critical_issues)}")
    
    if evaluation.critical_issues:
        logger.info(f"\n  Critical Issues:")
        for issue in evaluation.critical_issues[:3]:
            logger.info(f"    - {issue}")
    
    if evaluation.next_steps:
        logger.info(f"\n  Next Steps:")
        for step in evaluation.next_steps[:3]:
            logger.info(f"    - {step}")
    
    return evaluation


async def test_severity_assessment():
    """Test severity assessment for different scenarios."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Severity Assessment")
    logger.info("="*80)
    
    agent = BeeAIEvaluationAgent(llm_model="ollama:llama3.2")
    
    # Test different severity scenarios
    scenarios = [
        ("Excellent", 95, 0, 0),
        ("Good", 85, 1, 1),
        ("Fair", 70, 2, 2),
        ("Poor", 50, 3, 3),
        ("Critical", 30, 5, 2)
    ]
    
    for name, score, failed, warnings in scenarios:
        logger.info(f"\n  Testing {name} scenario (score: {score})...")
        
        validation_result = create_sample_validation_result(
            score=score,
            failed_checks=failed,
            warning_checks=warnings
        )
        
        evaluation = await agent.evaluate(validation_result)
        
        logger.info(f"    Health: {evaluation.overall_health}")
        logger.info(f"    Confidence: {evaluation.confidence:.2f}")
        logger.info(f"    Assessments: {len(evaluation.check_assessments)}")
        
        # Check critical assessments
        critical = evaluation.get_critical_assessments()
        if critical:
            logger.info(f"    Critical Assessments: {len(critical)}")


async def test_trend_analysis():
    """Test trend analysis across multiple validation runs."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Trend Analysis")
    logger.info("="*80)
    
    agent = BeeAIEvaluationAgent(llm_model="ollama:llama3.2")
    
    # Create historical results
    previous_results = [
        create_sample_validation_result(score=80, failed_checks=2, warning_checks=1),
        create_sample_validation_result(score=82, failed_checks=1, warning_checks=2),
        create_sample_validation_result(score=85, failed_checks=1, warning_checks=1),
    ]
    
    current_result = create_sample_validation_result(score=88, failed_checks=0, warning_checks=2)
    
    logger.info(f"Analyzing trend across {len(previous_results) + 1} validation runs")
    logger.info(f"  Previous scores: {[r.score for r in previous_results]}")
    logger.info(f"  Current score: {current_result.score}")
    
    # Perform trend analysis
    trend = await agent.evaluate_trend(current_result, previous_results)
    
    logger.info(f"\n✓ Trend analysis completed")
    logger.info(f"  Trend: {trend['trend']}")
    logger.info(f"  Score Change: {trend['score_change']:+.2f}")
    logger.info(f"  Average Previous: {trend['average_previous_score']:.2f}")
    logger.info(f"  Recurring Issues: {trend['recurring_issue_count']}")
    logger.info(f"  Message: {trend['message']}")
    logger.info(f"  Recommendation: {trend['recommendation']}")
    
    return trend


async def test_fallback_evaluation():
    """Test fallback evaluation mechanism."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Fallback Evaluation")
    logger.info("="*80)
    
    agent = BeeAIEvaluationAgent(llm_model="ollama:llama3.2")
    
    validation_result = create_sample_validation_result(score=65, failed_checks=3, warning_checks=2)
    
    logger.info("Testing fallback evaluation (simulating AI failure)...")
    
    # Use fallback directly
    evaluation = agent._create_fallback_evaluation(validation_result)
    
    logger.info(f"\n✓ Fallback evaluation created")
    logger.info(f"  Overall Health: {evaluation.overall_health}")
    logger.info(f"  Confidence: {evaluation.confidence:.2f}")
    logger.info(f"  Critical Issues: {len(evaluation.critical_issues)}")
    logger.info(f"  Recommendations: {len(evaluation.recommendations)}")
    
    # Verify fallback provides reasonable results
    assert evaluation.overall_health in ["excellent", "good", "fair", "poor", "critical"]
    assert 0 <= evaluation.confidence <= 1
    assert len(evaluation.check_assessments) > 0
    
    logger.info("  ✓ Fallback evaluation is functional")
    
    return evaluation


async def test_high_priority_recommendations():
    """Test high-priority recommendation extraction."""
    logger.info("\n" + "="*80)
    logger.info("TEST 6: High-Priority Recommendations")
    logger.info("="*80)
    
    agent = BeeAIEvaluationAgent(llm_model="ollama:llama3.2")
    
    validation_result = create_sample_validation_result(score=60, failed_checks=4, warning_checks=3)
    
    evaluation = await agent.evaluate(validation_result)
    
    high_priority = evaluation.get_high_priority_recommendations()
    
    logger.info(f"\n✓ High-priority recommendations extracted")
    logger.info(f"  Total Recommendations: {len(evaluation.recommendations)}")
    logger.info(f"  High-Priority: {len(high_priority)}")
    
    if high_priority:
        logger.info(f"\n  High-Priority Recommendations:")
        for i, rec in enumerate(high_priority, 1):
            logger.info(f"    {i}. {rec}")
    
    return high_priority


async def run_all_tests():
    """Run all evaluation agent tests."""
    logger.info("\n" + "="*80)
    logger.info("BeeAI EVALUATION AGENT TEST SUITE")
    logger.info("="*80)
    
    try:
        # Run tests
        await test_basic_evaluation()
        await test_evaluation_with_context()
        await test_severity_assessment()
        await test_trend_analysis()
        await test_fallback_evaluation()
        await test_high_priority_recommendations()
        
        logger.info("\n" + "="*80)
        logger.info("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"\n✗ Test suite failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())

# Made with Bob
