#
# Copyright contributors to the agentic-ai-cyberres project
#
from typing import List, Dict, Any, Optional
from llm import ChatLLM, SafetyViolationError

class OperationalGuardrails:
    @staticmethod
    def validate_tool_usage(tool_name: str, input_data: Dict[str, Any]) -> None:
        """Validate tool usage parameters"""
        tool_limits = {
            "FindRunningProcesses": {"min": (0, 1000)},
            "FindWhatsRunningByPorts": {"min": (0, 65535), "max": (1, 65535)},
            "MongoDBDataValidator": {"argument": {"max_length": 50}},
            "SendEmail": {"argument": {"max_length": 10000}}
        }
        
        if tool_name in tool_limits:
            for param, limits in tool_limits[tool_name].items():
                if param in input_data:
                    value = input_data[param]
                    if isinstance(value, (int, float)):
                        min_val, max_val = limits
                        if not min_val <= value <= max_val:
                            raise SafetyViolationError(f"Parameter {param} out of bounds: {value}")
                    elif isinstance(value, str):
                        max_len = limits["max_length"]
                        if len(value) > max_len:
                            raise SafetyViolationError(f"Parameter {param} too long: {len(value)} > {max_len}")

class TokenMemory:
    def __init__(self, llm: ChatLLM, max_messages: int = 100):
        self.llm = llm
        self.memory = []
        self.max_messages = max_messages
        self.max_tokens = 4000
    
    def add_message(self, role: str, content: str):
        """Add message with length validation"""
        if len(content) > 10000:
            raise SafetyViolationError("Message too long (max 10,000 characters)")
        
        self.memory.append({"role": role, "content": content})
        
        # Enforce memory limits
        if len(self.memory) > self.max_messages:
            self.memory = self.memory[-self.max_messages:]
    
    def get_context(self) -> List[Dict[str, str]]:
        return self.memory[-10:]

class BeeAgent:
    def __init__(self, llm: ChatLLM, memory: TokenMemory, tools: List[Any]):
        self.llm = llm
        self.memory = memory
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = 10
        self.max_retries_per_step = 3
        self.total_max_retries = 10
        self.guardrails = OperationalGuardrails()
        self.execution_count = 0
        self.max_executions_per_session = 50
    
    async def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # Rate limiting
        self.execution_count += 1
        if self.execution_count > self.max_executions_per_session:
            raise SafetyViolationError("Maximum executions per session exceeded")
        
        execution_config = kwargs.get('execution', {})
        self.max_iterations = execution_config.get("maxIterations", self.max_iterations)
        self.max_retries_per_step = execution_config.get("maxRetriesPerStep", self.max_retries_per_step)
        self.total_max_retries = execution_config.get("totalMaxRetries", self.total_max_retries)
        
        prompt = input_data["prompt"]
        
        # Input validation
        if len(prompt) > 5000:
            raise SafetyViolationError("Prompt too long (max 5000 characters)")
        
        self.memory.add_message("user", prompt)
        
        try:
            response_text = await self.llm.generate(prompt)
            self.memory.add_message("assistant", response_text)
            
            return {
                "result": {
                    "text": response_text,
                    "tools_used": [],
                    "iterations": 1
                }
            }
        except SafetyViolationError as e:
            self.memory.add_message("system", f"Security violation: {str(e)}")
            raise
        except Exception as e:
            self.memory.add_message("system", f"Execution error: {str(e)}")
            raise
    
    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        # Validate tool usage
        self.guardrails.validate_tool_usage(tool_name, tool_input)
        
        if tool_name not in self.tools:
            return f"Error: Tool {tool_name} not found"
        
        tool = self.tools[tool_name]
        
        for retry in range(self.max_retries_per_step):
            try:
                result = await tool.execute(tool_input)
                return result
            except SafetyViolationError as e:
                return f"Security violation: {str(e)}"
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