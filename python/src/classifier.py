#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Application classifier for workload discovery results."""

import logging
from typing import Dict, Any, List, Set
from models import (
    WorkloadDiscoveryResult,
    ResourceClassification,
    ResourceCategory,
    ApplicationDetection
)

logger = logging.getLogger(__name__)


class ApplicationClassifier:
    """Classify resources based on discovered applications."""
    
    # Application category mappings
    DATABASE_APPS: Set[str] = {
        "oracle", "mongodb", "postgresql", "mysql", "mariadb",
        "mssql", "sqlserver", "db2", "cassandra", "redis", 
        "memcached", "elasticsearch", "couchdb"
    }
    
    WEB_SERVER_APPS: Set[str] = {
        "apache", "nginx", "iis", "lighttpd", "caddy", "httpd"
    }
    
    APP_SERVER_APPS: Set[str] = {
        "tomcat", "jboss", "wildfly", "weblogic", "websphere",
        "glassfish", "jetty", "undertow"
    }
    
    MESSAGE_QUEUE_APPS: Set[str] = {
        "rabbitmq", "kafka", "activemq", "artemis", "zeromq",
        "nats", "pulsar"
    }
    
    CACHE_SERVER_APPS: Set[str] = {
        "redis", "memcached", "varnish", "haproxy"
    }
    
    def __init__(self, confidence_threshold: float = 0.6):
        """Initialize classifier.
        
        Args:
            confidence_threshold: Minimum confidence for classification (0-1)
        """
        self.confidence_threshold = confidence_threshold
    
    def classify(
        self,
        discovery_result: WorkloadDiscoveryResult
    ) -> ResourceClassification:
        """Classify resource based on discovered applications.
        
        Args:
            discovery_result: Workload discovery results
        
        Returns:
            ResourceClassification with category and recommendations
        """
        if not discovery_result.applications:
            logger.warning(f"No applications detected on {discovery_result.host}")
            return ResourceClassification(
                category=ResourceCategory.UNKNOWN,
                confidence=0.0,
                recommended_validations=["basic_connectivity", "system_health"]
            )
        
        # Sort applications by confidence
        sorted_apps = sorted(
            discovery_result.applications,
            key=lambda a: a.confidence,
            reverse=True
        )
        
        # Filter by confidence threshold
        confident_apps = [app for app in sorted_apps if app.confidence >= self.confidence_threshold]
        
        if not confident_apps:
            logger.warning(
                f"No applications above confidence threshold {self.confidence_threshold} on {discovery_result.host}"
            )
            primary_app = sorted_apps[0] if sorted_apps else None
            return ResourceClassification(
                category=ResourceCategory.UNKNOWN,
                primary_application=primary_app,
                confidence=primary_app.confidence if primary_app else 0.0,
                recommended_validations=["basic_connectivity", "system_health"]
            )
        
        primary_app = confident_apps[0]
        secondary_apps = confident_apps[1:3]  # Top 3 secondary apps
        
        # Determine category
        category = self._determine_category(primary_app)
        
        # Check for mixed environment
        if len(confident_apps) > 1:
            categories = set(self._determine_category(app) for app in confident_apps[:3])
            if len(categories) > 1:
                category = ResourceCategory.MIXED
        
        # Get recommended validations
        recommended_validations = self._get_recommended_validations(
            category,
            primary_app,
            secondary_apps
        )
        
        classification = ResourceClassification(
            category=category,
            primary_application=primary_app,
            secondary_applications=secondary_apps,
            confidence=primary_app.confidence,
            recommended_validations=recommended_validations
        )
        
        logger.info(
            f"Classified {discovery_result.host} as {category.value}",
            extra={
                "primary_app": primary_app.name,
                "confidence": primary_app.confidence,
                "secondary_apps": [app.name for app in secondary_apps]
            }
        )
        
        return classification
    
    def _determine_category(
        self,
        app: ApplicationDetection
    ) -> ResourceCategory:
        """Determine resource category from application.
        
        Args:
            app: Application detection
        
        Returns:
            ResourceCategory
        """
        app_name_lower = app.name.lower()
        
        # Check each category
        if any(db in app_name_lower for db in self.DATABASE_APPS):
            return ResourceCategory.DATABASE_SERVER
        elif any(web in app_name_lower for web in self.WEB_SERVER_APPS):
            return ResourceCategory.WEB_SERVER
        elif any(appserver in app_name_lower for appserver in self.APP_SERVER_APPS):
            return ResourceCategory.APPLICATION_SERVER
        elif any(mq in app_name_lower for mq in self.MESSAGE_QUEUE_APPS):
            return ResourceCategory.MESSAGE_QUEUE
        elif any(cache in app_name_lower for cache in self.CACHE_SERVER_APPS):
            return ResourceCategory.CACHE_SERVER
        else:
            return ResourceCategory.UNKNOWN
    
    def _get_recommended_validations(
        self,
        category: ResourceCategory,
        primary_app: ApplicationDetection,
        secondary_apps: List[ApplicationDetection]
    ) -> List[str]:
        """Get recommended validation checks based on classification.
        
        Args:
            category: Resource category
            primary_app: Primary application
            secondary_apps: Secondary applications
        
        Returns:
            List of recommended validation check names
        """
        validations = ["network_connectivity", "system_health"]
        
        # Add category-specific validations
        if category == ResourceCategory.DATABASE_SERVER:
            validations.extend([
                "database_connection",
                "database_health",
                "storage_usage",
                "replication_status"
            ])
            
            # Database-specific checks
            app_name_lower = primary_app.name.lower()
            if "oracle" in app_name_lower:
                validations.extend([
                    "tablespace_usage",
                    "archive_log_status",
                    "listener_status"
                ])
            elif "mongodb" in app_name_lower:
                validations.extend([
                    "replica_set_status",
                    "oplog_status",
                    "collection_validation"
                ])
            elif "postgresql" in app_name_lower or "mysql" in app_name_lower:
                validations.extend([
                    "table_health",
                    "connection_pool_status"
                ])
        
        elif category == ResourceCategory.WEB_SERVER:
            validations.extend([
                "http_endpoint_check",
                "https_endpoint_check",
                "ssl_certificate_validation",
                "response_time_check",
                "virtual_host_check"
            ])
        
        elif category == ResourceCategory.APPLICATION_SERVER:
            validations.extend([
                "application_health",
                "thread_pool_status",
                "memory_usage",
                "deployment_status",
                "jvm_metrics"
            ])
        
        elif category == ResourceCategory.MESSAGE_QUEUE:
            validations.extend([
                "queue_health",
                "message_flow_check",
                "cluster_status",
                "consumer_status",
                "queue_depth_check"
            ])
        
        elif category == ResourceCategory.CACHE_SERVER:
            validations.extend([
                "cache_hit_ratio",
                "memory_usage",
                "eviction_rate",
                "connection_count"
            ])
        
        elif category == ResourceCategory.MIXED:
            # Add validations for all detected application types
            for app in [primary_app] + secondary_apps:
                app_category = self._determine_category(app)
                if app_category == ResourceCategory.DATABASE_SERVER:
                    validations.append("database_check")
                elif app_category == ResourceCategory.WEB_SERVER:
                    validations.append("web_server_check")
                elif app_category == ResourceCategory.APPLICATION_SERVER:
                    validations.append("app_server_check")
        
        # Add validations for high-confidence secondary applications
        for app in secondary_apps:
            if app.confidence > 0.8:
                app_category = self._determine_category(app)
                if app_category == ResourceCategory.DATABASE_SERVER:
                    validations.append("secondary_database_check")
                elif app_category == ResourceCategory.WEB_SERVER:
                    validations.append("secondary_web_check")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_validations = []
        for v in validations:
            if v not in seen:
                seen.add(v)
                unique_validations.append(v)
        
        return unique_validations
    
    def get_application_summary(
        self,
        discovery_result: WorkloadDiscoveryResult
    ) -> Dict[str, Any]:
        """Get a summary of discovered applications.
        
        Args:
            discovery_result: Workload discovery results
        
        Returns:
            Summary dictionary with application counts and categories
        """
        if not discovery_result.applications:
            return {
                "total_applications": 0,
                "by_category": {},
                "high_confidence": [],
                "low_confidence": []
            }
        
        by_category: Dict[str, List[str]] = {}
        high_confidence = []
        low_confidence = []
        
        for app in discovery_result.applications:
            category = self._determine_category(app)
            category_name = category.value
            
            if category_name not in by_category:
                by_category[category_name] = []
            by_category[category_name].append(app.name)
            
            if app.confidence >= self.confidence_threshold:
                high_confidence.append({
                    "name": app.name,
                    "confidence": app.confidence,
                    "category": category_name
                })
            else:
                low_confidence.append({
                    "name": app.name,
                    "confidence": app.confidence,
                    "category": category_name
                })
        
        return {
            "total_applications": len(discovery_result.applications),
            "by_category": by_category,
            "high_confidence": high_confidence,
            "low_confidence": low_confidence,
            "confidence_threshold": self.confidence_threshold
        }


# Made with Bob