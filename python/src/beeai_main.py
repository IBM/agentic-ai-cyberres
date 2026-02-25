#!/usr/bin/env python3
"""
BeeAI-powered Recovery Validation Agent
Complete migration from Pydantic AI to BeeAI Framework
"""

import asyncio
import os
import sys
from typing import Optional
from dotenv import load_dotenv

# BeeAI Framework imports
from beeai_framework.adapters.ollama import OllamaChatModel
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.mcp import MCPClient, MCPTool
from beeai_framework.agents.types import AgentMeta

# Local imports
from models import ResourceInfo, ValidationResult
from email_service import EmailService
from credentials import CredentialsManager

# Load environment variables
load_dotenv()


class BeeAIValidationOrchestrator:
    """
    Main orchestrator using BeeAI framework for recovery validation.
    Coordinates discovery, validation, and evaluation agents.
    """
    
    def __init__(self):
        """Initialize the BeeAI orchestrator with all components."""
        self.llm_backend = os.getenv("LLM_BACKEND", "ollama")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
        
        # Initialize credentials manager
        self.credentials_manager = CredentialsManager()
        
        # Initialize email service
        self.email_service = EmailService()
        
        # Initialize BeeAI components
        self._init_beeai_components()
    
    def _init_beeai_components(self):
        """Initialize BeeAI LLM, memory, and MCP tools."""
        print("🚀 Initializing BeeAI Framework...")
        
        # Create Ollama chat model
        self.llm = OllamaChatModel(
            model_id=self.ollama_model,
            parameters={
                "temperature": 0.1,
                "num_ctx": 8192,
            },
            base_url=self.ollama_base_url
        )
        print(f"✅ LLM initialized: {self.ollama_model}")
        
        # Create memory for conversation history
        self.memory = UnconstrainedMemory()
        print("✅ Memory initialized")
        
        # Initialize MCP client and tools
        self._init_mcp_tools()
    
    def _init_mcp_tools(self):
        """Initialize MCP client and discover available tools."""
        print(f"🔧 Connecting to MCP server: {self.mcp_server_url}")
        
        try:
            # Create MCP client
            self.mcp_client = MCPClient(
                server_url=self.mcp_server_url,
                timeout=30
            )
            
            # Discover available tools
            self.mcp_tools = []
            available_tools = self.mcp_client.list_tools()
            
            for tool_info in available_tools:
                mcp_tool = MCPTool(
                    client=self.mcp_client,
                    name=tool_info["name"],
                    description=tool_info["description"],
                    input_schema=tool_info.get("inputSchema", {})
                )
                self.mcp_tools.append(mcp_tool)
            
            print(f"✅ Discovered {len(self.mcp_tools)} MCP tools")
            
            # Print tool categories
            tool_categories = {}
            for tool in self.mcp_tools:
                category = tool.name.split('_')[0] if '_' in tool.name else 'other'
                tool_categories[category] = tool_categories.get(category, 0) + 1
            
            print("📦 Tool categories:")
            for category, count in sorted(tool_categories.items()):
                print(f"   - {category}: {count} tools")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not connect to MCP server: {e}")
            print("   Continuing without MCP tools...")
            self.mcp_tools = []
    
    def _create_discovery_agent(self) -> ReActAgent:
        """Create a BeeAI agent for resource discovery."""
        meta = AgentMeta(
            name="DiscoveryAgent",
            description="Discovers workloads and resources on recovered systems",
            extra_description=(
                "I analyze recovered systems to identify:\n"
                "- Operating system and version\n"
                "- Running processes and services\n"
                "- Network ports and connections\n"
                "- Installed applications\n"
                "- Database instances (Oracle, MongoDB)\n"
                "I use MCP tools to gather comprehensive system information."
            )
        )
        
        # Filter tools relevant for discovery
        discovery_tools = [
            tool for tool in self.mcp_tools
            if any(keyword in tool.name.lower() for keyword in [
                'discover', 'scan', 'detect', 'list', 'get_info'
            ])
        ]
        
        agent = ReActAgent(
            llm=self.llm,
            tools=discovery_tools,
            memory=UnconstrainedMemory(),  # Separate memory for discovery
            meta=meta,
            stream=False
        )
        
        return agent
    
    def _create_validation_agent(self) -> ReActAgent:
        """Create a BeeAI agent for resource validation."""
        meta = AgentMeta(
            name="ValidationAgent",
            description="Validates recovered resources against acceptance criteria",
            extra_description=(
                "I validate recovered resources by:\n"
                "- Checking VM connectivity and accessibility\n"
                "- Verifying database availability and integrity\n"
                "- Testing application functionality\n"
                "- Validating network configurations\n"
                "- Ensuring data consistency\n"
                "I use MCP tools to perform comprehensive validation checks."
            )
        )
        
        # Filter tools relevant for validation
        validation_tools = [
            tool for tool in self.mcp_tools
            if any(keyword in tool.name.lower() for keyword in [
                'validate', 'check', 'test', 'verify', 'ping', 'connect'
            ])
        ]
        
        agent = ReActAgent(
            llm=self.llm,
            tools=validation_tools,
            memory=UnconstrainedMemory(),  # Separate memory for validation
            meta=meta,
            stream=False
        )
        
        return agent
    
    def _create_evaluation_agent(self) -> ReActAgent:
        """Create a BeeAI agent for result evaluation."""
        meta = AgentMeta(
            name="EvaluationAgent",
            description="Evaluates validation results and generates comprehensive reports",
            extra_description=(
                "I analyze validation results to:\n"
                "- Assess overall recovery success\n"
                "- Identify critical issues and failures\n"
                "- Provide actionable recommendations\n"
                "- Generate detailed reports\n"
                "- Determine recovery confidence levels\n"
                "I use intelligent reasoning to provide insights and guidance."
            )
        )
        
        # Evaluation agent uses minimal tools, focuses on analysis
        agent = ReActAgent(
            llm=self.llm,
            tools=[],  # No tools needed for evaluation
            memory=UnconstrainedMemory(),  # Separate memory for evaluation
            meta=meta,
            stream=False
        )
        
        return agent
    
    async def validate_resource(
        self,
        resource_info: ResourceInfo,
        auto_discover: bool = True
    ) -> ValidationResult:
        """
        Validate a recovered resource using BeeAI agents.
        
        Args:
            resource_info: Information about the resource to validate
            auto_discover: Whether to auto-discover workloads
            
        Returns:
            ValidationResult with comprehensive validation data
        """
        print(f"\n{'='*80}")
        print(f"🎯 Starting BeeAI Validation for: {resource_info.category} at {resource_info.ip_address}")
        print(f"{'='*80}\n")
        
        result = ValidationResult(
            resource_info=resource_info,
            status="in_progress",
            checks_passed=0,
            checks_failed=0,
            checks_total=0
        )
        
        try:
            # Phase 1: Discovery
            if auto_discover:
                print("📡 Phase 1: Discovery")
                print("-" * 80)
                discovery_agent = self._create_discovery_agent()
                
                discovery_prompt = f"""
                Discover workloads on the recovered {resource_info.category} at {resource_info.ip_address}.
                
                Use available MCP tools to:
                1. Detect the operating system
                2. Scan for running processes
                3. Identify open network ports
                4. Discover installed applications
                5. Find database instances
                
                Provide a comprehensive discovery report.
                """
                
                discovery_result = await discovery_agent.run(discovery_prompt)
                result.discovery_data = {
                    "output": discovery_result.output,
                    "discovered_workloads": []  # Parse from output
                }
                print(f"✅ Discovery complete\n")
            
            # Phase 2: Validation
            print("🔍 Phase 2: Validation")
            print("-" * 80)
            validation_agent = self._create_validation_agent()
            
            validation_prompt = f"""
            Validate the recovered {resource_info.category} at {resource_info.ip_address}.
            
            Perform the following validation checks:
            1. Verify system accessibility
            2. Check service availability
            3. Validate network connectivity
            4. Test application functionality
            5. Verify data integrity
            
            For each check, report:
            - Check name
            - Status (passed/failed)
            - Details
            - Any issues found
            
            Provide a structured validation report.
            """
            
            validation_result = await validation_agent.run(validation_prompt)
            
            # Parse validation results
            result.validation_checks = self._parse_validation_output(
                validation_result.output
            )
            result.checks_total = len(result.validation_checks)
            result.checks_passed = sum(
                1 for check in result.validation_checks if check.get("status") == "passed"
            )
            result.checks_failed = result.checks_total - result.checks_passed
            
            print(f"✅ Validation complete: {result.checks_passed}/{result.checks_total} checks passed\n")
            
            # Phase 3: Evaluation
            print("📊 Phase 3: Evaluation")
            print("-" * 80)
            evaluation_agent = self._create_evaluation_agent()
            
            evaluation_prompt = f"""
            Evaluate the validation results for {resource_info.category} at {resource_info.ip_address}.
            
            Validation Summary:
            - Total checks: {result.checks_total}
            - Passed: {result.checks_passed}
            - Failed: {result.checks_failed}
            
            Validation Details:
            {self._format_checks_for_evaluation(result.validation_checks)}
            
            Provide:
            1. Overall assessment (success/partial/failure)
            2. Critical issues identified
            3. Recommendations for remediation
            4. Recovery confidence level (0-100%)
            5. Next steps
            
            Be specific and actionable in your recommendations.
            """
            
            evaluation_result = await evaluation_agent.run(evaluation_prompt)
            result.evaluation_summary = evaluation_result.output
            
            # Determine final status
            if result.checks_failed == 0:
                result.status = "success"
            elif result.checks_passed > result.checks_failed:
                result.status = "partial"
            else:
                result.status = "failure"
            
            print(f"✅ Evaluation complete: {result.status}\n")
            
        except Exception as e:
            print(f"❌ Error during validation: {e}")
            result.status = "error"
            result.error_message = str(e)
        
        return result
    
    def _parse_validation_output(self, output: str) -> list:
        """Parse validation output into structured checks."""
        # Simple parsing - in production, use more sophisticated parsing
        checks = []
        
        # Look for check patterns in output
        lines = output.split('\n')
        current_check = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect check start
            if any(keyword in line.lower() for keyword in ['check:', 'test:', 'verify:']):
                if current_check:
                    checks.append(current_check)
                current_check = {
                    "name": line,
                    "status": "unknown",
                    "details": ""
                }
            elif current_check:
                # Look for status indicators
                if any(word in line.lower() for word in ['passed', 'success', '✓', '✅']):
                    current_check["status"] = "passed"
                elif any(word in line.lower() for word in ['failed', 'error', '✗', '❌']):
                    current_check["status"] = "failed"
                
                current_check["details"] += line + "\n"
        
        if current_check:
            checks.append(current_check)
        
        # If no checks found, create a default one
        if not checks:
            checks.append({
                "name": "Overall Validation",
                "status": "passed" if "success" in output.lower() else "unknown",
                "details": output
            })
        
        return checks
    
    def _format_checks_for_evaluation(self, checks: list) -> str:
        """Format validation checks for evaluation prompt."""
        formatted = []
        for i, check in enumerate(checks, 1):
            formatted.append(f"{i}. {check['name']}")
            formatted.append(f"   Status: {check['status']}")
            formatted.append(f"   Details: {check.get('details', 'N/A')[:200]}")
            formatted.append("")
        return "\n".join(formatted)
    
    async def send_report(self, result: ValidationResult):
        """Send validation report via email."""
        try:
            print("\n📧 Sending email report...")
            await self.email_service.send_validation_report(result)
            print("✅ Email sent successfully")
        except Exception as e:
            print(f"⚠️  Failed to send email: {e}")
    
    async def interactive_mode(self):
        """Run in interactive conversational mode."""
        print("\n" + "="*80)
        print("🤖 BeeAI Recovery Validation Agent - Interactive Mode")
        print("="*80)
        print("\nYou can say things like:")
        print("  - 'I have recovered a VM at 192.168.1.100, please validate it'")
        print("  - 'Validate the Oracle database at 10.0.0.50'")
        print("  - 'Check the MongoDB instance at db.example.com'")
        print("  - 'exit' to quit")
        print("\n" + "="*80 + "\n")
        
        # Create a conversational agent
        conversation_agent = ReActAgent(
            llm=self.llm,
            tools=self.mcp_tools,
            memory=self.memory,  # Use shared memory for conversation
            meta=AgentMeta(
                name="ValidationOrchestrator",
                description="Orchestrates recovery validation workflows",
                extra_description=(
                    "I help you validate recovered IT resources. "
                    "Tell me what you've recovered and I'll validate it for you."
                )
            ),
            stream=True
        )
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                print("\n🤖 Agent: ", end="", flush=True)
                
                # Run agent with streaming
                result = await conversation_agent.run(user_input)
                print(result.output)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


async def main():
    """Main entry point."""
    orchestrator = BeeAIValidationOrchestrator()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # CLI mode with arguments
        if sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
            await orchestrator.interactive_mode()
        else:
            print("Usage: python beeai_main.py [--interactive|-i]")
            sys.exit(1)
    else:
        # Default: interactive mode
        await orchestrator.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
