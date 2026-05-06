"""
OpenTelemetry instrumentation for BeeAI agents.
Integrates with existing orchestrator without changing architecture.
"""
import os
from typing import Optional
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode


class BeeAITelemetry:
    """
    OpenTelemetry integration for BeeAI framework.
    
    Usage:
        telemetry = BeeAITelemetry(service_name="validation-orchestrator")
        telemetry.initialize()
        
        with telemetry.trace_operation("discovery_phase"):
            # Your agent code here
            pass
    """
    
    def __init__(
        self,
        service_name: str = "beeai-agent",
        otlp_endpoint: Optional[str] = None,
        enabled: bool = True
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://localhost:4318"
        )
        self.enabled = enabled and os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"
        self.tracer: Optional[trace.Tracer] = None
        self.provider: Optional[TracerProvider] = None
        
    def initialize(self):
        """Initialize OpenTelemetry with OTLP exporter."""
        if not self.enabled:
            print("📊 Telemetry disabled")
            return
            
        try:
            # Create resource with service name
            resource = Resource(attributes={
                SERVICE_NAME: self.service_name
            })
            
            # Create tracer provider
            self.provider = TracerProvider(resource=resource)
            
            # Create OTLP exporter (HTTP)
            # HTTP exporter needs the full URL with http:// prefix and /v1/traces path
            endpoint = self.otlp_endpoint
            if not endpoint.endswith('/v1/traces'):
                endpoint = f"{endpoint}/v1/traces"
            print(f"📡 OTLP HTTP Exporter endpoint: {endpoint}")  # DEBUG
            
            try:
                # Enable verbose logging for debugging
                import logging
                logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.DEBUG)
                
                otlp_exporter = OTLPSpanExporter(
                    endpoint=endpoint,
                    timeout=10  # 10 second timeout
                )
                print(f"✅ OTLP HTTP Exporter created successfully")  # DEBUG
                print(f"   Timeout: 10s")  # DEBUG
            except Exception as e:
                print(f"❌ OTLP Exporter creation failed: {e}")  # DEBUG
                import traceback
                traceback.print_exc()
                raise
            
            # Add span processor
            self.provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            
            # Set global tracer provider
            trace.set_tracer_provider(self.provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            print(f"📊 Telemetry initialized: {self.service_name} → {self.otlp_endpoint}")
            
        except Exception as e:
            print(f"⚠️  Telemetry initialization failed: {e}")
            self.enabled = False
    
    def shutdown(self):
        """Shutdown telemetry and flush all pending spans."""
        if self.enabled and self.provider:
            try:
                self.provider.force_flush(timeout_millis=5000)
                self.provider.shutdown()
                print("📊 Telemetry shutdown complete")
            except Exception as e:
                print(f"⚠️  Telemetry shutdown error: {e}")
    
    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        attributes: Optional[dict] = None
    ):
        """
        Context manager for tracing operations.
        
        Args:
            operation_name: Name of the operation (e.g., "discovery_phase")
            attributes: Additional attributes to add to the span
        """
        if not self.enabled or not self.tracer:
            yield None
            return
            
        print(f"🔍 Creating span: {operation_name}")  # DEBUG
        with self.tracer.start_as_current_span(operation_name) as span:
            try:
                print(f"  ✓ Span started: {operation_name}")  # DEBUG
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                
                yield span
                
                # Mark as successful
                span.set_status(Status(StatusCode.OK))
                print(f"  ✓ Span completed: {operation_name}")  # DEBUG
                
            except Exception as e:
                # Record exception
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                # Force flush after each operation to ensure immediate export
                if self.provider:
                    try:
                        print(f"  📤 Flushing spans...")  # DEBUG
                        self.provider.force_flush(timeout_millis=1000)
                        print(f"  ✓ Flush complete")  # DEBUG
                    except Exception as e:
                        print(f"  ⚠️  Flush error: {e}")  # DEBUG
    
    def add_event(self, span, event_name: str, attributes: Optional[dict] = None):
        """Add an event to the current span."""
        if span and self.enabled:
            span.add_event(event_name, attributes=attributes or {})
    
    def set_attribute(self, span, key: str, value):
        """Set an attribute on the current span."""
        if span and self.enabled:
            span.set_attribute(key, str(value))


# Global telemetry instance
_telemetry: Optional[BeeAITelemetry] = None


def get_telemetry() -> BeeAITelemetry:
    """Get or create global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = BeeAITelemetry()
        _telemetry.initialize()
    return _telemetry


def trace_agent_operation(operation_name: str):
    """
    Decorator for tracing agent operations.
    
    Usage:
        @trace_agent_operation("discovery_phase")
        async def run_discovery(self, resource):
            # Your code here
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            with telemetry.trace_operation(operation_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

# Made with Bob


# ============================================================================
# Standalone Functions for CLI Compatibility
# ============================================================================

def initialize_telemetry(
    service_name: str = "validation-service",
    phoenix_endpoint: Optional[str] = None,
    enable_console_export: bool = False
) -> bool:
    """
    Initialize global telemetry instance.
    
    Args:
        service_name: Name of the service
        phoenix_endpoint: Phoenix OTLP endpoint URL
        enable_console_export: Whether to enable console export (not used with Phoenix)
    
    Returns:
        True if initialization succeeded, False otherwise
    """
    global _telemetry
    try:
        _telemetry = BeeAITelemetry(
            service_name=service_name,
            otlp_endpoint=phoenix_endpoint,
            enabled=True
        )
        _telemetry.initialize()
        return _telemetry.enabled
    except Exception as e:
        print(f"⚠️  Telemetry initialization failed: {e}")
        return False


def shutdown_telemetry(timeout: int = 5):
    """Shutdown global telemetry instance."""
    global _telemetry
    if _telemetry:
        _telemetry.shutdown()


def flush_telemetry(timeout: int = 5):
    """Flush pending telemetry spans."""
    global _telemetry
    if _telemetry and _telemetry.provider:
        try:
            _telemetry.provider.force_flush(timeout_millis=timeout * 1000)
        except Exception as e:
            print(f"⚠️  Telemetry flush error: {e}")


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled."""
    global _telemetry
    return _telemetry is not None and _telemetry.enabled


def trace_operation(
    operation_name: str,
    attributes: Optional[dict] = None,
    span_kind: Optional[str] = None,
    input_data: Optional[dict] = None,
    **kwargs
):
    """
    Context manager for tracing operations (standalone function version).
    
    Args:
        operation_name: Name of the operation
        attributes: Additional attributes
        span_kind: Type of span (INTERNAL, CLIENT, SERVER, etc.) - for compatibility
        input_data: Input data to record - merged into attributes
        **kwargs: Additional keyword arguments (ignored for compatibility)
    
    Returns:
        Context manager for tracing
    """
    global _telemetry
    if _telemetry:
        # Merge input_data into attributes if provided
        merged_attributes = attributes or {}
        if input_data:
            merged_attributes.update({f"input.{k}": v for k, v in input_data.items()})
        if span_kind:
            merged_attributes["span.kind"] = span_kind
        
        return _telemetry.trace_operation(operation_name, merged_attributes)
    else:
        # Return a no-op context manager if telemetry not initialized
        from contextlib import nullcontext
        return nullcontext()
