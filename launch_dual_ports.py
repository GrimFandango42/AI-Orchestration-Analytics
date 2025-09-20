#!/usr/bin/env python3
"""
Dual Port Launcher for AI Cost Intelligence & Orchestration Analytics
===================================================================
Supports running on both port 3000 (development) and port 8000 (production)
"""

import sys
import asyncio
import signal
import logging
from pathlib import Path
import argparse

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.launch import OrchestrationAnalytics

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='AI Cost Intelligence & Orchestration Analytics Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python launch_dual_ports.py --port 8000      # Production (default)
  python launch_dual_ports.py --port 3000      # Development
  python launch_dual_ports.py --dev            # Development mode (port 3000)
  python launch_dual_ports.py --test-data      # Generate test data and start
        '''
    )

    parser.add_argument('--port', type=int, default=8000,
                       help='Port to run dashboard on (default: 8000)')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--dev', action='store_true',
                       help='Development mode (equivalent to --port 3000)')
    parser.add_argument('--test-data', action='store_true',
                       help='Generate test data on startup')

    return parser.parse_args()

async def main():
    """Main entry point for dual port launcher"""
    args = parse_arguments()

    # Override port if dev mode
    if args.dev:
        args.port = 3000

    # Configure environment-specific settings
    if args.port == 3000:
        mode = "DEVELOPMENT"
        log_level = logging.DEBUG
        debug_mode = True
    else:
        mode = "PRODUCTION"
        log_level = logging.INFO
        debug_mode = False

    # Update logging configuration
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'data/logs/orchestration_port_{args.port}.log'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)

    # Initialize analytics system
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

        # Generate test data if requested or if database is empty
        if args.test_data:
            analytics.simulate_test_data()
            logger.info("Test data generated")
        else:
            sessions = analytics.db.get_session_summary(limit=1)
            if not sessions:
                analytics.simulate_test_data()
                logger.info("Generated initial test data for empty database")

        # Start health check task
        health_task = asyncio.create_task(analytics.run_health_checks())

        # Print startup information
        print("\n" + "="*70)
        print("AI COST INTELLIGENCE & ORCHESTRATION ANALYTICS")
        print("="*70)
        print(f"MODE: {mode}")
        print(f"PORT: {args.port}")
        print(f"Dashboard: http://{args.host}:{args.port}")
        print(f"DeepSeek: {'ONLINE' if analytics.deepseek_client.is_available() else 'OFFLINE'}")
        print(f"Debug Mode: {debug_mode}")
        print(f"Logs: data/logs/orchestration_port_{args.port}.log")
        print("\nPress Ctrl+C to shutdown")
        print("="*70)

        # Record the port assignment in our memories
        import datetime
        with open(f"data/logs/port_assignment_{args.port}.log", "w") as f:
            f.write(f"Port {args.port} assigned to AI Cost Intelligence & Orchestration Analytics\n")
            f.write(f"Mode: {mode}\n")
            f.write(f"Started at: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Purpose: {'Testing/Development' if args.port == 3000 else 'Production Analytics'}\n")

        # Start dashboard (this blocks)
        await analytics.start_dashboard(host=args.host, port=args.port)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    finally:
        await analytics.shutdown()

if __name__ == '__main__':
    asyncio.run(main())