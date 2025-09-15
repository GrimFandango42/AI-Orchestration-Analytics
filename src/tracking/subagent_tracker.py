"""
Subagent Tracking and Analytics
===============================
Monitors specialized agent invocations and performance patterns
"""

import time
import json
import re
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass

from src.core.database import OrchestrationDB

@dataclass
class SubagentInvocation:
    """Subagent invocation event"""
    agent_type: str
    agent_name: str
    trigger_phrase: str
    task_description: str
    parent_agent: Optional[str] = None
    confidence: float = 0.8
    estimated_complexity: str = "medium"

class SubagentTracker:
    """Tracks and analyzes subagent usage patterns"""

    def __init__(self, db: OrchestrationDB = None):
        self.db = db or OrchestrationDB()

        # Subagent definitions based on USER_MEMORIES.md
        self.available_agents = {
            'api-testing-specialist': {
                'triggers': [
                    'test this api', 'validate api contract', 'api security testing',
                    'test api endpoints', 'api testing', 'rest testing', 'graphql testing'
                ],
                'expertise': 'REST/GraphQL testing, contract validation, security testing',
                'mcp_integration': ['Smart Test Generation', 'Coverage Analytics', 'CI/CD Orchestration'],
                'specialization': 'OWASP API Top 10, authentication testing, performance benchmarking'
            },
            'performance-testing-expert': {
                'triggers': [
                    'performance testing', 'load testing', 'check bottlenecks',
                    'scalability testing', 'stress testing', 'benchmark'
                ],
                'expertise': 'Load testing, stress testing, performance profiling, optimization',
                'mcp_integration': ['CI/CD Orchestration', 'Coverage Analytics', 'Code Intelligence'],
                'specialization': 'k6/Artillery integration, APM tools, performance regression detection'
            },
            'security-testing-guardian': {
                'triggers': [
                    'security testing', 'vulnerability assessment', 'penetration testing',
                    'security scan', 'owasp', 'security audit'
                ],
                'expertise': 'SAST/DAST, OWASP Top 10, compliance validation, threat analysis',
                'mcp_integration': ['Smart Test Generation', 'Code Intelligence', 'CI/CD Orchestration'],
                'specialization': 'Automated security scanning, compliance reporting, vulnerability management'
            },
            'database-testing-specialist': {
                'triggers': [
                    'database testing', 'schema migration', 'data integrity',
                    'etl testing', 'migration testing', 'data quality'
                ],
                'expertise': 'Schema validation, data quality, migration testing, performance tuning',
                'mcp_integration': ['Smart Test Generation', 'Performance Testing', 'CI/CD Orchestration'],
                'specialization': 'Migration safety, backup/recovery testing, data consistency validation'
            },
            'general-purpose': {
                'triggers': [
                    'research', 'search for', 'find', 'explore', 'investigate',
                    'multi-step task', 'complex workflow'
                ],
                'expertise': 'Research, code search, multi-step task execution',
                'mcp_integration': ['All tools'],
                'specialization': 'Complex multi-step workflows, research tasks'
            }
        }

        # Pattern matching for agent chaining
        self.chaining_patterns = [
            'then use', 'followed by', 'after that', 'next', 'also',
            'integrate with', 'combined with', 'along with'
        ]

    def detect_subagent_invocation(self, user_input: str, context: Dict = None) -> List[SubagentInvocation]:
        """Detect if user input should trigger subagent(s)"""
        invocations = []
        input_lower = user_input.lower()

        # Check for explicit agent mentions
        explicit_agents = self._detect_explicit_agents(input_lower)

        # Check for trigger phrase matches
        triggered_agents = self._detect_trigger_phrases(input_lower)

        # Check for agent chaining patterns
        chained_agents = self._detect_agent_chaining(input_lower, explicit_agents + triggered_agents)

        all_detected = set(explicit_agents + triggered_agents + chained_agents)

        for agent_name in all_detected:
            if agent_name in self.available_agents:
                invocation = SubagentInvocation(
                    agent_type=agent_name.split('-')[0] if '-' in agent_name else agent_name,
                    agent_name=agent_name,
                    trigger_phrase=self._find_matching_trigger(input_lower, agent_name),
                    task_description=user_input,
                    confidence=self._calculate_confidence(input_lower, agent_name),
                    estimated_complexity=self._estimate_complexity(user_input, agent_name)
                )
                invocations.append(invocation)

        return invocations

    def _detect_explicit_agents(self, text: str) -> List[str]:
        """Detect explicit agent name mentions"""
        explicit = []
        for agent_name in self.available_agents.keys():
            # Check for exact name or variations
            variations = [
                agent_name,
                agent_name.replace('-', ' '),
                agent_name.replace('-testing-', '-'),
                agent_name.replace('-specialist', ''),
                agent_name.replace('-expert', ''),
                agent_name.replace('-guardian', '')
            ]

            for variation in variations:
                if variation in text:
                    explicit.append(agent_name)
                    break

        return explicit

    def _detect_trigger_phrases(self, text: str) -> List[str]:
        """Detect agent trigger phrases"""
        triggered = []

        for agent_name, config in self.available_agents.items():
            for trigger in config['triggers']:
                if trigger.lower() in text:
                    triggered.append(agent_name)
                    break

        return triggered

    def _detect_agent_chaining(self, text: str, existing_agents: List[str]) -> List[str]:
        """Detect patterns indicating multiple agents should be used"""
        chained = []

        # If chaining patterns are present and we have existing agents,
        # suggest complementary agents
        has_chaining = any(pattern in text for pattern in self.chaining_patterns)

        if has_chaining and existing_agents:
            # Security + Performance commonly chained
            if any('security' in agent for agent in existing_agents):
                if 'performance-testing-expert' not in existing_agents:
                    chained.append('performance-testing-expert')

            # API testing often needs security testing
            if 'api-testing-specialist' in existing_agents:
                if 'security-testing-guardian' not in existing_agents and 'security' in text:
                    chained.append('security-testing-guardian')

            # Database operations often need performance testing
            if 'database-testing-specialist' in existing_agents:
                if 'performance' in text and 'performance-testing-expert' not in existing_agents:
                    chained.append('performance-testing-expert')

        return chained

    def _find_matching_trigger(self, text: str, agent_name: str) -> str:
        """Find the specific trigger phrase that matched"""
        triggers = self.available_agents[agent_name]['triggers']
        for trigger in triggers:
            if trigger.lower() in text:
                return trigger
        return triggers[0] if triggers else "implicit"

    def _calculate_confidence(self, text: str, agent_name: str) -> float:
        """Calculate confidence score for agent invocation"""
        config = self.available_agents[agent_name]

        # Base confidence
        confidence = 0.6

        # Increase for explicit mentions
        if agent_name.replace('-', ' ') in text or agent_name in text:
            confidence += 0.3

        # Increase for multiple trigger matches
        trigger_matches = sum(1 for trigger in config['triggers'] if trigger in text)
        confidence += min(0.2, trigger_matches * 0.1)

        # Increase for domain-specific keywords
        domain_keywords = {
            'api-testing-specialist': ['api', 'endpoint', 'rest', 'graphql', 'postman'],
            'performance-testing-expert': ['performance', 'load', 'stress', 'benchmark', 'latency'],
            'security-testing-guardian': ['security', 'vulnerability', 'owasp', 'penetration', 'audit'],
            'database-testing-specialist': ['database', 'schema', 'migration', 'sql', 'data'],
            'general-purpose': ['research', 'search', 'find', 'explore', 'complex']
        }

        if agent_name in domain_keywords:
            keyword_matches = sum(1 for keyword in domain_keywords[agent_name] if keyword in text)
            confidence += min(0.2, keyword_matches * 0.05)

        return min(0.95, confidence)

    def _estimate_complexity(self, text: str, agent_name: str) -> str:
        """Estimate task complexity for the agent"""
        complexity_indicators = {
            'high': ['comprehensive', 'complete', 'full', 'enterprise', 'production', 'advanced'],
            'medium': ['test', 'validate', 'check', 'analyze', 'review', 'standard'],
            'low': ['simple', 'basic', 'quick', 'basic', 'minimal']
        }

        text_lower = text.lower()

        for level, indicators in complexity_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return level

        # Default based on text length and agent type
        if len(text) > 200:
            return 'high'
        elif len(text) > 100:
            return 'medium'
        else:
            return 'low'

    def track_invocation(self, session_id: str, invocation: SubagentInvocation,
                        parent_agent: str = None, execution_start: float = None) -> int:
        """Track a subagent invocation"""

        start_time = execution_start or time.time()

        # Handle both dict and SubagentInvocation object formats
        if isinstance(invocation, dict):
            # Convert dict to SubagentInvocation object
            invocation_obj = SubagentInvocation(
                agent_type=invocation.get('agent_type', 'specialized'),
                agent_name=invocation.get('agent_name', 'unknown'),
                trigger_phrase=invocation.get('trigger_phrase', ''),
                task_description=invocation.get('task_description', ''),
                parent_agent=invocation.get('parent_agent'),
                confidence=invocation.get('confidence', 0.8),
                estimated_complexity=invocation.get('estimated_complexity', 'medium')
            )
        else:
            invocation_obj = invocation

        return self.db.track_subagent(
            session_id=session_id,
            agent_type=invocation_obj.agent_type,
            agent_name=invocation_obj.agent_name,
            trigger_phrase=invocation_obj.trigger_phrase,
            task_description=invocation_obj.task_description,
            parent_agent=parent_agent,
            execution_time=None,  # Will be updated when complete
            success=None,  # Will be updated when complete
            error_message=None,
            tokens_used=None,
            cost=None,
            metadata={
                'confidence': invocation_obj.confidence,
                'estimated_complexity': invocation_obj.estimated_complexity,
                'detection_method': self._get_detection_method(invocation_obj),
                'available_agents': list(self.available_agents.keys())
            }
        )

    def _get_detection_method(self, invocation: SubagentInvocation) -> str:
        """Determine how the agent was detected"""
        if invocation.agent_name.replace('-', ' ') in invocation.task_description.lower():
            return 'explicit_mention'
        elif invocation.trigger_phrase != 'implicit':
            return 'trigger_phrase'
        else:
            return 'pattern_matching'

    def update_invocation_result(self, invocation_id: int, success: bool,
                               execution_time: float, error_message: str = None,
                               tokens_used: int = None, cost: float = None):
        """Update subagent invocation with results"""
        # This would update the database record with actual results
        # Implementation depends on database update capabilities
        pass

    def get_agent_usage_analytics(self, start_date: str = None,
                                 end_date: str = None) -> Dict[str, Any]:
        """Get comprehensive agent usage analytics"""

        # Get raw usage statistics
        usage_stats = self.db.get_subagent_usage()

        # Analyze patterns
        patterns = self._analyze_usage_patterns(usage_stats)

        # Generate recommendations
        recommendations = self._generate_recommendations(usage_stats, patterns)

        return {
            'usage_statistics': usage_stats,
            'patterns': patterns,
            'recommendations': recommendations,
            'agent_health': self._assess_agent_health(usage_stats)
        }

    def _analyze_usage_patterns(self, usage_stats: List[Dict]) -> Dict[str, Any]:
        """Analyze subagent usage patterns"""
        if not usage_stats:
            return {'no_data': True}

        total_invocations = sum(stat['invocation_count'] for stat in usage_stats)

        # Most used agents
        most_used = sorted(usage_stats, key=lambda x: x['invocation_count'], reverse=True)[:5]

        # Performance analysis
        fastest_agents = sorted([s for s in usage_stats if s['avg_execution_time']],
                               key=lambda x: x['avg_execution_time'])[:3]

        # Success rate analysis
        most_reliable = sorted([s for s in usage_stats if s['success_rate']],
                              key=lambda x: x['success_rate'], reverse=True)[:3]

        return {
            'total_invocations': total_invocations,
            'unique_agents_used': len(usage_stats),
            'most_used_agents': [agent['agent_name'] for agent in most_used],
            'fastest_agents': [agent['agent_name'] for agent in fastest_agents],
            'most_reliable_agents': [agent['agent_name'] for agent in most_reliable],
            'usage_distribution': {
                agent['agent_name']: round((agent['invocation_count'] / total_invocations) * 100, 2)
                for agent in usage_stats
            }
        }

    def _generate_recommendations(self, usage_stats: List[Dict],
                                 patterns: Dict[str, Any]) -> List[str]:
        """Generate usage optimization recommendations"""
        recommendations = []

        if patterns.get('no_data'):
            recommendations.append("No subagent usage detected. Consider using specialized agents for testing and analysis tasks.")
            return recommendations

        # Underutilized agents
        available_agents = set(self.available_agents.keys())
        used_agents = {stat['agent_name'] for stat in usage_stats}
        unused_agents = available_agents - used_agents

        if unused_agents:
            recommendations.append(f"Consider utilizing unused agents: {', '.join(unused_agents)}")

        # Performance recommendations
        slow_agents = [stat for stat in usage_stats
                      if (stat.get('avg_execution_time') or 0) > 30.0]
        if slow_agents:
            recommendations.append("Some agents have slow execution times. Review task complexity and optimize.")

        # Reliability recommendations
        unreliable_agents = [stat for stat in usage_stats
                           if stat.get('success_rate', 100) < 90.0]
        if unreliable_agents:
            recommendations.append("Some agents have low success rates. Review error patterns and improve robustness.")

        # Usage optimization
        total_invocations = patterns.get('total_invocations', 0)
        if total_invocations < 10:
            recommendations.append("Low subagent utilization. Consider automating more tasks with specialized agents.")

        return recommendations

    def _assess_agent_health(self, usage_stats: List[Dict]) -> Dict[str, str]:
        """Assess health status of each agent type"""
        health = {}

        for agent_name in self.available_agents.keys():
            # Find stats for this agent
            agent_stats = next((s for s in usage_stats if s['agent_name'] == agent_name), None)

            if not agent_stats:
                health[agent_name] = 'unused'
            elif agent_stats.get('success_rate', 0) < 80:
                health[agent_name] = 'poor'
            elif (agent_stats.get('avg_execution_time') or 0) > 60:
                health[agent_name] = 'slow'
            elif agent_stats.get('invocation_count', 0) < 5:
                health[agent_name] = 'underutilized'
            else:
                health[agent_name] = 'healthy'

        return health

    def simulate_agent_recommendations(self, task_description: str) -> Dict[str, Any]:
        """Simulate which agents would be recommended for a task"""
        invocations = self.detect_subagent_invocation(task_description)

        return {
            'task': task_description,
            'recommended_agents': [
                {
                    'agent_name': inv.agent_name,
                    'confidence': inv.confidence,
                    'trigger_phrase': inv.trigger_phrase,
                    'estimated_complexity': inv.estimated_complexity,
                    'expertise': self.available_agents[inv.agent_name]['expertise']
                }
                for inv in invocations
            ],
            'agent_count': len(invocations),
            'complexity_assessment': self._estimate_overall_complexity(task_description, invocations),
            'recommended_workflow': self._suggest_workflow(invocations)
        }

    def _estimate_overall_complexity(self, task: str, invocations: List[SubagentInvocation]) -> str:
        """Estimate overall task complexity based on agent requirements"""
        if not invocations:
            return 'simple'

        complexity_scores = {'low': 1, 'medium': 2, 'high': 3}
        total_complexity = sum(complexity_scores.get(inv.estimated_complexity, 2)
                              for inv in invocations)
        avg_complexity = total_complexity / len(invocations)

        if avg_complexity >= 2.5:
            return 'high'
        elif avg_complexity >= 1.5:
            return 'medium'
        else:
            return 'low'

    def _suggest_workflow(self, invocations: List[SubagentInvocation]) -> List[str]:
        """Suggest optimal workflow for multiple agents"""
        if len(invocations) <= 1:
            return [inv.agent_name for inv in invocations]

        # Define logical ordering for common agent combinations
        workflow_priorities = {
            'database-testing-specialist': 1,    # Database setup first
            'api-testing-specialist': 2,         # API testing after DB
            'security-testing-guardian': 3,      # Security after functionality
            'performance-testing-expert': 4,     # Performance testing last
            'general-purpose': 0                 # Research/setup tasks first
        }

        sorted_agents = sorted(invocations,
                             key=lambda x: workflow_priorities.get(x.agent_name, 2))

        return [inv.agent_name for inv in sorted_agents]