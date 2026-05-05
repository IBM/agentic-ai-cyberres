"""
Per-Agent Performance Metrics System

Tracks performance metrics for each agent individually to enable:
- Performance monitoring and optimization
- Bottleneck identification
- Agent-specific debugging
- Trend analysis over time
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of agents in the system."""
    DISCOVERY = "discovery"
    CLASSIFICATION = "classification"
    VALIDATION_PLANNING = "validation_planning"
    VALIDATION_EXECUTION = "validation_execution"
    EVALUATION = "evaluation"
    ORCHESTRATOR = "orchestrator"


class AgentExecutionMetrics(BaseModel):
    """Metrics for a single agent execution."""
    agent_type: AgentType
    execution_id: str = Field(..., description="Unique execution identifier")
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    
    # Agent-specific metrics
    input_size: Optional[int] = Field(None, description="Size of input data")
    output_size: Optional[int] = Field(None, description="Size of output data")
    llm_calls: int = Field(0, description="Number of LLM calls made")
    llm_tokens: int = Field(0, description="Total tokens used")
    tool_calls: int = Field(0, description="Number of tool calls made")
    
    # Resource usage
    memory_mb: Optional[float] = Field(None, description="Peak memory usage in MB")
    cpu_percent: Optional[float] = Field(None, description="Average CPU usage")
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)


class AgentMetricsSummary(BaseModel):
    """Aggregated metrics for an agent type."""
    agent_type: AgentType
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    
    # Timing statistics
    avg_duration_seconds: float
    min_duration_seconds: float
    max_duration_seconds: float
    p50_duration_seconds: float
    p95_duration_seconds: float
    p99_duration_seconds: float
    
    # LLM usage
    total_llm_calls: int
    total_llm_tokens: int
    avg_llm_calls_per_execution: float
    avg_llm_tokens_per_execution: float
    
    # Tool usage
    total_tool_calls: int
    avg_tool_calls_per_execution: float
    
    # Resource usage
    avg_memory_mb: Optional[float] = None
    avg_cpu_percent: Optional[float] = None
    
    # Time period
    period_start: datetime
    period_end: datetime


