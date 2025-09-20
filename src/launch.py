"""
AI Orchestration Analytics Launcher
===================================
Unified launcher for the consolidated orchestration analytics system
"""

import sys
import os
import asyncio
import signal
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import OrchestrationDB
from src.tracking.handoff_monitor import HandoffMonitor, DeepSeekClient
from src.tracking.subagent_tracker import SubagentTracker
from src.dashboard.realtime_dashboard import app
from src.instrumentation.realtime_pipeline import RealTimePipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/orchestration.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class OrchestrationAnalytics:
    """Main orchestration analytics system"""

    def __init__(self):
        self.db = None
        self.handoff_monitor = None
        self.subagent_tracker = None
        self.deepseek_client = None
        self.realtime_pipeline = None
        self.activity_broadcaster = None
        self.activity_generator = None
        self.running = False

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing AI Orchestration Analytics...")

        # Ensure directories exist
        os.makedirs('data/logs', exist_ok=True)
        os.makedirs('data/backups', exist_ok=True)

        # Initialize database
        self.db = OrchestrationDB()
        logger.info("Database initialized")

        # Initialize monitoring components
        self.handoff_monitor = HandoffMonitor(self.db)
        self.subagent_tracker = SubagentTracker(self.db)
        self.deepseek_client = DeepSeekClient()

        # Test DeepSeek connection
        deepseek_status = self.deepseek_client.get_health_status()
        if deepseek_status['available']:
            logger.info(f"DeepSeek connected: {deepseek_status['response_time']:.2f}s response time")
        else:
            logger.warning(f"DeepSeek not available: {deepseek_status.get('error', 'Unknown error')}")

        # Initialize real-time instrumentation pipeline
        self.realtime_pipeline = RealTimePipeline(self.db)
        await self.realtime_pipeline.initialize()
        logger.info("Real-time instrumentation pipeline initialized")

        # Initialize live activity broadcasting system
        try:
            from src.tracking.live_activity_broadcaster import create_activity_system
            self.activity_broadcaster, self.activity_generator = create_activity_system(self.db)
            # Note: WebSocket server will start when dashboard starts
            logger.info("Live activity broadcasting system initialized")
        except ImportError as e:
            logger.warning(f"Could not initialize live activity system: {e}")
            self.activity_broadcaster = None
            self.activity_generator = None

        # Demonstrate the instrumentation system
        asyncio.create_task(self._delayed_demonstration())

        self.running = True
        logger.info("SUCCESS: Orchestration Analytics with Real-Time Monitoring initialized successfully")

    async def start_dashboard(self, host='127.0.0.1', port=8000):
        """Start the web dashboard"""
        logger.info(f"Starting dashboard on http://{host}:{port}")

        try:
            # Set global instances for both dashboard modules
            import src.dashboard.orchestration_dashboard as dashboard_module
            import src.dashboard.realtime_dashboard as realtime_module

            # Set globals for orchestration dashboard
            dashboard_module.db = self.db
            dashboard_module.handoff_monitor = self.handoff_monitor
            dashboard_module.subagent_tracker = self.subagent_tracker
            dashboard_module.deepseek_client = self.deepseek_client
            dashboard_module.realtime_pipeline = self.realtime_pipeline

            # Set globals for realtime dashboard (which we're actually using)
            realtime_module.db = self.db
            realtime_module.handoff_monitor = self.handoff_monitor
            realtime_module.subagent_tracker = self.subagent_tracker
            realtime_module.deepseek_client = self.deepseek_client
            realtime_module.realtime_pipeline = self.realtime_pipeline

            # Start live activity WebSocket server if available
            if self.activity_broadcaster:
                try:
                    await self.activity_broadcaster.start_server()
                    logger.info(f"Live activity WebSocket server started on ws://localhost:{self.activity_broadcaster.port}")

                    # Generate some initial activity events
                    if self.activity_generator:
                        self.activity_generator.generate_system_activity('START', {
                            'message': 'AI Orchestration Analytics started',
                            'version': '1.0',
                            'dashboard_url': f'http://{host}:{port}'
                        })
                except Exception as e:
                    logger.warning(f"Could not start live activity WebSocket server: {e}")

            await app.run_task(host=host, port=port, debug=False)
        except Exception as e:
            logger.error(f"Dashboard startup failed: {e}")
            raise

    async def run_health_checks(self):
        """Run periodic health checks"""
        cleanup_counter = 0

        while self.running:
            try:
                # Check DeepSeek health
                deepseek_health = self.deepseek_client.get_health_status()
                if not deepseek_health['available']:
                    logger.warning("DeepSeek health check failed")

                # Log system status
                handoff_analytics = self.db.get_handoff_analytics()
                subagent_analytics = self.subagent_tracker.get_agent_usage_analytics()

                logger.info(f"Health check - Handoffs: {handoff_analytics.get('total_handoffs', 0)}, "
                          f"Subagents: {len(subagent_analytics.get('usage_statistics', []))}")

                # Run activity cleanup every 6th health check (30 minutes)
                cleanup_counter += 1
                if cleanup_counter >= 6:
                    try:
                        cleanup_count = self.db.cleanup_old_activities(days_to_keep=7)
                        if cleanup_count > 0:
                            logger.info(f"Cleaned up {cleanup_count} old activities (older than 7 days)")
                    except Exception as cleanup_error:
                        logger.error(f"Activity cleanup error: {cleanup_error}")
                    cleanup_counter = 0

            except Exception as e:
                logger.error(f"Health check error: {e}")

            # Wait 5 minutes before next check
            await asyncio.sleep(300)

    def simulate_test_data(self):
        """Generate test data for demonstration"""
        import uuid
        from datetime import datetime

        logger.info("Generating test data...")

        # Create test session
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        self.db.create_session(
            session_id=session_id,
            project_name="AI-Orchestration-Analytics",
            task_description="Testing the consolidated analytics system",
            metadata={"test": True, "version": "1.0"}
        )

        # Track test handoff
        self.db.track_handoff(
            session_id=session_id,
            task_type="implementation",
            task_description="Implement dashboard analytics",
            source_model="claude_orchestrator",
            target_model="deepseek",
            handoff_reason="Code implementation task - perfect for DeepSeek",
            confidence_score=0.9,
            tokens_used=1500,
            cost=0.0,
            savings=0.0225,  # $0.015 per 1k tokens saved
            success=True,
            response_time=2.1
        )

        # Track test subagent
        self.db.track_subagent(
            session_id=session_id,
            agent_type="api-testing",
            agent_name="api-testing-specialist",
            trigger_phrase="test api endpoints",
            task_description="Test the analytics API endpoints",
            execution_time=15.5,
            success=True,
            tokens_used=800,
            cost=0.012
        )

        # Track test outcome
        self.db.track_outcome(
            session_id=session_id,
            task_id="task_001",
            task_type="implementation",
            task_description="Analytics dashboard implementation",
            model_used="deepseek",
            success=True,
            execution_time=125.5,
            tokens_used=1500,
            cost=0.0,
            quality_score=4.2
        )

        logger.info("SUCCESS: Test data generated successfully")

    async def _delayed_demonstration(self):
        """Demonstrate the instrumentation system after a brief startup delay"""
        await asyncio.sleep(5)  # Wait 5 seconds for system to fully start
        if self.realtime_pipeline:
            await self.realtime_pipeline.demonstrate_instrumentation()

    async def shutdown(self):
        """Gracefully shutdown the system"""
        logger.info("Shutting down Orchestration Analytics...")
        self.running = False

        # Shutdown real-time pipeline
        if self.realtime_pipeline:
            await self.realtime_pipeline.shutdown()

        # Shutdown live activity WebSocket server
        if self.activity_broadcaster:
            await self.activity_broadcaster.stop_server()

        if self.db:
            self.db.close()

        logger.info("SUCCESS: Shutdown complete")

