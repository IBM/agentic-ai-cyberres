"""
BeeAI-based Evaluation Agent for Assessing Validation Results

This module provides a BeeAI RequirementAgent implementation for evaluating
validation results and providing comprehensive assessments. It replaces the
Pydantic AI implementation with BeeAI's declarative agent architecture.

Key Features:
- Intelligent evaluation using LLM reasoning
- Severity analysis and impact assessment
- Root cause identification
- Actionable remediation steps
- Trend analysis across multiple runs
- Comprehensive error handling
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

# BeeAI imports
from beeai_framework.agents.requirement.agent import RequirementAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import SlidingMemory, SlidingMemoryConfig

# Local imports
from models import (
    ResourceValidationResult,
    CheckResult,
    ValidationStatus,
    WorkloadDiscoveryResult,
    ResourceClassification
)

logger = logging.getLogger(__name__)


class ValidationAssessment(BaseModel):
    """Assessment of an individual validation check."""
    check_id: str = Field(..., description="Check identifier")
    severity: str = Field(..., description="Severity: critical, high, medium, low, info")
    impact_analysis: str = Field(..., description="Detailed analysis of the impact")
    root_cause: Optional[str] = Field(None, description="Potential root cause if identifiable")
    remediation_steps: List[str] = Field(default_factory=list, description="Specific steps to remediate")


class OverallEvaluation(BaseModel):
    """Overall evaluation of validation results with comprehensive analysis."""
    overall_health: str = Field(..., description="Overall health: excellent, good, fair, poor, critical")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evaluation (0-1)")
    summary: str = Field(..., description="Executive summary of findings")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues requiring immediate attention")
    warnings: List[str] = Field(default_factory=list, description="Warning-level issues to monitor")
    recommendations: List[str] = Field(default_factory=list, description="Prioritized actionable recommendations")
    check_assessments: List[ValidationAssessment] = Field(default_factory=list, description="Individual check assessments")
    next_steps: List[str] = Field(default_factory=list, description="Recommended next steps for operations team")
    
    def get_critical_assessments(self) -> List[ValidationAssessment]:
        """Get assessments with critical severity.
        
        Returns:
            List of critical severity assessments
        """
        return [a for a in self.check_assessments if a.severity == "critical"]
    
    def get_high_priority_recommendations(self) -> List[str]:
        """Get high-priority recommendations.
        
        Returns:
            List of top priority recommendations
        """
        recs = []
        if self.critical_issues:
            recs.extend([f"CRITICAL: {issue}" for issue in self.critical_issues[:3]])
        recs.extend(self.recommendations[:5])
        return recs


class BeeAIEvaluationAgent:
    """BeeAI-based agent for intelligent evaluation of validation results.
    
    This agent uses BeeAI's RequirementAgent to provide comprehensive evaluation
    of validation results, including severity analysis, root cause identification,
    and actionable recommendations.
    
    Architecture:
    - Evaluation Agent: Analyzes validation results using LLM reasoning
    - Context-Aware: Considers discovery and classification context
    - Trend Analysis: Tracks changes across multiple validation runs
    
    Example:
        >>> agent = BeeAIEvaluationAgent(llm_model="ollama:llama3.2")
        >>> evaluation = await agent.evaluate(
        ...     validation_result,
        ...     discovery_result=discovery,
        ...     classification=classification
        ... )
        >>> critical = evaluation.get_critical_assessments()
    """
    
    SYSTEM_PROMPT = """You are an expert infrastructure validation analyst with deep knowledge of system operations.

Your role is to:
1. Analyze validation results in the context of discovered workloads
2. Assess severity and business impact of issues
3. Identify root causes and patterns
4. Provide specific, actionable recommendations
5. Consider resource type, applications, and dependencies

Analysis Guidelines:
- **Thorough but Concise**: Provide detailed analysis without unnecessary verbosity
- **Prioritize by Impact**: Focus on business-critical issues first
- **Actionable Recommendations**: Provide specific steps, not generic advice
- **Consider Dependencies**: Identify cascading effects and related issues
- **Industry Best Practices**: Base recommendations on proven practices

Severity Levels:
- **critical**: System is down, data loss risk, or security breach
- **high**: Major functionality impaired, significant performance degradation
- **medium**: Performance degraded, minor functionality issues
- **low**: Minor issues with workarounds available
- **info**: Informational findings, no immediate action needed

