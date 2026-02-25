#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Test the application classifier."""

from datetime import datetime
from classifier import ApplicationClassifier
from models import (
    WorkloadDiscoveryResult,
    ApplicationDetection,
    PortInfo,
    ProcessInfo,
    ResourceCategory
)


def test_database_classification():
    """Test classification of database server."""
    print("\n=== Testing Database Server Classification ===")
    
    # Create discovery result with Oracle database
    discovery = WorkloadDiscoveryResult(
        host="db-server-01",
        ports=[
            PortInfo(port=1521, protocol="tcp", service="oracle", state="open"),
            PortInfo(port=22, protocol="tcp", service="ssh", state="open")
        ],
        processes=[
            ProcessInfo(pid=1234, name="oracle", cmdline="/u01/app/oracle/product/19c/bin/oracle", user="oracle")
        ],
        applications=[
            ApplicationDetection(
                name="Oracle Database",
                version="19c",
                confidence=0.95,
                detection_method="port_and_process",
                evidence={"port": 1521, "process": "oracle"}
            )
        ],
        discovery_time=datetime.now()
    )
    
    classifier = ApplicationClassifier(confidence_threshold=0.6)
    classification = classifier.classify(discovery)
    
    print(f"Category: {classification.category}")
    print(f"Primary App: {classification.primary_application.name if classification.primary_application else 'None'}")
    print(f"Confidence: {classification.confidence}")
    print(f"Recommended Validations: {classification.recommended_validations}")
    
    assert classification.category == ResourceCategory.DATABASE_SERVER
    assert "database_connection" in classification.recommended_validations
    assert "tablespace_usage" in classification.recommended_validations
    print("✓ Database classification test passed")


def test_web_server_classification():
    """Test classification of web server."""
    print("\n=== Testing Web Server Classification ===")
    
    discovery = WorkloadDiscoveryResult(
        host="web-server-01",
        ports=[
            PortInfo(port=80, protocol="tcp", service="http", state="open"),
            PortInfo(port=443, protocol="tcp", service="https", state="open"),
            PortInfo(port=22, protocol="tcp", service="ssh", state="open")
        ],
        processes=[
            ProcessInfo(pid=5678, name="nginx", cmdline="/usr/sbin/nginx -g daemon off;", user="www-data")
        ],
        applications=[
            ApplicationDetection(
                name="Nginx",
                version="1.21.0",
                confidence=0.92,
                detection_method="port_and_process",
                evidence={"port": 80, "process": "nginx"}
            )
        ],
        discovery_time=datetime.now()
    )
    
    classifier = ApplicationClassifier(confidence_threshold=0.6)
    classification = classifier.classify(discovery)
    
    print(f"Category: {classification.category}")
    print(f"Primary App: {classification.primary_application.name if classification.primary_application else 'None'}")
    print(f"Confidence: {classification.confidence}")
    print(f"Recommended Validations: {classification.recommended_validations}")
    
    assert classification.category == ResourceCategory.WEB_SERVER
    assert "http_endpoint_check" in classification.recommended_validations
    assert "ssl_certificate_validation" in classification.recommended_validations
    print("✓ Web server classification test passed")


def test_mixed_environment():
    """Test classification of mixed environment."""
    print("\n=== Testing Mixed Environment Classification ===")
    
    discovery = WorkloadDiscoveryResult(
        host="app-server-01",
        ports=[
            PortInfo(port=8080, protocol="tcp", service="http-proxy", state="open"),
            PortInfo(port=3306, protocol="tcp", service="mysql", state="open"),
            PortInfo(port=22, protocol="tcp", service="ssh", state="open")
        ],
        processes=[
            ProcessInfo(pid=1111, name="tomcat", cmdline="/opt/tomcat/bin/catalina.sh run", user="tomcat"),
            ProcessInfo(pid=2222, name="mysqld", cmdline="/usr/sbin/mysqld", user="mysql")
        ],
        applications=[
            ApplicationDetection(
                name="Apache Tomcat",
                version="9.0",
                confidence=0.88,
                detection_method="port_and_process",
                evidence={"port": 8080, "process": "tomcat"}
            ),
            ApplicationDetection(
                name="MySQL",
                version="8.0",
                confidence=0.85,
                detection_method="port_and_process",
                evidence={"port": 3306, "process": "mysqld"}
            )
        ],
        discovery_time=datetime.now()
    )
    
    classifier = ApplicationClassifier(confidence_threshold=0.6)
    classification = classifier.classify(discovery)
    
    print(f"Category: {classification.category}")
    print(f"Primary App: {classification.primary_application.name if classification.primary_application else 'None'}")
    print(f"Secondary Apps: {[app.name for app in classification.secondary_applications]}")
    print(f"Confidence: {classification.confidence}")
    print(f"Recommended Validations: {classification.recommended_validations}")
    
    assert classification.category == ResourceCategory.MIXED
    assert len(classification.secondary_applications) > 0
    print("✓ Mixed environment classification test passed")


