"""
Real-Time Instrumentation Module
================================
Comprehensive activity detection and monitoring for Claude Code orchestration

This module provides:
- Real-time activity detection and tracking
- File system monitoring for tool usage detection
- Session lifecycle management
- User message analysis for handoff decisions
- Automatic data pipeline to analytics backend
"""

from .session_manager import SessionManager
from .activity_detector import ActivityDetector
from .file_monitor import FileSystemMonitor
from .message_analyzer import MessageAnalyzer
from .realtime_pipeline import RealTimePipeline

__all__ = [
    'SessionManager',
    'ActivityDetector',
    'FileSystemMonitor',
    'MessageAnalyzer',
    'RealTimePipeline'
]