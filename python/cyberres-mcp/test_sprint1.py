#!/usr/bin/env python3
"""
Sprint 1 Testing Suite for Workload Discovery

This script tests the foundation components implemented in Sprint 1:
- Server creation
- Data models
- OS Detector
- Plugin registration
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cyberres_mcp.server import create_app
from cyberres_mcp.models import (
    OSType, OSDistribution, ConfidenceLevel,
    DetectionMethod, ApplicationCategory,
    DiscoveryRequest, OSInfo
)
from cyberres_mcp.plugins.workload_discovery import OSDetector


def test_server_creation():
    """Test 1: Server creates successfully"""
    print("Test 1: Creating MCP server...")
    try:
        app = create_app()
        print("✅ Server created successfully")
        return True
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test 2: Data models work correctly"""
    print("\nTest 2: Testing data models...")
    try:
        # Test enums
        os_type = OSType.LINUX
        dist = OSDistribution.UBUNTU
        conf = ConfidenceLevel.HIGH
        method = DetectionMethod.FILE_SYSTEM
        category = ApplicationCategory.DATABASE
        
        # Test DiscoveryRequest
        request = DiscoveryRequest(
            host="test-host",
            ssh_user="testuser",
            ssh_password="testpass"
        )
        
        # Test OSInfo
        os_info = OSInfo(
            os_type=OSType.LINUX,
            distribution=OSDistribution.UBUNTU,
            version="22.04",
            confidence=ConfidenceLevel.HIGH,
            detection_methods=[DetectionMethod.FILE_SYSTEM]
        )
        
        # Verify serialization
        os_dict = os_info.dict()
        assert os_dict['os_type'] == 'linux'
        assert os_dict['distribution'] == 'ubuntu'
        
        print(f"✅ Models working: OS={os_type.value}, Dist={dist.value}, Conf={conf.value}")
        print(f"   Request: host={request.host}, port={request.ssh_port}")
        print(f"   OSInfo serialization: OK")
        return True
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_os_detector_import():
    """Test 3: OS Detector imports correctly"""
    print("\nTest 3: Testing OS Detector import...")
    try:
        detector = OSDetector()
        print("✅ OS Detector imported and instantiated")
        print(f"   Distribution patterns: {len(detector.DISTRIBUTION_PATTERNS)} configured")
        return True
    except Exception as e:
        print(f"❌ OS Detector import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_os_detector_parsing():
    """Test 4: OS Detector parsing logic"""
    print("\nTest 4: Testing OS Detector parsing...")
    try:
        detector = OSDetector()
        
        # Test os-release parsing
        os_release_content = '''NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="22.04"
PRETTY_NAME="Ubuntu 22.04.3 LTS"
'''
        parsed = detector._parse_os_release(os_release_content)
        assert parsed['ID'] == 'ubuntu', f"Expected 'ubuntu', got '{parsed.get('ID')}'"
        assert parsed['VERSION_ID'] == '22.04', f"Expected '22.04', got '{parsed.get('VERSION_ID')}'"
        assert parsed['NAME'] == 'Ubuntu', f"Expected 'Ubuntu', got '{parsed.get('NAME')}'"
        
        print("✅ OS Detector parsing works correctly")
        print(f"   Parsed fields: {list(parsed.keys())}")
        
        # Test lsb_release parsing
        lsb_content = '''Distributor ID: Ubuntu
Description:    Ubuntu 22.04.3 LTS
Release:        22.04
Codename:       jammy
'''
        lsb_parsed = detector._parse_lsb_release(lsb_content)
        assert 'Distributor ID' in lsb_parsed
        assert lsb_parsed['Distributor ID'] == 'Ubuntu'
        
        print("✅ LSB release parsing works correctly")
        
        # Test distribution detection
        from cyberres_mcp.models import OSDistribution
        dist = detector._detect_distribution(parsed, lsb_parsed, "")
        assert dist == OSDistribution.UBUNTU, f"Expected UBUNTU, got {dist}"
        
        print("✅ Distribution detection works correctly")
        
        # Test version extraction
        version = detector._extract_version(parsed, lsb_parsed)
        assert version == "22.04", f"Expected '22.04', got '{version}'"
        
        print("✅ Version extraction works correctly")
        
        return True
    except Exception as e:
        print(f"❌ OS Detector parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confidence_calculation():
    """Test 5: Confidence calculation"""
    print("\nTest 5: Testing confidence calculation...")
    try:
        detector = OSDetector()
        
        # Test high confidence
        conf = detector._calculate_os_confidence(
            has_os_release=True,
            has_lsb=True,
            distribution_detected=True
        )
        assert conf == ConfidenceLevel.HIGH, f"Expected HIGH, got {conf}"
        print("✅ High confidence calculation correct")
        
        # Test medium confidence
        conf = detector._calculate_os_confidence(
            has_os_release=True,
            has_lsb=False,
            distribution_detected=True
        )
        assert conf == ConfidenceLevel.MEDIUM, f"Expected MEDIUM, got {conf}"
        print("✅ Medium confidence calculation correct")
        
        # Test low confidence
        conf = detector._calculate_os_confidence(
            has_os_release=False,
            has_lsb=False,
            distribution_detected=True
        )
        assert conf == ConfidenceLevel.LOW, f"Expected LOW, got {conf}"
        print("✅ Low confidence calculation correct")
        
        # Test uncertain
        conf = detector._calculate_os_confidence(
            has_os_release=False,
            has_lsb=False,
            distribution_detected=False
        )
        assert conf == ConfidenceLevel.UNCERTAIN, f"Expected UNCERTAIN, got {conf}"
        print("✅ Uncertain confidence calculation correct")
        
        return True
    except Exception as e:
        print(f"❌ Confidence calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plugin_registration():
    """Test 6: Plugin is properly registered"""
    print("\nTest 6: Testing plugin registration...")
    try:
        from cyberres_mcp.plugins import workload_discovery
        
        # Check attach function exists
        assert hasattr(workload_discovery, 'attach'), "attach function not found"
        print("✅ Plugin has attach function")
        
        # Check other exports
        assert hasattr(workload_discovery, 'OSDetector'), "OSDetector not exported"
        assert hasattr(workload_discovery, 'ApplicationDetector'), "ApplicationDetector not exported"
        assert hasattr(workload_discovery, 'ResultAggregator'), "ResultAggregator not exported"
        print("✅ Plugin exports correct classes")
        
        return True
    except Exception as e:
        print(f"❌ Plugin registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("Sprint 1 Testing Suite - Workload Discovery")
    print("=" * 70)
    print()
    
    results = []
    results.append(("Server Creation", test_server_creation()))
    results.append(("Data Models", test_models()))
    results.append(("OS Detector Import", test_os_detector_import()))
    results.append(("OS Detector Parsing", test_os_detector_parsing()))
    results.append(("Confidence Calculation", test_confidence_calculation()))
    results.append(("Plugin Registration", test_plugin_registration()))
    
    print()
    print("=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed == total:
        print()
        print("🎉 All tests passed! Sprint 1 is working correctly.")
        print()
        print("Next steps:")
        print("1. Test with a real Linux server using discover_os_only tool")
        print("2. Review the testing guide: docs/SPRINT1_TESTING_GUIDE.md")
        print("3. Proceed to Sprint 2: Application Detection")
        return 0
    else:
        print()
        print(f"⚠️  {total - passed} test(s) failed. Please review the errors above.")
        print()
        print("Troubleshooting:")
        print("1. Ensure all dependencies are installed: uv sync")
        print("2. Check Python version: python --version (need 3.13+)")
        print("3. Review error messages and stack traces above")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

# Made with Bob
