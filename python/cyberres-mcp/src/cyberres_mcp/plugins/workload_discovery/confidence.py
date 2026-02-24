"""
Confidence scoring for workload discovery.
Calculates and enhances confidence levels based on multiple detection methods.
"""

from typing import Any, List, Dict, Set
from collections import defaultdict

from ...models import ApplicationInstance, DetectionMethod, ConfidenceLevel


class ConfidenceScorer:
    """
    Calculates confidence scores for detected applications.
    Applies boost rules when multiple detection methods agree.
    """
    
    # Confidence level numeric values for calculations
    CONFIDENCE_VALUES = {
        ConfidenceLevel.HIGH: 90,
        ConfidenceLevel.MEDIUM: 70,
        ConfidenceLevel.LOW: 50,
        ConfidenceLevel.UNCERTAIN: 30
    }
    
    # Reverse mapping
    VALUE_TO_CONFIDENCE = {
        90: ConfidenceLevel.HIGH,
        70: ConfidenceLevel.MEDIUM,
        50: ConfidenceLevel.LOW,
        30: ConfidenceLevel.UNCERTAIN
    }
    
    def __init__(self):
        """Initialize the confidence scorer."""
        pass
    
    def score_application(self, app: ApplicationInstance) -> ConfidenceLevel:
        """
        Calculate confidence score for a single application.
        
        Args:
            app: Application instance to score
            
        Returns:
            Updated confidence level
        """
        base_score = self.CONFIDENCE_VALUES.get(app.confidence, 50)
        
        # Apply boost rules
        boost = 0
        
        # Multiple detection methods boost
        if len(app.detection_methods) >= 3:
            boost += 20
        elif len(app.detection_methods) == 2:
            boost += 10
        
        # Version detection boost
        if app.version and app.version != "unknown":
            boost += 10
        
        # Process info boost
        if app.process_info and 'pid' in app.process_info:
            boost += 5
        
        # Network bindings boost
        if app.network_bindings and len(app.network_bindings) > 0:
            boost += 5
        
        # Config files boost
        if app.config_files and len(app.config_files) > 0:
            boost += 5
        
        # Install path boost
        if app.install_path:
            boost += 5
        
        # Calculate final score
        final_score = min(base_score + boost, 100)
        
        # Convert to confidence level
        if final_score >= 85:
            return ConfidenceLevel.HIGH
        elif final_score >= 65:
            return ConfidenceLevel.MEDIUM
        elif final_score >= 45:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN
    
    def correlate_detections(
        self,
        process_detections: List[ApplicationInstance],
        port_detections: List[ApplicationInstance]
    ) -> List[ApplicationInstance]:
        """
        Correlate detections from process and port scanning.
        Merge matching applications and boost confidence.
        
        Args:
            process_detections: Applications detected via process scanning
            port_detections: Applications detected via port scanning
            
        Returns:
            Merged and correlated application instances
        """
        # Index applications by name for quick lookup
        process_by_name: Dict[str, List[ApplicationInstance]] = defaultdict(list)
        for app in process_detections:
            process_by_name[app.name].append(app)
        
        port_by_name: Dict[str, List[ApplicationInstance]] = defaultdict(list)
        for app in port_detections:
            port_by_name[app.name].append(app)
        
        # Find all unique application names
        all_names = set(process_by_name.keys()) | set(port_by_name.keys())
        
        merged: List[ApplicationInstance] = []
        
        for name in all_names:
            process_apps = process_by_name.get(name, [])
            port_apps = port_by_name.get(name, [])
            
            if process_apps and port_apps:
                # Both methods detected this app - merge and boost
                merged_app = self._merge_applications(process_apps[0], port_apps[0])
                merged.append(merged_app)
                
                # Add remaining instances if any
                for app in process_apps[1:]:
                    merged.append(app)
                for app in port_apps[1:]:
                    merged.append(app)
            elif process_apps:
                # Only process detection
                merged.extend(process_apps)
            else:
                # Only port detection
                merged.extend(port_apps)
        
        # Score all merged applications
        for app in merged:
            app.confidence = self.score_application(app)
        
        return merged
    
    def _merge_applications(
        self,
        app1: ApplicationInstance,
        app2: ApplicationInstance
    ) -> ApplicationInstance:
        """
        Merge two application instances detected by different methods.
        
        Args:
            app1: First application instance
            app2: Second application instance
            
        Returns:
            Merged application instance
        """
        # Combine detection methods
        detection_methods = list(set(app1.detection_methods + app2.detection_methods))
        
        # Use better version if available
        version = app1.version
        if app2.version and app2.version != "unknown":
            if version == "unknown" or not version:
                version = app2.version
        
        # Merge process info
        process_info = {**app1.process_info, **app2.process_info}
        
        # Merge network bindings
        network_bindings = app1.network_bindings + app2.network_bindings
        
        # Merge config files
        config_files = list(set(app1.config_files + app2.config_files))
        
        # Use install path from either (prefer non-None)
        install_path = app1.install_path or app2.install_path
        
        # Take higher confidence as base
        base_confidence = max(
            self.CONFIDENCE_VALUES.get(app1.confidence, 50),
            self.CONFIDENCE_VALUES.get(app2.confidence, 50)
        )
        
        # Create merged instance
        merged = ApplicationInstance(
            name=app1.name,
            category=app1.category,
            version=version,
            vendor=app1.vendor,
            detection_methods=detection_methods,
            confidence=self._score_to_confidence(base_confidence),
            process_info=process_info,
            network_bindings=network_bindings,
            config_files=config_files,
            install_path=install_path
        )
        
        return merged
    
    def _score_to_confidence(self, score: int) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 85:
            return ConfidenceLevel.HIGH
        elif score >= 65:
            return ConfidenceLevel.MEDIUM
        elif score >= 45:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN
    
    def filter_by_confidence(
        self,
        applications: List[ApplicationInstance],
        min_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    ) -> List[ApplicationInstance]:
        """
        Filter applications by minimum confidence level.
        
        Args:
            applications: List of application instances
            min_confidence: Minimum confidence level to include
            
        Returns:
            Filtered list of applications
        """
        min_score = self.CONFIDENCE_VALUES.get(min_confidence, 50)
        
        filtered = []
        for app in applications:
            app_score = self.CONFIDENCE_VALUES.get(app.confidence, 30)
            if app_score >= min_score:
                filtered.append(app)
        
        return filtered
    
    def get_confidence_statistics(
        self,
        applications: List[ApplicationInstance]
    ) -> Dict[str, Any]:
        """
        Get statistics about confidence levels.
        
        Args:
            applications: List of application instances
            
        Returns:
            Dictionary with confidence statistics
        """
        stats = {
            'total': len(applications),
            'by_confidence': {
                'high': 0,
                'medium': 0,
                'low': 0,
                'uncertain': 0
            },
            'by_detection_methods': {},
            'average_score': 0
        }
        
        total_score = 0
        
        for app in applications:
            # Count by confidence
            confidence_key = app.confidence.value
            stats['by_confidence'][confidence_key] += 1
            
            # Add to total score
            total_score += self.CONFIDENCE_VALUES.get(app.confidence, 30)
            
            # Count by number of detection methods
            method_count = len(app.detection_methods)
            stats['by_detection_methods'][method_count] = \
                stats['by_detection_methods'].get(method_count, 0) + 1
        
        # Calculate average
        if applications:
            stats['average_score'] = total_score / len(applications)
        
        return stats
    
    def rank_applications(
        self,
        applications: List[ApplicationInstance]
    ) -> List[ApplicationInstance]:
        """
        Rank applications by confidence and other factors.
        
        Args:
            applications: List of application instances
            
        Returns:
            Sorted list (highest confidence first)
        """
        def rank_key(app: ApplicationInstance) -> tuple:
            confidence_score = self.CONFIDENCE_VALUES.get(app.confidence, 30)
            method_count = len(app.detection_methods)
            has_version = 1 if app.version and app.version != "unknown" else 0
            
            # Return tuple for sorting (higher values first)
            return (confidence_score, method_count, has_version)
        
        return sorted(applications, key=rank_key, reverse=True)
    
    def validate_detection(self, app: ApplicationInstance) -> List[str]:
        """
        Validate a detection and return list of issues/warnings.
        
        Args:
            app: Application instance to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check for missing critical information
        if not app.detection_methods:
            issues.append("No detection methods recorded")
        
        if app.confidence == ConfidenceLevel.UNCERTAIN:
            issues.append("Very low confidence - may be false positive")
        
        if not app.version or app.version == "unknown":
            issues.append("Version not detected")
        
        if not app.process_info and not app.network_bindings:
            issues.append("No process or network information available")
        
        # Check for inconsistencies
        if DetectionMethod.PROCESS_SCAN in app.detection_methods and not app.process_info:
            issues.append("Process scan method but no process info")
        
        if DetectionMethod.PORT_SCAN in app.detection_methods and not app.network_bindings:
            issues.append("Port scan method but no network bindings")
        
        return issues

# Made with Bob
