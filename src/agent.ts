//
// Copyright contributors to the agentic-ai-cyberres project
//
import "dotenv/config.js";
import { BeeAgent } from "bee-agent-framework/agents/bee/agent";
import { FrameworkError } from "bee-agent-framework/errors";
import { TokenMemory } from "bee-agent-framework/memory/tokenMemory";
import { OpenMeteoTool } from "bee-agent-framework/tools/weather/openMeteo";
import { getChatLLM } from "./helpers/llm.js";
import { DuckDuckGoSearchTool } from "bee-agent-framework/tools/search/duckDuckGoSearch";
import { createConsoleReader } from "./helpers/reader.js";
import { MongoDBDataValidatorTool } from "./helpers/dataValidatorTools.ts";
import { PostgreSQLDataValidatorTool } from "./helpers/dataValidatorTools.ts";
import { FindWhatsRunningByPortsTool } from "./helpers/dataValidatorTools.ts";
import { FindRunningProcessesTool } from "./helpers/dataValidatorTools.ts";
import { SendEmailTool } from "./helpers/dataValidatorTools.ts";

const llm = getChatLLM();
const agent = new BeeAgent({
  llm,
  memory: new TokenMemory({ llm }),
  // tools: [new OpenMeteoTool(), new DuckDuckGoSearchTool(), MongoDBDataValidatorTool, PostgreSQLDataValidatorTool, FindWhatsRunningByPortsTool, FindRunningProcessesTool, SendEmailTool ],
  tools: [MongoDBDataValidatorTool, PostgreSQLDataValidatorTool, FindRunningProcessesTool, SendEmailTool ],
  systemPrompt: `You are a data validation assistant.
When asked to validate data, follow this workflow and do not go out of order:
1. FIRST: Use the LLM to determine what are some commonly used enterprise applications in the industry that run on Linux
2. SECOND: Use FindRunningProcesses to discover what enterprise applications are currently running on the Linux system
3. THIRD: Look for enterprise application process names in the output (for example, mongod, postgres)
4. FOURTH: VALIDATE: Call ONLY the appropriate validator tool only for each running application using the exact process name from FindRunningProcessesTool.
   - If 'mongod' is found → MongoDBDataValidator with argument 'mongod'
   - If 'postgres' is found → PostgreSQLDataValidator with argument 'postgres'
5. FIFTH: SEND EMAIL: ALWAYS send an email by calling the SendEmailTool tool. If a validation fails, still send the email.  If a validation succeeds, still send the email.  ALWAYS SEND THE EMAIL.
DO NOT SIMULATE OR HALLUCINATE RUNNING ANY OF THESE TOOLS. 
If not asked to validate data, use the LLM to decide on a new execution plan.`,
});

const reader = createConsoleReader({ fallback: "What are the most common enterprise applications that run on Linux in the industry today?  Do not include Linux or Linux distributions in the results.  Do not identify what's currently running." });
for await (const { prompt } of reader) {
  try {
    const response = await agent
      .run(
        { prompt },
        {
          execution: {
            maxIterations: 8,
            maxRetriesPerStep: 3,
            totalMaxRetries: 10,
          },
        },
      )
      .observe((emitter) => {
        emitter.on("update", (data) => {
          reader.write(`Agent 🤖 (${data.update.key}) :`, data.update.value);
        });
      });

    reader.write(`Agent 🤖 :`, response.result.text);
  } catch (error) {
    reader.write(`Error`, FrameworkError.ensure(error).dump());
  }
}
