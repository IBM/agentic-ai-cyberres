"""
BeeAI-Powered Main Entry Point for Recovery Validation

This module provides the main entry point for the BeeAI-powered validation system,
integrating the complete multi-agent workflow with the orchestrator.

Usage:
    python main_beeai.py
    
    Or with specific configuration:
    python main_beeai.py --llm ollama:llama3.2 --no-discovery --no-evaluation
"""

import os
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Optional

from beeai_agents.orchestrator import BeeAIValidationOrchestrator, WorkflowResult
from models import (
    ValidationRequest,
    VMResourceInfo,
    OracleDBResourceInfo,
    MongoDBResourceInfo,
    ResourceType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('beeai_validation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='BeeAI-Powered Recovery Validation Agent'
    )
    
    parser.add_argument(
        '--llm',
        type=str,
        default='ollama:llama3.2',
        help='LLM model to use (default: ollama:llama3.2)'
    )
    
    parser.add_argument(
        '--mcp-server',
        type=str,
        default='python/cyberres-mcp',
        help='Path to MCP server directory (default: python/cyberres-mcp)'
    )
    
    parser.add_argument(
        '--no-discovery',
        action='store_true',
        help='Disable workload discovery phase'
    )
    
    parser.add_argument(
        '--no-evaluation',
        action='store_true',
        help='Disable AI evaluation phase'
    )
    
    parser.add_argument(
        '--memory-size',
        type=int,
        default=50,
        help='Memory size for agents (default: 50)'
    )
    
    parser.add_argument(
        '--resource-type',
        type=str,
        choices=['vm', 'oracle', 'mongodb'],
        default='vm',
        help='Resource type to validate (default: vm)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        required=True,
        help='Resource hostname or IP address'
    )
    
    parser.add_argument(
        '--ssh-user',
        type=str,
        help='SSH username (for VM validation)'
    )
    
    parser.add_argument(
        '--ssh-password',
        type=str,
        help='SSH password (for VM validation)'
    )
    
    parser.add_argument(
        '--ssh-port',
        type=int,
        default=22,
        help='SSH port (default: 22)'
    )
    
    return parser.parse_args()


def create_validation_request(args) -> ValidationRequest:
    """Create validation request from arguments.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        ValidationRequest
    """
    if args.resource_type == 'vm':
        resource_info = VMResourceInfo(
            host=args.host,
            resource_type=ResourceType.VM,
            ssh_host=args.host,
            ssh_port=args.ssh_port,
            ssh_user=args.ssh_user or 'admin',
            ssh_password=args.ssh_password or 'password'
        )
    elif args.resource_type == 'oracle':
        resource_info = OracleDBResourceInfo(
            host=args.host,
            resource_type=ResourceType.ORACLE_DB,
            db_host=args.host,
            db_port=1521,
            db_service_name='ORCL',
            db_user='system',
            db_password='password'
        )
    else:  # mongodb
        resource_info = MongoDBResourceInfo(
            host=args.host,
            resource_type=ResourceType.MONGO_DB,
            db_host=args.host,
            db_port=27017,
            db_name='admin',
            db_user='admin',
            db_password='password'
        )
    
    return ValidationRequest(
        resource_info=resource_info,
        auto_discover=not args.no_discovery,
        acceptance_criteria={
            'min_score': 80,
            'required_checks': ['connectivity', 'system_health']
        }
    )


def display_welcome_banner(args):
    """Display welcome banner.
    
    Args:
        args: Parsed arguments
    """
    print("\n" + "=" * 80)
    print("  🤖 BEEAI-POWERED RECOVERY VALIDATION AGENT")
    print("  Multi-Agent Intelligent Infrastructure Validation")
    print("=" * 80)
    print(f"\n  Configuration:")
    print(f"    LLM Model: {args.llm}")
    print(f"    Resource Type: {args.resource_type.upper()}")
    print(f"    Target Host: {args.host}")
    print(f"    Discovery: {'Enabled' if not args.no_discovery else 'Disabled'}")
    print(f"    Evaluation: {'Enabled' if not args.no_evaluation else 'Disabled'}")
    print("=" * 80 + "\n")


def display_workflow_result(result: WorkflowResult):
    """Display workflow result in a user-friendly format.
    
    Args:
        result: Workflow execution result
    """
    print("\n" + "=" * 80)
    print("  📊 VALIDATION RESULTS")
    print("=" * 80)
    
    # Overall status
    status_emoji = {
        'success': '✅',
        'partial_success': '⚠️',
        'failure': '❌'
    }
    emoji = status_emoji.get(result.workflow_status, '❓')
    
    print(f"\n  {emoji} Workflow Status: {result.workflow_status.upper()}")
    print(f"  ⏱️  Execution Time: {result.execution_time_seconds:.2f}s")
    print(f"  📈 Validation Score: {result.validation_result.score}/100")
    
    # Phase timings
    if result.phase_timings:
        print(f"\n  Phase Timings:")
        for phase, timing in result.phase_timings.items():
            print(f"    • {phase.capitalize()}: {timing:.2f}s")
    
    # Discovery results
    if result.discovery_result:
        print(f"\n  🔍 Discovery Results:")
        print(f"    • Open Ports: {len(result.discovery_result.ports)}")
        print(f"    • Running Processes: {len(result.discovery_result.processes)}")
        print(f"    • Detected Applications: {len(result.discovery_result.applications)}")
        
        if result.discovery_result.applications:
            print(f"\n    Top Applications:")
            for app in result.discovery_result.applications[:5]:
                print(f"      - {app.name} ({app.confidence:.0%} confidence)")
    
    # Classification
    if result.classification:
        print(f"\n  🏷️  Classification:")
        print(f"    • Category: {result.classification.category.value}")
        print(f"    • Confidence: {result.classification.confidence:.0%}")
        if result.classification.primary_application:
            print(f"    • Primary App: {result.classification.primary_application.name}")
    
    # Validation results
    print(f"\n  ✓ Validation Checks:")
    print(f"    • Total: {len(result.validation_result.checks)}")
    print(f"    • Passed: {result.validation_result.passed_checks} ✅")
    print(f"    • Failed: {result.validation_result.failed_checks} ❌")
    print(f"    • Warnings: {result.validation_result.warning_checks} ⚠️")
    
    # Show failed checks
    failed_checks = [c for c in result.validation_result.checks 
                    if c.status.value == 'fail']
    if failed_checks:
        print(f"\n    Failed Checks:")
        for check in failed_checks[:5]:
            print(f"      ❌ {check.check_name}")
            if check.message:
                print(f"         {check.message}")
    
    # Evaluation
    if result.evaluation:
        print(f"\n  🎯 AI Evaluation:")
        print(f"    • Overall Health: {result.evaluation.overall_health.upper()}")
        print(f"    • Confidence: {result.evaluation.confidence:.0%}")
        print(f"    • Critical Issues: {len(result.evaluation.critical_issues)}")
        print(f"    • Recommendations: {len(result.evaluation.recommendations)}")
        
        if result.evaluation.critical_issues:
            print(f"\n    Critical Issues:")
            for issue in result.evaluation.critical_issues[:3]:
                print(f"      🔴 {issue}")
        
        if result.evaluation.recommendations:
            print(f"\n    Top Recommendations:")
            for i, rec in enumerate(result.evaluation.recommendations[:5], 1):
                print(f"      {i}. {rec}")
        
        if result.evaluation.next_steps:
            print(f"\n    Next Steps:")
            for step in result.evaluation.next_steps[:3]:
                print(f"      → {step}")
    
    # Errors
    if result.errors:
        print(f"\n  ⚠️  Errors Encountered:")
        for error in result.errors:
            print(f"    • {error}")
    
    print("\n" + "=" * 80 + "\n")


async def main():
    """Main entry point for BeeAI validation system."""
    # Parse arguments
    args = parse_arguments()
    
    # Display welcome banner
    display_welcome_banner(args)
    
    # Create orchestrator
    logger.info("Initializing BeeAI Validation Orchestrator...")
    orchestrator = BeeAIValidationOrchestrator(
        mcp_server_path=args.mcp_server,
        llm_model=args.llm,
        enable_discovery=not args.no_discovery,
        enable_ai_evaluation=not args.no_evaluation,
        memory_size=args.memory_size
    )
    
    try:
        # Initialize orchestrator
        print("🔧 Initializing orchestrator and agents...")
        await orchestrator.initialize()
        print("✅ Initialization complete\n")
        
        # Create validation request
        request = create_validation_request(args)
        
        # Execute workflow
        print(f"🚀 Starting validation workflow for {args.host}...\n")
        result = await orchestrator.execute_workflow(request)
        
        # Display results
        display_workflow_result(result)
        
        # Save detailed results
        output_file = f"validation_result_{args.host.replace('.', '_')}.json"
        with open(output_file, 'w') as f:
            f.write(result.model_dump_json(indent=2))
        print(f"📄 Detailed results saved to: {output_file}\n")
        
        # Exit code based on workflow status
        exit_code = 0 if result.workflow_status == 'success' else 1
        
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        print("\n\n👋 Goodbye!")
        exit_code = 130
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        print("Check beeai_validation.log for details.\n")
        exit_code = 1
        
    finally:
        # Cleanup
        print("🧹 Cleaning up resources...")
        await orchestrator.cleanup()
        print("✅ Cleanup complete\n")
    
    logger.info(f"BeeAI Validation Agent stopped (exit code: {exit_code})")
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

# Made with Bob
