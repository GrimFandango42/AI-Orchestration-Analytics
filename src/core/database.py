"""
Unified database management for AI Orchestration Analytics
"""

import sqlite3
import json
import os
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

        # Initialize project attribution and MCP detection systems
        self._project_attributor = None
        self._mcp_detector = None

        self.init_database()
        self._upgrade_schema_for_token_attribution()
        self._init_attribution_systems()

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

            # Create comprehensive indexes for performance optimization
            # Session-related indexes (for fast dashboard loading)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_time_desc ON orchestration_sessions(start_time DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project_time ON orchestration_sessions(project_name, start_time DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_time ON orchestration_sessions(start_time)")

            # Handoff events indexes (for analytics queries)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_timestamp_desc ON handoff_events(timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_session ON handoff_events(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_time ON handoff_events(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_target_model ON handoff_events(target_model, timestamp DESC)")

            # Subagent invocations indexes (for usage analytics)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subagents_timestamp_desc ON subagent_invocations(timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subagents_session ON subagent_invocations(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subagents_type ON subagent_invocations(agent_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_subagents_name_time ON subagent_invocations(agent_name, timestamp DESC)")

            # Task outcomes indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_session ON task_outcomes(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp ON task_outcomes(timestamp DESC)")

            # Cost metrics indexes (for financial analytics)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_period_start ON cost_metrics(period_start DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_period_type ON cost_metrics(period_type, period_start DESC)")

            # Pattern analysis indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_timestamp ON pattern_analysis(timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type_time ON pattern_analysis(pattern_type, timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_period ON cost_metrics(period_type, period_start)")

    def _init_attribution_systems(self):
        """Initialize project attribution and MCP detection systems"""
        try:
            # Import here to avoid circular imports
            from ..tracking.project_attribution import ProjectAttributor
            from ..tracking.mcp_tool_detector import MCPToolDetector

            self._project_attributor = ProjectAttributor()
            self._mcp_detector = MCPToolDetector()
        except ImportError as e:
            # Log the error but continue without attribution systems
            print(f"Warning: Could not initialize attribution systems: {e}")
            self._project_attributor = None
            self._mcp_detector = None

    # Session Management
    def create_session(self, session_id: str, project_name: str = None,
                      task_description: str = None, metadata: Dict = None,
                      working_directory: str = None, file_paths: List[str] = None) -> int:
        """Create new orchestration session with intelligent project attribution"""

        # Use intelligent project attribution if no project name provided
        if not project_name and self._project_attributor:
            try:
                # Use current working directory if not provided
                if not working_directory:
                    working_directory = os.getcwd()

                # Detect project from context
                detected_project, confidence = self._project_attributor.detect_project_from_context(
                    working_directory=working_directory,
                    file_paths=file_paths,
                    task_description=task_description,
                    metadata=metadata
                )

                # Use detected project if confidence is high enough
                if confidence > 0.5:
                    project_name = detected_project

                    # Add attribution info to metadata
                    if not metadata:
                        metadata = {}
                    metadata.update({
                        'attribution': {
                            'detected_project': detected_project,
                            'confidence': confidence,
                            'working_directory': working_directory,
                            'detection_method': 'intelligent_attribution'
                        }
                    })

            except Exception as e:
                # Log error but continue with fallback
                print(f"Warning: Project attribution failed: {e}")
                if not project_name:
                    project_name = 'other'

        # Fallback if no project detected
        if not project_name:
            project_name = 'other'

        # Check for MCP tool invocations
        if self._mcp_detector and task_description:
            try:
                mcp_invocation = self._mcp_detector.detect_mcp_invocation(
                    task_description=task_description,
                    metadata=metadata,
                    file_paths=file_paths
                )

                if mcp_invocation:
                    # Track MCP tool invocation as subagent activity
                    self.track_mcp_tool_invocation(
                        session_id=session_id,
                        tool_name=mcp_invocation.tool_name,
                        server_name=mcp_invocation.server_name,
                        tool_category=mcp_invocation.tool_type,
                        task_description=mcp_invocation.invocation_context,
                        estimated_tokens=mcp_invocation.estimated_tokens,
                        project_context=mcp_invocation.project_context
                    )

                    # Add MCP info to metadata
                    if not metadata:
                        metadata = {}
                    metadata.update({
                        'mcp_tool': {
                            'tool_name': mcp_invocation.tool_name,
                            'server_name': mcp_invocation.server_name,
                            'confidence': mcp_invocation.confidence,
                            'estimated_tokens': mcp_invocation.estimated_tokens
                        }
                    })

            except Exception as e:
                print(f"Warning: MCP tool detection failed: {e}")

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

    def get_project_grouped_activity(self, limit: int = 10, offset: int = 0) -> Dict:
        """Get activity grouped by project with expandable details

        Args:
            limit: Number of projects to return (default 10)
            offset: Number of projects to skip (default 0)

        Returns:
            Dict with project groups, each containing session info and sub-activities
        """
        # Get projects with session counts, date ranges, and statistics
        projects_cursor = self.conn.execute("""
            SELECT
                project_name,
                COUNT(*) as session_count,
                MIN(start_time) as earliest_session,
                MAX(start_time) as latest_session,
                COUNT(DISTINCT DATE(start_time)) as active_days,
                SUM(completed_tasks) as total_completed_tasks,
                SUM(failed_tasks) as total_failed_tasks
            FROM orchestration_sessions
            GROUP BY project_name
            ORDER BY latest_session DESC, session_count DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        projects = []
        for project_row in projects_cursor.fetchall():
            project_data = dict(project_row)
            project_name = project_data['project_name']

            # Get recent handoffs for this project
            handoffs_cursor = self.conn.execute("""
                SELECT
                    h.timestamp, h.session_id, h.task_description, h.target_model,
                    h.cost, h.confidence_score,
                    CASE WHEN h.success = 1 THEN 'success' ELSE 'failed' END as status
                FROM handoff_events h
                JOIN orchestration_sessions s ON h.session_id = s.session_id
                WHERE s.project_name = ?
                ORDER BY h.timestamp DESC
                LIMIT 20
            """, (project_name,))

            handoffs = [dict(row) for row in handoffs_cursor.fetchall()]

            # Get recent subagent invocations for this project
            subagents_cursor = self.conn.execute("""
                SELECT
                    sa.timestamp, sa.session_id, sa.agent_name, sa.task_description,
                    sa.cost, sa.execution_time,
                    CASE WHEN sa.success = 1 THEN 'success' ELSE 'failed' END as status
                FROM subagent_invocations sa
                JOIN orchestration_sessions s ON sa.session_id = s.session_id
                WHERE s.project_name = ?
                ORDER BY sa.timestamp DESC
                LIMIT 20
            """, (project_name,))

            subagents = [dict(row) for row in subagents_cursor.fetchall()]

            # Calculate project-level statistics
            total_cost = 0.0
            for handoff in handoffs:
                cost = handoff.get('cost', 0)
                if cost is not None:
                    total_cost += float(cost)
            for subagent in subagents:
                cost = subagent.get('cost', 0)
                if cost is not None:
                    total_cost += float(cost)

            success_rate = 0.0
            total_tasks = project_data['total_completed_tasks'] + project_data['total_failed_tasks']
            if total_tasks > 0:
                success_rate = (project_data['total_completed_tasks'] / total_tasks) * 100

            project_data.update({
                'handoffs': handoffs,
                'subagents': subagents,
                'total_handoffs': len(handoffs),
                'total_subagents': len(subagents),
                'total_cost': round(total_cost, 4),
                'success_rate': round(success_rate, 1)
            })

            projects.append(project_data)

        # Get total project count for pagination
        total_projects_cursor = self.conn.execute("""
            SELECT COUNT(DISTINCT project_name) FROM orchestration_sessions
        """)
        total_projects = total_projects_cursor.fetchone()[0]

        # Calculate pagination info
        total_pages = (total_projects + limit - 1) // limit
        current_page = (offset // limit) + 1
        has_next = offset + limit < total_projects
        has_previous = offset > 0

        return {
            'projects': projects,
            'pagination': {
                'total_count': total_projects,
                'total_pages': total_pages,
                'current_page': current_page,
                'page_size': limit,
                'has_next': has_next,
                'has_previous': has_previous,
                'next_offset': offset + limit if has_next else None,
                'previous_offset': max(0, offset - limit) if has_previous else None
            }
        }

    def _upgrade_schema_for_token_attribution(self):
        """Upgrade database schema to support token attribution tracking"""
        try:
            # Check if token attribution columns exist
            cursor = self.conn.execute("PRAGMA table_info(orchestration_sessions)")
            columns = [row[1] for row in cursor.fetchall()]

            # Add token attribution columns if they don't exist
            if 'claude_tokens_used' not in columns:
                self.conn.execute("ALTER TABLE orchestration_sessions ADD COLUMN claude_tokens_used INTEGER DEFAULT 0")
            if 'deepseek_tokens_used' not in columns:
                self.conn.execute("ALTER TABLE orchestration_sessions ADD COLUMN deepseek_tokens_used INTEGER DEFAULT 0")
            if 'mcp_tool_invocations' not in columns:
                self.conn.execute("ALTER TABLE orchestration_sessions ADD COLUMN mcp_tool_invocations INTEGER DEFAULT 0")

            # Add token attribution to handoff_events
            cursor = self.conn.execute("PRAGMA table_info(handoff_events)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'claude_tokens_used' not in columns:
                self.conn.execute("ALTER TABLE handoff_events ADD COLUMN claude_tokens_used INTEGER DEFAULT 0")
            if 'deepseek_tokens_used' not in columns:
                self.conn.execute("ALTER TABLE handoff_events ADD COLUMN deepseek_tokens_used INTEGER DEFAULT 0")
            if 'token_source' not in columns:
                self.conn.execute("ALTER TABLE handoff_events ADD COLUMN token_source TEXT DEFAULT 'claude'")

            # Add MCP tool tracking to subagent_invocations
            cursor = self.conn.execute("PRAGMA table_info(subagent_invocations)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'mcp_tool_name' not in columns:
                self.conn.execute("ALTER TABLE subagent_invocations ADD COLUMN mcp_tool_name TEXT")
            if 'mcp_server_name' not in columns:
                self.conn.execute("ALTER TABLE subagent_invocations ADD COLUMN mcp_server_name TEXT")
            if 'tool_category' not in columns:
                self.conn.execute("ALTER TABLE subagent_invocations ADD COLUMN tool_category TEXT")
            if 'estimated_tokens' not in columns:
                self.conn.execute("ALTER TABLE subagent_invocations ADD COLUMN estimated_tokens INTEGER DEFAULT 0")

            self.conn.commit()

        except Exception as e:
            logger.warning(f"Schema upgrade warning: {e}")

    def track_mcp_tool_invocation(self,
                                 session_id: str,
                                 tool_name: str,
                                 server_name: str,
                                 tool_category: str,
                                 task_description: str,
                                 estimated_tokens: int = 0,
                                 execution_time: float = None,
                                 success: bool = True,
                                 project_context: str = None) -> int:
        """Track MCP tool invocation as a subagent activity"""

        return self.track_subagent(
            session_id=session_id,
            agent_type='mcp_tool',
            agent_name=f"{server_name}.{tool_name}",
            trigger_phrase=f"MCP tool invocation: {tool_name}",
            task_description=task_description,
            execution_time=execution_time,
            success=success,
            tokens_used=estimated_tokens,
            metadata={
                'mcp_tool_name': tool_name,
                'mcp_server_name': server_name,
                'tool_category': tool_category,
                'project_context': project_context,
                'estimated_tokens': estimated_tokens,
                'invocation_type': 'mcp_tool'
            }
        )

    def get_project_token_attribution(self, project_name: str = None) -> Dict[str, Any]:
        """Get detailed token attribution analysis for projects"""

        if project_name:
            # Single project analysis
            where_clause = "WHERE s.project_name = ?"
            params = [project_name]
        else:
            # All projects
            where_clause = ""
            params = []

        # Get session-level token data
        session_tokens = self.conn.execute(f"""
            SELECT
                s.project_name,
                SUM(s.claude_tokens_used) as session_claude_tokens,
                SUM(s.deepseek_tokens_used) as session_deepseek_tokens,
                SUM(s.mcp_tool_invocations) as total_mcp_invocations,
                COUNT(*) as total_sessions
            FROM orchestration_sessions s
            {where_clause}
            GROUP BY s.project_name
        """, params).fetchall()

        # Get handoff-level token data
        handoff_tokens = self.conn.execute(f"""
            SELECT
                s.project_name,
                SUM(h.claude_tokens_used) as handoff_claude_tokens,
                SUM(h.deepseek_tokens_used) as handoff_deepseek_tokens,
                SUM(CASE WHEN h.target_model = 'deepseek' THEN 1 ELSE 0 END) as deepseek_handoffs,
                SUM(CASE WHEN h.target_model = 'claude' THEN 1 ELSE 0 END) as claude_handoffs,
                COUNT(*) as total_handoffs
            FROM handoff_events h
            JOIN orchestration_sessions s ON h.session_id = s.session_id
            {where_clause}
            GROUP BY s.project_name
        """, params).fetchall()

        # Get MCP tool usage data
        mcp_usage = self.conn.execute(f"""
            SELECT
                s.project_name,
                sa.mcp_server_name,
                sa.tool_category,
                COUNT(*) as invocation_count,
                SUM(sa.estimated_tokens) as total_mcp_tokens,
                AVG(sa.execution_time) as avg_execution_time
            FROM subagent_invocations sa
            JOIN orchestration_sessions s ON sa.session_id = s.session_id
            WHERE sa.agent_type = 'mcp_tool' {' AND ' + where_clause.replace('WHERE ', '') if where_clause else ''}
            GROUP BY s.project_name, sa.mcp_server_name, sa.tool_category
        """, params).fetchall()

        # Combine and structure the data
        result = {}

        for row in session_tokens:
            project = dict(row)
            project_name = project['project_name']
            result[project_name] = {
                'session_data': project,
                'handoff_data': {},
                'mcp_usage': {},
                'token_breakdown': {
                    'claude_total': project['session_claude_tokens'] or 0,
                    'deepseek_total': project['session_deepseek_tokens'] or 0,
                    'mcp_tool_tokens': 0
                }
            }

        # Add handoff data
        for row in handoff_tokens:
            handoff = dict(row)
            project_name = handoff['project_name']
            if project_name in result:
                result[project_name]['handoff_data'] = handoff
                # Add handoff tokens to totals
                result[project_name]['token_breakdown']['claude_total'] += handoff['handoff_claude_tokens'] or 0
                result[project_name]['token_breakdown']['deepseek_total'] += handoff['handoff_deepseek_tokens'] or 0

        # Add MCP usage data
        for row in mcp_usage:
            mcp = dict(row)
            project_name = mcp['project_name']
            if project_name in result:
                server_name = mcp['mcp_server_name'] or 'unknown'
                if server_name not in result[project_name]['mcp_usage']:
                    result[project_name]['mcp_usage'][server_name] = []

                result[project_name]['mcp_usage'][server_name].append(mcp)
                result[project_name]['token_breakdown']['mcp_tool_tokens'] += mcp['total_mcp_tokens'] or 0

        # Calculate percentages and insights
        for project_name, data in result.items():
            token_breakdown = data['token_breakdown']
            total_tokens = token_breakdown['claude_total'] + token_breakdown['deepseek_total'] + token_breakdown['mcp_tool_tokens']

            if total_tokens > 0:
                token_breakdown['claude_percentage'] = round((token_breakdown['claude_total'] / total_tokens) * 100, 1)
                token_breakdown['deepseek_percentage'] = round((token_breakdown['deepseek_total'] / total_tokens) * 100, 1)
                token_breakdown['mcp_percentage'] = round((token_breakdown['mcp_tool_tokens'] / total_tokens) * 100, 1)
            else:
                token_breakdown['claude_percentage'] = 0
                token_breakdown['deepseek_percentage'] = 0
                token_breakdown['mcp_percentage'] = 0

            token_breakdown['total_tokens'] = total_tokens

        return result

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')