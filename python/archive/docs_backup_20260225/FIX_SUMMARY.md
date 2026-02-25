# Agentic Workflow Review & Ollama Configuration Fix

## Executive Summary

This document summarizes the review of the agentic workflow in `python/src` and the immediate fix applied to enable local LLM usage with Ollama.

## Problem Identified

The user encountered a 401 error when running the agent:
```
HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 401 Unauthorized"
Error: Incorrect API key provided
```

**Root Cause**: The agent was hardcoded to use OpenAI's API, requiring an API key and incurring costs.

**User Requirement**: Use local LLMs running in Ollama with configurable backend selection.

## Solution Implemented

### 1. Environment Configuration (`.env`)
Changed default LLM backend from OpenAI to Ollama:

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

### 2. Code Changes (`conversation.py`)

Added dynamic LLM backend configuration:

```python
def get_llm_model_from_env() -> str:
    """Get LLM model configuration from environment variables.
    
    Supports: ollama, openai, groq, azure, vertexai
    """
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    
    if backend == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return f"ollama:{model}"
    elif backend == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return f"openai:{model}"
    # ... other backends
```

Updated `ConversationHandler` to use environment configuration:

```python
class ConversationHandler:
    def __init__(self, llm_model: Optional[str] = None):
        """Initialize with env-based LLM selection."""
        self.llm_model = llm_model or get_llm_model_from_env()
        logger.info(f"Using LLM model: {self.llm_model}")
```

## Benefits

1. **No API Costs**: Ollama runs locally, eliminating API fees
2. **Privacy**: All data stays on local machine
3. **Offline Capability**: Works without internet connection
4. **Flexibility**: Easy switching between backends via `.env`
5. **Configurable**: Supports 5 different LLM backends

## Agentic Workflow Best Practices Review

### Current Architecture Analysis

The `python/src` folder implements an agentic workflow with:

1. **Conversation Handler** (`conversation.py`)
   - Gathers user input for resource validation
   - Uses LLM to parse natural language
   - Extracts structured information

2. **Recovery Validation Agent** (`recovery_validation_agent.py`)
   - Orchestrates validation workflow
   - Connects to MCP server for tools
   - Manages validation lifecycle

3. **MCP Integration** (`mcp_stdio_client.py`, `mcp_client_compat.py`)
   - Stdio-based MCP client
   - Dynamic tool discovery
   - Tool execution and coordination

4. **Specialized Agents** (`agents/`)
   - Discovery Agent: Finds applications/services
   - Classification Agent: Categorizes resources
   - Validation Agent: Validates configurations
   - Evaluation Agent: Assesses results
   - Reporting Agent: Generates reports

### MCP Best Practices Alignment

#### ✅ What's Working Well

1. **Dynamic Tool Discovery**: `mcp_stdio_client.py` implements:
   - `discover_tools()` - Lists available MCP tools
   - `get_available_tools()` - Returns tool names
   - `has_tool(tool_name)` - Checks tool existence
   - `get_tool_description()` - Gets tool docs

2. **Modular Agent Architecture**: Separate agents for different concerns

3. **State Management**: Workflow persistence and resume capability

4. **Feature Flags**: 19 flags for gradual rollout control

5. **Tool Coordination**: Retry logic, caching, parallel execution

#### 🔄 Areas for Improvement

Based on MCP best practices for infrastructure validation:

### 1. Simplify User Input (Week 3 Priority)

**Current**: Agent asks for resource type, host, credentials, service names, etc.

**Best Practice**: Only ask for hostname + SSH credentials, then auto-discover everything.

**Recommendation**:
```python
# Simplified conversation flow
async def get_minimal_input(self) -> Dict[str, str]:
    """Only ask for essentials."""
    return {
        "hostname": await self.ask("What is the hostname/IP?"),
        "ssh_user": await self.ask("SSH username?"),
        "ssh_password": await self.ask("SSH password (or press Enter for key)?")
    }
```

Then use MCP tools to discover:
- Operating system
- Running applications (Oracle, MongoDB, etc.)
- Services and ports
- Configuration files

### 2. MCP-Centric Discovery (Week 3 Priority)

**Current**: Some hardcoded validation logic

**Best Practice**: Use MCP tools for all discovery

