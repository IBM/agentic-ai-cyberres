//
// Copyright contributors to the agentic-ai-cyberres project
//
import "dotenv/config.js";
import { ReActAgent } from "beeai-framework/agents/react/agent";
import { FrameworkError } from "beeai-framework/errors";
import { TokenMemory } from "beeai-framework/memory/tokenMemory";
import { OpenMeteoTool } from "beeai-framework/tools/weather/openMeteo";
import { getChatLLM } from "./helpers/llm.js";
import { DuckDuckGoSearchTool } from "beeai-framework/tools/search/duckDuckGoSearch";
import { createConsoleReader } from "./helpers/reader.js";
import { MongoDBDataValidatorTool } from "./helpers/dataValidatorTools.ts";
import { PostgreSQLDataValidatorTool } from "./helpers/dataValidatorTools.ts";
import { FindWhatsRunningByPortsTool } from "./helpers/dataValidatorTools.ts";
import { FindRunningProcessesTool } from "./helpers/dataValidatorTools.ts";
import { SendEmailTool } from "./helpers/dataValidatorTools.ts";
import { sendSimpleEmail } from "./helpers/emailHelper.ts";
import { Logger } from "beeai-framework/logger/logger";


Logger.root.level = "silent"; // disable internal logs
const logger = new Logger({ name: "app", level: "trace" });


const llm = getChatLLM();
const agent = new ReActAgent({
  llm,
  memory: new TokenMemory(),
  tools: [MongoDBDataValidatorTool, PostgreSQLDataValidatorTool, FindRunningProcessesTool ]
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

	// To observe all events (uncomment following block)
        // emitter.match("*.*", async (data: unknown, event) => {
        //   logger.trace(event, `Received event "${event.path}"`);
        // });

        // To get raw LLM input 
        emitter.match(
          (event) => event.creator === llm && event.name === "start",
          async (data: InferCallbackValue<GenerateEvents["start"]>, event) => {
            logger.trace(
              event,
              [
                `Received LLM event "${event.path}"`,
                JSON.stringify(data.input), // array of messages
              ].join("\n"),
            );
          },
        );


      });

    reader.write(`Agent 🤖 :`, response.result.text);

    // deterministically notify user of results instead of leaving it up to the LLM
    // Note that this sends an email for EVERY pronpt, assuming a somewhat autonomous run of this agent only for data validation.

    const result = await sendSimpleEmail(response.result.text);

    if (result.success) {
	reader.write(`Success`, result.message);
    } else {
	reader.write(`Error`, result.error);
    }

  } catch (error) {
    reader.write(`Error`, FrameworkError.ensure(error as Error).dump());
  }

}
