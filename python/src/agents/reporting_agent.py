#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Reporting agent for AI-powered report generation."""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic_ai import Agent
from pydantic import BaseModel, Field, field_validator

from models import (
    ResourceValidationResult,
    WorkloadDiscoveryResult,
    ResourceClassification,
    ValidationStatus,
    Finding,
    MetricValue,
    Action
)
from agents.base import AgentConfig, EnhancedAgent
from agents.evaluation_agent import OverallEvaluation
from tool_coordinator import ToolCoordinator
from state_manager import StateManager
from feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class ReportSection(BaseModel):
    """Individual report section."""
    
    model_config = {"strict": False, "validate_assignment": True}
    
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content in markdown")
    # CRITICAL FIX: Accept Union[int, str] to allow LLM to return either type
    # The validator will convert strings to integers
    priority: Union[int, str] = Field(
        default=3,
        description="Numeric priority from 1 (highest/most critical) to 5 (lowest/least critical). Use 1 for critical sections, 2 for high priority, 3 for medium, 4 for low, 5 for optional."
    )
    
    @field_validator('priority', mode='before')
    @classmethod
    def convert_priority(cls, v) -> int:
        """Convert any priority value to valid integer 1-5.
        
        This validator handles cases where the LLM returns string values
        like "critical", "high", "medium", "low", or "info" instead of
        numeric values. It gracefully converts them to the appropriate
        numeric priority (1-5).
        
        CRITICAL: The field type is Union[int, str] to allow Pydantic to accept
        string values from the LLM without throwing a validation error during
        JSON parsing. This validator then converts the string to an int.
        
        Args:
            v: The priority value (can be string, numeric, or None)
        
        Returns:
            int: Numeric priority value (1-5)
        """
        # Handle None or missing
        if v is None:
            return 3
        
        # If already int, validate range
        if isinstance(v, int):
            return max(1, min(5, v))
        
        # If float, convert to int
        if isinstance(v, float):
            return max(1, min(5, int(v)))
        
        # If string, try mapping first
        if isinstance(v, str):
            # Map common string values to numeric priorities
            priority_map = {
                'critical': 1, 'highest': 1, '1': 1,
                'high': 2, '2': 2,
                'medium': 3, 'normal': 3, '3': 3,
                'low': 4, '4': 4,
                'lowest': 5, 'info': 5, 'optional': 5, '5': 5
            }
            
            # Try to get mapped value (case-insensitive)
            mapped_value = priority_map.get(v.lower().strip())
            if mapped_value is not None:
                return mapped_value
            
            # Try parsing as number
            try:
                num = int(float(v))
                return max(1, min(5, num))
            except (ValueError, TypeError):
                pass
        
        # Default fallback to medium priority
        return 3


class ValidationReport(BaseModel):
    """Complete validation report."""
    executive_summary: str = Field(..., description="Executive summary")
    key_findings: List[str] = Field(..., description="Key findings")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues")
    recommendations: List[str] = Field(..., description="Recommendations")
    sections: List[ReportSection] = Field(..., description="Report sections")
    conclusion: str = Field(..., description="Conclusion")
    next_steps: List[str] = Field(..., description="Next steps")


