#!/usr/bin/env python3
"""
Basic BeeAI Framework Test
Tests BeeAI's OllamaChatModel with simple conversation.
"""

import asyncio
import logging
from beeai_framework.adapters.ollama import OllamaChatModel
from beeai_framework.backend.types import ChatModelParameters
from beeai_framework.backend.message import UserMessage, AssistantMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_beeai_basic():
    """Test basic BeeAI conversation."""
    print("\n" + "="*80)
    print("🐝 BeeAI Framework - Basic Test")
    print("="*80 + "\n")
    
    # Initialize BeeAI LLM
    print("1. Initializing BeeAI OllamaChatModel...")
    llm = OllamaChatModel(
        model_id="llama3.2:latest",
        parameters=ChatModelParameters(
            temperature=0.7,
            max_tokens=500
        )
    )
    print("   ✅ LLM initialized (using llama3.2:latest)\n")
    
    # Test simple conversation
    print("2. Testing simple conversation...")
    messages = [
        UserMessage(content="Hello! What is 2+2?")
    ]
    
    print("   Sending: 'Hello! What is 2+2?'")
    response = await llm.run(messages)
    
    # Extract response text
    if response.output and len(response.output) > 0:
        assistant_msg = response.output[0]
        if hasattr(assistant_msg, 'content') and len(assistant_msg.content) > 0:
            response_text = assistant_msg.content[0].text
            print(f"   Response: {response_text}\n")
        else:
            print(f"   Raw response: {response}\n")
    else:
        print(f"   Raw response: {response}\n")
    
    # Test resource extraction
    print("3. Testing resource information extraction...")
    messages = [
        UserMessage(content="""
        I have recovered a VM at IP address 192.168.1.100.
        The SSH credentials are: username=admin, password=secret123
        Please send the validation report to admin@example.com
        """)
    ]
    
    print("   Sending resource info...")
    response = await llm.run(messages)
    
    if response.output and len(response.output) > 0:
        assistant_msg = response.output[0]
        if hasattr(assistant_msg, 'content') and len(assistant_msg.content) > 0:
            response_text = assistant_msg.content[0].text
            print(f"   Response: {response_text[:200]}...\n")
    
    print("="*80)
    print("✅ BeeAI Basic Test Complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_beeai_basic())

# Made with Bob
