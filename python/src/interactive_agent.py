#!/usr/bin/env python3
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Interactive CLI for agentic validation workflow with Ollama support."""

import asyncio
import os
import sys
import json
import logging
from typing import Optional

from mcp_stdio_client import MCPStdioClient
from agents.orchestrator import ValidationOrchestrator
from agents.base import AgentConfig
from models import (
    ValidationRequest,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    ResourceType
)
from input_guardrails import InputGuardrails, GuardrailViolationError
from advanced_guardrails import AdvancedGuardrails, RateLimitConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InteractiveAgent:
    """Interactive agent that accepts natural language prompts."""
    
    def __init__(self, use_ollama: bool = True, enable_guardrails: bool = True):
        """Initialize interactive agent.
        
        Args:
            use_ollama: Use Ollama for local LLM (default: True)
            enable_guardrails: Enable input guardrails (default: True)
        """
        self.mcp_client: Optional[MCPStdioClient] = None
        self.orchestrator: Optional[ValidationOrchestrator] = None
        self.use_ollama = use_ollama
        self.enable_guardrails = enable_guardrails
        
        # Initialize guardrails
        if self.enable_guardrails:
            self.basic_guardrails = InputGuardrails(strict_mode=True)
            rate_config = RateLimitConfig(
                max_requests_per_minute=10,
                max_requests_per_hour=100,
                max_requests_per_day=1000
            )
            self.advanced_guardrails = AdvancedGuardrails(
                enable_rate_limiting=True,
                enable_content_filter=True,
                enable_behavioral_analysis=True,
                enable_encoding_validation=True,
                rate_limit_config=rate_config
            )
            logger.info("✅ Guardrails enabled")
        else:
            self.basic_guardrails = None
            self.advanced_guardrails = None
            logger.warning("⚠️  Guardrails disabled")
        
    async def start(self):
        """Start the interactive agent."""
        print("\n" + "="*70)
        print("🤖 AGENTIC VALIDATION WORKFLOW - Interactive Mode")
        print("="*70)
        
        # Connect to MCP server via stdio
        print(f"\n📡 Starting MCP server via stdio transport...")
        try:
            # Setup stdio client with cyberres-mcp server
            cyberres_mcp_dir = os.path.join(os.path.dirname(__file__), "..", "cyberres-mcp")
            server_env = os.environ.copy()
            server_env["MCP_TRANSPORT"] = "stdio"
            
            self.mcp_client = MCPStdioClient(
                server_command="uv",
                server_args=["--directory", cyberres_mcp_dir, "run", "cyberres-mcp"],
                server_env=server_env,
                timeout=30.0
            )
            await self.mcp_client.connect()
            print("✅ Connected to MCP server (stdio transport)")
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            print("\n💡 Make sure you're in the correct directory:")
            print("   cd python/src")
            print("   uv run python interactive_agent.py")
            return
        
        # Configure agent
        if self.use_ollama:
            print("\n🦙 Using Ollama (local LLM)")
            print("   Make sure Ollama is running: ollama serve")
            print("   Default model: llama3.2 (you can change this)")
            
            # Check if Ollama is available
            ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            # Set Ollama base URL for Pydantic AI
            os.environ["OLLAMA_BASE_URL"] = ollama_base_url
            
            agent_config = AgentConfig(
                model=f"ollama:{ollama_model}",
                temperature=0.7,
                max_tokens=4000
            )
        else:
            print("\n🌐 Using cloud LLM")
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print("⚠️  No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
                print("   Or use Ollama with --ollama flag")
                return
            agent_config = AgentConfig()
        
        # Create orchestrator
        self.orchestrator = ValidationOrchestrator(
            mcp_client=self.mcp_client,
            agent_config=agent_config,
            enable_discovery=True,
            enable_ai_evaluation=True
        )
        print("✅ Orchestrator initialized")
        
        # Start interactive loop
        await self.interactive_loop()
    
    async def interactive_loop(self):
        """Main interactive loop."""
        print("\n" + "="*70)
        print("📝 PROMPT EXAMPLES:")
        print("="*70)
        print("""
1. "Validate VM at 192.168.1.100 with user admin and password secret"

2. "Check Oracle database at db-server:1521 service ORCL 
    with db user system password oracle123
    and ssh user oracle password oracle123"

