#!/usr/bin/env python3
"""
DeepSeek Code Analysis Script for AI Orchestration Analytics

This script interfaces with the local DeepSeek R1 model via LM Studio to perform
comprehensive code analysis and improvement suggestions.
"""

import json
import requests
import time
import os
from pathlib import Path

class DeepSeekAnalyzer:
    def __init__(self, base_url="http://localhost:1234"):
        self.base_url = base_url
        self.model = "deepseek-r1"

    def send_request(self, messages, temperature=0.1, max_tokens=8000):
        """Send request to DeepSeek model"""
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error communicating with DeepSeek: {e}")
            return None

    def get_code_files_summary(self, project_root):
        """Generate a comprehensive code summary"""
        project_path = Path(project_root)

        # Key files to analyze
        key_files = [
            "src/launch.py",
            "src/core/database.py",
            "src/dashboard/orchestration_dashboard.py",
            "src/tracking/handoff_monitor.py",
            "src/tracking/subagent_tracker.py",
            "src/tracking/project_attribution.py",
            "src/tracking/mcp_tool_detector.py",
            "src/development/hot_reload.py"
        ]

        code_summary = {
            "project_structure": {},
            "key_files": {},
            "dependencies": {},
            "architecture": {
                "components": [
                    "Core Database (SQLite with analytics schema)",
                    "Dashboard Web Server (Quart/async Flask-like)",
                    "Handoff Monitoring (Claude/DeepSeek routing)",
                    "Subagent Tracking (MCP and specialized agents)",
                    "Project Attribution (intelligent project detection)",
                    "Hot Reload Development System",
                    "MCP Tool Detection and Integration"
                ],
                "database_tables": [
                    "orchestration_sessions", "handoff_events", "subagent_invocations",
                    "task_outcomes", "cost_metrics", "pattern_analysis"
                ],
                "api_endpoints": [
                    "/api/system-status", "/api/handoff-analytics", "/api/subagent-analytics",
                    "/api/cost-analytics", "/api/recent-activity", "/api/project-grouped-activity"
                ]
            }
        }

        # Read key files
        for file_path in key_files:
            full_path = project_path / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        code_summary["key_files"][file_path] = {
                            "size": len(content),
                            "lines": len(content.splitlines()),
                            "content": content[:3000] + "..." if len(content) > 3000 else content
                        }
                except Exception as e:
                    code_summary["key_files"][file_path] = {"error": str(e)}

        # Read dependencies
        requirements_path = project_path / "requirements.txt"
        if requirements_path.exists():
            with open(requirements_path, 'r', encoding='utf-8') as f:
                code_summary["dependencies"]["python"] = f.read()

        return code_summary

    def analyze_architecture(self, code_summary):
        """Analyze system architecture with DeepSeek"""

        system_prompt = """You are a senior software architect and code reviewer.
        Analyze this AI Orchestration Analytics codebase and provide:

        1. **CRITICAL BUGS** - Identify any critical bugs, errors, or security issues
        2. **ARCHITECTURE ASSESSMENT** - Evaluate the overall system design and structure
        3. **CODE QUALITY** - Review code patterns, error handling, and best practices
        4. **PERFORMANCE CONCERNS** - Identify potential bottlenecks and optimization opportunities
        5. **SECURITY ANALYSIS** - Check for security vulnerabilities and data protection issues
        6. **IMPROVEMENT RECOMMENDATIONS** - Suggest specific, actionable improvements

        Focus on production-readiness, scalability, and maintainability. Be specific about file locations and line numbers where possible."""

        user_content = f"""
        Here is the AI Orchestration Analytics system codebase summary:

        ## Architecture Overview
        {json.dumps(code_summary['architecture'], indent=2)}

        ## Key Files Analysis
        """

        # Add key file contents
        for file_path, file_info in code_summary["key_files"].items():
            if "content" in file_info:
                user_content += f"\n### {file_path} ({file_info.get('lines', 0)} lines)\n"
                user_content += f"```python\n{file_info['content']}\n```\n"

        user_content += f"""

        ## Dependencies
        ```
        {code_summary['dependencies'].get('python', '')}
        ```

        Please provide a comprehensive analysis focusing on making this system production-ready and identifying any critical issues that need immediate attention.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        print("Sending code to DeepSeek for comprehensive analysis...")
        response = self.send_request(messages, temperature=0.1)

        if response and 'choices' in response:
            analysis = response['choices'][0]['message']['content']
            print("DeepSeek analysis complete!")
            return analysis
        else:
            print("Failed to get response from DeepSeek")
            return None

    def analyze_specific_issues(self, issues_list):
        """Analyze specific code issues with DeepSeek"""

        system_prompt = """You are an expert Python developer.
        Analyze the provided code issues and bugs, then provide:
        1. Root cause analysis for each issue
        2. Specific code fixes with exact replacements
        3. Explanation of why the issue occurred
        4. Prevention strategies to avoid similar issues

        Provide production-ready solutions that are immediately implementable."""

        issues_text = "\n".join([f"- {issue}" for issue in issues_list])

        user_content = f"""
        Analyze these specific issues found in the AI Orchestration Analytics system:

        {issues_text}

        For each issue, provide the exact code fix needed and explain the solution.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        print("Sending specific issues to DeepSeek for analysis...")
        response = self.send_request(messages, temperature=0.1)

        if response and 'choices' in response:
            analysis = response['choices'][0]['message']['content']
            print("DeepSeek issue analysis complete!")
            return analysis
        else:
            print("Failed to get response from DeepSeek")
            return None

def main():
    """Main analysis workflow"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    analyzer = DeepSeekAnalyzer()

    print("Starting comprehensive DeepSeek code analysis...")

    # Get code summary
    print("Gathering code summary...")
    code_summary = analyzer.get_code_files_summary(project_root)

    # Test connection first
    test_response = analyzer.send_request([
        {"role": "user", "content": "Hello DeepSeek, are you ready for code analysis? Please respond briefly."}
    ])

    if not test_response:
        print("Cannot connect to DeepSeek. Please ensure LM Studio is running on localhost:1234")
        return

    print("DeepSeek connection confirmed!")

    # Run comprehensive analysis
    analysis = analyzer.analyze_architecture(code_summary)

    if analysis:
        # Save analysis to file
        with open("DEEPSEEK_ANALYSIS_RESULTS.md", "w", encoding="utf-8") as f:
            f.write("# DeepSeek Comprehensive Code Analysis\n\n")
            f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(analysis)

        print("Analysis saved to DEEPSEEK_ANALYSIS_RESULTS.md")

        # Also analyze specific known issues
        known_issues = [
            "TypeError: '>' not supported between instances of 'NoneType' and 'float' in subagent_tracker.py line 349",
            "NameError: name 'logger' is not defined in recent_activity API endpoint",
            "SQLite OperationalError: no such column: timestamp in recent activity queries",
            "SQLite OperationalError: no such column: status in project-grouped activity queries"
        ]

        issues_analysis = analyzer.analyze_specific_issues(known_issues)

        if issues_analysis:
            with open("DEEPSEEK_ISSUES_ANALYSIS.md", "w", encoding="utf-8") as f:
                f.write("# DeepSeek Specific Issues Analysis\n\n")
                f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(issues_analysis)

            print("Issues analysis saved to DEEPSEEK_ISSUES_ANALYSIS.md")

    print("DeepSeek analysis complete! Check the generated markdown files for results.")

if __name__ == "__main__":
    main()