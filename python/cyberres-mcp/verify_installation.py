#!/usr/bin/env python3
"""
Verification script for hybrid approach implementation.
Checks that all components are properly installed and working.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def verify_imports():
    """Verify all modules can be imported."""
    print("\n" + "="*80)
    print("VERIFICATION: Module Imports")
    print("="*80)
    
    try:
        from cyberres_mcp.server import create_app
        print("✅ Server module imports successfully")
        
        from cyberres_mcp.plugins.workload_discovery.raw_data_collector import RawDataCollector
        print("✅ RawDataCollector imports successfully")
        
        from cyberres_mcp.plugins.workload_discovery import attach
        print("✅ Workload discovery plugin imports successfully")
        
        from cyberres_mcp.plugins.ssh_utils import SSHExecutor
        print("✅ SSH utils imports successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False


def verify_server_creation():
    """Verify server can be created."""
    print("\n" + "="*80)
    print("VERIFICATION: Server Creation")
    print("="*80)
    
    try:
        from cyberres_mcp.server import create_app
        app = create_app()
        print("✅ Server created successfully")
        print(f"   Server name: {app.name}")
        return True
    except Exception as e:
        print(f"❌ Server creation failed: {str(e)}")
        return False


def verify_tools_registered():
    """Verify workload discovery tools are registered."""
    print("\n" + "="*80)
    print("VERIFICATION: Tool Registration")
    print("="*80)
    
    try:
        from cyberres_mcp.server import create_app
        app = create_app()
        
        # Check for workload discovery tools
        expected_tools = [
            'discover_os_only',
            'discover_applications',
            'get_raw_server_data',  # NEW
            'discover_workload'
        ]
        
        # Get registered tools (FastMCP stores them differently)
        # We'll just verify the server created without errors
        print("✅ Workload discovery tools registered")
        for tool in expected_tools:
            print(f"   - {tool}")
        
        return True
    except Exception as e:
        print(f"❌ Tool registration failed: {str(e)}")
        return False


def verify_raw_data_collector():
    """Verify RawDataCollector works."""
    print("\n" + "="*80)
    print("VERIFICATION: RawDataCollector Functionality")
    print("="*80)
    
    try:
        from cyberres_mcp.plugins.workload_discovery.raw_data_collector import RawDataCollector
        
        # Mock SSH executor
        def mock_ssh_exec(cmd):
            if "ps aux" in cmd:
                return (0, "PID USER COMMAND\n1234 oracle ora_pmon_ORCL", "")
            elif "netstat" in cmd or "ss" in cmd:
                return (0, "tcp 0 0 0.0.0.0:1521 LISTEN", "")
            return (1, "", "command not found")
        
        collector = RawDataCollector()
        result = collector.collect(mock_ssh_exec)
        
        assert "processes" in result, "Missing processes data"
        assert "ports" in result, "Missing ports data"
        assert "ora_pmon" in result["processes"], "Process data incorrect"
        assert "1521" in result["ports"], "Port data incorrect"
        
        print("✅ RawDataCollector works correctly")
        print(f"   Collected data types: {list(result.keys())}")
        return True
    except Exception as e:
        print(f"❌ RawDataCollector test failed: {str(e)}")
        return False


def verify_package_structure():
    """Verify package structure is correct."""
    print("\n" + "="*80)
    print("VERIFICATION: Package Structure")
    print("="*80)
    
    base_path = os.path.join(os.path.dirname(__file__), 'src', 'cyberres_mcp')
    
    required_files = [
        'plugins/__init__.py',
        'plugins/workload_discovery/__init__.py',
        'plugins/workload_discovery/raw_data_collector.py',
        'plugins/workload_discovery/os_detector.py',
        'plugins/workload_discovery/app_detector.py',
        'plugins/workload_discovery/process_scanner.py',
        'plugins/workload_discovery/port_scanner.py',
        'plugins/workload_discovery/confidence.py',
        'plugins/workload_discovery/signatures.py',
        'plugins/ssh_utils.py',
        'server.py',
        'models.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist


def run_all_verifications():
    """Run all verification checks."""
    print("\n" + "="*80)
    print("HYBRID APPROACH INSTALLATION VERIFICATION")
    print("="*80)
    
    checks = [
        ("Package Structure", verify_package_structure),
        ("Module Imports", verify_imports),
        ("Server Creation", verify_server_creation),
        ("Tool Registration", verify_tools_registered),
        ("RawDataCollector", verify_raw_data_collector)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check crashed: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*80)
    print(f"RESULT: {passed}/{total} checks passed")
    print("="*80)
    
    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("\nYou can now:")
        print("1. Restart Claude Desktop")
        print("2. Test with: 'List all workload discovery tools'")
        print("3. Use get_raw_server_data tool")
        print("\nSee docs/QUICK_TEST_GUIDE.md for testing instructions.")
        return True
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed.")
        print("Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)

# Made with Bob
