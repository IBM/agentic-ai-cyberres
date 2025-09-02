#
# Copyright contributors to the agentic-ai-cyberres project
#
import os
import asyncio
from reader import create_console_reader
from llm import get_chat_llm, Providers, SafetyViolationError
from agent import BeeAgent, TokenMemory
from dataValidatorTools import (
    FindRunningProcessesTool,
    MongoDBDataValidatorTool,
    SendEmailTool,
    FindWhatsRunningByPortsTool
)

class SessionGuardrails:
    @staticmethod
    def validate_environment():
        """Validate that required environment variables are set"""
        required_vars = ["USER_EMAIL", "MONGODB_NAME", "MONGODB_COLLECTION_NAME"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
            print("Some features may not work properly.")

async def main():
    # Validate environment
    SessionGuardrails.validate_environment()
    
    # Get LLM instance
    try:
        llm = get_chat_llm()
    except SafetyViolationError as e:
        print(f"Security configuration error: {e}")
        return
    
    # Create agent with tools
    agent = BeeAgent(
        llm=llm,
        memory=TokenMemory(llm=llm),
        tools=[
            FindRunningProcessesTool,
            MongoDBDataValidatorTool,
            SendEmailTool,
            FindWhatsRunningByPortsTool
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
            
        except SafetyViolationError as e:
            reader.write("Security Error", f"Blocked: {str(e)}")
        except Exception as error:
            reader.write("Error", f"Unexpected error: {str(error)}")

if __name__ == "__main__":
    asyncio.run(main())