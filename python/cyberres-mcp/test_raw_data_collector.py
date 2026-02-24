"""
Test suite for raw data collection (hybrid approach Phase 1).
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cyberres_mcp.plugins.workload_discovery.raw_data_collector import RawDataCollector


def test_raw_data_collector_basic():
    """Test basic raw data collection."""
    print("\n" + "="*80)
    print("TEST 1: Basic Raw Data Collection")
    print("="*80)
    
    # Mock SSH executor
    def mock_ssh_exec(cmd):
        if "ps aux" in cmd:
            return (0, "PID USER COMMAND\n1234 oracle ora_pmon_ORCL\n2345 postgres postgres", "")
        elif "netstat" in cmd or "ss" in cmd:
            return (0, "tcp 0 0 0.0.0.0:1521 LISTEN\ntcp 0 0 0.0.0.0:5432 LISTEN", "")
        return (1, "", "command not found")
    
    collector = RawDataCollector()
    result = collector.collect(mock_ssh_exec)
    
    # Verify results
    assert "processes" in result, "Should collect processes"
    assert "ports" in result, "Should collect ports"
    assert "ora_pmon" in result["processes"], "Should find Oracle process"
    assert "postgres" in result["processes"], "Should find PostgreSQL process"
    assert "1521" in result["ports"], "Should find Oracle port"
    assert "5432" in result["ports"], "Should find PostgreSQL port"
    
    print("✅ Basic collection works")
    print(f"   Collected data types: {list(result.keys())}")
    print(f"   Process data length: {len(result['processes'])} bytes")
    print(f"   Port data length: {len(result['ports'])} bytes")


def test_raw_data_collector_with_options():
    """Test raw data collection with custom options."""
    print("\n" + "="*80)
    print("TEST 2: Raw Data Collection with Options")
    print("="*80)
    
    # Mock SSH executor
    def mock_ssh_exec(cmd):
        if "ps aux" in cmd:
            return (0, "PID USER COMMAND\n1234 oracle ora_pmon_ORCL", "")
        elif "netstat" in cmd or "ss" in cmd:
            return (0, "tcp 0 0 0.0.0.0:1521 LISTEN", "")
        elif "rpm -qa" in cmd:
            return (0, "oracle-database-ee-19c\npostgresql14-server", "")
        elif "systemctl" in cmd:
            return (0, "oracle.service loaded active running\npostgresql.service loaded active running", "")
        elif "cat" in cmd:
            return (0, "# Oracle config\nDB_NAME=ORCL", "")
        return (1, "", "command not found")
    
    collector = RawDataCollector()
    
    # Test with all options enabled
    options = {
        "collect_processes": True,
        "collect_ports": True,
        "collect_packages": True,
        "collect_services": True,
        "collect_configs": True,
        "config_paths": ["/etc/oracle/tnsnames.ora"]
    }
    
    result = collector.collect(mock_ssh_exec, options)
    
    # Verify results
    assert "processes" in result, "Should collect processes"
    assert "ports" in result, "Should collect ports"
    assert "packages" in result, "Should collect packages"
    assert "services" in result, "Should collect services"
    assert "configs" in result, "Should collect configs"
    
    assert "oracle-database" in result["packages"], "Should find Oracle package"
    assert "postgresql" in result["services"], "Should find PostgreSQL service"
    assert "/etc/oracle/tnsnames.ora" in result["configs"], "Should collect config file"
    assert "DB_NAME" in result["configs"]["/etc/oracle/tnsnames.ora"], "Should have config content"
    
    print("✅ Collection with options works")
    print(f"   Collected data types: {list(result.keys())}")
    print(f"   Packages found: {len(result['packages'].splitlines())}")
    print(f"   Services found: {len(result['services'].splitlines())}")
    print(f"   Config files: {len(result['configs'])}")


def test_raw_data_collector_selective():
    """Test selective data collection."""
    print("\n" + "="*80)
    print("TEST 3: Selective Data Collection")
    print("="*80)
    
    # Mock SSH executor
    def mock_ssh_exec(cmd):
        if "ps aux" in cmd:
            return (0, "PID USER COMMAND\n1234 oracle ora_pmon_ORCL", "")
        elif "netstat" in cmd or "ss" in cmd:
            return (0, "tcp 0 0 0.0.0.0:1521 LISTEN", "")
        return (1, "", "command not found")
    
    collector = RawDataCollector()
    
    # Test collecting only processes
    options = {
        "collect_processes": True,
        "collect_ports": False,
        "collect_packages": False,
        "collect_services": False,
        "collect_configs": False
    }
    
    result = collector.collect(mock_ssh_exec, options)
    
    # Verify results
    assert "processes" in result, "Should collect processes"
    assert "ports" not in result, "Should not collect ports"
    assert "packages" not in result, "Should not collect packages"
    assert "services" not in result, "Should not collect services"
    assert "configs" not in result, "Should not collect configs"
    
    print("✅ Selective collection works")
    print(f"   Collected only: {list(result.keys())}")


def test_raw_data_collector_error_handling():
    """Test error handling in raw data collection."""
    print("\n" + "="*80)
    print("TEST 4: Error Handling")
    print("="*80)
    
    # Mock SSH executor that fails
    def mock_ssh_exec_fail(cmd):
        return (1, "", "Connection refused")
    
    collector = RawDataCollector()
    result = collector.collect(mock_ssh_exec_fail)
    
    # Should return empty strings for failed collections
    assert "processes" in result, "Should have processes key"
    assert "ports" in result, "Should have ports key"
    assert result["processes"] == "", "Failed process collection should return empty string"
    assert result["ports"] == "", "Failed port collection should return empty string"
    
    print("✅ Error handling works")
    print(f"   Failed collections return empty strings")


def test_raw_data_collector_fallback():
    """Test fallback commands."""
    print("\n" + "="*80)
    print("TEST 5: Fallback Commands")
    print("="*80)
    
    # Mock SSH executor where netstat fails but ss works
    def mock_ssh_exec(cmd):
        if "ps aux" in cmd:
            return (0, "PID USER COMMAND\n1234 oracle ora_pmon_ORCL", "")
        elif "netstat" in cmd:
            return (1, "", "netstat: command not found")
        elif "ss" in cmd:
            return (0, "tcp LISTEN 0 0 *:1521 *:*", "")
        elif "rpm" in cmd:
            return (1, "", "rpm: command not found")
        elif "dpkg" in cmd:
            return (0, "ii oracle-db 19c", "")
        elif "systemctl" in cmd:
            return (1, "", "systemctl: command not found")
        elif "service" in cmd:
            return (0, "oracle running", "")
        return (1, "", "command not found")
    
    collector = RawDataCollector()
    
    options = {
        "collect_processes": True,
        "collect_ports": True,
        "collect_packages": True,
        "collect_services": True
    }
    
    result = collector.collect(mock_ssh_exec, options)
    
    # Verify fallbacks worked
    assert "1521" in result["ports"], "Should use ss fallback for ports"
    assert "oracle-db" in result["packages"], "Should use dpkg fallback for packages"
    assert "oracle running" in result["services"], "Should use service fallback for services"
    
    print("✅ Fallback commands work")
    print(f"   ss fallback: ✓")
    print(f"   dpkg fallback: ✓")
    print(f"   service fallback: ✓")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("RAW DATA COLLECTOR TEST SUITE")
    print("="*80)
    
    tests = [
        ("Basic Collection", test_raw_data_collector_basic),
        ("Collection with Options", test_raw_data_collector_with_options),
        ("Selective Collection", test_raw_data_collector_selective),
        ("Error Handling", test_raw_data_collector_error_handling),
        ("Fallback Commands", test_raw_data_collector_fallback)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ {name} FAILED: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n❌ {name} ERROR: {str(e)}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Raw data collector is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

# Made with Bob
