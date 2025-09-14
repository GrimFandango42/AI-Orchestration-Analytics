"""
Hot Reload Development System
============================
Monitors file changes and automatically restarts the server for seamless CI/CD development.
"""

import time
import os
import sys
import subprocess
import psutil
from pathlib import Path
from typing import Dict, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import signal

logger = logging.getLogger(__name__)

class HotReloadHandler(FileSystemEventHandler):
    """Handles file system events for hot reload functionality"""

    def __init__(self, reload_callback, excluded_dirs=None, monitored_extensions=None):
        self.reload_callback = reload_callback
        self.excluded_dirs = excluded_dirs or {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'data'}
        self.monitored_extensions = monitored_extensions or {'.py', '.html', '.css', '.js', '.json'}
        self.last_reload = 0
        self.debounce_time = 2  # seconds

    def should_trigger_reload(self, file_path: str) -> bool:
        """Check if file change should trigger a reload"""
        path = Path(file_path)

        # Skip if in excluded directory
        for part in path.parts:
            if part in self.excluded_dirs:
                return False

        # Only monitor specific file extensions
        if path.suffix not in self.monitored_extensions:
            return False

        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_reload < self.debounce_time:
            return False

        return True

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        if self.should_trigger_reload(event.src_path):
            logger.info(f"File changed: {event.src_path}")
            self.last_reload = time.time()
            self.reload_callback(event.src_path)

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        if self.should_trigger_reload(event.src_path):
            logger.info(f"File created: {event.src_path}")
            self.last_reload = time.time()
            self.reload_callback(event.src_path)

