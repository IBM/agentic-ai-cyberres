#!/usr/bin/env python3
"""
BeeAI Telemetry Module
Centralized OpenTelemetry configuration and instrumentation

Versions verified:
- openinference-instrumentation-beeai: 0.1.15
- beeai-framework: 0.1.77
- opentelemetry-api: 1.39.1
- opentelemetry-sdk: 1.39.1
"""

import os
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Global telemetry state
_telemetry_initialized = False
_tracer_provider = None
_tracer = None


def initialize_telemetry(
    service_name: str = "beeai-validation",
    phoenix_endpoint: str = "http://localhost:6006",
    enable_console_export: bool = False,
) -> bool:
    """
    Initialize OpenTelemetry with Phoenix using native Phoenix SDK.
    
    Args:
        service_name: Service name for traces
        phoenix_endpoint: Phoenix UI endpoint (default: http://localhost:6006)
        enable_console_export: Also export to console for debugging
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _telemetry_initialized, _tracer_provider, _tracer
    
    if _telemetry_initialized:
        logger.warning("Telemetry already initialized")
        return True
    
    try:
        # Use Phoenix's native OpenTelemetry integration
        from phoenix.otel import register
        from openinference.instrumentation.beeai import BeeAIInstrumentor
        from opentelemetry import trace
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
        
        # Register with Phoenix
        # phoenix_endpoint should already include /v1/traces path
        _tracer_provider = register(
            project_name=service_name,
            endpoint=phoenix_endpoint,
        )
        
        # Add console exporter for debugging (optional)
        if enable_console_export:
            console_exporter = ConsoleSpanExporter()
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
        
        # Get tracer for manual instrumentation
        _tracer = trace.get_tracer(__name__)
        
        # Instrument BeeAI framework (automatic)
        BeeAIInstrumentor().instrument()
        
        _telemetry_initialized = True
        
        logger.info(
            f"✓ Phoenix telemetry initialized successfully → {phoenix_endpoint}",
            extra={
                "phoenix_endpoint": phoenix_endpoint,
                "service_name": service_name,
                "agent": "Telemetry",
            },
        )
        
        return True
        
    except ImportError as e:
        logger.error(
            f"✗ Telemetry initialization failed - missing dependencies: {e}",
            extra={"agent": "Telemetry"},
        )
        logger.error("  Install with: uv pip install arize-phoenix", extra={"agent": "Telemetry"})
        return False
    except Exception as e:
        logger.error(
            f"✗ Telemetry initialization failed: {e}",
            extra={"agent": "Telemetry"},
            exc_info=True,
        )
        return False


def flush_telemetry(timeout: int = 30) -> bool:
    """
    Force flush all pending traces to Phoenix.
    Call this after validation runs to ensure traces are sent.
    
    Args:
        timeout: Maximum seconds to wait for flush
        
    Returns:
        True if flush successful, False otherwise
    """
    global _tracer_provider
    
    if not _telemetry_initialized or _tracer_provider is None:
        logger.warning("Telemetry not initialized, cannot flush")
        return False
    
    try:
        logger.debug("Flushing traces to Phoenix...", extra={"agent": "Telemetry"})
        result = _tracer_provider.force_flush(timeout_millis=timeout * 1000)
        
        if result:
            logger.info(
                f"✓ Traces flushed successfully (timeout={timeout}s)",
                extra={"agent": "Telemetry"},
            )
        else:
            logger.warning(
                f"⚠ Trace flush timed out after {timeout}s",
                extra={"agent": "Telemetry"},
            )
        
        return result
        
    except Exception as e:
        logger.error(
            f"✗ Trace flush failed: {e}",
            extra={"agent": "Telemetry"},
            exc_info=True,
        )
        return False


def shutdown_telemetry(timeout: int = 30) -> bool:
    """
    Shutdown telemetry and flush remaining traces.
    Call this before application exit.
    
    Args:
        timeout: Maximum seconds to wait for shutdown
        
    Returns:
        True if shutdown successful, False otherwise
    """
    global _telemetry_initialized, _tracer_provider
    
    if not _telemetry_initialized or _tracer_provider is None:
        return True
    
    try:
        logger.info("Shutting down telemetry...", extra={"agent": "Telemetry"})
        result = _tracer_provider.shutdown()
        _telemetry_initialized = False
        _tracer_provider = None
        
        logger.info("✓ Telemetry shutdown complete", extra={"agent": "Telemetry"})
        return result
        
    except Exception as e:
        logger.error(
            f"✗ Telemetry shutdown failed: {e}",
            extra={"agent": "Telemetry"},
            exc_info=True,
        )
        return False


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[dict] = None,
):
    """
    Context manager for manual span creation.
    Use this to wrap operations that need explicit tracing.
    
    Usage:
        with trace_operation("validation_workflow", {"resource": "vm-01"}):
            # Your code here
            pass
    
    Args:
        operation_name: Name of the operation/span
        attributes: Optional attributes to add to span
    """
    global _tracer
    
    if not _telemetry_initialized or _tracer is None:
        # Telemetry not initialized, just execute without tracing
        yield None
        return
    
    from opentelemetry.trace import Status, StatusCode
    
    with _tracer.start_as_current_span(operation_name) as span:
        try:
            # Add attributes if provided
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            # Execute wrapped code
            yield span
            
            # Mark as successful
            span.set_status(Status(StatusCode.OK))
            
        except Exception as e:
            # Record exception and mark as error
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def get_tracer():
    """Get the global tracer for manual instrumentation."""
    return _tracer


def is_telemetry_enabled() -> bool:
    """Check if telemetry is initialized and enabled."""
    return _telemetry_initialized

# Made with Bob
