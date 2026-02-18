#
# Copyright contributors to the agentic-ai-cyberres project
#
"""LLM factory supporting multiple providers.

This module provides a factory pattern for creating LLM instances
supporting WatsonX, OpenAI, Ollama, Groq, Azure, and VertexAI providers.
"""

import os
from enum import Enum
from typing import Optional, Any, Dict
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_google_vertexai import ChatVertexAI
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult
from pydantic import BaseModel


class Providers(Enum):
    """Supported LLM providers."""
    WATSONX = "watsonx"
    OLLAMA = "ollama"
    OPENAI = "openai"
    GROQ = "groq"
    AZURE = "azure"
    VERTEXAI = "vertexai"


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def _get_watsonx_llm() -> BaseChatModel:
    """Create WatsonX LLM instance."""
    try:
        from ibm_watsonx_ai import Credentials
        from langchain_ibm import ChatWatsonx
        
        model_id = _get_env("WATSONX_MODEL", "meta-llama/llama-3-1-70b-instruct")
        api_key = _get_env("WATSONX_API_KEY")
        project_id = _get_env("WATSONX_PROJECT_ID")
        region = _get_env("WATSONX_REGION", "us-south")
        
        credentials = Credentials(
            api_key=api_key,
            url=f"https://{region}.watsonx.ai"
        )
        
        return ChatWatsonx(
            model_id=model_id,
            credentials=credentials,
            project_id=project_id,
            params={"temperature": 0, "max_tokens": 2048}
        )
    except ImportError:
        raise ImportError("ibm_watsonx_ai package is required for WatsonX. Install with: pip install ibm-watsonx-ai")


def _get_openai_llm() -> BaseChatModel:
    """Create OpenAI LLM instance."""
    model_id = _get_env("OPENAI_MODEL", "gpt-4o")
    return ChatOpenAI(
        model=model_id,
        temperature=0,
        max_tokens=2048,
        api_key=_get_env("OPENAI_API_KEY")
    )


def _get_groq_llm() -> BaseChatModel:
    """Create Groq LLM instance."""
    model_id = _get_env("GROQ_MODEL", "llama-3.1-70b-versatile")
    return ChatGroq(
        model=model_id,
        temperature=0,
        max_tokens=2048,
        api_key=_get_env("GROQ_API_KEY")
    )


def _get_ollama_llm() -> BaseChatModel:
    """Create Ollama LLM instance."""
    model_id = _get_env("OLLAMA_MODEL", "llama3.1:8b")
    host = _get_env("OLLAMA_HOST", "http://localhost:11434")
    return ChatOllama(
        model=model_id,
        temperature=0,
        base_url=host
    )


def _get_azure_llm() -> BaseChatModel:
    """Create Azure OpenAI LLM instance."""
    model_id = _get_env("OPENAI_MODEL", "gpt-4o-mini")
    api_key = _get_env("AZURE_OPENAI_API_KEY")
    api_version = _get_env("AZURE_OPENAI_API_VERSION", "2024-02-01")
    azure_endpoint = _get_env("AZURE_OPENAI_ENDPOINT")
    
    return ChatOpenAI(
        model=model_id,
        temperature=0,
        max_tokens=2048,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        azure_deployment=model_id
    )


def _get_vertexai_llm() -> BaseChatModel:
    """Create Google VertexAI LLM instance."""
    model_id = _get_env("VERTEXAI_MODEL", "gemini-1.5-flash-001")
    location = _get_env("VERTEXAI_LOCATION", "us-central1")
    project = _get_env("VERTEXAI_PROJECT")
    
    return ChatVertexAI(
        model_name=model_id,
        location=location,
        project=project,
        temperature=0,
        max_tokens=2048
    )


# Factory mapping
LLM_FACTORIES: Dict[str, callable] = {
    Providers.WATSONX.value: _get_watsonx_llm,
    Providers.OPENAI.value: _get_openai_llm,
    Providers.GROQ.value: _get_groq_llm,
    Providers.OLLAMA.value: _get_ollama_llm,
    Providers.AZURE.value: _get_azure_llm,
    Providers.VERTEXAI.value: _get_vertexai_llm,
}


def get_chat_llm(provider: Optional[str] = None) -> BaseChatModel:
    """Get a chat LLM instance based on the provider.
    
    Args:
        provider: The LLM provider name. If None, uses LLM_BACKEND env var
                  or defaults to "ollama".
    
    Returns:
        A LangChain chat model instance.
    
    Raises:
        ValueError: If the provider is not supported.
    """
    if not provider:
        provider = _get_env("LLM_BACKEND", Providers.OLLAMA.value)
    
    # Normalize provider name
    provider = provider.lower()
    
    # Try to match with enum
    provider_enum = None
    for p in Providers:
        if p.value.lower() == provider:
            provider_enum = p
            break
    
    if not provider_enum:
        # Try direct lookup
        if provider in LLM_FACTORIES:
            return LLM_FACTORIES[provider]()
        raise ValueError(f'Provider "{provider}" not supported. Available: {list(LLM_FACTORIES.keys())}')
    
    factory = LLM_FACTORIES.get(provider_enum.value)
    if not factory:
        raise ValueError(f'Provider "{provider}" not found.')
    
    return factory()


# Convenience function for compatibility
getChatLLM = get_chat_llm

