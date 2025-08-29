#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
import asyncio
from reader import create_console_reader
from llm import get_chat_llm, Providers
from agent import BeeAgent, TokenMemory
from dataValidatorTools import (
    MongoDBDataValidatorTool,
    FindWhatsRunningByPortsTool,
    FindRunningProcessesTool,
    SendEmailTool
)

async def main():
    # Get LLM instance (defaults to Ollama)
    llm = get_chat_llm()
    
    # Create agent with tools
    agent = BeeAgent(
        llm=llm,
        memory=TokenMemory(llm=llm),
        tools=[
            MongoDBDataValidatorTool,
            FindWhatsRunningByPortsTool,
            FindRunningProcessesTool,
            SendEmailTool
        ]
    )
    
    # Create console reader
    reader = create_console_reader(
        fallback="What are the most common enterprise applications that run on Linux in the industry today? Do not include Linux or Linux distributions in the results. Do not identify what's currently running."
    )
    
    # Main interaction loop
    async for prompt_data in reader:
        try:
            response = await agent.run(
                {"prompt": prompt_data["prompt"]},
                execution={
                    "maxIterations": 8,
                    "maxRetriesPerStep": 3,
                    "totalMaxRetries": 10
                }
            )
            
            reader.write("Agent 🤖", response["result"]["text"])
            
        except Exception as error:
            reader.write("Error", str(error))

if __name__ == "__main__":
    asyncio.run(main())