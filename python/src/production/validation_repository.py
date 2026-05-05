"""
Validation History Repository

Handles persistence of validation runs, checks, and results to PostgreSQL.
"""

import asyncpg
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class ValidationHistoryRepository:
    """Repository for validation history operations."""
    
    def __init__(self, connection_string: str):
        """
        Initialize repository.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
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
            Validation run ID (UUID)
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Insert validation run
                run_id = await conn.fetchval(
                    """
                    INSERT INTO validation_runs (
                        user_id, session_id, target_host, credential_id,
                        score, status, workflow_status, execution_time_seconds
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id
                    """,
                    user_id,
                    session_id,
                    result.request.resource_info.host,
                    getattr(result.request.resource_info, 'credential_id', 'unknown'),
                    result.validation_result.score if result.validation_result else 0,
                    result.validation_result.overall_status if result.validation_result else 'unknown',
                    result.workflow_status,
                    result.execution_time_seconds
                )
                
                # Insert validation checks
                if result.validation_result and result.validation_result.checks:
                    for check in result.validation_result.checks:
                        await conn.execute(
                            """
                            INSERT INTO validation_checks (
                                run_id, check_name, status, message, expected, actual, severity
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            run_id,
                            check.check_name,
                            check.status,
                            check.message,
                            check.expected,
                            check.actual,
                            getattr(check, 'severity', 'info')
                        )
                
                # Insert discovery results
                if result.discovery_result and result.discovery_result.applications:
                    for app in result.discovery_result.applications:
                        await conn.execute(
                            """
                            INSERT INTO discovery_results (
                                run_id, application_name, confidence, evidence
                            ) VALUES ($1, $2, $3, $4)
                            """,
                            run_id,
                            app.name,
                            app.confidence,
                            json.dumps(getattr(app, 'evidence', {}))
                        )
                
                # Insert evaluation results
                if result.evaluation:
                    await conn.execute(
                        """
                        INSERT INTO evaluation_results (
                            run_id, overall_health, confidence, critical_issues, recommendations
                        ) VALUES ($1, $2, $3, $4, $5)
                        """,
                        run_id,
                        result.evaluation.overall_health,
                        result.evaluation.confidence,
                        json.dumps(result.evaluation.critical_issues),
                        json.dumps(result.evaluation.recommendations)
                    )
                
                logger.info(f"Validation run saved: {run_id}")
                return str(run_id)
    
    async def get_validation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get validation run by ID.
        
        Args:
            run_id: Validation run ID
            
        Returns:
            Validation run dictionary or None
        """
        async with self.pool.acquire() as conn:
            # Get run
            run = await conn.fetchrow(
                """
                SELECT * FROM validation_runs WHERE id = $1
                """,
                run_id
            )
            
            if not run:
                return None
            
            # Get checks
            checks = await conn.fetch(
                """
                SELECT * FROM validation_checks WHERE run_id = $1 ORDER BY created_at
                """,
                run_id
            )
            
            # Get discovery results
            discoveries = await conn.fetch(
                """
                SELECT * FROM discovery_results WHERE run_id = $1
                """,
                run_id
            )
            
            # Get evaluation
            evaluation = await conn.fetchrow(
                """
                SELECT * FROM evaluation_results WHERE run_id = $1
                """,
                run_id
            )
            
            return {
                "run": dict(run),
                "checks": [dict(c) for c in checks],
                "discoveries": [dict(d) for d in discoveries],
                "evaluation": dict(evaluation) if evaluation else None
            }
    
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
        query = """
            SELECT 
                id, target_host, credential_id, score, status, workflow_status,
                execution_time_seconds, created_at
            FROM validation_runs
            WHERE user_id = $1
        """
        params = [user_id]
        param_count = 1
        
        if filters:
            if filters.get('target_host'):
                param_count += 1
                query += f" AND target_host = ${param_count}"
                params.append(filters['target_host'])
            
            if filters.get('status'):
                param_count += 1
                query += f" AND status = ${param_count}"
                params.append(filters['status'])
            
            if filters.get('min_score') is not None:
                param_count += 1
                query += f" AND score >= ${param_count}"
                params.append(filters['min_score'])
            
            if filters.get('max_score') is not None:
                param_count += 1
                query += f" AND score <= ${param_count}"
                params.append(filters['max_score'])
            
            if filters.get('date_from'):
                param_count += 1
                query += f" AND created_at >= ${param_count}"
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                param_count += 1
                query += f" AND created_at <= ${param_count}"
                params.append(filters['date_to'])
        
        query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_validation_statistics(
        self,
        user_id: str,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """
        Get validation statistics.
        
        Args:
            user_id: User ID
            time_range: Time range (7d, 30d, 90d)
            
        Returns:
            Statistics dictionary
        """
        # Parse time range
        days = int(time_range.rstrip('d'))
        date_from = datetime.utcnow() - timedelta(days=days)
        
        async with self.pool.acquire() as conn:
            # Total validations
            total = await conn.fetchval(
                """
                SELECT COUNT(*) FROM validation_runs
                WHERE user_id = $1 AND created_at >= $2
                """,
                user_id, date_from
            )
            
            # Average score
            avg_score = await conn.fetchval(
                """
                SELECT AVG(score) FROM validation_runs
                WHERE user_id = $1 AND created_at >= $2
                """,
                user_id, date_from
            )
            
            # Success rate
            success_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM validation_runs
                WHERE user_id = $1 AND created_at >= $2 AND workflow_status = 'completed'
                """,
                user_id, date_from
            )
            
            # Top targets
            top_targets = await conn.fetch(
                """
                SELECT target_host, COUNT(*) as count, AVG(score) as avg_score
                FROM validation_runs
                WHERE user_id = $1 AND created_at >= $2
                GROUP BY target_host
                ORDER BY count DESC
                LIMIT 10
                """,
                user_id, date_from
            )
            
            # Score distribution
            score_dist = await conn.fetch(
                """
                SELECT 
                    CASE 
                        WHEN score >= 90 THEN '90-100'
                        WHEN score >= 70 THEN '70-89'
                        WHEN score >= 50 THEN '50-69'
                        ELSE '0-49'
                    END as range,
                    COUNT(*) as count
                FROM validation_runs
                WHERE user_id = $1 AND created_at >= $2
                GROUP BY range
                ORDER BY range DESC
                """,
                user_id, date_from
            )
            
            return {
                "total_validations": total,
                "average_score": float(avg_score) if avg_score else 0,
                "success_rate": (success_count / total * 100) if total > 0 else 0,
                "top_targets": [dict(row) for row in top_targets],
                "score_distribution": [dict(row) for row in score_dist],
                "time_range": time_range
            }
    
    async def compare_validation_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple validation runs.
        
        Args:
            run_ids: List of validation run IDs
            
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
                "scores": [r["run"]["score"] for r in runs],
                "avg_score": sum(r["run"]["score"] for r in runs) / len(runs),
                "execution_times": [r["run"]["execution_time_seconds"] for r in runs]
            },
            "check_comparison": self._compare_checks(runs),
            "score_trend": self._analyze_score_trend(runs)
        }
        
        return comparison
    
    def _compare_checks(self, runs: List[Dict]) -> Dict[str, Any]:
        """Compare checks across runs."""
        all_check_names = set()
        for run in runs:
            for check in run["checks"]:
                all_check_names.add(check["check_name"])
        
        check_matrix = {}
        for check_name in all_check_names:
            check_matrix[check_name] = []
            for run in runs:
                check_status = next(
                    (c["status"] for c in run["checks"] if c["check_name"] == check_name),
                    "N/A"
                )
                check_matrix[check_name].append(check_status)
        
        return check_matrix
    
    def _analyze_score_trend(self, runs: List[Dict]) -> Dict[str, Any]:
        """Analyze score trend across runs."""
        scores = [r["run"]["score"] for r in runs]
        
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

# Made with Bob
