//
// Copyright contributors to the agentic-ai-cyberres project
//
import { ChatModel } from "beeai-framework/backend/chat";
import { getEnv, parseEnv } from "beeai-framework/internals/env";
import { z } from "zod";
import { WatsonxChatModel } from "beeai-framework/adapters/watsonx/backend/chat";
import { OpenAIChatModel } from "beeai-framework/adapters/openai/backend/chat";
import { OllamaChatModel } from "beeai-framework/adapters/ollama/backend/chat";
import { GroqChatModel } from "beeai-framework/adapters/groq/backend/chat";
import { GoogleVertexChatModel } from "beeai-framework/adapters/google-vertex/backend/chat";

export const Providers = {
  WATSONX: "watsonx",
  OLLAMA: "ollama",
  OPENAI: "openai",
  GROQ: "groq",
  AZURE: "azure",
  VERTEXAI: "vertexai",
} as const;
type Provider = (typeof Providers)[keyof typeof Providers];

export const LLMFactories: Record<Provider, () => ChatModel> = {
  [Providers.GROQ]: () =>
    new GroqChatModel(
      getEnv("GROQ_MODEL") || "llama-3.1-70b-versatile",
      {
        temperature: 0,
      },
      {
        apiKey: getEnv("GROQ_API_KEY"),
      }
    ),
  [Providers.OPENAI]: () =>
    new OpenAIChatModel(
      getEnv("OPENAI_MODEL") || "gpt-4o",
      {
        temperature: 0,
        maxTokens: 2048,
      }
    ),
  [Providers.OLLAMA]: () =>
    new OllamaChatModel(
      getEnv("OLLAMA_MODEL") || "llama3.1:8b",
      {
        temperature: 0,
      },
      {
        baseURL: getEnv("OLLAMA_HOST"),
      }
    ),
  [Providers.WATSONX]: () =>
    new WatsonxChatModel(
      getEnv("WATSONX_MODEL") || "meta-llama/llama-3-1-70b-instruct",
      {
        apiKey: getEnv("WATSONX_API_KEY"),
        projectId: getEnv("WATSONX_PROJECT_ID"),
        region: getEnv("WATSONX_REGION"),
      } as any
    ),
  [Providers.AZURE]: () =>
    new OpenAIChatModel(
      getEnv("OPENAI_MODEL") || "gpt-4o-mini",
      {
        temperature: 0,
        maxTokens: 2048,
      },
      {
        azure: true,
      }
    ),
  [Providers.VERTEXAI]: () =>
    new GoogleVertexChatModel(
      getEnv("VERTEXAI_MODEL") || "gemini-1.5-flash-001",
      {},
      {
        location: getEnv("VERTEXAI_LOCATION") || "us-central1",
        project: getEnv("VERTEXAI_PROJECT"),
      }
    ),
};

export function getChatLLM(provider?: Provider): ChatModel {
  if (!provider) {
    provider = parseEnv("LLM_BACKEND", z.nativeEnum(Providers), Providers.OLLAMA);
  }

  const factory = LLMFactories[provider];
  if (!factory) {
    throw new Error(`Provider "${provider}" not found.`);
  }
  return factory();
}
