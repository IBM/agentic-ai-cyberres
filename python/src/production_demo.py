#!/usr/bin/env python3
"""
Production-Style Demo - Natural Language Prompt to Complete Workflow

This demo shows how to use the agentic workflow in production:
1. Start the system
2. Give it a natural language prompt
3. Watch it execute the complete workflow automatically

Usage:
    python production_demo.py "Validate the Oracle database at db-server-01"
    python production_demo.py "Check the web server at web-server-01"
    python production_demo.py "Discover and validate app-server-01"
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    ValidationRequest,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    ResourceType
)
from agents.orchestrator import ValidationOrchestrator
from agents.base import AgentConfig
from mcp_stdio_client import MCPStdioClient
from report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionDemo:
    """Production-style demo that accepts natural language prompts."""
    
    def __init__(self, model: str = "ollama:llama3"):
        """Initialize demo.
        
        Args:
            model: LLM model to use (ollama:llama3, openai:gpt-4, etc.)
        """
        self.model = model
        self.mcp_client: Optional[MCPStdioClient] = None
        self.orchestrator: Optional[ValidationOrchestrator] = None
        self.report_generator = ReportGenerator()
        
    async def initialize(self):
        """Initialize the system."""
        print("\n" + "="*80)
        print("🚀 PRODUCTION DEMO - Agentic Validation Workflow")
        print("="*80)
        print(f"\n⚙️  Initializing system with model: {self.model}")
        
        # 1. Connect to MCP server
        print("\n📡 Connecting to MCP server...")
        self.mcp_client = MCPStdioClient(
            server_script_path="../cyberres-mcp/src/cyberres_mcp/server.py"
        )
        await self.mcp_client.connect()
        print("   ✅ MCP server connected")
        
        # 2. Initialize agent config
        print("\n🤖 Initializing AI agents...")
        agent_config = AgentConfig(
            model=self.model,
            temperature=0.1,
            max_tokens=4000
        )
        
        # 3. Create orchestrator
        self.orchestrator = ValidationOrchestrator(
            mcp_client=self.mcp_client,
            agent_config=agent_config,
            enable_discovery=True,
            enable_ai_evaluation=True
        )
        print("   ✅ Orchestrator initialized")
        print("   ✅ Discovery agent ready")
        print("   ✅ Validation agent ready")
        print("   ✅ Evaluation agent ready")
        
        print("\n✅ System ready!")
        
    async def parse_prompt(self, prompt: str, email: Optional[str] = None) -> ValidationRequest:
        """Parse natural language prompt into validation request.
        
        Args:
            prompt: Natural language prompt
            email: Optional email address for report delivery
            
        Returns:
            ValidationRequest
        """
        print("\n" + "="*80)
        print("📝 PARSING PROMPT")
        print("="*80)
        print(f"\nPrompt: \"{prompt}\"")
        
        # Simple parsing logic (in production, you'd use LLM for this)
        prompt_lower = prompt.lower()
        
        # Extract email address if not provided
        if not email:
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, prompt)
            if email_match:
                email = email_match.group(0)
                print(f"   📧 Email extracted: {email}")
        
        # Extract hostname
        hostname = None
        words = prompt.split()
        for i, word in enumerate(words):
            if word in ["at", "on", "server", "host"]:
                if i + 1 < len(words):
                    hostname = words[i + 1].strip('.,;:')
                    break
        
        if not hostname:
            # Try to find something that looks like a hostname
            for word in words:
                if '-' in word or '.' in word:
                    # Skip if it's an email address
                    if '@' not in word:
                        hostname = word.strip('.,;:')
                        break
        
        if not hostname:
            hostname = "unknown-host"
        
        # Determine resource type
        resource_type = ResourceType.VM
        resource_info = None
        
        if any(word in prompt_lower for word in ["oracle", "database", "db"]):
            resource_type = ResourceType.ORACLE_DB
            print(f"\n🔍 Detected: Oracle Database")
            print(f"   Host: {hostname}")
            resource_info = OracleDBResourceInfo(
                host=hostname,
                port=1521,
                service_name="ORCL",
                username="system",
                resource_type=ResourceType.ORACLE_DB
            )
        elif any(word in prompt_lower for word in ["mongo", "mongodb"]):
            resource_type = ResourceType.MONGO_DB
            print(f"\n🔍 Detected: MongoDB")
            print(f"   Host: {hostname}")
            resource_info = MongoDBResourceInfo(
                host=hostname,
                port=27017,
                database="admin",
                username="admin",
                resource_type=ResourceType.MONGO_DB
            )
        else:
            print(f"\n🔍 Detected: VM/Server")
            print(f"   Host: {hostname}")
            resource_info = VMResourceInfo(
                host=hostname,
                ssh_user="admin",
                ssh_port=22,
                resource_type=ResourceType.VM
            )
        
        # Create validation request
        request = ValidationRequest(
            resource_info=resource_info,
            auto_discover=True,
            validation_level="comprehensive",
            send_email=bool(email),
            email_recipient=email
        )
        
        print(f"\n✅ Request created:")
        print(f"   Resource Type: {resource_type.value}")
        print(f"   Auto Discovery: Enabled")
        print(f"   Validation Level: Comprehensive")
        if email:
            print(f"   📧 Email Report: {email}")
        
        return request
    
    async def execute_workflow(self, request: ValidationRequest):
        """Execute the complete workflow.
        
        Args:
            request: Validation request
        """
        print("\n" + "="*80)
        print("🔄 EXECUTING WORKFLOW")
        print("="*80)
        
        print("\n📋 Workflow Phases:")
        print("   1️⃣  Workload Discovery (AI-powered)")
        print("   2️⃣  Resource Classification")
        print("   3️⃣  Validation Planning")
        print("   4️⃣  Validation Execution")
        print("   5️⃣  AI Evaluation")
        print("   6️⃣  Report Generation")
        
        # Execute workflow
        print("\n🚀 Starting workflow execution...\n")
        result = await self.orchestrator.execute_workflow(request)
        
        # Display results
        print("\n" + "="*80)
        print("📊 WORKFLOW RESULTS")
        print("="*80)
        
        print(f"\n⏱️  Execution Time: {result.execution_time_seconds:.2f}s")
        print(f"📈 Workflow Status: {result.workflow_status.upper()}")
        
        # Discovery results
        if result.discovery_result:
            print(f"\n🔍 Discovery Results:")
            print(f"   Ports Found: {len(result.discovery_result.ports)}")
            print(f"   Processes Found: {len(result.discovery_result.processes)}")
            print(f"   Applications Detected: {len(result.discovery_result.applications)}")
            
            if result.discovery_result.applications:
                print(f"\n   📦 Detected Applications:")
                for app in result.discovery_result.applications[:5]:
                    print(f"      • {app.name} (confidence: {app.confidence:.0%})")
        
        # Classification results
        if result.classification:
            print(f"\n🏷️  Classification:")
            print(f"   Category: {result.classification.category.value}")
            print(f"   Confidence: {result.classification.confidence:.0%}")
            if result.classification.primary_application:
                print(f"   Primary App: {result.classification.primary_application.name}")
        
        # Validation results
        print(f"\n✅ Validation Results:")
        print(f"   Overall Status: {result.validation_result.overall_status.value}")
        print(f"   Score: {result.validation_result.score}/100")
        print(f"   Checks Passed: {result.validation_result.passed_checks}")
        print(f"   Checks Failed: {result.validation_result.failed_checks}")
        print(f"   Warnings: {result.validation_result.warnings}")
        
        # Evaluation results
        if result.evaluation:
            print(f"\n🤖 AI Evaluation:")
            print(f"   Overall Health: {result.evaluation.overall_health}")
            print(f"   Risk Level: {result.evaluation.risk_level}")
            print(f"\n   💡 Key Findings:")
            for finding in result.evaluation.key_findings[:3]:
                print(f"      • {finding}")
            
            if result.evaluation.recommendations:
                print(f"\n   📋 Recommendations:")
                for rec in result.evaluation.recommendations[:3]:
                    print(f"      • {rec}")
        
        # Errors
        if result.errors:
            print(f"\n⚠️  Errors:")
            for error in result.errors:
                print(f"   • {error}")
        
        return result
    
    async def generate_report(self, result):
        """Generate and save report.
        
        Args:
            result: Workflow result
        """
        print("\n" + "="*80)
        print("📄 GENERATING REPORT")
        print("="*80)
        
        # Generate report
        report = self.report_generator.generate_markdown_report(
            result.validation_result,
            result.discovery_result,
            result.classification,
            result.evaluation
        )
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_{result.request.resource_info.host}_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n✅ Report saved: {filename}")
        print(f"   Length: {len(report)} characters")
        
        # Show preview
        print(f"\n📄 Report Preview (first 500 chars):")
        print("-" * 80)
        print(report[:500])
        print("-" * 80)
        
        return filename
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.mcp_client:
            await self.mcp_client.disconnect()
            print("\n🔌 Disconnected from MCP server")
    
    async def run(self, prompt: str, email: Optional[str] = None):
        """Run complete demo.
        
        Args:
            prompt: Natural language prompt
            email: Optional email address for report delivery
        """
        try:
            # Initialize
            await self.initialize()
            
            # Parse prompt
            request = await self.parse_prompt(prompt, email)
            
            # Execute workflow
            result = await self.execute_workflow(request)
            
            # Generate report
            report_file = await self.generate_report(result)
            
            # Summary
            print("\n" + "="*80)
            print("✅ DEMO COMPLETE")
            print("="*80)
            print(f"\n📊 Summary:")
            print(f"   Workflow Status: {result.workflow_status}")
            print(f"   Validation Score: {result.validation_result.score}/100")
            print(f"   Execution Time: {result.execution_time_seconds:.2f}s")
            print(f"   Report: {report_file}")
            
            if result.workflow_status == "success":
                print(f"\n🎉 Validation completed successfully!")
            elif result.workflow_status == "partial_success":
                print(f"\n⚠️  Validation completed with warnings")
            else:
                print(f"\n❌ Validation failed")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    # Check arguments
    if len(sys.argv) < 2:
        print("\n" + "="*80)
        print("🤖 PRODUCTION DEMO - Agentic Validation Workflow")
        print("="*80)
        print("\nUsage:")
        print("  python production_demo.py \"<natural language prompt>\"")
        print("\nExamples:")
        print("  python production_demo.py \"Validate the Oracle database at db-server-01\"")
        print("  python production_demo.py \"Check the web server at web-server-01, send report to admin@example.com\"")
        print("  python production_demo.py \"Discover and validate app-server-01\" --email ops@company.com")
        print("  python production_demo.py \"Validate MongoDB at mongo-cluster-01\"")
        print("\nOptions:")
        print("  --model <model>  Use specific model (default: ollama:llama3)")
        print("                   Examples: openai:gpt-4, ollama:mistral")
        print("  --email <email>  Email address for report delivery")
        print("                   Can also be included in the prompt")
        print("\n" + "="*80)
        sys.exit(1)
    
    # Parse arguments
    prompt = sys.argv[1]
    model = "ollama:llama3"
    email = None
    
    if "--model" in sys.argv:
        model_idx = sys.argv.index("--model")
        if model_idx + 1 < len(sys.argv):
            model = sys.argv[model_idx + 1]
    
    if "--email" in sys.argv:
        email_idx = sys.argv.index("--email")
        if email_idx + 1 < len(sys.argv):
            email = sys.argv[email_idx + 1]
    
    # Run demo
    demo = ProductionDemo(model=model)
    await demo.run(prompt, email)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
