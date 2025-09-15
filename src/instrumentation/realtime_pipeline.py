"""
Real-Time Data Pipeline for Claude Code Orchestration
=====================================================
Orchestrates all instrumentation components and creates unified data flow
to the analytics backend
"""

import os
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from .session_manager import SessionManager
from .activity_detector import ActivityDetector, DetectedActivity
from .message_analyzer import MessageAnalyzer, MessageAnalysis
from src.core.database import OrchestrationDB
from src.tracking.handoff_monitor import HandoffMonitor
from src.tracking.subagent_tracker import SubagentTracker, SubagentInvocation

logger = logging.getLogger(__name__)

@dataclass
class PipelineEvent:
    """Unified pipeline event"""
    event_id: str
    event_type: str  # 'activity', 'message', 'session', 'handoff', 'subagent'
    timestamp: datetime
    session_id: Optional[str]
    data: Dict[str, Any]
    processed: bool = False

class RealTimePipeline:
    """Orchestrates real-time data collection and processing"""

    def __init__(self, db: OrchestrationDB = None):
        self.db = db or OrchestrationDB()

        # Core components
        self.session_manager = SessionManager(self.db)
        self.activity_detector = ActivityDetector(self.session_manager)
        self.message_analyzer = MessageAnalyzer()
        self.handoff_monitor = HandoffMonitor(self.db)
        self.subagent_tracker = SubagentTracker(self.db)

        # Pipeline state
        self.is_running = False
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.processed_events: List[PipelineEvent] = []
        self.processing_callbacks: List[Callable] = []

        # Statistics
        self.stats = {
            'events_processed': 0,
            'activities_tracked': 0,
            'messages_analyzed': 0,
            'handoffs_recorded': 0,
            'subagents_invoked': 0,
            'sessions_managed': 0,
            'pipeline_start_time': None,
            'last_activity_time': None
        }

        # Configuration
        self.batch_size = 10
        self.batch_timeout = 5.0  # seconds
        self.max_queue_size = 1000

    async def initialize(self):
        """Initialize the entire pipeline"""
        logger.info("Initializing Real-Time Pipeline...")

        try:
            # Initialize all components
            await self.session_manager.initialize()
            await self.activity_detector.initialize()

            # Set up activity callbacks
            self.activity_detector.add_activity_callback(self._on_activity_detected)

            # Start pipeline processing
            self.is_running = True
            self.stats['pipeline_start_time'] = datetime.now(timezone.utc)

            # Start processing tasks
            asyncio.create_task(self._process_event_queue())
            asyncio.create_task(self._periodic_health_check())

            logger.info("Real-Time Pipeline initialized successfully")

            # Create initial session
            await self._create_initial_session()

        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise

    async def _create_initial_session(self):
        """Create initial session for current context"""
        try:
            # This simulates a user starting the real-time tracking session
            session_id = await self.session_manager.start_session(
                working_directory=os.getcwd(),
                initial_task="Real-time activity tracking session - demonstrating comprehensive orchestration monitoring",
                project_name="AI-Orchestration-Analytics"
            )

            # Simulate an initial message to demonstrate message analysis
            await self.analyze_user_message(
                "Let's implement real-time activity tracking and test file monitoring. " +
                "We need to create comprehensive instrumentation that detects Read, Write, " +
                "Edit, and Bash tool usage. This is a complex implementation task requiring " +
                "file system monitoring, process detection, and database integration."
            )

            logger.info(f"Created initial session {session_id} with demonstration message analysis")

        except Exception as e:
            logger.error(f"Failed to create initial session: {e}")

    async def analyze_user_message(self, message: str, context: Dict[str, Any] = None) -> MessageAnalysis:
        """Analyze user message and process routing decisions"""
        try:
            # Analyze the message
            analysis = await self.message_analyzer.analyze_message(message, context)

            # Process handoff decision if available
            if analysis.handoff_decision:
                await self._process_handoff_decision(analysis)

            # Process subagent triggers if any
            if analysis.subagent_triggers:
                await self._process_subagent_triggers(analysis)

            # Queue for processing
            event = PipelineEvent(
                event_id=f"message_{int(time.time() * 1000)}",
                event_type='message',
                timestamp=analysis.timestamp,
                session_id=self.session_manager.current_session_id,
                data={
                    'message': message,
                    'analysis': analysis,
                    'handoff_decision': analysis.handoff_decision,
                    'subagent_triggers': analysis.subagent_triggers
                }
            )

            await self.event_queue.put(event)

            self.stats['messages_analyzed'] += 1
            self.stats['last_activity_time'] = datetime.now(timezone.utc)

            logger.debug(f"Analyzed message: {len(message)} chars, urgency={analysis.urgency_level}")

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
            raise

    async def _process_handoff_decision(self, analysis: MessageAnalysis):
        """Process handoff decision and track in database"""
        if not analysis.handoff_decision:
            return

        try:
            current_session = self.session_manager.get_current_session()
            if current_session:
                # Track handoff decision
                handoff_id = self.handoff_monitor.track_handoff(
                    session_id=current_session.session_id,
                    task_description=analysis.message,
                    task_type=analysis.task_classification.get('primary_type', 'general'),
                    decision=analysis.handoff_decision,
                    actual_model=None  # Will be updated when actual routing happens
                )

                self.stats['handoffs_recorded'] += 1

                logger.debug(f"Tracked handoff decision {handoff_id}: " +
                           f"route_to_deepseek={analysis.handoff_decision.should_route_to_deepseek}")

        except Exception as e:
            logger.error(f"Error processing handoff decision: {e}")

    async def _process_subagent_triggers(self, analysis: MessageAnalysis):
        """Process subagent triggers and track invocations"""
        current_session = self.session_manager.get_current_session()
        if not current_session:
            return

        try:
            for trigger in analysis.subagent_triggers:
                # Track subagent invocation
                invocation_id = self.subagent_tracker.track_invocation(
                    session_id=current_session.session_id,
                    invocation=trigger,
                    parent_agent="claude_orchestrator",
                    execution_start=time.time()
                )

                self.stats['subagents_invoked'] += 1

                logger.debug(f"Tracked subagent invocation {invocation_id}: {trigger.agent_name}")

        except Exception as e:
            logger.error(f"Error processing subagent triggers: {e}")

    async def _on_activity_detected(self, activity: DetectedActivity):
        """Callback for when activity is detected"""
        try:
            # Create pipeline event
            event = PipelineEvent(
                event_id=activity.activity_id,
                event_type='activity',
                timestamp=activity.timestamp,
                session_id=activity.session_id,
                data={
                    'activity': activity,
                    'tool_name': activity.tool_name,
                    'activity_type': activity.activity_type,
                    'details': activity.details
                }
            )

            await self.event_queue.put(event)

            self.stats['activities_tracked'] += 1
            self.stats['last_activity_time'] = datetime.now(timezone.utc)

            logger.debug(f"Queued activity: {activity.tool_name} - {activity.activity_type}")

        except Exception as e:
            logger.error(f"Error processing detected activity: {e}")

    async def _process_event_queue(self):
        """Process events from the queue in batches"""
        while self.is_running:
            try:
                events_batch = []
                start_time = time.time()

                # Collect events for batch processing
                while (len(events_batch) < self.batch_size and
                       time.time() - start_time < self.batch_timeout):
                    try:
                        event = await asyncio.wait_for(
                            self.event_queue.get(), timeout=0.1
                        )
                        events_batch.append(event)
                    except asyncio.TimeoutError:
                        continue

                # Process batch if we have events
                if events_batch:
                    await self._process_event_batch(events_batch)

            except Exception as e:
                logger.error(f"Error in event queue processing: {e}")
                await asyncio.sleep(1)

    async def _process_event_batch(self, events: List[PipelineEvent]):
        """Process a batch of events"""
        try:
            for event in events:
                await self._process_single_event(event)

            # Store processed events
            self.processed_events.extend(events)

            # Keep only recent events (last 1000)
            if len(self.processed_events) > 1000:
                self.processed_events = self.processed_events[-1000:]

            self.stats['events_processed'] += len(events)

            logger.debug(f"Processed batch of {len(events)} events")

        except Exception as e:
            logger.error(f"Error processing event batch: {e}")

    async def _process_single_event(self, event: PipelineEvent):
        """Process a single pipeline event"""
        try:
            if event.event_type == 'activity':
                await self._store_activity_event(event)
            elif event.event_type == 'message':
                await self._store_message_event(event)
            elif event.event_type == 'session':
                await self._store_session_event(event)

            # Mark as processed
            event.processed = True

            # Notify callbacks
            for callback in self.processing_callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Error in processing callback: {e}")

        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")

    async def _store_activity_event(self, event: PipelineEvent):
        """Store activity event in database as subagent invocation"""
        activity = event.data.get('activity')
        if not activity or not event.session_id:
            return

        try:
            # Map file operations to subagent invocations
            if activity.tool_name in ['Read', 'Write', 'Edit']:
                # Track as MCP tool invocation / subagent activity
                invocation_id = self.subagent_tracker.track_invocation(
                    session_id=event.session_id,
                    invocation=SubagentInvocation(
                        agent_type='mcp_tool',
                        agent_name=f"tool.{activity.tool_name.lower()}",
                        trigger_phrase=f"File operation: {activity.activity_type}",
                        task_description=f"{activity.tool_name} operation on {activity.details.get('relative_path', 'file')}",
                        confidence=activity.confidence
                    ),
                    parent_agent="claude_orchestrator",
                    execution_start=time.time()
                )

                logger.debug(f"Stored {activity.tool_name} activity as subagent invocation {invocation_id}")

        except Exception as e:
            logger.error(f"Error storing activity event: {e}")

    async def _store_message_event(self, event: PipelineEvent):
        """Store message analysis results"""
        # Message analysis results are already stored via handoff and subagent processing
        # This could be extended to store additional message metadata
        pass

    async def _store_session_event(self, event: PipelineEvent):
        """Store session-related events"""
        # Session events are handled by the session manager
        # This could be extended for session milestone tracking
        pass

    async def _periodic_health_check(self):
        """Perform periodic health checks on all components"""
        while self.is_running:
            try:
                # Check component health
                health_status = await self.get_pipeline_health()

                if health_status['overall_status'] != 'healthy':
                    logger.warning(f"Pipeline health issues detected: {health_status}")

                # Log statistics periodically
                if self.stats['events_processed'] % 100 == 0 and self.stats['events_processed'] > 0:
                    logger.info(f"Pipeline stats: {self.stats['events_processed']} events processed")

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(60)

    async def get_pipeline_health(self) -> Dict[str, Any]:
        """Get comprehensive pipeline health status"""
        try:
            current_time = datetime.now(timezone.utc)

            # Component health
            component_health = {
                'session_manager': len(self.session_manager.active_sessions) > 0,
                'activity_detector': self.activity_detector.is_active,
                'file_monitor': self.activity_detector.file_monitor.is_monitoring,
                'process_monitor': self.activity_detector.process_monitor.monitoring,
                'database': True  # Could add actual DB health check
            }

            # Overall health
            all_healthy = all(component_health.values())

            # Queue health
            queue_size = self.event_queue.qsize()
            queue_healthy = queue_size < self.max_queue_size * 0.8

            # Activity freshness
            activity_fresh = True
            if self.stats['last_activity_time']:
                time_since_activity = (current_time - self.stats['last_activity_time']).total_seconds()
                activity_fresh = time_since_activity < 300  # 5 minutes

            return {
                'overall_status': 'healthy' if (all_healthy and queue_healthy) else 'degraded',
                'component_health': component_health,
                'queue_size': queue_size,
                'queue_healthy': queue_healthy,
                'activity_freshness': {
                    'is_fresh': activity_fresh,
                    'last_activity': self.stats['last_activity_time'].isoformat() if self.stats['last_activity_time'] else None,
                    'time_since_activity_seconds': (current_time - self.stats['last_activity_time']).total_seconds() if self.stats['last_activity_time'] else None
                },
                'statistics': self.stats.copy(),
                'uptime_seconds': (current_time - self.stats['pipeline_start_time']).total_seconds() if self.stats['pipeline_start_time'] else 0
            }

        except Exception as e:
            logger.error(f"Error getting pipeline health: {e}")
            return {'overall_status': 'error', 'error': str(e)}

    def add_processing_callback(self, callback: Callable):
        """Add callback for when events are processed"""
        self.processing_callbacks.append(callback)

    async def force_pipeline_sync(self) -> Dict[str, Any]:
        """Force synchronization of all pipeline data"""
        try:
            # Force session sync
            session_sync = await self.session_manager.force_session_sync()

            # Force activity sync
            activity_sync = await self.activity_detector.force_activity_sync()

            # Process remaining queue
            remaining_events = []
            while not self.event_queue.empty():
                try:
                    event = self.event_queue.get_nowait()
                    remaining_events.append(event)
                except asyncio.QueueEmpty:
                    break

            if remaining_events:
                await self._process_event_batch(remaining_events)

            return {
                'session_sync': session_sync,
                'activity_sync': activity_sync,
                'remaining_events_processed': len(remaining_events),
                'total_events_processed': self.stats['events_processed'],
                'sync_timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error in pipeline sync: {e}")
            return {'error': str(e)}

    async def demonstrate_instrumentation(self):
        """Demonstrate the instrumentation system by creating test activities"""
        logger.info("🚀 Demonstrating real-time instrumentation system...")

        try:
            # Simulate user messages
            test_messages = [
                "Please read the database.py file and analyze its structure",
                "Write a new function to handle file uploads with error handling",
                "Edit the configuration file to add the new API endpoint",
                "Run the tests and fix any failing test cases",
                "Can you help me implement API security testing for this endpoint?",
                "We need performance testing for the database queries under load"
            ]

            for i, message in enumerate(test_messages):
                logger.info(f"📝 Processing message {i+1}: {message[:50]}...")
                await self.analyze_user_message(message)
                await asyncio.sleep(1)  # Brief pause between messages

            logger.info("✅ Demonstration complete - check dashboard for real-time data!")

        except Exception as e:
            logger.error(f"Error in demonstration: {e}")

    async def shutdown(self):
        """Shutdown the pipeline gracefully"""
        logger.info("Shutting down Real-Time Pipeline...")

        self.is_running = False

        # Shutdown components
        await self.activity_detector.shutdown()

        # Process remaining events
        await self.force_pipeline_sync()

        logger.info("Pipeline shutdown complete")