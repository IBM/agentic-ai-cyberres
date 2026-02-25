#!/usr/bin/env python3
"""
BeeAI Interactive Validation CLI

Interactive command-line interface for validating infrastructure resources
using the BeeAI-powered validation workflow.

Usage:
    python beeai_interactive.py

Then provide natural language prompts like:
    "Validate VM at 192.168.1.100 with SSH user admin"
    "Check Oracle database at db.example.com port 1521"
    "Discover and validate MongoDB at mongo-server:27017"
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import BeeAI components
from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import (
    ValidationRequest,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    ResourceType
)


class BeeAIInteractiveCLI:
    """Interactive CLI for BeeAI validation workflow."""
    
    def __init__(self):
        """Initialize the interactive CLI."""
        self.orchestrator = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize the BeeAI orchestrator."""
        if self.initialized:
            return
        
        print("\n" + "="*60)
        print("🤖 BeeAI Infrastructure Validation System")
        print("="*60)
        print("\nInitializing BeeAI orchestrator...")
        
        try:
            self.orchestrator = BeeAIValidationOrchestrator(
                mcp_server_path="../cyberres-mcp",
                llm_model="ollama:llama3.2",
                enable_discovery=True,
                enable_ai_evaluation=True
            )
            
            await self.orchestrator.initialize()
            self.initialized = True
            
            print("✅ BeeAI orchestrator initialized successfully!")
            print(f"✅ Connected to MCP server")
            print(f"✅ Discovered {len(self.orchestrator._mcp_tools)} MCP tools")
            print(f"✅ LLM: {self.orchestrator.llm_model}")
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            logger.error(f"Initialization failed: {e}", exc_info=True)
            raise
    
    def parse_prompt(self, prompt: str) -> ValidationRequest:
        """Parse natural language prompt into ValidationRequest.
        
        Args:
            prompt: Natural language prompt from user
        
        Returns:
            ValidationRequest object
        
        Examples:
            "Validate VM at 192.168.1.100 with SSH user admin password secret"
            "Check Oracle database at db.example.com port 1521 user system password oracle"
            "Validate MongoDB at mongo-server:27017"
        """
        prompt_lower = prompt.lower()
        
        # Detect resource type
        if 'vm' in prompt_lower or 'server' in prompt_lower or 'linux' in prompt_lower:
            return self._parse_vm_prompt(prompt)
        elif 'oracle' in prompt_lower or 'db' in prompt_lower:
            return self._parse_oracle_prompt(prompt)
        elif 'mongo' in prompt_lower:
            return self._parse_mongo_prompt(prompt)
        else:
            # Default to VM
            return self._parse_vm_prompt(prompt)
    
    def _parse_vm_prompt(self, prompt: str) -> ValidationRequest:
        """Parse VM validation prompt."""
        import re
        
        # Extract host (IP or hostname) - try multiple patterns
        # Pattern 1: "at <host>" or "host <host>"
        host_match = re.search(r'(?:at|host)\s+([^\s]+)', prompt)
        if not host_match:
            # Pattern 2: "vm <ip_address>" (IP address directly after vm)
            host_match = re.search(r'vm\s+(\d+\.\d+\.\d+\.\d+)', prompt)
        if not host_match:
            # Pattern 3: any IP address in the prompt
            host_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', prompt)
        if not host_match:
            # Pattern 4: any hostname-like string
            host_match = re.search(r'vm\s+([a-zA-Z0-9.-]+)', prompt)
        
        host = host_match.group(1) if host_match else "localhost"
        
        # Extract SSH user
        user_match = re.search(r'user\s+([^\s:]+)', prompt)
        ssh_user = user_match.group(1) if user_match else "root"
        
        # Extract SSH password (handle optional colon)
        password_match = re.search(r'password:?\s+([^\s]+)', prompt)
        ssh_password = password_match.group(1) if password_match else None
        
        # Extract SSH port
        port_match = re.search(r'port\s+(\d+)', prompt)
        ssh_port = int(port_match.group(1)) if port_match else 22
        
        vm_resource = VMResourceInfo(
            host=host,
            resource_type=ResourceType.VM,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_port=ssh_port
        )
        
        return ValidationRequest(
            resource_info=vm_resource,
            auto_discover=True
        )
    
    def _parse_oracle_prompt(self, prompt: str) -> ValidationRequest:
        """Parse Oracle database validation prompt."""
        import re
        
        # Extract host
        host_match = re.search(r'(?:at|host)\s+([^\s]+)', prompt)
        host = host_match.group(1) if host_match else "localhost"
        
        # Extract port
        port_match = re.search(r'port\s+(\d+)', prompt)
        port = int(port_match.group(1)) if port_match else 1521
        
        # Extract user
        user_match = re.search(r'user\s+([^\s]+)', prompt)
        db_user = user_match.group(1) if user_match else "system"
        
        # Extract password
        password_match = re.search(r'password\s+([^\s]+)', prompt)
        db_password = password_match.group(1) if password_match else None
        
        # Extract service name
        service_match = re.search(r'service\s+([^\s]+)', prompt)
        service_name = service_match.group(1) if service_match else "ORCL"
        
        oracle_resource = OracleDBResourceInfo(
            host=host,
            resource_type=ResourceType.ORACLE_DB,
            port=port,
            db_user=db_user,
            db_password=db_password,
            service_name=service_name
        )
        
        return ValidationRequest(
            resource_info=oracle_resource,
            auto_discover=False
        )
    
    def _parse_mongo_prompt(self, prompt: str) -> ValidationRequest:
        """Parse MongoDB validation prompt."""
        import re
        
        # Extract host
        host_match = re.search(r'(?:at|host)\s+([^\s:]+)', prompt)
        host = host_match.group(1) if host_match else "localhost"
        
        # Extract port
        port_match = re.search(r':(\d+)', prompt)
        port = int(port_match.group(1)) if port_match else 27017
        
        # Extract user
        user_match = re.search(r'user\s+([^\s]+)', prompt)
        mongo_user = user_match.group(1) if user_match else None
        
        # Extract password
        password_match = re.search(r'password\s+([^\s]+)', prompt)
        mongo_password = password_match.group(1) if password_match else None
        
        mongo_resource = MongoDBResourceInfo(
            host=host,
            resource_type=ResourceType.MONGODB,
            port=port,
            mongo_user=mongo_user,
            mongo_password=mongo_password
        )
        
        return ValidationRequest(
            resource_info=mongo_resource,
            auto_discover=False
        )
    
    async def execute_validation(self, prompt: str):
        """Execute validation based on user prompt.
        
        Args:
            prompt: Natural language validation prompt
        """
        print("\n" + "-"*60)
        print(f"📝 Prompt: {prompt}")
        print("-"*60)
        
        try:
            # Parse prompt into request
            print("\n🔍 Parsing prompt...")
            request = self.parse_prompt(prompt)
            
            print(f"✅ Detected resource type: {request.resource_info.resource_type.value}")
            print(f"✅ Target host: {request.resource_info.host}")
            
            # Execute workflow
            print("\n🚀 Starting validation workflow...")
            result = await self.orchestrator.execute_workflow(request)
            
            # Display results
            self._display_results(result)
            
        except Exception as e:
            print(f"\n❌ Validation failed: {e}")
            logger.error(f"Validation error: {e}", exc_info=True)
    
    def _display_results(self, result):
        """Display validation results in a user-friendly format."""
        print("\n" + "="*60)
        print("📊 VALIDATION RESULTS")
        print("="*60)
        
        # Overall status
        status_emoji = {
            "success": "✅",
            "partial_success": "⚠️",
            "failure": "❌"
        }
        emoji = status_emoji.get(result.workflow_status, "❓")
        
        print(f"\n{emoji} Status: {result.workflow_status.upper()}")
        print(f"📈 Score: {result.validation_result.score}/100")
        print(f"⏱️  Execution Time: {result.execution_time_seconds:.2f}s")
        
        # Check summary
        print(f"\n📋 Checks Summary:")
        print(f"  ✅ Passed: {result.validation_result.passed_checks}")
        print(f"  ❌ Failed: {result.validation_result.failed_checks}")
        print(f"  ⚠️  Warnings: {result.validation_result.warning_checks}")
        
        # Discovery results
        if result.discovery_result:
            print(f"\n🔍 Discovery Results:")
            print(f"  Ports: {len(result.discovery_result.ports)}")
            print(f"  Processes: {len(result.discovery_result.processes)}")
            print(f"  Applications: {len(result.discovery_result.applications)}")
            
            if result.discovery_result.applications:
                print(f"\n  Detected Applications:")
                for app in result.discovery_result.applications[:5]:
                    print(f"    - {app.name} (confidence: {app.confidence:.0%})")
        
        # Classification
        if result.classification:
            print(f"\n🏷️  Classification:")
            print(f"  Category: {result.classification.category.value}")
            print(f"  Confidence: {result.classification.confidence:.0%}")
        
        # Evaluation
        if result.evaluation:
            print(f"\n🎯 AI Evaluation:")
            print(f"  Overall Health: {result.evaluation.overall_health.upper()}")
            print(f"  Confidence: {result.evaluation.confidence:.0%}")
            
            if result.evaluation.critical_issues:
                print(f"\n  ⚠️  Critical Issues ({len(result.evaluation.critical_issues)}):")
                for issue in result.evaluation.critical_issues[:3]:
                    print(f"    - {issue}")
            
            if result.evaluation.recommendations:
                print(f"\n  💡 Recommendations ({len(result.evaluation.recommendations)}):")
                for rec in result.evaluation.recommendations[:3]:
                    print(f"    - {rec}")
        
        # Phase timings
        if result.phase_timings:
            print(f"\n⏱️  Phase Timings:")
            for phase, time in result.phase_timings.items():
                print(f"  {phase}: {time:.2f}s")
        
        print("\n" + "="*60)
    
    async def run(self):
        """Run the interactive CLI loop."""
        await self.initialize()
        
        print("\n" + "="*60)
        print("💬 Interactive Mode")
        print("="*60)
        print("\nEnter validation prompts (or 'quit' to exit)")
        print("\nExamples:")
        print("  • Validate VM at 192.168.1.100 with SSH user admin password secret")
        print("  • Check Oracle database at db.example.com port 1521 user system")
        print("  • Validate MongoDB at mongo-server:27017")
        print("\n" + "-"*60)
        
        while True:
            try:
                # Get user input
                prompt = input("\n🤖 Enter prompt: ").strip()
                
                if not prompt:
                    continue
                
                if prompt.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Execute validation
                await self.execute_validation(prompt)
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"Error in interactive loop: {e}", exc_info=True)
        
        # Cleanup
        if self.orchestrator:
            await self.orchestrator.cleanup()


async def main():
    """Main entry point."""
    cli = BeeAIInteractiveCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

# Made with Bob
