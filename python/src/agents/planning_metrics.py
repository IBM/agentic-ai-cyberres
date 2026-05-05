"""
Planning Metrics Aggregation System

This module provides comprehensive metrics tracking and reporting for the
LLM-based validation planning system. It tracks planning performance,
success rates, tool selection patterns, and plan quality metrics.

Key Features:
- Real-time metrics collection during planning
- Aggregated statistics across multiple workflows
- Planning quality analysis
- Tool selection pattern tracking
- Performance benchmarking
- Detailed reporting capabilities
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from statistics import mean, median, stdev

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlanningMetricsSummary(BaseModel):
    """Summary of planning metrics for a single planning operation."""
    planner_used: str = Field(..., description="Planner type (llm or deterministic)")
    planning_time_ms: int = Field(..., description="Planning duration in milliseconds")
    llm_model: Optional[str] = Field(None, description="LLM model used")
    num_checks: int = Field(..., description="Number of checks in plan")
    num_priority_checks: int = Field(..., description="Number of high-priority checks")
    tool_names: List[str] = Field(default_factory=list, description="Tools selected")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback")
    resource_category: str = Field(..., description="Resource category")
    timestamp: datetime = Field(default_factory=datetime.now)


@dataclass
class PlanningMetricsAggregator:
    """Aggregates and analyzes planning metrics across multiple workflows.
    
    This class collects metrics from individual planning operations and
    provides comprehensive analysis including:
    - Success rates (LLM vs fallback)
    - Performance statistics (timing, check counts)
    - Tool selection patterns
    - Quality metrics
    - Trend analysis
    
    Example:
        >>> aggregator = PlanningMetricsAggregator()
        >>> aggregator.record_planning(metrics)
        >>> report = aggregator.generate_report()
        >>> print(report)
    """
    
    # Metrics storage
    all_metrics: List[PlanningMetricsSummary] = field(default_factory=list)
    
    # Counters
    llm_success_count: int = 0
    llm_failure_count: int = 0
    deterministic_count: int = 0
    
    # Timing statistics
    planning_times_ms: List[int] = field(default_factory=list)
    llm_planning_times_ms: List[int] = field(default_factory=list)
    deterministic_planning_times_ms: List[int] = field(default_factory=list)
    
    # Check statistics
    check_counts: List[int] = field(default_factory=list)
    priority_check_counts: List[int] = field(default_factory=list)
    
    # Tool usage tracking
    tool_usage_counter: Counter = field(default_factory=Counter)
    tool_by_category: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    
    # Fallback reasons
    fallback_reasons: Counter = field(default_factory=Counter)
    
    # Category statistics
    category_stats: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(dict))
    
    def record_planning(self, metrics: PlanningMetricsSummary) -> None:
        """Record metrics from a single planning operation.
        
        Args:
            metrics: Planning metrics to record
        """
        self.all_metrics.append(metrics)
        
        # Update counters
        if metrics.planner_used == "llm":
            self.llm_success_count += 1
            self.llm_planning_times_ms.append(metrics.planning_time_ms)
        else:
            self.deterministic_count += 1
            self.deterministic_planning_times_ms.append(metrics.planning_time_ms)
            
            if metrics.fallback_reason:
                self.fallback_reasons[metrics.fallback_reason] += 1
                self.llm_failure_count += 1
        
        # Update timing statistics
        self.planning_times_ms.append(metrics.planning_time_ms)
        
        # Update check statistics
        self.check_counts.append(metrics.num_checks)
        self.priority_check_counts.append(metrics.num_priority_checks)
        
        # Update tool usage
        for tool_name in metrics.tool_names:
            self.tool_usage_counter[tool_name] += 1
            self.tool_by_category[metrics.resource_category][tool_name] += 1
        
        # Update category statistics
        category = metrics.resource_category
        if category not in self.category_stats:
            self.category_stats[category] = {
                "count": 0,
                "llm_count": 0,
                "deterministic_count": 0,
                "avg_checks": 0,
                "avg_time_ms": 0
            }
        
        cat_stats = self.category_stats[category]
        cat_stats["count"] += 1
        if metrics.planner_used == "llm":
            cat_stats["llm_count"] += 1
        else:
            cat_stats["deterministic_count"] += 1
        
        logger.debug(f"Recorded planning metrics: {metrics.planner_used} planner, "
                    f"{metrics.num_checks} checks, {metrics.planning_time_ms}ms")
    
    def get_llm_success_rate(self) -> float:
        """Calculate LLM planning success rate.
        
        Returns:
            Success rate as percentage (0-100)
        """
        total_attempts = self.llm_success_count + self.llm_failure_count
        if total_attempts == 0:
            return 0.0
        return (self.llm_success_count / total_attempts) * 100
    
    def get_fallback_usage_rate(self) -> float:
        """Calculate fallback usage rate.
        
        Returns:
            Fallback rate as percentage (0-100)
        """
        total = len(self.all_metrics)
        if total == 0:
            return 0.0
        return (self.deterministic_count / total) * 100
    
    def get_average_planning_time(self) -> float:
        """Get average planning time across all operations.
        
        Returns:
            Average time in milliseconds
        """
        if not self.planning_times_ms:
            return 0.0
        return mean(self.planning_times_ms)
    
    def get_planning_time_stats(self) -> Dict[str, float]:
        """Get detailed planning time statistics.
        
        Returns:
            Dictionary with min, max, mean, median, stdev
        """
        if not self.planning_times_ms:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "stdev": 0.0
            }
        
        return {
            "min": float(min(self.planning_times_ms)),
            "max": float(max(self.planning_times_ms)),
            "mean": mean(self.planning_times_ms),
            "median": median(self.planning_times_ms),
            "stdev": stdev(self.planning_times_ms) if len(self.planning_times_ms) > 1 else 0.0
        }
    
    def get_check_count_stats(self) -> Dict[str, float]:
        """Get statistics on number of checks per plan.
        
        Returns:
            Dictionary with min, max, mean, median
        """
        if not self.check_counts:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0
            }
        
        return {
            "min": float(min(self.check_counts)),
            "max": float(max(self.check_counts)),
            "mean": mean(self.check_counts),
            "median": median(self.check_counts)
        }
    
    def get_top_tools(self, n: int = 10) -> List[tuple[str, int]]:
        """Get most frequently used tools.
        
        Args:
            n: Number of top tools to return
        
        Returns:
            List of (tool_name, count) tuples
        """
        return self.tool_usage_counter.most_common(n)
    
    def get_tool_selection_patterns(self) -> Dict[str, List[tuple[str, int]]]:
        """Get tool selection patterns by resource category.
        
        Returns:
            Dictionary mapping category to list of (tool, count) tuples
        """
        patterns = {}
        for category, counter in self.tool_by_category.items():
            patterns[category] = counter.most_common(10)
        return patterns
    
    def get_fallback_reasons_summary(self) -> List[tuple[str, int]]:
        """Get summary of fallback reasons.
        
        Returns:
            List of (reason, count) tuples sorted by frequency
        """
        return self.fallback_reasons.most_common()
    
    def get_category_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed breakdown by resource category.
        
        Returns:
            Dictionary with statistics per category
        """
        breakdown = {}
        
        for category, stats in self.category_stats.items():
            # Calculate averages
            category_metrics = [m for m in self.all_metrics if m.resource_category == category]
            
            if category_metrics:
                avg_checks = mean([m.num_checks for m in category_metrics])
                avg_time = mean([m.planning_time_ms for m in category_metrics])
                avg_priority = mean([m.num_priority_checks for m in category_metrics])
            else:
                avg_checks = avg_time = avg_priority = 0.0
            
            breakdown[category] = {
                "total_plans": stats["count"],
                "llm_plans": stats["llm_count"],
                "deterministic_plans": stats["deterministic_count"],
                "llm_success_rate": (stats["llm_count"] / stats["count"] * 100) if stats["count"] > 0 else 0.0,
                "avg_checks": avg_checks,
                "avg_priority_checks": avg_priority,
                "avg_planning_time_ms": avg_time
            }
        
        return breakdown
    
    def generate_report(self) -> str:
        """Generate comprehensive planning metrics report.
        
        Returns:
            Formatted report string
        """
        if not self.all_metrics:
            return "No planning metrics recorded yet."
        
        report_lines = [
            "=" * 80,
            "PLANNING METRICS REPORT",
            "=" * 80,
            "",
            "OVERVIEW",
            "-" * 80,
            f"Total Plans Created: {len(self.all_metrics)}",
            f"LLM Plans: {self.llm_success_count} ({self.get_llm_success_rate():.1f}% success rate)",
            f"Deterministic Plans: {self.deterministic_count} ({self.get_fallback_usage_rate():.1f}% fallback rate)",
            f"LLM Failures: {self.llm_failure_count}",
            "",
            "PERFORMANCE METRICS",
            "-" * 80,
        ]
        
        # Planning time statistics
        time_stats = self.get_planning_time_stats()
        report_lines.extend([
            f"Average Planning Time: {time_stats['mean']:.1f}ms",
            f"Median Planning Time: {time_stats['median']:.1f}ms",
            f"Min/Max Planning Time: {time_stats['min']:.0f}ms / {time_stats['max']:.0f}ms",
            f"Std Dev: {time_stats['stdev']:.1f}ms",
        ])
        
        if self.llm_planning_times_ms:
            report_lines.append(f"Avg LLM Planning Time: {mean(self.llm_planning_times_ms):.1f}ms")
        if self.deterministic_planning_times_ms:
            report_lines.append(f"Avg Deterministic Planning Time: {mean(self.deterministic_planning_times_ms):.1f}ms")
        
        report_lines.append("")
        
        # Check count statistics
        check_stats = self.get_check_count_stats()
        report_lines.extend([
            "CHECK STATISTICS",
            "-" * 80,
            f"Average Checks per Plan: {check_stats['mean']:.1f}",
            f"Median Checks per Plan: {check_stats['median']:.0f}",
            f"Min/Max Checks: {check_stats['min']:.0f} / {check_stats['max']:.0f}",
            f"Average Priority Checks: {mean(self.priority_check_counts):.1f}" if self.priority_check_counts else "Average Priority Checks: 0.0",
            "",
        ])
        
        # Tool usage patterns
        report_lines.extend([
            "TOP TOOLS USED",
            "-" * 80,
        ])
        
        top_tools = self.get_top_tools(10)
        for i, (tool, count) in enumerate(top_tools, 1):
            percentage = (count / len(self.all_metrics)) * 100
            report_lines.append(f"{i:2d}. {tool:40s} {count:4d} ({percentage:5.1f}%)")
        
        report_lines.append("")
        
        # Fallback reasons
        if self.fallback_reasons:
            report_lines.extend([
                "FALLBACK REASONS",
                "-" * 80,
            ])
            for reason, count in self.get_fallback_reasons_summary():
                percentage = (count / self.llm_failure_count) * 100 if self.llm_failure_count > 0 else 0
                report_lines.append(f"  {reason}: {count} ({percentage:.1f}%)")
            report_lines.append("")
        
        # Category breakdown
        report_lines.extend([
            "CATEGORY BREAKDOWN",
            "-" * 80,
        ])
        
        category_breakdown = self.get_category_breakdown()
        for category, stats in sorted(category_breakdown.items()):
            report_lines.extend([
                f"\n{category.upper()}:",
                f"  Total Plans: {stats['total_plans']}",
                f"  LLM Plans: {stats['llm_plans']} ({stats['llm_success_rate']:.1f}%)",
                f"  Deterministic Plans: {stats['deterministic_plans']}",
                f"  Avg Checks: {stats['avg_checks']:.1f}",
                f"  Avg Priority Checks: {stats['avg_priority_checks']:.1f}",
                f"  Avg Planning Time: {stats['avg_planning_time_ms']:.1f}ms",
            ])
        
        report_lines.extend([
            "",
            "=" * 80,
        ])
        
        return "\n".join(report_lines)
    
    def get_summary_dict(self) -> Dict[str, Any]:
        """Get metrics summary as dictionary for programmatic access.
        
        Returns:
            Dictionary with all key metrics
        """
        return {
            "total_plans": len(self.all_metrics),
            "llm_plans": self.llm_success_count,
            "deterministic_plans": self.deterministic_count,
            "llm_success_rate": self.get_llm_success_rate(),
            "fallback_rate": self.get_fallback_usage_rate(),
            "avg_planning_time_ms": self.get_average_planning_time(),
            "planning_time_stats": self.get_planning_time_stats(),
            "check_count_stats": self.get_check_count_stats(),
            "top_tools": self.get_top_tools(10),
            "fallback_reasons": self.get_fallback_reasons_summary(),
            "category_breakdown": self.get_category_breakdown(),
            "tool_selection_patterns": self.get_tool_selection_patterns()
        }
    
    def reset(self) -> None:
        """Reset all metrics to initial state."""
        self.all_metrics.clear()
        self.llm_success_count = 0
        self.llm_failure_count = 0
        self.deterministic_count = 0
        self.planning_times_ms.clear()
        self.llm_planning_times_ms.clear()
        self.deterministic_planning_times_ms.clear()
        self.check_counts.clear()
        self.priority_check_counts.clear()
        self.tool_usage_counter.clear()
        self.tool_by_category.clear()
        self.fallback_reasons.clear()
        self.category_stats.clear()
        logger.info("Planning metrics aggregator reset")


