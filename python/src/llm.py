#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
from enum import Enum
from typing import Dict, Any, Optional
from groq import Groq
import ollama
from openai import OpenAI
import google.auth
from google.cloud import aiplatform

class Providers(Enum):
    WATSONX = "watsonx"
    OLLAMA = "ollama"
    OPENAI = "openai"
    GROQ = "groq"
    AZURE = "azure"
    VERTEXAI = "vertexai"

class ChatLLM:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("provider")
        self.client = config.get("client")
        self.model_id = config.get("model_id")
    
    async def generate(self, prompt: str) -> str:
        if self.provider == Providers.GROQ:
            return await self._generate_groq(prompt)
        elif self.provider == Providers.OPENAI:
            return await self._generate_openai(prompt)
        elif self.provider == Providers.OLLAMA:
            return await self._generate_ollama(prompt)
        elif self.provider == Providers.VERTEXAI:
            return await self._generate_vertexai(prompt)
        else:
            raise ValueError(f"Provider {self.provider} not implemented")
    
    async def _generate_groq(self, prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    
    async def _generate_openai(self, prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    
    async def _generate_ollama(self, prompt: str) -> str:
        response = self.client.chat(model=self.model_id, messages=[
            {"role": "user", "content": prompt}
        ])
        return response['message']['content']
    
    async def _generate_vertexai(self, prompt: str) -> str:
        # Simplified VertexAI implementation
        client = aiplatform.gapic.PredictionServiceClient()
        # Actual implementation would depend on VertexAI setup
        return f"VertexAI response to: {prompt}"

def get_chat_llm(provider: Optional[Providers] = None) -> ChatLLM:
    if not provider:
        provider_str = os.getenv("LLM_BACKEND", Providers.OLLAMA.value)
        provider = Providers(provider_str)
    
    if provider == Providers.GROQ:
        return ChatLLM({
            "provider": provider,
            "model_id": os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
            "client": Groq(api_key=os.getenv("GROQ_API_KEY"))
        })
    elif provider == Providers.OPENAI:
        return ChatLLM({
            "provider": provider,
            "model_id": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "client": OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        })
    elif provider == Providers.OLLAMA:
        return ChatLLM({
            "provider": provider,
            "model_id": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            "client": ollama.Client(host=os.getenv("OLLAMA_HOST"))
        })
    elif provider == Providers.AZURE:
        return ChatLLM({
            "provider": provider,
            "model_id": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "client": OpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                base_url=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
        })
    elif provider == Providers.VERTEXAI:
        credentials, project = google.auth.default()
        return ChatLLM({
            "provider": provider,
            "model_id": os.getenv("VERTEXAI_MODEL", "gemini-1.5-flash-001"),
            "location": os.getenv("VERTEXAI_LOCATION", "us-central1"),
            "project": os.getenv("VERTEXAI_PROJECT", project)
        })
    else:
        raise ValueError(f"Provider '{provider}' not supported")