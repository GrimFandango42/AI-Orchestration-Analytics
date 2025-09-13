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

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')