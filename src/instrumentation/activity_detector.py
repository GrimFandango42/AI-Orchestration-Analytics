"""
Activity Detector for Claude Code Orchestration
===============================================
Comprehensive detection and classification of Claude Code activities including:
- Tool usage (Read, Write, Edit, Bash)
- Process monitoring for Bash commands
- Session boundaries and task completion
- Real-time activity correlation
"""

import os
import psutil
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path

from .file_monitor import FileSystemMonitor, FileActivity
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

@dataclass
class DetectedActivity:
    """Unified representation of detected activity"""
    activity_id: str
    activity_type: str  # 'file_operation', 'process_execution', 'session_event', 'user_interaction'
    tool_name: str  # 'Read', 'Write', 'Edit', 'Bash', 'Task', etc.
    timestamp: datetime
    session_id: Optional[str]
    details: Dict[str, Any]
    confidence: float
    source: str  # 'file_monitor', 'process_monitor', 'session_manager'
    raw_data: Any = None

class ProcessMonitor:
    """Monitor process execution for Bash tool detection"""

    def __init__(self):
        self.monitored_processes: Dict[int, Dict] = {}
        self.recent_commands: List[Dict] = []
        self.monitoring = False
        self.check_interval = 1.0  # Check every second

    async def start_monitoring(self):
        """Start process monitoring"""
        self.monitoring = True
        asyncio.create_task(self._monitor_processes())
        logger.info("Process monitoring started")

    async def _monitor_processes(self):
        """Continuously monitor for new processes"""
        while self.monitoring:
            try:
                current_processes = set(psutil.pids())

                for pid in current_processes:
                    if pid not in self.monitored_processes:
                        try:
                            process = psutil.Process(pid)
                            process_info = self._get_process_info(process)

                            if self._should_track_process(process_info):
                                self.monitored_processes[pid] = process_info
                                await self._on_process_detected(process_info)

                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

                # Clean up completed processes
                self._cleanup_completed_processes()

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                await asyncio.sleep(5)

    def _get_process_info(self, process: psutil.Process) -> Dict:
        """Extract process information"""
        try:
            return {
                'pid': process.pid,
                'name': process.name(),
                'cmdline': process.cmdline(),
                'cwd': process.cwd() if hasattr(process, 'cwd') else None,
                'create_time': process.create_time(),
                'parent_pid': process.ppid(),
                'status': process.status(),
                'detected_at': time.time()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}

    def _should_track_process(self, process_info: Dict) -> bool:
        """Determine if process should be tracked as tool usage"""
        if not process_info:
            return False

        name = process_info.get('name', '').lower()
        cmdline = ' '.join(process_info.get('cmdline', [])).lower()

        # Track shell commands and development tools
        tracked_processes = {
            'cmd.exe', 'powershell.exe', 'bash.exe', 'sh.exe', 'zsh.exe',
            'python.exe', 'node.exe', 'npm.exe', 'yarn.exe', 'pnpm.exe',
            'git.exe', 'docker.exe', 'kubectl.exe',
            'pytest.exe', 'jest.exe', 'mocha.exe',
            'curl.exe', 'wget.exe', 'ping.exe', 'netstat.exe'
        }

        if name in tracked_processes:
            return True

        # Track if command line contains development-related keywords
        dev_keywords = {
            'python', 'node', 'npm', 'git', 'docker', 'test', 'build',
            'install', 'run', 'start', 'dev', 'serve', 'deploy'
        }

        return any(keyword in cmdline for keyword in dev_keywords)

    async def _on_process_detected(self, process_info: Dict):
        """Handle detected process"""
        command_summary = {
            'pid': process_info['pid'],
            'command': ' '.join(process_info.get('cmdline', [])),
            'timestamp': datetime.now(timezone.utc),
            'cwd': process_info.get('cwd'),
            'tool_classification': self._classify_command_as_tool(process_info)
        }

        self.recent_commands.append(command_summary)

        # Keep only recent commands (last 100)
        if len(self.recent_commands) > 100:
            self.recent_commands = self.recent_commands[-100:]

        logger.debug(f"Detected command: {command_summary['command']}")

    def _classify_command_as_tool(self, process_info: Dict) -> str:
        """Classify command as Claude Code tool usage"""
        cmdline = ' '.join(process_info.get('cmdline', [])).lower()

        # Classification logic
        if any(term in cmdline for term in ['git', 'clone', 'pull', 'push', 'commit']):
            return 'Bash'  # Git operations
        elif any(term in cmdline for term in ['python', 'node', 'npm', 'run']):
            return 'Bash'  # Script execution
        elif any(term in cmdline for term in ['test', 'pytest', 'jest']):
            return 'Bash'  # Testing
        elif any(term in cmdline for term in ['build', 'compile', 'make']):
            return 'Bash'  # Build operations
        else:
            return 'Bash'  # Generic bash command

    def _cleanup_completed_processes(self):
        """Clean up processes that are no longer running"""
        completed_pids = []
        for pid in self.monitored_processes:
            try:
                process = psutil.Process(pid)
                if not process.is_running():
                    completed_pids.append(pid)
            except psutil.NoSuchProcess:
                completed_pids.append(pid)

        for pid in completed_pids:
            del self.monitored_processes[pid]

    def get_recent_commands(self, limit: int = 20) -> List[Dict]:
        """Get recent command executions"""
        return self.recent_commands[-limit:] if self.recent_commands else []

    async def stop_monitoring(self):
        """Stop process monitoring"""
        self.monitoring = False
        logger.info("Process monitoring stopped")