class AgentMetricsCollector:
    """
    Collects and aggregates metrics for all agents.
    
    Usage:
        collector = AgentMetricsCollector()
        
        # Start tracking
        exec_id = collector.start_execution(AgentType.DISCOVERY)
        
        # ... agent execution ...
        
        # End tracking
        collector.end_execution(
            exec_id,
            success=True,
            llm_calls=2,
            tool_calls=5
        )
        
        # Get summary
        summary = collector.get_summary(AgentType.DISCOVERY)
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._executions: Dict[str, AgentExecutionMetrics] = {}
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        logger.info("Agent metrics collector initialized")
    
    def start_execution(
        self,
        agent_type: AgentType,
        execution_id: Optional[str] = None
    ) -> str:
        """
        Start tracking an agent execution.
        
        Args:
            agent_type: Type of agent
            execution_id: Optional custom execution ID
        
        Returns:
            Execution ID for tracking
        """
        if execution_id is None:
            execution_id = f"{agent_type.value}_{int(time.time() * 1000)}"
        
        self._active_executions[execution_id] = {
            "agent_type": agent_type,
            "start_time": datetime.utcnow(),
            "start_timestamp": time.time()
        }
        
        logger.debug(f"Started tracking {agent_type.value} execution: {execution_id}")
        return execution_id
    
    def end_execution(
        self,
        execution_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        input_size: Optional[int] = None,
        output_size: Optional[int] = None,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        tool_calls: int = 0,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ):
        """
        End tracking an agent execution and record metrics.
        
        Args:
            execution_id: Execution ID from start_execution
            success: Whether execution succeeded
            error_message: Error message if failed
            input_size: Size of input data
            output_size: Size of output data
            llm_calls: Number of LLM calls
            llm_tokens: Total tokens used
            tool_calls: Number of tool calls
            memory_mb: Peak memory usage
            cpu_percent: Average CPU usage
            custom_metrics: Additional custom metrics
        """
        if execution_id not in self._active_executions:
            logger.warning(f"Unknown execution ID: {execution_id}")
            return
        
        active = self._active_executions[execution_id]
        end_time = datetime.utcnow()
        duration = time.time() - active["start_timestamp"]
        
        metrics = AgentExecutionMetrics(
            agent_type=active["agent_type"],
            execution_id=execution_id,
            start_time=active["start_time"],
            end_time=end_time,
            duration_seconds=duration,
            success=success,
            error_message=error_message,
            input_size=input_size,
            output_size=output_size,
            llm_calls=llm_calls,
            llm_tokens=llm_tokens,
            tool_calls=tool_calls,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            custom_metrics=custom_metrics or {}
        )
        
        self._executions[execution_id] = metrics
        del self._active_executions[execution_id]
        
        logger.info(
            f"Completed {metrics.agent_type.value} execution: "
            f"{duration:.2f}s, success={success}, "
            f"llm_calls={llm_calls}, tool_calls={tool_calls}"
        )
    
    def get_summary(
        self,
        agent_type: AgentType,
        since: Optional[datetime] = None
    ) -> AgentMetricsSummary:
        """
        Get aggregated metrics summary for an agent type.
        
        Args:
            agent_type: Type of agent
            since: Optional start time for filtering
        
        Returns:
            Aggregated metrics summary
        """
        # Filter executions
        executions = [
            m for m in self._executions.values()
            if m.agent_type == agent_type and (
                since is None or m.start_time >= since
            )
        ]
        
        if not executions:
            # Return empty summary
            now = datetime.utcnow()
            return AgentMetricsSummary(
                agent_type=agent_type,
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                success_rate=0.0,
                avg_duration_seconds=0.0,
                min_duration_seconds=0.0,
                max_duration_seconds=0.0,
                p50_duration_seconds=0.0,
                p95_duration_seconds=0.0,
                p99_duration_seconds=0.0,
                total_llm_calls=0,
                total_llm_tokens=0,
                avg_llm_calls_per_execution=0.0,
                avg_llm_tokens_per_execution=0.0,
                total_tool_calls=0,
                avg_tool_calls_per_execution=0.0,
                period_start=now,
                period_end=now
            )
        
        # Calculate statistics
        successful = [m for m in executions if m.success]
        failed = [m for m in executions if not m.success]
        
        durations = sorted([m.duration_seconds for m in executions])
        total_llm_calls = sum(m.llm_calls for m in executions)
        total_llm_tokens = sum(m.llm_tokens for m in executions)
        total_tool_calls = sum(m.tool_calls for m in executions)
        
        # Calculate percentiles
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] * (1 - c) + data[f + 1] * c
            return data[f]
        
        # Memory and CPU averages
        memory_values = [m.memory_mb for m in executions if m.memory_mb is not None]
        cpu_values = [m.cpu_percent for m in executions if m.cpu_percent is not None]
        
        return AgentMetricsSummary(
            agent_type=agent_type,
            total_executions=len(executions),
            successful_executions=len(successful),
            failed_executions=len(failed),
            success_rate=len(successful) / len(executions),
            avg_duration_seconds=sum(durations) / len(durations),
            min_duration_seconds=min(durations),
            max_duration_seconds=max(durations),
            p50_duration_seconds=percentile(durations, 0.50),
            p95_duration_seconds=percentile(durations, 0.95),
            p99_duration_seconds=percentile(durations, 0.99),
            total_llm_calls=total_llm_calls,
            total_llm_tokens=total_llm_tokens,
            avg_llm_calls_per_execution=total_llm_calls / len(executions),
            avg_llm_tokens_per_execution=total_llm_tokens / len(executions),
            total_tool_calls=total_tool_calls,
            avg_tool_calls_per_execution=total_tool_calls / len(executions),
            avg_memory_mb=sum(memory_values) / len(memory_values) if memory_values else None,
            avg_cpu_percent=sum(cpu_values) / len(cpu_values) if cpu_values else None,
            period_start=min(m.start_time for m in executions),
            period_end=max(m.end_time for m in executions)
        )
    
    def get_all_summaries(
        self,
        since: Optional[datetime] = None
    ) -> Dict[AgentType, AgentMetricsSummary]:
        """
        Get summaries for all agent types.
        
        Args:
            since: Optional start time for filtering
        
        Returns:
            Dictionary mapping agent type to summary
        """
        return {
            agent_type: self.get_summary(agent_type, since)
            for agent_type in AgentType
        }
    
    def get_execution(self, execution_id: str) -> Optional[AgentExecutionMetrics]:
        """
        Get metrics for a specific execution.
        
        Args:
            execution_id: Execution ID
        
        Returns:
            Execution metrics or None if not found
        """
        return self._executions.get(execution_id)
    
    def get_recent_executions(
        self,
        agent_type: Optional[AgentType] = None,
        limit: int = 10
    ) -> List[AgentExecutionMetrics]:
        """
        Get recent executions, optionally filtered by agent type.
        
        Args:
            agent_type: Optional agent type filter
            limit: Maximum number of executions to return
        
        Returns:
            List of recent execution metrics
        """
        executions = list(self._executions.values())
        
        if agent_type:
            executions = [m for m in executions if m.agent_type == agent_type]
        
        # Sort by end time descending
        executions.sort(key=lambda m: m.end_time, reverse=True)
        
        return executions[:limit]
    
    def clear_old_executions(self, older_than: datetime):
        """
        Clear executions older than specified time.
        
        Args:
            older_than: Clear executions before this time
        """
        to_remove = [
            exec_id for exec_id, metrics in self._executions.items()
            if metrics.end_time < older_than
        ]
        
        for exec_id in to_remove:
            del self._executions[exec_id]
        
        logger.info(f"Cleared {len(to_remove)} old execution metrics")
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics as dictionary.
        
        Returns:
            Dictionary with all metrics data
        """
        return {
            "executions": [
                m.model_dump() for m in self._executions.values()
            ],
            "summaries": {
                agent_type.value: self.get_summary(agent_type).model_dump()
                for agent_type in AgentType
            }
        }


