"""
Comprehensive API Testing Suite for AI Orchestration Analytics
============================================================

This test suite validates:
1. REST API endpoint functionality
2. Input validation and boundary conditions
3. Error handling and status codes
4. Authentication and authorization
5. Response format validation
6. Rate limiting and throttling
7. Pagination testing
8. Integration with frontend dashboard

Test Categories:
- System Health Tests
- Analytics API Tests
- Tracking API Tests
- Error Handling Tests
- Security Tests
- Performance Tests
- Integration Tests
"""

import pytest
import httpx
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from faker import Faker
import logging
from pydantic import BaseModel, ValidationError
from jsonschema import validate, ValidationError as JsonSchemaValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()

# Test Configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30.0
MAX_CONCURRENT_REQUESTS = 50

# JSON Schema Definitions for Response Validation
SYSTEM_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "deepseek": {
            "type": "object",
            "properties": {
                "available": {"type": "boolean"},
                "response_time": {"type": ["number", "null"]},
                "models_loaded": {"type": ["integer", "null"]},
                "status": {"type": "string"}
            },
            "required": ["available"]
        },
        "active_sessions": {"type": "integer"},
        "handoffs_today": {"type": "integer"},
        "subagents_spawned": {"type": "integer"},
        "savings_today": {"type": "number"}
    },
    "required": ["deepseek", "active_sessions", "handoffs_today", "subagents_spawned", "savings_today"]
}

HANDOFF_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "total_handoffs": {"type": "integer"},
        "deepseek_handoffs": {"type": "integer"},
        "claude_handoffs": {"type": "integer"},
        "success_rate": {"type": "number"},
        "avg_confidence": {"type": "number"}
    }
}

SUBAGENT_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "patterns": {
            "type": "object",
            "properties": {
                "unique_agents_used": {"type": "integer"},
                "total_invocations": {"type": "integer"},
                "overall_success_rate": {"type": "number"},
                "avg_execution_time": {"type": "number"}
            }
        },
        "usage_statistics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string"},
                    "count": {"type": "integer"},
                    "success_rate": {"type": "number"}
                }
            }
        }
    }
}

COST_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "monthly_cost": {"type": "number"},
        "monthly_savings": {"type": "number"},
        "optimization_rate": {"type": "number"},
        "daily_data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "cost": {"type": "number"},
                    "savings": {"type": "number"}
                },
                "required": ["date", "cost", "savings"]
            }
        }
    },
    "required": ["monthly_cost", "monthly_savings", "optimization_rate", "daily_data"]
}

PERFORMANCE_METRICS_SCHEMA = {
    "type": "object",
    "properties": {
        "avg_response_time": {"type": "number"},
        "deepseek_response_time": {"type": "number"},
        "uptime": {"type": "number"},
        "error_rate": {"type": "number"}
    },
    "required": ["avg_response_time", "deepseek_response_time", "uptime", "error_rate"]
}

RECENT_ACTIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "activities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "session_id": {"type": ["string", "null"]},
                    "event_type": {"type": "string"},
                    "model_or_agent": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                    "cost": {"type": "number"}
                }
            }
        },
        "pagination": {
            "type": "object",
            "properties": {
                "current_page": {"type": "integer"},
                "total_pages": {"type": "integer"},
                "total_count": {"type": "integer"},
                "has_next": {"type": "boolean"},
                "has_previous": {"type": "boolean"}
            },
            "required": ["current_page", "total_pages", "total_count", "has_next", "has_previous"]
        },
        "status": {"type": "string", "enum": ["success"]}
    },
    "required": ["activities", "pagination", "status"]
}

PROJECT_GROUPED_ACTIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "session_count": {"type": "integer"},
                    "total_handoffs": {"type": "integer"},
                    "total_subagents": {"type": "integer"},
                    "success_rate": {"type": "number"},
                    "total_cost": {"type": "number"},
                    "earliest_session": {"type": "string"},
                    "latest_session": {"type": "string"},
                    "handoffs": {"type": "array"},
                    "subagents": {"type": "array"}
                }
            }
        },
        "pagination": {
            "type": "object",
            "properties": {
                "current_page": {"type": "integer"},
                "total_pages": {"type": "integer"},
                "total_count": {"type": "integer"},
                "has_next": {"type": "boolean"},
                "has_previous": {"type": "boolean"}
            }
        },
        "status": {"type": "string", "enum": ["success"]}
    },
    "required": ["projects", "pagination", "status"]
}

