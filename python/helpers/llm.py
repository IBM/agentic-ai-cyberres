import os

class ChatLLM:
    def __init__(self, model_id=None, parameters=None):
        self.model_id = model_id
        self.parameters = parameters or {}

class GroqChatLLM(ChatLLM):
    def __init__(self, model_id=None, api_key=None):
        super().__init__(model_id)
        self.api_key = api_key

class OpenAIChatLLM(ChatLLM):
    def __init__(self, model_id=None, temperature=0, max_tokens=2048, azure=False):
        super().__init__(model_id, {"temperature": temperature, "max_tokens": max_tokens})
        self.azure = azure

class OllamaChatLLM(ChatLLM):
    def __init__(self, model_id=None, temperature=0, host=None):
        super().__init__(model_id, {"temperature": temperature})
        self.host = host

class WatsonXChatLLM(ChatLLM):
    @classmethod
    def from_preset(cls, model_id, api_key=None, project_id=None, region=None):
        instance = cls(model_id)
        instance.api_key = api_key
        instance.project_id = project_id
        instance.region = region
        return instance

class VertexAIChatLLM(ChatLLM):
    def __init__(self, model_id=None, location=None, project=None, parameters=None):
        super().__init__(model_id, parameters)
        self.location = location
        self.project = project

Providers = {
    "WATSONX": "watsonx",
    "OLLAMA": "ollama",
    "OPENAI": "openai",
    "GROQ": "groq",
    "AZURE": "azure",
    "VERTEXAI": "vertexai",
}

def get_env(key, default=None):
    return os.getenv(key, default)

def get_chat_llm(provider=None):
    if provider is None:
        provider = get_env("LLM_BACKEND", "ollama").lower()

    if provider == Providers["GROQ"]:
        return GroqChatLLM(
            model_id=get_env("GROQ_MODEL", "llama-3.1-70b-versatile"),
            api_key=get_env("GROQ_API_KEY"),
        )
    elif provider == Providers["OPENAI"]:
        return OpenAIChatLLM(
            model_id=get_env("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            max_tokens=2048,
        )
    elif provider == Providers["OLLAMA"]:
        return OllamaChatLLM(
            model_id=get_env("OLLAMA_MODEL", "llama3.1:8b"),
            temperature=0,
            host=get_env("OLLAMA_HOST"),
        )
    elif provider == Providers["WATSONX"]:
        return WatsonXChatLLM.from_preset(
            get_env("WATSONX_MODEL", "meta-llama/llama-3-1-70b-instruct"),
            api_key=get_env("WATSONX_API_KEY"),
            project_id=get_env("WATSONX_PROJECT_ID"),
            region=get_env("WATSONX_REGION"),
        )
    elif provider == Providers["AZURE"]:
        return OpenAIChatLLM(
            model_id=get_env("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            max_tokens=2048,
            azure=True,
        )
    elif provider == Providers["VERTEXAI"]:
        return VertexAIChatLLM(
            model_id=get_env("VERTEXAI_MODEL", "gemini-1.5-flash-001"),
            location=get_env("VERTEXAI_LOCATION", "us-central1"),
            project=get_env("VERTEXAI_PROJECT"),
            parameters={},
        )
    else:
        raise ValueError(f"Provider '{provider}' not found.")
