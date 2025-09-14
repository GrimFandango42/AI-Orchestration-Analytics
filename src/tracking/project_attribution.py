"""
Intelligent Project Attribution System
====================================
Automatically detects and attributes activities to the correct AI project
based on context clues like working directory, file paths, MCP interactions, and task content.
"""

import os
import re
from typing import Dict, Optional, List, Tuple, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ProjectAttributor:
    """Intelligent project attribution system for AI orchestration tracking"""

    def __init__(self):
        # Complete project inventory from CLAUDE.md
        self.projects = {
            # AI/ML & Language Models
            'agenticSeek': {
                'aliases': ['agenticseek', 'agenic-seek', 'agenticSeek'],
                'keywords': ['search engine', 'ai search', 'docker', 'elasticsearch'],
                'paths': ['agenticSeek', 'agenticseek'],
                'category': 'AI/ML',
                'priority': 8
            },
            'Claude Computer Use Agent': {
                'aliases': ['claude-computer-use', 'computer-use', 'desktop-automation'],
                'keywords': ['computer use', 'desktop automation', 'anthropic api'],
                'paths': ['Claude Computer Use Agent'],
                'category': 'AI/ML',
                'priority': 7
            },
            'VoiceCloner': {
                'aliases': ['voicecloner', 'voice-cloner', 'voice cloning'],
                'keywords': ['voice cloning', 'speech synthesis', 'audio generation'],
                'paths': ['VoiceCloner', 'VoiceCloner_Backend'],
                'category': 'AI/ML',
                'priority': 9
            },
            'VoiceFlow': {
                'aliases': ['voiceflow', 'voice-flow'],
                'keywords': ['speech processing', 'voice workflow', 'audio processing'],
                'paths': ['VoiceFlow'],
                'category': 'AI/ML',
                'priority': 7
            },
            'personal-transcriber': {
                'aliases': ['transcriber', 'audio-transcription'],
                'keywords': ['transcription', 'audio to text', 'speech recognition'],
                'paths': ['personal-transcriber'],
                'category': 'AI/ML',
                'priority': 6
            },

            # MCP Ecosystem - High Priority
            'Claude-MCP-tools': {
                'aliases': ['mcp-tools', 'claude-mcp', 'mcp-servers', 'claude mcp tools'],
                'keywords': ['mcp server', 'model context protocol', 'tool integration', 'fastmcp'],
                'paths': ['Claude-MCP-tools'],
                'category': 'MCP',
                'priority': 10  # Highest priority - most active
            },
            'Jarvis-MCP': {
                'aliases': ['jarvis', 'jarvis-mcp', 'personal assistant'],
                'keywords': ['jarvis', 'personal assistant', 'mcp integration', 'ai assistant'],
                'paths': ['Jarvis-MCP'],
                'category': 'MCP',
                'priority': 8
            },
            'tool-foundation': {
                'aliases': ['tool-foundation', 'universal-tool'],
                'keywords': ['tool development', 'mcp integration', 'tool framework'],
                'paths': ['tool-foundation'],
                'category': 'MCP',
                'priority': 7
            },

            # Web Applications
            'GooMe': {
                'aliases': ['goome', 'groupme-clone', 'goome_v2'],
                'keywords': ['groupme', 'privacy', 'oauth', 'social platform', 'messaging'],
                'paths': ['GooMe', 'GooMe_v2'],
                'category': 'Web',
                'priority': 8
            },
            'GroupMeNavigator': {
                'aliases': ['groupme-navigator', 'groupme-nav'],
                'keywords': ['groupme navigation', 'groupme management', 'social media'],
                'paths': ['GroupMeNavigator'],
                'category': 'Web',
                'priority': 7
            },
            'AuroraBorealisApp': {
                'aliases': ['aurora', 'aurora-app', 'northern-lights'],
                'keywords': ['aurora tracking', 'visualization', 'weather app'],
                'paths': ['AuroraBorealisApp'],
                'category': 'Web',
                'priority': 6
            },

            # Analytics & Cost Optimization
            'AI-Orchestration-Analytics': {
                'aliases': ['orchestration-analytics', 'ai-analytics', 'cost-analytics'],
                'keywords': ['orchestration', 'cost optimization', 'analytics dashboard', 'deepseek handoff'],
                'paths': ['AI-Orchestration-Analytics', 'AI-Cost-Optimizer', 'AI-Cost-Optimizer-PRJ'],
                'category': 'Analytics',
                'priority': 9  # Current project - high priority
            },
            'HealthcareCostAccounting': {
                'aliases': ['healthcare-cost', 'medical-accounting'],
                'keywords': ['healthcare finance', 'cost analysis', 'medical accounting'],
                'paths': ['HealthcareCostAccounting'],
                'category': 'Analytics',
                'priority': 6
            },

            # Development Tools
            'ScreenPilot': {
                'aliases': ['screen-pilot', 'screen-automation'],
                'keywords': ['screen automation', 'control system', 'automation'],
                'paths': ['ScreenPilot'],
                'category': 'Development',
                'priority': 6
            },
            'Hyperion-Orchestrator': {
                'aliases': ['hyperion', 'orchestrator', 'multi-service'],
                'keywords': ['orchestration', 'multi-service', 'platform'],
                'paths': ['Hyperion-Orchestrator'],
                'category': 'Development',
                'priority': 7
            }
        }

        # Working directory cache for session persistence
        self._working_directory_cache = None
        self._last_detected_project = None

        # Context indicators for better attribution
        self.context_indicators = {
            'file_extensions': {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.tsx': 'react',
                '.jsx': 'react',
                '.md': 'documentation',
                '.json': 'config',
                '.yml': 'config',
                '.yaml': 'config'
            },
            'mcp_indicators': [
                'mcp server', 'fastmcp', 'model context protocol',
                'claude desktop', 'mcp-server', 'server.ts', 'server.js'
            ],
            'web_indicators': [
                'react', 'next.js', 'frontend', 'backend', 'api',
                'express', 'fastapi', 'flask', 'django'
            ]
        }

    def detect_project_from_context(self,
                                   working_directory: str = None,
                                   file_paths: List[str] = None,
                                   task_description: str = None,
                                   metadata: Dict = None) -> Tuple[str, float]:
        """
        Intelligently detect project attribution from multiple context sources.

        Args:
            working_directory: Current working directory path
            file_paths: List of file paths being accessed
            task_description: Description of the task being performed
            metadata: Additional context metadata

        Returns:
            Tuple of (project_name, confidence_score)
        """

        attribution_scores = {}

        # 1. Working Directory Analysis (Highest Priority)
        if working_directory:
            dir_score = self._analyze_working_directory(working_directory)
            for project, score in dir_score.items():
                attribution_scores[project] = attribution_scores.get(project, 0) + score * 0.4

        # 2. File Path Analysis
        if file_paths:
            file_score = self._analyze_file_paths(file_paths)
            for project, score in file_score.items():
                attribution_scores[project] = attribution_scores.get(project, 0) + score * 0.3

        # 3. Task Description Analysis
        if task_description:
            task_score = self._analyze_task_description(task_description)
            for project, score in task_score.items():
                attribution_scores[project] = attribution_scores.get(project, 0) + score * 0.2

        # 4. Metadata Analysis
        if metadata:
            meta_score = self._analyze_metadata(metadata)
            for project, score in meta_score.items():
                attribution_scores[project] = attribution_scores.get(project, 0) + score * 0.1

        # Find best match
        if not attribution_scores:
            return self._get_fallback_project(working_directory, task_description)

        # Sort by score and apply priority weighting
        weighted_scores = {}
        for project, score in attribution_scores.items():
            project_priority = self.projects.get(project, {}).get('priority', 1)
            weighted_scores[project] = score * (1 + project_priority * 0.05)

        best_project = max(weighted_scores.items(), key=lambda x: x[1])
        return best_project[0], min(best_project[1], 0.95)  # Cap confidence at 95%

    def _analyze_working_directory(self, working_dir: str) -> Dict[str, float]:
        """Analyze working directory for project clues"""
        scores = {}
        working_dir = working_dir.replace('\\', '/').lower()

        # Cache working directory for session persistence
        self._working_directory_cache = working_dir

        # Direct path matching
        for project_name, project_info in self.projects.items():
            for path in project_info.get('paths', []):
                path_lower = path.lower().replace('-', '').replace('_', '').replace(' ', '')
                if path_lower in working_dir.replace('-', '').replace('_', '').replace(' ', ''):
                    scores[project_name] = 0.9

            # Alias matching
            for alias in project_info.get('aliases', []):
                alias_lower = alias.lower().replace('-', '').replace('_', '').replace(' ', '')
                if alias_lower in working_dir.replace('-', '').replace('_', '').replace(' ', ''):
                    scores[project_name] = scores.get(project_name, 0) + 0.7

        # AI_Projects directory structure detection
        if 'ai_projects' in working_dir or 'ai-projects' in working_dir:
            # Extract project folder name
            parts = working_dir.split('/')
            if len(parts) >= 2:
                for i, part in enumerate(parts):
                    if 'ai_project' in part.lower():
                        if i + 1 < len(parts):
                            folder_name = parts[i + 1]
                            # Try to match folder name to project
                            for project_name, project_info in self.projects.items():
                                if (folder_name.lower().replace('-', '').replace('_', '') ==
                                    project_name.lower().replace('-', '').replace('_', '').replace(' ', '')):
                                    scores[project_name] = 0.95

        return scores

    def _analyze_file_paths(self, file_paths: List[str]) -> Dict[str, float]:
        """Analyze file paths for project attribution clues"""
        scores = {}

        for file_path in file_paths:
            file_path_lower = file_path.lower().replace('\\', '/')

            # Check if file path contains project indicators
            for project_name, project_info in self.projects.items():
                # Path matching
                for path in project_info.get('paths', []):
                    if path.lower() in file_path_lower:
                        scores[project_name] = scores.get(project_name, 0) + 0.6

                # Keyword matching in file names
                for keyword in project_info.get('keywords', []):
                    if keyword.lower() in file_path_lower:
                        scores[project_name] = scores.get(project_name, 0) + 0.3

        return scores

    def _analyze_task_description(self, task_description: str) -> Dict[str, float]:
        """Analyze task description for project attribution clues"""
        scores = {}
        task_lower = task_description.lower()

        for project_name, project_info in self.projects.items():
            # Direct project name matching
            if project_name.lower() in task_lower:
                scores[project_name] = 0.8

            # Alias matching
            for alias in project_info.get('aliases', []):
                if alias.lower() in task_lower:
                    scores[project_name] = scores.get(project_name, 0) + 0.6

            # Keyword matching
            for keyword in project_info.get('keywords', []):
                if keyword.lower() in task_lower:
                    scores[project_name] = scores.get(project_name, 0) + 0.4

        # Special patterns
        if any(indicator in task_lower for indicator in self.context_indicators['mcp_indicators']):
            scores['Claude-MCP-tools'] = scores.get('Claude-MCP-tools', 0) + 0.5

        return scores

    def _analyze_metadata(self, metadata: Dict) -> Dict[str, float]:
        """Analyze metadata for project attribution clues"""
        scores = {}

        # Convert metadata to searchable string
        meta_str = str(metadata).lower()

        for project_name, project_info in self.projects.items():
            for keyword in project_info.get('keywords', []):
                if keyword.lower() in meta_str:
                    scores[project_name] = scores.get(project_name, 0) + 0.3

        # Check for specific metadata fields
        if isinstance(metadata, dict):
            if 'project' in metadata:
                project_value = str(metadata['project']).lower()
                for project_name, project_info in self.projects.items():
                    if (project_name.lower() == project_value or
                        any(alias.lower() == project_value for alias in project_info.get('aliases', []))):
                        scores[project_name] = 0.9

        return scores

    def _get_fallback_project(self, working_directory: str = None, task_description: str = None) -> Tuple[str, float]:
        """Fallback attribution when no clear project is detected"""

        # Use cached working directory if available
        if not working_directory and self._working_directory_cache:
            working_directory = self._working_directory_cache

        # If in AI-Orchestration-Analytics directory, attribute to current project
        if working_directory and 'orchestration-analytics' in working_directory.lower():
            return 'AI-Orchestration-Analytics', 0.7

        # Use last detected project if available
        if self._last_detected_project:
            return self._last_detected_project, 0.5

        # Default to 'other' for unmatched activities
        return 'other', 0.3

    def get_active_project_context(self) -> Dict[str, Any]:
        """Get current active project context for session management"""
        working_dir = os.getcwd().replace('\\', '/')

        project_name, confidence = self.detect_project_from_context(
            working_directory=working_dir
        )

        # Cache the detected project
        if confidence > 0.5:
            self._last_detected_project = project_name

        return {
            'project_name': project_name,
            'confidence': confidence,
            'working_directory': working_dir,
            'project_category': self.projects.get(project_name, {}).get('category', 'Unknown'),
            'detection_method': 'working_directory_analysis'
        }

    def enhance_session_metadata(self,
                                existing_metadata: Dict = None,
                                working_directory: str = None,
                                file_paths: List[str] = None) -> Dict:
        """Enhance session metadata with attribution context"""

        metadata = existing_metadata.copy() if existing_metadata else {}

        # Add attribution context
        project_name, confidence = self.detect_project_from_context(
            working_directory=working_directory,
            file_paths=file_paths,
            task_description=metadata.get('task_description'),
            metadata=metadata
        )

        attribution_context = {
            'attribution': {
                'detected_project': project_name,
                'confidence': confidence,
                'working_directory': working_directory or os.getcwd(),
                'detection_timestamp': os.path.getmtime,
                'method': 'intelligent_attribution_v1'
            }
        }

        metadata.update(attribution_context)
        return metadata

    def get_project_aliases(self, project_name: str) -> List[str]:
        """Get all aliases for a project for normalization"""
        project_info = self.projects.get(project_name, {})
        return [project_name] + project_info.get('aliases', [])

    def normalize_project_name(self, input_name: str) -> str:
        """Normalize project name to canonical form"""
        input_lower = input_name.lower().strip()

        for project_name, project_info in self.projects.items():
            if project_name.lower() == input_lower:
                return project_name

            for alias in project_info.get('aliases', []):
                if alias.lower() == input_lower:
                    return project_name

        return input_name  # Return original if no match found