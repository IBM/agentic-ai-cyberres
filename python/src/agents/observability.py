"""
OpenTelemetry Instrumentation for BeeAI Agents

Provides comprehensive observability with:
- Distributed tracing across agent containers
- Metrics collection for performance monitoring
- Integration with Arize Phoenix for visualization
- Compatible with Datadog, Grafana, and other OTEL backends
"""

import logging
import os
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


class ObservabilityConfig:
    """Configuration for OpenTelemetry observability."""
    
    def __init__(
        self,
        enabled: bool = True,
        service_name: str = "beeai-validation",
        service_version: str = "1.0.0",
        otlp_endpoint: Optional[str] = None,
        export_interval_ms: int = 5000,
        max_export_batch_size: int = 512,
    ):
        self.enabled = enabled
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://localhost:4317"
        )
        self.export_interval_ms = export_interval_ms
        self.max_export_batch_size = max_export_batch_size


class BeeAIObservability:
    """
    OpenTelemetry instrumentation for BeeAI agents.
    
    Features:
    - Automatic span creation for agent operations
    - Metrics collection (latency, success rate, error rate)
    - Context propagation across agent boundaries
    - Integration with Arize Phoenix dashboard
    
    Example:
        >>> config = ObservabilityConfig(
        ...     service_name="discovery-agent",
        ...     otlp_endpoint="http://phoenix:4317"
        ... )
        >>> obs = BeeAIObservability(config)
        >>> obs.setup()
        >>> 
        >>> # Instrument a function
        >>> @obs.trace_operation("discover_workload")
        >>> async def discover(resource):
        ...     return await agent.discover(resource)
    """
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        self._metrics: Dict[str, Any] = {}
        self._initialized = False
    
    def setup(self) -> None:
        """Initialize OpenTelemetry providers and exporters."""
        if not self.config.enabled:
            logger.info("Observability disabled")
            return
        
        if self._initialized:
            logger.warning("Observability already initialized")
            return
        
        try:
            # Create resource with service metadata
            resource = Resource.create({
                SERVICE_NAME: self.config.service_name,
                SERVICE_VERSION: self.config.service_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            })
            
            # Setup tracing
            self._setup_tracing(resource)
            
            # Setup metrics
            self._setup_metrics(resource)
            
            self._initialized = True
            logger.info(
                f"✓ Observability initialized: {self.config.service_name} "
                f"→ {self.config.otlp_endpoint}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize observability: {e}", exc_info=True)
            raise
    
    def _setup_tracing(self, resource: Resource) -> None:
        """Setup distributed tracing with OTLP export."""
        # Create OTLP span exporter
        span_exporter = OTLPSpanExporter(
            endpoint=self.config.otlp_endpoint,
            insecure=True  # Use TLS in production
        )
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                span_exporter,
                max_export_batch_size=self.config.max_export_batch_size
            )
        )
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Get tracer for this service
        self.tracer = trace.get_tracer(
            self.config.service_name,
            self.config.service_version
        )
        
        logger.info(f"✓ Tracing configured: {self.config.service_name}")
    
    def _setup_metrics(self, resource: Resource) -> None:
        """Setup metrics collection with OTLP export."""
        # Create OTLP metric exporter
        metric_exporter = OTLPMetricExporter(
            endpoint=self.config.otlp_endpoint,
            insecure=True
        )
        
        # Create metric reader
        metric_reader = PeriodicExportingMetricReader(
            metric_exporter,
            export_interval_millis=self.config.export_interval_ms
        )
        
        # Create meter provider
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(meter_provider)
        
        # Get meter for this service
        self.meter = metrics.get_meter(
            self.config.service_name,
            self.config.service_version
        )
        
        # Create standard metrics
        self._create_standard_metrics()
        
        logger.info(f"✓ Metrics configured: {self.config.service_name}")
    
    def _create_standard_metrics(self) -> None:
        """Create standard metrics for agent operations."""
        if not self.meter:
            return
        
        # Operation duration histogram
        self._metrics["operation_duration"] = self.meter.create_histogram(
            name="agent.operation.duration",
            description="Duration of agent operations in milliseconds",
            unit="ms"
        )
        
        # Operation counter
        self._metrics["operation_count"] = self.meter.create_counter(
            name="agent.operation.count",
            description="Total number of agent operations"
        )
        
        # Error counter
        self._metrics["error_count"] = self.meter.create_counter(
            name="agent.error.count",
            description="Total number of errors"
        )
        
        # Success rate gauge
        self._metrics["success_rate"] = self.meter.create_up_down_counter(
            name="agent.success.rate",
            description="Success rate of operations (0-100)"
        )
    
    @contextmanager
    def trace_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        record_exception: bool = True
    ):
        """
        Context manager for creating traced spans.
        
        Args:
            name: Span name
            attributes: Additional span attributes
            record_exception: Whether to record exceptions
        
        Example:
            >>> with obs.trace_span("validate_vm", {"host": "192.168.1.100"}):
            ...     result = validate_vm(host)
        """
        if not self.tracer or not self.config.enabled:
            yield None
            return
        
        with self.tracer.start_as_current_span(name) as span:
            # Add attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            
            start_time = time.time()
            
            try:
                yield span
                
                # Record success
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                if record_exception:
                    span.record_exception(e)
                
                # Update error metrics
                if "error_count" in self._metrics:
                    self._metrics["error_count"].add(
                        1,
                        {"operation": name, "error_type": type(e).__name__}
                    )
                
                raise
            
            finally:
                # Record duration
                duration_ms = (time.time() - start_time) * 1000
                
                if "operation_duration" in self._metrics:
                    self._metrics["operation_duration"].record(
                        duration_ms,
                        {"operation": name}
                    )
                
                if "operation_count" in self._metrics:
                    self._metrics["operation_count"].add(
                        1,
                        {"operation": name}
                    )
    
    def trace_operation(
        self,
        operation_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Callable:
        """
        Decorator for tracing function/method operations.
        
        Args:
            operation_name: Custom operation name (defaults to function name)
            attributes: Additional span attributes
        
        Example:
            >>> @obs.trace_operation("discover_workload")
            >>> async def discover(resource):
            ...     return await agent.discover(resource)
        """
        def decorator(func: Callable) -> Callable:
            op_name = operation_name or func.__name__
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_span(op_name, attributes):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.trace_span(op_name, attributes):
                    return func(*args, **kwargs)
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a custom metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            attributes: Additional metric attributes
        """
        if not self.meter or not self.config.enabled:
            return
        
        if metric_name not in self._metrics:
            # Create counter for new metrics
            self._metrics[metric_name] = self.meter.create_counter(
                name=f"agent.custom.{metric_name}",
                description=f"Custom metric: {metric_name}"
            )
        
        self._metrics[metric_name].add(value, attributes or {})
    
    def get_trace_context(self) -> Dict[str, str]:
        """
        Get current trace context for propagation.
        
        Returns:
            Dictionary with trace context headers
        """
        if not self.config.enabled:
            return {}
        
        carrier = {}
        TraceContextTextMapPropagator().inject(carrier)
        return carrier
    
    def inject_trace_context(self, carrier: Dict[str, str]) -> None:
        """
        Inject trace context from carrier (for distributed tracing).
        
        Args:
            carrier: Dictionary with trace context headers
        """
        if not self.config.enabled or not carrier:
            return
        
        TraceContextTextMapPropagator().extract(carrier)


# Global observability instance
_global_observability: Optional[BeeAIObservability] = None


def setup_observability(config: ObservabilityConfig) -> BeeAIObservability:
    """
    Setup global observability instance.
    
    Args:
        config: Observability configuration
    
    Returns:
        Configured BeeAIObservability instance
    """
    global _global_observability
    
    _global_observability = BeeAIObservability(config)
    _global_observability.setup()
    
    return _global_observability


def get_observability() -> Optional[BeeAIObservability]:
    """Get global observability instance."""
    return _global_observability


# Convenience decorators using global instance
def trace_operation(
    operation_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Callable:
    """Decorator using global observability instance."""
    obs = get_observability()
    if obs:
        return obs.trace_operation(operation_name, attributes)
    
    # No-op decorator if observability not setup
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None
):
    """Context manager using global observability instance."""
    obs = get_observability()
    if obs:
        with obs.trace_span(name, attributes) as span:
            yield span
    else:
        yield None

# Made with Bob
