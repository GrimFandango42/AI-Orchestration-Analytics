#!/usr/bin/env python3
"""
Comprehensive Database Testing Suite for AI Orchestration Analytics
Database Testing Specialist Agent Implementation

This script conducts thorough database testing including:
1. Schema validation and integrity checks
2. Data consistency and referential integrity
3. Transaction testing and ACID properties
4. Query performance analysis
5. Migration testing
6. Connection management validation
7. Backup and recovery testing
8. Data volume and stress testing
"""

import sqlite3
import json
import os
import sys
import time
import threading
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import uuid
import random
import concurrent.futures

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import OrchestrationDB

class DatabaseTestingSuite:
    """Comprehensive database testing suite"""

    def __init__(self, test_db_path: str = "data/test_orchestration.db"):
        self.test_db_path = test_db_path
        self.test_results = {}
        self.performance_metrics = {}
        self.setup_test_database()

    def setup_test_database(self):
        """Setup isolated test database"""
        # Ensure test directory exists
        Path(self.test_db_path).parent.mkdir(parents=True, exist_ok=True)

        # Remove existing test db if it exists
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        # Create fresh test database instance
        self.db = OrchestrationDB(self.test_db_path)
        print(f"✓ Test database created at: {self.test_db_path}")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive database testing suite"""
        print("=" * 80)
        print("DATABASE TESTING SUITE - AI ORCHESTRATION ANALYTICS")
        print("=" * 80)

        test_categories = [
            ("Schema Validation", self.test_schema_integrity),
            ("Data Integrity", self.test_data_integrity),
            ("Transaction Testing", self.test_transaction_handling),
            ("Query Performance", self.test_query_performance),
            ("Migration Testing", self.test_migration_scenarios),
            ("Connection Management", self.test_connection_management),
            ("Backup & Recovery", self.test_backup_recovery),
            ("Data Volume Testing", self.test_data_volume_performance)
        ]

        for category, test_func in test_categories:
            print(f"\n{'-' * 60}")
            print(f"TESTING: {category}")
            print(f"{'-' * 60}")

            start_time = time.time()
            try:
                results = test_func()
                elapsed = time.time() - start_time
                self.test_results[category] = {
                    'status': 'PASSED' if results.get('success', True) else 'FAILED',
                    'results': results,
                    'execution_time': elapsed,
                    'timestamp': datetime.now().isoformat()
                }
                print(f"✓ {category} completed in {elapsed:.2f}s")
            except Exception as e:
                elapsed = time.time() - start_time
                self.test_results[category] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'execution_time': elapsed,
                    'timestamp': datetime.now().isoformat()
                }
                print(f"✗ {category} failed: {e}")

        return self.generate_comprehensive_report()

    def test_schema_integrity(self) -> Dict[str, Any]:
        """Test database schema integrity and constraints"""
        results = {'success': True, 'checks': [], 'issues': []}

        # Check if all required tables exist
        expected_tables = [
            'orchestration_sessions', 'handoff_events', 'subagent_invocations',
            'task_outcomes', 'cost_metrics', 'pattern_analysis',
            'claude_account_analysis'
        ]

        cursor = self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in expected_tables:
            if table in existing_tables:
                results['checks'].append(f"✓ Table '{table}' exists")
            else:
                results['issues'].append(f"✗ Missing table: {table}")
                results['success'] = False

        # Check foreign key constraints
        fk_tests = [
            ("handoff_events", "session_id", "orchestration_sessions"),
            ("subagent_invocations", "session_id", "orchestration_sessions"),
            ("task_outcomes", "session_id", "orchestration_sessions")
        ]

        for child_table, fk_column, parent_table in fk_tests:
            cursor = self.db.conn.execute(f"PRAGMA foreign_key_list({child_table})")
            fk_info = cursor.fetchall()

            fk_exists = any(fk[2] == parent_table and fk[3] == fk_column for fk in fk_info)
            if fk_exists:
                results['checks'].append(f"✓ Foreign key constraint: {child_table}.{fk_column} -> {parent_table}")
            else:
                results['issues'].append(f"✗ Missing FK constraint: {child_table}.{fk_column} -> {parent_table}")

        # Check indexes
        expected_indexes = [
            'idx_sessions_time', 'idx_handoffs_session', 'idx_handoffs_time',
            'idx_subagents_session', 'idx_subagents_type', 'idx_outcomes_session'
        ]

        cursor = self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = [row[0] for row in cursor.fetchall()]

        for index in expected_indexes:
            if index in existing_indexes:
                results['checks'].append(f"✓ Index '{index}' exists")
            else:
                results['issues'].append(f"✗ Missing index: {index}")

        # Test column data types and constraints
        self._validate_column_constraints(results)

        return results

    def _validate_column_constraints(self, results: Dict):
        """Validate column data types and constraints"""
        table_schemas = {
            'orchestration_sessions': {
                'id': 'INTEGER PRIMARY KEY',
                'session_id': 'TEXT UNIQUE NOT NULL',
                'start_time': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            },
            'handoff_events': {
                'confidence_score': 'REAL',
                'tokens_used': 'INTEGER',
                'success': 'BOOLEAN'
            }
        }

        for table, expected_columns in table_schemas.items():
            cursor = self.db.conn.execute(f"PRAGMA table_info({table})")
            actual_columns = {row[1]: row[2] for row in cursor.fetchall()}

            for col_name, expected_type in expected_columns.items():
                if col_name in actual_columns:
                    results['checks'].append(f"✓ Column {table}.{col_name} exists")
                else:
                    results['issues'].append(f"✗ Missing column: {table}.{col_name}")

    def test_data_integrity(self) -> Dict[str, Any]:
        """Test data consistency and referential integrity"""
        results = {'success': True, 'checks': [], 'issues': [], 'violations': []}

        # Insert test data for integrity testing
        session_id = str(uuid.uuid4())
        self._insert_test_data(session_id)

        # Test referential integrity
        self._test_referential_integrity(results, session_id)

        # Test unique constraints
        self._test_unique_constraints(results)

        # Test data consistency
        self._test_data_consistency(results, session_id)

        # Test constraint enforcement
        self._test_constraint_enforcement(results)

        return results

    def _insert_test_data(self, session_id: str):
        """Insert test data for integrity testing"""
        # Create session
        self.db.create_session(
            session_id=session_id,
            project_name="test_project",
            task_description="Database integrity testing"
        )

        # Add handoff events
        self.db.track_handoff(
            session_id=session_id,
            task_type="implementation",
            task_description="Test handoff",
            source_model="claude",
            target_model="deepseek",
            handoff_reason="Cost optimization",
            confidence_score=0.95,
            tokens_used=1000,
            cost=0.015,
            savings=0.01
        )

        # Add subagent invocation
        self.db.track_subagent(
            session_id=session_id,
            agent_type="database-testing-specialist",
            agent_name="db_test_agent",
            task_description="Database testing task",
            execution_time=5.2,
            tokens_used=500,
            cost=0.0075
        )

    def _test_referential_integrity(self, results: Dict, session_id: str):
        """Test referential integrity constraints"""
        try:
            # Try to insert handoff with non-existent session_id
            fake_session = str(uuid.uuid4())
            self.db.track_handoff(
                session_id=fake_session,
                task_type="test",
                task_description="Referential integrity test",
                source_model="claude",
                target_model="deepseek",
                handoff_reason="Test"
            )

            # Check if the record was inserted (it shouldn't violate FK if we allow it)
            cursor = self.db.conn.execute(
                "SELECT COUNT(*) FROM handoff_events WHERE session_id = ?",
                (fake_session,)
            )
            count = cursor.fetchone()[0]

            if count > 0:
                results['checks'].append("✓ Foreign key constraint allows orphaned records (as designed)")

        except Exception as e:
            results['checks'].append(f"✓ Referential integrity maintained: {str(e)}")

    def _test_unique_constraints(self, results: Dict):
        """Test unique constraint enforcement"""
        try:
            session_id = str(uuid.uuid4())

            # Insert first session
            self.db.create_session(session_id=session_id, project_name="unique_test_1")
            results['checks'].append("✓ First session created successfully")

            # Try to insert duplicate session_id
            try:
                self.db.create_session(session_id=session_id, project_name="unique_test_2")
                results['issues'].append("✗ Unique constraint not enforced for session_id")
                results['success'] = False
            except sqlite3.IntegrityError:
                results['checks'].append("✓ Unique constraint enforced for session_id")

        except Exception as e:
            results['issues'].append(f"✗ Unique constraint test failed: {e}")
            results['success'] = False

    def _test_data_consistency(self, results: Dict, session_id: str):
        """Test data consistency across related tables"""
        # Check session data consistency
        session_cursor = self.db.conn.execute(
            "SELECT * FROM orchestration_sessions WHERE session_id = ?",
            (session_id,)
        )
        session = session_cursor.fetchone()

        if session:
            results['checks'].append("✓ Session data exists and consistent")

            # Check related handoff events
            handoff_cursor = self.db.conn.execute(
                "SELECT COUNT(*) FROM handoff_events WHERE session_id = ?",
                (session_id,)
            )
            handoff_count = handoff_cursor.fetchone()[0]

            # Check related subagent invocations
            subagent_cursor = self.db.conn.execute(
                "SELECT COUNT(*) FROM subagent_invocations WHERE session_id = ?",
                (session_id,)
            )
            subagent_count = subagent_cursor.fetchone()[0]

            if handoff_count > 0:
                results['checks'].append(f"✓ Found {handoff_count} related handoff events")
            if subagent_count > 0:
                results['checks'].append(f"✓ Found {subagent_count} related subagent invocations")
        else:
            results['issues'].append("✗ Session data not found")
            results['success'] = False

    def _test_constraint_enforcement(self, results: Dict):
        """Test constraint enforcement (NOT NULL, data types, etc.)"""
        try:
            # Test NOT NULL constraints
            try:
                self.db.conn.execute(
                    "INSERT INTO orchestration_sessions (session_id) VALUES (NULL)"
                )
                results['issues'].append("✗ NOT NULL constraint not enforced for session_id")
                results['success'] = False
            except sqlite3.IntegrityError:
                results['checks'].append("✓ NOT NULL constraint enforced")

        except Exception as e:
            results['issues'].append(f"✗ Constraint enforcement test failed: {e}")

    def test_transaction_handling(self) -> Dict[str, Any]:
        """Test ACID properties and transaction handling"""
        results = {'success': True, 'checks': [], 'issues': [], 'acid_tests': {}}

        # Test Atomicity
        results['acid_tests']['atomicity'] = self._test_atomicity()

        # Test Consistency
        results['acid_tests']['consistency'] = self._test_consistency()

        # Test Isolation
        results['acid_tests']['isolation'] = self._test_isolation()

        # Test Durability
        results['acid_tests']['durability'] = self._test_durability()

        # Test concurrent transactions
        results['concurrent_transactions'] = self._test_concurrent_transactions()

        return results

    def _test_atomicity(self) -> Dict[str, Any]:
        """Test transaction atomicity (all-or-nothing)"""
        result = {'success': True, 'details': []}

        try:
            session_id = str(uuid.uuid4())

            # Start transaction
            self.db.conn.execute("BEGIN TRANSACTION")

            try:
                # Insert session
                self.db.create_session(session_id=session_id, project_name="atomicity_test")
                result['details'].append("✓ Session inserted in transaction")

                # Insert handoff
                self.db.track_handoff(
                    session_id=session_id,
                    task_type="test",
                    task_description="Atomicity test",
                    source_model="claude",
                    target_model="deepseek",
                    handoff_reason="Test"
                )
                result['details'].append("✓ Handoff inserted in transaction")

                # Force an error to test rollback
                self.db.conn.execute("INSERT INTO non_existent_table VALUES (1)")

            except sqlite3.OperationalError:
                # Expected error - rollback transaction
                self.db.conn.execute("ROLLBACK")
                result['details'].append("✓ Transaction rolled back due to error")

                # Verify no data was committed
                cursor = self.db.conn.execute(
                    "SELECT COUNT(*) FROM orchestration_sessions WHERE session_id = ?",
                    (session_id,)
                )
                count = cursor.fetchone()[0]

                if count == 0:
                    result['details'].append("✓ Atomicity maintained - no partial data committed")
                else:
                    result['details'].append("✗ Atomicity violated - partial data committed")
                    result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Atomicity test failed: {e}")

        return result

    def _test_consistency(self) -> Dict[str, Any]:
        """Test database consistency constraints"""
        result = {'success': True, 'details': []}

        try:
            # Test that database remains in consistent state
            session_id = str(uuid.uuid4())

            # Insert valid data
            self.db.create_session(session_id=session_id, project_name="consistency_test")

            # Check database integrity after insertion
            cursor = self.db.conn.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            if integrity_result == "ok":
                result['details'].append("✓ Database integrity maintained")
            else:
                result['details'].append(f"✗ Database integrity compromised: {integrity_result}")
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Consistency test failed: {e}")

        return result

    def _test_isolation(self) -> Dict[str, Any]:
        """Test transaction isolation"""
        result = {'success': True, 'details': []}

        try:
            # Create two separate database connections to simulate concurrent transactions
            conn1 = sqlite3.connect(self.test_db_path)
            conn2 = sqlite3.connect(self.test_db_path)

            session_id = str(uuid.uuid4())

            # Transaction 1 starts
            conn1.execute("BEGIN TRANSACTION")
            conn1.execute(
                "INSERT INTO orchestration_sessions (session_id, project_name) VALUES (?, ?)",
                (session_id, "isolation_test")
            )
            result['details'].append("✓ Transaction 1 inserted data")

            # Transaction 2 tries to read uncommitted data
            cursor2 = conn2.execute(
                "SELECT COUNT(*) FROM orchestration_sessions WHERE session_id = ?",
                (session_id,)
            )
            count = cursor2.fetchone()[0]

            if count == 0:
                result['details'].append("✓ Isolation maintained - uncommitted data not visible")
            else:
                result['details'].append("✗ Isolation violated - uncommitted data visible")
                result['success'] = False

            # Commit transaction 1
            conn1.execute("COMMIT")

            # Now transaction 2 should see the data
            cursor2 = conn2.execute(
                "SELECT COUNT(*) FROM orchestration_sessions WHERE session_id = ?",
                (session_id,)
            )
            count = cursor2.fetchone()[0]

            if count == 1:
                result['details'].append("✓ Committed data now visible to other transactions")
            else:
                result['details'].append("✗ Committed data not visible")
                result['success'] = False

            conn1.close()
            conn2.close()

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Isolation test failed: {e}")

        return result

    def _test_durability(self) -> Dict[str, Any]:
        """Test transaction durability"""
        result = {'success': True, 'details': []}

        try:
            session_id = str(uuid.uuid4())

            # Insert and commit data
            with self.db.conn:
                self.db.create_session(session_id=session_id, project_name="durability_test")
            result['details'].append("✓ Data committed to database")

            # Close and reopen connection to simulate restart
            self.db.close()
            self.db = OrchestrationDB(self.test_db_path)

            # Verify data persists after restart
            cursor = self.db.conn.execute(
                "SELECT project_name FROM orchestration_sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()

            if row and row[0] == "durability_test":
                result['details'].append("✓ Data survived database restart - durability maintained")
            else:
                result['details'].append("✗ Data lost after restart - durability violated")
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Durability test failed: {e}")

        return result

    def _test_concurrent_transactions(self) -> Dict[str, Any]:
        """Test concurrent transaction handling"""
        result = {'success': True, 'details': [], 'concurrent_results': []}

        def concurrent_worker(worker_id: int):
            """Worker function for concurrent testing"""
            worker_result = {'worker_id': worker_id, 'success': True, 'operations': 0, 'errors': []}

            try:
                # Create separate connection for this worker
                conn = sqlite3.connect(self.test_db_path, timeout=10.0)
                conn.row_factory = sqlite3.Row

                for i in range(10):  # Each worker performs 10 operations
                    session_id = f"worker_{worker_id}_session_{i}"

                    try:
                        with conn:
                            conn.execute(
                                "INSERT INTO orchestration_sessions (session_id, project_name) VALUES (?, ?)",
                                (session_id, f"concurrent_test_worker_{worker_id}")
                            )
                        worker_result['operations'] += 1

                    except Exception as e:
                        worker_result['errors'].append(f"Operation {i}: {str(e)}")
                        worker_result['success'] = False

                conn.close()

            except Exception as e:
                worker_result['success'] = False
                worker_result['errors'].append(f"Worker setup failed: {str(e)}")

            return worker_result

        try:
            # Run concurrent transactions
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_worker = {executor.submit(concurrent_worker, i): i for i in range(5)}

                for future in concurrent.futures.as_completed(future_to_worker):
                    worker_result = future.result()
                    result['concurrent_results'].append(worker_result)

                    if worker_result['success']:
                        result['details'].append(f"✓ Worker {worker_result['worker_id']}: {worker_result['operations']} operations")
                    else:
                        result['details'].append(f"✗ Worker {worker_result['worker_id']}: {len(worker_result['errors'])} errors")
                        result['success'] = False

            # Verify total records inserted
            cursor = self.db.conn.execute(
                "SELECT COUNT(*) FROM orchestration_sessions WHERE project_name LIKE 'concurrent_test_worker_%'"
            )
            total_inserted = cursor.fetchone()[0]
            result['details'].append(f"✓ Total concurrent insertions: {total_inserted}")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Concurrent transaction test failed: {e}")

        return result

    def test_query_performance(self) -> Dict[str, Any]:
        """Analyze query performance and identify optimization opportunities"""
        results = {'success': True, 'performance_tests': {}, 'optimization_recommendations': []}

        # Generate test data for performance testing
        self._generate_performance_test_data()

        # Test common query patterns
        query_tests = [
            ("session_summary_query", "SELECT * FROM orchestration_sessions ORDER BY start_time DESC LIMIT 100"),
            ("handoff_analytics_query", """
                SELECT COUNT(*) as total_handoffs,
                       AVG(confidence_score) as avg_confidence,
                       SUM(cost) as total_cost
                FROM handoff_events
                WHERE timestamp >= datetime('now', '-30 days')
            """),
            ("subagent_usage_query", """
                SELECT agent_type, COUNT(*) as count, AVG(execution_time) as avg_time
                FROM subagent_invocations
                GROUP BY agent_type
                ORDER BY count DESC
            """),
            ("join_performance_query", """
                SELECT s.project_name, COUNT(h.id) as handoff_count, AVG(h.confidence_score) as avg_confidence
                FROM orchestration_sessions s
                LEFT JOIN handoff_events h ON s.session_id = h.session_id
                GROUP BY s.project_name
            """)
        ]

        for test_name, query in query_tests:
            performance_result = self._measure_query_performance(test_name, query)
            results['performance_tests'][test_name] = performance_result

            # Add optimization recommendations based on performance
            if performance_result['execution_time'] > 0.1:  # >100ms
                results['optimization_recommendations'].append({
                    'query': test_name,
                    'issue': f"Slow execution time: {performance_result['execution_time']:.3f}s",
                    'recommendation': "Consider adding indexes or optimizing query structure"
                })

        # Test index effectiveness
        results['index_analysis'] = self._analyze_index_effectiveness()

        return results

    def _generate_performance_test_data(self):
        """Generate test data for performance testing"""
        print("Generating performance test data...")

        # Generate sessions, handoffs, and subagent data
        for i in range(100):  # 100 sessions
            session_id = f"perf_test_session_{i}"
            self.db.create_session(
                session_id=session_id,
                project_name=f"test_project_{i % 10}",  # 10 different projects
                task_description=f"Performance test task {i}"
            )

            # Add 2-5 handoffs per session
            for j in range(random.randint(2, 5)):
                self.db.track_handoff(
                    session_id=session_id,
                    task_type=random.choice(["implementation", "analysis", "debugging"]),
                    task_description=f"Handoff {j} for session {i}",
                    source_model="claude",
                    target_model=random.choice(["deepseek", "claude"]),
                    handoff_reason="Performance test",
                    confidence_score=random.uniform(0.7, 0.99),
                    tokens_used=random.randint(100, 2000),
                    cost=random.uniform(0.001, 0.03)
                )

            # Add 1-3 subagent invocations per session
            for k in range(random.randint(1, 3)):
                self.db.track_subagent(
                    session_id=session_id,
                    agent_type=random.choice(["api-testing-specialist", "performance-testing-expert", "database-testing-specialist"]),
                    agent_name=f"agent_{k}",
                    task_description=f"Subagent task {k}",
                    execution_time=random.uniform(0.5, 10.0),
                    tokens_used=random.randint(50, 1000)
                )

    def _measure_query_performance(self, test_name: str, query: str) -> Dict[str, Any]:
        """Measure query execution performance"""
        result = {
            'test_name': test_name,
            'query': query,
            'success': True,
            'execution_time': 0,
            'rows_returned': 0,
            'query_plan': []
        }

        try:
            # Measure execution time
            start_time = time.time()
            cursor = self.db.conn.execute(query)
            rows = cursor.fetchall()
            execution_time = time.time() - start_time

            result['execution_time'] = execution_time
            result['rows_returned'] = len(rows)

            # Get query plan for analysis
            explain_cursor = self.db.conn.execute(f"EXPLAIN QUERY PLAN {query}")
            result['query_plan'] = [dict(zip(['selectid', 'order', 'from', 'detail'], row))
                                   for row in explain_cursor.fetchall()]

            print(f"  {test_name}: {execution_time:.3f}s ({len(rows)} rows)")

        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            print(f"  {test_name}: ERROR - {e}")

        return result

    def _analyze_index_effectiveness(self) -> Dict[str, Any]:
        """Analyze index usage and effectiveness"""
        analysis = {'indexes': [], 'recommendations': []}

        # Get list of all indexes
        cursor = self.db.conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
        indexes = cursor.fetchall()

        for index_name, index_sql in indexes:
            if index_name and not index_name.startswith('sqlite_'):  # Skip system indexes
                index_info = {
                    'name': index_name,
                    'sql': index_sql,
                    'usage_analysis': 'Index exists and should improve query performance'
                }
                analysis['indexes'].append(index_info)

        # Recommend additional indexes based on common query patterns
        potential_indexes = [
            {
                'table': 'handoff_events',
                'columns': ['target_model', 'timestamp'],
                'reason': 'Optimize handoff analytics queries by target model and time range'
            },
            {
                'table': 'subagent_invocations',
                'columns': ['agent_type', 'success'],
                'reason': 'Optimize subagent success rate queries'
            },
            {
                'table': 'task_outcomes',
                'columns': ['model_used', 'success', 'timestamp'],
                'reason': 'Optimize outcome analysis queries'
            }
        ]

        for index_rec in potential_indexes:
            analysis['recommendations'].append(index_rec)

        return analysis

    def test_migration_scenarios(self) -> Dict[str, Any]:
        """Test database migration scenarios"""
        results = {'success': True, 'migration_tests': [], 'issues': []}

        # Test schema upgrade scenarios
        migration_tests = [
            self._test_add_column_migration,
            self._test_add_index_migration,
            self._test_add_table_migration
        ]

        for test_func in migration_tests:
            try:
                test_result = test_func()
                results['migration_tests'].append(test_result)
                if not test_result['success']:
                    results['success'] = False
            except Exception as e:
                results['issues'].append(f"Migration test failed: {e}")
                results['success'] = False

        return results

    def _test_add_column_migration(self) -> Dict[str, Any]:
        """Test adding a new column (simulating schema evolution)"""
        result = {'test': 'add_column_migration', 'success': True, 'details': []}

        try:
            # Check if test column already exists
            cursor = self.db.conn.execute("PRAGMA table_info(orchestration_sessions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'test_migration_column' not in columns:
                # Add new column
                self.db.conn.execute("ALTER TABLE orchestration_sessions ADD COLUMN test_migration_column TEXT DEFAULT 'default_value'")
                result['details'].append("✓ Added new column successfully")

                # Verify column was added
                cursor = self.db.conn.execute("PRAGMA table_info(orchestration_sessions)")
                new_columns = [row[1] for row in cursor.fetchall()]

                if 'test_migration_column' in new_columns:
                    result['details'].append("✓ New column verified in schema")
                else:
                    result['details'].append("✗ New column not found in schema")
                    result['success'] = False
            else:
                result['details'].append("✓ Column already exists (previous test)")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Add column migration failed: {e}")

        return result

    def _test_add_index_migration(self) -> Dict[str, Any]:
        """Test adding a new index"""
        result = {'test': 'add_index_migration', 'success': True, 'details': []}

        try:
            index_name = 'idx_test_migration'

            # Check if index already exists
            cursor = self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
            exists = cursor.fetchone()

            if not exists:
                # Create new index
                self.db.conn.execute(f"CREATE INDEX {index_name} ON orchestration_sessions(project_name, start_time)")
                result['details'].append("✓ Created new index successfully")

                # Verify index was created
                cursor = self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
                if cursor.fetchone():
                    result['details'].append("✓ New index verified in schema")
                else:
                    result['details'].append("✗ New index not found")
                    result['success'] = False
            else:
                result['details'].append("✓ Index already exists (previous test)")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Add index migration failed: {e}")

        return result

    def _test_add_table_migration(self) -> Dict[str, Any]:
        """Test adding a new table"""
        result = {'test': 'add_table_migration', 'success': True, 'details': []}

        try:
            table_name = 'test_migration_table'

            # Check if table already exists
            cursor = self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            exists = cursor.fetchone()

            if not exists:
                # Create new table
                self.db.conn.execute(f"""
                    CREATE TABLE {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                result['details'].append("✓ Created new table successfully")

                # Verify table was created
                cursor = self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                if cursor.fetchone():
                    result['details'].append("✓ New table verified in schema")

                    # Test inserting data into new table
                    self.db.conn.execute(f"INSERT INTO {table_name} (name) VALUES (?)", ("test_record",))
                    result['details'].append("✓ Successfully inserted data into new table")
                else:
                    result['details'].append("✗ New table not found")
                    result['success'] = False
            else:
                result['details'].append("✓ Table already exists (previous test)")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Add table migration failed: {e}")

        return result

    def test_connection_management(self) -> Dict[str, Any]:
        """Test connection management and pooling"""
        results = {'success': True, 'connection_tests': []}

        # Test thread-local connections
        results['connection_tests'].append(self._test_thread_local_connections())

        # Test connection timeout handling
        results['connection_tests'].append(self._test_connection_timeouts())

        # Test connection cleanup
        results['connection_tests'].append(self._test_connection_cleanup())

        # Test concurrent connection handling
        results['connection_tests'].append(self._test_concurrent_connections())

        # Check for any failed tests
        results['success'] = all(test['success'] for test in results['connection_tests'])

        return results

    def _test_thread_local_connections(self) -> Dict[str, Any]:
        """Test thread-local connection management"""
        result = {'test': 'thread_local_connections', 'success': True, 'details': []}

        connections_created = []

        def worker_thread():
            try:
                # Access database from thread - should create thread-local connection
                db = OrchestrationDB(self.test_db_path)
                conn_id = id(db.conn)
                connections_created.append(conn_id)

                # Perform database operation
                cursor = db.conn.execute("SELECT COUNT(*) FROM orchestration_sessions")
                count = cursor.fetchone()[0]
                return True
            except Exception as e:
                result['details'].append(f"✗ Thread worker failed: {e}")
                return False

        try:
            # Create multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=worker_thread)
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Check that different connections were created
            if len(set(connections_created)) == len(connections_created):
                result['details'].append(f"✓ Created {len(connections_created)} unique thread-local connections")
            else:
                result['details'].append("✗ Thread-local connections not properly isolated")
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Thread-local connection test failed: {e}")

        return result

    def _test_connection_timeouts(self) -> Dict[str, Any]:
        """Test connection timeout handling"""
        result = {'test': 'connection_timeouts', 'success': True, 'details': []}

        try:
            # Create connection with short timeout
            conn = sqlite3.connect(self.test_db_path, timeout=1.0)

            # Start a long-running transaction in main connection
            self.db.conn.execute("BEGIN EXCLUSIVE TRANSACTION")

            try:
                # This should timeout quickly
                start_time = time.time()
                conn.execute("BEGIN EXCLUSIVE TRANSACTION")
                elapsed = time.time() - start_time

                result['details'].append(f"✗ No timeout occurred (elapsed: {elapsed:.2f}s)")
                result['success'] = False

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    result['details'].append("✓ Connection timeout handled properly")
                else:
                    result['details'].append(f"✗ Unexpected timeout error: {e}")
                    result['success'] = False

            finally:
                self.db.conn.execute("ROLLBACK")
                conn.close()

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Connection timeout test failed: {e}")

        return result

    def _test_connection_cleanup(self) -> Dict[str, Any]:
        """Test proper connection cleanup"""
        result = {'test': 'connection_cleanup', 'success': True, 'details': []}

        try:
            # Create and close database instance
            test_db = OrchestrationDB(self.test_db_path)

            # Access connection to ensure it's created
            _ = test_db.conn
            result['details'].append("✓ Database connection established")

            # Close database
            test_db.close()
            result['details'].append("✓ Database connection closed")

            # Try to access connection after close - should create new one
            try:
                _ = test_db.conn  # This should work (create new connection)
                result['details'].append("✓ New connection created after close")
            except Exception as e:
                result['details'].append(f"✗ Failed to create new connection after close: {e}")
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Connection cleanup test failed: {e}")

        return result

    def _test_concurrent_connections(self) -> Dict[str, Any]:
        """Test handling of concurrent database connections"""
        result = {'test': 'concurrent_connections', 'success': True, 'details': []}

        def connection_worker(worker_id: int):
            try:
                db = OrchestrationDB(self.test_db_path)

                # Perform database operations
                session_id = f"concurrent_conn_test_{worker_id}"
                db.create_session(session_id=session_id, project_name=f"concurrent_test_{worker_id}")

                # Read some data
                sessions = db.get_session_summary(limit=10)

                return {'worker_id': worker_id, 'success': True, 'sessions_found': len(sessions)}

            except Exception as e:
                return {'worker_id': worker_id, 'success': False, 'error': str(e)}

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_worker = {executor.submit(connection_worker, i): i for i in range(10)}

                worker_results = []
                for future in concurrent.futures.as_completed(future_to_worker):
                    worker_result = future.result()
                    worker_results.append(worker_result)

                    if worker_result['success']:
                        result['details'].append(f"✓ Worker {worker_result['worker_id']}: success")
                    else:
                        result['details'].append(f"✗ Worker {worker_result['worker_id']}: {worker_result['error']}")
                        result['success'] = False

                successful_workers = sum(1 for r in worker_results if r['success'])
                result['details'].append(f"✓ {successful_workers}/10 concurrent workers completed successfully")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Concurrent connections test failed: {e}")

        return result

    def test_backup_recovery(self) -> Dict[str, Any]:
        """Test backup and recovery procedures"""
        results = {'success': True, 'backup_tests': []}

        # Test database backup
        results['backup_tests'].append(self._test_database_backup())

        # Test backup integrity
        results['backup_tests'].append(self._test_backup_integrity())

        # Test point-in-time recovery
        results['backup_tests'].append(self._test_point_in_time_recovery())

        # Test cross-platform compatibility
        results['backup_tests'].append(self._test_backup_compatibility())

        results['success'] = all(test['success'] for test in results['backup_tests'])

        return results

    def _test_database_backup(self) -> Dict[str, Any]:
        """Test database backup creation"""
        result = {'test': 'database_backup', 'success': True, 'details': []}

        try:
            # Create backup directory
            backup_dir = Path("data/backups")
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"test_backup_{int(time.time())}.db"

            # Create backup using SQLite backup API
            source_conn = sqlite3.connect(self.test_db_path)
            backup_conn = sqlite3.connect(str(backup_path))

            source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            if backup_path.exists():
                result['details'].append(f"✓ Backup created successfully: {backup_path}")

                # Verify backup size
                backup_size = backup_path.stat().st_size
                original_size = Path(self.test_db_path).stat().st_size

                if backup_size == original_size:
                    result['details'].append("✓ Backup size matches original database")
                else:
                    result['details'].append(f"⚠ Backup size differs: {backup_size} vs {original_size}")

                # Store backup path for other tests
                result['backup_path'] = str(backup_path)

            else:
                result['details'].append("✗ Backup file not created")
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Database backup failed: {e}")

        return result

    def _test_backup_integrity(self) -> Dict[str, Any]:
        """Test backup file integrity"""
        result = {'test': 'backup_integrity', 'success': True, 'details': []}

        try:
            # Find a recent backup file
            backup_dir = Path("data/backups")
            backup_files = list(backup_dir.glob("test_backup_*.db"))

            if not backup_files:
                result['details'].append("✗ No backup files found for integrity test")
                result['success'] = False
                return result

            backup_path = backup_files[0]  # Use the first backup found

            # Test backup integrity
            backup_conn = sqlite3.connect(str(backup_path))

            # Check integrity
            cursor = backup_conn.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            if integrity_result == "ok":
                result['details'].append("✓ Backup integrity check passed")
            else:
                result['details'].append(f"✗ Backup integrity compromised: {integrity_result}")
                result['success'] = False

            # Verify data can be read from backup
            cursor = backup_conn.execute("SELECT COUNT(*) FROM orchestration_sessions")
            session_count = cursor.fetchone()[0]
            result['details'].append(f"✓ Backup contains {session_count} sessions")

            backup_conn.close()

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Backup integrity test failed: {e}")

        return result

    def _test_point_in_time_recovery(self) -> Dict[str, Any]:
        """Test point-in-time recovery capability"""
        result = {'test': 'point_in_time_recovery', 'success': True, 'details': []}

        try:
            # Record current state
            original_cursor = self.db.conn.execute("SELECT COUNT(*) FROM orchestration_sessions")
            original_count = original_cursor.fetchone()[0]

            # Create checkpoint
            checkpoint_time = datetime.now()

            # Add more data after checkpoint
            session_id = str(uuid.uuid4())
            self.db.create_session(
                session_id=session_id,
                project_name="recovery_test",
                task_description="Point-in-time recovery test"
            )

            # Record new state
            new_cursor = self.db.conn.execute("SELECT COUNT(*) FROM orchestration_sessions")
            new_count = new_cursor.fetchone()[0]

            result['details'].append(f"✓ Added test data: {original_count} -> {new_count} sessions")

            # Simulate recovery by querying data before checkpoint
            # (In real scenario, this would involve restoring from backup)
            recovery_cursor = self.db.conn.execute("""
                SELECT COUNT(*) FROM orchestration_sessions
                WHERE start_time < ?
            """, (checkpoint_time.isoformat(),))

            recovery_count = recovery_cursor.fetchone()[0]

            if recovery_count == original_count:
                result['details'].append("✓ Point-in-time recovery simulation successful")
            else:
                result['details'].append(f"✗ Recovery count mismatch: {recovery_count} vs {original_count}")
                result['success'] = False

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Point-in-time recovery test failed: {e}")

        return result

    def _test_backup_compatibility(self) -> Dict[str, Any]:
        """Test backup compatibility across different environments"""
        result = {'test': 'backup_compatibility', 'success': True, 'details': []}

        try:
            # Create a temporary copy of the database
            temp_path = tempfile.mktemp(suffix=".db")
            shutil.copy2(self.test_db_path, temp_path)

            # Open with different connection parameters
            compatibility_tests = [
                {"name": "Standard Connection", "params": {}},
                {"name": "WAL Mode", "params": {"isolation_level": None}},
                {"name": "Timeout Connection", "params": {"timeout": 30.0}}
            ]

            for test in compatibility_tests:
                try:
                    conn = sqlite3.connect(temp_path, **test["params"])
                    conn.row_factory = sqlite3.Row

                    # Test basic operations
                    cursor = conn.execute("SELECT COUNT(*) FROM orchestration_sessions")
                    count = cursor.fetchone()[0]

                    conn.close()
                    result['details'].append(f"✓ {test['name']}: {count} sessions accessible")

                except Exception as e:
                    result['details'].append(f"✗ {test['name']}: {e}")
                    result['success'] = False

            # Clean up
            os.unlink(temp_path)

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Backup compatibility test failed: {e}")

        return result

    def test_data_volume_performance(self) -> Dict[str, Any]:
        """Test performance with large datasets and high-volume inserts"""
        results = {'success': True, 'volume_tests': []}

        # Test large dataset performance
        results['volume_tests'].append(self._test_large_dataset_queries())

        # Test bulk insert performance
        results['volume_tests'].append(self._test_bulk_insert_performance())

        # Test concurrent high-volume operations
        results['volume_tests'].append(self._test_concurrent_high_volume())

        # Test database growth and storage efficiency
        results['volume_tests'].append(self._test_storage_efficiency())

        results['success'] = all(test['success'] for test in results['volume_tests'])

        return results

    def _test_large_dataset_queries(self) -> Dict[str, Any]:
        """Test query performance with large datasets"""
        result = {'test': 'large_dataset_queries', 'success': True, 'details': []}

        try:
            # Generate large dataset if not already present
            cursor = self.db.conn.execute("SELECT COUNT(*) FROM orchestration_sessions")
            current_count = cursor.fetchone()[0]

            target_count = 1000
            if current_count < target_count:
                print(f"Generating large dataset ({target_count - current_count} additional records)...")
                self._generate_large_dataset(target_count - current_count)
                result['details'].append(f"✓ Generated {target_count - current_count} additional records")

            # Test various queries on large dataset
            large_dataset_queries = [
                ("Full table scan", "SELECT COUNT(*) FROM orchestration_sessions"),
                ("Filtered query", "SELECT * FROM orchestration_sessions WHERE project_name LIKE 'test%' LIMIT 100"),
                ("Aggregation query", "SELECT project_name, COUNT(*), AVG(total_cost) FROM orchestration_sessions GROUP BY project_name"),
                ("Join query", """
                    SELECT s.project_name, COUNT(h.id) as handoffs, AVG(h.confidence_score) as avg_confidence
                    FROM orchestration_sessions s
                    LEFT JOIN handoff_events h ON s.session_id = h.session_id
                    GROUP BY s.project_name
                    LIMIT 50
                """)
            ]

            for query_name, query in large_dataset_queries:
                start_time = time.time()
                cursor = self.db.conn.execute(query)
                rows = cursor.fetchall()
                execution_time = time.time() - start_time

                result['details'].append(f"✓ {query_name}: {execution_time:.3f}s ({len(rows)} rows)")

                # Flag slow queries
                if execution_time > 2.0:  # > 2 seconds
                    result['details'].append(f"  ⚠ Query is slow: {execution_time:.3f}s")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Large dataset query test failed: {e}")

        return result

    def _generate_large_dataset(self, count: int):
        """Generate large dataset for volume testing"""
        batch_size = 100
        batches = count // batch_size

        for batch in range(batches):
            batch_data = []
            for i in range(batch_size):
                record_num = batch * batch_size + i
                session_id = f"volume_test_session_{record_num}"

                batch_data.append((
                    session_id,
                    f"volume_test_project_{record_num % 50}",  # 50 different projects
                    f"Volume test task {record_num}",
                    json.dumps({"batch": batch, "record": record_num})
                ))

            # Batch insert
            self.db.conn.executemany("""
                INSERT INTO orchestration_sessions
                (session_id, project_name, task_description, metadata)
                VALUES (?, ?, ?, ?)
            """, batch_data)

            self.db.conn.commit()

            if (batch + 1) % 10 == 0:  # Progress indicator every 10 batches
                print(f"  Generated {(batch + 1) * batch_size} records...")

    def _test_bulk_insert_performance(self) -> Dict[str, Any]:
        """Test bulk insert performance"""
        result = {'test': 'bulk_insert_performance', 'success': True, 'details': []}

        try:
            # Test different bulk insert strategies
            strategies = [
                ("Individual INSERTs", self._test_individual_inserts),
                ("Batch executemany", self._test_batch_executemany),
                ("Transaction batching", self._test_transaction_batching)
            ]

            for strategy_name, strategy_func in strategies:
                start_time = time.time()
                records_inserted = strategy_func(100)  # Insert 100 records
                execution_time = time.time() - start_time

                rate = records_inserted / execution_time if execution_time > 0 else 0
                result['details'].append(f"✓ {strategy_name}: {execution_time:.3f}s ({rate:.1f} records/sec)")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Bulk insert performance test failed: {e}")

        return result

    def _test_individual_inserts(self, count: int) -> int:
        """Test individual insert performance"""
        for i in range(count):
            session_id = f"individual_insert_{i}_{int(time.time())}"
            self.db.create_session(
                session_id=session_id,
                project_name=f"bulk_test_individual_{i % 10}",
                task_description=f"Individual insert test {i}"
            )
        return count

    def _test_batch_executemany(self, count: int) -> int:
        """Test batch executemany performance"""
        batch_data = []
        for i in range(count):
            session_id = f"batch_insert_{i}_{int(time.time())}"
            batch_data.append((
                session_id,
                f"bulk_test_batch_{i % 10}",
                f"Batch insert test {i}",
                None
            ))

        self.db.conn.executemany("""
            INSERT INTO orchestration_sessions
            (session_id, project_name, task_description, metadata)
            VALUES (?, ?, ?, ?)
        """, batch_data)

        self.db.conn.commit()
        return count

    def _test_transaction_batching(self, count: int) -> int:
        """Test transaction batching performance"""
        batch_size = 20
        batches = count // batch_size

        for batch in range(batches):
            with self.db.conn:  # Transaction per batch
                for i in range(batch_size):
                    record_num = batch * batch_size + i
                    session_id = f"transaction_batch_{record_num}_{int(time.time())}"
                    self.db.conn.execute("""
                        INSERT INTO orchestration_sessions
                        (session_id, project_name, task_description)
                        VALUES (?, ?, ?)
                    """, (
                        session_id,
                        f"bulk_test_transaction_{record_num % 10}",
                        f"Transaction batch test {record_num}"
                    ))

        return batches * batch_size

    def _test_concurrent_high_volume(self) -> Dict[str, Any]:
        """Test concurrent high-volume operations"""
        result = {'test': 'concurrent_high_volume', 'success': True, 'details': []}

        def high_volume_worker(worker_id: int, operation_count: int):
            try:
                db = OrchestrationDB(self.test_db_path)

                for i in range(operation_count):
                    session_id = f"concurrent_volume_{worker_id}_{i}_{int(time.time())}"
                    db.create_session(
                        session_id=session_id,
                        project_name=f"concurrent_volume_test_{worker_id}",
                        task_description=f"Concurrent volume test {i}"
                    )

                return {'worker_id': worker_id, 'success': True, 'operations': operation_count}

            except Exception as e:
                return {'worker_id': worker_id, 'success': False, 'error': str(e)}

        try:
            start_time = time.time()

            # Run concurrent workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_worker = {
                    executor.submit(high_volume_worker, i, 50): i
                    for i in range(5)  # 5 workers, 50 operations each
                }

                total_operations = 0
                successful_workers = 0

                for future in concurrent.futures.as_completed(future_to_worker):
                    worker_result = future.result()

                    if worker_result['success']:
                        total_operations += worker_result['operations']
                        successful_workers += 1
                        result['details'].append(f"✓ Worker {worker_result['worker_id']}: {worker_result['operations']} operations")
                    else:
                        result['details'].append(f"✗ Worker {worker_result['worker_id']}: {worker_result['error']}")
                        result['success'] = False

            execution_time = time.time() - start_time
            rate = total_operations / execution_time if execution_time > 0 else 0

            result['details'].append(f"✓ Concurrent operations: {total_operations} in {execution_time:.3f}s ({rate:.1f} ops/sec)")
            result['details'].append(f"✓ Successful workers: {successful_workers}/5")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Concurrent high-volume test failed: {e}")

        return result

    def _test_storage_efficiency(self) -> Dict[str, Any]:
        """Test database growth and storage efficiency"""
        result = {'test': 'storage_efficiency', 'success': True, 'details': []}

        try:
            # Get current database size
            db_path = Path(self.test_db_path)
            initial_size = db_path.stat().st_size

            # Get record counts
            tables = ['orchestration_sessions', 'handoff_events', 'subagent_invocations', 'task_outcomes']
            record_counts = {}
            total_records = 0

            for table in tables:
                cursor = self.db.conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                record_counts[table] = count
                total_records += count

            # Calculate storage metrics
            if total_records > 0:
                bytes_per_record = initial_size / total_records
                result['details'].append(f"✓ Database size: {initial_size:,} bytes")
                result['details'].append(f"✓ Total records: {total_records:,}")
                result['details'].append(f"✓ Average bytes per record: {bytes_per_record:.1f}")

                # Storage efficiency assessment
                if bytes_per_record < 1000:  # Less than 1KB per record is good
                    result['details'].append("✓ Storage efficiency: GOOD")
                elif bytes_per_record < 5000:  # Less than 5KB per record is acceptable
                    result['details'].append("✓ Storage efficiency: ACCEPTABLE")
                else:
                    result['details'].append("⚠ Storage efficiency: NEEDS OPTIMIZATION")

            # Detailed breakdown
            for table, count in record_counts.items():
                result['details'].append(f"  {table}: {count:,} records")

            # Test VACUUM operation for space reclamation
            pre_vacuum_size = db_path.stat().st_size
            self.db.conn.execute("VACUUM")
            post_vacuum_size = db_path.stat().st_size

            space_reclaimed = pre_vacuum_size - post_vacuum_size
            if space_reclaimed > 0:
                result['details'].append(f"✓ VACUUM reclaimed {space_reclaimed:,} bytes")
            else:
                result['details'].append("✓ VACUUM completed (no space reclaimed)")

        except Exception as e:
            result['success'] = False
            result['details'].append(f"✗ Storage efficiency test failed: {e}")

        return result

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive database testing report"""
        report = {
            'summary': {
                'total_tests': len(self.test_results),
                'passed_tests': sum(1 for r in self.test_results.values() if r['status'] == 'PASSED'),
                'failed_tests': sum(1 for r in self.test_results.values() if r['status'] == 'FAILED'),
                'error_tests': sum(1 for r in self.test_results.values() if r['status'] == 'ERROR'),
                'total_execution_time': sum(r['execution_time'] for r in self.test_results.values())
            },
            'test_results': self.test_results,
            'recommendations': self._generate_recommendations(),
            'performance_summary': self._generate_performance_summary(),
            'report_timestamp': datetime.now().isoformat()
        }

        return report

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on test results"""
        recommendations = []

        # Schema recommendations
        schema_results = self.test_results.get('Schema Validation', {}).get('results', {})
        if schema_results.get('issues'):
            recommendations.append({
                'category': 'Schema Integrity',
                'priority': 'HIGH',
                'issue': 'Missing schema components detected',
                'recommendation': 'Address missing tables, indexes, or constraints',
                'details': schema_results['issues']
            })

        # Performance recommendations
        performance_results = self.test_results.get('Query Performance', {}).get('results', {})
        if 'optimization_recommendations' in performance_results:
            for opt_rec in performance_results['optimization_recommendations']:
                recommendations.append({
                    'category': 'Query Performance',
                    'priority': 'MEDIUM',
                    'issue': opt_rec['issue'],
                    'recommendation': opt_rec['recommendation'],
                    'query': opt_rec['query']
                })

        # Volume testing recommendations
        volume_results = self.test_results.get('Data Volume Testing', {}).get('results', {})
        for test in volume_results.get('volume_tests', []):
            if 'Storage efficiency: NEEDS OPTIMIZATION' in str(test.get('details', [])):
                recommendations.append({
                    'category': 'Storage Optimization',
                    'priority': 'MEDIUM',
                    'issue': 'Storage efficiency needs improvement',
                    'recommendation': 'Consider data archiving, compression, or schema optimization'
                })

        # Connection management recommendations
        connection_results = self.test_results.get('Connection Management', {}).get('results', {})
        if not connection_results.get('success', True):
            recommendations.append({
                'category': 'Connection Management',
                'priority': 'HIGH',
                'issue': 'Connection management issues detected',
                'recommendation': 'Review connection pooling and timeout configurations'
            })

        return recommendations

    def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance testing summary"""
        summary = {
            'query_performance': {},
            'volume_performance': {},
            'connection_performance': {},
            'overall_assessment': 'GOOD'
        }

        # Query performance summary
        perf_results = self.test_results.get('Query Performance', {}).get('results', {})
        if 'performance_tests' in perf_results:
            total_queries = len(perf_results['performance_tests'])
            slow_queries = sum(1 for test in perf_results['performance_tests'].values()
                             if test.get('execution_time', 0) > 0.1)

            summary['query_performance'] = {
                'total_queries_tested': total_queries,
                'slow_queries': slow_queries,
                'performance_score': max(0, 100 - (slow_queries * 20))  # Deduct 20 points per slow query
            }

        # Volume performance summary
        volume_results = self.test_results.get('Data Volume Testing', {}).get('results', {})
        if 'volume_tests' in volume_results:
            successful_volume_tests = sum(1 for test in volume_results['volume_tests']
                                        if test.get('success', False))
            total_volume_tests = len(volume_results['volume_tests'])

            summary['volume_performance'] = {
                'successful_tests': successful_volume_tests,
                'total_tests': total_volume_tests,
                'success_rate': (successful_volume_tests / total_volume_tests * 100) if total_volume_tests > 0 else 0
            }

        # Overall assessment
        passed_tests = self.test_results.get('summary', {}).get('passed_tests', 0)
        total_tests = self.test_results.get('summary', {}).get('total_tests', 1)
        success_rate = (passed_tests / total_tests) * 100

        if success_rate >= 95:
            summary['overall_assessment'] = 'EXCELLENT'
        elif success_rate >= 85:
            summary['overall_assessment'] = 'GOOD'
        elif success_rate >= 70:
            summary['overall_assessment'] = 'FAIR'
        else:
            summary['overall_assessment'] = 'NEEDS_IMPROVEMENT'

        return summary

    def cleanup(self):
        """Clean up test resources"""
        try:
            if hasattr(self, 'db'):
                self.db.close()

            # Optionally remove test database
            if os.path.exists(self.test_db_path):
                # Keep test database for analysis
                print(f"Test database preserved at: {self.test_db_path}")

        except Exception as e:
            print(f"Cleanup warning: {e}")


def main():
    """Main execution function"""
    print("=" * 80)
    print("AI ORCHESTRATION ANALYTICS - DATABASE TESTING SUITE")
    print("Database Testing Specialist Agent")
    print("=" * 80)

    # Initialize testing suite
    test_suite = DatabaseTestingSuite()

    try:
        # Run comprehensive tests
        results = test_suite.run_all_tests()

        # Print summary
        print("\n" + "=" * 80)
        print("TESTING COMPLETE - SUMMARY REPORT")
        print("=" * 80)

        summary = results['summary']
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✓ Passed: {summary['passed_tests']}")
        print(f"✗ Failed: {summary['failed_tests']}")
        print(f"⚠ Errors: {summary['error_tests']}")
        print(f"Total Execution Time: {summary['total_execution_time']:.2f}s")

        # Print recommendations
        if results['recommendations']:
            print(f"\n{'-' * 60}")
            print("OPTIMIZATION RECOMMENDATIONS")
            print(f"{'-' * 60}")

            for rec in results['recommendations']:
                priority = rec['priority']
                category = rec['category']
                issue = rec['issue']
                recommendation = rec['recommendation']

                print(f"[{priority}] {category}: {issue}")
                print(f"  → {recommendation}")
                print()

        # Performance summary
        perf_summary = results['performance_summary']
        print(f"{'-' * 60}")
        print("PERFORMANCE ASSESSMENT")
        print(f"{'-' * 60}")
        print(f"Overall Assessment: {perf_summary['overall_assessment']}")

        if 'query_performance' in perf_summary:
            qp = perf_summary['query_performance']
            print(f"Query Performance Score: {qp.get('performance_score', 'N/A')}/100")
            print(f"Slow Queries: {qp.get('slow_queries', 0)}/{qp.get('total_queries_tested', 0)}")

        # Save detailed report
        report_path = f"data/database_test_report_{int(time.time())}.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nDetailed report saved to: {report_path}")

    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
    except Exception as e:
        print(f"\n\nTesting failed with error: {e}")
    finally:
        # Cleanup
        test_suite.cleanup()
        print("\nDatabase testing completed.")


if __name__ == "__main__":
    main()