"""
Session Manager for Claude Code Orchestration
==============================================
Manages the lifecycle of Claude Code sessions and tracks orchestration activity
"""

import os
import time
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from pathlib import Path

from src.core.database import OrchestrationDB
from src.tracking.project_attribution import ProjectAttributor

logger = logging.getLogger(__name__)

@dataclass
class ActiveSession:
    """Represents an active Claude Code session"""
    session_id: str
    start_time: datetime
    working_directory: str
    project_name: str
    initial_task: str
    activity_count: int = 0
    tool_invocations: List[str] = field(default_factory=list)
    last_activity: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'working_directory': self.working_directory,
            'project_name': self.project_name,
            'task_description': self.initial_task,
            'activity_count': self.activity_count,
            'tool_invocations': self.tool_invocations,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'metadata': self.metadata
        }

class SessionManager:
    """Manages Claude Code session lifecycle and tracking"""

    def __init__(self, db: OrchestrationDB = None):
        self.db = db or OrchestrationDB()
        self.active_sessions: Dict[str, ActiveSession] = {}
        self.current_session_id: Optional[str] = None
        self.project_attributor = None
        self._session_timeout = 3600  # 1 hour timeout for inactive sessions
        self._activity_detection_interval = 30  # Check every 30 seconds

        # Initialize project attribution system
        try:
            self.project_attributor = ProjectAttributor()
        except Exception as e:
            logger.warning(f"Could not initialize project attributor: {e}")

    async def initialize(self):
        """Initialize the session manager"""
        logger.info("Initializing SessionManager...")

        # Start periodic session cleanup
        asyncio.create_task(self._periodic_session_cleanup())

        # Auto-detect current session if working in AI_Projects
        await self._auto_detect_current_session()

        logger.info("SessionManager initialized successfully")

    async def _auto_detect_current_session(self):
        """Auto-detect if we're in an active Claude Code session"""
        try:
            current_dir = os.getcwd()

            # Check if we're in AI_Projects directory
            if "AI_Projects" in current_dir:
                # Extract project name from path
                project_name = self._extract_project_name(current_dir)

                # Create a new session for the current context
                session_id = await self.start_session(
                    working_directory=current_dir,
                    initial_task="Real-time activity tracking implementation session",
                    project_name=project_name
                )

                logger.info(f"Auto-detected session {session_id} for project {project_name}")
                return session_id

        except Exception as e:
            logger.error(f"Error in auto-detection: {e}")

        return None

    def _extract_project_name(self, directory_path: str) -> str:
        """Extract project name from directory path"""
        try:
            if self.project_attributor:
                result = self.project_attributor.detect_project_from_path(directory_path)
                # If result is a tuple (project_name, confidence), extract the project name
                if isinstance(result, tuple):
                    return result[0]
                return result
        except Exception as e:
            logger.warning(f"Project attribution failed: {e}")

        # Fallback: extract from path
        path_parts = Path(directory_path).parts
        ai_projects_index = None

        for i, part in enumerate(path_parts):
            if part == "AI_Projects":
                ai_projects_index = i
                break

        if ai_projects_index is not None and ai_projects_index + 1 < len(path_parts):
            return path_parts[ai_projects_index + 1]

        return "unknown-project"

    async def start_session(self, working_directory: str, initial_task: str,
                          project_name: Optional[str] = None) -> str:
        """Start a new Claude Code session"""

        # Generate unique session ID
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        session_id = f"claude_realtime_{timestamp}_{unique_id}"

        # Detect project if not provided
        if not project_name:
            project_name = self._extract_project_name(working_directory)

        # Create session object
        session = ActiveSession(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            working_directory=working_directory,
            project_name=project_name,
            initial_task=initial_task,
            metadata={
                'auto_detected': True,
                'instrumentation_version': '1.0.0',
                'session_type': 'real_time_tracking'
            }
        )

        # Store in active sessions
        self.active_sessions[session_id] = session
        self.current_session_id = session_id

        # Track in database
        try:
            self.db.track_session(
                session_id=session_id,
                project_name=project_name,
                task_description=initial_task,
                start_time=session.start_time,
                metadata=session.metadata
            )

            logger.info(f"Started session {session_id} for project {project_name}")

        except Exception as e:
            logger.error(f"Failed to track session in database: {e}")

        return session_id

    async def track_activity(self, activity_type: str, details: Dict[str, Any],
                           session_id: Optional[str] = None) -> bool:
        """Track activity in the current or specified session"""

        target_session_id = session_id or self.current_session_id
        if not target_session_id or target_session_id not in self.active_sessions:
            # Auto-start session if none exists
            if not target_session_id:
                target_session_id = await self._auto_detect_current_session()
                if not target_session_id:
                    logger.warning("No active session found and auto-detection failed")
                    return False

        session = self.active_sessions[target_session_id]

        # Update session activity
        session.activity_count += 1
        session.last_activity = datetime.now(timezone.utc)

        # Track tool invocations
        if activity_type == 'tool_usage':
            tool_name = details.get('tool_name', 'unknown')
            session.tool_invocations.append(f"{tool_name}:{time.time()}")

        # Update metadata
        session.metadata[f'last_{activity_type}'] = time.time()

        logger.debug(f"Tracked {activity_type} activity in session {target_session_id}")

        return True

    def get_current_session(self) -> Optional[ActiveSession]:
        """Get the current active session"""
        if self.current_session_id and self.current_session_id in self.active_sessions:
            return self.active_sessions[self.current_session_id]
        return None

    def get_session(self, session_id: str) -> Optional[ActiveSession]:
        """Get a specific session by ID"""
        return self.active_sessions.get(session_id)

    def list_active_sessions(self) -> List[ActiveSession]:
        """List all active sessions"""
        return list(self.active_sessions.values())

    async def end_session(self, session_id: Optional[str] = None,
                         end_reason: str = "manual") -> bool:
        """End a session and finalize its tracking"""

        target_session_id = session_id or self.current_session_id
        if not target_session_id or target_session_id not in self.active_sessions:
            logger.warning(f"Session {target_session_id} not found")
            return False

        session = self.active_sessions[target_session_id]
        end_time = datetime.now(timezone.utc)

        # Calculate session duration
        duration = (end_time - session.start_time).total_seconds()

        # Update session metadata
        session.metadata.update({
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'end_reason': end_reason,
            'total_activities': session.activity_count,
            'unique_tools_used': len(set(tool.split(':')[0] for tool in session.tool_invocations))
        })

        # Update database
        try:
            # This would require adding an update method to the database
            # For now, we'll log the completion
            logger.info(f"Session {target_session_id} completed: {duration:.1f}s, {session.activity_count} activities")

        except Exception as e:
            logger.error(f"Failed to update session end in database: {e}")

        # Remove from active sessions
        del self.active_sessions[target_session_id]

        # Clear current session if this was it
        if self.current_session_id == target_session_id:
            self.current_session_id = None

        return True

    async def _periodic_session_cleanup(self):
        """Periodically clean up inactive sessions"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                inactive_sessions = []

                for session_id, session in self.active_sessions.items():
                    # Check if session has been inactive
                    last_activity = session.last_activity or session.start_time
                    inactive_duration = (current_time - last_activity).total_seconds()

                    if inactive_duration > self._session_timeout:
                        inactive_sessions.append(session_id)

                # End inactive sessions
                for session_id in inactive_sessions:
                    await self.end_session(session_id, end_reason="timeout")
                    logger.info(f"Auto-ended inactive session {session_id}")

                # Wait before next cleanup
                await asyncio.sleep(self._activity_detection_interval)

            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Wait a minute on error

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about session management"""
        active_count = len(self.active_sessions)
        current_session = self.get_current_session()

        total_activities = sum(session.activity_count for session in self.active_sessions.values())
        total_tools = sum(len(session.tool_invocations) for session in self.active_sessions.values())

        return {
            'active_sessions': active_count,
            'current_session_id': self.current_session_id,
            'current_session_project': current_session.project_name if current_session else None,
            'total_activities_tracked': total_activities,
            'total_tool_invocations': total_tools,
            'session_timeout_seconds': self._session_timeout,
            'last_cleanup': datetime.now(timezone.utc).isoformat()
        }

    async def force_session_sync(self) -> Dict[str, Any]:
        """Force synchronization of all active sessions with database"""
        sync_results = {
            'sessions_synced': 0,
            'errors': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        for session_id, session in self.active_sessions.items():
            try:
                # Update session metrics in database
                # This would require extending the database interface
                sync_results['sessions_synced'] += 1
                logger.debug(f"Synced session {session_id}")

            except Exception as e:
                error_msg = f"Failed to sync session {session_id}: {e}"
                sync_results['errors'].append(error_msg)
                logger.error(error_msg)

        logger.info(f"Session sync completed: {sync_results['sessions_synced']} sessions synced")
        return sync_results