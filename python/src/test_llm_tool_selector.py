#!/usr/bin/env python3
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Test script for LLM-driven tool selector."""

import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_llm_tool_selector():
    """Test the LLM tool selector with sample data."""
    from llm_tool_selector import LLMToolSelector
    
    print("=" * 60)
    print("Testing LLM-Driven Tool Selector")
    print("=" * 60)
    
    # Sample discovered applications
    discovered_apps = [
        {
            "name": "Oracle Database",
            "version": "19c",
            "ports": [1521],
            "confidence": "high"
        }
    ]
    
    # Sample available tools (simulating MCP tools)
    available_tools = [
        {
            "name": "db_oracle_discover_and_validate",
            "description": "Discover Oracle listener/services via SSH and optionally validate DB connectivity. Uses ps -ef | grep pmon to infer SIDs, runs lsnrctl status to parse services. If oracle_user and oracle_password provided, attempts connection.",
            "parameters": {
                "ssh_host": {"type": "string", "required": True},
                "ssh_user": {"type": "string", "required": True},
                "ssh_password": {"type": "string", "required": False},
                "oracle_user": {"type": "string", "required": False},
                "oracle_password": {"type": "string", "required": False}
            }
        },
        {
            "name": "db_oracle_connect",
            "description": "Attempt to connect to an Oracle instance and return basic info. Requires either DSN or host+service. Queries v$instance and v$database for metadata.",
            "parameters": {
                "user": {"type": "string", "required": True},
                "password": {"type": "string", "required": True},
                "service": {"type": "string", "required": False},
                "host": {"type": "string", "required": False}
            }
        },
        {
            "name": "vm_validate_core",
            "description": "Validate VM core functionality via SSH including connectivity, disk space, memory, CPU.",
            "parameters": {
                "host": {"type": "string", "required": True},
                "ssh_user": {"type": "string", "required": True},
                "ssh_password": {"type": "string", "required": False}
            }
        }
    ]
    
    # Available credentials (SSH only, no Oracle DB credentials)
    available_credentials = {
        "ssh": {
            "hostname": "9.11.68.243",
            "username": "root",
            "password": "available"
        },
        "oracle_db": None
    }
    
    validation_goal = "Validate Oracle Database recovery on server 9.11.68.243"
    
    print(f"\nDiscovered Applications: {len(discovered_apps)}")
    for app in discovered_apps:
        print(f"  - {app['name']} {app['version']}")
    
    print(f"\nAvailable Tools: {len(available_tools)}")
    for tool in available_tools:
        print(f"  - {tool['name']}")
    
    print(f"\nAvailable Credentials:")
    print(f"  - SSH: ✓")
    print(f"  - Oracle DB: ✗")
    
    print(f"\nValidation Goal: {validation_goal}")
    
    print("\n" + "-" * 60)
    print("Calling LLM Tool Selector...")
    print("-" * 60)
    
    try:
        selector = LLMToolSelector()
        selected_tools, summary = await selector.select_tools(
            discovered_apps=discovered_apps,
            available_tools=available_tools,
            available_credentials=available_credentials,
            validation_goal=validation_goal
        )
        
        print("\n✓ LLM Tool Selection Complete!")
        print("\n" + "=" * 60)
        print("SELECTION SUMMARY")
        print("=" * 60)
        print(f"Total tools available: {summary.total_tools_available}")
        print(f"Tools can execute: {summary.tools_can_execute}")
        print(f"Tools blocked by credentials: {summary.tools_blocked_by_credentials}")
        print(f"\nRecommendation: {summary.recommendation}")
        
        print("\n" + "=" * 60)
        print("SELECTED TOOLS")
        print("=" * 60)
        
        for i, tool in enumerate(selected_tools, 1):
            status = "✓ CAN EXECUTE" if tool.can_execute else "✗ BLOCKED"
            print(f"\n{i}. {tool.tool_name} ({tool.priority}) {status}")
            print(f"   Reasoning: {tool.reasoning}")
            print(f"   Required credentials: {', '.join(tool.required_credentials)}")
            if tool.missing_credentials:
                print(f"   Missing credentials: {', '.join(tool.missing_credentials)}")
        
        print("\n" + "=" * 60)
        print("TEST RESULT: SUCCESS ✓")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error("Test failed", exc_info=True)
        print("\n" + "=" * 60)
        print("TEST RESULT: FAILED ✗")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_llm_tool_selector())
    sys.exit(0 if success else 1)

# Made with Bob
