"""
Message Analyzer for Claude Code Orchestration
==============================================
Analyzes user messages to detect:
- Handoff opportunities (Claude vs DeepSeek routing)
- Subagent invocation triggers
- Task complexity and type classification
- Real-time routing decisions
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from src.tracking.handoff_monitor import HandoffMonitor, HandoffDecision
from src.tracking.subagent_tracker import SubagentTracker, SubagentInvocation

logger = logging.getLogger(__name__)

@dataclass
class MessageAnalysis:
    """Result of message analysis"""
    message: str
    timestamp: datetime
    handoff_decision: Optional[HandoffDecision]
    subagent_triggers: List[SubagentInvocation]
    task_classification: Dict[str, Any]
    urgency_level: str  # 'low', 'medium', 'high'
    complexity_score: float  # 0.0 to 1.0
    metadata: Dict[str, Any]

class MessageAnalyzer:
    """Analyzes user messages for orchestration decisions"""

    def __init__(self, handoff_monitor: HandoffMonitor = None,
                 subagent_tracker: SubagentTracker = None):
        self.handoff_monitor = handoff_monitor or HandoffMonitor()
        self.subagent_tracker = subagent_tracker or SubagentTracker()

        # Message patterns for classification
        self.urgency_patterns = {
            'high': [
                r'\b(urgent|asap|immediately|now|quick|fast|emergency)\b',
                r'\b(fix|bug|error|broken|failing|crash)\b',
                r'\b(deadline|due|today|tonight)\b'
            ],
            'medium': [
                r'\b(soon|when you can|sometime|eventually)\b',
                r'\b(improve|optimize|enhance|update)\b',
                r'\b(review|check|validate|test)\b'
            ],
            'low': [
                r'\b(later|future|someday|maybe|consider)\b',
                r'\b(research|explore|investigate|learn)\b',
                r'\b(documentation|comment|readme)\b'
            ]
        }

        # Task type patterns
        self.task_type_patterns = {
            'implementation': [
                r'\b(implement|create|build|write|code|develop)\b',
                r'\b(add feature|new function|create class)\b',
                r'\b(generate|produce|make)\b'
            ],
            'debugging': [
                r'\b(debug|fix|resolve|solve|troubleshoot)\b',
                r'\b(error|bug|issue|problem|exception)\b',
                r'\b(not working|failing|broken)\b'
            ],
            'analysis': [
                r'\b(analyze|examine|investigate|study|research)\b',
                r'\b(understand|explain|clarify|describe)\b',
                r'\b(why|how|what|when|where)\b'
            ],
            'refactoring': [
                r'\b(refactor|restructure|reorganize|cleanup)\b',
                r'\b(improve|optimize|enhance|simplify)\b',
                r'\b(rewrite|redesign|rework)\b'
            ],
            'testing': [
                r'\b(test|validate|verify|check)\b',
                r'\b(unit test|integration test|e2e test)\b',
                r'\b(coverage|assertion|mock)\b'
            ],
            'documentation': [
                r'\b(document|comment|readme|wiki|guide)\b',
                r'\b(explain|describe|tutorial|example)\b',
                r'\b(documentation|docs|manual)\b'
            ]
        }

        # Complexity indicators
        self.complexity_indicators = {
            'high': [
                r'\b(architecture|design pattern|system)\b',
                r'\b(multiple|complex|advanced|enterprise)\b',
                r'\b(integration|api|database|performance)\b',
                r'\b(scalability|security|optimization)\b'
            ],
            'medium': [
                r'\b(function|method|class|module)\b',
                r'\b(feature|component|service)\b',
                r'\b(configuration|setup|install)\b'
            ],
            'low': [
                r'\b(simple|basic|quick|small|minor)\b',
                r'\b(fix|update|change|modify)\b',
                r'\b(comment|variable|constant)\b'
            ]
        }

        # Programming language detection
        self.language_patterns = {
            'python': r'\b(python|\.py|pip|venv|flask|django|fastapi|pandas|numpy)\b',
            'javascript': r'\b(javascript|js|node|npm|react|vue|angular|express)\b',
            'typescript': r'\b(typescript|ts|tsx|interface|type)\b',
            'java': r'\b(java|\.java|maven|gradle|spring|junit)\b',
            'c++': r'\b(c\+\+|cpp|\.cpp|\.h|cmake|make)\b',
            'go': r'\b(go|golang|\.go|goroutine|channel)\b',
            'rust': r'\b(rust|cargo|\.rs|crate)\b'
        }

    async def analyze_message(self, message: str, context: Dict[str, Any] = None) -> MessageAnalysis:
        """Perform comprehensive analysis of user message"""
        timestamp = datetime.now(timezone.utc)

        # Clean and normalize message
        normalized_message = self._normalize_message(message)

        # Task classification
        task_classification = self._classify_task(normalized_message)

        # Urgency detection
        urgency_level = self._detect_urgency(normalized_message)

        # Complexity scoring
        complexity_score = self._calculate_complexity_score(normalized_message, task_classification)

        # Handoff decision analysis
        handoff_decision = None
        try:
            handoff_decision = self.handoff_monitor.analyze_task(
                task_description=message,
                task_type=task_classification.get('primary_type', 'general'),
                session_context=context
            )
        except Exception as e:
            logger.error(f"Error in handoff analysis: {e}")

        # Subagent trigger detection
        subagent_triggers = []
        try:
            subagent_triggers = self.subagent_tracker.detect_subagent_invocation(
                user_input=message,
                context=context
            )
        except Exception as e:
            logger.error(f"Error in subagent detection: {e}")

        # Additional metadata
        metadata = {
            'message_length': len(message),
            'word_count': len(message.split()),
            'detected_languages': self._detect_programming_languages(normalized_message),
            'contains_code': self._contains_code_snippets(message),
            'question_type': self._classify_question_type(normalized_message),
            'technical_terms': self._extract_technical_terms(normalized_message)
        }

        return MessageAnalysis(
            message=message,
            timestamp=timestamp,
            handoff_decision=handoff_decision,
            subagent_triggers=subagent_triggers,
            task_classification=task_classification,
            urgency_level=urgency_level,
            complexity_score=complexity_score,
            metadata=metadata
        )

    def _normalize_message(self, message: str) -> str:
        """Normalize message for analysis"""
        # Convert to lowercase
        normalized = message.lower()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        # Remove special characters but keep important punctuation
        normalized = re.sub(r'[^\w\s\.\?\!\-\(\)]', '', normalized)

        return normalized.strip()

    def _classify_task(self, message: str) -> Dict[str, Any]:
        """Classify the task type from message"""
        task_scores = {}

        for task_type, patterns in self.task_type_patterns.items():
            score = 0
            matches = []

            for pattern in patterns:
                found_matches = re.findall(pattern, message, re.IGNORECASE)
                if found_matches:
                    score += len(found_matches)
                    matches.extend(found_matches)

            if score > 0:
                task_scores[task_type] = {
                    'score': score,
                    'matches': matches
                }

        # Determine primary task type
        primary_type = 'general'
        if task_scores:
            primary_type = max(task_scores.keys(), key=lambda k: task_scores[k]['score'])

        return {
            'primary_type': primary_type,
            'all_scores': task_scores,
            'confidence': task_scores.get(primary_type, {}).get('score', 0) / 10.0
        }

    def _detect_urgency(self, message: str) -> str:
        """Detect urgency level from message"""
        urgency_scores = {'high': 0, 'medium': 0, 'low': 0}

        for level, patterns in self.urgency_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                urgency_scores[level] += len(matches)

        # Determine urgency
        if urgency_scores['high'] > 0:
            return 'high'
        elif urgency_scores['medium'] > 0:
            return 'medium'
        elif urgency_scores['low'] > 0:
            return 'low'
        else:
            return 'medium'  # Default

    def _calculate_complexity_score(self, message: str, task_classification: Dict) -> float:
        """Calculate complexity score (0.0 to 1.0)"""
        base_score = 0.5  # Start at medium complexity

        # Adjust based on complexity indicators
        for level, patterns in self.complexity_indicators.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, message, re.IGNORECASE))
                if level == 'high':
                    base_score += matches * 0.1
                elif level == 'low':
                    base_score -= matches * 0.1

        # Adjust based on task type
        task_complexity_modifiers = {
            'implementation': 0.1,
            'debugging': 0.05,
            'refactoring': 0.15,
            'analysis': -0.05,
            'testing': 0.0,
            'documentation': -0.1
        }

        primary_type = task_classification.get('primary_type', 'general')
        modifier = task_complexity_modifiers.get(primary_type, 0)
        base_score += modifier

        # Adjust based on message length (longer often means more complex)
        word_count = len(message.split())
        if word_count > 100:
            base_score += 0.1
        elif word_count < 20:
            base_score -= 0.1

        # Clamp to 0.0-1.0 range
        return max(0.0, min(1.0, base_score))

    def _detect_programming_languages(self, message: str) -> List[str]:
        """Detect mentioned programming languages"""
        detected = []

        for language, pattern in self.language_patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                detected.append(language)

        return detected

    def _contains_code_snippets(self, message: str) -> bool:
        """Detect if message contains code snippets"""
        code_indicators = [
            r'```',  # Markdown code blocks
            r'`[^`]+`',  # Inline code
            r'\b(def|function|class|if|for|while|return)\s*\(',  # Code keywords
            r'[{}\[\]();]',  # Common code punctuation
            r'\/\/|\/\*|\*\/|#',  # Comments
        ]

        for pattern in code_indicators:
            if re.search(pattern, message):
                return True

        return False

    def _classify_question_type(self, message: str) -> str:
        """Classify type of question being asked"""
        question_patterns = {
            'how': r'\bhow\b',
            'what': r'\bwhat\b',
            'why': r'\bwhy\b',
            'when': r'\bwhen\b',
            'where': r'\bwhere\b',
            'which': r'\bwhich\b',
            'can': r'\bcan\s+(you|i|we)\b'
        }

        for q_type, pattern in question_patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                return q_type

        # Check if it's a statement/command
        if message.endswith('?'):
            return 'question'
        elif any(word in message for word in ['please', 'could', 'would', 'can']):
            return 'request'
        else:
            return 'statement'

    def _extract_technical_terms(self, message: str) -> List[str]:
        """Extract technical terms from message"""
        # Common technical terms in software development
        technical_terms = {
            'api', 'rest', 'graphql', 'json', 'xml', 'database', 'sql',
            'frontend', 'backend', 'fullstack', 'framework', 'library',
            'algorithm', 'data structure', 'design pattern', 'mvc',
            'authentication', 'authorization', 'security', 'encryption',
            'deployment', 'ci/cd', 'docker', 'kubernetes', 'cloud',
            'git', 'version control', 'branch', 'merge', 'commit',
            'testing', 'unit test', 'integration', 'tdd', 'bdd',
            'agile', 'scrum', 'sprint', 'kanban'
        }

        found_terms = []
        words = re.findall(r'\b\w+\b', message.lower())

        for word in words:
            if word in technical_terms:
                found_terms.append(word)

        return list(set(found_terms))  # Remove duplicates

    def get_analysis_summary(self, analyses: List[MessageAnalysis]) -> Dict[str, Any]:
        """Get summary statistics from multiple message analyses"""
        if not analyses:
            return {'total_messages': 0}

        total = len(analyses)

        # Urgency distribution
        urgency_counts = {'high': 0, 'medium': 0, 'low': 0}
        for analysis in analyses:
            urgency_counts[analysis.urgency_level] += 1

        # Task type distribution
        task_types = {}
        for analysis in analyses:
            task_type = analysis.task_classification.get('primary_type', 'general')
            task_types[task_type] = task_types.get(task_type, 0) + 1

        # Average complexity
        avg_complexity = sum(a.complexity_score for a in analyses) / total

        # Handoff recommendations
        handoff_stats = {'deepseek': 0, 'claude': 0, 'unknown': 0}
        for analysis in analyses:
            if analysis.handoff_decision:
                if analysis.handoff_decision.should_route_to_deepseek:
                    handoff_stats['deepseek'] += 1
                else:
                    handoff_stats['claude'] += 1
            else:
                handoff_stats['unknown'] += 1

        # Subagent trigger frequency
        subagent_triggers = {}
        for analysis in analyses:
            for trigger in analysis.subagent_triggers:
                agent = trigger.agent_name
                subagent_triggers[agent] = subagent_triggers.get(agent, 0) + 1

        return {
            'total_messages': total,
            'urgency_distribution': urgency_counts,
            'task_type_distribution': task_types,
            'average_complexity': avg_complexity,
            'handoff_recommendations': handoff_stats,
            'subagent_trigger_frequency': subagent_triggers,
            'technical_coverage': {
                'messages_with_code': len([a for a in analyses if a.metadata.get('contains_code')]),
                'programming_languages': self._aggregate_detected_languages(analyses),
                'avg_message_length': sum(a.metadata.get('message_length', 0) for a in analyses) / total
            }
        }

    def _aggregate_detected_languages(self, analyses: List[MessageAnalysis]) -> Dict[str, int]:
        """Aggregate detected programming languages across analyses"""
        language_counts = {}

        for analysis in analyses:
            languages = analysis.metadata.get('detected_languages', [])
            for lang in languages:
                language_counts[lang] = language_counts.get(lang, 0) + 1

        return language_counts