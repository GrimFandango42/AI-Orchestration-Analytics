"""
File System Monitor for Claude Code Tool Detection
==================================================
Monitors file system changes to detect Read, Write, Edit tool usage in real-time
"""

import os
import time
import asyncio
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Set, List, Optional, Any, Callable
from dataclasses import dataclass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

logger = logging.getLogger(__name__)

@dataclass
class FileActivity:
    """Represents a detected file activity"""
    file_path: str
    activity_type: str  # 'read', 'write', 'edit', 'create', 'delete'
    timestamp: datetime
    file_size: int
    file_hash: Optional[str] = None
    estimated_tool: str = 'unknown'  # 'Read', 'Write', 'Edit'
    confidence: float = 0.8
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class FileSystemMonitor:
    """Monitors file system for Claude Code tool usage"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.observer = Observer()
        self.event_handler = ClaudeFileEventHandler(self._on_file_activity)
        self.monitored_paths: Set[str] = set()
        self.file_hashes: Dict[str, str] = {}
        self.file_access_times: Dict[str, float] = {}
        self.recent_activities: List[FileActivity] = []
        self.is_monitoring = False

        # File patterns to monitor
        self.monitored_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.php', '.rb', '.go', '.rs', '.kt', '.swift', '.scala',
            '.html', '.css', '.scss', '.sass', '.less',
            '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.md', '.txt', '.rst', '.tex', '.doc', '.docx',
            '.sql', '.db', '.sqlite', '.sqlite3',
            '.sh', '.bat', '.ps1', '.cmd'
        }

        # Directories to ignore
        self.ignored_dirs = {
            '.git', '.svn', '.hg', '__pycache__', '.pytest_cache',
            'node_modules', '.venv', 'venv', '.env',
            '.idea', '.vscode', '.vs',
            'build', 'dist', 'target', 'bin', 'obj',
            '.next', '.nuxt', '.tmp', 'temp', 'tmp'
        }

        # Activity debouncing (prevent duplicate events)
        self.debounce_delay = 0.5  # seconds
        self.pending_events: Dict[str, float] = {}

    async def start_monitoring(self, paths: List[str] = None):
        """Start monitoring specified paths or auto-detect current working directory"""
        if not paths:
            # Auto-detect current working directory
            current_dir = os.getcwd()
            if "AI_Projects" in current_dir:
                paths = [current_dir]
            else:
                logger.warning("Not in AI_Projects directory, monitoring may be limited")
                paths = [current_dir]

        for path in paths:
            if os.path.exists(path):
                self.add_watch_path(path)

        if not self.monitored_paths:
            logger.error("No valid paths to monitor")
            return False

        # Start the observer
        self.observer.start()
        self.is_monitoring = True

        # Start activity processing
        asyncio.create_task(self._process_pending_events())

        logger.info(f"File monitoring started for {len(self.monitored_paths)} paths")
        return True

    def add_watch_path(self, path: str):
        """Add a path to monitor"""
        if os.path.isdir(path):
            self.observer.schedule(self.event_handler, path, recursive=True)
            self.monitored_paths.add(path)

            # Build initial file hash index
            self._index_existing_files(path)

            logger.info(f"Added watch path: {path}")
        else:
            logger.warning(f"Path does not exist: {path}")

    def _index_existing_files(self, root_path: str):
        """Build an index of existing files and their hashes"""
        try:
            for root, dirs, files in os.walk(root_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignored_dirs]

                for file in files:
                    file_path = os.path.join(root, file)
                    if self._should_monitor_file(file_path):
                        try:
                            file_hash = self._calculate_file_hash(file_path)
                            self.file_hashes[file_path] = file_hash
                        except Exception as e:
                            logger.debug(f"Could not hash file {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error indexing files in {root_path}: {e}")

    def _should_monitor_file(self, file_path: str) -> bool:
        """Determine if a file should be monitored"""
        # Check extension
        _, ext = os.path.splitext(file_path.lower())
        if ext not in self.monitored_extensions:
            return False

        # Check if in ignored directory
        path_parts = Path(file_path).parts
        for part in path_parts:
            if part in self.ignored_dirs:
                return False

        # Check file size (skip very large files)
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return False
        except OSError:
            return False

        return True

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file content"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def _on_file_activity(self, event):
        """Handle file system events"""
        if not self.is_monitoring:
            return

        file_path = event.src_path
        if not self._should_monitor_file(file_path):
            return

        # Debounce events
        current_time = time.time()
        if file_path in self.pending_events:
            if current_time - self.pending_events[file_path] < self.debounce_delay:
                return

        self.pending_events[file_path] = current_time

        # Schedule processing
        asyncio.create_task(self._process_file_event(event))

    async def _process_file_event(self, event):
        """Process a file system event and classify tool usage"""
        file_path = event.src_path
        current_time = datetime.now(timezone.utc)

        try:
            # Determine activity type and tool
            activity_type, estimated_tool, confidence = self._classify_file_event(event, file_path)

            if activity_type == 'ignore':
                return

            # Get file information
            file_size = 0
            file_hash = None
            try:
                file_size = os.path.getsize(file_path)
                file_hash = self._calculate_file_hash(file_path)
            except OSError:
                pass

            # Create activity record
            activity = FileActivity(
                file_path=file_path,
                activity_type=activity_type,
                timestamp=current_time,
                file_size=file_size,
                file_hash=file_hash,
                estimated_tool=estimated_tool,
                confidence=confidence,
                metadata={
                    'event_type': event.event_type,
                    'is_directory': event.is_directory,
                    'relative_path': os.path.relpath(file_path, os.getcwd()),
                    'file_extension': os.path.splitext(file_path)[1]
                }
            )

            # Store activity
            self.recent_activities.append(activity)

            # Keep only recent activities (last 1000)
            if len(self.recent_activities) > 1000:
                self.recent_activities = self.recent_activities[-1000:]

            # Update file tracking
            if file_hash:
                self.file_hashes[file_path] = file_hash

            # Callback to session manager or pipeline
            if self.callback:
                await self.callback(activity)

            logger.debug(f"Detected {estimated_tool} tool usage: {activity_type} on {os.path.basename(file_path)}")

        except Exception as e:
            logger.error(f"Error processing file event for {file_path}: {e}")

    def _classify_file_event(self, event, file_path: str) -> tuple[str, str, float]:
        """Classify file event to determine tool usage"""

        if event.is_directory:
            return 'ignore', 'unknown', 0.0

        previous_hash = self.file_hashes.get(file_path, "")

        try:
            current_hash = self._calculate_file_hash(file_path) if os.path.exists(file_path) else ""
        except Exception:
            current_hash = ""

        # Classify based on event type and hash changes
        if isinstance(event, FileCreatedEvent):
            # New file created
            return 'create', 'Write', 0.9

        elif isinstance(event, FileModifiedEvent):
            if not os.path.exists(file_path):
                return 'ignore', 'unknown', 0.0

            # Check if content actually changed
            if previous_hash and current_hash == previous_hash:
                # File access without content change (likely Read)
                return 'read', 'Read', 0.7
            elif previous_hash and current_hash != previous_hash:
                # Content changed (Edit or Write)
                return 'edit', 'Edit', 0.9
            else:
                # First time seeing this file
                return 'write', 'Write', 0.8

        elif isinstance(event, FileDeletedEvent):
            return 'delete', 'Edit', 0.6

        return 'unknown', 'unknown', 0.1

    async def _process_pending_events(self):
        """Process pending events with debouncing"""
        while self.is_monitoring:
            try:
                current_time = time.time()
                expired_events = []

                for file_path, event_time in self.pending_events.items():
                    if current_time - event_time > self.debounce_delay:
                        expired_events.append(file_path)

                # Clean up expired events
                for file_path in expired_events:
                    del self.pending_events[file_path]

                await asyncio.sleep(0.1)  # Check every 100ms

            except Exception as e:
                logger.error(f"Error in pending events processing: {e}")
                await asyncio.sleep(1)

    def get_recent_activities(self, limit: int = 50) -> List[FileActivity]:
        """Get recent file activities"""
        return self.recent_activities[-limit:] if self.recent_activities else []

    def get_activity_stats(self) -> Dict[str, Any]:
        """Get statistics about detected activities"""
        if not self.recent_activities:
            return {
                'total_activities': 0,
                'by_tool': {},
                'by_type': {},
                'monitored_paths': len(self.monitored_paths),
                'is_monitoring': self.is_monitoring
            }

        # Aggregate statistics
        by_tool = {}
        by_type = {}
        by_extension = {}

        for activity in self.recent_activities:
            # By tool
            tool = activity.estimated_tool
            by_tool[tool] = by_tool.get(tool, 0) + 1

            # By activity type
            activity_type = activity.activity_type
            by_type[activity_type] = by_type.get(activity_type, 0) + 1

            # By file extension
            ext = os.path.splitext(activity.file_path)[1]
            by_extension[ext] = by_extension.get(ext, 0) + 1

        return {
            'total_activities': len(self.recent_activities),
            'by_tool': by_tool,
            'by_type': by_type,
            'by_extension': by_extension,
            'monitored_paths': len(self.monitored_paths),
            'is_monitoring': self.is_monitoring,
            'monitored_extensions': len(self.monitored_extensions),
            'ignored_directories': len(self.ignored_dirs)
        }

    async def stop_monitoring(self):
        """Stop file system monitoring"""
        self.is_monitoring = False
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

        logger.info("File system monitoring stopped")

class ClaudeFileEventHandler(FileSystemEventHandler):
    """Event handler for file system changes"""

    def __init__(self, callback):
        self.callback = callback
        super().__init__()

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event)

    def on_created(self, event):
        if not event.is_directory:
            self.callback(event)

    def on_deleted(self, event):
        if not event.is_directory:
            self.callback(event)

    def on_moved(self, event):
        if not event.is_directory:
            # Treat as delete + create
            self.callback(event)