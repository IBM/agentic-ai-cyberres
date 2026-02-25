#!/usr/bin/env python3
"""
Simple entry point for BeeAI validation using the complete orchestrator.
This uses the full BeeAI implementation with automatic MCP tool discovery.
"""

import asyncio
import sys
from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType

async def main():
    """Run validation with BeeAI orchestrator."""
    
    print("\n" + "="*80)
    print("🐝 BeeAI Recovery Validation Agent")
    print("   Using Complete BeeAI Orchestrator with Automatic Tool Discovery")
    print("="*80 + "\n")
    
    # Get resource info from user
    print("Enter resource details:")
    host = input("  Host/IP: ").strip()
    if not host:
        print("❌ Host is required")
        return
    
    ssh_user = input("  SSH User [root]: ").strip() or "root"
    ssh_password = input("  SSH Password: ").strip()
    email = input("  Email for report: ").strip()
    
    # Create resource info
    vm_info = VMResourceInfo(
        host=host,
        resource_type=ResourceType.VM,
        ssh_host=host,
        ssh_port=22,
        ssh_user=ssh_user,
        ssh_password=ssh_password
    )
    
    # Create validation request
    request = ValidationRequest(
        resource_info=vm_info,
        auto_discover=True,
        acceptance_criteria={
            "min_score": 70,
            "required_checks": ["connectivity", "ssh_access"]
        }
    )
    
    print("\n" + "="*80)
    print("🚀 Initializing BeeAI Orchestrator...")
    print("="*80 + "\n")
    
    # Create orchestrator - it will automatically discover MCP tools
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path="python/cyberres-mcp",
        llm_model="ollama:llama3.2:latest",
        enable_discovery=True,
        enable_ai_evaluation=True
    )
    
    try:
        # Initialize - this connects to MCP and discovers all tools
        await orchestrator.initialize()
        
        print("\n" + "="*80)
        print("🔄 Executing Validation Workflow...")
        print("   The BeeAI agent will automatically:")
        print("   1. Discover available MCP tools")
        print("   2. Decide which tools to use based on the task")
        print("   3. Execute the tools")
        print("   4. Analyze results")
        print("="*80 + "\n")
        
        # Execute workflow - agent decides which tools to use
        result = await orchestrator.execute_workflow(request)
        
        # Display results
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
        
        if result.discovery_result:
            print(f"\n🔍 Discovery Results:")
            print(f"   - Ports: {len(result.discovery_result.ports)}")
            print(f"   - Processes: {len(result.discovery_result.processes)}")
            print(f"   - Applications: {len(result.discovery_result.applications)}")
        
        if result.evaluation:
            print(f"\n🧠 AI Evaluation:")
            print(f"   - Overall Health: {result.evaluation.overall_health}")
            print(f"   - Critical Issues: {len(result.evaluation.critical_issues)}")
            print(f"   - Recommendations: {len(result.evaluation.recommendations)}")
            
            if result.evaluation.recommendations:
                print(f"\n💡 Top Recommendations:")
                for i, rec in enumerate(result.evaluation.recommendations[:3], 1):
                    print(f"      {i}. {rec}")
        
        print(f"\n⏱️  Phase Timings:")
        for phase, duration in result.phase_timings.items():
            print(f"   - {phase.capitalize()}: {duration:.2f}s")
        
        if email:
            print(f"\n📧 Report would be sent to: {email}")
        
        print("\n" + "="*80)
        print("✅ Validation Complete!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await orchestrator.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)

# Made with Bob
