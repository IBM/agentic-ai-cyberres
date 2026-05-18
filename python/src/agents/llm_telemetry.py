"""
LLM-specific telemetry instrumentation.

Provides utilities for tracing LLM API calls with token metrics.
"""
from typing import Optional, Dict, Any
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


@contextmanager
def trace_llm_call(
    model_name: str,
    prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    """
    Context manager for tracing LLM API calls.
    
    Records LLM-specific attributes including model, prompt, and token usage.
    Use this to wrap any LLM API call to get detailed metrics in Phoenix.
    
    Args:
        model_name: Name of the LLM model (e.g., "granite-13b-chat-v2")
        prompt: The prompt text (will be truncated if too long)
        max_tokens: Maximum tokens requested
        temperature: Temperature parameter
    
    Yields:
        Span object for adding additional attributes
    
    Example:
        with trace_llm_call("granite-13b-chat-v2", prompt=prompt_text) as span:
            response = await llm.generate(prompt)
            
            # Record token usage from response
            if hasattr(response, 'usage'):
                span.set_attribute("llm.prompt_tokens", response.usage.prompt_tokens)
                span.set_attribute("llm.completion_tokens", response.usage.completion_tokens)
                span.set_attribute("llm.total_tokens", response.usage.total_tokens)
            
            # Optionally record response
            span.set_attribute("llm.response", str(response)[:500])
    """
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(f"llm.{model_name}") as span:
        # Set LLM-specific attributes following OpenTelemetry semantic conventions
        span.set_attribute("llm.model", model_name)
        span.set_attribute("llm.system", "watsonx")  # or "ibm-watsonx"
        span.set_attribute("llm.request.type", "completion")
        
        if prompt:
            # Truncate long prompts to avoid excessive span size
            truncated_prompt = prompt[:1000] if len(prompt) > 1000 else prompt
            span.set_attribute("llm.prompt", truncated_prompt)
            span.set_attribute("llm.prompt_length", len(prompt))
        
        if max_tokens:
            span.set_attribute("llm.request.max_tokens", max_tokens)
        
        if temperature is not None:
            span.set_attribute("llm.request.temperature", temperature)
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            span.set_attribute("llm.error", str(e))
            raise


def record_llm_response(
    span,
    response_text: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
):
    """
    Helper function to record LLM response metrics on a span.
    
    Args:
        span: The span object from trace_llm_call context
        response_text: The response text (will be truncated)
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used
    
    Example:
        with trace_llm_call("granite-13b-chat-v2", prompt=prompt) as span:
            response = await llm.generate(prompt)
            record_llm_response(
                span,
                response_text=response.text,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
    """
    if not span:
        return
    
    if response_text:
        # Truncate long responses
        truncated_response = response_text[:1000] if len(response_text) > 1000 else response_text
        span.set_attribute("llm.response", truncated_response)
        span.set_attribute("llm.response_length", len(response_text))
    
    if prompt_tokens is not None:
        span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
    
    if completion_tokens is not None:
        span.set_attribute("llm.usage.completion_tokens", completion_tokens)
    
    if total_tokens is not None:
        span.set_attribute("llm.usage.total_tokens", total_tokens)


# Async version for async LLM calls
from contextlib import asynccontextmanager

@asynccontextmanager
async def trace_llm_call_async(
    model_name: str,
    prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    """
    Async context manager for tracing LLM API calls.
    
    Same as trace_llm_call but for async code.
    
    Example:
        async with trace_llm_call_async("granite-13b-chat-v2", prompt=prompt) as span:
            response = await llm.generate_async(prompt)
            record_llm_response(span, response_text=response.text, ...)
    """
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(f"llm.{model_name}") as span:
        # CRITICAL: Set service name for Phoenix
        from agents.telemetry import get_telemetry
        telemetry = get_telemetry()
        if telemetry:
            span.set_attribute("service.name", telemetry.service_name)
        
        # Set LLM-specific attributes
        span.set_attribute("llm.model", model_name)
        span.set_attribute("llm.system", "watsonx")
        span.set_attribute("llm.request.type", "completion")
        
        if prompt:
            truncated_prompt = prompt[:1000] if len(prompt) > 1000 else prompt
            span.set_attribute("llm.prompt", truncated_prompt)
            span.set_attribute("llm.prompt_length", len(prompt))
        
        if max_tokens:
            span.set_attribute("llm.request.max_tokens", max_tokens)
        
        if temperature is not None:
            span.set_attribute("llm.request.temperature", temperature)
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            span.set_attribute("llm.error", str(e))
            raise

# Made with Bob