# Global metrics collector instance
_global_collector: Optional[AgentMetricsCollector] = None


def get_global_collector() -> AgentMetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        Global AgentMetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = AgentMetricsCollector()
    return _global_collector


# Context manager for easy metrics tracking
class track_agent_execution:
    """
    Context manager for tracking agent execution metrics.
    
    Usage:
        with track_agent_execution(AgentType.DISCOVERY) as tracker:
            # ... agent execution ...
            tracker.record_llm_call()
            tracker.record_tool_call()
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        collector: Optional[AgentMetricsCollector] = None
    ):
        """
        Initialize execution tracker.
        
        Args:
            agent_type: Type of agent
            collector: Optional custom collector (uses global if None)
        """
        self.agent_type = agent_type
        self.collector = collector or get_global_collector()
        self.execution_id: Optional[str] = None
        self.llm_calls = 0
        self.llm_tokens = 0
        self.tool_calls = 0
        self.success = True
        self.error_message: Optional[str] = None
        self.custom_metrics: Dict[str, Any] = {}
    
    def __enter__(self):
        """Start tracking."""
        self.execution_id = self.collector.start_execution(self.agent_type)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking."""
        if exc_type is not None:
            self.success = False
            self.error_message = str(exc_val)
        
        if self.execution_id:
            self.collector.end_execution(
                self.execution_id,
                success=self.success,
                error_message=self.error_message,
                llm_calls=self.llm_calls,
                llm_tokens=self.llm_tokens,
                tool_calls=self.tool_calls,
                custom_metrics=self.custom_metrics
            )
        
        return False  # Don't suppress exceptions
    
    def record_llm_call(self, tokens: int = 0):
        """Record an LLM call."""
        self.llm_calls += 1
        self.llm_tokens += tokens
    
    def record_tool_call(self):
        """Record a tool call."""
        self.tool_calls += 1
    
    def add_custom_metric(self, key: str, value: Any):
        """Add a custom metric."""
        self.custom_metrics[key] = value


# Made with Bob