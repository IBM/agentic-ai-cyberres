#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Main agent implementation with tools and interactive console.

This module provides the main agent functionality similar to the TypeScript
implementation, integrating with LangChain agents and various tools.
"""

import os
import sys
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import helpers - using absolute imports from the package
try:
    from .helpers import llm
    from .helpers import reader
    from .helpers import data_validator_tools
except ImportError:
    # Fallback for direct execution
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from helpers import llm
    from helpers import reader
    from helpers import data_validator_tools

# LangChain imports - using langchain-core and langchain-community
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, SystemMessage


class Agent:
    """Main agent class that orchestrates tools and LLM.
    
    This agent provides functionality similar to the BeeAgent in the
    TypeScript implementation, with support for multiple tools and
    interactive console input.
    """
    
    def __init__(
        self,
        llm_instance: Optional[Any] = None,
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 8,
        max_retries_per_step: int = 3,
        total_max_retries: int = 10
    ):
        """Initialize the agent.
        
        Args:
            llm_instance: The language model to use. If None, will be created from env.
            tools: List of tools available to the agent.
            max_iterations: Maximum number of iterations per execution.
            max_retries_per_step: Maximum retries per step.
            total_max_retries: Maximum total retries.
        """
        self.llm = llm_instance
        self.tools = tools or []
        self.max_iterations = max_iterations
        self.max_retries_per_step = max_retries_per_step
        self.total_max_retries = total_max_retries
        
        # Initialize LLM if not provided
        if self.llm is None:
            provider = os.getenv("LLM_BACKEND")
            self.llm = llm.get_chat_llm(provider)
    
    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the agent.
        
        Args:
            tool: The tool to add.
        """
        self.tools.append(tool)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name.
        
        Args:
            name: The name of the tool.
        
        Returns:
            The tool if found, None otherwise.
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def _build_system_message(self) -> str:
        """Build the system message with available tools."""
        tools_description = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in self.tools
        ])
        
        return f"""You are a helpful agent with access to the following tools:

{tools_description}

When you need to use a tool, respond with the tool name and arguments in the format:
TOOL: <tool_name>
ARGUMENTS: <json_arguments>

Otherwise, provide your response directly."""
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return its result.
        
        Args:
            tool_name: The name of the tool to execute.
            tool_input: The input arguments for the tool.
        
        Returns:
            The result of the tool execution.
        """
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    return tool.invoke(tool_input)
                except Exception as e:
                    return f"Error executing tool: {str(e)}"
        return f"Tool '{tool_name}' not found"
    
    def _parse_llm_response(self, response: str) -> Optional[tuple[str, Dict]]:
        """Parse the LLM response to extract tool calls.
        
        Args:
            response: The LLM response text.
        
        Returns:
            Tuple of (tool_name, tool_input) or None if no tool call.
        """
        import re
        import json
        
        # Look for TOOL: and ARGUMENTS: patterns
        tool_match = re.search(r'TOOL:\s*(\w+)', response)
        args_match = re.search(r'ARGUMENTS:\s*(\{.*\})', response, re.DOTALL)
        
        if tool_match and args_match:
            tool_name = tool_match.group(1)
            try:
                tool_input = json.loads(args_match.group(1))
                return tool_name, tool_input
            except json.JSONDecodeError:
                pass
        return None
    
    async def run(self, prompt: str, execution: Optional[Dict[str, Any]] = None, console_reader=None) -> Dict[str, Any]:
        """Run the agent with a prompt.
        
        Args:
            prompt: The user's prompt.
            execution: Optional execution parameters.
            console_reader: Optional console reader for callbacks.
        
        Returns:
            Dictionary with the result.
        """
        max_iterations = (execution.get("maxIterations") if execution else None) or self.max_iterations
        max_retries = (execution.get("totalMaxRetries") if execution else None) or self.total_max_retries
        
        system_message = self._build_system_message()
        
        # Build messages for the LLM
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=prompt)
        ]
        
        iteration = 0
        final_response = ""
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call the LLM
            try:
                response = await self.llm.agenerate([messages])
                response_text = response.generations[0][0].text
                
                # Log the response if console_reader is provided
                if console_reader:
                    console_reader.write(f"Agent 🤖 (iteration {iteration})", response_text[:200])
                
                # Check if the response contains a tool call
                tool_call = self._parse_llm_response(response_text)
                
                if tool_call:
                    tool_name, tool_input = tool_call
                    
                    # Log tool execution if console_reader
                    if console_reader:
                        console_reader.write(f"Tool 🤖 ({tool_name})", str(tool_input))
                    
                    # Execute the tool
                    tool_result = self._execute_tool(tool_name, tool_input)
                    
                    # Add tool result to messages
                    messages.append(HumanMessage(content=f"Tool result: {tool_result}"))
                    
                    # Add assistant message
                    messages.append(HumanMessage(content=response_text))
                else:
                    # No tool call, this is the final response
                    final_response = response_text
                    break
                    
            except Exception as e:
                if console_reader:
                    console_reader.write("Error", str(e))
                final_response = f"Error: {str(e)}"
                break
        
        return {
            "result": {
                "text": final_response
            },
            "iterations": iteration
        }
    
    def run_sync(self, prompt: str, execution: Optional[Dict[str, Any]] = None, console_reader=None) -> Dict[str, Any]:
        """Synchronous version of run().
        
        Args:
            prompt: The user's prompt.
            execution: Optional execution parameters.
            console_reader: Optional console reader for callbacks.
        
        Returns:
            Dictionary with the result.
        """
        return asyncio.run(self.run(prompt, execution, console_reader))
    
    def run_interactive(self, fallback_prompt: Optional[str] = None) -> None:
        """Run the agent in interactive console mode.
        
        Args:
            fallback_prompt: Default prompt to use when user enters empty input.
        """
        console = reader.create_console_reader(
            fallback=fallback_prompt or "What are the most common enterprise applications that run on Linux in the industry today? Do not include Linux or Linux distributions in the results. Do not identify what's currently running."
        )
        
        print("Interactive session has started. To escape, input 'q' and submit.")
        
        for console_input in console:
            try:
                # Run the agent
                response = self.run_sync(console_input.prompt, console_reader=console)
                
                # Write response
                console.write("Agent 🤖 :", response.get("result", {}).get("text", ""))
            except Exception as e:
                console.write("Error", str(e))


def _create_tool_wrapper(func):
    """Create a wrapper function for LangChain Tool that handles the input properly."""
    def wrapper(input_str: str) -> str:
        # Parse the input if it's a JSON string, otherwise use as-is
        try:
            import json
            # Try to parse as JSON
            if input_str.strip().startswith('{'):
                params = json.loads(input_str)
                return func.invoke(params)
        except (json.JSONDecodeError, Exception):
            pass
        # If not JSON, just pass as argument
        return func.invoke({"argument": input_str})
    return wrapper


def create_agent(
    provider: Optional[str] = None,
    max_iterations: int = 8,
    max_retries_per_step: int = 3,
    total_max_retries: int = 10
) -> Agent:
    """Create an agent with default tools.
    
    Args:
        provider: The LLM provider to use.
        max_iterations: Maximum iterations per execution.
        max_retries_per_step: Maximum retries per step.
        total_max_retries: Maximum total retries.
    
    Returns:
        Configured Agent instance.
    """
    # Get LLM
    chat_llm = llm.get_chat_llm(provider)
    
    # Create LangChain tools from the data validator functions
    tools = [
        Tool(
            name="find_running_processes",
            description="Find running processes on the system. Determines what applications are running on the system by looking at running processes. Disregard processes that are used by typical Linux system processes.",
            func=_create_tool_wrapper(data_validator_tools.find_running_processes)
        ),
        Tool(
            name="find_whats_running_by_ports",
            description="Find applications running on listening ports. Determines what applications are running on the system by looking at open listening ports. Disregard ports that are used by typical Linux system processes.",
            func=_create_tool_wrapper(data_validator_tools.find_whats_running_by_ports)
        ),
        Tool(
            name="validate_mongodb",
            description="Validate a MongoDB database. This tool validates a mongod database to ensure the database is not corrupted. Do not use this tool to validate anything that is not mongod. It can only be used if mongod is currently running.",
            func=_create_tool_wrapper(data_validator_tools.validate_mongodb)
        ),
        Tool(
            name="validate_postgresql",
            description="Validate a PostgreSQL database. This tool validates a PostgreSQL database to ensure the database is not corrupted. It can validate a single table or all tables in the database depending on configuration. Do not use this tool to validate anything that is not postgres. It can only be used if postgres is currently running.",
            func=_create_tool_wrapper(data_validator_tools.validate_postgresql)
        ),
        Tool(
            name="send_email",
            description="Send an email.",
            func=_create_tool_wrapper(data_validator_tools.send_email)
        ),
    ]
    
    return Agent(
        llm_instance=chat_llm,
        tools=tools,
        max_iterations=max_iterations,
        max_retries_per_step=max_retries_per_step,
        total_max_retries=total_max_retries
    )


def main():
    """Main entry point for running the agent."""
    # Create agent
    agent = create_agent()
    
    # Run interactive mode
    agent.run_interactive()


if __name__ == "__main__":
    main()