3. "Validate MongoDB at mongo-server:27017
    with mongo user admin password mongo123
    and ssh user ubuntu password ubuntu123"

Type 'help' for more examples, 'quit' to exit
""")
        
        while True:
            print("\n" + "-"*70)
            prompt = input("\n🎯 Enter your validation request (or 'quit'): ").strip()
            
            if not prompt:
                continue
            
            if prompt.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if prompt.lower() == 'help':
                self.show_help()
                continue
            
            # Parse prompt and execute
            await self.process_prompt(prompt)
    
    def show_help(self):
        """Show help information."""
        print("\n" + "="*70)
        print("📚 HELP - Prompt Format")
        print("="*70)
        print("""
BASIC FORMAT:
"Validate [resource_type] at [host] with [credentials]"

RESOURCE TYPES:
- VM / virtual machine / server
- Oracle / Oracle database / Oracle DB
- MongoDB / Mongo / Mongo database

CREDENTIALS:
- For VM: "user [username] password [password]"
- For VM with key: "user [username] key [path]"
- For Oracle: "db user [user] password [pass] and ssh user [user] password [pass]"
- For MongoDB: "mongo user [user] password [pass] and ssh user [user] password [pass]"

EXAMPLES:

1. VM Validation:
   "Validate VM at 192.168.1.100 with user admin password secret"
   "Check server at 10.0.0.5 with user ubuntu key ~/.ssh/id_rsa"

2. Oracle Database:
   "Validate Oracle at db-server:1521 service ORCL 
    with db user system password oracle123 
    and ssh user oracle password oracle123"

3. MongoDB:
   "Check MongoDB at mongo-server:27017 
    with mongo user admin password mongo123 
    and ssh user ubuntu password ubuntu123"

SHORTCUTS:
- Type 'help' to see this message
- Type 'quit' or 'exit' to quit
- Press Ctrl+C to interrupt

