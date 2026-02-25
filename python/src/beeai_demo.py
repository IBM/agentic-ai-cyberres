#!/usr/bin/env python3
"""
BeeAI-powered Recovery Validation Agent - Demo Version
Simplified for quick demonstration
"""

import asyncio
import os
import sys
import re
from dotenv import load_dotenv

# BeeAI Framework imports
from beeai_framework.adapters.ollama import OllamaChatModel
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.agents.types import AgentMeta
from beeai_framework.backend.types import ChatModelParameters

# Load environment variables
load_dotenv()


class BeeAIDemo:
    """
    Simplified BeeAI demo for recovery validation.
    Shows conversational interface with natural language understanding.
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
                max_tokens=8192,
            ),
            base_url=self.ollama_base_url
        )
        print(f"✅ LLM initialized: {self.ollama_model}")
        
        # Create shared memory for conversation
        self.memory = UnconstrainedMemory()
        print("✅ Memory initialized")
        
        # Create the main conversational agent
        self.agent = self._create_agent()
        print("✅ Agent created\n")
    
    def _create_agent(self) -> ReActAgent:
        """Create the main BeeAI conversational agent."""
        meta = AgentMeta(
            name="RecoveryValidationAgent",
            description="AI-powered recovery validation assistant",
            tools=[],  # Required field
            extra_description=(
                "I am an intelligent recovery validation agent powered by BeeAI framework. "
                "I help you validate recovered IT resources including:\n"
                "- Virtual Machines (VMs)\n"
                "- Oracle Databases\n"
                "- MongoDB Instances\n"
                "- Network Services\n\n"
                "I can understand natural language requests like:\n"
                "- 'I have recovered a VM at 192.168.1.100, please validate it'\n"
                "- 'Check the Oracle database at 10.0.0.50'\n"
                "- 'Validate MongoDB at db.example.com'\n\n"
                "I will guide you through the validation process and provide "
                "comprehensive reports with actionable recommendations."
            )
        )
        
        agent = ReActAgent(
            llm=self.llm,
            tools=[],  # No tools for demo, pure conversation
            memory=self.memory,
            meta=meta,
            stream=False
        )
        
        return agent
    
    def _extract_resource_info(self, user_input: str) -> dict:
        """Extract resource information from natural language input."""
        info = {
            "type": None,
            "ip": None,
            "action": None
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
        else:
            # Look for hostname
            hostname_pattern = r'\b[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*\b'
            hostname_match = re.search(hostname_pattern, user_input.lower())
            if hostname_match and '.' in hostname_match.group():
                info["ip"] = hostname_match.group()
        
        # Detect action
        if any(word in user_input.lower() for word in ['validate', 'check', 'test', 'verify']):
            info["action"] = "validate"
        elif any(word in user_input.lower() for word in ['discover', 'scan', 'find']):
            info["action"] = "discover"
        
        return info
    
    async def process_validation_request(self, user_input: str) -> str:
        """Process a validation request and return structured response."""
        # Extract resource information
        resource_info = self._extract_resource_info(user_input)
        
        if not resource_info["type"] or not resource_info["ip"]:
            return await self.agent.run(user_input)
        
        # Create a structured validation prompt
        validation_prompt = f"""
User Request: {user_input}

I understand you want to validate a {resource_info['type']} at {resource_info['ip']}.

Let me guide you through the validation process:

**Phase 1: Discovery**
I will discover what's running on this {resource_info['type']}:
- Operating system and version
- Running services and processes
- Network configuration
- Installed applications
- Database instances (if applicable)

**Phase 2: Validation**
I will perform comprehensive validation checks:
- System accessibility and connectivity
- Service availability and health
- Data integrity and consistency
- Performance metrics
- Security configuration

**Phase 3: Evaluation**
I will analyze the results and provide:
- Overall recovery status (Success/Partial/Failure)
- Critical issues identified
- Actionable recommendations
- Recovery confidence score
- Next steps

**Phase 4: Reporting**
I will generate a detailed report and send it to your email.

Would you like me to proceed with the validation? 
If yes, I'll need some additional information:
- SSH credentials (for VM) or database credentials
- Any specific services or applications to check
- Email address for the report

Please provide these details, or say 'proceed' to use default credentials from environment.
"""
        
        return validation_prompt
    
    async def interactive_mode(self):
        """Run in interactive conversational mode."""
        print("\n" + "="*80)
        print("🤖 BeeAI Recovery Validation Agent - Interactive Demo")
        print("="*80)
        print("\n💡 Example requests:")
        print("  • 'I have recovered a VM at 192.168.1.100, please validate it'")
        print("  • 'Validate the Oracle database at 10.0.0.50'")
        print("  • 'Check the MongoDB instance at db.example.com'")
        print("  • 'What can you help me with?'")
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
                
                print("\n🤖 Agent: ", end="", flush=True)
                
                # Check if this is a validation request
                if any(word in user_input.lower() for word in ['validate', 'check', 'recovered', 'recovery']):
                    response = await self.process_validation_request(user_input)
                    print(response)
                else:
                    # General conversation - handle both string and structured output
                    result = await self.agent.run(user_input)
                    # Extract text from result
                    if hasattr(result, 'output'):
                        output_text = result.output
                    elif hasattr(result, 'text'):
                        output_text = result.text
                    else:
                        output_text = str(result)
                    print(output_text)
                
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
        demo = BeeAIDemo()
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
