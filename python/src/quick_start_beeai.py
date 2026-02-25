#!/usr/bin/env python3
"""
Quick Start Script for BeeAI Validation System

This script provides an easy way to test the BeeAI implementation
with a sample validation request.

Usage:
    python quick_start_beeai.py
"""

import asyncio
import logging
from datetime import datetime

from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def quick_start_demo():
    """Run a quick demo of the BeeAI validation system."""
    
    print("\n" + "="*80)
    print("🐝 BeeAI Validation System - Quick Start Demo")
    print("="*80)
    print("\nThis demo will:")
    print("  1. Initialize the BeeAI orchestrator")
    print("  2. Connect to MCP server and discover tools")
    print("  3. Run a sample VM validation")
    print("  4. Display results")
    print("\n" + "="*80 + "\n")
    
    try:
        # Step 1: Create orchestrator
        print("📋 Step 1: Creating BeeAI Validation Orchestrator...")
        orchestrator = BeeAIValidationOrchestrator(
            mcp_server_path="python/cyberres-mcp",
            llm_model="ollama:llama3.2:latest",
            enable_discovery=True,
            enable_ai_evaluation=True,
            memory_size=50
        )
        print("✅ Orchestrator created\n")
        
        # Step 2: Initialize
        print("🔧 Step 2: Initializing components...")
        print("   - Connecting to MCP server...")
        print("   - Discovering MCP tools...")
        print("   - Initializing agents...")
        
        await orchestrator.initialize()
        
        print("✅ Initialization complete")
        print(f"   - Discovery enabled: {orchestrator.enable_discovery}")
        print(f"   - Evaluation enabled: {orchestrator.enable_ai_evaluation}")
        print(f"   - LLM model: {orchestrator.llm_model}\n")
        
        # Step 3: Create sample request
        print("📝 Step 3: Creating sample validation request...")
        
        # Get user input or use defaults
        print("\nEnter resource details (or press Enter for defaults):")
        host = input("  Host/IP [192.168.1.100]: ").strip() or "192.168.1.100"
        ssh_user = input("  SSH User [admin]: ").strip() or "admin"
        ssh_password = input("  SSH Password [password123]: ").strip() or "password123"
        
        vm_info = VMResourceInfo(
            host=host,
            resource_type=ResourceType.VM,
            ssh_host=host,
            ssh_port=22,
            ssh_user=ssh_user,
            ssh_password=ssh_password
        )
        
        request = ValidationRequest(
            resource_info=vm_info,
            auto_discover=True,
            acceptance_criteria={
                "min_score": 70,
                "required_checks": ["connectivity", "ssh_access"]
            }
        )
        
        print(f"\n✅ Request created for {host}\n")
        
        # Step 4: Execute workflow
        print("🚀 Step 4: Executing validation workflow...")
        print("="*80)
        
        start_time = datetime.now()
        result = await orchestrator.execute_workflow(request)
        end_time = datetime.now()
        
        # Step 5: Display results
        print("\n" + "="*80)
        print("📊 VALIDATION RESULTS")
        print("="*80)
        
        print(f"\n🎯 Overall Status: {result.workflow_status.upper()}")
        print(f"📈 Score: {result.validation_result.overall_score}/100")
        print(f"⏱️  Execution Time: {result.execution_time_seconds:.2f}s")
        
        print(f"\n📋 Check Summary:")
        print(f"   ✅ Passed: {result.validation_result.passed_checks}")
        print(f"   ❌ Failed: {result.validation_result.failed_checks}")
        print(f"   ⚠️  Warnings: {result.validation_result.warning_checks}")
        
        # Discovery results
        if result.discovery_result:
            print(f"\n🔍 Discovery Results:")
            print(f"   - Ports found: {len(result.discovery_result.ports)}")
            print(f"   - Processes found: {len(result.discovery_result.processes)}")
            print(f"   - Applications detected: {len(result.discovery_result.applications)}")
            
            if result.discovery_result.applications:
                print(f"\n   📦 Detected Applications:")
                for app in result.discovery_result.applications[:5]:
                    print(f"      - {app.name} (confidence: {app.confidence:.2%})")
        
        # Classification
        if result.classification:
            print(f"\n🏷️  Classification:")
            print(f"   - Category: {result.classification.category.value}")
            print(f"   - Confidence: {result.classification.confidence:.2%}")
        
        # Evaluation
        if result.evaluation:
            print(f"\n🧠 AI Evaluation:")
            print(f"   - Overall Health: {result.evaluation.overall_health}")
            print(f"   - Critical Issues: {len(result.evaluation.critical_issues)}")
            print(f"   - Recommendations: {len(result.evaluation.recommendations)}")
            
            if result.evaluation.critical_issues:
                print(f"\n   ⚠️  Critical Issues:")
                for issue in result.evaluation.critical_issues[:3]:
                    print(f"      - {issue}")
            
            if result.evaluation.recommendations:
                print(f"\n   💡 Top Recommendations:")
                for i, rec in enumerate(result.evaluation.recommendations[:3], 1):
                    print(f"      {i}. {rec}")
        
        # Phase timings
        print(f"\n⏱️  Phase Timings:")
        for phase, duration in result.phase_timings.items():
            print(f"   - {phase.capitalize()}: {duration:.2f}s")
        
        # Errors
        if result.errors:
            print(f"\n⚠️  Errors Encountered:")
            for error in result.errors:
                print(f"   - {error}")
        
        # Detailed check results
        print(f"\n📋 Detailed Check Results:")
        for check in result.validation_result.checks:
            status_icon = "✅" if check.status == "PASS" else "❌" if check.status == "FAIL" else "⚠️"
            print(f"   {status_icon} {check.name}: {check.status}")
            if check.message:
                print(f"      └─ {check.message}")
        
        print("\n" + "="*80)
        print("✅ Demo Complete!")
        print("="*80)
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        await orchestrator.cleanup()
        print("✅ Cleanup complete\n")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure MCP server is running: cd python/cyberres-mcp && uv run cyberres-mcp")
        print("  2. Check Ollama is running: ollama list")
        print("  3. Verify model exists: ollama pull llama3.2")
        print("  4. Check logs for details")
        return False


async def main():
    """Main entry point."""
    success = await quick_start_demo()
    
    if success:
        print("\n🎉 Success! The BeeAI validation system is working correctly.")
        print("\nNext steps:")
        print("  1. Review the results above")
        print("  2. Try with your own resources")
        print("  3. Explore main_beeai.py for more options")
        print("  4. Read BEEAI_IMPLEMENTATION_COMPLETE.md for full documentation")
    else:
        print("\n❌ Demo failed. Please check the error messages above.")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
