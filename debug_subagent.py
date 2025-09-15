#!/usr/bin/env python3
"""
Simple debug script to test subagent endpoint directly
"""

import json
import requests

BASE_URL = "http://localhost:8000"

def test_subagent_simple():
    """Test subagent endpoint with minimal data"""
    print("Testing subagent endpoint...")

    try:
        # Create a minimal session first
        session_data = {
            "session_id": "debug_session",
            "project_name": "AI-Orchestration-Analytics",
            "task_description": "Debug test",
            "metadata": {"debug": True}
        }

        session_response = requests.post(f"{BASE_URL}/api/track/session", json=session_data)
        print(f"Session response: {session_response.status_code}")
        if session_response.status_code != 200:
            print(f"Session failed: {session_response.text}")
            return False

        # Now test subagent
        subagent_data = {
            "session_id": "debug_session",
            "invocation": {
                "agent_type": "specialized",
                "agent_name": "api-testing-specialist",
                "trigger_phrase": "test api",
                "task_description": "Debug test",
                "parent_agent": "claude",
                "confidence": 0.8,
                "estimated_complexity": "low"
            },
            "parent_agent": "claude"
        }

        print(f"Sending subagent data: {json.dumps(subagent_data, indent=2)}")

        subagent_response = requests.post(f"{BASE_URL}/api/track/subagent", json=subagent_data)
        print(f"Subagent response status: {subagent_response.status_code}")
        print(f"Subagent response text: {subagent_response.text}")

        if subagent_response.status_code == 200:
            print("SUCCESS!")
            return True
        else:
            print("FAILED!")
            return False

    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    test_subagent_simple()