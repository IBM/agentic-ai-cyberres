"""
BeeAI configuration for CyberRes Recovery Validation agents.
"""

import os
from typing import Optional, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    
    provider: Literal["ollama", "openai", "groq", "anthropic"] = Field(
        default="ollama",
        description="LLM provider to use"
    )
    model: str = Field(
        default="llama3.2:3b",
        description="Model name/identifier"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the provider (if required)"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for the provider API"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation"
    )
    max_tokens: int = Field(
        default=2000,
        gt=0,
        description="Maximum tokens in response"
    )


class MemoryConfig(BaseModel):
    """Memory configuration for agents."""
    
    type: Literal["sliding", "token", "unconstrained", "summarize"] = Field(
        default="sliding",
        description="Type of memory to use"
    )
    max_messages: int = Field(
        default=50,
        gt=0,
        description="Maximum number of messages to retain (for sliding memory)"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens to retain (for token memory)"
    )


class CacheConfig(BaseModel):
    """Caching configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable LLM response caching"
    )
    ttl_seconds: int = Field(
        default=3600,
        gt=0,
        description="Cache time-to-live in seconds"
    )
    max_size: int = Field(
        default=1000,
        gt=0,
        description="Maximum number of cached responses"
    )


class ObservabilityConfig(BaseModel):
    """Observability and tracing configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing"
    )
    service_name: str = Field(
        default="cyberres-validation",
        description="Service name for tracing"
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="OpenTelemetry collector endpoint"
    )


class BeeAIConfig(BaseModel):
    """Complete BeeAI configuration."""
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    # MCP configuration
    mcp_server_path: str = Field(
        default="../cyberres-mcp/src/cyberres_mcp/server.py",
        description="Path to MCP server"
    )
    mcp_mode: Literal["stdio", "http"] = Field(
        default="stdio",
        description="MCP connection mode"
    )
    
    # Workflow configuration
    enable_discovery: bool = Field(
        default=True,
        description="Enable workload discovery phase"
    )
    enable_ai_evaluation: bool = Field(
        default=True,
        description="Enable AI-powered evaluation phase"
    )
    parallel_execution: bool = Field(
        default=True,
        description="Enable parallel validation execution"
    )
    max_parallel_checks: int = Field(
        default=5,
        gt=0,
        description="Maximum number of parallel validation checks"
    )
    
    @classmethod
    def from_env(cls) -> "BeeAIConfig":
        """Create configuration from environment variables."""
        
        # LLM configuration
        llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        llm_model = os.getenv("LLM_MODEL", "llama3.2:3b")
        llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
        llm_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Memory configuration
        memory_type = os.getenv("MEMORY_TYPE", "sliding")
        max_messages = int(os.getenv("MAX_MESSAGES", "50"))
        
        # Cache configuration
        cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
        
        # Observability configuration
        observability_enabled = os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true"
        otel_endpoint = os.getenv("OTEL_ENDPOINT")
        
        # MCP configuration
        mcp_server_path = os.getenv("MCP_SERVER_PATH", "../cyberres-mcp/src/cyberres_mcp/server.py")
        mcp_mode = os.getenv("MCP_MODE", "stdio")
        
        # Workflow configuration
        enable_discovery = os.getenv("ENABLE_DISCOVERY", "true").lower() == "true"
        enable_ai_evaluation = os.getenv("ENABLE_AI_EVALUATION", "true").lower() == "true"
        parallel_execution = os.getenv("PARALLEL_EXECUTION", "true").lower() == "true"
        
        return cls(
            llm=LLMConfig(
                provider=llm_provider,
                model=llm_model,
                api_key=llm_api_key,
                base_url=llm_base_url if llm_provider == "ollama" else None
            ),
            memory=MemoryConfig(
                type=memory_type,
                max_messages=max_messages
            ),
            cache=CacheConfig(
                enabled=cache_enabled,
                ttl_seconds=cache_ttl
            ),
            observability=ObservabilityConfig(
                enabled=observability_enabled,
                endpoint=otel_endpoint
            ),
            mcp_server_path=mcp_server_path,
            mcp_mode=mcp_mode,
            enable_discovery=enable_discovery,
            enable_ai_evaluation=enable_ai_evaluation,
            parallel_execution=parallel_execution
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return self.model_dump()


# Default configuration instance
default_config = BeeAIConfig.from_env()

# Made with Bob