class PlanningMetricsReporter:
    """Reporter for planning metrics with various output formats.
    
    This class provides different reporting formats for planning metrics:
    - Console output (formatted text)
    - JSON export
    - CSV export
    - Summary statistics
    
    Example:
        >>> reporter = PlanningMetricsReporter(aggregator)
        >>> reporter.print_report()
        >>> reporter.export_json("metrics.json")
    """
    
    def __init__(self, aggregator: PlanningMetricsAggregator):
        """Initialize reporter with metrics aggregator.
        
        Args:
            aggregator: Metrics aggregator to report on
        """
        self.aggregator = aggregator
    
    def print_report(self) -> None:
        """Print formatted report to console."""
        report = self.aggregator.generate_report()
        print(report)
    
    def get_report_text(self) -> str:
        """Get report as formatted text string.
        
        Returns:
            Formatted report string
        """
        return self.aggregator.generate_report()
    
    def get_summary_json(self) -> Dict[str, Any]:
        """Get metrics summary as JSON-serializable dictionary.
        
        Returns:
            Dictionary with all metrics
        """
        return self.aggregator.get_summary_dict()
    
    def export_json(self, filepath: str) -> None:
        """Export metrics to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        import json
        
        summary = self.get_summary_json()
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Planning metrics exported to {filepath}")
    
    def export_csv(self, filepath: str) -> None:
        """Export individual planning metrics to CSV file.
        
        Args:
            filepath: Path to output CSV file
        """
        import csv
        
        if not self.aggregator.all_metrics:
            logger.warning("No metrics to export")
            return
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "timestamp",
                "planner_used",
                "planning_time_ms",
                "llm_model",
                "num_checks",
                "num_priority_checks",
                "resource_category",
                "fallback_reason",
                "tools_used"
            ])
            
            # Data rows
            for metric in self.aggregator.all_metrics:
                writer.writerow([
                    metric.timestamp.isoformat(),
                    metric.planner_used,
                    metric.planning_time_ms,
                    metric.llm_model or "",
                    metric.num_checks,
                    metric.num_priority_checks,
                    metric.resource_category,
                    metric.fallback_reason or "",
                    ",".join(metric.tool_names)
                ])
        
        logger.info(f"Planning metrics exported to {filepath}")


# Global metrics aggregator instance
_global_aggregator: Optional[PlanningMetricsAggregator] = None


def get_global_aggregator() -> PlanningMetricsAggregator:
    """Get or create global metrics aggregator instance.
    
    Returns:
        Global PlanningMetricsAggregator instance
    """
    global _global_aggregator
    if _global_aggregator is None:
        _global_aggregator = PlanningMetricsAggregator()
    return _global_aggregator


def reset_global_aggregator() -> None:
    """Reset the global metrics aggregator."""
    global _global_aggregator
    if _global_aggregator is not None:
        _global_aggregator.reset()

# Made with Bob
