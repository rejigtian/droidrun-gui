"""
Session manager for tracking DroidAgent execution sessions.

This module manages the lifecycle of agent sessions, storing metadata
and providing thread-safe access to session information.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from droidrun.backend.models import AgentRunRequest, AgentSession, SessionStatus

logger = logging.getLogger("droidrun.backend")


class SessionManager:
    """
    Manages agent execution sessions.

    This class tracks active and completed sessions, providing thread-safe
    access to session metadata and status information.
    """

    def __init__(self):
        """Initialize the session manager."""
        self._sessions: dict[str, AgentSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, config: AgentRunRequest) -> AgentSession:
        """
        Create a new agent session.

        Args:
            config: Agent configuration

        Returns:
            Created AgentSession
        """
        async with self._lock:
            session_id = str(uuid.uuid4())

            session = AgentSession(
                session_id=session_id,
                goal=config.goal,
                status=SessionStatus.PENDING,
                created_at=datetime.now(),
                config=config,
            )

            self._sessions[session_id] = session
            logger.info(f"Created session {session_id} for goal: {config.goal}")

            return session

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            AgentSession or None if not found
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_session_status(
        self, session_id: str, status: SessionStatus, error: Optional[str] = None
    ) -> bool:
        """
        Update session status.

        Args:
            session_id: Session identifier
            status: New status
            error: Error message if status is FAILED

        Returns:
            True if updated, False if session not found
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            session.status = status

            if status == SessionStatus.RUNNING and not session.started_at:
                session.started_at = datetime.now()

            if status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.STOPPED):
                session.completed_at = datetime.now()

            if error:
                session.error = error

            logger.info(f"Session {session_id} status updated to {status.value}")
            return True

    async def list_sessions(
        self, status_filter: Optional[SessionStatus] = None, limit: Optional[int] = None
    ) -> list[AgentSession]:
        """
        List all sessions with optional filtering.

        Args:
            status_filter: Filter by status
            limit: Maximum number of sessions to return

        Returns:
            List of AgentSession objects
        """
        async with self._lock:
            sessions = list(self._sessions.values())

            # Filter by status if specified
            if status_filter:
                sessions = [s for s in sessions if s.status == status_filter]

            # Sort by creation time (most recent first)
            sessions.sort(key=lambda s: s.created_at, reverse=True)

            # Apply limit if specified
            if limit:
                sessions = sessions[:limit]

            return sessions

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session {session_id}")
                return True
            return False

    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old sessions.

        Args:
            max_age_hours: Maximum age in hours for sessions to keep

        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta

        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=max_age_hours)

            to_delete = [
                session_id
                for session_id, session in self._sessions.items()
                if session.created_at < cutoff
                and session.status
                in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.STOPPED)
            ]

            for session_id in to_delete:
                del self._sessions[session_id]

            if to_delete:
                logger.info(f"Cleaned up {len(to_delete)} old sessions")

            return len(to_delete)

    async def get_session_count(self, status: Optional[SessionStatus] = None) -> int:
        """
        Get count of sessions.

        Args:
            status: Filter by status (optional)

        Returns:
            Number of sessions
        """
        async with self._lock:
            if status:
                return sum(1 for s in self._sessions.values() if s.status == status)
            return len(self._sessions)

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists
        """
        async with self._lock:
            return session_id in self._sessions


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    Returns:
        SessionManager singleton
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