class ServerManager:
    """Manages server lifecycle for hot reload"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.server_process: Optional[subprocess.Popen] = None
        self.server_pid_file = os.path.join(project_root, "data", "server.pid")
        self.restart_count = 0
        self.max_restarts_per_minute = 10
        self.restart_times = []

    def start_server(self) -> bool:
        """Start the orchestration analytics server"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.server_pid_file), exist_ok=True)

            # Stop existing server if running
            self.stop_server()

            # Start new server process
            launch_script = os.path.join(self.project_root, "src", "launch.py")
            cmd = [sys.executable, launch_script]

            logger.info(f"Starting server: {' '.join(cmd)}")

            # Start process with proper output handling
            self.server_process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            # Save PID for cleanup
            with open(self.server_pid_file, 'w') as f:
                f.write(str(self.server_process.pid))

            # Wait a moment for server to start
            time.sleep(3)

            # Check if server started successfully
            if self.server_process.poll() is None:
                logger.info(f"Server started successfully (PID: {self.server_process.pid})")
                self.restart_count += 1
                self.restart_times.append(time.time())
                return True
            else:
                logger.error("Server failed to start")
                return False

        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return False

    def stop_server(self) -> bool:
        """Stop the running server"""
        try:
            # Try to stop current process
            if self.server_process and self.server_process.poll() is None:
                logger.info(f"Stopping server process (PID: {self.server_process.pid})")

                if os.name == 'nt':  # Windows
                    # Use taskkill for Windows
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.server_process.pid)],
                                 check=False, capture_output=True)
                else:  # Unix-like
                    self.server_process.terminate()

                # Wait for process to stop
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("Server didn't stop gracefully, force killing")
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.server_process.pid)],
                                     check=False, capture_output=True)
                    else:
                        self.server_process.kill()

            # Also kill any processes using port 8000
            self.kill_processes_on_port(8000)

            # Clean up PID file
            if os.path.exists(self.server_pid_file):
                os.remove(self.server_pid_file)

            self.server_process = None
            logger.info("Server stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False

    def kill_processes_on_port(self, port: int):
        """Kill any processes using the specified port"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.info['connections']
                    if connections:
                        for conn in connections:
                            if conn.laddr.port == port:
                                logger.info(f"Killing process {proc.info['pid']} ({proc.info['name']}) using port {port}")
                                psutil.Process(proc.info['pid']).terminate()
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            logger.error(f"Error killing processes on port {port}: {e}")

    def restart_server(self, changed_file: str = None):
        """Restart the server after file changes"""
        try:
            # Check restart rate limiting
            current_time = time.time()
            self.restart_times = [t for t in self.restart_times if current_time - t < 60]  # Keep last minute

            if len(self.restart_times) >= self.max_restarts_per_minute:
                logger.warning(f"Too many restarts ({len(self.restart_times)}) in the last minute. Skipping restart.")
                return False

            logger.info(f"🔄 Hot reload triggered by: {changed_file or 'file change'}")

            # Stop and start server
            if self.stop_server():
                time.sleep(1)  # Brief pause
                if self.start_server():
                    logger.info("✅ Hot reload completed successfully")
                    return True
                else:
                    logger.error("❌ Failed to restart server")
                    return False
            else:
                logger.error("❌ Failed to stop server for restart")
                return False

        except Exception as e:
            logger.error(f"Error during server restart: {e}")
            return False

    def is_server_running(self) -> bool:
        """Check if server is currently running"""
        return self.server_process is not None and self.server_process.poll() is None

class HotReloadSystem:
    """Main hot reload system orchestrator"""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.server_manager = ServerManager(self.project_root)
        self.observer = Observer()
        self.is_running = False
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for hot reload system"""
        log_dir = os.path.join(self.project_root, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, "hot_reload.log")

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    def start(self):
        """Start the hot reload system"""
        try:
            logger.info("🚀 Starting AI Orchestration Analytics Hot Reload System")
            logger.info(f"Project root: {self.project_root}")

            # Start initial server
            if not self.server_manager.start_server():
                logger.error("Failed to start initial server")
                return False

            # Setup file system watcher
            reload_handler = HotReloadHandler(
                reload_callback=self.server_manager.restart_server,
                excluded_dirs={'.git', '__pycache__', '.pytest_cache', 'node_modules', 'data', 'logs'},
                monitored_extensions={'.py', '.html', '.css', '.js', '.json', '.md'}
            )

            # Watch the src directory and specific config files
            watch_paths = [
                os.path.join(self.project_root, "src"),
                os.path.join(self.project_root, "requirements.txt"),
                os.path.join(self.project_root, "CLAUDE.md")
            ]

            for watch_path in watch_paths:
                if os.path.exists(watch_path):
                    self.observer.schedule(reload_handler, watch_path, recursive=True)
                    logger.info(f"Watching: {watch_path}")

            # Start file system observer
            self.observer.start()
            self.is_running = True

            logger.info("✅ Hot reload system started successfully")
            logger.info("📝 Monitoring file changes for automatic server restart")
            logger.info("🌐 Dashboard: http://localhost:8000")
            logger.info("🛑 Press Ctrl+C to stop")

            # Keep running
            try:
                while self.is_running:
                    time.sleep(1)

                    # Check if server is still running
                    if not self.server_manager.is_server_running():
                        logger.warning("Server stopped unexpectedly, restarting...")
                        self.server_manager.start_server()

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")

            return True

        except Exception as e:
            logger.error(f"Error starting hot reload system: {e}")
            return False
        finally:
            self.stop()

    def stop(self):
        """Stop the hot reload system"""
        try:
            logger.info("🛑 Stopping hot reload system...")
            self.is_running = False

            # Stop file system observer
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()

            # Stop server
            self.server_manager.stop_server()

            logger.info("✅ Hot reload system stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping hot reload system: {e}")

def main():
    """Main entry point for hot reload system"""
    # Handle command line arguments
    project_root = None
    if len(sys.argv) > 1:
        project_root = sys.argv[1]

    # Create and start hot reload system
    hot_reload = HotReloadSystem(project_root)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        hot_reload.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the system
    success = hot_reload.start()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()