async def main():
    """Main entry point"""
    analytics = OrchestrationAnalytics()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(analytics.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize system
        await analytics.initialize()

        # Generate test data if database is empty
        sessions = analytics.db.get_session_summary(limit=1)
        if not sessions:
            analytics.simulate_test_data()

        # Start health check task
        health_task = asyncio.create_task(analytics.run_health_checks())

        # Print startup info
        print("\n" + "="*60)
        print("AI ORCHESTRATION ANALYTICS")
        print("="*60)
        print("SUCCESS: System initialized successfully")
        print("Dashboard: http://localhost:8000")
        print("DeepSeek Status:", "ONLINE" if analytics.deepseek_client.is_available() else "OFFLINE")
        print("Logs: data/logs/orchestration.log")
        print("\nPress Ctrl+C to shutdown")
        print("="*60)

        # Start dashboard (this blocks)
        await analytics.start_dashboard()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Startup error: {e}")
    finally:
        await analytics.shutdown()

def run_cli():
    """CLI entry point for testing individual components"""
    import argparse

    parser = argparse.ArgumentParser(description='AI Orchestration Analytics CLI')
    parser.add_argument('--test-handoff', action='store_true',
                       help='Test handoff decision making')
    parser.add_argument('--test-subagent', action='store_true',
                       help='Test subagent detection')
    parser.add_argument('--generate-data', action='store_true',
                       help='Generate test data')
    parser.add_argument('--dashboard', action='store_true',
                       help='Start dashboard only (default)')

    args = parser.parse_args()

    analytics = OrchestrationAnalytics()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(analytics.initialize())

        if args.test_handoff:
            # Test handoff decision
            decision = analytics.handoff_monitor.analyze_task(
                "Implement a function to calculate fibonacci numbers",
                "implementation"
            )
            print(f"Handoff Decision: {decision}")

        elif args.test_subagent:
            # Test subagent detection
            invocations = analytics.subagent_tracker.detect_subagent_invocation(
                "Please test the API endpoints for security vulnerabilities"
            )
            for inv in invocations:
                print(f"Subagent: {inv.agent_name} (confidence: {inv.confidence:.2f})")

        elif args.generate_data:
            analytics.simulate_test_data()
            print("SUCCESS: Test data generated")

        else:
            # Default: start dashboard
            loop.run_until_complete(analytics.start_dashboard())

    except KeyboardInterrupt:
        print("\nGoodbye!")
    finally:
        loop.run_until_complete(analytics.shutdown())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_cli()
    else:
        asyncio.run(main())