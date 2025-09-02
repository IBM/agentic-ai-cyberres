#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
import re
from enum import Enum
from typing import Dict, Any, Optional, List
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

class SafetyViolationError(Exception):
    """Exception raised for safety violations"""
    pass

class LLMGuardrails:
    @staticmethod
    def validate_prompt(prompt: str) -> None:
        """Validate prompt for safety and appropriateness"""
        # Block potentially harmful commands
        dangerous_patterns = [
            r"rm\s+-rf", r"chmod\s+777", r"passwd", r"adduser", 
            r"useradd", r"usermod", r"chsh", r"visudo", r"dd\s+if=",
            r">\s+/dev/", r"mkfs", r"fdisk", r"shutdown", r"reboot",
            r"halt", r"poweroff", r"init\s+0", r"killall", r"pkill",
            r":(){:|:&};:", r"wget\s+-O-\s*http", r"curl\s+.*\|.*sh"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                raise SafetyViolationError(f"Prompt contains potentially dangerous command: {pattern}")
        
        # Block sensitive data requests
        sensitive_patterns = [
            r"password", r"secret", r"key", r"credential", r"token",
            r"ssh\-", r"private", r"\.pem", r"\.key", r"\.env",
            r"/etc/shadow", r"/etc/passwd", r"\.bash_history"
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                raise SafetyViolationError(f"Prompt requests sensitive information: {pattern}")
    
    @staticmethod
    def validate_response(response: str) -> str:
        """Validate and sanitize LLM response"""
        # Remove any command execution patterns
        response = re.sub(r'```(bash|shell|sh)[\s\S]*?```', '[CODE BLOCK REMOVED]', response)
        
        # Sanitize potential command injections
        sanitized = re.sub(r'`.*?`', '[COMMAND REMOVED]', response)
        sanitized = re.sub(r'\$(\(|{).*?(\)|})', '[VARIABLE REMOVED]', sanitized)
        
        return sanitized

class ChatLLM:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("provider")
        self.client = config.get("client")
        self.model_id = config.get("model_id")
        self.guardrails = LLMGuardrails()
    
    async def generate(self, prompt: str) -> str:
        # Validate prompt safety
        self.guardrails.validate_prompt(prompt)
        
        if self.provider == Providers.GROQ:
            response = await self._generate_groq(prompt)
        elif self.provider == Providers.OPENAI:
            response = await self._generate_openai(prompt)
        elif self.provider == Providers.OLLAMA:
            response = await self._generate_ollama(prompt)
        elif self.provider == Providers.VERTEXAI:
            response = await self._generate_vertexai(prompt)
        else:
            raise ValueError(f"Provider {self.provider} not implemented")
        
        # Validate and sanitize response
        return self.guardrails.validate_response(response)
    
    async def _generate_groq(self, prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=2048
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise SafetyViolationError(f"Groq API error: {str(e)}")
    
    async def _generate_openai(self, prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=2048
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise SafetyViolationError(f"OpenAI API error: {str(e)}")
    
    async def _generate_ollama(self, prompt: str) -> str:
        try:
            response = self.client.chat(model=self.model_id, messages=[
                {"role": "user", "content": prompt}
            ])
            return response['message']['content']
        except Exception as e:
            raise SafetyViolationError(f"Ollama API error: {str(e)}")
    
    async def _generate_vertexai(self, prompt: str) -> str:
        # Simplified VertexAI implementation with error handling
        try:
            # Actual implementation would depend on VertexAI setup
            return f"VertexAI response to: {prompt}"
        except Exception as e:
            raise SafetyViolationError(f"VertexAI API error: {str(e)}")

def get_chat_llm(provider: Optional[Providers] = None) -> ChatLLM:
    if not provider:
        provider_str = os.getenv("LLM_BACKEND", Providers.OLLAMA.value)
        provider = Providers(provider_str)
    
    # Validate environment variables
    required_vars = {
        Providers.GROQ: ["GROQ_API_KEY"],
        Providers.OPENAI: ["OPENAI_API_KEY"],
        Providers.AZURE: ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"],
        Providers.VERTEXAI: ["VERTEXAI_PROJECT"]
    }
    
    if provider in required_vars:
        for var in required_vars[provider]:
            if not os.getenv(var):
                raise SafetyViolationError(f"Missing required environment variable: {var}")
    
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