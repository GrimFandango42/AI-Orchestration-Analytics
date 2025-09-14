"""
MCP Tool Detection and Subagent Integration
===========================================
Detects MCP tool invocations and tracks them as subagent activities
with proper project attribution and token tracking.
"""

import re
import json
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class MCPToolInvocation:
    """Represents an MCP tool invocation event"""
    tool_name: str
    server_name: str
    tool_type: str  # 'standard', 'custom', 'builtin'
    invocation_context: str
    parameters: Dict[str, Any]
    estimated_tokens: int
    project_context: str
    confidence: float

class MCPToolDetector:
    """Detects and categorizes MCP tool invocations for subagent tracking"""

    def __init__(self):
        # Comprehensive MCP tool mapping based on Claude-MCP-tools project
        self.mcp_tools = {
            # File System Operations
            'filesystem': {
                'server': 'filesystem',
                'tools': ['read_file', 'write_file', 'create_directory', 'list_directory',
                         'delete_file', 'move_file', 'copy_file', 'get_file_info'],
                'type': 'standard',
                'category': 'file_operations',
                'avg_tokens': 150,
                'description': 'File system read/write operations'
            },

            # Database Operations
            'sqlite': {
                'server': 'sqlite',
                'tools': ['execute_query', 'list_tables', 'describe_table', 'read_query'],
                'type': 'standard',
                'category': 'database',
                'avg_tokens': 200,
                'description': 'SQLite database operations'
            },

            # Web & API Operations
            'fetch': {
                'server': 'fetch',
                'tools': ['fetch_url', 'post_request', 'get_request', 'web_search'],
                'type': 'standard',
                'category': 'web_api',
                'avg_tokens': 300,
                'description': 'Web fetching and API calls'
            },

            # System Operations
            'bash': {
                'server': 'bash',
                'tools': ['execute', 'run_command', 'shell_command'],
                'type': 'standard',
                'category': 'system',
                'avg_tokens': 180,
                'description': 'System command execution'
            },

            # Git Operations
            'git': {
                'server': 'git',
                'tools': ['git_commit', 'git_status', 'git_diff', 'git_log', 'git_branch'],
                'type': 'standard',
                'category': 'version_control',
                'avg_tokens': 220,
                'description': 'Git version control operations'
            },

            # Custom Claude-MCP-tools
            'smart_test_generation': {
                'server': 'smart-test-generation',
                'tools': ['generate_tests', 'analyze_coverage', 'create_test_suite'],
                'type': 'custom',
                'category': 'testing',
                'avg_tokens': 400,
                'description': 'Intelligent test generation and coverage analysis'
            },

            'code_intelligence': {
                'server': 'code-intelligence',
                'tools': ['analyze_code', 'refactor_suggestion', 'code_review', 'dependency_analysis'],
                'type': 'custom',
                'category': 'code_analysis',
                'avg_tokens': 350,
                'description': 'Advanced code analysis and intelligence'
            },

            'cicd_orchestration': {
                'server': 'cicd-orchestration',
                'tools': ['trigger_pipeline', 'deploy_application', 'run_tests', 'build_project'],
                'type': 'custom',
                'category': 'devops',
                'avg_tokens': 280,
                'description': 'CI/CD pipeline orchestration and deployment'
            },

            'performance_testing': {
                'server': 'performance-testing',
                'tools': ['load_test', 'stress_test', 'benchmark', 'performance_analysis'],
                'type': 'custom',
                'category': 'performance',
                'avg_tokens': 320,
                'description': 'Performance testing and benchmarking'
            },

            # Specialized MCP Tools
            'search_integration': {
                'server': 'search-integration',
                'tools': ['semantic_search', 'index_content', 'search_query', 'similarity_search'],
                'type': 'custom',
                'category': 'search',
                'avg_tokens': 250,
                'description': 'Semantic search and content indexing'
            },

            'data_processing': {
                'server': 'data-processing',
                'tools': ['process_csv', 'transform_data', 'aggregate_data', 'clean_data'],
                'type': 'custom',
                'category': 'data',
                'avg_tokens': 200,
                'description': 'Data processing and transformation'
            }
        }

        # Patterns to detect MCP tool invocations in task descriptions
        self.detection_patterns = [
            # Direct tool invocations
            r'(?i)(use|invoke|call|execute)\s+(.*?)\s+(tool|server|mcp)',
            r'(?i)mcp\s+server\s+(\w+)',
            r'(?i)(filesystem|sqlite|fetch|bash|git)\.(\w+)',
            r'(?i)run\s+(.*?)\s+via\s+mcp',

            # Tool-specific patterns
            r'(?i)(read|write|create|delete)\s+(file|directory)',
            r'(?i)(query|select|insert|update)\s+.*?(database|sqlite)',
            r'(?i)(fetch|get|post)\s+.*?(url|api|http)',
            r'(?i)(execute|run)\s+(command|bash|shell)',
            r'(?i)(commit|push|pull|branch)\s+.*?git',

            # Custom tool patterns
            r'(?i)(generate|create)\s+(test|tests)',
            r'(?i)(analyze|review)\s+(code|coverage)',
            r'(?i)(deploy|build|pipeline)',
            r'(?i)(load|stress|performance)\s+test',
            r'(?i)(search|index|query)\s+(content|semantic)'
        ]

    def detect_mcp_invocation(self,
                             task_description: str,
                             metadata: Dict = None,
                             file_paths: List[str] = None) -> Optional[MCPToolInvocation]:
        """
        Detect MCP tool invocation from context clues

        Args:
            task_description: Description of the task being performed
            metadata: Additional context metadata
            file_paths: File paths being accessed

        Returns:
            MCPToolInvocation if detected, None otherwise
        """

        if not task_description:
            return None

        task_lower = task_description.lower()

        # Check for direct MCP tool mentions
        detected_tools = []

        for tool_name, tool_info in self.mcp_tools.items():
            # Check tool name in description
            if tool_name.lower() in task_lower:
                detected_tools.append((tool_name, tool_info, 0.8))
                continue

            # Check individual tool functions
            for tool_func in tool_info['tools']:
                if tool_func.lower() in task_lower:
                    detected_tools.append((tool_name, tool_info, 0.7))
                    break

            # Check server name
            if tool_info['server'].lower() in task_lower:
                detected_tools.append((tool_name, tool_info, 0.6))

        # Pattern-based detection
        for pattern in self.detection_patterns:
            matches = re.findall(pattern, task_description)
            if matches:
                # Try to map pattern matches to tools
                for match in matches:
                    match_text = ' '.join(match) if isinstance(match, tuple) else match
                    for tool_name, tool_info in self.mcp_tools.items():
                        if any(keyword in match_text.lower() for keyword in tool_info['tools']):
                            detected_tools.append((tool_name, tool_info, 0.5))

        # File path analysis
        if file_paths:
            for file_path in file_paths:
                if any(ext in file_path for ext in ['.py', '.js', '.ts', '.json', '.md']):
                    detected_tools.append(('filesystem', self.mcp_tools['filesystem'], 0.6))
                    break

        # Metadata analysis
        if metadata:
            meta_str = str(metadata).lower()
            if 'mcp' in meta_str or 'server' in meta_str:
                # Look for server references in metadata
                for tool_name, tool_info in self.mcp_tools.items():
                    if tool_info['server'] in meta_str:
                        detected_tools.append((tool_name, tool_info, 0.7))

        if not detected_tools:
            return None

        # Select best match
        best_tool = max(detected_tools, key=lambda x: x[2])
        tool_name, tool_info, confidence = best_tool

        # Estimate token usage based on tool type and complexity
        estimated_tokens = self._estimate_token_usage(tool_info, task_description)

        # Extract parameters from task description
        parameters = self._extract_parameters(task_description, tool_info)

        return MCPToolInvocation(
            tool_name=tool_name,
            server_name=tool_info['server'],
            tool_type=tool_info['type'],
            invocation_context=task_description,
            parameters=parameters,
            estimated_tokens=estimated_tokens,
            project_context=self._infer_project_context(task_description, metadata),
            confidence=confidence
        )

    def _estimate_token_usage(self, tool_info: Dict, task_description: str) -> int:
        """Estimate token usage for MCP tool invocation"""
        base_tokens = tool_info.get('avg_tokens', 150)

        # Adjust based on task complexity
        complexity_multiplier = 1.0

        task_lower = task_description.lower()
        if len(task_description) > 200:
            complexity_multiplier *= 1.3
        if any(word in task_lower for word in ['complex', 'comprehensive', 'detailed', 'full']):
            complexity_multiplier *= 1.4
        if any(word in task_lower for word in ['simple', 'quick', 'basic']):
            complexity_multiplier *= 0.8

        # Tool type adjustments
        if tool_info['type'] == 'custom':
            complexity_multiplier *= 1.2
        elif tool_info['type'] == 'standard':
            complexity_multiplier *= 1.0

        return int(base_tokens * complexity_multiplier)

    def _extract_parameters(self, task_description: str, tool_info: Dict) -> Dict[str, Any]:
        """Extract parameters from task description"""
        parameters = {}

        # Look for common parameter patterns
        task_lower = task_description.lower()

        # File paths
        file_patterns = re.findall(r'(?i)file[:\s]+([\w\./\\-]+)', task_description)
        if file_patterns:
            parameters['file_path'] = file_patterns[0]

        # URLs
        url_patterns = re.findall(r'https?://[\w\./\-?=&%]+', task_description)
        if url_patterns:
            parameters['url'] = url_patterns[0]

        # Commands
        if 'execute' in task_lower or 'run' in task_lower:
            command_patterns = re.findall(r'(?i)(?:execute|run)\s+["\']?([^"\']+)["\']?', task_description)
            if command_patterns:
                parameters['command'] = command_patterns[0]

        # Query patterns for database operations
        if any(db_word in task_lower for db_word in ['select', 'insert', 'update', 'delete']):
            parameters['query_type'] = 'database_operation'

        return parameters

    def _infer_project_context(self, task_description: str, metadata: Dict = None) -> str:
        """Infer project context from task and metadata"""

        # Check metadata first
        if metadata and 'project' in str(metadata).lower():
            if isinstance(metadata, dict) and 'project' in metadata:
                return metadata['project']

        # Common project indicators in task descriptions
        project_indicators = {
            'voicecloner': 'VoiceCloner',
            'goome': 'GooMe',
            'mcp': 'Claude-MCP-tools',
            'orchestration': 'AI-Orchestration-Analytics',
            'analytics': 'AI-Orchestration-Analytics',
            'agenticseek': 'agenticSeek',
            'jarvis': 'Jarvis-MCP',
            'healthcare': 'HealthcareCostAccounting'
        }

        task_lower = task_description.lower()
        for indicator, project in project_indicators.items():
            if indicator in task_lower:
                return project

        return 'Claude-MCP-tools'  # Default for MCP tool invocations

    def get_tool_categories(self) -> Dict[str, List[str]]:
        """Get tools organized by category"""
        categories = {}
        for tool_name, tool_info in self.mcp_tools.items():
            category = tool_info.get('category', 'other')
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
        return categories

    def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """Get detailed information about a specific tool"""
        return self.mcp_tools.get(tool_name)

    def is_mcp_related(self, task_description: str) -> bool:
        """Quick check if task is MCP-related"""
        task_lower = task_description.lower()
        mcp_keywords = ['mcp', 'server', 'tool', 'filesystem', 'sqlite', 'fetch', 'bash', 'git']
        return any(keyword in task_lower for keyword in mcp_keywords)