# API Reference

> RESTful API endpoints for tracking orchestration events and retrieving analytics data.

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently, no authentication is required for local development. Future versions may include API key authentication.

---

## Tracking Endpoints

### Track Orchestration Session
Create a new orchestration session for tracking.

**Endpoint**: `POST /track/session`

**Request Body**:
```json
{
  "session_id": "unique_session_identifier",
  "project_name": "AI-Orchestration-Analytics",
  "task_description": "Implement new analytics feature",
  "metadata": {
    "version": "1.0.0",
    "user_context": {...}
  }
}
```

**Response**:
```json
{
  "session_id": 12345,
  "status": "success"
}
```

### Track Model Handoff
Record a task routing decision between Claude and DeepSeek.

**Endpoint**: `POST /track/handoff`

**Request Body**:
```json
{
  "session_id": "sess_12345",
  "task_type": "implementation",
  "task_description": "Implement user authentication",
  "actual_model": "deepseek"
}
```

**Response**:
```json
{
  "handoff_id": 67890,
  "status": "success"
}
```

### Track Subagent Invocation
Log specialized agent usage.

**Endpoint**: `POST /track/subagent`

**Request Body**:
```json
{
  "session_id": "sess_12345",
  "invocation": {
    "agent_type": "api-testing",
    "agent_name": "api-testing-specialist",
    "trigger_phrase": "test api endpoints",
    "task_description": "Validate REST API security",
    "confidence": 0.9
  },
  "parent_agent": "claude_orchestrator"
}
```

**Response**:
```json
{
  "invocation_id": 24680,
  "status": "success"
}
```

---

## Analytics Endpoints

### System Status
Get current system health and metrics.

**Endpoint**: `GET /system-status`

**Response**:
```json
{
  "deepseek": {
    "available": true,
    "response_time": 2.06,
    "status": "healthy"
  },
  "active_sessions": 3,
  "handoffs_today": 25,
  "subagents_spawned": 8,
  "savings_today": 15.75
}
```

### Handoff Analytics
Retrieve handoff decision analytics and patterns.

**Endpoint**: `GET /handoff-analytics`

**Query Parameters**:
- `start_date` (optional): ISO date string
- `end_date` (optional): ISO date string

**Response**:
```json
{
  "total_handoffs": 150,
  "deepseek_handoffs": 135,
  "claude_handoffs": 15,
  "avg_confidence": 0.92,
  "total_cost": 2.25,
  "total_savings": 22.50,
  "avg_response_time": 1.85,
  "success_rate": 96.7
}
```

### Subagent Analytics
Get comprehensive subagent usage statistics.

**Endpoint**: `GET /subagent-analytics`

**Response**:
```json
{
  "usage_statistics": [
    {
      "agent_name": "api-testing-specialist",
      "agent_type": "api-testing",
      "invocation_count": 45,
      "avg_execution_time": 15.2,
      "success_rate": 97.8,
      "total_tokens": 12500,
      "total_cost": 0.75
    }
  ],
  "patterns": {
    "total_invocations": 120,
    "unique_agents_used": 4,
    "most_used_agents": ["api-testing-specialist", "security-testing-guardian"],
    "fastest_agents": ["general-purpose", "api-testing-specialist"],
    "most_reliable_agents": ["database-testing-specialist"]
  },
  "recommendations": [
    "Consider utilizing unused agents: performance-testing-expert",
    "Some agents have slow execution times. Review task complexity."
  ]
}
```

### Cost Analytics
Retrieve cost optimization metrics and trends.

**Endpoint**: `GET /cost-analytics`

**Response**:
```json
{
  "monthly_cost": 15.50,
  "monthly_savings": 185.20,
  "optimization_rate": 92.3,
  "daily_data": [
    {
      "date": "2025-01-13",
      "cost": 0.85,
      "savings": 8.20
    },
    {
      "date": "2025-01-14",
      "cost": 1.20,
      "savings": 12.50
    }
  ]
}
```

### Performance Metrics
Get system performance and health metrics.

**Endpoint**: `GET /performance-metrics`

**Response**:
```json
{
  "avg_response_time": 1.8,
  "deepseek_response_time": 2.06,
  "uptime": 99.2,
  "error_rate": 2.1
}
```

### Recent Activity
Get recent orchestration activity log.

**Endpoint**: `GET /recent-activity`

**Query Parameters**:
- `limit` (optional): Number of activities to return (default: 50)

**Response**:
```json
{
  "activities": [
    {
      "timestamp": "2025-01-16T10:30:00Z",
      "session_id": "sess_12345",
      "event_type": "handoff",
      "model_or_agent": "deepseek",
      "description": "Code implementation task routed to DeepSeek",
      "status": "success",
      "cost": 0.0
    },
    {
      "timestamp": "2025-01-16T10:25:00Z",
      "session_id": "sess_12344",
      "event_type": "subagent",
      "model_or_agent": "api-testing-specialist",
      "description": "API testing specialist invoked",
      "status": "success",
      "cost": 0.025
    }
  ]
}
```

---

## Error Responses

### Standard Error Format
All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": "Additional error context (optional)"
  }
}
```

### Common Error Codes
- `400 Bad Request`: Invalid request body or parameters
- `404 Not Found`: Endpoint or resource not found
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: System maintenance or overload

---

## Rate Limiting
Currently no rate limiting is implemented for local development. Production deployments should implement appropriate rate limiting based on usage patterns.

---

## Response Headers
All responses include:
```
Content-Type: application/json
X-API-Version: 1.0.0
X-Response-Time: <time_in_ms>
```

---

## SDK Support
Python SDK available in the main codebase:
```python
from src.core.database import OrchestrationDB

db = OrchestrationDB()
# Direct database access for advanced use cases
```

---

*For additional API features or custom endpoints, refer to the source code in `src/dashboard/orchestration_dashboard.py`.*