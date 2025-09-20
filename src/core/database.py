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

            # Token orchestration tables for enhanced routing
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS token_budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    project_name TEXT,
                    initial_budget INTEGER DEFAULT 5000,
                    current_budget INTEGER DEFAULT 5000,
                    claude_tokens_used INTEGER DEFAULT 0,
                    deepseek_tokens_used INTEGER DEFAULT 0,
                    other_tokens_used INTEGER DEFAULT 0,
                    budget_exhausted BOOLEAN DEFAULT FALSE,
                    priority_level TEXT DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES orchestration_sessions(session_id)
                )
            """)

            # Model capacity thresholds
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS model_capacity_thresholds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    capacity_threshold REAL DEFAULT 0.8,
                    cost_per_token REAL DEFAULT 0.0,
                    quality_score REAL DEFAULT 1.0,
                    speed_score REAL DEFAULT 1.0,
                    availability_score REAL DEFAULT 1.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)

            # Routing decisions log
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    task_description TEXT,
                    task_complexity TEXT,
                    quality_requirement REAL,
                    speed_requirement TEXT,
                    cost_budget REAL,
                    selected_model TEXT,
                    selected_vendor TEXT,
                    routing_score REAL,
                    routing_factors TEXT,
                    alternatives_considered TEXT,
                    confidence_score REAL,
                    execution_success BOOLEAN,
                    actual_cost REAL,
                    actual_tokens INTEGER,
                    actual_duration REAL,
                    user_satisfaction REAL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES orchestration_sessions(session_id)
                )
            """)

            # Model performance tracking
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    task_type TEXT,
                    complexity_level TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time REAL,
                    tokens_used INTEGER,
                    cost REAL,
                    quality_score REAL,
                    success_rate REAL,
                    error_count INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    user_rating REAL,
                    project_context TEXT,
                    metadata TEXT
                )
            """)

            # Claude Code hooks tracking
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS claude_code_hooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    hook_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    trigger_event TEXT,
                    hook_data TEXT,
                    processing_time REAL,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES orchestration_sessions(session_id)
                )
            """)

            # Indexes for new tables
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_token_budgets_session ON token_budgets(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_token_budgets_project ON token_budgets(project_name, updated_at DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_model_capacity_vendor ON model_capacity_thresholds(vendor, model_name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_routing_decisions_session ON routing_decisions(session_id, timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_routing_decisions_model ON routing_decisions(selected_model, timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_model_performance_model ON model_performance(model_name, vendor, timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_model_performance_task_type ON model_performance(task_type, complexity_level, timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_claude_hooks_session ON claude_code_hooks(session_id, timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_claude_hooks_type ON claude_code_hooks(hook_type, timestamp DESC)")

            # Live activities table for real-time tracking
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS live_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    session_id TEXT,
                    data JSON NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    priority INTEGER DEFAULT 1
                )
            """)

            # Create indexes for live activities table
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON live_activities(timestamp DESC)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_event_type ON live_activities(event_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_session ON live_activities(session_id)")

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

    def track_session(self, session_id: str, project_name: str = None,
                     task_description: str = None, metadata: Dict = None,
                     working_directory: str = None, start_time=None, **kwargs) -> int:
        """Simple wrapper around create_session for real-time instrumentation"""
        return self.create_session(
            session_id=session_id,
            project_name=project_name,
            task_description=task_description,
            metadata=metadata,
            working_directory=working_directory
        )

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
                       0 as cost, 'claude' as model_or_agent, 'success' as status, project_name
                FROM orchestration_sessions
                UNION ALL
                SELECT h.timestamp, 'handoff' as event_type, h.session_id,
                       h.task_description as description, h.cost, h.target_model as model_or_agent,
                       CASE WHEN h.success = 1 THEN 'success' ELSE 'failed' END as status,
                       COALESCE(s.project_name, 'Unknown') as project_name
                FROM handoff_events h
                LEFT JOIN orchestration_sessions s ON h.session_id = s.session_id
                UNION ALL
                SELECT sub.timestamp, 'subagent' as event_type, sub.session_id,
                       sub.task_description as description, sub.cost, sub.agent_name as model_or_agent,
                       CASE WHEN sub.success = 1 THEN 'success' ELSE 'failed' END as status,
                       COALESCE(s.project_name, 'Unknown') as project_name
                FROM subagent_invocations sub
                LEFT JOIN orchestration_sessions s ON sub.session_id = s.session_id
            )
        """)
        total_count = total_count_cursor.fetchone()[0]

        # Get paginated activities
        cursor = self.conn.execute("""
            SELECT timestamp, event_type, session_id, description, cost, model_or_agent, status, project_name
            FROM (
                SELECT start_time as timestamp, 'session' as event_type, session_id,
                       project_name as description, 0 as cost, 'claude' as model_or_agent,
                       'success' as status, project_name
                FROM orchestration_sessions
                UNION ALL
                SELECT h.timestamp, 'handoff' as event_type, h.session_id,
                       h.task_description as description, h.cost, h.target_model as model_or_agent,
                       CASE WHEN h.success = 1 THEN 'success' ELSE 'failed' END as status,
                       COALESCE(s.project_name, 'Unknown') as project_name
                FROM handoff_events h
                LEFT JOIN orchestration_sessions s ON h.session_id = s.session_id
                UNION ALL
                SELECT sub.timestamp, 'subagent' as event_type, sub.session_id,
                       sub.task_description as description, sub.cost, sub.agent_name as model_or_agent,
                       CASE WHEN sub.success = 1 THEN 'success' ELSE 'failed' END as status,
                       COALESCE(s.project_name, 'Unknown') as project_name
                FROM subagent_invocations sub
                LEFT JOIN orchestration_sessions s ON sub.session_id = s.session_id
            )
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        activities = []
        for row in cursor.fetchall():
            activity = dict(row)
            # Ensure proper data types
            activity['cost'] = float(activity['cost']) if activity['cost'] else 0.0

            # Fix timezone handling: Add 'Z' suffix to indicate UTC timestamps
            # Database stores UTC timestamps without timezone info, so we need to indicate this to frontend
            if activity.get('timestamp') and not activity['timestamp'].endswith('Z'):
                activity['timestamp'] = activity['timestamp'] + 'Z'

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

            # Fix timezone handling for handoffs: Add 'Z' suffix to indicate UTC timestamps
            for handoff in handoffs:
                if handoff.get('timestamp') and not handoff['timestamp'].endswith('Z'):
                    handoff['timestamp'] = handoff['timestamp'] + 'Z'

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

            # Fix timezone handling for subagents: Add 'Z' suffix to indicate UTC timestamps
            for subagent in subagents:
                if subagent.get('timestamp') and not subagent['timestamp'].endswith('Z'):
                    subagent['timestamp'] = subagent['timestamp'] + 'Z'

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

    # Enhanced orchestration methods
    def track_token_budget(self, session_id: str, project_name: str = None,
                          initial_budget: int = 5000, priority_level: str = 'medium') -> int:
        """Create and track token budget for session"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO token_budgets
                (session_id, project_name, initial_budget, current_budget, priority_level)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, project_name, initial_budget, initial_budget, priority_level))
            return cursor.lastrowid

    def update_token_usage(self, session_id: str, claude_tokens: int = 0,
                          deepseek_tokens: int = 0, other_tokens: int = 0):
        """Update token usage for session budget"""
        with self.conn:
            # Update token counts
            self.conn.execute("""
                UPDATE token_budgets
                SET claude_tokens_used = claude_tokens_used + ?,
                    deepseek_tokens_used = deepseek_tokens_used + ?,
                    other_tokens_used = other_tokens_used + ?,
                    current_budget = initial_budget - (claude_tokens_used + deepseek_tokens_used + other_tokens_used),
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (claude_tokens, deepseek_tokens, other_tokens, session_id))

            # Check if budget exhausted
            result = self.conn.execute("""
                SELECT current_budget FROM token_budgets WHERE session_id = ?
            """, (session_id,)).fetchone()

            if result and result[0] <= 0:
                self.conn.execute("""
                    UPDATE token_budgets SET budget_exhausted = TRUE WHERE session_id = ?
                """, (session_id,))

    def track_routing_decision(self, session_id: str, task_description: str,
                              selected_model: str, selected_vendor: str,
                              routing_score: float, confidence_score: float,
                              task_complexity: str = 'medium',
                              quality_requirement: float = 0.8,
                              speed_requirement: str = 'normal',
                              cost_budget: float = None,
                              routing_factors: dict = None,
                              alternatives_considered: list = None) -> int:
        """Track routing decision with full context"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO routing_decisions (
                    session_id, task_description, task_complexity, quality_requirement,
                    speed_requirement, cost_budget, selected_model, selected_vendor,
                    routing_score, routing_factors, alternatives_considered, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, task_description, task_complexity, quality_requirement,
                  speed_requirement, cost_budget, selected_model, selected_vendor,
                  routing_score, json.dumps(routing_factors) if routing_factors else None,
                  json.dumps(alternatives_considered) if alternatives_considered else None,
                  confidence_score))
            return cursor.lastrowid

    def track_model_performance(self, model_name: str, vendor: str, task_type: str,
                               complexity_level: str, response_time: float = None,
                               tokens_used: int = None, cost: float = None,
                               quality_score: float = None, success_rate: float = None,
                               error_count: int = 0, user_rating: float = None,
                               project_context: str = None) -> int:
        """Track model performance metrics"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO model_performance (
                    model_name, vendor, task_type, complexity_level, response_time,
                    tokens_used, cost, quality_score, success_rate, error_count,
                    user_rating, project_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (model_name, vendor, task_type, complexity_level, response_time,
                  tokens_used, cost, quality_score, success_rate, error_count,
                  user_rating, project_context))
            return cursor.lastrowid

    def track_claude_hook(self, session_id: str, hook_type: str, trigger_event: str,
                         hook_data: dict = None, processing_time: float = None,
                         success: bool = True, error_message: str = None) -> int:
        """Track Claude Code hook execution"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO claude_code_hooks (
                    session_id, hook_type, trigger_event, hook_data,
                    processing_time, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, hook_type, trigger_event,
                  json.dumps(hook_data) if hook_data else None,
                  processing_time, success, error_message))
            return cursor.lastrowid

    def get_session_token_status(self, session_id: str) -> dict:
        """Get current token budget status for session"""
        cursor = self.conn.execute("""
            SELECT * FROM token_budgets WHERE session_id = ? ORDER BY updated_at DESC LIMIT 1
        """, (session_id,))

        result = cursor.fetchone()
        if result:
            return dict(result)
        return None

    def get_routing_analytics(self, start_date: str = None, end_date: str = None,
                             model_name: str = None) -> dict:
        """Get routing decision analytics"""
        base_query = """
            SELECT
                selected_model,
                selected_vendor,
                COUNT(*) as decision_count,
                AVG(routing_score) as avg_routing_score,
                AVG(confidence_score) as avg_confidence,
                SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                AVG(actual_cost) as avg_cost,
                AVG(actual_tokens) as avg_tokens,
                AVG(actual_duration) as avg_duration
            FROM routing_decisions
            WHERE 1=1
        """

        params = []
        if start_date and end_date:
            base_query += " AND timestamp BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        if model_name:
            base_query += " AND selected_model = ?"
            params.append(model_name)

        base_query += " GROUP BY selected_model, selected_vendor ORDER BY decision_count DESC"

        cursor = self.conn.execute(base_query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_model_performance_analytics(self, model_name: str = None, task_type: str = None) -> list:
        """Get model performance analytics"""
        base_query = """
            SELECT
                model_name,
                vendor,
                task_type,
                complexity_level,
                COUNT(*) as execution_count,
                AVG(response_time) as avg_response_time,
                AVG(tokens_used) as avg_tokens,
                AVG(cost) as avg_cost,
                AVG(quality_score) as avg_quality,
                AVG(success_rate) as avg_success_rate,
                SUM(error_count) as total_errors,
                AVG(user_rating) as avg_user_rating
            FROM model_performance
            WHERE 1=1
        """

        params = []
        if model_name:
            base_query += " AND model_name = ?"
            params.append(model_name)
        if task_type:
            base_query += " AND task_type = ?"
            params.append(task_type)

        base_query += """
            GROUP BY model_name, vendor, task_type, complexity_level
            ORDER BY execution_count DESC
        """

        cursor = self.conn.execute(base_query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_capacity_dashboard_data(self) -> dict:
        """Get comprehensive capacity and orchestration dashboard data"""
        # Token budget summary
        token_summary = self.conn.execute("""
            SELECT
                COUNT(*) as total_sessions,
                SUM(initial_budget) as total_initial_budget,
                SUM(current_budget) as total_remaining_budget,
                SUM(claude_tokens_used) as total_claude_tokens,
                SUM(deepseek_tokens_used) as total_deepseek_tokens,
                SUM(CASE WHEN budget_exhausted = 1 THEN 1 ELSE 0 END) as exhausted_sessions,
                AVG(CASE WHEN current_budget > 0 THEN current_budget * 100.0 / initial_budget ELSE 0 END) as avg_remaining_percentage
            FROM token_budgets
            WHERE updated_at >= datetime('now', '-7 days')
        """).fetchone()

        # Recent routing decisions
        recent_routing = self.conn.execute("""
            SELECT
                selected_model,
                selected_vendor,
                COUNT(*) as decision_count,
                AVG(confidence_score) as avg_confidence
            FROM routing_decisions
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY selected_model, selected_vendor
            ORDER BY decision_count DESC
        """).fetchall()

        # Model performance trends
        performance_trends = self.conn.execute("""
            SELECT
                model_name,
                vendor,
                COUNT(*) as executions,
                AVG(response_time) as avg_response_time,
                AVG(quality_score) as avg_quality,
                AVG(success_rate) as avg_success_rate
            FROM model_performance
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY model_name, vendor
            ORDER BY executions DESC
        """).fetchall()

        # Claude Code hooks activity
        hooks_activity = self.conn.execute("""
            SELECT
                hook_type,
                COUNT(*) as hook_count,
                AVG(processing_time) as avg_processing_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM claude_code_hooks
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY hook_type
            ORDER BY hook_count DESC
        """).fetchall()

        return {
            'token_summary': dict(token_summary) if token_summary else {},
            'recent_routing': [dict(row) for row in recent_routing],
            'performance_trends': [dict(row) for row in performance_trends],
            'hooks_activity': [dict(row) for row in hooks_activity]
        }

    # Live Activity Management
    def record_live_activity(self, event_type: str, session_id: str = None,
                            data: Dict = None, priority: int = 1) -> int:
        """Record a new live activity event"""
        if data is None:
            data = {}

        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO live_activities (event_type, session_id, data, priority)
                VALUES (?, ?, ?, ?)
            """, (event_type, session_id, json.dumps(data), priority))
            return cursor.lastrowid

    def get_live_activities(self, limit: int = 50, offset: int = 0,
                           event_type: str = None, since_timestamp: str = None,
                           until_timestamp: str = None, project_name: str = None,
                           session_id: str = None, search_text: str = None,
                           sort_by: str = 'timestamp', sort_order: str = 'DESC') -> List[Dict]:
        """Get live activities with comprehensive filtering and sorting"""

        # Base query with project extraction from session data
        query = """
            SELECT la.id, la.event_type, la.session_id, la.data, la.timestamp, la.priority,
                   COALESCE(s.project_name,
                           JSON_EXTRACT(la.data, '$.project_name'),
                           'Unknown') as project_name
            FROM live_activities la
            LEFT JOIN orchestration_sessions s ON la.session_id = s.session_id
        """
        params = []
        conditions = []

        # Event type filter
        if event_type:
            conditions.append("la.event_type = ?")
            params.append(event_type)

        # Time range filters
        if since_timestamp:
            conditions.append("la.timestamp >= ?")
            params.append(since_timestamp)

        if until_timestamp:
            conditions.append("la.timestamp <= ?")
            params.append(until_timestamp)

        # Project filter
        if project_name:
            conditions.append("(s.project_name = ? OR JSON_EXTRACT(la.data, '$.project_name') = ?)")
            params.extend([project_name, project_name])

        # Session filter
        if session_id:
            conditions.append("la.session_id = ?")
            params.append(session_id)

        # Text search in activity data
        if search_text:
            conditions.append("(la.data LIKE ? OR la.event_type LIKE ?)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern])

        # Add WHERE clause if we have conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Sorting
        valid_sort_columns = ['timestamp', 'event_type', 'project_name', 'priority']
        if sort_by not in valid_sort_columns:
            sort_by = 'timestamp'

        valid_sort_orders = ['ASC', 'DESC']
        if sort_order.upper() not in valid_sort_orders:
            sort_order = 'DESC'

        query += f" ORDER BY {sort_by} {sort_order.upper()}"

        # Pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(query, params)
        activities = []
        for row in cursor.fetchall():
            activity = dict(row)
            activity['data'] = json.loads(activity['data'])
            activities.append(activity)

        return activities

    def get_live_activities_count(self, event_type: str = None, since_timestamp: str = None,
                                 until_timestamp: str = None, project_name: str = None,
                                 session_id: str = None, search_text: str = None) -> int:
        """Get total count of activities matching the filters"""
        query = """
            SELECT COUNT(*) as total
            FROM live_activities la
            LEFT JOIN orchestration_sessions s ON la.session_id = s.session_id
        """
        params = []
        conditions = []

        # Apply same filters as get_live_activities
        if event_type:
            conditions.append("la.event_type = ?")
            params.append(event_type)

        if since_timestamp:
            conditions.append("la.timestamp >= ?")
            params.append(since_timestamp)

        if until_timestamp:
            conditions.append("la.timestamp <= ?")
            params.append(until_timestamp)

        if project_name:
            conditions.append("(s.project_name = ? OR JSON_EXTRACT(la.data, '$.project_name') = ?)")
            params.extend([project_name, project_name])

        if session_id:
            conditions.append("la.session_id = ?")
            params.append(session_id)

        if search_text:
            conditions.append("(la.data LIKE ? OR la.event_type LIKE ?)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor = self.conn.execute(query, params)
        return cursor.fetchone()[0]

    def get_activity_stats(self, period_hours: int = 24) -> Dict:
        """Get live activity statistics"""
        cursor = self.conn.execute("""
            SELECT
                event_type,
                COUNT(*) as count,
                MAX(timestamp) as latest_timestamp
            FROM live_activities
            WHERE timestamp >= datetime('now', '-{} hours')
            GROUP BY event_type
            ORDER BY count DESC
        """.format(period_hours))

        stats_by_type = {dict(row)['event_type']: dict(row) for row in cursor.fetchall()}

        # Total activities
        total_cursor = self.conn.execute("""
            SELECT COUNT(*) as total_activities
            FROM live_activities
            WHERE timestamp >= datetime('now', '-{} hours')
        """.format(period_hours))

        total_activities = total_cursor.fetchone()[0]

        return {
            'total_activities': total_activities,
            'by_type': stats_by_type,
            'period_hours': period_hours
        }

    def get_unique_activity_projects(self) -> List[str]:
        """Get unique project names from activities"""
        cursor = self.conn.execute("""
            SELECT DISTINCT
                COALESCE(s.project_name, JSON_EXTRACT(la.data, '$.project_name')) as project_name
            FROM live_activities la
            LEFT JOIN orchestration_sessions s ON la.session_id = s.session_id
            WHERE COALESCE(s.project_name, JSON_EXTRACT(la.data, '$.project_name')) IS NOT NULL
            ORDER BY project_name
        """)
        return [row[0] for row in cursor.fetchall()]

    def get_unique_activity_event_types(self) -> List[str]:
        """Get unique event types from activities"""
        cursor = self.conn.execute("""
            SELECT DISTINCT event_type
            FROM live_activities
            ORDER BY event_type
        """)
        return [row[0] for row in cursor.fetchall()]

    def cleanup_old_activities(self, days_to_keep: int = 7):
        """Clean up old live activities"""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM live_activities
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days_to_keep))
            return cursor.rowcount

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')