class ActivityDetector:
    """Main activity detector orchestrating all monitoring systems"""

    def __init__(self, session_manager: SessionManager = None):
        self.session_manager = session_manager or SessionManager()
        self.file_monitor = FileSystemMonitor(callback=self._on_file_activity)
        self.process_monitor = ProcessMonitor()

        self.detected_activities: List[DetectedActivity] = []
        self.activity_callbacks: List[callable] = []
        self.is_active = False

        # Activity correlation
        self.activity_correlation_window = 5.0  # seconds
        self.last_activity_time = 0

    async def initialize(self):
        """Initialize all monitoring components"""
        logger.info("Initializing ActivityDetector...")

        # Initialize session manager
        await self.session_manager.initialize()

        # Start file system monitoring
        await self.file_monitor.start_monitoring()

        # Start process monitoring
        await self.process_monitor.start_monitoring()

        self.is_active = True

        # Start activity correlation
        asyncio.create_task(self._correlate_activities())

        logger.info("ActivityDetector initialized successfully")

    def add_activity_callback(self, callback: callable):
        """Add callback for when activities are detected"""
        self.activity_callbacks.append(callback)

    async def _on_file_activity(self, file_activity: FileActivity):
        """Handle file system activity detection"""
        current_session = self.session_manager.get_current_session()
        session_id = current_session.session_id if current_session else None

        # Create unified activity record
        activity = DetectedActivity(
            activity_id=f"file_{int(time.time() * 1000)}_{id(file_activity)}",
            activity_type='file_operation',
            tool_name=file_activity.estimated_tool,
            timestamp=file_activity.timestamp,
            session_id=session_id,
            details={
                'file_path': file_activity.file_path,
                'operation_type': file_activity.activity_type,
                'file_size': file_activity.file_size,
                'relative_path': file_activity.metadata.get('relative_path'),
                'file_extension': file_activity.metadata.get('file_extension')
            },
            confidence=file_activity.confidence,
            source='file_monitor',
            raw_data=file_activity
        )

        await self._process_detected_activity(activity)

    async def _correlate_activities(self):
        """Correlate activities to detect complex tool usage patterns"""
        while self.is_active:
            try:
                # Look for activity patterns in recent activities
                recent_activities = self.get_recent_activities(limit=10)

                if len(recent_activities) >= 2:
                    patterns = self._detect_activity_patterns(recent_activities)
                    for pattern in patterns:
                        await self._process_pattern_detection(pattern)

                await asyncio.sleep(2)  # Check every 2 seconds

            except Exception as e:
                logger.error(f"Error in activity correlation: {e}")
                await asyncio.sleep(5)

    def _detect_activity_patterns(self, activities: List[DetectedActivity]) -> List[Dict]:
        """Detect patterns in recent activities"""
        patterns = []

        # Pattern 1: Multiple file operations in quick succession (Edit tool usage)
        file_ops = [a for a in activities if a.activity_type == 'file_operation']
        if len(file_ops) >= 3:
            time_span = (file_ops[-1].timestamp - file_ops[0].timestamp).total_seconds()
            if time_span < 10:  # Within 10 seconds
                patterns.append({
                    'type': 'bulk_edit_pattern',
                    'activities': file_ops,
                    'confidence': 0.8,
                    'inferred_tool': 'Edit'
                })

        # Pattern 2: Process followed by file changes (Bash tool usage)
        process_activities = [a for a in activities if a.activity_type == 'process_execution']
        if process_activities and file_ops:
            for proc_activity in process_activities:
                subsequent_files = [
                    f for f in file_ops
                    if f.timestamp > proc_activity.timestamp
                    and (f.timestamp - proc_activity.timestamp).total_seconds() < 30
                ]
                if subsequent_files:
                    patterns.append({
                        'type': 'bash_with_file_output_pattern',
                        'trigger_process': proc_activity,
                        'resulting_files': subsequent_files,
                        'confidence': 0.9,
                        'inferred_tool': 'Bash'
                    })

        return patterns

    async def _process_pattern_detection(self, pattern: Dict):
        """Process detected activity patterns"""
        current_session = self.session_manager.get_current_session()
        session_id = current_session.session_id if current_session else None

        pattern_activity = DetectedActivity(
            activity_id=f"pattern_{int(time.time() * 1000)}",
            activity_type='pattern_detection',
            tool_name=pattern['inferred_tool'],
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            details={
                'pattern_type': pattern['type'],
                'activity_count': len(pattern.get('activities', [])),
                'description': f"Detected {pattern['type']} indicating {pattern['inferred_tool']} usage"
            },
            confidence=pattern['confidence'],
            source='activity_correlator',
            raw_data=pattern
        )

        await self._process_detected_activity(pattern_activity)

    async def _process_detected_activity(self, activity: DetectedActivity):
        """Process and store detected activity"""
        # Store activity
        self.detected_activities.append(activity)

        # Keep only recent activities (last 1000)
        if len(self.detected_activities) > 1000:
            self.detected_activities = self.detected_activities[-1000:]

        # Update session activity tracking
        if activity.session_id:
            await self.session_manager.track_activity(
                activity_type=activity.activity_type,
                details=activity.details
            )

        # Notify callbacks
        for callback in self.activity_callbacks:
            try:
                await callback(activity)
            except Exception as e:
                logger.error(f"Error in activity callback: {e}")

        logger.debug(f"Processed {activity.tool_name} activity: {activity.activity_type}")

    def get_recent_activities(self, limit: int = 50) -> List[DetectedActivity]:
        """Get recent detected activities"""
        return self.detected_activities[-limit:] if self.detected_activities else []

    def get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of detected activities"""
        if not self.detected_activities:
            return {
                'total_activities': 0,
                'by_tool': {},
                'by_type': {},
                'session_info': {},
                'monitoring_status': {
                    'file_monitor': self.file_monitor.is_monitoring,
                    'process_monitor': self.process_monitor.monitoring,
                    'is_active': self.is_active
                }
            }

        # Aggregate by tool
        by_tool = {}
        by_type = {}
        by_source = {}

        for activity in self.detected_activities:
            # By tool
            tool = activity.tool_name
            by_tool[tool] = by_tool.get(tool, 0) + 1

            # By type
            activity_type = activity.activity_type
            by_type[activity_type] = by_type.get(activity_type, 0) + 1

            # By source
            source = activity.source
            by_source[source] = by_source.get(source, 0) + 1

        # Session info
        current_session = self.session_manager.get_current_session()
        session_info = current_session.to_dict() if current_session else {}

        return {
            'total_activities': len(self.detected_activities),
            'by_tool': by_tool,
            'by_type': by_type,
            'by_source': by_source,
            'session_info': session_info,
            'monitoring_status': {
                'file_monitor': self.file_monitor.is_monitoring,
                'process_monitor': self.process_monitor.monitoring,
                'is_active': self.is_active
            },
            'file_monitor_stats': self.file_monitor.get_activity_stats(),
            'recent_commands': self.process_monitor.get_recent_commands(limit=10)
        }

    async def force_activity_sync(self) -> Dict[str, Any]:
        """Force synchronization of detected activities"""
        # This would sync all detected activities to the database
        # For now, return summary of what would be synced

        activities_to_sync = [
            a for a in self.detected_activities
            if a.session_id and a.activity_type in ['file_operation', 'process_execution']
        ]

        return {
            'activities_to_sync': len(activities_to_sync),
            'session_activities': len([a for a in activities_to_sync if a.session_id]),
            'file_operations': len([a for a in activities_to_sync if a.activity_type == 'file_operation']),
            'process_executions': len([a for a in activities_to_sync if a.activity_type == 'process_execution']),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    async def shutdown(self):
        """Shutdown all monitoring"""
        self.is_active = False

        await self.file_monitor.stop_monitoring()
        await self.process_monitor.stop_monitoring()

        # End current session
        current_session = self.session_manager.get_current_session()
        if current_session:
            await self.session_manager.end_session(
                session_id=current_session.session_id,
                end_reason="shutdown"
            )

        logger.info("ActivityDetector shutdown complete")