import asyncio
import logging
import os
import sys
import traceback

from beeai_framework.adapters.beeai.backend.document_processor import LLMDocumentReranker
from beeai_framework.adapters.beeai.backend.vector_store import TemporalVectorStore
from beeai_framework.adapters.langchain.backend.vector_store import LangChainVectorStore
from beeai_framework.agents.experimental.rag import RAGAgent, RagAgentRunInput
from beeai_framework.agents import AgentExecutionConfig
from beeai_framework.backend import UserMessage
from beeai_framework.backend.chat import ChatModel
from beeai_framework.backend.document_loader import DocumentLoader
from beeai_framework.backend.embedding import EmbeddingModel
from beeai_framework.backend.vector_store import VectorStore
from beeai_framework.errors import FrameworkError
from beeai_framework.logger import Logger
from beeai_framework.memory import UnconstrainedMemory
from examples.helpers.io import ConsoleReader
from langchain.document_loaders import UnstructuredMarkdownLoader

# LC dependencies - to be swapped with BAI dependencies
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "Optional modules are not found.\nRun 'pip install \"beeai-framework[rag]\"' to install."
    ) from e

import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


from dotenv import load_dotenv

load_dotenv()  # load environment variables
logger = Logger("rag-agent", level=logging.DEBUG)


POPULATE_VECTOR_DB = True
VECTOR_DB_PATH_4_DUMP = "docs/vectorstore"  # Set this path for persistency
INPUT_DOCUMENTS_LOCATION = "docs/integrations"


async def populate_documents() -> VectorStore | None:
    embedding_model = EmbeddingModel.from_name("ollama:nomic-embed-text:latest", truncate_input_tokens=500)

    # Load existing vector store if available
    if VECTOR_DB_PATH_4_DUMP and os.path.exists(VECTOR_DB_PATH_4_DUMP):
        print(f"Loading vector store from: {VECTOR_DB_PATH_4_DUMP}")
        preloaded_vector_store: VectorStore = TemporalVectorStore.load(
            path=VECTOR_DB_PATH_4_DUMP, embedding_model=embedding_model
        )
        return preloaded_vector_store

    # Create new vector store if population is enabled
    if POPULATE_VECTOR_DB:
        embedding_model = EmbeddingModel.from_name("ollama:nomic-embed-text:latest", truncate_input_tokens=500)
        # embedding_model = EmbeddingModel.from_name("watsonx:ibm/slate-125m-english-rtrvr-v2", truncate_input_tokens=500)

        # Document loading
        # loader = UnstructuredMarkdownLoader(file_path="docs/modules/agents.mdx")
        loader = DocumentLoader.from_name(
            name="langchain:UnstructuredMarkdownLoader", file_path="docs/modules/agents.mdx"
        )
        try:
            documents = await loader.load()
        except Exception as e:
            print(e)
            return None

        # Note: Text splitting will be abstracted in future versions
        from beeai_framework.adapters.langchain.mappers.documents import (
            document_to_lc_document,
            lc_document_to_document,
        )

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=1000)
        lc_documents = [document_to_lc_document(doc) for doc in documents]
        all_splits = text_splitter.split_documents(lc_documents)
        documents = [lc_document_to_document(document) for document in all_splits]
        print(f"Loaded {len(documents)} documents")

        vector_store: TemporalVectorStore = VectorStore.from_name(
            name="beeai:TemporalVectorStore", embedding_model=embedding_model
        ) 
        _ = await vector_store.add_documents(documents=documents)
        if VECTOR_DB_PATH_4_DUMP and isinstance(vector_store, TemporalVectorStore):
            print(f"Dumping vector store to: {VECTOR_DB_PATH_4_DUMP}")
            vector_store.vector_store.dump(VECTOR_DB_PATH_4_DUMP)
        return vector_store

    # unable to fetch or build vector store
    return None


async def main() -> None:
    reader = ConsoleReader()
    
    vector_store = await populate_documents()
    reader.write("🛠️ System: ", "Documents populated and vector store loaded.")
    
    if vector_store is None:
        raise FileNotFoundError(
            f"Vector database not found at {VECTOR_DB_PATH_4_DUMP}. "
            "Either set POPULATE_VECTOR_DB=True to create a new one, or ensure the database file exists."
        )

    llm = ChatModel.from_name("ollama:llama3.2")
    reranker = LLMDocumentReranker(llm)

    reader.write("🛠️ System: ", "LLM initialized and document reranking is done.")
    
    agent = RAGAgent(llm=llm, memory=UnconstrainedMemory(), vector_store=vector_store, reranker=reranker)
    
    reader.write("🛠️ System: ", "Agent initialized with vector store and reranker")
    
    for user_query in reader:
        # output: ReActAgentRunOutput = await agent.run(
        #     user_query=user_query, execution=AgentExecutionConfig(total_max_retries=2, max_retries_per_step=3, max_iterations=8)
        # ).on(
        #     "update",
        #     lambda data, event: handle_agent_update(data, conv_history, user_query, reader)
        # )
        # response = await agent.run(RagAgentRunInput(message=UserMessage("What agents are available in BeeAI?")))
        response = await agent.run(RagAgentRunInput(message=UserMessage(user_query)))
        reader.write(f"Agent(final_answer) 🤖 : ", response.message.text)
        # print(response.message.text)

    # response = await agent.run(RagAgentRunInput(message=UserMessage("What agents are available in BeeAI?")))
    # print(response.message.text)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except FrameworkError as e:
        traceback.print_exc()
        sys.exit(e.explain())