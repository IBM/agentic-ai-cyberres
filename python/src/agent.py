#
# Copyright contributors to the agentic-ai-cyberres project
#
from typing import List, Dict, Any, Optional
from llm import ChatLLM

class TokenMemory:
    def __init__(self, llm: ChatLLM):
        self.llm = llm
        self.memory = []
        self.max_tokens = 4000
    
    def add_message(self, role: str, content: str):
        self.memory.append({"role": role, "content": content})
    
    def get_context(self) -> List[Dict[str, str]]:
        return self.memory[-10:]  # Return last 10 messages for context

class BeeAgent:
    def __init__(self, llm: ChatLLM, memory: TokenMemory, tools: List[Any]):
        self.llm = llm
        self.memory = memory
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = 10
        self.max_retries_per_step = 3
        self.total_max_retries = 10
    
    async def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # Extract execution config from kwargs
        execution_config = kwargs.get('execution', {})
        self.max_iterations = execution_config.get("maxIterations", self.max_iterations)
        self.max_retries_per_step = execution_config.get("maxRetriesPerStep", self.max_retries_per_step)
        self.total_max_retries = execution_config.get("totalMaxRetries", self.total_max_retries)
        
        prompt = input_data["prompt"]
        self.memory.add_message("user", prompt)
        
        context = self.memory.get_context()
        
        # Simple implementation - in a real agent, this would involve tool usage and reasoning
        response_text = await self.llm.generate(prompt)
        
        self.memory.add_message("assistant", response_text)
        
        return {
            "result": {
                "text": response_text,
                "tools_used": [],
                "iterations": 1
            }
        }
    
    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        if tool_name not in self.tools:
            return f"Error: Tool {tool_name} not found"
        
        tool = self.tools[tool_name]
        
        for retry in range(self.max_retries_per_step):
            try:
                result = await tool.execute(tool_input)
                return result
            except Exception as e:
                if retry == self.max_retries_per_step - 1:
                    return f"Error executing tool {tool_name}: {str(e)}"
                continue
        
        return f"Failed to execute tool {tool_name} after {self.max_retries_per_step} retries"

# Add DynamicTool class definition here since it's used by the tools
class DynamicTool:
    def __init__(self, name: str, description: str, handler):
        self.name = name
        self.description = description
        self.handler = handler
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        return await self.handler(input_data)

class StringToolOutput:
    def __init__(self, output: str):
        self.output = output