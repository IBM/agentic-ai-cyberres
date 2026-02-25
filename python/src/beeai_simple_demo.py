#!/usr/bin/env python3
"""
BeeAI-powered Recovery Validation Agent - Simple Demo
Pure conversational interface without structured output parsing
"""

import asyncio
import os
import sys
import re
from dotenv import load_dotenv

# BeeAI Framework imports
from beeai_framework.adapters.ollama import OllamaChatModel
from beeai_framework.backend.types import ChatModelParameters
from beeai_framework.backend.message import UserMessage, AssistantMessage

# Load environment variables
load_dotenv()


class SimpleBeeAIDemo:
    """
    Simplified BeeAI demo using direct LLM calls.
    No agent framework, just pure conversation.
    """
    
    def __init__(self):
        """Initialize the BeeAI demo."""
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        print("🚀 Initializing BeeAI Framework...")
        
        # Create Ollama chat model
        self.llm = OllamaChatModel(
            model_id=self.ollama_model,
            parameters=ChatModelParameters(
                temperature=0.7,
                max_tokens=2048,
            ),
            base_url=self.ollama_base_url
        )
        print(f"✅ LLM initialized: {self.ollama_model}\n")
        
        # Conversation history
        self.messages = []
        
        # System prompt
        self.system_prompt = """You are an intelligent Recovery Validation Agent powered by IBM's BeeAI Framework.

Your role is to help users validate recovered IT resources including:
- Virtual Machines (VMs)
- Oracle Databases  
- MongoDB Instances
- Network Services

When a user mentions they have recovered a resource and want to validate it:
1. Acknowledge the resource type and location (IP/hostname)
2. Explain the validation process in 4 phases:
   - Phase 1: Discovery (OS, services, processes, applications)
   - Phase 2: Validation (connectivity, availability, integrity)
   - Phase 3: Evaluation (status, issues, recommendations)
   - Phase 4: Reporting (detailed report via email)
3. Ask for necessary credentials (SSH for VMs, DB credentials for databases)
4. Confirm email address for the report

When user provides credentials:
1. Acknowledge receipt
2. Confirm you'll proceed with validation
3. Explain what you'll do next
4. Be helpful and professional

Be conversational, helpful, and professional. Use emojis sparingly."""
    
    def _extract_resource_info(self, user_input: str) -> dict:
        """Extract resource information from natural language input."""
        info = {
            "type": None,
            "ip": None,
            "credentials": {}
        }
        
        # Detect resource type
        if any(word in user_input.lower() for word in ['vm', 'virtual machine', 'server']):
            info["type"] = "VM"
        elif any(word in user_input.lower() for word in ['oracle', 'oracle db', 'oracle database']):
            info["type"] = "Oracle Database"
        elif any(word in user_input.lower() for word in ['mongo', 'mongodb']):
            info["type"] = "MongoDB"
        
        # Extract IP address or hostname
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ip_match = re.search(ip_pattern, user_input)
        if ip_match:
            info["ip"] = ip_match.group()
        
        # Extract credentials if mentioned
        if 'root' in user_input.lower():
            info["credentials"]["user"] = "root"
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, user_input)
        if email_match:
            info["credentials"]["email"] = email_match.group()
        
        return info
    
    async def chat(self, user_input: str) -> str:
        """Send a message and get response."""
        # Add user message to history
        self.messages.append(UserMessage(content=user_input))
        
        # Prepare messages for LLM (include system prompt)
        llm_messages = [UserMessage(content=self.system_prompt)] + self.messages
        
        # Get response from LLM
        try:
            response = await self.llm.run(llm_messages)
            
            # Extract text from response - BeeAI returns output as list of messages
            if hasattr(response, 'output') and len(response.output) > 0:
                # Get the last message from output
                last_message = response.output[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    # Content might be a list of MessageTextContent objects
                    if isinstance(content, list) and len(content) > 0:
                        # Extract text from first content item
                        if hasattr(content[0], 'text'):
                            response_text = content[0].text
                        else:
                            response_text = str(content[0])
                    elif isinstance(content, str):
                        response_text = content
                    else:
                        response_text = str(content)
                else:
                    response_text = str(last_message)
            elif hasattr(response, 'content'):
                response_text = response.content
            elif hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)
            
            # Add assistant response to history
            self.messages.append(AssistantMessage(content=response_text))
            
            return response_text
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}\nPlease try rephrasing your request."
    
    async def interactive_mode(self):
        """Run in interactive conversational mode."""
        print("\n" + "="*80)
        print("🤖 BeeAI Recovery Validation Agent - Interactive Demo")
        print("="*80)
        print("\n💡 Example requests:")
        print("  • 'What can you help me with?'")
        print("  • 'I have recovered a VM at 192.168.1.100, please validate it'")
        print("  • 'Validate the Oracle database at 10.0.0.50'")
        print("  • 'Check the MongoDB instance at db.example.com'")
        print("  • 'exit' to quit")
        print("\n" + "="*80 + "\n")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    print("\n👋 Thank you for using BeeAI Recovery Validation Agent!")
                    print("   Goodbye! 🚀\n")
                    break
                
                print("\n🤖 Agent:")
                
                # Get response
                response = await self.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! 🚀\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("   Please try again or type 'exit' to quit.\n")


async def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("  BeeAI Framework - Recovery Validation Agent")
    print("  Powered by IBM BeeAI v0.1.77")
    print("="*80 + "\n")
    
    try:
        demo = SimpleBeeAIDemo()
        await demo.interactive_mode()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("   Please check your configuration and try again.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! 🚀\n")
        sys.exit(0)

# Made with Bob