CONFIGURATION:
- MCP Server: stdio transport (subprocess)
- LLM: {llm_type}
- Discovery: Enabled
- AI Evaluation: Enabled
""".format(
            llm_type="Ollama (local)" if self.use_ollama else "Cloud API"
        ))
    
    async def process_prompt(self, prompt: str):
        """Process user prompt and execute validation.
        
        Args:
            prompt: Natural language validation request
        """
        print(f"\n🔍 Processing: {prompt}")
        
        try:
            # Validate input with guardrails
            if self.enable_guardrails and self.basic_guardrails and self.advanced_guardrails:
                print("🛡️  Running security checks...")
                
                # Layer 1: Basic guardrails
                try:
                    self.basic_guardrails.validate_and_raise(prompt)
                except GuardrailViolationError as e:
                    print(f"\n🚫 SECURITY VIOLATION DETECTED:\n")
                    print(str(e))
                    print("\n💡 Your input was blocked for security reasons.")
                    print("   Please review the violations above and try again.\n")
                    return
                
                # Layer 2: Advanced guardrails
                is_valid, violations, rate_msg = self.advanced_guardrails.validate(prompt)
                
                if rate_msg:
                    print(f"\n⏱️  RATE LIMIT: {rate_msg}\n")
                    return
                
                if not is_valid:
                    print(f"\n⚠️  ADVANCED SECURITY CHECK FAILED:\n")
                    for v in violations:
                        print(f"   - [{v.severity.value.upper()}] {v.message}")
                    print("\n💡 Please address the issues above and try again.\n")
                    return
                
                # Log warnings for non-blocking violations
                warning_violations = [v for v in violations if v.severity.name in ['MEDIUM', 'LOW']]
                if warning_violations:
                    print(f"\n⚠️  Warnings (non-blocking):")
                    for v in warning_violations:
                        print(f"   - {v.message}")
                    print()
                
                print("✅ Security checks passed\n")
            
            # Parse the prompt
            request = self.parse_prompt(prompt)
            
            if not request:
                print("❌ Could not parse the prompt. Type 'help' for examples.")
                return
            
            print(f"\n✅ Parsed request:")
            print(f"   Resource Type: {request.resource_info.resource_type.value}")
            print(f"   Host: {request.resource_info.host}")
            
            # Execute workflow
            print(f"\n🚀 Executing validation workflow...")
            print("   This may take 30-120 seconds...")
            
            result = await self.orchestrator.execute_workflow(request)
            
            # Display results
            self.display_results(result)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    def parse_prompt(self, prompt: str) -> Optional[ValidationRequest]:
        """Parse natural language prompt into ValidationRequest.
        
        Args:
            prompt: User prompt
        
        Returns:
            ValidationRequest or None if parsing fails
        """
        prompt_lower = prompt.lower()
        
        # Determine resource type
        if any(word in prompt_lower for word in ['oracle', 'oracle db', 'oracle database']):
            return self._parse_oracle_prompt(prompt)
        elif any(word in prompt_lower for word in ['mongodb', 'mongo']):
            return self._parse_mongodb_prompt(prompt)
        else:
            # Default to VM
            return self._parse_vm_prompt(prompt)
    
    def _parse_vm_prompt(self, prompt: str) -> Optional[ValidationRequest]:
        """Parse VM validation prompt."""
        import re
        
        # Extract host
        host_match = re.search(r'at\s+([^\s]+)', prompt)
        if not host_match:
            return None
        host = host_match.group(1)
        
        # Extract user
        user_match = re.search(r'user\s+(\w+)', prompt)
        if not user_match:
            return None
        user = user_match.group(1)
        
        # Extract password or key
        password_match = re.search(r'password\s+(\S+)', prompt)
        key_match = re.search(r'key\s+([^\s]+)', prompt)
        
        if password_match:
            password = password_match.group(1)
            key_path = None
        elif key_match:
            password = None
            key_path = key_match.group(1)
        else:
            return None
        
        return ValidationRequest(
            resource_info=VMResourceInfo(
                host=host,
                ssh_user=user,
                ssh_password=password,
                ssh_key_path=key_path
            ),
            auto_discover=True
        )
    
    def _parse_oracle_prompt(self, prompt: str) -> Optional[ValidationRequest]:
        """Parse Oracle database validation prompt."""
        import re
        
        # Extract host and port
        host_match = re.search(r'at\s+([^:\s]+)(?::(\d+))?', prompt)
        if not host_match:
            return None
        host = host_match.group(1)
        port = int(host_match.group(2)) if host_match.group(2) else 1521
        
        # Extract service name
        service_match = re.search(r'service\s+(\w+)', prompt)
        service_name = service_match.group(1) if service_match else None
        
        # Extract DB credentials
        db_user_match = re.search(r'db user\s+(\w+)', prompt)
        db_pass_match = re.search(r'db.*?password\s+(\S+)', prompt)
        
        if not db_user_match or not db_pass_match:
            return None
        
        # Extract SSH credentials
        ssh_user_match = re.search(r'ssh user\s+(\w+)', prompt)
        ssh_pass_match = re.search(r'ssh.*?password\s+(\S+)', prompt)
        
        return ValidationRequest(
            resource_info=OracleDBResourceInfo(
                host=host,
                port=port,
                service_name=service_name,
                db_user=db_user_match.group(1),
                db_password=db_pass_match.group(1),
                ssh_user=ssh_user_match.group(1) if ssh_user_match else None,
                ssh_password=ssh_pass_match.group(1) if ssh_pass_match else None
            ),
            auto_discover=True
        )
    
    def _parse_mongodb_prompt(self, prompt: str) -> Optional[ValidationRequest]:
        """Parse MongoDB validation prompt."""
        import re
        
        # Extract host and port
        host_match = re.search(r'at\s+([^:\s]+)(?::(\d+))?', prompt)
        if not host_match:
            return None
        host = host_match.group(1)
        port = int(host_match.group(2)) if host_match.group(2) else 27017
        
        # Extract Mongo credentials
        mongo_user_match = re.search(r'mongo user\s+(\w+)', prompt)
        mongo_pass_match = re.search(r'mongo.*?password\s+(\S+)', prompt)
        
        # Extract SSH credentials
        ssh_user_match = re.search(r'ssh user\s+(\w+)', prompt)
        ssh_pass_match = re.search(r'ssh.*?password\s+(\S+)', prompt)
        
        return ValidationRequest(
            resource_info=MongoDBResourceInfo(
                host=host,
                port=port,
                mongo_user=mongo_user_match.group(1) if mongo_user_match else None,
                mongo_password=mongo_pass_match.group(1) if mongo_pass_match else None,
                ssh_user=ssh_user_match.group(1) if ssh_user_match else None,
                ssh_password=ssh_pass_match.group(1) if ssh_pass_match else None
            ),
            auto_discover=True
        )
    
    def display_results(self, result):
        """Display workflow results.
        
        Args:
            result: WorkflowResult
        """
        print("\n" + "="*70)
        print("📊 VALIDATION RESULTS")
        print("="*70)
        
        print(f"\n⏱️  Execution Time: {result.execution_time_seconds:.2f}s")
        print(f"📈 Workflow Status: {result.workflow_status.upper()}")
        
        # Discovery results
        if result.discovery_result:
            print(f"\n🔍 WORKLOAD DISCOVERY:")
            print(f"   Ports Found: {len(result.discovery_result.ports)}")
            print(f"   Processes Found: {len(result.discovery_result.processes)}")
            print(f"   Applications Detected: {len(result.discovery_result.applications)}")
            
            if result.discovery_result.applications:
                print(f"\n   📱 Detected Applications:")
                for app in result.discovery_result.applications[:5]:
                    print(f"      • {app.name} (confidence: {app.confidence:.0%})")
        
        # Classification
        if result.classification:
            print(f"\n🏷️  RESOURCE CLASSIFICATION:")
            print(f"   Category: {result.classification.category.value}")
            print(f"   Confidence: {result.classification.confidence:.0%}")
            if result.classification.primary_application:
                print(f"   Primary App: {result.classification.primary_application.name}")
        
        # Validation plan
        if result.validation_plan:
            print(f"\n📋 VALIDATION PLAN:")
            print(f"   Strategy: {result.validation_plan.strategy_name}")
            print(f"   Total Checks: {len(result.validation_plan.checks)}")
            print(f"   Priority Checks: {len(result.validation_plan.get_priority_checks())}")
        
        # Validation results
        print(f"\n✅ VALIDATION RESULTS:")
        print(f"   Overall Score: {result.validation_result.score}/100")
        print(f"   Status: {result.validation_result.overall_status.value}")
        print(f"   ✓ Passed: {result.validation_result.passed_checks}")
        print(f"   ✗ Failed: {result.validation_result.failed_checks}")
        print(f"   ⚠ Warnings: {result.validation_result.warning_checks}")
        
        # Show failed checks
        if result.validation_result.failed_checks > 0:
            print(f"\n   Failed Checks:")
            for check in result.validation_result.checks:
                if check.status.value == "FAIL":
                    print(f"      ✗ {check.check_name}: {check.message}")
        
        # AI Evaluation
        if result.evaluation:
            print(f"\n🤖 AI EVALUATION:")
            print(f"   Overall Health: {result.evaluation.overall_health.upper()}")
            print(f"   Confidence: {result.evaluation.confidence:.0%}")
            print(f"   Critical Issues: {len(result.evaluation.critical_issues)}")
            print(f"   Warnings: {len(result.evaluation.warnings)}")
            
            if result.evaluation.summary:
                print(f"\n   Summary:")
                print(f"   {result.evaluation.summary}")
            
            if result.evaluation.recommendations:
                print(f"\n   💡 Top Recommendations:")
                for i, rec in enumerate(result.evaluation.recommendations[:5], 1):
                    print(f"      {i}. {rec}")
        
        # Errors
        if result.errors:
            print(f"\n⚠️  ERRORS:")
            for error in result.errors:
                print(f"   • {error}")
        
        print("\n" + "="*70)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.mcp_client:
            await self.mcp_client.disconnect()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Interactive agentic validation workflow"
    )
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:3000",
        help="MCP server URL (default: http://localhost:3000)"
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        default=True,
        help="Use Ollama for local LLM (default: True)"
    )
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Use cloud LLM instead of Ollama"
    )
    parser.add_argument(
        "--ollama-model",
        default="llama3.2",
        help="Ollama model to use (default: llama3.2)"
    )
    
    args = parser.parse_args()
    
    # Set Ollama model
    if args.ollama_model:
        os.environ["OLLAMA_MODEL"] = args.ollama_model
    
    use_ollama = not args.cloud
    
    agent = InteractiveAgent(
        use_ollama=use_ollama
    )
    
    try:
        await agent.start()
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)


# Made with Bob