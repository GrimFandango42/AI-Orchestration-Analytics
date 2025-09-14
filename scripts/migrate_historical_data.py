"""
Historical Data Migration Script
===============================
Consolidates historical data from archived projects into the unified system.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
import uuid

# Add src to path for imports
sys.path.append('src')
from core.database import OrchestrationDB

class HistoricalDataMigrator:
    """Migrates and consolidates historical data from archived databases"""

    def __init__(self):
        self.target_db = OrchestrationDB()
        self.migration_log = []

        # Source databases with their data
        self.source_databases = {
            'orchestration_analytics.db': {
                'path': 'archive-old-projects/AI-Cost-Optimizer-PRJ/data/orchestration_analytics.db',
                'priority': 1,  # Highest priority - most comprehensive data
                'tables': {
                    'orchestration_events': 'orchestration_sessions',
                    'claude_tool_usage': 'handoff_events',
                    'mcp_agent_usage': 'subagent_invocations'
                }
            },
            'ai_usage.db': {
                'path': 'archive-old-projects/AI-Cost-Optimizer-PRJ/data/ai_usage.db',
                'priority': 2,
                'tables': {
                    'usage_logs': 'orchestration_sessions',
                    'orchestration_events': 'handoff_events',
                    'performance_metrics': 'cost_metrics'
                }
            },
            'unified_orchestration.db': {
                'path': 'archive-old-projects/AI-Cost-Optimizer-PRJ/data/unified_orchestration.db',
                'priority': 3,
                'tables': {
                    'usage_logs': 'orchestration_sessions',
                    'orchestration_events': 'handoff_events',
                    'performance_metrics': 'cost_metrics'
                }
            }
        }

    def backup_current_database(self):
        """Create backup of current database before migration"""
        import shutil

        backup_path = f"data/orchestration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2("data/orchestration.db", backup_path)
        self.migration_log.append(f"SUCCESS: Database backed up to {backup_path}")
        print(f"Database backed up to: {backup_path}")
        return backup_path

    def migrate_orchestration_events(self, source_conn, source_table):
        """Migrate orchestration events to orchestration_sessions"""
        cursor = source_conn.cursor()

        try:
            cursor.execute(f"""
                SELECT * FROM {source_table}
                ORDER BY timestamp
            """)

            records = cursor.fetchall()
            migrated = 0

            for record in records:
                try:
                    # Convert Row to dict for easier access
                    record_dict = dict(record)

                    # Generate unique session ID to avoid duplicates
                    original_id = record_dict.get('id', 'unknown')
                    session_id = f"migrated_{source_table}_{original_id}_{uuid.uuid4().hex[:8]}"

                    # Extract relevant fields
                    project_name = record_dict.get('project_name') or record_dict.get('project') or 'Historical Data'
                    task_description = record_dict.get('task_description') or record_dict.get('description') or record_dict.get('event_type', 'Historical orchestration event')

                    # Create session record
                    self.target_db.create_session(
                        session_id=session_id,
                        project_name=project_name,
                        task_description=task_description,
                        metadata={
                            'migrated_from': source_table,
                            'original_record': record_dict,
                            'migration_timestamp': datetime.now().isoformat()
                        }
                    )

                    migrated += 1

                except Exception as e:
                    self.migration_log.append(f"WARNING: Error migrating record {record_dict.get('id', 'unknown')}: {e}")

            self.migration_log.append(f"SUCCESS: Migrated {migrated} orchestration events from {source_table}")
            return migrated

        except sqlite3.Error as e:
            self.migration_log.append(f"ERROR: Error migrating from {source_table}: {e}")
            return 0

    def migrate_handoff_events(self, source_conn, source_table):
        """Migrate handoff-related events to handoff_events table"""
        cursor = source_conn.cursor()

        try:
            cursor.execute(f"SELECT * FROM {source_table} ORDER BY timestamp")
            records = cursor.fetchall()
            migrated = 0

            for record in records:
                try:
                    record_dict = dict(record)

                    # Generate unique session ID
                    original_id = record_dict.get('id', 'unknown')
                    session_id = f"migrated_{source_table}_{original_id}_{uuid.uuid4().hex[:8]}"

                    # Map fields for handoff events
                    task_type = record_dict.get('task_type') or record_dict.get('tool_type') or 'general'
                    task_description = record_dict.get('task_description') or record_dict.get('description') or 'Historical handoff event'

                    # Determine source and target models
                    source_model = 'claude_orchestrator'
                    target_model = record_dict.get('model_used') or record_dict.get('provider') or 'deepseek'

                    # Extract other metrics
                    tokens_used = record_dict.get('token_count') or record_dict.get('tokens_used') or 0
                    cost = record_dict.get('cost') or record_dict.get('estimated_cost') or 0
                    response_time = record_dict.get('response_time') or record_dict.get('execution_time') or 0
                    success = record_dict.get('success', True)

                    # Calculate savings (assume DeepSeek is free, Claude costs $0.015/1k tokens)
                    savings = 0.015 * (tokens_used / 1000) if target_model == 'deepseek' else 0

                    self.target_db.track_handoff(
                        session_id=session_id,
                        task_type=task_type,
                        task_description=task_description,
                        source_model=source_model,
                        target_model=target_model,
                        handoff_reason=f"Historical data migration from {source_table}",
                        confidence_score=0.8,  # Default confidence for migrated data
                        tokens_used=int(tokens_used) if tokens_used else None,
                        cost=float(cost) if cost else None,
                        savings=savings,
                        success=success,
                        response_time=float(response_time) if response_time else None,
                        metadata={
                            'migrated_from': source_table,
                            'original_record': record_dict,
                            'migration_timestamp': datetime.now().isoformat()
                        }
                    )

                    migrated += 1

                except Exception as e:
                    self.migration_log.append(f"WARNING: Error migrating handoff record: {e}")

            self.migration_log.append(f"SUCCESS: Migrated {migrated} handoff events from {source_table}")
            return migrated

        except sqlite3.Error as e:
            self.migration_log.append(f"ERROR: Error migrating handoffs from {source_table}: {e}")
            return 0

    def migrate_subagent_events(self, source_conn, source_table):
        """Migrate MCP agent usage to subagent_invocations"""
        cursor = source_conn.cursor()

        try:
            cursor.execute(f"SELECT * FROM {source_table} ORDER BY timestamp")
            records = cursor.fetchall()
            migrated = 0

            for record in records:
                try:
                    record_dict = dict(record)

                    # Generate unique session ID
                    original_id = record_dict.get('id', 'unknown')
                    session_id = f"migrated_{source_table}_{original_id}_{uuid.uuid4().hex[:8]}"

                    # Map MCP agent data to subagent structure
                    agent_name = record_dict.get('agent_name') or record_dict.get('tool_name') or 'unknown-agent'
                    agent_type = agent_name.split('-')[0] if '-' in agent_name else 'general'
                    task_description = record_dict.get('task_description') or record_dict.get('description') or 'Historical agent invocation'

                    execution_time = record_dict.get('execution_time') or record_dict.get('response_time') or 0
                    success = record_dict.get('success', True)
                    tokens_used = record_dict.get('token_count') or record_dict.get('tokens_used') or 0
                    cost = record_dict.get('cost') or 0

                    self.target_db.track_subagent(
                        session_id=session_id,
                        agent_type=agent_type,
                        agent_name=agent_name,
                        trigger_phrase='migrated_data',
                        task_description=task_description,
                        execution_time=float(execution_time) if execution_time else None,
                        success=success,
                        tokens_used=int(tokens_used) if tokens_used else None,
                        cost=float(cost) if cost else None,
                        metadata={
                            'migrated_from': source_table,
                            'original_record': record_dict,
                            'migration_timestamp': datetime.now().isoformat()
                        }
                    )

                    migrated += 1

                except Exception as e:
                    self.migration_log.append(f"WARNING: Error migrating subagent record: {e}")

            self.migration_log.append(f"SUCCESS: Migrated {migrated} subagent events from {source_table}")
            return migrated

        except sqlite3.Error as e:
            self.migration_log.append(f"ERROR: Error migrating subagents from {source_table}: {e}")
            return 0

    def execute_migration(self):
        """Execute the full migration process"""
        print("Starting historical data migration...")
        self.migration_log.append(f"Migration started at {datetime.now()}")

        # Backup current database
        backup_path = self.backup_current_database()

        total_migrated = 0

        # Process each source database in priority order
        for db_name, config in sorted(self.source_databases.items(), key=lambda x: x[1]['priority']):
            db_path = config['path']

            if not os.path.exists(db_path):
                self.migration_log.append(f"WARNING: Skipping {db_name}: not found at {db_path}")
                continue

            print(f"\nProcessing {db_name}...")

            try:
                source_conn = sqlite3.connect(db_path)
                source_conn.row_factory = sqlite3.Row

                for source_table, target_table in config['tables'].items():
                    try:
                        # Check if source table exists and has data
                        cursor = source_conn.cursor()
                        cursor.execute(f"SELECT COUNT(*) FROM {source_table}")
                        count = cursor.fetchone()[0]

                        if count == 0:
                            continue

                        print(f"  Migrating {source_table} ({count} records) -> {target_table}")

                        # Route to appropriate migration method
                        if target_table == 'orchestration_sessions':
                            migrated = self.migrate_orchestration_events(source_conn, source_table)
                        elif target_table == 'handoff_events':
                            migrated = self.migrate_handoff_events(source_conn, source_table)
                        elif target_table == 'subagent_invocations':
                            migrated = self.migrate_subagent_events(source_conn, source_table)
                        else:
                            print(f"    Skipping {source_table} -> {target_table} (no migration handler)")
                            continue

                        total_migrated += migrated

                    except sqlite3.Error as e:
                        self.migration_log.append(f"ERROR: Error processing {source_table}: {e}")

                source_conn.close()

            except sqlite3.Error as e:
                self.migration_log.append(f"ERROR: Error opening {db_path}: {e}")

        # Generate migration summary
        self.migration_log.append(f"Migration completed at {datetime.now()}")
        self.migration_log.append(f"Total records migrated: {total_migrated}")

        # Save migration log
        log_path = f"data/migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_path, 'w') as f:
            f.write("\\n".join(self.migration_log))

        print(f"\\nMigration completed!")
        print(f"Total records migrated: {total_migrated}")
        print(f"Migration log saved to: {log_path}")
        print(f"Database backup: {backup_path}")

        return total_migrated, log_path

if __name__ == "__main__":
    migrator = HistoricalDataMigrator()
    migrator.execute_migration()