import asyncio
import os
from helpers.llm import get_chat_llm
from helpers.reader import ConsoleReader
from helpers.data_validator_tools import (
    MongoDBDataValidatorTool,
    FindWhatsRunningByPortsTool,
    FindRunningProcessesTool,
    SendEmailTool,
)
from bee_agent_framework import BeeAgent, TokenMemory, OpenMeteoTool, DuckDuckGoSearchTool, FrameworkError

async def main():
    llm = get_chat_llm()
    agent = BeeAgent(
        llm=llm,
        memory=TokenMemory(llm=llm),
        tools=[
            OpenMeteoTool(),
            DuckDuckGoSearchTool(),
            MongoDBDataValidatorTool(),
            FindWhatsRunningByPortsTool(),
            FindRunningProcessesTool(),
            SendEmailTool(),
        ],
    )

    reader = ConsoleReader(
        fallback="What are the most common enterprise applications that run on Linux in the industry today?  Do not include Linux or Linux distributions in the results.  Do not identify what's currently running."
    )

    async for prompt in reader:
        try:
            response = await agent.run(
                {"prompt": prompt},
                execution={
                    "maxIterations": 8,
                    "maxRetriesPerStep": 3,
                    "totalMaxRetries": 10,
                },
            )
            # Assuming response has an observe method similar to Node.js version
            async for update in response.observe():
                reader.write(f"Agent 🤖 ({update['key']}) :", update["value"])
            reader.write("Agent 🤖 :", response.result.text)
        except FrameworkError as error:
            reader.write("Error", str(error))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
