"""
AI Orchestration Analytics - Load Testing with Locust
=====================================================
Comprehensive load testing for dashboard, API endpoints, and WebSocket connections.
"""

from locust import HttpUser, task, between, events
import json
import random
import time
from datetime import datetime, timedelta
import uuid


class OrchestrationAnalyticsUser(HttpUser):
    """Simulate user interactions with the AI Orchestration Analytics system"""

    wait_time = between(1, 5)  # Wait 1-5 seconds between requests

    def on_start(self):
        """Called when a simulated user starts running"""
        # Generate unique session ID for this user
        self.session_id = f"perf_test_{uuid.uuid4().hex[:8]}"
        self.project_names = [
            "AI-Orchestration-Analytics", "Claude-MCP-tools", "agenticSeek",
            "GooMe", "VoiceCloner", "tool-foundation", "GroupMeNavigator"
        ]

    @task(10)  # High weight - most common request
    def view_dashboard(self):
        """Load the main dashboard page"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200 and "AI Orchestration Analytics" in response.text:
                response.success()
            else:
                response.failure(f"Dashboard load failed: {response.status_code}")

    @task(8)
    def get_system_status(self):
        """Check system status API endpoint"""
        with self.client.get("/api/system-status", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "deepseek" in data and "active_sessions" in data:
                    response.success()
                else:
                    response.failure("Missing required fields in system status")
            else:
                response.failure(f"System status failed: {response.status_code}")

    @task(6)
    def get_handoff_analytics(self):
        """Fetch handoff analytics data"""
        with self.client.get("/api/handoff-analytics", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "total_handoffs" in data:
                    response.success()
                else:
                    response.failure("Invalid handoff analytics response")
            else:
                response.failure(f"Handoff analytics failed: {response.status_code}")

    @task(6)
    def get_subagent_analytics(self):
        """Fetch subagent usage analytics"""
        with self.client.get("/api/subagent-analytics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Subagent analytics failed: {response.status_code}")

    @task(5)
    def get_cost_analytics(self):
        """Fetch cost optimization analytics"""
        with self.client.get("/api/cost-analytics", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "monthly_cost" in data and "monthly_savings" in data:
                    response.success()
                else:
                    response.failure("Invalid cost analytics response")
            else:
                response.failure(f"Cost analytics failed: {response.status_code}")

    @task(5)
    def get_performance_metrics(self):
        """Fetch system performance metrics"""
        with self.client.get("/api/performance-metrics", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "avg_response_time" in data and "uptime" in data:
                    response.success()
                else:
                    response.failure("Invalid performance metrics response")
            else:
                response.failure(f"Performance metrics failed: {response.status_code}")

    @task(4)
    def get_recent_activity(self):
        """Fetch recent activity with pagination"""
        page = random.randint(1, 5)
        limit = random.choice([10, 25, 50])

        with self.client.get(f"/api/recent-activity?page={page}&limit={limit}",
                           catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "activities" in data and "pagination" in data:
                    response.success()
                else:
                    response.failure("Invalid recent activity response")
            else:
                response.failure(f"Recent activity failed: {response.status_code}")

    @task(4)
    def get_project_grouped_activity(self):
        """Fetch project-grouped activity data"""
        page = random.randint(1, 3)

        with self.client.get(f"/api/project-grouped-activity?page={page}&limit=10",
                           catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "projects" in data and "pagination" in data:
                    response.success()
                else:
                    response.failure("Invalid project activity response")
            else:
                response.failure(f"Project activity failed: {response.status_code}")

    @task(3)
    def get_account_transition_analysis(self):
        """Fetch account transition analysis"""
        with self.client.get("/api/account-transition-analysis", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "transition_projection" in data:
                    response.success()
                else:
                    response.failure("Invalid transition analysis response")
            else:
                response.failure(f"Transition analysis failed: {response.status_code}")

    @task(2)
    def track_session(self):
        """Create a new tracking session"""
        session_data = {
            "session_id": f"{self.session_id}_{int(time.time())}",
            "project_name": random.choice(self.project_names),
            "task_description": f"Performance test task {random.randint(1, 1000)}",
            "metadata": {
                "test": True,
                "load_test": True,
                "timestamp": datetime.now().isoformat()
            }
        }

        with self.client.post("/api/track/session",
                            json=session_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "session_id" in data and data.get("status") == "success":
                    response.success()
                else:
                    response.failure("Invalid session tracking response")
            else:
                response.failure(f"Session tracking failed: {response.status_code}")

    @task(2)
    def track_handoff(self):
        """Track a model handoff event"""
        handoff_data = {
            "session_id": self.session_id,
            "task_description": f"Load test handoff {random.randint(1, 1000)}",
            "task_type": random.choice(["implementation", "analysis", "debugging"]),
            "actual_model": random.choice(["deepseek", "claude"])
        }

        with self.client.post("/api/track/handoff",
                            json=handoff_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "handoff_id" in data and data.get("status") == "success":
                    response.success()
                else:
                    response.failure("Invalid handoff tracking response")
            else:
                response.failure(f"Handoff tracking failed: {response.status_code}")


class HeavyLoadUser(OrchestrationAnalyticsUser):
    """Simulate heavy load scenarios with rapid requests"""

    wait_time = between(0.1, 1.0)  # Much shorter wait times

    @task(15)
    def rapid_dashboard_requests(self):
        """Rapid dashboard page loads"""
        self.view_dashboard()

    @task(10)
    def concurrent_api_calls(self):
        """Make multiple API calls in quick succession"""
        self.get_system_status()
        self.get_handoff_analytics()
        self.get_subagent_analytics()


class DatabaseStressUser(HttpUser):
    """Focus on database-intensive operations"""

    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.session_id = f"db_stress_{uuid.uuid4().hex[:8]}"

    @task(10)
    def large_activity_query(self):
        """Request large amounts of activity data"""
        limit = random.choice([100, 200, 500])  # Large page sizes
        page = random.randint(1, 10)

        with self.client.get(f"/api/recent-activity?page={page}&limit={limit}",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Large query failed: {response.status_code}")

    @task(8)
    def complex_analytics_query(self):
        """Request complex analytics that require joins"""
        with self.client.get("/api/project-grouped-activity?page=1&limit=50",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Complex query failed: {response.status_code}")

    @task(5)
    def write_intensive_operations(self):
        """Perform database write operations"""
        # Create multiple tracking entries
        for _ in range(3):
            session_data = {
                "session_id": f"{self.session_id}_{int(time.time())}_{random.randint(1,1000)}",
                "project_name": f"stress_test_project_{random.randint(1, 10)}",
                "task_description": f"Database stress test operation {random.randint(1, 10000)}",
                "metadata": {"stress_test": True, "batch_operation": True}
            }

            self.client.post("/api/track/session", json=session_data)


# Performance monitoring event handlers
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Log performance metrics for each request"""
    if response_time > 2000:  # Log slow requests (>2s)
        print(f"SLOW REQUEST: {name} took {response_time}ms")

    if exception:
        print(f"REQUEST FAILED: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("=== AI Orchestration Analytics Performance Test Started ===")
    print(f"Target Host: {environment.host}")
    print(f"Test started at: {datetime.now()}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - generate performance summary"""
    print("\n=== Performance Test Summary ===")

    stats = environment.stats

    # Calculate key metrics
    total_requests = stats.num_requests
    total_failures = stats.num_failures
    failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    avg_response_time = stats.total.avg_response_time
    max_response_time = stats.total.max_response_time
    rps = stats.total.current_rps

    print(f"Total Requests: {total_requests}")
    print(f"Total Failures: {total_failures} ({failure_rate:.2f}%)")
    print(f"Average Response Time: {avg_response_time:.2f}ms")
    print(f"Maximum Response Time: {max_response_time:.2f}ms")
    print(f"Requests per Second: {rps:.2f}")

    # Performance assessment
    if failure_rate > 5:
        print("⚠️  HIGH FAILURE RATE - System may be overloaded")
    if avg_response_time > 2000:
        print("⚠️  SLOW RESPONSE TIMES - Performance optimization needed")
    if rps < 10:
        print("⚠️  LOW THROUGHPUT - Scalability concerns")

    print(f"Test completed at: {datetime.now()}")


# Custom user classes for different test scenarios
class BurstLoadUser(OrchestrationAnalyticsUser):
    """Simulate burst/spike traffic patterns"""

    def wait_time(self):
        # Simulate burst pattern - sometimes no wait, sometimes longer wait
        return random.choice([0.1, 0.2, 3.0, 5.0])

    @task(20)
    def burst_requests(self):
        """Simulate burst of requests"""
        # Make 3-5 rapid requests
        for _ in range(random.randint(3, 5)):
            self.get_system_status()
            time.sleep(0.1)  # Very short delay between burst requests


if __name__ == "__main__":
    # This allows running the locust file directly for testing
    import subprocess
    import sys

    print("Starting Locust load test...")
    print("Access the web UI at http://localhost:8089")
    print("Set target host to http://localhost:8000")

    # Run locust with web UI
    subprocess.run([
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host=http://localhost:8000"
    ])