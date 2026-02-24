#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Reporting agent for AI-powered report generation."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from models import (
    ResourceValidationResult,
    WorkloadDiscoveryResult,
    ResourceClassification,
    ValidationStatus
)
from agents.base import AgentConfig, EnhancedAgent
from agents.evaluation_agent import OverallEvaluation
from tool_coordinator import ToolCoordinator
from state_manager import StateManager
from feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class ReportSection(BaseModel):
    """Individual report section."""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content in markdown")
    priority: int = Field(..., ge=1, le=5, description="Priority (1=highest)")


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
            self.log_step("Using template-based report generation (AI disabled)")
        
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
        # Build prompt with all available data
        prompt = self._build_report_prompt(
            validation_result,
            discovery_result,
            classification,
            evaluation
        )
        
        # Get AI-generated report
        result = await self.ai_agent.run(prompt)
        report = result.data
        
        self.log_step(
            f"AI report generated: {len(report.sections)} sections, "
            f"{len(report.recommendations)} recommendations"
        )
        
        return report
    
    def _generate_with_template(
        self,
        validation_result: ResourceValidationResult,
        discovery_result: Optional[WorkloadDiscoveryResult],
        classification: Optional[ResourceClassification],
        evaluation: Optional[OverallEvaluation]
    ) -> str:
        """Generate report using template.
        
        Args:
            validation_result: Validation results
            discovery_result: Discovery results
            classification: Classification
            evaluation: Evaluation
        
        Returns:
            Markdown report string
        """
        self.log_step("Using template-based report generation")
        
        sections = []
        
        # Header
        sections.append(f"# Validation Report: {validation_result.resource_host}")
        sections.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append(f"**Resource Type**: {validation_result.resource_type.value}")
        sections.append(f"**Overall Score**: {validation_result.score}/100")
        sections.append(f"**Status**: {validation_result.overall_status.value}")
        
        # Executive Summary
        sections.append("\n## Executive Summary")
        if evaluation:
            sections.append(f"\n{evaluation.summary}")
            sections.append(f"\n**Overall Health**: {evaluation.overall_health}")
        else:
            sections.append(f"\nValidation completed with {validation_result.passed_checks} passed, "
                          f"{validation_result.failed_checks} failed, and "
                          f"{validation_result.warning_checks} warning checks.")
        
        # Discovery Information
        if discovery_result:
            sections.append("\n## Discovered Workload")
            sections.append(f"\n- **Open Ports**: {len(discovery_result.ports)}")
            sections.append(f"- **Running Processes**: {len(discovery_result.processes)}")
            sections.append(f"- **Detected Applications**: {len(discovery_result.applications)}")
            
            if discovery_result.applications:
                sections.append("\n### Applications")
                for app in discovery_result.applications[:5]:
                    sections.append(f"- {app.name} (confidence: {app.confidence:.0%})")
        
        # Classification
        if classification:
            sections.append("\n## Resource Classification")
            sections.append(f"\n- **Category**: {classification.category.value}")
            sections.append(f"- **Confidence**: {classification.confidence:.0%}")
            if classification.primary_application:
                sections.append(f"- **Primary Application**: {classification.primary_application.name}")
        
        # Validation Results
        sections.append("\n## Validation Results")
        sections.append(f"\n- **Total Checks**: {len(validation_result.checks)}")
        sections.append(f"- **Passed**: {validation_result.passed_checks}")
        sections.append(f"- **Failed**: {validation_result.failed_checks}")
        sections.append(f"- **Warnings**: {validation_result.warning_checks}")
        sections.append(f"- **Execution Time**: {validation_result.execution_time_seconds:.2f}s")
        
        # Failed Checks
        failed_checks = [c for c in validation_result.checks if c.status == ValidationStatus.FAIL]
        if failed_checks:
            sections.append("\n### Failed Checks")
            for check in failed_checks:
                sections.append(f"\n#### {check.check_name}")
                if check.message:
                    sections.append(f"- **Message**: {check.message}")
                if check.expected:
                    sections.append(f"- **Expected**: {check.expected}")
                if check.actual:
                    sections.append(f"- **Actual**: {check.actual}")
        
        # Recommendations
        sections.append("\n## Recommendations")
        if evaluation and evaluation.recommendations:
            for i, rec in enumerate(evaluation.recommendations, 1):
                sections.append(f"{i}. {rec}")
        else:
            if validation_result.failed_checks > 0:
                sections.append(f"1. Address {validation_result.failed_checks} failed check(s)")
            if validation_result.warning_checks > 0:
                sections.append(f"2. Review {validation_result.warning_checks} warning(s)")
            sections.append("3. Schedule follow-up validation")
        
        # Next Steps
        sections.append("\n## Next Steps")
        if evaluation and evaluation.next_steps:
            for i, step in enumerate(evaluation.next_steps, 1):
                sections.append(f"{i}. {step}")
        else:
            sections.append("1. Review failed checks and warnings")
            sections.append("2. Implement recommended fixes")
            sections.append("3. Re-run validation")
        
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