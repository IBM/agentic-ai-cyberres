# Ollama Configuration Fix

## Problem
The agent was trying to use OpenAI API but failing with 401 error because:
1. `.env` file had `LLM_BACKEND=openai` 
2. `conversation.py` was hardcoded to use `openai:gpt-4o-mini`
3. No environment variable configuration support

## Solution

### 1. Updated `.env` Configuration
Changed from OpenAI to Ollama:

```bash
# Before
LLM_BACKEND=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# After
LLM_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 2. Updated `conversation.py`
Added environment variable support:

```python
def get_llm_model_from_env() -> str:
    """Get LLM model configuration from environment variables."""
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    
    if backend == "ollama":
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return f"ollama:{model}"
    elif backend == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return f"openai:{model}"
    # ... other backends
```

Updated `ConversationHandler.__init__()`:
```python
def __init__(self, llm_model: Optional[str] = None):
    """Initialize conversation handler.
    
    Args:
        llm_model: LLM model to use (if None, reads from env)
    """
    self.llm_model = llm_model or get_llm_model_from_env()
    logger.info(f"ConversationHandler using LLM model: {self.llm_model}")
```

## Supported LLM Backends

The agent now supports multiple LLM backends via environment variables:

### 1. Ollama (Local, Recommended)
```bash
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 2. OpenAI
```bash
LLM_BACKEND=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 3. Groq
```bash
LLM_BACKEND=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-70b-versatile
```

### 4. Azure OpenAI
```bash
LLM_BACKEND=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_MODEL=gpt-4o-mini
```

### 5. Vertex AI
```bash
LLM_BACKEND=vertexai
VERTEXAI_PROJECT=your-gcp-project
VERTEXAI_LOCATION=us-central1
VERTEXAI_MODEL=gemini-1.5-flash-001
```

## How to Test with Ollama

### Prerequisites
1. Install Ollama: https://ollama.ai/download
2. Pull a model:
```bash
ollama pull llama3.2
```

### Start Ollama Server
```bash
# Ollama runs automatically on macOS/Windows
# On Linux, start it:
ollama serve
```

### Verify Ollama is Running
```bash
curl http://localhost:11434/api/tags
```

Should return list of available models.

### Run the Agent
```bash
cd python/src
python main.py
```

The agent will now use Ollama instead of OpenAI!

## Testing Different Models

You can test different Ollama models by changing the `.env` file:

```bash
# Fast, smaller model (recommended for testing)
OLLAMA_MODEL=llama3.2

# Larger, more capable model
OLLAMA_MODEL=llama3.1:8b

# Even larger
OLLAMA_MODEL=llama3.1:70b

# Code-focused model
OLLAMA_MODEL=codellama
```

## Switching Between Backends

Simply change `LLM_BACKEND` in `.env`:

```bash
# Use local Ollama (no API key needed)
LLM_BACKEND=ollama

# Use OpenAI (requires API key)
LLM_BACKEND=openai

# Use Groq (requires API key, fast inference)
LLM_BACKEND=groq
```

No code changes needed!

## Benefits

1. **No API Costs**: Ollama runs locally, no API fees
2. **Privacy**: Data stays on your machine
3. **Offline**: Works without internet
4. **Fast**: Local inference is quick for smaller models
5. **Flexible**: Easy to switch between backends

## Next Steps

After verifying Ollama works:
1. Test the full workflow with a real VM
2. Verify MCP tool discovery works
3. Test validation with discovered applications
4. Generate reports

## Troubleshooting

### Ollama Not Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.2
```

### Connection Refused
Check `OLLAMA_BASE_URL` in `.env` matches where Ollama is running:
```bash
OLLAMA_BASE_URL=http://localhost:11434
```

### Slow Performance
Use a smaller model:
```bash
OLLAMA_MODEL=llama3.2  # Faster
# Instead of
OLLAMA_MODEL=llama3.1:70b  # Slower but more capable