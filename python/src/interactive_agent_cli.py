#!/usr/bin/env python3
"""
Interactive CLI for testing enhanced agents manually.

This tool provides an interactive command-line interface to test
the Phase 2 enhanced agents with your own prompts and inputs.
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from models import (
    VMResourceInfo, ResourceType, WorkloadDiscoveryResult,
    PortInfo, ProcessInfo, ApplicationDetection,
    ResourceValidationResult, CheckResult, ValidationStatus
)
from mcp_stdio_client import MCPStdioClient
from tool_coordinator import ToolCoordinator
from state_manager import StateManager
from feature_flags import FeatureFlags
from agents.discovery_agent_enhanced import EnhancedDiscoveryAgent
from agents.classification_agent import ClassificationAgent
from agents.reporting_agent import ReportingAgent
from agents.base import AgentConfig


class InteractiveAgentCLI:
    """Interactive CLI for testing agents."""
    
    def __init__(self):
        """Initialize CLI."""
        self.mcp_client: Optional[MCPStdioClient] = None
        self.tool_coordinator: Optional[ToolCoordinator] = None
        self.state_manager: Optional[StateManager] = None
        self.feature_flags: Optional[FeatureFlags] = None
        self.agent_config: Optional[AgentConfig] = None
        
        self.discovery_agent: Optional[EnhancedDiscoveryAgent] = None
        self.classification_agent: Optional[ClassificationAgent] = None
        self.reporting_agent: Optional[ReportingAgent] = None
        
        self.current_discovery: Optional[WorkloadDiscoveryResult] = None
        self.current_classification = None
        self.current_validation = None
    
    def print_banner(self):
        """Print welcome banner."""
        print("\n" + "=" * 80)
        print("🤖 Interactive Agent CLI - Phase 2 Enhanced Agents")
        print("=" * 80)
        print("\nTest the enhanced agentic workflow with your own prompts!")
        print("\nAvailable Commands:")
        print("  1. setup     - Configure agents (model, features)")
        print("  2. discover  - Run discovery on a resource")
        print("  3. classify  - Classify discovered workload")
        print("  4. report    - Generate validation report")
        print("  5. workflow  - Run complete workflow")
        print("  6. status    - Show current state")
        print("  7. help      - Show this help")
        print("  8. quit      - Exit")
        print("=" * 80 + "\n")
    
    async def setup(self):
        """Setup agents with user configuration."""
        print("\n📋 Agent Setup")
        print("-" * 80)
        
        # Choose model
        print("\nChoose LLM Model:")
        print("  1. OpenAI GPT-4 (cloud, best quality)")
        print("  2. Ollama Llama 3 (local, free)")
        print("  3. Ollama Mistral (local, fast)")
        print("  4. Custom")
        
        choice = input("\nEnter choice (1-4) [2]: ").strip() or "2"
        
        model_map = {
            "1": "openai:gpt-4",
            "2": "ollama:llama3",
            "3": "ollama:mistral"
        }
        
        if choice in model_map:
            model = model_map[choice]
        else:
            model = input("Enter model string (e.g., ollama:llama3): ").strip()
        
        print(f"\n✅ Selected model: {model}")
        
        # Feature flags
        print("\n🚩 Feature Flags:")
        use_coordinator = input("  Use tool coordinator? (y/n) [y]: ").strip().lower() != 'n'
        use_parallel = input("  Use parallel execution? (y/n) [y]: ").strip().lower() != 'n'
        use_ai_classification = input("  Use AI classification? (y/n) [y]: ").strip().lower() != 'n'
        use_ai_reporting = input("  Use AI reporting? (y/n) [y]: ").strip().lower() != 'n'
        
        # Initialize components
        print("\n⚙️  Initializing components...")
        
        self.tool_coordinator = ToolCoordinator(cache_ttl=300)
        self.state_manager = StateManager(state_file="interactive_state.json")
        self.feature_flags = FeatureFlags({
            "use_tool_coordinator": use_coordinator,
            "parallel_tool_execution": use_parallel,
            "ai_classification": use_ai_classification,
            "ai_reporting": use_ai_reporting
        })
        
        self.agent_config = AgentConfig(
            model=model,
            temperature=0.1
        )
        
        # Initialize MCP client
        print("  Connecting to MCP server...")
        self.mcp_client = MCPStdioClient(
            server_script_path="../cyberres-mcp/src/cyberres_mcp/server.py"
        )
        await self.mcp_client.connect()
        print("  ✅ MCP client connected")
        
        # Create agents
        print("  Creating agents...")
        self.discovery_agent = EnhancedDiscoveryAgent(
            mcp_client=self.mcp_client,
            config=self.agent_config,
            tool_coordinator=self.tool_coordinator,
            state_manager=self.state_manager,
            feature_flags=self.feature_flags
        )
        
        self.classification_agent = ClassificationAgent(
            config=self.agent_config,
            feature_flags=self.feature_flags
        )
        
        self.reporting_agent = ReportingAgent(
            config=self.agent_config,
            feature_flags=self.feature_flags
        )
        
        print("\n✅ Setup complete!")
        print(f"   Model: {model}")
        print(f"   Tool Coordinator: {'✅' if use_coordinator else '❌'}")
        print(f"   Parallel Execution: {'✅' if use_parallel else '❌'}")
        print(f"   AI Classification: {'✅' if use_ai_classification else '❌'}")
        print(f"   AI Reporting: {'✅' if use_ai_reporting else '❌'}")
    
    async def discover(self):
        """Run discovery on a resource."""
        if not self.discovery_agent:
            print("\n❌ Please run 'setup' first!")
            return
        
        print("\n🔍 Discovery Agent")
        print("-" * 80)
        
        # Get resource details
        host = input("\nEnter hostname: ").strip()
        ssh_user = input("Enter SSH user [admin]: ").strip() or "admin"
        ssh_port = input("Enter SSH port [22]: ").strip() or "22"
        
        resource = VMResourceInfo(
            host=host,
            resource_type=ResourceType.VM,
            ssh_user=ssh_user,
            ssh_port=int(ssh_port)
        )
        
        print(f"\n🚀 Running discovery on {host}...")
        print("   This will:")
        print("   - Create AI-powered discovery plan")
        print("   - Scan ports and processes")
        print("   - Detect applications")
        print("   - Use tool coordinator for retry/cache")
        
        workflow_id = f"interactive_{int(datetime.now().timestamp())}"
        
        try:
            self.current_discovery = await self.discovery_agent.discover(
                resource=resource,
                workflow_id=workflow_id
            )
            
            print("\n✅ Discovery completed!")
            print(f"   - Workflow ID: {workflow_id}")
            print(f"   - Ports found: {len(self.current_discovery.ports)}")
            print(f"   - Processes found: {len(self.current_discovery.processes)}")
            print(f"   - Applications detected: {len(self.current_discovery.applications)}")
            
            if self.current_discovery.applications:
                print("\n   Detected Applications:")
                for app in self.current_discovery.applications[:5]:
                    print(f"     - {app.name} (confidence: {app.confidence:.0%})")
            
            # Show execution history
            history = self.discovery_agent.get_execution_history()
            if history:
                print(f"\n   Execution History: {len(history)} actions")
                for record in history[-3:]:
                    print(f"     - {record['action']}")
        
        except Exception as e:
            print(f"\n❌ Discovery failed: {e}")
    
    async def classify(self):
        """Classify discovered workload."""
        if not self.classification_agent:
            print("\n❌ Please run 'setup' first!")
            return
        
        if not self.current_discovery:
            print("\n❌ Please run 'discover' first!")
            return
        
        print("\n🏷️  Classification Agent")
        print("-" * 80)
        
        print(f"\n🚀 Classifying {self.current_discovery.host}...")
        print("   This will:")
        print("   - Analyze ports, processes, and applications")
        print("   - Use AI to determine resource category")
        print("   - Provide confidence score and reasoning")
        
        try:
            self.current_classification = await self.classification_agent.classify(
                self.current_discovery
            )
            
            print("\n✅ Classification completed!")
            print(f"   - Category: {self.current_classification.category.value}")
            print(f"   - Confidence: {self.current_classification.confidence:.0%}")
            
            if self.current_classification.primary_application:
                print(f"   - Primary App: {self.current_classification.primary_application.name}")
            
            if self.current_classification.secondary_applications:
                print(f"   - Secondary Apps: {len(self.current_classification.secondary_applications)}")
            
            print(f"\n   Reasoning:")
            print(f"   {self.current_classification.reasoning}")
            
            if self.current_classification.recommended_validations:
                print(f"\n   Recommended Validations:")
                for val in self.current_classification.recommended_validations:
                    print(f"     - {val}")
        
        except Exception as e:
            print(f"\n❌ Classification failed: {e}")
    
    async def report(self):
        """Generate validation report."""
        if not self.reporting_agent:
            print("\n❌ Please run 'setup' first!")
            return
        
        print("\n📊 Reporting Agent")
        print("-" * 80)
        
        # Create mock validation result
        print("\n📝 Creating validation result...")
        host = self.current_discovery.host if self.current_discovery else "test-server"
        
        validation_result = ResourceValidationResult(
            resource_type=ResourceType.VM,
            resource_host=host,
            overall_status=ValidationStatus.PASS,
            score=85,
            checks=[
                CheckResult(
                    check_id="net_001",
                    check_name="Network Connectivity",
                    status=ValidationStatus.PASS,
                    message="All ports accessible"
                ),
                CheckResult(
                    check_id="sys_001",
                    check_name="System Resources",
                    status=ValidationStatus.WARNING,
                    message="CPU usage at 80%"
                ),
            ],
            execution_time_seconds=12.5
        )
        
        print(f"\n🚀 Generating report for {host}...")
        print("   This will:")
        print("   - Create executive summary")
        print("   - Identify key findings")
        print("   - Provide recommendations")
        print("   - Format in professional markdown")
        
        try:
            report = await self.reporting_agent.generate_report(
                validation_result=validation_result,
                discovery_result=self.current_discovery,
                classification=self.current_classification,
                format="markdown"
            )
            
            print("\n✅ Report generated!")
            print(f"   - Length: {len(report)} characters")
            
            # Save report
            report_file = f"interactive_report_{int(datetime.now().timestamp())}.md"
            with open(report_file, "w") as f:
                f.write(report)
            print(f"   - Saved to: {report_file}")
            
            # Show preview
            print("\n📄 Report Preview (first 500 chars):")
            print("-" * 80)
            print(report[:500] + "...")
            print("-" * 80)
            
            view = input("\nView full report? (y/n) [n]: ").strip().lower()
            if view == 'y':
                print("\n" + "=" * 80)
                print(report)
                print("=" * 80)
        
        except Exception as e:
            print(f"\n❌ Report generation failed: {e}")
    
    async def workflow(self):
        """Run complete workflow."""
        print("\n🔄 Complete Workflow")
        print("-" * 80)
        print("\nThis will run: Discovery → Classification → Report")
        
        confirm = input("\nContinue? (y/n) [y]: ").strip().lower()
        if confirm == 'n':
            return
        
        # Discovery
        await self.discover()
        if not self.current_discovery:
            return
        
        # Classification
        await self.classify()
        if not self.current_classification:
            return
        
        # Report
        await self.report()
        
        print("\n✅ Complete workflow finished!")
    
    def status(self):
        """Show current status."""
        print("\n📊 Current Status")
        print("-" * 80)
        
        print(f"\nAgents Initialized: {'✅' if self.discovery_agent else '❌'}")
        if self.agent_config:
            print(f"Model: {self.agent_config.model}")
        
        if self.feature_flags:
            print(f"\nFeature Flags:")
            for flag in ["use_tool_coordinator", "parallel_tool_execution", 
                        "ai_classification", "ai_reporting"]:
                status = "✅" if self.feature_flags.is_enabled(flag) else "❌"
                print(f"  {flag}: {status}")
        
        print(f"\nDiscovery Result: {'✅' if self.current_discovery else '❌'}")
        if self.current_discovery:
            print(f"  Host: {self.current_discovery.host}")
            print(f"  Ports: {len(self.current_discovery.ports)}")
            print(f"  Applications: {len(self.current_discovery.applications)}")
        
        print(f"\nClassification: {'✅' if self.current_classification else '❌'}")
        if self.current_classification:
            print(f"  Category: {self.current_classification.category.value}")
            print(f"  Confidence: {self.current_classification.confidence:.0%}")
    
    def help(self):
        """Show help."""
        self.print_banner()
    
    async def run(self):
        """Run interactive CLI."""
        self.print_banner()
        
        while True:
            try:
                command = input("\n🤖 Enter command (or 'help'): ").strip().lower()
                
                if command in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                elif command == 'setup':
                    await self.setup()
                
                elif command == 'discover':
                    await self.discover()
                
                elif command == 'classify':
                    await self.classify()
                
                elif command == 'report':
                    await self.report()
                
                elif command == 'workflow':
                    await self.workflow()
                
                elif command == 'status':
                    self.status()
                
                elif command == 'help':
                    self.help()
                
                else:
                    print(f"\n❌ Unknown command: {command}")
                    print("   Type 'help' for available commands")
            
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Cleanup
        if self.mcp_client:
            await self.mcp_client.disconnect()
            print("✅ MCP client disconnected")


async def main():
    """Main entry point."""
    cli = InteractiveAgentCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)

# Made with Bob
