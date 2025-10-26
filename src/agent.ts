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
  tools: [new OpenMeteoTool(), new DuckDuckGoSearchTool(), MongoDBDataValidatorTool, PostgreSQLDataValidatorTool, FindWhatsRunningByPortsTool, FindRunningProcessesTool, SendEmailTool ],
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
