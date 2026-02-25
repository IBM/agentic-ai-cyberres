#!/usr/bin/env python3
"""Test the priority field validator in ReportSection."""

import sys
from pydantic import ValidationError

# Import the ReportSection model
from agents.reporting_agent import ReportSection


def test_priority_validator():
    """Test various priority value inputs."""
    
    print("Testing ReportSection priority validator...")
    print("=" * 60)
    
    test_cases = [
        # (input_value, expected_output, description)
        (1, 1, "Numeric 1"),
        (2, 2, "Numeric 2"),
        (3, 3, "Numeric 3"),
        (4, 4, "Numeric 4"),
        (5, 5, "Numeric 5"),
        ("critical", 1, "String 'critical'"),
        ("highest", 1, "String 'highest'"),
        ("high", 2, "String 'high'"),
        ("HIGH", 2, "String 'HIGH' (uppercase)"),
        ("medium", 3, "String 'medium'"),
        ("normal", 3, "String 'normal'"),
        ("low", 4, "String 'low'"),
        ("lowest", 5, "String 'lowest'"),
        ("info", 5, "String 'info'"),
        ("optional", 5, "String 'optional'"),
        (2.5, 2, "Float 2.5"),
        (3.9, 3, "Float 3.9"),
        (0, 1, "Out of range 0 (clamped to 1)"),
        (6, 5, "Out of range 6 (clamped to 5)"),
        (100, 5, "Out of range 100 (clamped to 5)"),
        ("invalid", 3, "Invalid string (defaults to 3)"),
        ("xyz", 3, "Invalid string 'xyz' (defaults to 3)"),
    ]
    
    passed = 0
    failed = 0
    
    for input_value, expected, description in test_cases:
        try:
            section = ReportSection(
                title="Test Section",
                content="Test content",
                priority=input_value
            )
            
            if section.priority == expected:
                print(f"✅ PASS: {description}")
                print(f"   Input: {repr(input_value)} → Output: {section.priority}")
                passed += 1
            else:
                print(f"❌ FAIL: {description}")
                print(f"   Input: {repr(input_value)} → Expected: {expected}, Got: {section.priority}")
                failed += 1
                
        except ValidationError as e:
            print(f"❌ FAIL: {description}")
            print(f"   Input: {repr(input_value)} → ValidationError: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ FAIL: {description}")
            print(f"   Input: {repr(input_value)} → Unexpected error: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(test_priority_validator())

# Made with Bob
