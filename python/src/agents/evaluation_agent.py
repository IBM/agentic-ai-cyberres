#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Evaluation agent for assessing validation results using Pydantic AI."""

import logging
from typing import Optional, List, Dict, Any
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from models import (
    ResourceValidationResult,
    CheckResult,
    ValidationStatus,
    WorkloadDiscoveryResult,
    ResourceClassification
)
from agents.base import AgentConfig

logger = logging.getLogger(__name__)


class ValidationAssessment(BaseModel):
    """Assessment of a validation check."""
    check_id: str = Field(..., description="Check identifier")
    severity: str = Field(..., description="Severity: critical, high, medium, low, info")
    impact_analysis: str = Field(..., description="Analysis of the impact")
    root_cause: Optional[str] = Field(None, description="Potential root cause")
    remediation_steps: List[str] = Field(default_factory=list, description="Steps to remediate")


class OverallEvaluation(BaseModel):
    """Overall evaluation of validation results."""
    overall_health: str = Field(..., description="Overall health: excellent, good, fair, poor, critical")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evaluation (0-1)")
    summary: str = Field(..., description="Executive summary of findings")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues found")
    warnings: List[str] = Field(default_factory=list, description="Warning-level issues")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    check_assessments: List[ValidationAssessment] = Field(default_factory=list, description="Individual check assessments")
    next_steps: List[str] = Field(default_factory=list, description="Recommended next steps")
    
    def get_critical_assessments(self) -> List[ValidationAssessment]:
        """Get critical severity assessments."""
        return [a for a in self.check_assessments if a.severity == "critical"]
    
    def get_high_priority_recommendations(self) -> List[str]:
        """Get high-priority recommendations."""
        recs = []
        if self.critical_issues:
            recs.extend([f"CRITICAL: {issue}" for issue in self.critical_issues[:3]])
        recs.extend(self.recommendations[:5])
        return recs


