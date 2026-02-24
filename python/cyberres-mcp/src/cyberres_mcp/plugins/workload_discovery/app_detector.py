"""
Application detector for workload discovery.
Orchestrates process scanning, port scanning, and confidence scoring.
"""

from typing import Callable, List, Tuple

from ...models import ApplicationInstance, DiscoveryRequest
from .process_scanner import ProcessScanner
from .port_scanner import PortScanner
from .confidence import ConfidenceScorer


class ApplicationDetector:
    """
    Main application detector that orchestrates all detection methods.
    Combines process scanning, port scanning, and confidence scoring.
    """
    
    def __init__(self):
        """Initialize the application detector."""
        self.process_scanner = ProcessScanner()
        self.port_scanner = PortScanner()
        self.confidence_scorer = ConfidenceScorer()
    
    def detect(
        self,
        request: DiscoveryRequest,
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> List[ApplicationInstance]:
        """
        Detect applications using all available methods.
        
        Args:
            request: Discovery request with configuration
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of detected application instances
        """
        detected_apps: List[ApplicationInstance] = []
        
        # Run process scanning
        if request.detect_applications:
            process_apps = self.process_scanner.scan(ssh_exec)
            
            # Run port scanning
            port_apps = self.port_scanner.scan(ssh_exec)
            
            # Correlate and merge detections
            detected_apps = self.confidence_scorer.correlate_detections(
                process_apps,
                port_apps
            )
            
            # Rank by confidence
            detected_apps = self.confidence_scorer.rank_applications(detected_apps)
        
        return detected_apps
    
    def detect_by_process_only(
        self,
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> List[ApplicationInstance]:
        """
        Detect applications using only process scanning.
        
        Args:
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of detected application instances
        """
        apps = self.process_scanner.scan(ssh_exec)
        
        # Score applications
        for app in apps:
            app.confidence = self.confidence_scorer.score_application(app)
        
        return self.confidence_scorer.rank_applications(apps)
    
    def detect_by_port_only(
        self,
        ssh_exec: Callable[[str], Tuple[str, str, int]]
    ) -> List[ApplicationInstance]:
        """
        Detect applications using only port scanning.
        
        Args:
            ssh_exec: Function to execute SSH commands
            
        Returns:
            List of detected application instances
        """
        apps = self.port_scanner.scan(ssh_exec)
        
        # Score applications
        for app in apps:
            app.confidence = self.confidence_scorer.score_application(app)
        
        return self.confidence_scorer.rank_applications(apps)
    
    def validate_detections(
        self,
        applications: List[ApplicationInstance]
    ) -> dict:
        """
        Validate all detections and return validation report.
        
        Args:
            applications: List of detected applications
            
        Returns:
            Validation report with issues and statistics
        """
        report = {
            'total_applications': len(applications),
            'valid_applications': 0,
            'applications_with_issues': 0,
            'issues_by_app': {},
            'statistics': self.confidence_scorer.get_confidence_statistics(applications)
        }
        
        for app in applications:
            issues = self.confidence_scorer.validate_detection(app)
            
            if issues:
                report['applications_with_issues'] += 1
                report['issues_by_app'][app.name] = issues
            else:
                report['valid_applications'] += 1
        
        return report

# Made with Bob
