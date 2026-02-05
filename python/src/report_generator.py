#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Report generation for recovery validation agent."""

import logging
from typing import Dict, Any
from datetime import datetime
from jinja2 import Template
from models import ValidationReport, ValidationStatus

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate validation reports in various formats."""
    
    def __init__(self):
        """Initialize report generator."""
        pass
    
    def generate_text_report(self, report: ValidationReport) -> str:
        """Generate plain text report.
        
        Args:
            report: Validation report
        
        Returns:
            Plain text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("RECOVERY VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary section
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Resource Type: {report.result.resource_type.value.upper()}")
        lines.append(f"Resource Host: {report.result.resource_host}")
        lines.append(f"Overall Status: {report.result.overall_status.value}")
        lines.append(f"Validation Score: {report.result.score}/100")
        lines.append(f"Execution Time: {report.result.execution_time_seconds:.2f} seconds")
        lines.append(f"Report Generated: {report.report_generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        
        # Statistics
        lines.append("VALIDATION STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total Checks: {len(report.result.checks)}")
        lines.append(f"Passed: {report.result.passed_checks}")
        lines.append(f"Failed: {report.result.failed_checks}")
        lines.append(f"Warnings: {report.result.warning_checks}")
        lines.append("")
        
        # Detailed results
        lines.append("DETAILED RESULTS")
        lines.append("-" * 80)
        
        for check in report.result.checks:
            status_symbol = {
                ValidationStatus.PASS: "✓",
                ValidationStatus.FAIL: "✗",
                ValidationStatus.WARNING: "⚠",
                ValidationStatus.ERROR: "⚠",
                ValidationStatus.SKIPPED: "○"
            }.get(check.status, "?")
            
            lines.append(f"{status_symbol} {check.check_name}")
            lines.append(f"  Status: {check.status.value}")
            if check.expected:
                lines.append(f"  Expected: {check.expected}")
            if check.actual:
                lines.append(f"  Actual: {check.actual}")
            if check.message:
                lines.append(f"  Message: {check.message}")
            lines.append("")
        
        # Recommendations
        if report.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 80)
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        # Discovery info
        if report.result.discovery_info:
            lines.append("DISCOVERY INFORMATION")
            lines.append("-" * 80)
            for key, value in report.result.discovery_info.items():
                lines.append(f"{key}: {value}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generate_html_report(self, report: ValidationReport) -> str:
        """Generate HTML report for email.
        
        Args:
            report: Validation report
        
        Returns:
            HTML report
        """
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 28px;
        }
        .header .subtitle {
            font-size: 14px;
            opacity: 0.9;
        }
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            margin: 10px 0;
        }
        .status-pass { background: #10b981; color: white; }
        .status-fail { background: #ef4444; color: white; }
        .status-warning { background: #f59e0b; color: white; }
        .status-error { background: #ef4444; color: white; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .summary-card {
            background: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .summary-card .label {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .summary-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #1e293b;
        }
        .section {
            margin: 30px 0;
        }
        .section-title {
            font-size: 20px;
            font-weight: bold;
            color: #1e293b;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }
        .check-item {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .check-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .check-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 10px;
            font-weight: bold;
        }
        .icon-pass { background: #10b981; color: white; }
        .icon-fail { background: #ef4444; color: white; }
        .icon-warning { background: #f59e0b; color: white; }
        .icon-error { background: #ef4444; color: white; }
        .icon-skipped { background: #94a3b8; color: white; }
        .check-name {
            font-weight: bold;
            flex: 1;
        }
        .check-details {
            font-size: 14px;
            color: #64748b;
            margin-left: 34px;
        }
        .check-details div {
            margin: 5px 0;
        }
        .recommendations {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 6px;
        }
        .recommendations ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #64748b;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Recovery Validation Report</h1>
        <div class="subtitle">{{ resource_type }} | {{ timestamp }}</div>
    </div>
    
    <div class="summary-grid">
        <div class="summary-card">
            <div class="label">Overall Status</div>
            <div class="value">
                <span class="status-badge status-{{ status_class }}">{{ overall_status }}</span>
            </div>
        </div>
        <div class="summary-card">
            <div class="label">Validation Score</div>
            <div class="value">{{ score }}/100</div>
        </div>
        <div class="summary-card">
            <div class="label">Resource Host</div>
            <div class="value" style="font-size: 18px;">{{ host }}</div>
        </div>
        <div class="summary-card">
            <div class="label">Execution Time</div>
            <div class="value">{{ execution_time }}s</div>
        </div>
    </div>
    
    <div class="summary-grid">
        <div class="summary-card">
            <div class="label">Total Checks</div>
            <div class="value">{{ total_checks }}</div>
        </div>
        <div class="summary-card" style="border-left-color: #10b981;">
            <div class="label">Passed</div>
            <div class="value" style="color: #10b981;">{{ passed_checks }}</div>
        </div>
        <div class="summary-card" style="border-left-color: #ef4444;">
            <div class="label">Failed</div>
            <div class="value" style="color: #ef4444;">{{ failed_checks }}</div>
        </div>
        <div class="summary-card" style="border-left-color: #f59e0b;">
            <div class="label">Warnings</div>
            <div class="value" style="color: #f59e0b;">{{ warning_checks }}</div>
        </div>
    </div>
    
    {% if recommendations %}
    <div class="section">
        <div class="recommendations">
            <strong>⚠️ Recommendations</strong>
            <ul>
            {% for rec in recommendations %}
                <li>{{ rec }}</li>
            {% endfor %}
            </ul>
        </div>
    </div>
    {% endif %}
    
    <div class="section">
        <div class="section-title">Detailed Validation Results</div>
        {% for check in checks %}
        <div class="check-item">
            <div class="check-header">
                <div class="check-icon icon-{{ check.status_class }}">
                    {{ check.icon }}
                </div>
                <div class="check-name">{{ check.name }}</div>
            </div>
            <div class="check-details">
                {% if check.expected %}
                <div><strong>Expected:</strong> {{ check.expected }}</div>
                {% endif %}
                {% if check.actual %}
                <div><strong>Actual:</strong> {{ check.actual }}</div>
                {% endif %}
                {% if check.message %}
                <div><strong>Message:</strong> {{ check.message }}</div>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    
    <div class="footer">
        <p>Generated by CyberRes Recovery Validation Agent</p>
        <p>Report ID: {{ report_id }} | Generated at {{ timestamp }}</p>
    </div>
</body>
</html>
        """
        
        # Prepare template data
        status_class_map = {
            ValidationStatus.PASS: "pass",
            ValidationStatus.FAIL: "fail",
            ValidationStatus.WARNING: "warning",
            ValidationStatus.ERROR: "error"
        }
        
        icon_map = {
            ValidationStatus.PASS: "✓",
            ValidationStatus.FAIL: "✗",
            ValidationStatus.WARNING: "⚠",
            ValidationStatus.ERROR: "⚠",
            ValidationStatus.SKIPPED: "○"
        }
        
        checks_data = []
        for check in report.result.checks:
            checks_data.append({
                "name": check.check_name,
                "status_class": status_class_map.get(check.status, "error"),
                "icon": icon_map.get(check.status, "?"),
                "expected": check.expected,
                "actual": check.actual,
                "message": check.message
            })
        
        template_data = {
            "resource_type": report.result.resource_type.value.upper(),
            "timestamp": report.report_generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "overall_status": report.result.overall_status.value,
            "status_class": status_class_map.get(report.result.overall_status, "error"),
            "score": report.result.score,
            "host": report.result.resource_host,
            "execution_time": f"{report.result.execution_time_seconds:.2f}",
            "total_checks": len(report.result.checks),
            "passed_checks": report.result.passed_checks,
            "failed_checks": report.result.failed_checks,
            "warning_checks": report.result.warning_checks,
            "recommendations": report.recommendations,
            "checks": checks_data,
            "report_id": f"{report.result.resource_type.value}-{report.result.resource_host}-{int(report.report_generated_at.timestamp())}"
        }
        
        template = Template(template_str)
        return template.render(**template_data)
    
    def generate_recommendations(self, report: ValidationReport) -> list[str]:
        """Generate recommendations based on validation results.
        
        Args:
            report: Validation report
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        for check in report.result.checks:
            if check.status == ValidationStatus.FAIL:
                if "filesystem" in check.check_id.lower():
                    recommendations.append(
                        f"Clean up {check.check_name} to free disk space (currently at {check.actual})"
                    )
                elif "memory" in check.check_id.lower():
                    recommendations.append(
                        f"Investigate high memory usage on {report.result.resource_host} ({check.actual})"
                    )
                elif "tablespace" in check.check_id.lower():
                    recommendations.append(
                        f"Extend or clean up {check.check_name} (currently {check.actual})"
                    )
                elif "service" in check.check_id.lower():
                    recommendations.append(
                        f"Start required services that are not running: {check.message}"
                    )
                elif "connection" in check.check_id.lower():
                    recommendations.append(
                        f"Verify database credentials and network connectivity for {report.result.resource_host}"
                    )
                elif "replica" in check.check_id.lower():
                    recommendations.append(
                        f"Check MongoDB replica set configuration and member status"
                    )
        
        # Add general recommendations based on overall status
        if report.result.overall_status == ValidationStatus.FAIL:
            if report.result.score < 50:
                recommendations.append(
                    "Multiple critical issues detected. Consider re-running recovery process."
                )
            else:
                recommendations.append(
                    "Address failed checks before putting resource into production."
                )
        
        return recommendations

# Made with Bob
