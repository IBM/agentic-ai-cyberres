"""
Validation History Repository - MongoDB Implementation

Handles persistence of validation runs, checks, and results to MongoDB.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class ValidationHistoryRepositoryMongoDB:
    """Repository for validation history operations using MongoDB."""
    
    def __init__(self, connection_string: str, database_name: str = "beeai"):
        """
        Initialize repository.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Database name (default: beeai)
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def initialize(self):
        """Initialize MongoDB connection and create indexes."""
        self.client = AsyncIOMotorClient(self.connection_string)
        self.db = self.client[self.database_name]
        
        # Create indexes for optimal query performance
        await self._create_indexes()
        
        logger.info(f"MongoDB connection initialized: {self.database_name}")
    
    async def _create_indexes(self):
        """Create indexes for collections."""
        # Validation runs indexes
        await self.db.validation_runs.create_index([("user_id", 1), ("created_at", -1)])
        await self.db.validation_runs.create_index([("target_host", 1)])
        await self.db.validation_runs.create_index([("status", 1)])
        await self.db.validation_runs.create_index([("score", 1)])
        await self.db.validation_runs.create_index([("session_id", 1)])
        await self.db.validation_runs.create_index([("created_at", -1)])
        
        # User sessions indexes
        await self.db.user_sessions.create_index([("user_id", 1)])
        await self.db.user_sessions.create_index([("session_id", 1)], unique=True)
        await self.db.user_sessions.create_index([("last_activity", -1)])
        
        # Audit log indexes
        await self.db.audit_log.create_index([("user_id", 1)])
        await self.db.audit_log.create_index([("action", 1)])
        await self.db.audit_log.create_index([("created_at", -1)])
        
        logger.info("MongoDB indexes created")
    
    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    async def save_validation_run(
        self,
        user_id: str,
        session_id: str,
        result: Any  # WorkflowResult object
    ) -> str:
        """
        Save validation run and return ID.
        
        Args:
            user_id: User ID
            session_id: Session ID
            result: WorkflowResult object
            
        Returns:
            Validation run ID (ObjectId as string)
        """
        # Build validation run document
        validation_run = {
            "user_id": user_id,
            "session_id": session_id,
            "target_host": result.request.resource_info.host,
            "credential_id": getattr(result.request.resource_info, 'credential_id', 'unknown'),
            "score": result.validation_result.score if result.validation_result else 0,
            "status": result.validation_result.overall_status if result.validation_result else 'unknown',
            "workflow_status": result.workflow_status,
            "execution_time_seconds": result.execution_time_seconds,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            
            # Embedded validation checks
            "checks": [],
            
            # Embedded discovery results
            "discoveries": [],
            
            # Embedded evaluation
            "evaluation": None
        }
        
        # Add validation checks
        if result.validation_result and result.validation_result.checks:
            for check in result.validation_result.checks:
                validation_run["checks"].append({
                    "check_name": check.check_name,
                    "status": check.status,
                    "message": check.message,
                    "expected": check.expected,
                    "actual": check.actual,
                    "severity": getattr(check, 'severity', 'info'),
                    "created_at": datetime.utcnow()
                })
        
        # Add discovery results
        if result.discovery_result and result.discovery_result.applications:
            for app in result.discovery_result.applications:
                validation_run["discoveries"].append({
                    "application_name": app.name,
                    "confidence": app.confidence,
                    "evidence": getattr(app, 'evidence', {}),
                    "created_at": datetime.utcnow()
                })
        
        # Add evaluation results
        if result.evaluation:
            validation_run["evaluation"] = {
                "overall_health": result.evaluation.overall_health,
                "confidence": result.evaluation.confidence,
                "critical_issues": result.evaluation.critical_issues,
                "recommendations": result.evaluation.recommendations,
                "created_at": datetime.utcnow()
            }
        
        # Insert document
        insert_result = await self.db.validation_runs.insert_one(validation_run)
        run_id = str(insert_result.inserted_id)
        
        logger.info(f"Validation run saved: {run_id}")
        return run_id
    
    async def get_validation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get validation run by ID.
        
        Args:
            run_id: Validation run ID (ObjectId as string)
            
        Returns:
            Validation run dictionary or None
        """
        try:
            object_id = ObjectId(run_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId: {run_id}")
            return None
        
        run = await self.db.validation_runs.find_one({"_id": object_id})
        
        if run:
            # Convert ObjectId to string for JSON serialization
            run["_id"] = str(run["_id"])
            return run
        
        return None
    
    async def list_validation_runs(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List validation runs with filters.
        
        Args:
            user_id: User ID
            limit: Maximum results
            offset: Offset for pagination
            filters: Optional filters (target_host, status, min_score, max_score, date_from, date_to)
            
        Returns:
            List of validation run dictionaries
        """
        query = {"user_id": user_id}
        
        # Apply filters
        if filters:
            if filters.get('target_host'):
                query["target_host"] = filters['target_host']
            
            if filters.get('status'):
                query["status"] = filters['status']
            
            if filters.get('min_score') is not None or filters.get('max_score') is not None:
                query["score"] = {}
                if filters.get('min_score') is not None:
                    query["score"]["$gte"] = filters['min_score']
                if filters.get('max_score') is not None:
                    query["score"]["$lte"] = filters['max_score']
            
            if filters.get('date_from') or filters.get('date_to'):
                query["created_at"] = {}
                if filters.get('date_from'):
                    query["created_at"]["$gte"] = filters['date_from']
                if filters.get('date_to'):
                    query["created_at"]["$lte"] = filters['date_to']
        
        # Query with pagination
        cursor = self.db.validation_runs.find(query).sort("created_at", -1).skip(offset).limit(limit)
        
        runs = []
        async for run in cursor:
            run["_id"] = str(run["_id"])
            # Return summary without embedded documents for list view
            runs.append({
                "_id": run["_id"],
                "target_host": run["target_host"],
                "credential_id": run["credential_id"],
                "score": run["score"],
                "status": run["status"],
                "workflow_status": run["workflow_status"],
                "execution_time_seconds": run["execution_time_seconds"],
                "created_at": run["created_at"],
                "check_count": len(run.get("checks", [])),
                "discovery_count": len(run.get("discoveries", []))
            })
        
        return runs
    
    async def get_validation_statistics(
        self,
        user_id: str,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """
        Get validation statistics using MongoDB aggregation.
        
        Args:
            user_id: User ID
            time_range: Time range (7d, 30d, 90d)
            
        Returns:
            Statistics dictionary
        """
        # Parse time range
        days = int(time_range.rstrip('d'))
        date_from = datetime.utcnow() - timedelta(days=days)
        
        # Aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "created_at": {"$gte": date_from}
                }
            },
            {
                "$facet": {
                    "total_stats": [
                        {
                            "$group": {
                                "_id": None,
                                "total_validations": {"$sum": 1},
                                "average_score": {"$avg": "$score"},
                                "max_score": {"$max": "$score"},
                                "min_score": {"$min": "$score"},
                                "successful_validations": {
                                    "$sum": {
                                        "$cond": [{"$eq": ["$workflow_status", "completed"]}, 1, 0]
                                    }
                                },
                                "failed_validations": {
                                    "$sum": {
                                        "$cond": [{"$eq": ["$workflow_status", "failed"]}, 1, 0]
                                    }
                                }
                            }
                        }
                    ],
                    "top_targets": [
                        {
                            "$group": {
                                "_id": "$target_host",
                                "count": {"$sum": 1},
                                "avg_score": {"$avg": "$score"}
                            }
                        },
                        {"$sort": {"count": -1}},
                        {"$limit": 10}
                    ],
                    "score_distribution": [
                        {
                            "$bucket": {
                                "groupBy": "$score",
                                "boundaries": [0, 50, 70, 90, 101],
                                "default": "other",
                                "output": {
                                    "count": {"$sum": 1}
                                }
                            }
                        }
                    ]
                }
            }
        ]
        
        result = await self.db.validation_runs.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "total_validations": 0,
                "average_score": 0,
                "success_rate": 0,
                "top_targets": [],
                "score_distribution": [],
                "time_range": time_range
            }
        
        stats = result[0]
        total_stats = stats["total_stats"][0] if stats["total_stats"] else {}
        
        total = total_stats.get("total_validations", 0)
        success_count = total_stats.get("successful_validations", 0)
        
        return {
            "total_validations": total,
            "average_score": total_stats.get("average_score", 0),
            "max_score": total_stats.get("max_score", 0),
            "min_score": total_stats.get("min_score", 0),
            "success_rate": (success_count / total * 100) if total > 0 else 0,
            "top_targets": [
                {
                    "target_host": t["_id"],
                    "count": t["count"],
                    "avg_score": t["avg_score"]
                }
                for t in stats["top_targets"]
            ],
            "score_distribution": [
                {
                    "range": f"{d['_id']}-{d['_id']+19}" if isinstance(d['_id'], int) else str(d['_id']),
                    "count": d["count"]
                }
                for d in stats["score_distribution"]
            ],
            "time_range": time_range
        }
    
    async def compare_validation_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple validation runs.
        
        Args:
            run_ids: List of validation run IDs (ObjectId as strings)
            
        Returns:
            Comparison dictionary
        """
        runs = []
        for run_id in run_ids:
            run_data = await self.get_validation_run(run_id)
            if run_data:
                runs.append(run_data)
        
        if not runs:
            return {"error": "No valid runs found"}
        
        # Build comparison
        comparison = {
            "runs": runs,
            "summary": {
                "count": len(runs),
                "scores": [r["score"] for r in runs],
                "avg_score": sum(r["score"] for r in runs) / len(runs),
                "execution_times": [r["execution_time_seconds"] for r in runs]
            },
            "check_comparison": self._compare_checks(runs),
            "score_trend": self._analyze_score_trend(runs)
        }
        
        return comparison
    
    def _compare_checks(self, runs: List[Dict]) -> Dict[str, Any]:
        """Compare checks across runs."""
        all_check_names = set()
        for run in runs:
            for check in run.get("checks", []):
                all_check_names.add(check["check_name"])
        
        check_matrix = {}
        for check_name in all_check_names:
            check_matrix[check_name] = []
            for run in runs:
                check_status = next(
                    (c["status"] for c in run.get("checks", []) if c["check_name"] == check_name),
                    "N/A"
                )
                check_matrix[check_name].append(check_status)
        
        return check_matrix
    
    def _analyze_score_trend(self, runs: List[Dict]) -> Dict[str, Any]:
        """Analyze score trend across runs."""
        scores = [r["score"] for r in runs]
        
        if len(scores) < 2:
            return {"trend": "insufficient_data"}
        
        # Simple trend analysis
        improving = all(scores[i] <= scores[i+1] for i in range(len(scores)-1))
        declining = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
        
        if improving:
            trend = "improving"
        elif declining:
            trend = "declining"
        else:
            trend = "fluctuating"
        
        return {
            "trend": trend,
            "min_score": min(scores),
            "max_score": max(scores),
            "score_change": scores[-1] - scores[0]
        }
    
    async def save_user_session(self, session_data: Dict[str, Any]) -> str:
        """
        Save user session.
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            Session ID
        """
        session_data["created_at"] = datetime.utcnow()
        session_data["last_activity"] = datetime.utcnow()
        
        result = await self.db.user_sessions.insert_one(session_data)
        return str(result.inserted_id)
    
    async def update_session_activity(self, session_id: str):
        """Update session last activity timestamp."""
        await self.db.user_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"last_activity": datetime.utcnow()}}
        )
    
    async def log_audit_event(
        self,
        user_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log audit event.
        
        Args:
            user_id: User ID
            action: Action performed
            details: Additional details
            session_id: Session ID
            ip_address: IP address
            user_agent: User agent string
        """
        audit_entry = {
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow()
        }
        
        await self.db.audit_log.insert_one(audit_entry)

# Made with Bob