**Recommendation**:
```python
async def discover_resources(self, hostname: str, ssh_creds: dict):
    """Use MCP tools to discover everything."""
    
    # 1. Discover available MCP tools
    tools = await self.mcp_client.get_available_tools()
    
    # 2. Use discovery tools
    if "discover_applications" in tools:
        apps = await self.mcp_client.call_tool(
            "discover_applications",
            {"hostname": hostname, **ssh_creds}
        )
    
    # 3. Select validation tools based on what was found
    validation_tools = self.select_validation_tools(apps, tools)
    
    # 4. Run validations
    results = await self.run_validations(validation_tools)
```

### 3. Intelligent Tool Selection (Week 3 Priority)

**Current**: Predefined validation workflows

**Best Practice**: Dynamically select tools based on discovery

**Recommendation**:
```python
def select_validation_tools(
    self, 
    discovered_apps: List[str],
    available_tools: List[str]
) -> List[str]:
    """Select validation tools based on what was discovered."""
    
    validation_map = {
        "oracle": ["validate_oracle_db", "check_oracle_listener"],
        "mongodb": ["validate_mongodb", "check_mongo_replication"],
        "nginx": ["validate_nginx_config", "check_nginx_status"],
        # ... etc
    }
    
    selected = []
    for app in discovered_apps:
        if app.lower() in validation_map:
            for tool in validation_map[app.lower()]:
                if tool in available_tools:
                    selected.append(tool)
    
    return selected
```

### 4. Enhanced Error Handling

**Current**: Basic error handling

**Best Practice**: Graceful degradation with fallbacks

**Recommendation**:
```python
async def validate_with_fallback(self, tool_name: str, params: dict):
    """Try validation with fallback strategies."""
    
    try:
        return await self.mcp_client.call_tool(tool_name, params)
    except ToolNotFoundError:
        logger.warning(f"Tool {tool_name} not available, trying alternative")
        return await self.try_alternative_validation(tool_name, params)
    except ToolExecutionError as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"status": "error", "message": str(e)}
```

## Implementation Roadmap

### ✅ Completed (Phase 4 Week 1)
- Fixed import errors
- Created compatibility wrapper
- Added Ollama configuration support
- Documented changes

### 🔄 In Progress (Phase 4 Week 2) - Next 3 Hours
- Remove compatibility wrapper
- Refactor to use `MCPStdioClient` directly
- Add proper connection management
- Use dynamic tool discovery throughout

### 📋 Planned (Phase 4 Week 3) - 4 Hours
- Simplify conversation to only ask hostname + SSH
- Update orchestrator to use `get_available_tools()`
- Add intelligent tool selection
- Implement full MCP-centric workflow

### 📋 Planned (Phase 4 Week 4) - 2 Hours
- Create integration tests
- Test end-to-end workflow
- Final documentation
- Demo guide

## How to Test Now

### 1. Ensure Ollama is Running
```bash
# Check Ollama
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# Pull model if needed
ollama pull llama3.2
```

### 2. Start MCP Server
```bash
cd python/cyberres-mcp
uv run mcp dev src/cyberres_mcp/server.py
```

### 3. Run Agent
```bash
cd python/src
python main.py
```

### Expected Behavior
- Agent starts without OpenAI API errors
- Uses local Ollama for conversation
- Connects to MCP server via stdio
- Discovers 15+ available tools
- Can validate resources using existing workflow

## Key Takeaways

1. **Ollama Configuration**: Agent now supports local LLMs via environment variables
2. **MCP Best Practices**: Dynamic tool discovery is implemented and working
3. **Next Steps**: Simplify user input and enhance MCP-centric discovery
4. **Timeline**: 3 more weeks to complete full MCP best practices implementation

## References

- `OLLAMA_CONFIGURATION_FIX.md` - Detailed Ollama setup guide
- `WEEK1_SUMMARY.md` - Phase 4 Week 1 implementation details
- `PHASE4_IMPLEMENTATION_PLAN.md` - Complete 4-week roadmap
- `PHASE3_MCP_BEST_PRACTICES.md` - MCP best practices documentation
- `CORRECT_MCP_WORKFLOW.md` - Correct MCP workflow patterns

## Support

For issues or questions:
1. Check `TROUBLESHOOTING.md`
2. Review `OLLAMA_CONFIGURATION_FIX.md` for Ollama-specific issues
3. See `TEST_QUICK_START.md` for testing guidance