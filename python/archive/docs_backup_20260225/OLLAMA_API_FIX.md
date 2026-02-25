# Ollama API Endpoint Fix

## Problem
PydanticAI is trying to use Ollama's OpenAI-compatible API but getting 404 errors:
```
HTTP Request: POST http://localhost:11434/chat/completions "HTTP/1.1 404 Not Found"
```

## Root Cause
PydanticAI expects Ollama's OpenAI-compatible API at `/v1/chat/completions`, but it's trying `/chat/completions` (missing `/v1` prefix).

## Solutions

### Option 1: Use Ollama's Native API (Recommended)
Instead of using PydanticAI's Ollama integration, use the native `ollama` Python library directly.

### Option 2: Configure OpenAI-Compatible Endpoint
Set the base URL to include `/v1`:
```bash
export OLLAMA_BASE_URL="http://localhost:11434/v1"
```

### Option 3: Use OpenAI Library with Ollama
Configure OpenAI client to point to Ollama:
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama doesn't need a real key
)
```

## Quick Fix for Testing

Update `.env`:
```bash
# Change from:
OLLAMA_BASE_URL=http://localhost:11434

# To:
OLLAMA_BASE_URL=http://localhost:11434/v1
```

## Alternative: Skip LLM for Testing

For immediate testing without LLM, use the simplified conversation handler that doesn't require LLM:

```python
from conversation_simple import SimpleConversationHandler

# This only asks for 3 fields, no LLM needed
handler = SimpleConversationHandler()
inputs = await handler.get_validation_inputs()
```

## Verification

Test Ollama endpoint:
```bash
# Native API (works)
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}'

# OpenAI-compatible API (should work with /v1)
curl http://localhost:11434/v1/chat/completions -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Hello"}]
}'
```

## Recommendation for Production

Use `SimpleConversationHandler` which:
- ✅ No LLM dependency
- ✅ Direct user input (3 fields only)
- ✅ Faster and more reliable
- ✅ No API costs
- ✅ Works offline

The MCP-centric workflow uses `SimpleConversationHandler` by default, so this issue only affects the legacy conversation flow.

---
*Last Updated: 2026-02-24*