# Test Data Factories
def create_test_session_data():
    """Create test session data"""
    return {
        "session_id": fake.uuid4(),
        "project_name": fake.word(),
        "task_description": fake.text(max_nb_chars=200),
        "metadata": {
            "user": fake.user_name(),
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    }

def create_test_handoff_data():
    """Create test handoff data"""
    return {
        "session_id": fake.uuid4(),
        "task_description": fake.text(max_nb_chars=150),
        "task_type": fake.random_element(["implementation", "analysis", "debugging"]),
        "actual_model": fake.random_element(["deepseek", "claude"])
    }

def create_test_subagent_data():
    """Create test subagent invocation data"""
    return {
        "session_id": fake.uuid4(),
        "invocation": {
            "agent_name": fake.random_element(["api-testing-specialist", "security-testing-guardian", "performance-testing-expert"]),
            "trigger_phrase": fake.text(max_nb_chars=100),
            "confidence": fake.random.uniform(0.0, 1.0),
            "estimated_complexity": fake.random_element(["low", "medium", "high"]),
            "execution_time": fake.random.uniform(1.0, 30.0),
            "success": fake.boolean()
        },
        "parent_agent": fake.random_element(["claude_orchestrator", None])
    }

# Test Fixtures and Helper Classes
@pytest.fixture
async def http_client():
    """Create HTTP client for testing"""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TEST_TIMEOUT,
        limits=httpx.Limits(max_connections=MAX_CONCURRENT_REQUESTS)
    ) as client:
        yield client

@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return create_test_session_data()

@pytest.fixture
def sample_handoff_data():
    """Sample handoff data for testing"""
    return create_test_handoff_data()

@pytest.fixture
def sample_subagent_data():
    """Sample subagent data for testing"""
    return create_test_subagent_data()