def test_low_confidence():
    """Test classification with low confidence applications."""
    print("\n=== Testing Low Confidence Classification ===")
    
    discovery = WorkloadDiscoveryResult(
        host="unknown-server-01",
        ports=[
            PortInfo(port=8000, protocol="tcp", service="unknown", state="open"),
            PortInfo(port=22, protocol="tcp", service="ssh", state="open")
        ],
        processes=[
            ProcessInfo(pid=9999, name="custom-app", cmdline="/opt/custom/app", user="appuser")
        ],
        applications=[
            ApplicationDetection(
                name="Custom Application",
                version=None,
                confidence=0.45,
                detection_method="port_only",
                evidence={"port": 8000}
            )
        ],
        discovery_time=datetime.now()
    )
    
    classifier = ApplicationClassifier(confidence_threshold=0.6)
    classification = classifier.classify(discovery)
    
    print(f"Category: {classification.category}")
    print(f"Primary App: {classification.primary_application.name if classification.primary_application else 'None'}")
    print(f"Confidence: {classification.confidence}")
    print(f"Recommended Validations: {classification.recommended_validations}")
    
    assert classification.category == ResourceCategory.UNKNOWN
    assert "basic_connectivity" in classification.recommended_validations
    print("✓ Low confidence classification test passed")


def test_application_summary():
    """Test application summary generation."""
    print("\n=== Testing Application Summary ===")
    
    discovery = WorkloadDiscoveryResult(
        host="multi-app-server",
        ports=[
            PortInfo(port=80, protocol="tcp", service="http", state="open"),
            PortInfo(port=3306, protocol="tcp", service="mysql", state="open"),
            PortInfo(port=6379, protocol="tcp", service="redis", state="open")
        ],
        processes=[],
        applications=[
            ApplicationDetection(
                name="Nginx",
                version="1.21.0",
                confidence=0.92,
                detection_method="port",
                evidence={"port": 80}
            ),
            ApplicationDetection(
                name="MySQL",
                version="8.0",
                confidence=0.85,
                detection_method="port",
                evidence={"port": 3306}
            ),
            ApplicationDetection(
                name="Redis",
                version="6.2",
                confidence=0.78,
                detection_method="port",
                evidence={"port": 6379}
            ),
            ApplicationDetection(
                name="Unknown Service",
                version=None,
                confidence=0.35,
                detection_method="port",
                evidence={"port": 8888}
            )
        ],
        discovery_time=datetime.now()
    )
    
    classifier = ApplicationClassifier(confidence_threshold=0.6)
    summary = classifier.get_application_summary(discovery)
    
    print(f"Total Applications: {summary['total_applications']}")
    print(f"By Category: {summary['by_category']}")
    print(f"High Confidence: {len(summary['high_confidence'])} apps")
    print(f"Low Confidence: {len(summary['low_confidence'])} apps")
    
    assert summary['total_applications'] == 4
    assert len(summary['high_confidence']) == 3
    assert len(summary['low_confidence']) == 1
    print("✓ Application summary test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Application Classifier Test Suite")
    print("=" * 60)
    
    try:
        test_database_classification()
        test_web_server_classification()
        test_mixed_environment()
        test_low_confidence()
        test_application_summary()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()


# Made with Bob