Overall Health Ratings:
- **excellent**: All checks passed, optimal configuration, no issues
- **good**: Minor issues only, system is healthy and stable
- **fair**: Some issues present, needs attention but not urgent
- **poor**: Multiple issues, immediate action recommended
- **critical**: System failure, severe issues, emergency response needed

Evaluation Process:
1. Review all validation check results
2. Analyze failed and warning checks in detail
3. Consider resource type and discovered applications
4. Identify patterns and root causes
5. Assess business impact and urgency
6. Provide prioritized, actionable recommendations
7. Suggest next steps for operations team
"""
    
    EVALUATION_INSTRUCTIONS = [
        "Analyze validation results thoroughly and systematically",
        "Consider the resource type and discovered applications",
        "Assess severity based on business impact, not just technical failure",
        "Identify root causes where possible from available information",
        "Provide specific, actionable remediation steps",
        "Prioritize recommendations by urgency and impact",
        "Consider dependencies and cascading effects",
        "Suggest realistic next steps for the operations team"
    ]
    
    def __init__(
        self,
        llm_model: str = "ollama:llama3.2",
        memory_size: int = 100,  # Larger memory for evaluation context
        temperature: float = 0.3  # Higher for nuanced analysis
    ):
        """Initialize BeeAI Evaluation Agent.
        
        Args:
            llm_model: LLM model identifier (e.g., "ollama:llama3.2", "openai:gpt-4")
            memory_size: Size of sliding memory window
            temperature: LLM temperature for evaluation (0.0-1.0)
        """
        self.llm_model = llm_model
        self.memory_size = memory_size
        self.temperature = temperature
        
        # Evaluation agent will be created on first use
        self._evaluation_agent = None
        
        logger.info(
            f"BeeAI Evaluation Agent initialized with model: {llm_model}"
        )
    
    def _create_evaluation_agent(self) -> RequirementAgent:
        """Create evaluation agent for result analysis.
        
        Returns:
            Configured RequirementAgent for evaluation
        """
        if self._evaluation_agent is not None:
            return self._evaluation_agent
        
        logger.info("Creating evaluation agent...")
        
        # Create LLM
        llm = ChatModel.from_name(self.llm_model)
        
        # Create memory (larger for evaluation context)
        memory = SlidingMemory(SlidingMemoryConfig(size=self.memory_size))
        
        # Create evaluation agent
        self._evaluation_agent = RequirementAgent(
            llm=llm,
            memory=memory,
            tools=[],  # Evaluation doesn't need tools
            name="Validation Evaluation Agent",
            description="Provides comprehensive evaluation of validation results with actionable insights",
            role="Infrastructure Validation Analyst",
            instructions=self.EVALUATION_INSTRUCTIONS,
            notes=[
                "Always provide detailed reasoning for severity assessments",
                "Consider business impact, not just technical failures",
                "Provide specific remediation steps, not generic advice",
                "Prioritize recommendations by urgency and impact"
            ],
        )
        
        logger.info("Evaluation agent created")
        return self._evaluation_agent
    
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
            OverallEvaluation with comprehensive assessment
        
        Raises:
            Exception: If evaluation fails
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
            # Use BeeAI agent for evaluation
            evaluation_agent = self._create_evaluation_agent()
            
            result = await evaluation_agent.run(
                prompt,
                expected_output=OverallEvaluation
            )
            
            if result.output_structured:
                evaluation = result.output_structured
                logger.info(
                    f"Evaluation complete: {evaluation.overall_health} "
                    f"({len(evaluation.critical_issues)} critical, "
                    f"{len(evaluation.warnings)} warnings)"
                )
                return evaluation
            else:
                logger.warning("No structured output, using fallback evaluation")
                return self._create_fallback_evaluation(validation_result)
        
        except Exception as e:
            logger.warning(f"Failed to create AI evaluation: {e}, using fallback")
            return self._create_fallback_evaluation(validation_result)
    
    def _build_evaluation_prompt(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification]
    ) -> str:
        """Build comprehensive evaluation prompt.
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery context
            classification: Classification context
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "# Validation Results Evaluation Task",
            "",
            "## Resource Information",
            f"- **Host**: {validation_result.resource_host}",
            f"- **Type**: {validation_result.resource_type.value}",
            f"- **Overall Score**: {validation_result.score}/100",
            f"- **Execution Time**: {validation_result.execution_time_seconds:.2f}s",
        ]
        
        # Add discovery context
        if discovery_result:
            prompt_parts.extend([
                "",
                "## Discovered Workload Context",
                f"- **Open Ports**: {len(discovery_result.ports)}",
                f"- **Running Processes**: {len(discovery_result.processes)}",
                f"- **Detected Applications**: {len(discovery_result.applications)}",
            ])
            
            if discovery_result.applications:
                apps = ", ".join(
                    f"{app.name} ({app.confidence:.0%})"
                    for app in discovery_result.applications[:5]
                )
                prompt_parts.append(f"- **Applications**: {apps}")
        
        # Add classification context
        if classification:
            prompt_parts.extend([
                "",
                "## Resource Classification",
                f"- **Category**: {classification.category.value}",
                f"- **Confidence**: {classification.confidence:.0%}",
            ])
            
            if classification.primary_application:
                prompt_parts.append(
                    f"- **Primary Application**: {classification.primary_application.name}"
                )
        
        # Add validation summary
        prompt_parts.extend([
            "",
            "## Validation Results Summary",
            f"- **Total Checks**: {len(validation_result.checks)}",
            f"- **Passed**: {validation_result.passed_checks}",
            f"- **Failed**: {validation_result.failed_checks}",
            f"- **Warnings**: {validation_result.warning_checks}",
        ])
        
        # Add failed checks details
        failed_checks = [c for c in validation_result.checks if c.status == ValidationStatus.FAIL]
        if failed_checks:
            prompt_parts.extend([
                "",
                "## Failed Checks (Detailed Analysis Required)",
            ])
            for check in failed_checks:
                prompt_parts.append(f"\n### {check.check_name} (ID: {check.check_id})")
                if check.expected:
                    prompt_parts.append(f"- **Expected**: {check.expected}")
                if check.actual:
                    prompt_parts.append(f"- **Actual**: {check.actual}")
                if check.message:
                    prompt_parts.append(f"- **Message**: {check.message}")
                if check.details:
                    prompt_parts.append(f"- **Details**: {check.details}")
        
        # Add warning checks
        warning_checks = [c for c in validation_result.checks if c.status == ValidationStatus.WARNING]
        if warning_checks:
            prompt_parts.extend([
                "",
                "## Warning Checks (Review Recommended)",
            ])
            for check in warning_checks:
                prompt_parts.append(f"\n### {check.check_name} (ID: {check.check_id})")
                if check.message:
                    prompt_parts.append(f"- **Message**: {check.message}")
                if check.details:
                    prompt_parts.append(f"- **Details**: {check.details}")
        
        # Add passed checks summary
        passed_checks = [c for c in validation_result.checks if c.status == ValidationStatus.PASS]
        if passed_checks:
            prompt_parts.extend([
                "",
                f"## Passed Checks ({len(passed_checks)} total)",
                "- " + ", ".join(c.check_name for c in passed_checks[:10])
            ])
            if len(passed_checks) > 10:
                prompt_parts.append(f"- ... and {len(passed_checks) - 10} more")
        
        # Add evaluation requirements
        prompt_parts.extend([
            "",
            "## Your Evaluation Task",
            "Provide a comprehensive evaluation including:",
            "",
            "1. **Overall Health Assessment**: Rate the system health (excellent/good/fair/poor/critical)",
            "2. **Severity Analysis**: For each failed/warning check, assess severity and impact",
            "3. **Root Cause Analysis**: Identify potential root causes where possible",
            "4. **Remediation Steps**: Provide specific, actionable steps to resolve issues",
            "5. **Prioritized Recommendations**: Order recommendations by urgency and impact",
            "6. **Next Steps**: Suggest concrete next steps for the operations team",
            "",
            "Consider:",
            "- Resource type and discovered applications",
            "- Business impact of failures",
            "- Dependencies and cascading effects",
            "- Industry best practices",
            "",
            "Respond with a complete OverallEvaluation including all required fields."
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
            OverallEvaluation with rule-based assessment
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
        
        # Collect issues and create assessments
        critical_issues = []
        warnings = []
        assessments = []
        
        for check in validation_result.checks:
            if check.status == ValidationStatus.FAIL:
                issue = f"{check.check_name}: {check.message or 'Check failed'}"
                critical_issues.append(issue)
                
                # Determine severity based on number of failures
                severity = "critical" if validation_result.failed_checks == 1 else "high"
                if validation_result.failed_checks > 3:
                    severity = "medium"
                
                assessments.append(ValidationAssessment(
                    check_id=check.check_id,
                    severity=severity,
                    impact_analysis=f"Check '{check.check_name}' failed. {check.message or ''}",
                    root_cause=None,
                    remediation_steps=[
                        f"Investigate {check.check_name} failure",
                        "Review system logs for errors",
                        "Verify configuration and connectivity",
                        "Consult documentation for this check type"
                    ]
                ))
            
            elif check.status == ValidationStatus.WARNING:
                warning = f"{check.check_name}: {check.message or 'Warning condition detected'}"
                warnings.append(warning)
                
                assessments.append(ValidationAssessment(
                    check_id=check.check_id,
                    severity="low",
                    impact_analysis=f"Warning condition in {check.check_name}. {check.message or ''}",
                    root_cause=None,
                    remediation_steps=[
                        "Monitor the situation",
                        "Review if issue persists or worsens",
                        "Consider preventive action if pattern emerges"
                    ]
                ))
        
        # Generate recommendations
        recommendations = []
        if validation_result.failed_checks > 0:
            recommendations.append(
                f"Address {validation_result.failed_checks} failed check(s) immediately"
            )
            recommendations.append("Prioritize checks by business impact")
        if validation_result.warning_checks > 0:
            recommendations.append(
                f"Review {validation_result.warning_checks} warning(s) for potential issues"
            )
        if validation_result.score < 80:
            recommendations.append("Perform comprehensive system review")
            recommendations.append("Consider engaging technical support if issues persist")
        
        # Next steps
        next_steps = []
        if critical_issues:
            next_steps.append("Prioritize resolution of failed checks")
            next_steps.append("Engage appropriate technical teams")
            next_steps.append("Document findings and remediation actions")
        if validation_result.score >= 80:
            next_steps.append("Continue regular monitoring")
            next_steps.append("Schedule next validation cycle")
        else:
            next_steps.append("Schedule follow-up validation after remediation")
            next_steps.append("Track resolution progress")
        
        # Create summary
        summary = (
            f"Validation completed with {validation_result.passed_checks} passed, "
            f"{validation_result.failed_checks} failed, and {validation_result.warning_checks} warning checks. "
            f"Overall score: {validation_result.score}/100. "
            f"System health assessed as {health}."
        )
        
        return OverallEvaluation(
            overall_health=health,
            confidence=0.7,  # Lower confidence for rule-based fallback
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
            previous_results: Previous validation results (chronological order)
        
        Returns:
            Trend analysis dictionary with insights
        """
        if not previous_results:
            return {
                "trend": "no_history",
                "message": "No previous results available for trend analysis",
                "current_score": current_result.score
            }
        
        logger.info(f"Analyzing trend across {len(previous_results) + 1} validation runs")
        
        # Calculate score trend
        scores = [r.score for r in previous_results] + [current_result.score]
        avg_previous = sum(r.score for r in previous_results) / len(previous_results)
        
        # Determine trend
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
        
        # Calculate score volatility
        if len(scores) > 1:
            score_changes = [abs(scores[i] - scores[i-1]) for i in range(1, len(scores))]
            avg_volatility = sum(score_changes) / len(score_changes)
        else:
            avg_volatility = 0
        
        return {
            "trend": trend,
            "current_score": current_result.score,
            "average_previous_score": round(avg_previous, 2),
            "score_change": round(current_result.score - avg_previous, 2),
            "score_volatility": round(avg_volatility, 2),
            "recurring_issues": list(set(recurring_issues)),
            "recurring_issue_count": len(set(recurring_issues)),
            "message": f"Validation trend is {trend} (score change: {current_result.score - avg_previous:+.1f})",
            "recommendation": self._get_trend_recommendation(trend, recurring_issues)
        }
    
    def _get_trend_recommendation(self, trend: str, recurring_issues: List[str]) -> str:
        """Get recommendation based on trend analysis.
        
        Args:
            trend: Trend direction
            recurring_issues: List of recurring issue IDs
        
        Returns:
            Recommendation string
        """
        if trend == "degrading":
            return "System health is declining. Investigate root causes and take corrective action."
        elif trend == "improving":
            return "System health is improving. Continue current practices and monitor progress."
        elif recurring_issues:
            return f"System is stable but has {len(recurring_issues)} recurring issue(s). Address persistent problems."
        else:
            return "System is stable. Continue regular monitoring and maintenance."


# Backward compatibility alias
EvaluationAgent = BeeAIEvaluationAgent

# Made with Bob