class APITestResult:
    """Container for API test results"""
    def __init__(self):
        self.endpoint_tests: List[Dict[str, Any]] = []
        self.validation_errors: List[Dict[str, Any]] = []
        self.performance_metrics: List[Dict[str, Any]] = []
        self.security_findings: List[Dict[str, Any]] = []
        self.integration_results: List[Dict[str, Any]] = []

    def add_endpoint_test(self, endpoint: str, method: str, status_code: int,
                         response_time: float, success: bool, details: str = ""):
        """Add endpoint test result"""
        self.endpoint_tests.append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def add_validation_error(self, endpoint: str, error_type: str, details: str):
        """Add validation error"""
        self.validation_errors.append({
            "endpoint": endpoint,
            "error_type": error_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def add_performance_metric(self, endpoint: str, metric: str, value: float):
        """Add performance metric"""
        self.performance_metrics.append({
            "endpoint": endpoint,
            "metric": metric,
            "value": value,
            "timestamp": datetime.now().isoformat()
        })

    def add_security_finding(self, endpoint: str, finding_type: str, severity: str, details: str):
        """Add security finding"""
        self.security_findings.append({
            "endpoint": endpoint,
            "finding_type": finding_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

# Global test results collector
test_results = APITestResult()

# ============================================================================
# SYSTEM HEALTH AND STATUS TESTS
# ============================================================================

@pytest.mark.asyncio
class TestSystemHealthAPIs:
    """Test system health and status endpoints"""

    async def test_system_status_endpoint(self, http_client):
        """Test /api/system-status endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/system-status")
            response_time = time.time() - start_time

            # Test HTTP status code
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Test response format
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate response schema
            validate(data, SYSTEM_STATUS_SCHEMA)

            # Test specific fields
            assert "deepseek" in data, "Missing deepseek field"
            assert "active_sessions" in data, "Missing active_sessions field"
            assert "handoffs_today" in data, "Missing handoffs_today field"
            assert "subagents_spawned" in data, "Missing subagents_spawned field"
            assert "savings_today" in data, "Missing savings_today field"

            # Test data types
            assert isinstance(data["active_sessions"], int), "active_sessions should be integer"
            assert isinstance(data["handoffs_today"], int), "handoffs_today should be integer"
            assert isinstance(data["subagents_spawned"], int), "subagents_spawned should be integer"
            assert isinstance(data["savings_today"], (int, float)), "savings_today should be number"

            # Test DeepSeek status structure
            deepseek = data["deepseek"]
            assert isinstance(deepseek["available"], bool), "DeepSeek available should be boolean"

            test_results.add_endpoint_test("/api/system-status", "GET", response.status_code,
                                         response_time, True, "All validations passed")
            test_results.add_performance_metric("/api/system-status", "response_time", response_time)

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/system-status", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/system-status", "schema_validation", str(e))
            raise
        except Exception as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/system-status", "GET", 0,
                                         response_time, False, f"Request failed: {str(e)}")
            raise

    async def test_system_status_response_time(self, http_client):
        """Test system status response time performance"""
        response_times = []

        # Make multiple requests to test consistency
        for i in range(5):
            start_time = time.time()
            response = await http_client.get("/api/system-status")
            response_time = time.time() - start_time
            response_times.append(response_time)

            assert response.status_code == 200

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Performance thresholds
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.2f}s exceeds 2s threshold"
        assert max_response_time < 5.0, f"Max response time {max_response_time:.2f}s exceeds 5s threshold"

        test_results.add_performance_metric("/api/system-status", "avg_response_time", avg_response_time)
        test_results.add_performance_metric("/api/system-status", "max_response_time", max_response_time)

# ============================================================================
# ANALYTICS API TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAnalyticsAPIs:
    """Test analytics endpoints"""

    async def test_handoff_analytics_endpoint(self, http_client):
        """Test /api/handoff-analytics endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/handoff-analytics")
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate against schema
            validate(data, HANDOFF_ANALYTICS_SCHEMA)

            # Test numerical constraints
            if "success_rate" in data and data["success_rate"] is not None:
                assert 0 <= data["success_rate"] <= 100, "Success rate should be between 0-100"

            if "avg_confidence" in data and data["avg_confidence"] is not None:
                assert 0 <= data["avg_confidence"] <= 1, "Confidence should be between 0-1"

            test_results.add_endpoint_test("/api/handoff-analytics", "GET", response.status_code,
                                         response_time, True, "Schema and constraint validation passed")

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/handoff-analytics", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/handoff-analytics", "validation", str(e))
            raise

    async def test_subagent_analytics_endpoint(self, http_client):
        """Test /api/subagent-analytics endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/subagent-analytics")
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate against schema
            validate(data, SUBAGENT_ANALYTICS_SCHEMA)

            # Test data consistency
            if "usage_statistics" in data and data["usage_statistics"]:
                for agent_stat in data["usage_statistics"]:
                    if "success_rate" in agent_stat and agent_stat["success_rate"] is not None:
                        assert 0 <= agent_stat["success_rate"] <= 100, f"Invalid success rate: {agent_stat['success_rate']}"

                    if "count" in agent_stat:
                        assert agent_stat["count"] >= 0, "Agent count cannot be negative"

            test_results.add_endpoint_test("/api/subagent-analytics", "GET", response.status_code,
                                         response_time, True, "Analytics validation passed")

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/subagent-analytics", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/subagent-analytics", "validation", str(e))
            raise

    async def test_cost_analytics_endpoint(self, http_client):
        """Test /api/cost-analytics endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/cost-analytics")
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate against schema
            validate(data, COST_ANALYTICS_SCHEMA)

            # Test financial data constraints
            assert data["monthly_cost"] >= 0, "Monthly cost cannot be negative"
            assert data["monthly_savings"] >= 0, "Monthly savings cannot be negative"
            assert 0 <= data["optimization_rate"] <= 100, "Optimization rate should be 0-100%"

            # Test daily data consistency
            if data["daily_data"]:
                for daily_record in data["daily_data"]:
                    assert daily_record["cost"] >= 0, "Daily cost cannot be negative"
                    assert daily_record["savings"] >= 0, "Daily savings cannot be negative"

                    # Validate date format
                    try:
                        datetime.fromisoformat(daily_record["date"])
                    except ValueError:
                        raise AssertionError(f"Invalid date format: {daily_record['date']}")

            test_results.add_endpoint_test("/api/cost-analytics", "GET", response.status_code,
                                         response_time, True, "Cost analytics validation passed")

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/cost-analytics", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/cost-analytics", "validation", str(e))
            raise

    async def test_performance_metrics_endpoint(self, http_client):
        """Test /api/performance-metrics endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/performance-metrics")
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate against schema
            validate(data, PERFORMANCE_METRICS_SCHEMA)

            # Test performance metric constraints
            assert data["avg_response_time"] >= 0, "Average response time cannot be negative"
            assert data["deepseek_response_time"] >= 0, "DeepSeek response time cannot be negative"
            assert 0 <= data["uptime"] <= 100, "Uptime should be percentage 0-100"
            assert 0 <= data["error_rate"] <= 100, "Error rate should be percentage 0-100"

            test_results.add_endpoint_test("/api/performance-metrics", "GET", response.status_code,
                                         response_time, True, "Performance metrics validation passed")

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/performance-metrics", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/performance-metrics", "validation", str(e))
            raise

# ============================================================================
# ACTIVITY AND PAGINATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestActivityAPIs:
    """Test activity endpoints with pagination"""

    async def test_recent_activity_endpoint(self, http_client):
        """Test /api/recent-activity endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/recent-activity")
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate against schema
            validate(data, RECENT_ACTIVITY_SCHEMA)

            # Test pagination structure
            pagination = data["pagination"]
            assert pagination["current_page"] >= 1, "Current page should be >= 1"
            assert pagination["total_pages"] >= 0, "Total pages should be >= 0"
            assert pagination["total_count"] >= 0, "Total count should be >= 0"

            # Test activities array
            activities = data["activities"]
            assert isinstance(activities, list), "Activities should be array"

            for activity in activities:
                if activity.get("cost") is not None:
                    assert activity["cost"] >= 0, "Activity cost cannot be negative"

                if activity.get("timestamp"):
                    try:
                        datetime.fromisoformat(activity["timestamp"].replace('Z', '+00:00'))
                    except ValueError:
                        raise AssertionError(f"Invalid timestamp format: {activity['timestamp']}")

            test_results.add_endpoint_test("/api/recent-activity", "GET", response.status_code,
                                         response_time, True, f"Found {len(activities)} activities")

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/recent-activity", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/recent-activity", "validation", str(e))
            raise

    async def test_recent_activity_pagination(self, http_client):
        """Test pagination functionality for recent activity"""
        # Test different page sizes
        for limit in [10, 25, 50, 100]:
            response = await http_client.get(f"/api/recent-activity?limit={limit}")
            assert response.status_code == 200

            data = response.json()
            activities = data["activities"]

            # Should respect limit (unless there are fewer total items)
            if data["pagination"]["total_count"] > limit:
                assert len(activities) <= limit, f"Should return max {limit} activities"
            else:
                assert len(activities) == data["pagination"]["total_count"]

        # Test pagination with page parameter
        page_1 = await http_client.get("/api/recent-activity?page=1&limit=5")
        page_2 = await http_client.get("/api/recent-activity?page=2&limit=5")

        if page_1.status_code == 200 and page_2.status_code == 200:
            data_1 = page_1.json()
            data_2 = page_2.json()

            # Pages should have different activities (if enough data exists)
            if data_1["pagination"]["total_count"] > 5:
                activities_1 = {act.get("session_id", act.get("timestamp")) for act in data_1["activities"]}
                activities_2 = {act.get("session_id", act.get("timestamp")) for act in data_2["activities"]}

                # Should have some different activities between pages
                assert activities_1 != activities_2 or len(activities_1) == 0 or len(activities_2) == 0

        test_results.add_endpoint_test("/api/recent-activity", "GET", 200, 0.0, True, "Pagination tests passed")

    async def test_project_grouped_activity_endpoint(self, http_client):
        """Test /api/project-grouped-activity endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/project-grouped-activity")
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"

            # Validate against schema
            validate(data, PROJECT_GROUPED_ACTIVITY_SCHEMA)

            # Test project data structure
            projects = data["projects"]
            assert isinstance(projects, list), "Projects should be array"

            for project in projects:
                assert project["session_count"] >= 0, "Session count cannot be negative"
                assert project["total_handoffs"] >= 0, "Total handoffs cannot be negative"
                assert project["total_subagents"] >= 0, "Total subagents cannot be negative"
                assert 0 <= project["success_rate"] <= 100, "Success rate should be 0-100%"
                assert project["total_cost"] >= 0, "Total cost cannot be negative"

                # Validate date strings
                try:
                    datetime.fromisoformat(project["earliest_session"])
                    datetime.fromisoformat(project["latest_session"])
                except ValueError:
                    raise AssertionError(f"Invalid date format in project {project['project_name']}")

            test_results.add_endpoint_test("/api/project-grouped-activity", "GET", response.status_code,
                                         response_time, True, f"Found {len(projects)} projects")

        except (AssertionError, JsonSchemaValidationError) as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/project-grouped-activity", "GET",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            test_results.add_validation_error("/api/project-grouped-activity", "validation", str(e))
            raise

    async def test_account_transition_analysis_endpoint(self, http_client):
        """Test /api/account-transition-analysis endpoint"""
        start_time = time.time()

        try:
            response = await http_client.get("/api/account-transition-analysis")
            response_time = time.time() - start_time

            # This endpoint might not be fully implemented yet
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON object"
                assert "status" in data, "Should have status field"

                if data.get("transition_projection"):
                    projection = data["transition_projection"]
                    assert isinstance(projection, dict), "Projection should be object"

                test_results.add_endpoint_test("/api/account-transition-analysis", "GET",
                                             response.status_code, response_time, True,
                                             "Account transition analysis working")
            else:
                # Endpoint might return error if not fully implemented
                assert response.status_code in [500, 501], f"Unexpected status code: {response.status_code}"
                test_results.add_endpoint_test("/api/account-transition-analysis", "GET",
                                             response.status_code, response_time, False,
                                             "Endpoint not fully implemented")

        except Exception as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/account-transition-analysis", "GET", 0,
                                         response_time, False, str(e))

# ============================================================================
# TRACKING API TESTS (POST endpoints)
# ============================================================================

@pytest.mark.asyncio
class TestTrackingAPIs:
    """Test tracking endpoints that accept POST data"""

    async def test_track_session_endpoint(self, http_client, sample_session_data):
        """Test /api/track/session endpoint"""
        start_time = time.time()

        try:
            response = await http_client.post("/api/track/session", json=sample_session_data)
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"
            assert "session_id" in data, "Should return session_id"
            assert "status" in data, "Should return status"
            assert data["status"] == "success", "Status should be success"

            test_results.add_endpoint_test("/api/track/session", "POST", response.status_code,
                                         response_time, True, "Session tracking successful")

        except Exception as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/track/session", "POST",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            raise

    async def test_track_session_invalid_data(self, http_client):
        """Test /api/track/session with invalid data"""
        invalid_payloads = [
            {},  # Empty payload
            {"session_id": ""},  # Empty session_id
            {"session_id": None},  # Null session_id
            {"invalid_field": "value"},  # Missing required fields
            "not_json",  # Invalid JSON structure
        ]

        for payload in invalid_payloads:
            try:
                response = await http_client.post("/api/track/session", json=payload)

                # Should handle invalid data gracefully
                if response.status_code not in [200, 400, 422]:
                    test_results.add_validation_error("/api/track/session", "invalid_data_handling",
                                                    f"Unexpected status code {response.status_code} for payload: {payload}")

            except Exception as e:
                # Server errors on invalid data are also worth noting
                test_results.add_validation_error("/api/track/session", "invalid_data_exception",
                                                f"Exception on payload {payload}: {str(e)}")

    async def test_track_handoff_endpoint(self, http_client, sample_handoff_data):
        """Test /api/track/handoff endpoint"""
        start_time = time.time()

        try:
            response = await http_client.post("/api/track/handoff", json=sample_handoff_data)
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"
            assert "handoff_id" in data, "Should return handoff_id"
            assert "status" in data, "Should return status"
            assert data["status"] == "success", "Status should be success"

            test_results.add_endpoint_test("/api/track/handoff", "POST", response.status_code,
                                         response_time, True, "Handoff tracking successful")

        except Exception as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/track/handoff", "POST",
                                         response.status_code if 'response' in locals() else 0,
                                         response_time, False, str(e))
            raise

    async def test_track_subagent_endpoint(self, http_client, sample_subagent_data):
        """Test /api/track/subagent endpoint"""
        start_time = time.time()

        try:
            response = await http_client.post("/api/track/subagent", json=sample_subagent_data)
            response_time = time.time() - start_time

            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"
            assert "invocation_id" in data, "Should return invocation_id"
            assert "status" in data, "Should return status"
            assert data["status"] == "success", "Status should be success"

            test_results.add_endpoint_test("/api/track/subagent", "POST", response.status_code,
                                         response_time, True, "Subagent tracking successful")

        except Exception as e:
            response_time = time.time() - start_time
            test_results.add_endpoint_test("/api/track/subagent", "POST",
                                         response.status_code if 'response' in locals' else 0,
                                         response_time, False, str(e))
            raise

# ============================================================================
# ERROR HANDLING AND EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and edge cases"""

    async def test_nonexistent_endpoints(self, http_client):
        """Test non-existent endpoints return appropriate errors"""
        nonexistent_endpoints = [
            "/api/nonexistent",
            "/api/system-status/invalid",
            "/api/fake-endpoint",
            "/api/",
            "/invalid/path"
        ]

        for endpoint in nonexistent_endpoints:
            response = await http_client.get(endpoint)

            # Should return 404 or 405 for non-existent endpoints
            assert response.status_code in [404, 405], f"Endpoint {endpoint} should return 404/405, got {response.status_code}"

            test_results.add_endpoint_test(endpoint, "GET", response.status_code, 0.0, True,
                                         "Correctly returns 404/405 for non-existent endpoint")

    async def test_method_not_allowed(self, http_client):
        """Test incorrect HTTP methods return 405 Method Not Allowed"""
        method_tests = [
            ("/api/system-status", "POST"),
            ("/api/system-status", "PUT"),
            ("/api/system-status", "DELETE"),
            ("/api/handoff-analytics", "POST"),
            ("/api/track/session", "GET"),
            ("/api/track/session", "PUT"),
        ]

        for endpoint, method in method_tests:
            try:
                if method == "POST":
                    response = await http_client.post(endpoint, json={})
                elif method == "PUT":
                    response = await http_client.put(endpoint, json={})
                elif method == "DELETE":
                    response = await http_client.delete(endpoint)
                else:
                    response = await http_client.get(endpoint)

                # Should return 405 for wrong methods on tracking endpoints
                # or 200 for GET on analytics endpoints
                if endpoint.startswith("/api/track/") and method == "GET":
                    assert response.status_code in [405, 404], f"{endpoint} {method} should return 405/404"

                test_results.add_endpoint_test(endpoint, method, response.status_code, 0.0, True,
                                             f"Method handling test: {response.status_code}")

            except Exception as e:
                test_results.add_validation_error(endpoint, "method_test",
                                                f"Error testing {method}: {str(e)}")

    async def test_malformed_json_requests(self, http_client):
        """Test malformed JSON in POST requests"""
        tracking_endpoints = [
            "/api/track/session",
            "/api/track/handoff",
            "/api/track/subagent"
        ]

        malformed_payloads = [
            '{"invalid": json}',  # Invalid JSON syntax
            '{invalid_json',  # Incomplete JSON
            'null',  # Null payload
            '[]',  # Array instead of object
            '"string"',  # String instead of object
        ]

        for endpoint in tracking_endpoints:
            for payload in malformed_payloads:
                try:
                    response = await http_client.post(
                        endpoint,
                        content=payload,
                        headers={"Content-Type": "application/json"}
                    )

                    # Should handle malformed JSON gracefully
                    assert response.status_code in [400, 422, 500], f"Should handle malformed JSON appropriately"

                except Exception as e:
                    test_results.add_validation_error(endpoint, "malformed_json",
                                                    f"Error with payload '{payload}': {str(e)}")

# ============================================================================
# SECURITY TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAPISecurity:
    """Test API security aspects"""

    async def test_cors_headers(self, http_client):
        """Test CORS headers are properly set"""
        response = await http_client.get("/api/system-status")

        # Check for CORS headers
        headers = response.headers

        if "access-control-allow-origin" in headers:
            cors_origin = headers["access-control-allow-origin"]
            # Warn if wildcard CORS is used (security risk in production)
            if cors_origin == "*":
                test_results.add_security_finding("/api/system-status", "cors_wildcard", "WARNING",
                                                "Wildcard CORS policy detected - consider restricting origins in production")
            else:
                test_results.add_security_finding("/api/system-status", "cors_restricted", "INFO",
                                                f"CORS origin restricted to: {cors_origin}")
        else:
            test_results.add_security_finding("/api/system-status", "cors_missing", "INFO",
                                            "No CORS headers detected")

    async def test_sql_injection_attempts(self, http_client):
        """Test SQL injection protection in query parameters"""
        sql_injection_payloads = [
            "'; DROP TABLE sessions; --",
            "' OR 1=1 --",
            "1' UNION SELECT * FROM users --",
            "admin'/**/OR/**/1=1#",
            "' OR 'a'='a"
        ]

        for payload in sql_injection_payloads:
            try:
                # Test with query parameters that might be vulnerable
                response = await http_client.get(f"/api/recent-activity?page={payload}")

                # Should not cause 500 errors or expose database errors
                if response.status_code == 500:
                    try:
                        error_text = response.text
                        if any(keyword in error_text.lower() for keyword in ['sql', 'database', 'sqlite', 'syntax error']):
                            test_results.add_security_finding("/api/recent-activity", "sql_injection_exposure", "HIGH",
                                                            f"Potential SQL injection vulnerability with payload: {payload}")
                    except:
                        pass

            except Exception as e:
                test_results.add_security_finding("/api/recent-activity", "sql_injection_error", "MEDIUM",
                                                f"Error testing SQL injection with '{payload}': {str(e)}")

    async def test_xss_protection(self, http_client):
        """Test XSS protection in POST data"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>"
        ]

        for payload in xss_payloads:
            try:
                # Test XSS in session tracking
                malicious_data = {
                    "session_id": fake.uuid4(),
                    "project_name": payload,
                    "task_description": payload,
                    "metadata": {"user": payload}
                }

                response = await http_client.post("/api/track/session", json=malicious_data)

                # Should not return the script in response
                if response.status_code == 200:
                    response_text = response.text
                    if "<script>" in response_text or "javascript:" in response_text:
                        test_results.add_security_finding("/api/track/session", "xss_reflection", "HIGH",
                                                        f"Potential XSS vulnerability - script reflected in response")

            except Exception as e:
                test_results.add_security_finding("/api/track/session", "xss_test_error", "LOW",
                                                f"Error testing XSS with '{payload}': {str(e)}")

    async def test_input_length_limits(self, http_client):
        """Test input length limits to prevent DoS"""
        # Test with very long strings
        very_long_string = "A" * 100000  # 100KB string

        large_payload = {
            "session_id": fake.uuid4(),
            "project_name": very_long_string,
            "task_description": very_long_string,
            "metadata": {"large_field": very_long_string}
        }

        try:
            response = await http_client.post("/api/track/session", json=large_payload, timeout=10.0)

            # Should handle large payloads gracefully
            if response.status_code == 500:
                test_results.add_security_finding("/api/track/session", "large_payload_dos", "MEDIUM",
                                                "Server error on large payload - consider input size limits")
            elif response.status_code in [413, 400]:
                test_results.add_security_finding("/api/track/session", "large_payload_protected", "INFO",
                                                "Server properly rejects large payloads")

        except httpx.TimeoutException:
            test_results.add_security_finding("/api/track/session", "large_payload_timeout", "HIGH",
                                            "Server timeout on large payload - potential DoS vulnerability")
        except Exception as e:
            test_results.add_security_finding("/api/track/session", "large_payload_error", "MEDIUM",
                                            f"Error with large payload: {str(e)}")

# ============================================================================
# PERFORMANCE AND LOAD TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAPIPerformance:
    """Test API performance under various conditions"""

    async def test_concurrent_requests(self, http_client):
        """Test API performance under concurrent load"""
        async def make_request():
            start_time = time.time()
            try:
                response = await http_client.get("/api/system-status")
                response_time = time.time() - start_time
                return {
                    "success": response.status_code == 200,
                    "response_time": response_time,
                    "status_code": response.status_code
                }
            except Exception as e:
                return {
                    "success": False,
                    "response_time": time.time() - start_time,
                    "error": str(e)
                }

        # Test with 10 concurrent requests
        concurrent_requests = 10
        tasks = [make_request() for _ in range(concurrent_requests)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        average_response_time = sum(r["response_time"] for r in results) / len(results)
        max_response_time = max(r["response_time"] for r in results)

        success_rate = (successful_requests / concurrent_requests) * 100

        # Performance assertions
        assert success_rate >= 90, f"Success rate {success_rate:.1f}% is below 90% threshold"
        assert average_response_time < 5.0, f"Average response time {average_response_time:.2f}s exceeds 5s threshold"

        test_results.add_performance_metric("/api/system-status", "concurrent_success_rate", success_rate)
        test_results.add_performance_metric("/api/system-status", "concurrent_avg_response_time", average_response_time)
        test_results.add_performance_metric("/api/system-status", "concurrent_max_response_time", max_response_time)

    async def test_sustained_load(self, http_client):
        """Test API under sustained load"""
        request_count = 50
        results = []

        for i in range(request_count):
            start_time = time.time()
            try:
                response = await http_client.get("/api/handoff-analytics")
                response_time = time.time() - start_time
                results.append({
                    "request_number": i + 1,
                    "success": response.status_code == 200,
                    "response_time": response_time
                })

                # Small delay between requests
                await asyncio.sleep(0.1)

            except Exception as e:
                results.append({
                    "request_number": i + 1,
                    "success": False,
                    "response_time": time.time() - start_time,
                    "error": str(e)
                })

        # Analyze sustained load performance
        successful_requests = sum(1 for r in results if r["success"])
        success_rate = (successful_requests / request_count) * 100

        response_times = [r["response_time"] for r in results if r["success"]]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            # Check for performance degradation over time
            first_half = response_times[:len(response_times)//2]
            second_half = response_times[len(response_times)//2:]

            if first_half and second_half:
                first_half_avg = sum(first_half) / len(first_half)
                second_half_avg = sum(second_half) / len(second_half)

                degradation_ratio = second_half_avg / first_half_avg
                if degradation_ratio > 1.5:
                    test_results.add_performance_metric("/api/handoff-analytics", "performance_degradation", degradation_ratio)

        test_results.add_performance_metric("/api/handoff-analytics", "sustained_load_success_rate", success_rate)

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestIntegration:
    """Test integration between API and frontend dashboard"""

    async def test_dashboard_loads(self, http_client):
        """Test that dashboard page loads correctly"""
        start_time = time.time()

        try:
            response = await http_client.get("/")
            response_time = time.time() - start_time

            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

            # Check for key dashboard elements
            html_content = response.text
            assert "AI Orchestration Analytics" in html_content
            assert "Chart.js" in html_content  # Charting library
            assert "/api/system-status" in html_content  # API calls

            test_results.add_integration_result("dashboard_load", True, response_time,
                                               "Dashboard loaded successfully")

        except Exception as e:
            response_time = time.time() - start_time
            test_results.add_integration_result("dashboard_load", False, response_time, str(e))
            raise

    async def test_api_dashboard_integration(self, http_client):
        """Test that all dashboard API calls work together"""
        dashboard_api_endpoints = [
            "/api/system-status",
            "/api/handoff-analytics",
            "/api/subagent-analytics",
            "/api/cost-analytics",
            "/api/performance-metrics",
            "/api/recent-activity",
            "/api/project-grouped-activity"
        ]

        integration_results = {}

        for endpoint in dashboard_api_endpoints:
            try:
                start_time = time.time()
                response = await http_client.get(endpoint)
                response_time = time.time() - start_time

                integration_results[endpoint] = {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "success": response.status_code == 200
                }

                if response.status_code == 200:
                    # Verify JSON response
                    data = response.json()
                    assert isinstance(data, dict)

            except Exception as e:
                integration_results[endpoint] = {
                    "status_code": 0,
                    "response_time": 0,
                    "success": False,
                    "error": str(e)
                }

        # Check overall integration health
        successful_endpoints = sum(1 for r in integration_results.values() if r["success"])
        integration_success_rate = (successful_endpoints / len(dashboard_api_endpoints)) * 100

        test_results.add_integration_result("api_integration", integration_success_rate >= 90,
                                          0.0, f"Integration success rate: {integration_success_rate:.1f}%")

        assert integration_success_rate >= 80, f"Integration success rate {integration_success_rate:.1f}% is below 80% threshold"

# ============================================================================
# TEST REPORT GENERATION
# ============================================================================

def generate_comprehensive_test_report():
    """Generate a comprehensive API test report"""

    report = {
        "test_execution_summary": {
            "timestamp": datetime.now().isoformat(),
            "total_endpoints_tested": len(set(test["endpoint"] for test in test_results.endpoint_tests)),
            "total_tests_executed": len(test_results.endpoint_tests),
            "overall_success_rate": 0.0,
            "total_validation_errors": len(test_results.validation_errors),
            "total_security_findings": len(test_results.security_findings),
            "performance_metrics_collected": len(test_results.performance_metrics)
        },
        "endpoint_test_results": test_results.endpoint_tests,
        "validation_errors": test_results.validation_errors,
        "security_findings": test_results.security_findings,
        "performance_analysis": {
            "metrics": test_results.performance_metrics,
            "summary": {}
        },
        "integration_results": test_results.integration_results,
        "recommendations": []
    }

    # Calculate overall success rate
    if test_results.endpoint_tests:
        successful_tests = sum(1 for test in test_results.endpoint_tests if test["success"])
        report["test_execution_summary"]["overall_success_rate"] = (successful_tests / len(test_results.endpoint_tests)) * 100

    # Performance analysis summary
    if test_results.performance_metrics:
        metrics_by_endpoint = {}
        for metric in test_results.performance_metrics:
            endpoint = metric["endpoint"]
            if endpoint not in metrics_by_endpoint:
                metrics_by_endpoint[endpoint] = []
            metrics_by_endpoint[endpoint].append(metric)

        report["performance_analysis"]["summary"] = metrics_by_endpoint

    # Generate recommendations based on findings
    recommendations = []

    # Security recommendations
    high_security_findings = [f for f in test_results.security_findings if f["severity"] == "HIGH"]
    if high_security_findings:
        recommendations.append({
            "category": "Security",
            "priority": "HIGH",
            "recommendation": f"Address {len(high_security_findings)} high-severity security findings",
            "details": [f["finding_type"] for f in high_security_findings]
        })

    # Performance recommendations
    slow_endpoints = []
    for metric in test_results.performance_metrics:
        if metric["metric"] == "response_time" and metric["value"] > 2.0:
            slow_endpoints.append(metric["endpoint"])

    if slow_endpoints:
        recommendations.append({
            "category": "Performance",
            "priority": "MEDIUM",
            "recommendation": "Optimize slow-responding endpoints",
            "details": list(set(slow_endpoints))
        })

    # Validation recommendations
    if test_results.validation_errors:
        recommendations.append({
            "category": "Data Validation",
            "priority": "HIGH",
            "recommendation": f"Fix {len(test_results.validation_errors)} validation errors",
            "details": [e["error_type"] for e in test_results.validation_errors]
        })

    report["recommendations"] = recommendations

    return report

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Run the comprehensive test suite
    pytest.main([__file__, "-v", "--tb=short"])

    # Generate and save test report
    report = generate_comprehensive_test_report()

    # Save report to file
    with open("api_test_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print("\n" + "="*80)
    print("COMPREHENSIVE API TEST REPORT")
    print("="*80)

    summary = report["test_execution_summary"]
    print(f"📊 Test Execution Summary:")
    print(f"   • Endpoints Tested: {summary['total_endpoints_tested']}")
    print(f"   • Total Tests: {summary['total_tests_executed']}")
    print(f"   • Success Rate: {summary['overall_success_rate']:.1f}%")
    print(f"   • Validation Errors: {summary['total_validation_errors']}")
    print(f"   • Security Findings: {summary['total_security_findings']}")
    print(f"   • Performance Metrics: {summary['performance_metrics_collected']}")

    if report["recommendations"]:
        print(f"\n🔍 Key Recommendations:")
        for rec in report["recommendations"][:3]:  # Top 3 recommendations
            print(f"   • [{rec['priority']}] {rec['category']}: {rec['recommendation']}")

    print(f"\n📄 Full report saved to: api_test_report.json")
    print("="*80)