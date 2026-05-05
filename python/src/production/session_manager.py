"""
Production Session Manager for Chainlit UI

Provides per-user session isolation with automatic cleanup and resource management.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage user sessions with isolated state."""
    
    def __init__(self, max_age_minutes: int = 60, cleanup_interval_minutes: int = 10):
        """
        Initialize session manager.
        
        Args:
            max_age_minutes: Maximum session age before cleanup
            cleanup_interval_minutes: Interval between cleanup runs
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._max_age_minutes = max_age_minutes
        self._cleanup_interval_minutes = cleanup_interval_minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session manager started")
    
    async def stop(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Session manager stopped")
    
    async def create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new user session.
        
        Args:
            session_id: Optional session ID (generated if not provided)
            user_id: Optional user ID
            
        Returns:
            Session dictionary
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        async with self._lock:
            session = {
                "id": session_id,
                "user_id": user_id,
                "cli_wrapper": None,
                "mcp_client": None,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "validation_history": [],
                "user_preferences": {},
                "metadata": {}
            }
            self._sessions[session_id] = session
            logger.info(f"Session created: {session_id}")
            return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get existing session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session dictionary or None if not found
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Update last activity
                session["last_activity"] = datetime.utcnow()
            return session
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        """
        Update session data.
        
        Args:
            session_id: Session ID
            updates: Dictionary of updates to apply
        """
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].update(updates)
                self._sessions[session_id]["last_activity"] = datetime.utcnow()
                logger.debug(f"Session updated: {session_id}")
    
    async def add_validation_to_history(self, session_id: str, validation_result: Dict[str, Any]):
        """
        Add validation result to session history.
        
        Args:
            session_id: Session ID
            validation_result: Validation result dictionary
        """
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["validation_history"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": validation_result
                })
                # Keep only last 50 validations in memory
                if len(self._sessions[session_id]["validation_history"]) > 50:
                    self._sessions[session_id]["validation_history"] = \
                        self._sessions[session_id]["validation_history"][-50:]
    
    async def cleanup_session(self, session_id: str):
        """
        Cleanup session resources.
        
        Args:
            session_id: Session ID to cleanup
        """
        async with self._lock:
            if session_id not in self._sessions:
                return
            
            session = self._sessions[session_id]
            
            try:
                # Cleanup orchestrator
                if session.get("cli_wrapper") and hasattr(session["cli_wrapper"], "orchestrator"):
                    if session["cli_wrapper"].orchestrator:
                        await session["cli_wrapper"].orchestrator.cleanup()
                        logger.debug(f"Orchestrator cleaned up for session {session_id}")
                
                # Cleanup MCP client
                if session.get("mcp_client"):
                    if hasattr(session["mcp_client"], "is_connected") and session["mcp_client"].is_connected():
                        await session["mcp_client"].disconnect()
                        logger.debug(f"MCP client disconnected for session {session_id}")
                
                # Remove session
                del self._sessions[session_id]
                logger.info(f"Session cleaned up: {session_id}")
                
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")
                # Still remove the session even if cleanup fails
                if session_id in self._sessions:
                    del self._sessions[session_id]
    
    async def cleanup_stale_sessions(self):
        """Cleanup sessions inactive for too long."""
        now = datetime.utcnow()
        stale_sessions = []
        
        async with self._lock:
            for session_id, session in self._sessions.items():
                age = (now - session["last_activity"]).total_seconds() / 60
                if age > self._max_age_minutes:
                    stale_sessions.append(session_id)
        
        # Cleanup outside the lock to avoid blocking
        for session_id in stale_sessions:
            logger.info(f"Cleaning up stale session: {session_id}")
            await self.cleanup_session(session_id)
        
        if stale_sessions:
            logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")
    
    async def _cleanup_loop(self):
        """Background task to cleanup stale sessions."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_minutes * 60)
                await self.cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        now = datetime.utcnow()
        
        total_sessions = len(self._sessions)
        active_sessions = 0
        idle_sessions = 0
        
        for session in self._sessions.values():
            age_minutes = (now - session["last_activity"]).total_seconds() / 60
            if age_minutes < 5:  # Active in last 5 minutes
                active_sessions += 1
            else:
                idle_sessions += 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "idle_sessions": idle_sessions,
            "max_age_minutes": self._max_age_minutes
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def initialize_session_manager():
    """Initialize and start session manager."""
    manager = get_session_manager()
    await manager.start()
    return manager


async def shutdown_session_manager():
    """Shutdown session manager."""
    manager = get_session_manager()
    await manager.stop()

# Made with Bob