class ReportingAgent(EnhancedAgent):
    """AI-powered reporting agent for generating comprehensive validation reports.
    
    This agent creates detailed, actionable reports from validation results,
    discovery data, and evaluation analysis.
    """
    
    SYSTEM_PROMPT = """You are a technical report writer specializing in infrastructure validation reports.

Your role is to create comprehensive, actionable reports that are:
- Clear and concise
- Technically accurate
- Prioritized by severity and business impact
- Suitable for both technical and management audiences
- Formatted in markdown for readability

Report Structure:
1. Executive Summary: High-level overview for management
2. Key Findings: Most important discoveries
3. Critical Issues: Issues requiring immediate attention
4. Detailed Sections: Technical details organized by category
5. Recommendations: Prioritized action items
6. Conclusion: Overall assessment
7. Next Steps: Clear path forward

Writing Guidelines:
- Use clear, professional language
- Avoid jargon when possible, explain when necessary
- Use bullet points and tables for clarity
- Highlight critical information
- Provide specific, actionable recommendations
- Include severity levels (Critical, High, Medium, Low)
- Add context and business impact
- Use markdown formatting (headers, lists, code blocks, tables)

IMPORTANT - Section Priority Field:
- The "priority" field in sections MUST be a NUMBER from 1 to 5
- 1 = Highest priority (critical issues, executive summary)
- 2 = High priority (key findings, major issues)
- 3 = Medium priority (detailed analysis)
- 4 = Low priority (supporting information)
- 5 = Lowest priority (optional details)
- DO NOT use text like "high", "medium", "low" - use numbers only!

EXAMPLE RESPONSE FORMAT (COPY THIS STRUCTURE):
{
  "executive_summary": "...",
  "key_findings": ["...", "..."],
  "critical_issues": ["..."],
  "recommendations": ["...", "..."],
  "sections": [
    {
      "title": "Executive Summary",
      "content": "...",
      "priority": 1
    },
    {
      "title": "Critical Findings",
      "content": "...",
      "priority": 2
    },
    {
      "title": "Detailed Analysis",
      "content": "...",
      "priority": 3
    }
  ],
  "conclusion": "...",
  "next_steps": ["...", "..."]
}

CRITICAL: The "priority" field MUST be an integer (1, 2, 3, 4, or 5), NOT a string!

Tone:
- Professional but accessible
- Objective and fact-based
- Constructive (focus on solutions)
- Urgent for critical issues, measured for others"""
    
    def __init__(
        self,
        mcp_client: Optional[Any] = None,
        config: Optional[AgentConfig] = None,
        tool_coordinator: Optional[ToolCoordinator] = None,
        state_manager: Optional[StateManager] = None,
        feature_flags: Optional[FeatureFlags] = None
    ):
        """Initialize reporting agent.
        
        Args:
            mcp_client: Optional MCP client (not used for reporting)
            config: Agent configuration for Pydantic AI
            tool_coordinator: Optional tool coordinator
            state_manager: Optional state manager
            feature_flags: Optional feature flags
        """
        super().__init__(
            mcp_client=mcp_client or object(),  # Dummy client
            name="reporting",
            tool_coordinator=tool_coordinator,
            state_manager=state_manager,
            feature_flags=feature_flags
        )
        
        self.config = config or AgentConfig(
            temperature=0.3,  # Slightly higher for more natural writing
            max_tokens=8000   # More tokens for detailed reports
        )
        
        # Create AI reporting agent
        self.ai_agent = self.config.create_agent(
            result_type=ValidationReport,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        self.log_step("Reporting agent initialized")
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Execute report generation.
        
        This method implements the abstract execute() method from BaseAgent.
        It generates a validation report based on the provided context.
        
        Args:
            context: Execution context containing:
                - validation_result: ResourceValidationResult (required)
                - discovery_result: WorkloadDiscoveryResult (optional)
                - classification: ResourceClassification (optional)
                - evaluation: OverallEvaluation (optional)
                - format: Output format (optional, default: "markdown")
        
        Returns:
            Formatted report string
        
        Raises:
            ValueError: If required context data is missing
        """
        # Extract required data from context
        validation_result = context.get("validation_result")
        if not validation_result:
            raise ValueError("validation_result is required in context")
        
        # Extract optional data
        discovery_result = context.get("discovery_result")
        classification = context.get("classification")
        evaluation = context.get("evaluation")
        format = context.get("format", "markdown")
        
        # Delegate to generate_report method
        return await self.generate_report(
            validation_result=validation_result,
            discovery_result=discovery_result,
            classification=classification,
            evaluation=evaluation,
            format=format
        )
    
    async def generate_report(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult] = None,
        classification: Optional[ResourceClassification] = None,
        evaluation: Optional[OverallEvaluation] = None,
        format: str = "markdown"
    ) -> str:
        """Generate comprehensive validation report.
        
        Args:
            validation_result: Validation results
            discovery_result: Optional discovery results
            classification: Optional classification
            evaluation: Optional evaluation
            format: Output format (markdown, html, json)
        
        Returns:
            Formatted report string
        """
        self.log_step(f"Generating report for {validation_result.resource_host}")
        
        # Check if AI reporting is enabled
        use_ai = (
            self.feature_flags and
            self.feature_flags.is_enabled("ai_reporting")
        )
        
        # Day 3 Optimization: Smart LLM usage
        # DISABLED: Always use AI when ai_reporting is enabled for comprehensive reports
        # if use_ai and self.feature_flags.is_enabled("smart_llm_usage"):
        #     if self._is_simple_report(validation_result, evaluation):
        #         self.log_step("Simple report detected - using template (no LLM needed)")
        #         use_ai = False
        
        if use_ai:
            try:
                self.log_step("Using AI-powered report generation")
                report = await self._generate_with_ai(
                    validation_result,
                    discovery_result,
                    classification,
                    evaluation
                )
                
                formatted_report = self._format_report(report, format)
                
                self.record_execution(
                    action="report_generated",
                    result={
                        "host": validation_result.resource_host,
                        "format": format,
                        "method": "ai",
                        "length": len(formatted_report)
                    }
                )
                
                return formatted_report
                
            except Exception as e:
                self.log_step(f"AI report generation failed: {e}", level="warning")
                self.log_step("Falling back to template-based report")
        else:
            self.log_step("Using template-based report generation (AI disabled or simple case)")
        
        # Fallback to template-based report
        report = self._generate_with_template(
            validation_result,
            discovery_result,
            classification,
            evaluation
        )
        
        self.record_execution(
            action="report_generated",
            result={
                "host": validation_result.resource_host,
                "format": format,
                "method": "template",
                "length": len(report)
            }
        )
        
        return report
    
    def _is_simple_report(
        self,
        validation_result: ResourceValidationResult,
        evaluation: Optional[OverallEvaluation]
    ) -> bool:
        """Check if this is a simple report that doesn't need AI.
        
        Simple reports are:
        - Single resource validation
        - All validations passed
        - No critical issues
        - Low complexity
        
        Args:
            validation_result: Validation results
            evaluation: Optional evaluation
        
        Returns:
            True if simple report, False if complex
        """
        # Check validation status
        if validation_result.overall_status != ValidationStatus.PASS:
            return False  # Failed validations need AI analysis
        
        # Check for failed or warning checks
        if validation_result.failed_checks > 0:
            return False  # Failed checks need AI analysis
        
        if validation_result.warning_checks > 3:
            return False  # Many warnings need AI analysis
        
        # Check evaluation if available
        if evaluation:
            if not evaluation.is_acceptable:
                return False  # Unacceptable results need AI analysis
            
            if evaluation.critical_issues:
                return False  # Critical issues need AI analysis
        
        # Check number of checks
        if len(validation_result.checks) > 5:
            return False  # Many checks need AI synthesis
        
        # This is a simple case - all passed, few checks, no issues
        return True
    
    async def _generate_with_ai(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification],
        evaluation: Optional[OverallEvaluation]
    ) -> ValidationReport:
        """Generate report using AI.
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery results
            classification: Classification
            evaluation: Evaluation
        
        Returns:
            ValidationReport
        """
        from pydantic import ValidationError
        import json
        import re
        
        # Build prompt with all available data
        prompt = self._build_report_prompt(
            validation_result,
            discovery_result,
            classification,
            evaluation
        )
        
        try:
            # Get AI-generated report
            result = await self.ai_agent.run(prompt)
            
            # INTERCEPT: Fix priority values before Pydantic validation
            try:
                if hasattr(result, 'data'):
                    data = result.data
                    if hasattr(data, 'sections') and data.sections:
                        priority_map = {
                            'critical': 1, 'highest': 1,
                            'high': 2,
                            'medium': 3, 'normal': 3,
                            'low': 4,
                            'lowest': 5, 'info': 5, 'optional': 5
                        }
                        
                        for section in data.sections:
                            if hasattr(section, 'priority'):
                                if isinstance(section.priority, str):
                                    # Convert string priority to int
                                    fixed_priority = priority_map.get(section.priority.lower().strip(), 3)
                                    section.priority = fixed_priority
                                    self.log_step(f"Fixed priority: '{section.priority}' -> {fixed_priority}")
                                elif not isinstance(section.priority, int):
                                    # Convert any other type to int
                                    try:
                                        section.priority = int(section.priority)
                                    except (ValueError, TypeError):
                                        section.priority = 3
            except Exception as fix_error:
                self.log_step(f"Error fixing priorities: {fix_error}", level="warning")
                # Continue anyway - let Pydantic handle it
            
            report = result.data
            
            self.log_step(
                f"AI report generated: {len(report.sections)} sections, "
                f"{len(report.recommendations)} recommendations"
            )
            
            return report
            
        except ValidationError as e:
            # Check if it's a priority field error
            error_str = str(e)
            if 'priority' in error_str and 'could not convert string to float' in error_str:
                self.log_step("Priority validation error detected - attempting to fix response", level="warning")
                
                # Try to get the raw response and fix it
                try:
                    # Re-run with explicit instruction to use numeric priorities
                    retry_prompt = prompt + "\n\nIMPORTANT: The 'priority' field MUST be a NUMBER (1, 2, 3, 4, or 5), NOT a string like 'high' or 'medium'. Use only integers!"
                    
                    result = await self.ai_agent.run(retry_prompt)
                    report = result.data
                    
                    self.log_step("Successfully generated report after retry", level="info")
                    return report
                    
                except Exception as retry_error:
                    self.log_step(f"Retry failed: {retry_error}", level="error")
                    raise e
            else:
                # Different validation error, re-raise
                raise
    
    def _generate_with_template(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification],
        evaluation: Optional[OverallEvaluation]
    ) -> str:
        """Generate enhanced detailed report using template.
        
        This method creates a comprehensive report with:
        - Detailed check-by-check results in tables
        - Critical issues highlighted with icons
        - Specific actionable recommendations
        - Structured sections (VM Health, Filesystem, Applications, etc.)
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery results
            classification: Classification
            evaluation: Evaluation
        
        Returns:
            Markdown report string with detailed formatting
        """
        self.log_step("Using enhanced template-based report generation")
        
        sections = []
        
        # Header with status icon
        status_icon = self._get_status_icon(validation_result.overall_status)
        sections.append(f"# {status_icon} Validation Report: {validation_result.resource_host}")
        sections.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append(f"**Resource Type**: {validation_result.resource_type.value.upper()}")
        sections.append(f"**Overall Score**: {validation_result.score}/100")
        sections.append(f"**Status**: {validation_result.overall_status.value}")
        
        # Parse and categorize checks
        categorized_checks = self._categorize_checks(validation_result.checks)
        critical_issues = self._identify_critical_issues(validation_result, categorized_checks)
        
        # Executive Summary
        sections.append("\n## 📊 Executive Summary")
        if evaluation:
            sections.append(f"\n{evaluation.summary}")
            sections.append(f"\n**Overall Health**: {evaluation.overall_health}")
        else:
            sections.append(f"\nValidation completed with **{validation_result.passed_checks} passed**, "
                          f"**{validation_result.failed_checks} failed**, and "
                          f"**{validation_result.warning_checks} warning** checks.")
        
        # Critical Issues Section (if any)
        if critical_issues:
            sections.append("\n## 🚨 Critical Issues")
            sections.append("\nThe following issues require immediate attention:\n")
            for issue in critical_issues:
                sections.append(f"- 🔴 **{issue['title']}**: {issue['description']}")
        
        # VM / OS Health Section
        if 'vm_health' in categorized_checks or 'os_info' in categorized_checks:
            sections.append("\n## 🖥️ VM / OS Health")
            vm_table = self._create_check_table(
                categorized_checks.get('vm_health', []) + categorized_checks.get('os_info', []),
                ["Check", "Result", "Status"]
            )
            sections.append(vm_table)
        
        # Filesystem Usage Section
        if 'filesystem' in categorized_checks:
            sections.append("\n## 💾 Filesystem Usage")
            fs_table = self._create_filesystem_table(categorized_checks['filesystem'])
            sections.append(fs_table)
            
            # Add critical filesystem warnings
            fs_critical = [c for c in categorized_checks['filesystem']
                          if c.status == ValidationStatus.FAIL or
                          (c.details and self._is_disk_critical(c.details))]
            if fs_critical:
                sections.append("\n> 🚨 **Critical filesystem issues detected.** "
                              "Filesystems above 85% capacity require immediate attention.")
        
        # Network Section
        if 'network' in categorized_checks:
            sections.append("\n## 🌐 Network Configuration")
            net_table = self._create_check_table(
                categorized_checks['network'],
                ["Check", "Result", "Status"]
            )
            sections.append(net_table)
        
        # Application Discovery Section
        if discovery_result and discovery_result.applications:
            sections.append("\n## 🗄️ Application Discovery")
            for app in discovery_result.applications:
                sections.append(f"\n### {app.name}")
                app_table = self._create_application_table(app, categorized_checks)
                sections.append(app_table)
        
        # Services Section
        if 'services' in categorized_checks:
            sections.append("\n## ⚙️ System Services")
            svc_table = self._create_check_table(
                categorized_checks['services'],
                ["Service", "Status", "Result"]
            )
            sections.append(svc_table)
        
        # Detailed Validation Results
        sections.append("\n## 📋 Detailed Validation Results")
        sections.append(f"\n- **Total Checks**: {len(validation_result.checks)}")
        sections.append(f"- **Passed**: ✅ {validation_result.passed_checks}")
        sections.append(f"- **Failed**: 🔴 {validation_result.failed_checks}")
        sections.append(f"- **Warnings**: ⚠️ {validation_result.warning_checks}")
        sections.append(f"- **Execution Time**: {validation_result.execution_time_seconds:.2f}s")
        
        # All Checks Table
        all_checks_table = self._create_all_checks_table(validation_result.checks)
        sections.append(all_checks_table)
        
        # Recommendations Section
        sections.append("\n## 💡 Recommendations")
        recommendations = self._generate_specific_recommendations(
            validation_result, categorized_checks, critical_issues, evaluation
        )
        if recommendations:
            sections.append("\n| Priority | Issue | Recommendation |")
            sections.append("|---|---|---|")
            for rec in recommendations:
                sections.append(f"| {rec['priority']} | {rec['issue']} | {rec['recommendation']} |")
        
        # Next Steps
        sections.append("\n## 🎯 Next Steps")
        next_steps = self._generate_next_steps(validation_result, critical_issues, evaluation)
        for i, step in enumerate(next_steps, 1):
            sections.append(f"{i}. {step}")
        
        return "\n".join(sections)
    
    def _calculate_key_metrics(
        self,
        validation_result: ResourceValidationResult,
        historical_results: Optional[List[ResourceValidationResult]] = None
    ) -> List[MetricValue]:
        """Calculate key metrics with trends."""
        metrics = []
        
        # Health Score Metric
        current_score = validation_result.score
        previous_score = historical_results[-1].score if historical_results else None
        
        trend = "unknown"
        change_pct = None
        if previous_score is not None:
            change_pct = ((current_score - previous_score) / previous_score) * 100 if previous_score > 0 else 0
            if change_pct > 5:
                trend = "improving"
            elif change_pct < -5:
                trend = "degrading"
            else:
                trend = "stable"
        
        status = "good" if current_score >= 80 else "warning" if current_score >= 60 else "critical"
        
        metrics.append(MetricValue(
            name="Health Score",
            current=current_score,
            previous=previous_score,
            trend=trend,
            change_percentage=change_pct,
            unit="points",
            threshold=80.0,
            status=status
        ))
        
        # Failed Checks Metric
        current_failed = validation_result.failed_checks
        previous_failed = historical_results[-1].failed_checks if historical_results else None
        
        failed_trend = "unknown"
        if previous_failed is not None:
            if current_failed < previous_failed:
                failed_trend = "improving"
            elif current_failed > previous_failed:
                failed_trend = "degrading"
            else:
                failed_trend = "stable"
        
        metrics.append(MetricValue(
            name="Failed Checks",
            current=float(current_failed),
            previous=float(previous_failed) if previous_failed is not None else None,
            trend=failed_trend,
            change_percentage=None,
            unit="checks",
            threshold=0.0,
            status="critical" if current_failed > 0 else "good"
        ))
        
        # Validation Duration Metric
        metrics.append(MetricValue(
            name="Validation Duration",
            current=validation_result.execution_time_seconds,
            previous=historical_results[-1].execution_time_seconds if historical_results else None,
            trend="stable",
            change_percentage=None,
            unit="seconds",
            threshold=120.0,
            status="good" if validation_result.execution_time_seconds < 120 else "warning"
        ))
        
        return metrics
    
    def _extract_findings(
        self,
        validation_result: ResourceValidationResult,
        evaluation: Optional[OverallEvaluation] = None
    ) -> List[Finding]:
        """Extract findings from validation results."""
        findings = []
        
        # Extract from failed checks
        for check in validation_result.checks:
            if check.status == ValidationStatus.FAIL:
                severity = "high" if validation_result.failed_checks <= 2 else "medium"
                
                finding = Finding(
                    title=check.check_name,
                    severity=severity,
                    category="configuration",
                    description=check.message or "Check failed",
                    impact=f"Check '{check.check_name}' failed, which may impact system reliability",
                    evidence=[
                        f"Expected: {check.expected}" if check.expected else "",
                        f"Actual: {check.actual}" if check.actual else ""
                    ],
                    recommendations=[
                        f"Investigate {check.check_name}",
                        "Review system logs for errors",
                        "Verify configuration settings"
                    ],
                    affected_components=[check.check_name]
                )
                findings.append(finding)
            
            elif check.status == ValidationStatus.WARNING:
                finding = Finding(
                    title=check.check_name,
                    severity="low",
                    category="configuration",
                    description=check.message or "Warning condition detected",
                    impact="Minor issue that should be monitored",
                    evidence=[f"Message: {check.message}"] if check.message else [],
                    recommendations=["Monitor the situation", "Review if issue persists"],
                    affected_components=[check.check_name]
                )
                findings.append(finding)
        
        return findings
        return "\n".join(sections)
    
    def _build_report_prompt(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification],
        evaluation: Optional[OverallEvaluation]
    ) -> str:
        """Build prompt for AI report generation.
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery results
            classification: Classification
            evaluation: Evaluation
        
        Returns:
            Prompt string
        """
        prompt_parts = [
            "Generate a comprehensive validation report for this resource:",
            f"\n## Resource Information",
            f"Host: {validation_result.resource_host}",
            f"Type: {validation_result.resource_type.value}",
            f"Overall Score: {validation_result.score}/100",
            f"Status: {validation_result.overall_status.value}",
        ]
        
        # Add discovery data
        if discovery_result:
            prompt_parts.extend([
                f"\n## Discovery Data",
                f"Open Ports: {len(discovery_result.ports)}",
                f"Running Processes: {len(discovery_result.processes)}",
                f"Detected Applications: {len(discovery_result.applications)}",
            ])
            
            if discovery_result.applications:
                apps = ", ".join(app.name for app in discovery_result.applications[:5])
                prompt_parts.append(f"Applications: {apps}")
        
        # Add classification
        if classification:
            prompt_parts.extend([
                f"\n## Classification",
                f"Category: {classification.category.value}",
                f"Confidence: {classification.confidence:.0%}",
            ])
            if classification.primary_application:
                prompt_parts.append(f"Primary Application: {classification.primary_application.name}")
        
        # Add validation results
        prompt_parts.extend([
            f"\n## Validation Results",
            f"Total Checks: {len(validation_result.checks)}",
            f"Passed: {validation_result.passed_checks}",
            f"Failed: {validation_result.failed_checks}",
            f"Warnings: {validation_result.warning_checks}",
            f"Execution Time: {validation_result.execution_time_seconds:.2f}s",
        ])
        
        # Add failed checks
        failed_checks = [c for c in validation_result.checks if c.status == ValidationStatus.FAIL]
        if failed_checks:
            prompt_parts.append("\n### Failed Checks:")
            for check in failed_checks[:10]:  # Limit to first 10
                prompt_parts.append(f"\n**{check.check_name}**")
                if check.message:
                    prompt_parts.append(f"Message: {check.message}")
        
        # Add evaluation
        if evaluation:
            prompt_parts.extend([
                f"\n## Evaluation",
                f"Overall Health: {evaluation.overall_health}",
                f"Confidence: {evaluation.confidence:.0%}",
                f"Summary: {evaluation.summary}",
            ])
            
            if evaluation.critical_issues:
                prompt_parts.append("\nCritical Issues:")
                for issue in evaluation.critical_issues:
                    prompt_parts.append(f"- {issue}")
            
            if evaluation.recommendations:
                prompt_parts.append("\nRecommendations:")
                for rec in evaluation.recommendations[:5]:
                    prompt_parts.append(f"- {rec}")
        
        prompt_parts.extend([
            "\n## Your Task",
            "Create a comprehensive validation report with:",
            "1. Executive summary for management",
            "2. Key findings (3-5 most important points)",
            "3. Critical issues requiring immediate attention",
            "4. Detailed sections organized by category",
            "5. Prioritized recommendations",
            "6. Clear conclusion",
            "7. Specific next steps",
            "\nUse markdown formatting and professional tone."
        ])
        
        return "\n".join(prompt_parts)
    
    def _format_report(self, report: ValidationReport, format: str) -> str:
        """Format report for output.
        
        Args:
            report: ValidationReport
            format: Output format
        
        Returns:
            Formatted report string
        """
        if format == "markdown":
            return self._format_markdown(report)
        elif format == "html":
            return self._format_html(report)
        elif format == "json":
            return report.model_dump_json(indent=2)
        else:
            return self._format_markdown(report)
    
    def _format_markdown(self, report: ValidationReport) -> str:
        """Format report as markdown.
        
        Args:
            report: ValidationReport
        
        Returns:
            Markdown string
        """
        sections = []
        
        # Executive Summary
        sections.append("# Validation Report")
        sections.append(f"\n## Executive Summary\n\n{report.executive_summary}")
        
        # Key Findings
        sections.append("\n## Key Findings\n")
        for i, finding in enumerate(report.key_findings, 1):
            sections.append(f"{i}. {finding}")
        
        # Critical Issues
        if report.critical_issues:
            sections.append("\n## ⚠️ Critical Issues\n")
            for i, issue in enumerate(report.critical_issues, 1):
                sections.append(f"{i}. **{issue}**")
        
        # Detailed Sections
        for section in sorted(report.sections, key=lambda s: s.priority):
            sections.append(f"\n## {section.title}\n\n{section.content}")
        
        # Recommendations
        sections.append("\n## Recommendations\n")
        for i, rec in enumerate(report.recommendations, 1):
            sections.append(f"{i}. {rec}")
        
        # Conclusion
        sections.append(f"\n## Conclusion\n\n{report.conclusion}")
        
        # Next Steps
        sections.append("\n## Next Steps\n")
        for i, step in enumerate(report.next_steps, 1):
            sections.append(f"{i}. {step}")
        
        return "\n".join(sections)
    
    def _format_html(self, report: ValidationReport) -> str:
        """Format report as HTML.
        
        Args:
            report: ValidationReport
        
        Returns:
            HTML string
        """
        # Simple HTML conversion (could be enhanced with proper HTML library)
        markdown = self._format_markdown(report)
        # Basic markdown to HTML conversion
        html = markdown.replace("# ", "<h1>").replace("\n", "</h1>\n", 1)
        html = html.replace("## ", "<h2>").replace("\n", "</h2>\n")
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        return f"<html><body>{html}</body></html>"


# Made with Bob
    def _get_status_icon(self, status: ValidationStatus) -> str:
        """Get icon for validation status.
        
        Args:
            status: Validation status
            
        Returns:
            Status icon emoji
        """
        icons = {
            ValidationStatus.PASS: "✅",
            ValidationStatus.FAIL: "🔴",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.SKIPPED: "⏭️",
            ValidationStatus.ERROR: "❌"
        }
        return icons.get(status, "❓")
    
    def _categorize_checks(self, checks: List[Any]) -> Dict[str, List[Any]]:
        """Categorize validation checks by type.
        
        Args:
            checks: List of CheckResult objects
            
        Returns:
            Dictionary mapping category to list of checks
        """
        categories = {
            'vm_health': [],
            'os_info': [],
            'filesystem': [],
            'network': [],
            'services': [],
            'database': [],
            'other': []
        }
        
        for check in checks:
            check_name_lower = check.check_name.lower()
            
            # Categorize based on check name patterns
            if any(keyword in check_name_lower for keyword in ['uptime', 'load', 'memory', 'cpu', 'hostname']):
                categories['vm_health'].append(check)
            elif any(keyword in check_name_lower for keyword in ['os', 'distribution', 'kernel', 'version']):
                categories['os_info'].append(check)
            elif any(keyword in check_name_lower for keyword in ['disk', 'filesystem', 'mount', 'storage', 'space']):
                categories['filesystem'].append(check)
            elif any(keyword in check_name_lower for keyword in ['network', 'port', 'firewall', 'connectivity', 'ping']):
                categories['network'].append(check)
            elif any(keyword in check_name_lower for keyword in ['service', 'systemd', 'daemon', 'process']):
                categories['services'].append(check)
            elif any(keyword in check_name_lower for keyword in ['database', 'oracle', 'mongo', 'sql', 'listener']):
                categories['database'].append(check)
            else:
                categories['other'].append(check)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _identify_critical_issues(
        self,
        validation_result: ResourceValidationResult,
        categorized_checks: Dict[str, List[Any]]
    ) -> List[Dict[str, str]]:
        """Identify critical issues requiring immediate attention.
        
        Args:
            validation_result: Validation results
            categorized_checks: Categorized checks
            
        Returns:
            List of critical issue dictionaries
        """
        critical_issues = []
        
        # Check for failed validations
        if validation_result.failed_checks > 0:
            failed = [c for c in validation_result.checks if c.status == ValidationStatus.FAIL]
            for check in failed:
                critical_issues.append({
                    'title': check.check_name,
                    'description': check.message or 'Check failed',
                    'severity': 'CRITICAL'
                })
        
        # Check filesystem usage
        if 'filesystem' in categorized_checks:
            for check in categorized_checks['filesystem']:
                if check.details and self._is_disk_critical(check.details):
                    usage = self._extract_disk_usage(check.details)
                    critical_issues.append({
                        'title': f'Filesystem {check.check_name} at critical capacity',
                        'description': f'Usage at {usage}% - exceeds 85% threshold',
                        'severity': 'CRITICAL'
                    })
        
        # Check for low memory
        if 'vm_health' in categorized_checks:
            for check in categorized_checks['vm_health']:
                if 'memory' in check.check_name.lower() and check.status == ValidationStatus.FAIL:
                    critical_issues.append({
                        'title': 'Low memory available',
                        'description': check.message or 'Memory below threshold',
                        'severity': 'CRITICAL'
                    })
        
        return critical_issues
    
    def _is_disk_critical(self, details: Dict[str, Any]) -> bool:
        """Check if disk usage is critical (>85%).
        
        Args:
            details: Check details dictionary
            
        Returns:
            True if critical, False otherwise
        """
        try:
            # Try to extract usage percentage
            usage_str = details.get('usage', details.get('use_percent', '0%'))
            if isinstance(usage_str, str):
                usage = float(usage_str.rstrip('%'))
            else:
                usage = float(usage_str)
            return usage > 85.0
        except (ValueError, TypeError, AttributeError):
            return False
    
    def _extract_disk_usage(self, details: Dict[str, Any]) -> str:
        """Extract disk usage percentage from details.
        
        Args:
            details: Check details dictionary
            
        Returns:
            Usage percentage as string
        """
        try:
            usage_str = details.get('usage', details.get('use_percent', '0%'))
            if isinstance(usage_str, str):
                return usage_str.rstrip('%')
            return str(int(float(usage_str)))
        except (ValueError, TypeError, AttributeError):
            return '0'
    
    def _create_check_table(
        self,
        checks: List[Any],
        headers: List[str]
    ) -> str:
        """Create a markdown table for checks.
        
        Args:
            checks: List of CheckResult objects
            headers: Table headers
            
        Returns:
            Markdown table string
        """
        if not checks:
            return "\n*No checks in this category*"
        
        lines = []
        lines.append("\n| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        
        for check in checks:
            status_icon = self._get_status_icon(check.status)
            
            # Extract result value
            result = check.actual or check.message or "N/A"
            if isinstance(result, dict):
                result = str(result)
            elif len(str(result)) > 50:
                result = str(result)[:47] + "..."
            
            lines.append(f"| {check.check_name} | {result} | {status_icon} |")
        
        return "\n".join(lines)
    
    def _create_filesystem_table(self, fs_checks: List[Any]) -> str:
        """Create detailed filesystem usage table.
        
        Args:
            fs_checks: List of filesystem CheckResult objects
            
        Returns:
            Markdown table string
        """
        if not fs_checks:
            return "\n*No filesystem checks available*"
        
        lines = []
        lines.append("\n| Mount | Size | Used | Available | Use% | Status |")
        lines.append("|---|---|---|---|---|---|")
        
        for check in fs_checks:
            status_icon = self._get_status_icon(check.status)
            
            # Extract filesystem details
            if check.details:
                mount = check.details.get('mount', check.check_name)
                size = check.details.get('size', 'N/A')
                used = check.details.get('used', 'N/A')
                available = check.details.get('available', 'N/A')
                use_pct = check.details.get('use_percent', check.details.get('usage', 'N/A'))
                
                # Highlight critical usage
                if self._is_disk_critical(check.details):
                    use_pct = f"**{use_pct}**"
                    status_icon = "🔴 **CRITICAL**"
                
                lines.append(f"| {mount} | {size} | {used} | {available} | {use_pct} | {status_icon} |")
            else:
                lines.append(f"| {check.check_name} | N/A | N/A | N/A | N/A | {status_icon} |")
        
        return "\n".join(lines)
    
    def _create_application_table(
        self,
        app: Any,
        categorized_checks: Dict[str, List[Any]]
    ) -> str:
        """Create table for application-specific checks.
        
        Args:
            app: ApplicationDetection object
            categorized_checks: Categorized checks
            
        Returns:
            Markdown table string
        """
        lines = []
        lines.append("\n| Check | Result | Status |")
        lines.append("|---|---|---|")
        
        # Add application metadata
        lines.append(f"| Name | {app.name} | ✅ |")
        if app.version:
            lines.append(f"| Version | {app.version} | ✅ |")
        lines.append(f"| Confidence | {app.confidence:.0%} | ✅ |")
        lines.append(f"| Detection Method | {app.detection_method} | ✅ |")
        
        # Add evidence if available
        if app.evidence:
            for key, value in list(app.evidence.items())[:5]:  # Limit to 5 items
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"| {key.replace('_', ' ').title()} | {value} | ℹ️ |")
        
        # Find related checks
        app_name_lower = app.name.lower()
        related_checks = []
        for category, checks in categorized_checks.items():
            for check in checks:
                if app_name_lower in check.check_name.lower():
                    related_checks.append(check)
        
        # Add related checks
        for check in related_checks:
            status_icon = self._get_status_icon(check.status)
            result = check.actual or check.message or "N/A"
            if len(str(result)) > 40:
                result = str(result)[:37] + "..."
            lines.append(f"| {check.check_name} | {result} | {status_icon} |")
        
        return "\n".join(lines)
    
    def _create_all_checks_table(self, checks: List[Any]) -> str:
        """Create comprehensive table of all checks.
        
        Args:
            checks: List of all CheckResult objects
            
        Returns:
            Markdown table string
        """
        lines = []
        lines.append("\n### All Validation Checks\n")
        lines.append("| # | Check Name | Status | Result |")
        lines.append("|---|---|---|---|")
        
        for i, check in enumerate(checks, 1):
            status_icon = self._get_status_icon(check.status)
            result = check.actual or check.message or "Passed"
            if isinstance(result, dict):
                result = "See details"
            elif len(str(result)) > 60:
                result = str(result)[:57] + "..."
            
            lines.append(f"| {i} | {check.check_name} | {status_icon} | {result} |")
        
        return "\n".join(lines)
    
    def _generate_specific_recommendations(
        self,
        validation_result: ResourceValidationResult,
        categorized_checks: Dict[str, List[Any]],
        critical_issues: List[Dict[str, str]],
        evaluation: Optional[OverallEvaluation]
    ) -> List[Dict[str, str]]:
        """Generate specific, actionable recommendations.
        
        Args:
            validation_result: Validation results
            categorized_checks: Categorized checks
            critical_issues: List of critical issues
            evaluation: Optional evaluation
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Critical issues first
        for issue in critical_issues:
            if 'filesystem' in issue['title'].lower():
                recommendations.append({
                    'priority': '🔴 **CRITICAL**',
                    'issue': issue['title'],
                    'recommendation': 'Free space immediately - clean logs, temp files, or expand volume'
                })
            elif 'memory' in issue['title'].lower():
                recommendations.append({
                    'priority': '🔴 **CRITICAL**',
                    'issue': issue['title'],
                    'recommendation': 'Investigate memory usage, restart services, or add more RAM'
                })
            else:
                recommendations.append({
                    'priority': '🔴 **CRITICAL**',
                    'issue': issue['title'],
                    'recommendation': issue['description']
                })
        
        # Network issues
        if 'network' in categorized_checks:
            failed_net = [c for c in categorized_checks['network'] if c.status == ValidationStatus.FAIL]
            for check in failed_net:
                recommendations.append({
                    'priority': '⚠️ **WARNING**',
                    'issue': f'{check.check_name} failed',
                    'recommendation': 'Verify firewall rules and network configuration'
                })
        
        # Service issues
        if 'services' in categorized_checks:
            failed_svc = [c for c in categorized_checks['services'] if c.status == ValidationStatus.FAIL]
            for check in failed_svc:
                recommendations.append({
                    'priority': '⚠️ **WARNING**',
                    'issue': f'Service {check.check_name} not running',
                    'recommendation': 'Start service and enable on boot: systemctl start/enable'
                })
        
        # Add evaluation recommendations if available
        if evaluation and evaluation.recommendations:
            for rec in evaluation.recommendations[:3]:  # Limit to top 3
                recommendations.append({
                    'priority': 'ℹ️ **INFO**',
                    'issue': 'General recommendation',
                    'recommendation': rec
                })
        
        # If no specific recommendations, add general ones
        if not recommendations:
            if validation_result.warning_checks > 0:
                recommendations.append({
                    'priority': 'ℹ️ **INFO**',
                    'issue': f'{validation_result.warning_checks} warnings detected',
                    'recommendation': 'Review warning checks and monitor for changes'
                })
            recommendations.append({
                'priority': 'ℹ️ **INFO**',
                'issue': 'Ongoing monitoring',
                'recommendation': 'Schedule regular validation checks to track system health'
            })
        
        return recommendations
    
    def _generate_next_steps(
        self,
        validation_result: ResourceValidationResult,
        critical_issues: List[Dict[str, str]],
        evaluation: Optional[OverallEvaluation]
    ) -> List[str]:
        """Generate specific next steps.
        
        Args:
            validation_result: Validation results
            critical_issues: List of critical issues
            evaluation: Optional evaluation
            
        Returns:
            List of next step strings
        """
        steps = []
        
        # Critical issues first
        if critical_issues:
            steps.append(f"🔴 **IMMEDIATE**: Address {len(critical_issues)} critical issue(s) identified above")
        
        # Failed checks
        if validation_result.failed_checks > 0:
            steps.append(f"Investigate and resolve {validation_result.failed_checks} failed check(s)")
        
        # Warnings
        if validation_result.warning_checks > 0:
            steps.append(f"Review {validation_result.warning_checks} warning(s) and determine if action is needed")
        
        # Evaluation next steps
        if evaluation and evaluation.next_steps:
            steps.extend(evaluation.next_steps[:2])  # Add top 2
        
        # General steps
        if not critical_issues and validation_result.failed_checks == 0:
            steps.append("✅ System is healthy - continue regular monitoring")
        
        steps.append("Schedule follow-up validation in 24-48 hours to verify fixes")
        steps.append("Document any changes made and update runbooks")
        
        return steps