class EvaluationAgent:
    """Agent for intelligent evaluation of validation results."""
    
    SYSTEM_PROMPT = """You are an expert infrastructure validation analyst. Your role is to:
1. Analyze validation results in context of the discovered workload
2. Assess the severity and impact of any issues
3. Identify root causes and patterns
4. Provide actionable recommendations
5. Consider the resource type and applications when evaluating

You should:
- Be thorough but concise in your analysis
- Prioritize issues by severity and business impact
- Provide specific, actionable remediation steps
- Consider dependencies and cascading effects
- Use industry best practices for recommendations

Severity Levels:
- critical: System is down or data loss risk
- high: Major functionality impaired
- medium: Performance degraded or minor issues
- low: Minor issues with workarounds
- info: Informational findings

Overall Health Ratings:
- excellent: All checks passed, optimal configuration
- good: Minor issues only, system is healthy
- fair: Some issues present, needs attention
- poor: Multiple issues, immediate action needed
- critical: System failure or severe issues"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize evaluation agent.
        
        Args:
            config: Agent configuration (uses defaults if not provided)
        """
        self.config = config or AgentConfig()
        
        # Create evaluation agent with higher temperature for nuanced analysis
        eval_config = AgentConfig(
            model=self.config.model,
            api_key=self.config.api_key,
            temperature=0.3,  # Lower for more consistent analysis
            max_tokens=6000   # More tokens for detailed analysis
        )
        
        self.evaluation_agent = eval_config.create_agent(
            result_type=OverallEvaluation,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        logger.info("Evaluation agent initialized")
    
    async def evaluate(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult] = None,
        classification: Optional[ResourceClassification] = None
    ) -> OverallEvaluation:
        """Evaluate validation results with context.
        
        Args:
            validation_result: Validation results to evaluate
            discovery_result: Optional workload discovery context
            classification: Optional resource classification
        
        Returns:
            OverallEvaluation with assessment and recommendations
        """
        logger.info(
            f"Evaluating validation results for {validation_result.resource_host} "
            f"(score: {validation_result.score}/100)"
        )
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            validation_result,
            discovery_result,
            classification
        )
        
        try:
            result = await self.evaluation_agent.run(prompt)
            evaluation = result.data
            
            logger.info(
                f"Evaluation complete: {evaluation.overall_health} "
                f"({len(evaluation.critical_issues)} critical, "
                f"{len(evaluation.warnings)} warnings)"
            )
            
            return evaluation
            
        except Exception as e:
            logger.warning(f"Failed to create AI evaluation, using fallback: {e}")
            return self._create_fallback_evaluation(validation_result)
    
    def _build_evaluation_prompt(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification]
    ) -> str:
        """Build prompt for evaluation.
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery context
            classification: Classification context
        
        Returns:
            Prompt string
        """
        prompt_parts = [
            "Evaluate these validation results and provide a comprehensive assessment:",
            f"\n## Resource Information",
            f"Host: {validation_result.resource_host}",
            f"Type: {validation_result.resource_type.value}",
            f"Overall Score: {validation_result.score}/100",
            f"Execution Time: {validation_result.execution_time_seconds:.2f}s",
        ]
        
        # Add discovery context
        if discovery_result:
            prompt_parts.extend([
                f"\n## Discovered Workload",
                f"Open Ports: {len(discovery_result.ports)}",
                f"Running Processes: {len(discovery_result.processes)}",
                f"Detected Applications: {len(discovery_result.applications)}",
            ])
            
            if discovery_result.applications:
                apps = ", ".join(
                    f"{app.name} ({app.confidence:.0%})"
                    for app in discovery_result.applications[:5]
                )
                prompt_parts.append(f"Applications: {apps}")
        
        # Add classification context
        if classification:
            prompt_parts.extend([
                f"\n## Resource Classification",
                f"Category: {classification.category.value}",
                f"Confidence: {classification.confidence:.0%}",
            ])
            
            if classification.primary_application:
                prompt_parts.append(
                    f"Primary Application: {classification.primary_application.name}"
                )
        
        # Add validation results
        prompt_parts.extend([
            f"\n## Validation Results",
            f"Total Checks: {len(validation_result.checks)}",
            f"Passed: {validation_result.passed_checks}",
            f"Failed: {validation_result.failed_checks}",
            f"Warnings: {validation_result.warning_checks}",
        ])
        
        # Add failed checks details
        failed_checks = [c for c in validation_result.checks if c.status == ValidationStatus.FAIL]
        if failed_checks:
            prompt_parts.append("\n### Failed Checks:")
            for check in failed_checks:
                prompt_parts.append(f"\n**{check.check_name}** (ID: {check.check_id})")
                if check.expected:
                    prompt_parts.append(f"  Expected: {check.expected}")
                if check.actual:
                    prompt_parts.append(f"  Actual: {check.actual}")
                if check.message:
                    prompt_parts.append(f"  Message: {check.message}")
                if check.details:
                    prompt_parts.append(f"  Details: {check.details}")
        
        # Add warning checks
        warning_checks = [c for c in validation_result.checks if c.status == ValidationStatus.WARNING]
        if warning_checks:
            prompt_parts.append("\n### Warning Checks:")
            for check in warning_checks:
                prompt_parts.append(f"\n**{check.check_name}** (ID: {check.check_id})")
                if check.message:
                    prompt_parts.append(f"  Message: {check.message}")
        
        # Add passed checks summary
        passed_checks = [c for c in validation_result.checks if c.status == ValidationStatus.PASS]
        if passed_checks:
            prompt_parts.append(f"\n### Passed Checks: {len(passed_checks)}")
            prompt_parts.append("  " + ", ".join(c.check_name for c in passed_checks[:10]))
            if len(passed_checks) > 10:
                prompt_parts.append(f"  ... and {len(passed_checks) - 10} more")
        
        prompt_parts.extend([
            "\n## Your Task",
            "Provide a comprehensive evaluation including:",
            "1. Overall health assessment",
            "2. Severity analysis for each failed/warning check",
            "3. Root cause analysis where possible",
            "4. Specific remediation steps",
            "5. Prioritized recommendations",
            "6. Next steps for the operations team",
            "\nConsider the resource type, discovered applications, and business impact in your analysis."
        ])
        
        return "\n".join(prompt_parts)
    
    def _create_fallback_evaluation(
        self,
        validation_result: ResourceValidationResult
    ) -> OverallEvaluation:
        """Create fallback evaluation when AI fails.
        
        Args:
            validation_result: Validation results
        
        Returns:
            OverallEvaluation with basic assessment
        """
        logger.info("Creating fallback evaluation")
        
        # Determine overall health based on score
        if validation_result.score >= 90:
            health = "excellent"
        elif validation_result.score >= 75:
            health = "good"
        elif validation_result.score >= 60:
            health = "fair"
        elif validation_result.score >= 40:
            health = "poor"
        else:
            health = "critical"
        
        # Collect issues
        critical_issues = []
        warnings = []
        assessments = []
        
        for check in validation_result.checks:
            if check.status == ValidationStatus.FAIL:
                issue = f"{check.check_name}: {check.message or 'Check failed'}"
                critical_issues.append(issue)
                
                assessments.append(ValidationAssessment(
                    check_id=check.check_id,
                    severity="high" if validation_result.failed_checks <= 2 else "medium",
                    impact_analysis=f"Check '{check.check_name}' failed",
                    remediation_steps=[
                        f"Investigate {check.check_name}",
                        "Review system logs",
                        "Verify configuration"
                    ]
                ))
            
            elif check.status == ValidationStatus.WARNING:
                warning = f"{check.check_name}: {check.message or 'Warning condition'}"
                warnings.append(warning)
                
                assessments.append(ValidationAssessment(
                    check_id=check.check_id,
                    severity="low",
                    impact_analysis=f"Warning in {check.check_name}",
                    remediation_steps=["Monitor the situation", "Review if issue persists"]
                ))
        
        # Generate recommendations
        recommendations = []
        if validation_result.failed_checks > 0:
            recommendations.append(
                f"Address {validation_result.failed_checks} failed check(s) immediately"
            )
        if validation_result.warning_checks > 0:
            recommendations.append(
                f"Review {validation_result.warning_checks} warning(s) for potential issues"
            )
        if validation_result.score < 80:
            recommendations.append("Perform comprehensive system review")
        
        # Next steps
        next_steps = []
        if critical_issues:
            next_steps.append("Prioritize resolution of failed checks")
            next_steps.append("Engage appropriate technical teams")
        if validation_result.score >= 80:
            next_steps.append("Continue regular monitoring")
        else:
            next_steps.append("Schedule follow-up validation after remediation")
        
        summary = (
            f"Validation completed with {validation_result.passed_checks} passed, "
            f"{validation_result.failed_checks} failed, and {validation_result.warning_checks} warning checks. "
            f"Overall score: {validation_result.score}/100."
        )
        
        return OverallEvaluation(
            overall_health=health,
            confidence=0.7,  # Lower confidence for fallback
            summary=summary,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
            check_assessments=assessments,
            next_steps=next_steps
        )
    
    async def evaluate_trend(
        self,
        current_result: ResourceValidationResult,
        previous_results: List[ResourceValidationResult]
    ) -> Dict[str, Any]:
        """Evaluate trends across multiple validation runs.
        
        Args:
            current_result: Current validation result
            previous_results: Previous validation results
        
        Returns:
            Trend analysis dictionary
        """
        if not previous_results:
            return {
                "trend": "no_history",
                "message": "No previous results for comparison"
            }
        
        # Calculate score trend
        scores = [r.score for r in previous_results] + [current_result.score]
        avg_previous = sum(r.score for r in previous_results) / len(previous_results)
        
        trend = "stable"
        if current_result.score > avg_previous + 10:
            trend = "improving"
        elif current_result.score < avg_previous - 10:
            trend = "degrading"
        
        # Check for recurring issues
        current_failed = {c.check_id for c in current_result.checks if c.status == ValidationStatus.FAIL}
        recurring_issues = []
        
        for prev_result in previous_results[-3:]:  # Last 3 results
            prev_failed = {c.check_id for c in prev_result.checks if c.status == ValidationStatus.FAIL}
            recurring = current_failed & prev_failed
            if recurring:
                recurring_issues.extend(recurring)
        
        return {
            "trend": trend,
            "current_score": current_result.score,
            "average_previous_score": avg_previous,
            "score_change": current_result.score - avg_previous,
            "recurring_issues": list(set(recurring_issues)),
            "message": f"Validation trend is {trend}"
        }


# Made with Bob