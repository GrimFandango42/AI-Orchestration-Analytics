"""
AI Model Handoff Monitor
========================
Tracks and analyzes handoffs between Claude Code and DeepSeek local model
"""

import time
import json
import requests
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.core.database import OrchestrationDB

@dataclass
class HandoffDecision:
    """Handoff routing decision result"""
    should_route_to_deepseek: bool
    confidence: float
    reasoning: str
    estimated_tokens: int
    cost_savings: float
    route_reason: str
    response_time_estimate: float

class DeepSeekClient:
    """DeepSeek local model client"""

    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url
        self.api_url = f"{base_url}/v1"
        self.model_name = "deepseek-r1"

    def is_available(self) -> bool:
        """Check if DeepSeek is running and available"""
        try:
            response = requests.get(f"{self.api_url}/models", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status of DeepSeek"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.api_url}/models", timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                models = response.json().get('data', [])
                return {
                    'available': True,
                    'response_time': response_time,
                    'models_loaded': len(models),
                    'status': 'healthy'
                }
            else:
                return {
                    'available': False,
                    'error': f"HTTP {response.status_code}",
                    'status': 'error'
                }
        except requests.exceptions.RequestException as e:
            return {
                'available': False,
                'error': str(e),
                'status': 'offline'
            }

class HandoffMonitor:
    """Monitor and track model handoffs"""

    def __init__(self, db: OrchestrationDB = None):
        self.db = db or OrchestrationDB()
        self.deepseek_client = DeepSeekClient()

        # Task classification patterns
        self.deepseek_patterns = {
            'high_priority': [
                'implement', 'code', 'function', 'class', 'refactor', 'debug',
                'write', 'create', 'generate', 'simple', 'basic', 'routine',
                'fix bug', 'add feature', 'update code', 'modify'
            ],
            'medium_priority': [
                'fix', 'update', 'modify', 'add', 'remove', 'change', 'test',
                'documentation', 'comment', 'format', 'cleanup'
            ],
            'low_priority': [
                'analyze', 'explain', 'design', 'architecture', 'strategy',
                'complex', 'advanced', 'optimize performance', 'security',
                'review', 'plan', 'recommend', 'evaluate'
            ]
        }

    def analyze_task(self, task_description: str, task_type: str = "general",
                    session_context: Dict = None) -> HandoffDecision:
        """
        Analyze task to determine optimal routing between Claude and DeepSeek
        """
        task_lower = task_description.lower()

        # Calculate pattern scores
        high_score = sum(1 for pattern in self.deepseek_patterns['high_priority']
                        if pattern in task_lower)
        medium_score = sum(1 for pattern in self.deepseek_patterns['medium_priority']
                          if pattern in task_lower)
        low_score = sum(1 for pattern in self.deepseek_patterns['low_priority']
                       if pattern in task_lower)

        # Calculate routing decision
        total_score = (high_score * 3) + (medium_score * 2) - (low_score * 2)

        # Check DeepSeek availability
        deepseek_available = self.deepseek_client.is_available()

        # Base routing decision
        should_route = (total_score > 0 or task_type in [
            'code_generation', 'debugging', 'implementation', 'refactoring'
        ]) and deepseek_available

        # Confidence calculation
        confidence = min(0.95, max(0.3, (abs(total_score) + 2) / 8))
        if not deepseek_available:
            confidence *= 0.1  # Very low confidence if DeepSeek unavailable

        # Reasoning
        reasoning_parts = []
        if high_score > 0:
            reasoning_parts.append(f"Implementation task detected ({high_score} indicators)")
        if medium_score > 0:
            reasoning_parts.append(f"Routine task indicators ({medium_score})")
        if low_score > 0:
            reasoning_parts.append(f"Complex reasoning required ({low_score} indicators)")
        if not deepseek_available:
            reasoning_parts.append("DeepSeek unavailable - fallback to Claude")
        if not reasoning_parts:
            reasoning_parts.append("General task - evaluating complexity")

        reasoning = "; ".join(reasoning_parts)

        # Cost calculation
        estimated_tokens = min(4000, max(200, len(task_description) * 4))
        cost_per_token_claude = 0.000015  # $0.015 per 1k tokens
        cost_savings = (cost_per_token_claude * estimated_tokens) if should_route else 0

        # Response time estimation
        response_time_estimate = 2.0 if should_route else 0.5  # DeepSeek slower but local

        # Route reason categorization
        route_reason = self._categorize_route_reason(
            high_score, medium_score, low_score, deepseek_available
        )

        return HandoffDecision(
            should_route_to_deepseek=should_route,
            confidence=confidence,
            reasoning=reasoning,
            estimated_tokens=estimated_tokens,
            cost_savings=cost_savings,
            route_reason=route_reason,
            response_time_estimate=response_time_estimate
        )

    def _categorize_route_reason(self, high: int, medium: int, low: int,
                                deepseek_available: bool) -> str:
        """Categorize the routing decision reason"""
        if not deepseek_available:
            return "deepseek_unavailable"
        elif high >= 2:
            return "code_implementation_task"
        elif high >= 1:
            return "simple_coding_task"
        elif medium >= 2:
            return "routine_modification"
        elif low >= 1:
            return "complex_reasoning_needed"
        else:
            return "general_task_evaluation"

    def track_handoff(self, session_id: str, task_description: str, task_type: str,
                     decision: HandoffDecision, actual_model: str = None) -> int:
        """Track a handoff decision and execution"""

        # Determine actual routing
        if actual_model:
            routed_to_deepseek = actual_model.lower() == 'deepseek'
        else:
            routed_to_deepseek = decision.should_route_to_deepseek

        source_model = "claude_orchestrator"
        target_model = "deepseek" if routed_to_deepseek else "claude"

        # Track in database
        handoff_id = self.db.track_handoff(
            session_id=session_id,
            task_type=task_type,
            task_description=task_description,
            source_model=source_model,
            target_model=target_model,
            handoff_reason=decision.reasoning,
            confidence_score=decision.confidence,
            tokens_used=decision.estimated_tokens,
            cost=0 if routed_to_deepseek else (decision.estimated_tokens * 0.000015),
            savings=decision.cost_savings if routed_to_deepseek else 0,
            success=True,  # Will be updated when task completes
            response_time=decision.response_time_estimate,
            metadata={
                'route_reason': decision.route_reason,
                'deepseek_available': self.deepseek_client.is_available(),
                'decision_factors': {
                    'estimated_tokens': decision.estimated_tokens,
                    'confidence': decision.confidence
                }
            }
        )

        return handoff_id

    def update_handoff_result(self, handoff_id: int, success: bool,
                             actual_tokens: int = None, actual_cost: float = None,
                             actual_response_time: float = None):
        """Update handoff result with actual execution metrics"""
        # This would update the handoff record with actual results
        # Implementation depends on database update methods
        pass

    def get_routing_analytics(self, start_date: str = None,
                            end_date: str = None) -> Dict[str, Any]:
        """Get routing decision analytics"""
        return self.db.get_handoff_analytics(start_date, end_date)

    def get_deepseek_performance(self) -> Dict[str, Any]:
        """Get DeepSeek performance metrics"""
        health = self.deepseek_client.get_health_status()

        # Get recent handoff analytics
        analytics = self.get_routing_analytics()

        return {
            'health': health,
            'routing_stats': analytics,
            'availability_score': 1.0 if health['available'] else 0.0,
            'recommendation': self._get_performance_recommendation(health, analytics)
        }

    def _get_performance_recommendation(self, health: Dict, analytics: Dict) -> str:
        """Generate performance recommendations"""
        if not health['available']:
            return "DeepSeek is offline. Start LM Studio and load DeepSeek model."

        if health.get('response_time', 0) > 3.0:
            return "DeepSeek response time is slow. Consider optimizing model settings."

        deepseek_ratio = analytics.get('deepseek_handoffs', 0) / max(
            analytics.get('total_handoffs', 1), 1
        )

        if deepseek_ratio < 0.7:
            return "Low DeepSeek usage. Review task routing patterns for optimization."

        return "Performance is optimal. Continue current routing strategy."

    def simulate_routing(self, tasks: list) -> Dict[str, Any]:
        """Simulate routing decisions for a batch of tasks"""
        results = {
            'total_tasks': len(tasks),
            'deepseek_routed': 0,
            'claude_routed': 0,
            'total_savings': 0,
            'decisions': []
        }

        for i, task in enumerate(tasks):
            decision = self.analyze_task(task.get('description', ''),
                                       task.get('type', 'general'))

            results['decisions'].append({
                'task_id': i,
                'description': task.get('description', ''),
                'routed_to': 'deepseek' if decision.should_route_to_deepseek else 'claude',
                'confidence': decision.confidence,
                'reasoning': decision.reasoning,
                'savings': decision.cost_savings
            })

            if decision.should_route_to_deepseek:
                results['deepseek_routed'] += 1
            else:
                results['claude_routed'] += 1

            results['total_savings'] += decision.cost_savings

        results['deepseek_percentage'] = (results['deepseek_routed'] / len(tasks)) * 100
        results['optimization_score'] = min(100, results['deepseek_percentage'] * 1.1)

        return results