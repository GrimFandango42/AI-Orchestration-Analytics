"""
Unified database management for AI Orchestration Analytics
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading

class OrchestrationDB:
    """Database manager for orchestration analytics"""

    def __init__(self, db_path: str = "data/orchestration.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.init_database()

    @property
    def conn(self):
        """Thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def init_database(self):
        """Initialize database schema"""
        with self.conn:
            # Orchestration sessions table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS orchestration_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    project_name TEXT,
                    task_description TEXT,
                    total_tasks INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    total_savings REAL DEFAULT 0,
                    metadata TEXT
                )
            """)

            # Handoff events table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS handoff_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    task_type TEXT,
                    task_description TEXT,
                    source_model TEXT,
                    target_model TEXT,
                    handoff_reason TEXT,
                    confidence_score REAL,
                    tokens_used INTEGER,
                    cost REAL,
                    savings REAL,
                    success BOOLEAN,
                    response_time REAL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES orchestration_sessions(session_id)
                )
            """)

            # Subagent invocations table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS subagent_invocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    agent_type TEXT,
                    agent_name TEXT,
                    trigger_phrase TEXT,
                    task_description TEXT,
                    parent_agent TEXT,
                    execution_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    tokens_used INTEGER,
                    cost REAL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES orchestration_sessions(session_id)
                )
            """)

            # Task outcomes table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS task_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    task_id TEXT,
                    task_type TEXT,
                    task_description TEXT,
                    model_used TEXT,
                    success BOOLEAN,
                    error_type TEXT,
                    error_message TEXT,
                    execution_time REAL,
                    tokens_used INTEGER,
                    cost REAL,
                    quality_score REAL,
                    user_feedback TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES orchestration_sessions(session_id)
                )
            """)

            # Cost metrics table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    period_type TEXT,  -- 'hourly', 'daily', 'weekly', 'monthly'
                    period_start TIMESTAMP,
                    period_end TIMESTAMP,
                    total_cost REAL,
                    claude_cost REAL,
                    deepseek_cost REAL,
                    other_cost REAL,
                    total_savings REAL,
                    total_tokens INTEGER,
                    claude_tokens INTEGER,
                    deepseek_tokens INTEGER,
                    total_tasks INTEGER,
                    successful_tasks INTEGER,
                    failed_tasks INTEGER,
                    routing_accuracy REAL,
                    metadata TEXT
                )
            """)

            # Claude account tier analysis table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS claude_account_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    period_type TEXT,  -- 'daily', 'weekly', 'monthly'
                    period_start TIMESTAMP,
                    period_end TIMESTAMP,
                    current_tier TEXT,  -- 'max', 'pro', 'free'
                    claude_tokens_used INTEGER,
                    deepseek_tokens_used INTEGER,
                    total_interactions INTEGER,
                    claude_cost_actual REAL,
                    claude_cost_if_pro REAL,
                    deepseek_cost_actual REAL,
                    combined_effectiveness_score REAL,
                    max_tier_equivalent_score REAL,
                    recommended_tier TEXT,
                    projected_savings REAL,
                    transition_confidence REAL,
                    metadata TEXT
                )
            """)

            # Pattern analysis table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pattern_type TEXT,  -- 'success', 'failure', 'routing', 'subagent'
                    pattern_name TEXT,
                    description TEXT,
                    frequency INTEGER,
                    confidence REAL,
                    impact_score REAL,
                    recommendations TEXT,
                    metadata TEXT
                )
            """)

            # Create indexes for performance
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_time ON orchestration_sessions(start_time)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_session ON handoff_events(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_time ON handoff_events(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subagents_session ON subagent_invocations(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subagents_type ON subagent_invocations(agent_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_session ON task_outcomes(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_period ON cost_metrics(period_type, period_start)")

    # Session Management
    def create_session(self, session_id: str, project_name: str = None,
                      task_description: str = None, metadata: Dict = None) -> int:
        """Create new orchestration session"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO orchestration_sessions
                (session_id, project_name, task_description, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, project_name, task_description,
                  json.dumps(metadata) if metadata else None))
            return cursor.lastrowid

    def update_session(self, session_id: str, **kwargs):
        """Update session information"""
        allowed_fields = ['end_time', 'total_tasks', 'completed_tasks',
                         'failed_tasks', 'total_cost', 'total_savings']

        updates = []
        values = []
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if updates:
            values.append(session_id)
            with self.conn:
                self.conn.execute(f"""
                    UPDATE orchestration_sessions
                    SET {', '.join(updates)}
                    WHERE session_id = ?
                """, values)

    # Handoff Tracking
    def track_handoff(self, session_id: str, task_type: str, task_description: str,
                     source_model: str, target_model: str, handoff_reason: str,
                     confidence_score: float = None, tokens_used: int = None,
                     cost: float = None, savings: float = None, success: bool = True,
                     response_time: float = None, metadata: Dict = None) -> int:
        """Track a model handoff event"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO handoff_events
                (session_id, task_type, task_description, source_model, target_model,
                 handoff_reason, confidence_score, tokens_used, cost, savings,
                 success, response_time, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, task_type, task_description, source_model, target_model,
                  handoff_reason, confidence_score, tokens_used, cost, savings,
                  success, response_time, json.dumps(metadata) if metadata else None))
            return cursor.lastrowid

    # Subagent Tracking
    def track_subagent(self, session_id: str, agent_type: str, agent_name: str,
                      trigger_phrase: str = None, task_description: str = None,
                      parent_agent: str = None, execution_time: float = None,
                      success: bool = True, error_message: str = None,
                      tokens_used: int = None, cost: float = None,
                      metadata: Dict = None) -> int:
        """Track a subagent invocation"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO subagent_invocations
                (session_id, agent_type, agent_name, trigger_phrase, task_description,
                 parent_agent, execution_time, success, error_message,
                 tokens_used, cost, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, agent_type, agent_name, trigger_phrase, task_description,
                  parent_agent, execution_time, success, error_message,
                  tokens_used, cost, json.dumps(metadata) if metadata else None))
            return cursor.lastrowid

    # Task Outcome Tracking
    def track_outcome(self, session_id: str, task_id: str, task_type: str,
                     task_description: str, model_used: str, success: bool,
                     error_type: str = None, error_message: str = None,
                     execution_time: float = None, tokens_used: int = None,
                     cost: float = None, quality_score: float = None,
                     user_feedback: str = None, metadata: Dict = None) -> int:
        """Track task outcome"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO task_outcomes
                (session_id, task_id, task_type, task_description, model_used,
                 success, error_type, error_message, execution_time,
                 tokens_used, cost, quality_score, user_feedback, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, task_id, task_type, task_description, model_used,
                  success, error_type, error_message, execution_time,
                  tokens_used, cost, quality_score, user_feedback,
                  json.dumps(metadata) if metadata else None))
            return cursor.lastrowid

    # Analytics Queries
    def get_session_summary(self, session_id: str = None, limit: int = 100) -> List[Dict]:
        """Get session summaries"""
        if session_id:
            cursor = self.conn.execute("""
                SELECT * FROM orchestration_sessions
                WHERE session_id = ?
            """, (session_id,))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM orchestration_sessions
                ORDER BY start_time DESC LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_handoff_analytics(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get handoff analytics"""
        query = """
            SELECT
                COUNT(*) as total_handoffs,
                SUM(CASE WHEN target_model = 'deepseek' THEN 1 ELSE 0 END) as deepseek_handoffs,
                SUM(CASE WHEN target_model = 'claude' THEN 1 ELSE 0 END) as claude_handoffs,
                AVG(confidence_score) as avg_confidence,
                SUM(cost) as total_cost,
                SUM(savings) as total_savings,
                AVG(response_time) as avg_response_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM handoff_events
        """

        params = []
        if start_date and end_date:
            query += " WHERE timestamp BETWEEN ? AND ?"
            params = [start_date, end_date]

        cursor = self.conn.execute(query, params)
        return dict(cursor.fetchone())

    def get_subagent_usage(self, limit: int = 20) -> List[Dict]:
        """Get subagent usage statistics"""
        cursor = self.conn.execute("""
            SELECT
                agent_type,
                agent_name,
                COUNT(*) as invocation_count,
                AVG(execution_time) as avg_execution_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost
            FROM subagent_invocations
            GROUP BY agent_type, agent_name
            ORDER BY invocation_count DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_pattern_analysis(self, pattern_type: str = None) -> List[Dict]:
        """Get pattern analysis results"""
        if pattern_type:
            cursor = self.conn.execute("""
                SELECT * FROM pattern_analysis
                WHERE pattern_type = ?
                ORDER BY timestamp DESC
            """, (pattern_type,))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM pattern_analysis
                ORDER BY timestamp DESC
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_cost_metrics(self, period_type: str = 'daily', limit: int = 30) -> List[Dict]:
        """Get cost metrics for specified period"""
        cursor = self.conn.execute("""
            SELECT * FROM cost_metrics
            WHERE period_type = ?
            ORDER BY period_start DESC
            LIMIT ?
        """, (period_type, limit))

        return [dict(row) for row in cursor.fetchall()]

    def track_claude_usage(self, period_type: str, period_start, period_end,
                          current_tier: str = 'max', claude_tokens: int = 0,
                          deepseek_tokens: int = 0, total_interactions: int = 0,
                          effectiveness_score: float = 1.0, metadata: dict = None):
        """Track Claude Code usage for account tier analysis"""

        # Claude pricing (approximations based on API rates)
        CLAUDE_MAX_MONTHLY = 200.0  # ~$200/month for Max account
        CLAUDE_PRO_MONTHLY = 20.0   # $20/month for Pro account
        CLAUDE_TOKEN_COST = 0.015   # ~$0.015 per 1k tokens

        # Calculate costs
        claude_cost_actual = (claude_tokens / 1000) * CLAUDE_TOKEN_COST if current_tier != 'max' else CLAUDE_MAX_MONTHLY / 30
        claude_cost_if_pro = min((claude_tokens / 1000) * CLAUDE_TOKEN_COST, CLAUDE_PRO_MONTHLY / 30)
        deepseek_cost_actual = 0  # Local DeepSeek is free

        # Calculate effectiveness scores
        combined_effectiveness = effectiveness_score
        max_tier_equivalent = effectiveness_score * 1.0  # Max tier baseline

        # Determine recommendations
        if combined_effectiveness >= 0.9 and claude_cost_if_pro < claude_cost_actual:
            recommended_tier = 'pro'
            projected_savings = claude_cost_actual - claude_cost_if_pro
            transition_confidence = min(combined_effectiveness, 0.95)
        else:
            recommended_tier = current_tier
            projected_savings = 0
            transition_confidence = effectiveness_score

        self.conn.execute("""
            INSERT INTO claude_account_analysis (
                period_type, period_start, period_end, current_tier,
                claude_tokens_used, deepseek_tokens_used, total_interactions,
                claude_cost_actual, claude_cost_if_pro, deepseek_cost_actual,
                combined_effectiveness_score, max_tier_equivalent_score,
                recommended_tier, projected_savings, transition_confidence, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (period_type, period_start, period_end, current_tier,
              claude_tokens, deepseek_tokens, total_interactions,
              claude_cost_actual, claude_cost_if_pro, deepseek_cost_actual,
              combined_effectiveness, max_tier_equivalent,
              recommended_tier, projected_savings, transition_confidence,
              json.dumps(metadata) if metadata else None))

        self.conn.commit()

    def get_claude_account_analysis(self, period_type: str = 'daily', limit: int = 30) -> List[Dict]:
        """Get Claude account tier analysis data"""
        cursor = self.conn.execute("""
            SELECT * FROM claude_account_analysis
            WHERE period_type = ?
            ORDER BY period_start DESC
            LIMIT ?
        """, (period_type, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_account_transition_projection(self) -> Dict:
        """Generate Max-to-Pro account transition projection"""

        # Get recent usage data
        recent_handoffs = self.conn.execute("""
            SELECT
                COUNT(*) as total_handoffs,
                SUM(CASE WHEN target_model = 'deepseek' THEN 1 ELSE 0 END) as deepseek_handoffs,
                SUM(tokens_used) as total_tokens,
                AVG(confidence_score) as avg_confidence,
                SUM(savings) as total_savings
            FROM handoff_events
            WHERE timestamp >= datetime('now', '-30 days')
        """).fetchone()

        recent_sessions = self.conn.execute("""
            SELECT COUNT(*) as total_sessions
            FROM orchestration_sessions
            WHERE start_time >= datetime('now', '-30 days')
        """).fetchone()

        # Calculate metrics
        total_handoffs = recent_handoffs['total_handoffs'] or 0
        deepseek_handoffs = recent_handoffs['deepseek_handoffs'] or 0
        deepseek_ratio = deepseek_handoffs / total_handoffs if total_handoffs > 0 else 0
        avg_confidence = recent_handoffs['avg_confidence'] or 0
        monthly_savings = (recent_handoffs['total_savings'] or 0) * 1.0
        total_sessions = recent_sessions['total_sessions'] or 0

        # Transition analysis
        effectiveness_score = min(deepseek_ratio * 1.2 + avg_confidence * 0.5, 1.0)

        # Cost projections
        current_max_cost = 200.0  # $200/month Max account
        pro_monthly_cost = 20.0   # $20/month Pro account
        estimated_overage = max(0, (total_handoffs - 1000) * 0.01)  # Rough Pro overage estimate
        projected_pro_cost = pro_monthly_cost + estimated_overage

        potential_savings = current_max_cost - projected_pro_cost

        # Transition readiness
        if effectiveness_score >= 0.85 and deepseek_ratio >= 0.7:
            readiness = 'ready'
            confidence = min(effectiveness_score, 0.95)
        elif effectiveness_score >= 0.7 and deepseek_ratio >= 0.5:
            readiness = 'approaching'
            confidence = effectiveness_score * 0.8
        else:
            readiness = 'not_ready'
            confidence = effectiveness_score * 0.6

        return {
            'transition_readiness': readiness,
            'confidence_score': confidence,
            'effectiveness_score': effectiveness_score,
            'deepseek_utilization_ratio': deepseek_ratio,
            'current_monthly_cost': current_max_cost,
            'projected_pro_cost': projected_pro_cost,
            'potential_monthly_savings': potential_savings,
            'total_sessions_30d': total_sessions,
            'total_handoffs_30d': total_handoffs,
            'deepseek_handoffs_30d': deepseek_handoffs,
            'avg_routing_confidence': avg_confidence,
            'estimated_break_even_days': max(1, int(30 * (1 - effectiveness_score))) if effectiveness_score < 1 else 1,
            'recommendation': self._get_tier_recommendation(readiness, effectiveness_score, potential_savings)
        }

    def _get_tier_recommendation(self, readiness: str, effectiveness: float, savings: float) -> str:
        """Get tier recommendation with reasoning"""
        if readiness == 'ready' and savings > 100:
            return f"RECOMMEND: Switch to Pro (${savings:.0f}/month savings, {effectiveness:.1%} effectiveness maintained)"
        elif readiness == 'approaching':
            return f"MONITOR: Continue optimizing DeepSeek routing ({effectiveness:.1%} current effectiveness)"
        else:
            return "MAINTAIN: Stay on Max account until DeepSeek effectiveness improves"

    def get_recent_activity(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get recent orchestration activity with pagination

        Args:
            limit: Number of records to return (default 50)
            offset: Number of records to skip (default 0)

        Returns:
            Dict with activities list, total_count, and pagination info
        """
        # Get total count for pagination
        total_count_cursor = self.conn.execute("""
            SELECT COUNT(*) as total FROM (
                SELECT start_time as timestamp, 'session' as event_type, session_id, project_name as description,
                       0 as cost, 'claude' as model_or_agent, 'success' as status
                FROM orchestration_sessions
                UNION ALL
                SELECT timestamp, 'handoff' as event_type, session_id,
                       task_description as description, cost, target_model as model_or_agent,
                       CASE WHEN success = 1 THEN 'success' ELSE 'failed' END as status
                FROM handoff_events
                UNION ALL
                SELECT timestamp, 'subagent' as event_type, session_id,
                       task_description as description, cost, agent_name as model_or_agent,
                       CASE WHEN success = 1 THEN 'success' ELSE 'failed' END as status
                FROM subagent_invocations
            )
        """)
        total_count = total_count_cursor.fetchone()[0]

        # Get paginated activities
        cursor = self.conn.execute("""
            SELECT timestamp, event_type, session_id, description, cost, model_or_agent, status
            FROM (
                SELECT start_time as timestamp, 'session' as event_type, session_id,
                       project_name as description, 0 as cost, 'claude' as model_or_agent,
                       'success' as status
                FROM orchestration_sessions
                UNION ALL
                SELECT timestamp, 'handoff' as event_type, session_id,
                       task_description as description, cost, target_model as model_or_agent,
                       CASE WHEN success = 1 THEN 'success' ELSE 'failed' END as status
                FROM handoff_events
                UNION ALL
                SELECT timestamp, 'subagent' as event_type, session_id,
                       task_description as description, cost, agent_name as model_or_agent,
                       CASE WHEN success = 1 THEN 'success' ELSE 'failed' END as status
                FROM subagent_invocations
            )
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        activities = []
        for row in cursor.fetchall():
            activity = dict(row)
            # Ensure proper data types
            activity['cost'] = float(activity['cost']) if activity['cost'] else 0.0
            activities.append(activity)

        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        current_page = (offset // limit) + 1
        has_next = offset + limit < total_count
        has_previous = offset > 0

        return {
            'activities': activities,
            'pagination': {
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': current_page,
                'page_size': limit,
                'has_next': has_next,
                'has_previous': has_previous,
                'next_offset': offset + limit if has_next else None,
                'previous_offset': max(0, offset - limit) if has_previous else None
            }
        }

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')