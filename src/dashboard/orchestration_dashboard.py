"""
AI Orchestration Analytics Dashboard
====================================
Unified dashboard for tracking AI orchestration, handoffs, and subagent usage
"""

from quart import Quart, jsonify, render_template_string, request
from quart_cors import cors
import sqlite3
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

from src.core.database import OrchestrationDB
from src.tracking.handoff_monitor import HandoffMonitor, DeepSeekClient
from src.tracking.subagent_tracker import SubagentTracker

app = Quart(__name__)
app = cors(app, allow_origin="*")

# Global instances
db = OrchestrationDB()
handoff_monitor = HandoffMonitor(db)
subagent_tracker = SubagentTracker(db)
deepseek_client = DeepSeekClient()

@app.route("/")
async def dashboard():
    """Main orchestration analytics dashboard"""
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Orchestration Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .status-bar {
            display: flex;
            justify-content: space-around;
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }

        .status-item {
            text-align: center;
        }

        .status-value {
            font-size: 2em;
            font-weight: bold;
            display: block;
        }

        .status-online { color: #22c55e; }
        .status-offline { color: #ef4444; }
        .status-warning { color: #f59e0b; }

        /* Tooltip Styles */
        .tooltip {
            position: absolute;
            background: rgba(0, 0, 0, 0.95);
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.4;
            max-width: 300px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            pointer-events: none;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.2s ease;
        }

        .tooltip.show {
            opacity: 1;
            transform: translateY(0);
        }

        .tooltip::before {
            content: '';
            position: absolute;
            top: -8px;
            left: 50%;
            transform: translateX(-50%);
            border: 4px solid transparent;
            border-bottom-color: rgba(0, 0, 0, 0.95);
        }

        .tooltip-title {
            font-weight: bold;
            margin-bottom: 8px;
            color: #60a5fa;
        }

        .tooltip-item {
            margin: 4px 0;
            display: flex;
            justify-content: space-between;
        }

        .tooltip-label {
            margin-right: 12px;
        }

        .tooltip-value {
            font-weight: 500;
        }

        [data-tooltip] {
            cursor: help;
            position: relative;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }

        .card-title {
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 20px;
            color: #4a5568;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }

        .metric:last-child { border-bottom: none; }

        .metric-label { color: #718096; }
        .metric-value {
            font-weight: 600;
            font-size: 1.1em;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }

        .table-container {
            max-height: 400px;
            overflow-y: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }

        th, td {
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        th {
            background-color: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            position: sticky;
            top: 0;
        }

        .model-deepseek {
            color: #22c55e;
            font-weight: bold;
        }

        .model-claude {
            color: #3b82f6;
            font-weight: bold;
        }

        .success { color: #22c55e; }
        .error { color: #ef4444; }
        .warning { color: #f59e0b; }

        .refresh-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            align-items: center;
        }

        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: transform 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #4a5568;
        }

        .toggle-switch {
            position: relative;
            width: 50px;
            height: 25px;
            background-color: #cbd5e0;
            border-radius: 25px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .toggle-switch.active {
            background-color: #667eea;
        }

        .toggle-switch::after {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 21px;
            height: 21px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
        }

        .toggle-switch.active::after {
            transform: translateX(25px);
        }

        .project-activity-container {
            max-height: 400px;
            overflow-y: auto;
        }

        .project-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 12px;
            background: #f7fafc;
        }

        .project-header {
            padding: 12px 16px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e2e8f0;
            background: #ffffff;
            border-radius: 8px 8px 0 0;
        }

        .project-header:hover {
            background: #f1f5f9;
        }

        .project-header.expanded {
            border-radius: 8px 8px 0 0;
        }

        .project-info {
            flex: 1;
        }

        .project-name {
            font-weight: 600;
            color: #2d3748;
            margin: 0;
        }

        .project-stats {
            font-size: 0.85rem;
            color: #718096;
            margin-top: 4px;
        }

        .project-expand-icon {
            transition: transform 0.2s;
            color: #718096;
        }

        .project-expand-icon.expanded {
            transform: rotate(180deg);
        }

        .project-activities {
            display: none;
            padding: 16px;
            background: #ffffff;
            border-radius: 0 0 8px 8px;
        }

        .project-activities.expanded {
            display: block;
        }

        .activity-group {
            margin-bottom: 16px;
        }

        .activity-group:last-child {
            margin-bottom: 0;
        }

        .activity-group-title {
            font-size: 0.9rem;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #e2e8f0;
        }

        .activity-item {
            padding: 8px 12px;
            margin-bottom: 6px;
            background: #f7fafc;
            border-radius: 4px;
            border-left: 3px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .activity-item.handoff {
            border-left-color: #3b82f6;
        }

        .activity-item.subagent {
            border-left-color: #667eea;
        }

        .activity-details {
            flex: 1;
        }

        .activity-meta {
            font-size: 0.8rem;
            color: #718096;
        }

        .activity-description {
            font-size: 0.85rem;
            color: #2d3748;
            margin-top: 2px;
        }

        .activity-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-right: 8px;
        }

        .activity-badge.success {
            background: #c6f6d5;
            color: #22543d;
        }

        .activity-badge.failed {
            background: #fed7d7;
            color: #742a2a;
        }

        .activity-cost {
            font-size: 0.8rem;
            color: #4a5568;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .project-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .project-stats {
                margin-top: 8px;
            }

            .activity-item {
                flex-direction: column;
                align-items: flex-start;
            }

            .activity-cost {
                margin-top: 4px;
                align-self: flex-end;
            }

            .status-bar {
                flex-direction: column;
                gap: 15px;
            }
        }

        .live-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Orchestration Analytics</h1>
            <p>Real-time monitoring of Claude Code orchestration, DeepSeek handoffs, and subagent usage</p>
        </div>

        <div class="status-bar" id="statusBar">
            <!-- Status items will be loaded here -->
        </div>

        <div class="refresh-controls">
            <button class="btn" onclick="refreshAll()">Refresh All Data</button>
            <div class="auto-refresh">
                <span>Auto-refresh</span>
                <div class="toggle-switch" id="autoRefreshToggle" onclick="toggleAutoRefresh()"></div>
                <span class="live-indicator" id="liveIndicator" style="display: none;"></span>
            </div>
        </div>

        <div class="dashboard-grid">
            <!-- Handoff Analytics -->
            <div class="card">
                <h3 class="card-title">Model Handoff Analytics</h3>
                <div id="handoffMetrics">
                    <!-- Metrics will be loaded here -->
                </div>
                <div class="chart-container">
                    <canvas id="handoffChart"></canvas>
                </div>
            </div>

            <!-- Subagent Usage -->
            <div class="card">
                <h3 class="card-title">Subagent Usage Patterns</h3>
                <div id="subagentMetrics">
                    <!-- Metrics will be loaded here -->
                </div>
                <div class="chart-container">
                    <canvas id="subagentChart"></canvas>
                </div>
            </div>

            <!-- Cost Analytics -->
            <div class="card">
                <h3 class="card-title">Cost Optimization</h3>
                <div id="costMetrics">
                    <!-- Metrics will be loaded here -->
                </div>
                <div class="chart-container">
                    <canvas id="costChart"></canvas>
                </div>
            </div>

            <!-- Max-to-Pro Account Transition Analysis -->
            <div class="card">
                <h3 class="card-title">Max → Pro Account Transition</h3>
                <div id="accountTransitionMetrics">
                    <!-- Metrics will be loaded here -->
                </div>
                <div class="chart-container">
                    <canvas id="transitionChart"></canvas>
                </div>
            </div>

            <!-- Performance Metrics -->
            <div class="card">
                <h3 class="card-title">Performance Metrics</h3>
                <div id="performanceMetrics">
                    <!-- Metrics will be loaded here -->
                </div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="card">
            <h3 class="card-title">Project Activity Overview</h3>
            <div class="activity-view-controls" style="margin-bottom: 15px;">
                <button class="btn btn-secondary" id="toggleViewBtn" onclick="toggleActivityView()">Switch to Flat View</button>
            </div>
            <div id="projectGroupedView" class="project-activity-container">
                <!-- Project-grouped activity will be loaded here -->
            </div>
            <div id="flatActivityView" class="table-container" style="display: none;">
                <table id="activityTable">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Session</th>
                            <th>Event Type</th>
                            <th>Model/Agent</th>
                            <th>Description</th>
                            <th>Status</th>
                            <th>Cost</th>
                        </tr>
                    </thead>
                    <tbody id="activityBody">
                        <!-- Activity data will be loaded here -->
                    </tbody>
                </table>
            </div>

            <!-- Pagination Controls for both views -->
            <div class="pagination-container" style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; padding: 0 10px;">
                <div class="pagination-info">
                    <span id="paginationInfo">Loading...</span>
                </div>
                <div class="pagination-controls">
                    <button id="prevBtn" class="btn" style="margin-right: 10px;" onclick="loadActivityPage('prev')" disabled>← Previous</button>
                    <span id="pageInfo">Page 1</span>
                    <button id="nextBtn" class="btn" style="margin-left: 10px;" onclick="loadActivityPage('next')" disabled>Next →</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let charts = {};
        let autoRefreshInterval = null;
        let isAutoRefresh = false;
        let currentActivityPage = 1;
        let activityPagination = null;
        let isProjectView = true;
        let currentProjectPage = 1;
        let projectPagination = null;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            refreshAll();
            initializeTooltips();
        });

        // Tooltip System
        let currentTooltip = null;

        function initializeTooltips() {
            document.addEventListener('mouseover', handleTooltipShow);
            document.addEventListener('mouseout', handleTooltipHide);
            document.addEventListener('mousemove', handleTooltipMove);
        }

        function handleTooltipShow(e) {
            const element = e.target.closest('[data-tooltip]');
            if (!element) return;

            const tooltipType = element.getAttribute('data-tooltip');
            const tooltipData = element.getAttribute('data-tooltip-data');

            showTooltip(element, tooltipType, tooltipData);
        }

        function handleTooltipHide(e) {
            if (!e.target.closest('[data-tooltip]')) {
                hideTooltip();
            }
        }

        function handleTooltipMove(e) {
            if (currentTooltip) {
                positionTooltip(currentTooltip, e);
            }
        }

        function showTooltip(element, type, data) {
            hideTooltip(); // Hide any existing tooltip

            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.innerHTML = generateTooltipContent(type, data);

            document.body.appendChild(tooltip);
            currentTooltip = tooltip;

            // Position and show
            setTimeout(() => {
                tooltip.classList.add('show');
            }, 50);
        }

        function hideTooltip() {
            if (currentTooltip) {
                currentTooltip.remove();
                currentTooltip = null;
            }
        }

        function positionTooltip(tooltip, e) {
            const tooltipRect = tooltip.getBoundingClientRect();
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;

            let left = e.clientX + 10;
            let top = e.clientY - tooltipRect.height - 10;

            // Adjust if tooltip would go off screen
            if (left + tooltipRect.width > viewportWidth) {
                left = e.clientX - tooltipRect.width - 10;
            }
            if (top < 0) {
                top = e.clientY + 10;
            }

            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
        }

        function generateTooltipContent(type, rawData) {
            let data;
            try {
                data = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
            } catch {
                data = rawData;
            }

            switch (type) {
                case 'deepseek-status':
                    return `
                        <div class="tooltip-title">DeepSeek Connection Status</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Status:</span>
                            <span class="tooltip-value">${data.available ? 'Connected' : 'Disconnected'}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Response Time:</span>
                            <span class="tooltip-value">${data.response_time?.toFixed(2) || 'N/A'}s</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Models Loaded:</span>
                            <span class="tooltip-value">${data.models_loaded || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Health Status:</span>
                            <span class="tooltip-value">${data.status || 'Unknown'}</span>
                        </div>
                    `;

                case 'active-sessions':
                    return `
                        <div class="tooltip-title">Active Sessions</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Current Count:</span>
                            <span class="tooltip-value">${data}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Definition:</span>
                            <span class="tooltip-value">Sessions with ongoing orchestration</span>
                        </div>
                    `;

                case 'handoffs-today':
                    return `
                        <div class="tooltip-title">Handoffs Today</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Total Count:</span>
                            <span class="tooltip-value">${data}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Definition:</span>
                            <span class="tooltip-value">Model handoffs since midnight</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Includes:</span>
                            <span class="tooltip-value">Claude → DeepSeek transitions</span>
                        </div>
                    `;

                case 'subagents-spawned':
                    return `
                        <div class="tooltip-title">Subagents Spawned</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Today's Count:</span>
                            <span class="tooltip-value">${data}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Definition:</span>
                            <span class="tooltip-value">Specialized agent invocations</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Includes:</span>
                            <span class="tooltip-value">Testing, security, MCP tools</span>
                        </div>
                    `;

                case 'savings-today':
                    return `
                        <div class="tooltip-title">Cost Savings Today</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Amount Saved:</span>
                            <span class="tooltip-value">$${parseFloat(data).toFixed(4)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Source:</span>
                            <span class="tooltip-value">DeepSeek vs Claude pricing</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Calculation:</span>
                            <span class="tooltip-value">$0.015/1k tokens avoided</span>
                        </div>
                    `;

                case 'total-handoffs':
                    return `
                        <div class="tooltip-title">Total Handoffs Breakdown</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">DeepSeek Handoffs:</span>
                            <span class="tooltip-value">${data.deepseek || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Claude Handoffs:</span>
                            <span class="tooltip-value">${data.claude || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Total:</span>
                            <span class="tooltip-value">${data.total || 0}</span>
                        </div>
                    `;

                case 'deepseek-usage':
                    return `
                        <div class="tooltip-title">DeepSeek Usage Analysis</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">DeepSeek:</span>
                            <span class="tooltip-value">${data.deepseek || 0} handoffs</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Claude:</span>
                            <span class="tooltip-value">${data.claude || 0} handoffs</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Optimization:</span>
                            <span class="tooltip-value">${((data.deepseek / Math.max(data.total, 1)) * 100).toFixed(1)}% local routing</span>
                        </div>
                    `;

                case 'handoff-success-rate':
                    return `
                        <div class="tooltip-title">Handoff Success Rate</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Success Rate:</span>
                            <span class="tooltip-value">${(data.success_rate || 0).toFixed(1)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Successful:</span>
                            <span class="tooltip-value">${data.successful || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Failed:</span>
                            <span class="tooltip-value">${data.failed || 0}</span>
                        </div>
                    `;

                case 'avg-confidence':
                    return `
                        <div class="tooltip-title">Confidence Score Range</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Average:</span>
                            <span class="tooltip-value">${(data.avg || 0).toFixed(3)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Minimum:</span>
                            <span class="tooltip-value">${(data.min || 0).toFixed(3)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Maximum:</span>
                            <span class="tooltip-value">${(data.max || 0).toFixed(3)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Scale:</span>
                            <span class="tooltip-value">0.0 - 1.0 (higher = more confident)</span>
                        </div>
                    `;

                case 'unique-agents':
                    return `
                        <div class="tooltip-title">Subagent Diversity Analysis</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Unique Agents:</span>
                            <span class="tooltip-value">${data.unique_agents || 0} different agents</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Coverage:</span>
                            <span class="tooltip-value">${data.total_invocations ? ((data.unique_agents / data.total_invocations) * 100).toFixed(1) : 0}% diversity</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Most Active:</span>
                            <span class="tooltip-value">${data.most_active || 'N/A'}</span>
                        </div>
                    `;

                case 'subagent-invocations':
                    return `
                        <div class="tooltip-title">Subagent Invocation Breakdown</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Total Invocations:</span>
                            <span class="tooltip-value">${data.total || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Success Rate:</span>
                            <span class="tooltip-value">${data.success_rate ? data.success_rate.toFixed(1) : 0}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Avg Duration:</span>
                            <span class="tooltip-value">${data.avg_duration ? data.avg_duration.toFixed(1) : 0}s per invocation</span>
                        </div>
                    `;

                case 'most-used-agent':
                    return `
                        <div class="tooltip-title">Most Active Subagent</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Agent:</span>
                            <span class="tooltip-value">${data.name || 'N/A'}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Invocations:</span>
                            <span class="tooltip-value">${data.count || 0} times</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Success Rate:</span>
                            <span class="tooltip-value">${data.success_rate ? data.success_rate.toFixed(1) : 0}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Specialization:</span>
                            <span class="tooltip-value">${data.specialization || 'General purpose'}</span>
                        </div>
                    `;

                case 'monthly-cost':
                    return `
                        <div class="tooltip-title">Monthly Cost Breakdown</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Claude Usage:</span>
                            <span class="tooltip-value">$${(data.claude_cost || 0).toFixed(2)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">DeepSeek Usage:</span>
                            <span class="tooltip-value">$${(data.deepseek_cost || 0).toFixed(2)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Total:</span>
                            <span class="tooltip-value">$${(data.total || 0).toFixed(2)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">vs Pure Claude:</span>
                            <span class="tooltip-value">$${(data.pure_claude_cost || 0).toFixed(2)}</span>
                        </div>
                    `;

                case 'monthly-savings':
                    return `
                        <div class="tooltip-title">Monthly Savings Analysis</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Total Savings:</span>
                            <span class="tooltip-value">$${(data.total_savings || 0).toFixed(2)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">From DeepSeek:</span>
                            <span class="tooltip-value">$${(data.deepseek_savings || 0).toFixed(2)}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Cost Reduction:</span>
                            <span class="tooltip-value">${(data.reduction_percent || 0).toFixed(1)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">ROI:</span>
                            <span class="tooltip-value">${data.roi || 'Infinite'} (local model)</span>
                        </div>
                    `;

                case 'optimization-rate':
                    return `
                        <div class="tooltip-title">Cost Optimization Performance</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Optimization Rate:</span>
                            <span class="tooltip-value">${(data.rate || 0).toFixed(1)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Target:</span>
                            <span class="tooltip-value">90% DeepSeek usage</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Performance:</span>
                            <span class="tooltip-value">${data.rate >= 90 ? 'Excellent' : data.rate >= 75 ? 'Good' : 'Needs improvement'}</span>
                        </div>
                    `;

                case 'response-time':
                    return `
                        <div class="tooltip-title">Response Time Analysis</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Average:</span>
                            <span class="tooltip-value">${(data.avg || 0).toFixed(2)}s</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">95th Percentile:</span>
                            <span class="tooltip-value">${(data.p95 || 0).toFixed(2)}s</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Target:</span>
                            <span class="tooltip-value"><2.0s</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Status:</span>
                            <span class="tooltip-value">${data.avg <= 2.0 ? 'Meeting target' : 'Above target'}</span>
                        </div>
                    `;

                case 'deepseek-response':
                    return `
                        <div class="tooltip-title">DeepSeek Performance</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Response Time:</span>
                            <span class="tooltip-value">${(data.response_time || 0).toFixed(2)}s</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">vs Claude:</span>
                            <span class="tooltip-value">${data.claude_time ? ((data.response_time / data.claude_time) * 100).toFixed(1) : 'N/A'}% of Claude time</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Availability:</span>
                            <span class="tooltip-value">${data.availability ? data.availability.toFixed(1) : 0}%</span>
                        </div>
                    `;

                case 'system-uptime':
                    return `
                        <div class="tooltip-title">System Availability</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Uptime:</span>
                            <span class="tooltip-value">${(data.uptime || 0).toFixed(2)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Downtime Events:</span>
                            <span class="tooltip-value">${data.downtime_events || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Last Restart:</span>
                            <span class="tooltip-value">${data.last_restart || 'N/A'}</span>
                        </div>
                    `;

                case 'error-rate':
                    return `
                        <div class="tooltip-title">Error Rate Analysis</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Error Rate:</span>
                            <span class="tooltip-value">${(data.rate || 0).toFixed(2)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Total Errors:</span>
                            <span class="tooltip-value">${data.total_errors || 0}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Most Common:</span>
                            <span class="tooltip-value">${data.most_common || 'Connection timeout'}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Target:</span>
                            <span class="tooltip-value"><5.0%</span>
                        </div>
                    `;

                case 'transition-status':
                    return `
                        <div class="tooltip-title">Account Transition Readiness</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Status:</span>
                            <span class="tooltip-value">${data.status || 'Unknown'}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">DeepSeek Usage:</span>
                            <span class="tooltip-value">${(data.deepseek_usage || 0).toFixed(1)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Readiness Score:</span>
                            <span class="tooltip-value">${(data.readiness_score || 0).toFixed(1)}%</span>
                        </div>
                    `;

                case 'effectiveness-score':
                    return `
                        <div class="tooltip-title">Optimization Effectiveness</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Score:</span>
                            <span class="tooltip-value">${(data.score || 0).toFixed(1)}%</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Quality Maintained:</span>
                            <span class="tooltip-value">${data.quality_maintained ? 'Yes' : 'No'}</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Cost Reduction:</span>
                            <span class="tooltip-value">${(data.cost_reduction || 0).toFixed(1)}%</span>
                        </div>
                    `;

                default:
                    return `
                        <div class="tooltip-title">Metric Details</div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Value:</span>
                            <span class="tooltip-value">${data}</span>
                        </div>
                    `;
            }
        }

        async function refreshAll() {
            try {
                await Promise.all([
                    loadSystemStatus(),
                    loadHandoffAnalytics(),
                    loadSubagentAnalytics(),
                    loadCostAnalytics(),
                    loadAccountTransitionAnalysis(),
                    loadPerformanceMetrics(),
                    loadActivityData()
                ]);

                updateLiveIndicator();
            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        async function loadSystemStatus() {
            const response = await fetch('/api/system-status');
            const data = await response.json();

            const statusBar = document.getElementById('statusBar');
            statusBar.innerHTML = `
                <div class="status-item">
                    <span class="status-value ${data.deepseek.available ? 'status-online' : 'status-offline'}"
                          data-tooltip="deepseek-status" data-tooltip-data='${JSON.stringify(data.deepseek).replace(/'/g, "&apos;")}'>
                        ${data.deepseek.available ? 'ONLINE' : 'OFFLINE'}
                    </span>
                    <label>DeepSeek Status</label>
                </div>
                <div class="status-item">
                    <span class="status-value" data-tooltip="active-sessions" data-tooltip-data='${data.active_sessions || 0}'>
                        ${data.active_sessions || 0}
                    </span>
                    <label>Active Sessions</label>
                </div>
                <div class="status-item">
                    <span class="status-value" data-tooltip="handoffs-today" data-tooltip-data='${data.handoffs_today || 0}'>
                        ${data.handoffs_today || 0}
                    </span>
                    <label>Handoffs Today</label>
                </div>
                <div class="status-item">
                    <span class="status-value" data-tooltip="subagents-spawned" data-tooltip-data='${data.subagents_spawned || 0}'>
                        ${data.subagents_spawned || 0}
                    </span>
                    <label>Subagents Spawned</label>
                </div>
                <div class="status-item">
                    <span class="status-value status-online" data-tooltip="savings-today"
                          data-tooltip-data='${(data.savings_today || 0).toFixed(4)}'>
                        $${(data.savings_today || 0).toFixed(2)}
                    </span>
                    <label>Savings Today</label>
                </div>
            `;
        }

        async function loadHandoffAnalytics() {
            const response = await fetch('/api/handoff-analytics');
            const data = await response.json();

            const metrics = document.getElementById('handoffMetrics');
            const handoffBreakdown = {
                total: data.total_handoffs || 0,
                deepseek: data.deepseek_handoffs || 0,
                claude: data.claude_handoffs || 0
            };
            const successBreakdown = {
                success_rate: data.success_rate || 0,
                successful: data.successful_handoffs || 0,
                failed: data.failed_handoffs || 0
            };
            const confidenceBreakdown = {
                avg: data.avg_confidence || 0,
                min: data.min_confidence || 0,
                max: data.max_confidence || 1.0
            };

            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Total Handoffs</span>
                    <span class="metric-value" data-tooltip="total-handoffs"
                          data-tooltip-data='${JSON.stringify(handoffBreakdown).replace(/'/g, "&apos;")}'>
                        ${data.total_handoffs || 0}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">DeepSeek Usage</span>
                    <span class="metric-value model-deepseek" data-tooltip="deepseek-usage"
                          data-tooltip-data='${JSON.stringify(handoffBreakdown).replace(/'/g, "&apos;")}'>
                        ${((data.deepseek_handoffs / Math.max(data.total_handoffs, 1)) * 100).toFixed(1)}%
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Success Rate</span>
                    <span class="metric-value success" data-tooltip="handoff-success-rate"
                          data-tooltip-data='${JSON.stringify(successBreakdown).replace(/'/g, "&apos;")}'>
                        ${(data.success_rate || 0).toFixed(1)}%
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Confidence</span>
                    <span class="metric-value" data-tooltip="avg-confidence"
                          data-tooltip-data='${JSON.stringify(confidenceBreakdown).replace(/'/g, "&apos;")}'>
                        ${(data.avg_confidence || 0).toFixed(2)}
                    </span>
                </div>
            `;

            // Update handoff chart
            updateHandoffChart(data);
        }

        async function loadSubagentAnalytics() {
            const response = await fetch('/api/subagent-analytics');
            const data = await response.json();

            const metrics = document.getElementById('subagentMetrics');
            const topAgent = data.usage_statistics?.[0];

            const uniqueAgentData = {
                unique_agents: data.patterns?.unique_agents_used || 0,
                total_invocations: data.patterns?.total_invocations || 0,
                most_active: topAgent?.agent_name || 'N/A'
            };

            const invocationData = {
                total: data.patterns?.total_invocations || 0,
                success_rate: data.patterns?.overall_success_rate || 0,
                avg_duration: data.patterns?.avg_execution_time || 0
            };

            const mostUsedAgentData = {
                name: topAgent?.agent_name || 'N/A',
                count: topAgent?.count || 0,
                success_rate: topAgent?.success_rate || 0,
                specialization: topAgent?.specialization || 'General purpose'
            };

            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Unique Agents Used</span>
                    <span class="metric-value" data-tooltip="unique-agents"
                          data-tooltip-data='${JSON.stringify(uniqueAgentData).replace(/'/g, "&apos;")}'>
                        ${data.patterns?.unique_agents_used || 0}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Invocations</span>
                    <span class="metric-value" data-tooltip="subagent-invocations"
                          data-tooltip-data='${JSON.stringify(invocationData).replace(/'/g, "&apos;")}'>
                        ${data.patterns?.total_invocations || 0}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Most Used Agent</span>
                    <span class="metric-value" data-tooltip="most-used-agent"
                          data-tooltip-data='${JSON.stringify(mostUsedAgentData).replace(/'/g, "&apos;")}'>
                        ${topAgent?.agent_name || 'None'}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Success Rate</span>
                    <span class="metric-value success" data-tooltip="most-used-agent"
                          data-tooltip-data='${JSON.stringify(mostUsedAgentData).replace(/'/g, "&apos;")}'>
                        ${topAgent ? topAgent.success_rate.toFixed(1) : 0}%
                    </span>
                </div>
            `;

            // Update subagent chart
            updateSubagentChart(data);
        }

        async function loadCostAnalytics() {
            const response = await fetch('/api/cost-analytics');
            const data = await response.json();

            const metrics = document.getElementById('costMetrics');

            const costBreakdown = {
                total: data.monthly_cost || 0,
                claude_cost: data.claude_cost || 0,
                deepseek_cost: data.deepseek_cost || 0,
                pure_claude_cost: data.pure_claude_cost || (data.monthly_cost + data.monthly_savings) || 0
            };

            const savingsBreakdown = {
                total_savings: data.monthly_savings || 0,
                deepseek_savings: data.deepseek_savings || data.monthly_savings || 0,
                reduction_percent: data.cost_reduction_percent || 0,
                roi: 'Infinite'
            };

            const optimizationData = {
                rate: data.optimization_rate || 0
            };

            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Monthly Cost</span>
                    <span class="metric-value" data-tooltip="monthly-cost"
                          data-tooltip-data='${JSON.stringify(costBreakdown).replace(/'/g, "&apos;")}'>
                        $${(data.monthly_cost || 0).toFixed(2)}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Monthly Savings</span>
                    <span class="metric-value status-online" data-tooltip="monthly-savings"
                          data-tooltip-data='${JSON.stringify(savingsBreakdown).replace(/'/g, "&apos;")}'>
                        $${(data.monthly_savings || 0).toFixed(2)}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Optimization Rate</span>
                    <span class="metric-value" data-tooltip="optimization-rate"
                          data-tooltip-data='${JSON.stringify(optimizationData).replace(/'/g, "&apos;")}'>
                        ${(data.optimization_rate || 0).toFixed(1)}%
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Projected Annual</span>
                    <span class="metric-value status-online" data-tooltip="monthly-savings"
                          data-tooltip-data='${JSON.stringify({...savingsBreakdown, annual_savings: (data.monthly_savings || 0) * 12}).replace(/'/g, "&apos;")}'>
                        $${((data.monthly_savings || 0) * 12).toFixed(0)}
                    </span>
                </div>
            `;

            // Update cost chart
            updateCostChart(data);
        }

        async function loadPerformanceMetrics() {
            const response = await fetch('/api/performance-metrics');
            const data = await response.json();

            const metrics = document.getElementById('performanceMetrics');

            const responseTimeData = {
                avg: data.avg_response_time || 0,
                p95: data.p95_response_time || 0
            };

            const deepseekResponseData = {
                response_time: data.deepseek_response_time || 0,
                claude_time: data.claude_response_time || 0,
                availability: data.deepseek_availability || 0
            };

            const uptimeData = {
                uptime: data.uptime || 0,
                downtime_events: data.downtime_events || 0,
                last_restart: data.last_restart || 'N/A'
            };

            const errorData = {
                rate: data.error_rate || 0,
                total_errors: data.total_errors || 0,
                most_common: data.most_common_error || 'Connection timeout'
            };

            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Avg Response Time</span>
                    <span class="metric-value" data-tooltip="response-time"
                          data-tooltip-data='${JSON.stringify(responseTimeData).replace(/'/g, "&apos;")}'>
                        ${(data.avg_response_time || 0).toFixed(2)}s
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">DeepSeek Response</span>
                    <span class="metric-value" data-tooltip="deepseek-response"
                          data-tooltip-data='${JSON.stringify(deepseekResponseData).replace(/'/g, "&apos;")}'>
                        ${(data.deepseek_response_time || 0).toFixed(2)}s
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">System Uptime</span>
                    <span class="metric-value success" data-tooltip="system-uptime"
                          data-tooltip-data='${JSON.stringify(uptimeData).replace(/'/g, "&apos;")}'>
                        ${(data.uptime || 0).toFixed(1)}%
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Error Rate</span>
                    <span class="metric-value ${data.error_rate > 5 ? 'error' : 'success'}" data-tooltip="error-rate"
                          data-tooltip-data='${JSON.stringify(errorData).replace(/'/g, "&apos;")}'>
                        ${(data.error_rate || 0).toFixed(1)}%
                    </span>
                </div>
            `;
        }

        async function loadAccountTransitionAnalysis() {
            try {
                const response = await fetch('/api/account-transition-analysis');
                const data = await response.json();

                if (data.transition_projection) {
                    const projection = data.transition_projection;
                    const metrics = document.getElementById('accountTransitionMetrics');

                    // Status color based on readiness
                    const readinessColor = projection.transition_readiness === 'ready' ? '#10B981' :
                                         projection.transition_readiness === 'approaching' ? '#F59E0B' : '#EF4444';

                    const transitionStatusData = {
                        status: projection.transition_readiness,
                        deepseek_usage: projection.deepseek_utilization_ratio * 100,
                        readiness_score: projection.effectiveness_score * 100
                    };

                    const effectivenessData = {
                        score: projection.effectiveness_score * 100,
                        quality_maintained: projection.quality_maintained || true,
                        cost_reduction: projection.cost_reduction_percent || 0
                    };

                    const savingsProjectionData = {
                        monthly_savings: projection.potential_monthly_savings,
                        annual_savings: projection.potential_monthly_savings * 12,
                        current_usage: projection.deepseek_utilization_ratio * 100,
                        target_usage: 90
                    };

                    metrics.innerHTML = `
                        <div class="metric">
                            <span class="metric-label">Transition Status</span>
                            <span class="metric-value" style="color: ${readinessColor}" data-tooltip="transition-status"
                                  data-tooltip-data='${JSON.stringify(transitionStatusData).replace(/'/g, "&apos;")}'>
                                ${projection.transition_readiness.toUpperCase()}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">DeepSeek Utilization</span>
                            <span class="metric-value" data-tooltip="transition-status"
                                  data-tooltip-data='${JSON.stringify(transitionStatusData).replace(/'/g, "&apos;")}'>
                                ${(projection.deepseek_utilization_ratio * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Effectiveness Score</span>
                            <span class="metric-value success" data-tooltip="effectiveness-score"
                                  data-tooltip-data='${JSON.stringify(effectivenessData).replace(/'/g, "&apos;")}'>
                                ${(projection.effectiveness_score * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Potential Monthly Savings</span>
                            <span class="metric-value success" data-tooltip="monthly-savings"
                                  data-tooltip-data='${JSON.stringify(savingsProjectionData).replace(/'/g, "&apos;")}'>
                                $${projection.potential_monthly_savings.toFixed(0)}
                            </span>
                        </div>
                        <div class="recommendation-box" style="margin-top: 15px; padding: 12px; background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10B981; border-radius: 4px;">
                            <strong>Recommendation:</strong><br>
                            <span style="font-size: 13px;">${projection.recommendation}</span>
                        </div>
                    `;

                    // Create transition projection chart
                    updateTransitionChart(projection);
                }
            } catch (error) {
                console.error('Error loading account transition analysis:', error);
                const metrics = document.getElementById('accountTransitionMetrics');
                metrics.innerHTML = '<div class="error">Error loading transition analysis</div>';
            }
        }

        function updateTransitionChart(projection) {
            const ctx = document.getElementById('transitionChart').getContext('2d');

            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['DeepSeek Usage', 'Claude Usage'],
                    datasets: [{
                        data: [
                            projection.deepseek_utilization_ratio * 100,
                            (1 - projection.deepseek_utilization_ratio) * 100
                        ],
                        backgroundColor: ['#10B981', '#667eea'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Current Usage Distribution',
                            font: { size: 14, weight: 'bold' }
                        },
                        legend: {
                            position: 'bottom',
                            labels: { padding: 20, usePointStyle: true }
                        }
                    }
                }
            });
        }

        async function loadRecentActivity(page = 1) {
            try {
                const response = await fetch(`/api/recent-activity?page=${page}&limit=50`);
                const data = await response.json();

                if (data.status === 'success') {
                    currentActivityPage = page;
                    activityPagination = data.pagination;

                    const tbody = document.getElementById('activityBody');
                    tbody.innerHTML = data.activities.map(activity => `
                        <tr>
                            <td>${new Date(activity.timestamp).toLocaleTimeString()}</td>
                            <td>${activity.session_id?.substring(0, 8) || 'N/A'}</td>
                            <td>${activity.event_type}</td>
                            <td class="model-${activity.model_or_agent?.toLowerCase() || ''}">${activity.model_or_agent || 'Unknown'}</td>
                            <td>${activity.description?.substring(0, 50) || ''}${activity.description?.length > 50 ? '...' : ''}</td>
                            <td class="${activity.status}">${activity.status}</td>
                            <td>$${(activity.cost || 0).toFixed(3)}</td>
                        </tr>
                    `).join('');

                    // Update pagination info
                    updateActivityPagination();
                } else {
                    console.error('Error loading recent activity:', data.error);
                    const tbody = document.getElementById('activityBody');
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #ff6b6b;">Error loading activity data</td></tr>';
                }
            } catch (error) {
                console.error('Error fetching recent activity:', error);
                const tbody = document.getElementById('activityBody');
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #ff6b6b;">Error loading activity data</td></tr>';
            }
        }

        function updateActivityPagination() {
            if (!activityPagination) return;

            const paginationInfo = document.getElementById('paginationInfo');
            const pageInfo = document.getElementById('pageInfo');
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');

            // Update info text
            const start = ((currentActivityPage - 1) * 50) + 1;
            const end = Math.min(currentActivityPage * 50, activityPagination.total_count);
            paginationInfo.textContent = `Showing ${start}-${end} of ${activityPagination.total_count} activities`;

            // Update page info
            pageInfo.textContent = `Page ${currentActivityPage} of ${activityPagination.total_pages}`;

            // Update button states
            prevBtn.disabled = !activityPagination.has_previous;
            nextBtn.disabled = !activityPagination.has_next;
        }

        function loadActivityPage(direction) {
            if (isProjectView) {
                if (!projectPagination) return;
                let newPage = currentProjectPage;
                if (direction === 'next' && projectPagination.has_next) {
                    newPage = currentProjectPage + 1;
                } else if (direction === 'prev' && projectPagination.has_previous) {
                    newPage = currentProjectPage - 1;
                }
                if (newPage !== currentProjectPage) {
                    loadProjectGroupedActivity(newPage);
                }
            } else {
                if (!activityPagination) return;
                let newPage = currentActivityPage;
                if (direction === 'next' && activityPagination.has_next) {
                    newPage = currentActivityPage + 1;
                } else if (direction === 'prev' && activityPagination.has_previous) {
                    newPage = currentActivityPage - 1;
                }
                if (newPage !== currentActivityPage) {
                    loadRecentActivity(newPage);
                }
            }
        }

        // New activity management functions
        async function loadActivityData() {
            if (isProjectView) {
                await loadProjectGroupedActivity();
            } else {
                await loadRecentActivity();
            }
        }

        async function loadProjectGroupedActivity(page = 1) {
            try {
                const response = await fetch(`/api/project-grouped-activity?page=${page}&limit=10`);
                const data = await response.json();

                if (data.status === 'success') {
                    currentProjectPage = page;
                    projectPagination = data.pagination;

                    const container = document.getElementById('projectGroupedView');
                    container.innerHTML = data.projects.map(project => `
                        <div class="project-card">
                            <div class="project-header" onclick="toggleProject('${project.project_name}')">
                                <div class="project-info">
                                    <h4 class="project-name">${project.project_name}</h4>
                                    <div class="project-stats">
                                        ${project.session_count} sessions •
                                        ${project.total_handoffs} handoffs •
                                        ${project.total_subagents} subagents •
                                        ${project.success_rate}% success •
                                        $${project.total_cost} total cost
                                        <br>
                                        <small>${formatDateRange(project.earliest_session, project.latest_session)}</small>
                                    </div>
                                </div>
                                <div class="project-expand-icon" id="icon-${project.project_name}">▼</div>
                            </div>
                            <div class="project-activities" id="activities-${project.project_name}">
                                ${renderProjectActivities(project)}
                            </div>
                        </div>
                    `).join('');

                    updatePagination();
                } else {
                    console.error('Error loading project activity:', data.error);
                    const container = document.getElementById('projectGroupedView');
                    container.innerHTML = '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error loading project activity data</div>';
                }
            } catch (error) {
                console.error('Error fetching project activity:', error);
                const container = document.getElementById('projectGroupedView');
                container.innerHTML = '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error loading project activity data</div>';
            }
        }

        function renderProjectActivities(project) {
            let html = '';

            // Handoffs section
            if (project.handoffs && project.handoffs.length > 0) {
                html += `
                    <div class="activity-group">
                        <div class="activity-group-title">Model Handoffs (${project.handoffs.length})</div>
                        ${project.handoffs.map(handoff => `
                            <div class="activity-item handoff">
                                <div class="activity-details">
                                    <div class="activity-meta">
                                        ${new Date(handoff.timestamp).toLocaleString()} •
                                        Session: ${handoff.session_id?.substring(0, 8)} •
                                        Confidence: ${(handoff.confidence_score || 0).toFixed(2)}
                                    </div>
                                    <div class="activity-description">${handoff.task_description}</div>
                                </div>
                                <div style="display: flex; align-items: center;">
                                    <span class="activity-badge ${handoff.status}">${handoff.status}</span>
                                    <span class="activity-cost">$${(handoff.cost || 0).toFixed(3)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            // Subagents section
            if (project.subagents && project.subagents.length > 0) {
                html += `
                    <div class="activity-group">
                        <div class="activity-group-title">Subagent Invocations (${project.subagents.length})</div>
                        ${project.subagents.map(subagent => `
                            <div class="activity-item subagent">
                                <div class="activity-details">
                                    <div class="activity-meta">
                                        ${new Date(subagent.timestamp).toLocaleString()} •
                                        Session: ${subagent.session_id?.substring(0, 8)} •
                                        Agent: ${subagent.agent_name}
                                        ${subagent.execution_time ? ` • ${subagent.execution_time.toFixed(1)}s` : ''}
                                    </div>
                                    <div class="activity-description">${subagent.task_description}</div>
                                </div>
                                <div style="display: flex; align-items: center;">
                                    <span class="activity-badge ${subagent.status}">${subagent.status}</span>
                                    <span class="activity-cost">$${(subagent.cost || 0).toFixed(3)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            if (!html) {
                html = '<div style="text-align: center; color: #718096; padding: 20px;">No handoffs or subagent activities found for this project.</div>';
            }

            return html;
        }

        function formatDateRange(earliest, latest) {
            const early = new Date(earliest);
            const late = new Date(latest);

            if (early.toDateString() === late.toDateString()) {
                return `${early.toLocaleDateString()}`;
            } else {
                return `${early.toLocaleDateString()} - ${late.toLocaleDateString()}`;
            }
        }

        function toggleProject(projectName) {
            const activities = document.getElementById(`activities-${projectName}`);
            const icon = document.getElementById(`icon-${projectName}`);
            const header = activities.previousElementSibling;

            if (activities.classList.contains('expanded')) {
                activities.classList.remove('expanded');
                icon.classList.remove('expanded');
                header.classList.remove('expanded');
            } else {
                activities.classList.add('expanded');
                icon.classList.add('expanded');
                header.classList.add('expanded');
            }
        }

        function toggleActivityView() {
            const toggleBtn = document.getElementById('toggleViewBtn');
            const projectView = document.getElementById('projectGroupedView');
            const flatView = document.getElementById('flatActivityView');

            if (isProjectView) {
                // Switch to flat view
                projectView.style.display = 'none';
                flatView.style.display = 'block';
                toggleBtn.textContent = 'Switch to Project View';
                isProjectView = false;
                loadRecentActivity(1);
            } else {
                // Switch to project view
                flatView.style.display = 'none';
                projectView.style.display = 'block';
                toggleBtn.textContent = 'Switch to Flat View';
                isProjectView = true;
                loadProjectGroupedActivity(1);
            }
        }

        function updatePagination() {
            if (isProjectView && projectPagination) {
                updateProjectPagination();
            } else if (!isProjectView && activityPagination) {
                updateActivityPagination();
            }
        }

        function updateProjectPagination() {
            const paginationInfo = document.getElementById('paginationInfo');
            const pageInfo = document.getElementById('pageInfo');
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');

            // Update info text
            const start = ((currentProjectPage - 1) * 10) + 1;
            const end = Math.min(currentProjectPage * 10, projectPagination.total_count);
            paginationInfo.textContent = `Showing ${start}-${end} of ${projectPagination.total_count} projects`;

            // Update page info
            pageInfo.textContent = `Page ${currentProjectPage} of ${projectPagination.total_pages}`;

            // Update buttons
            prevBtn.disabled = !projectPagination.has_previous;
            nextBtn.disabled = !projectPagination.has_next;
        }

        function updateHandoffChart(data) {
            const ctx = document.getElementById('handoffChart').getContext('2d');

            if (charts.handoff) {
                charts.handoff.destroy();
            }

            charts.handoff = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['DeepSeek', 'Claude'],
                    datasets: [{
                        data: [data.deepseek_handoffs || 0, data.claude_handoffs || 0],
                        backgroundColor: ['#22c55e', '#3b82f6'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        function updateSubagentChart(data) {
            const ctx = document.getElementById('subagentChart').getContext('2d');

            if (charts.subagent) {
                charts.subagent.destroy();
            }

            const agents = data.usage_statistics?.slice(0, 5) || [];

            charts.subagent = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: agents.map(a => a.agent_name?.replace(/-/g, ' ') || 'Unknown'),
                    datasets: [{
                        label: 'Invocations',
                        data: agents.map(a => a.invocation_count || 0),
                        backgroundColor: '#667eea',
                        borderColor: '#764ba2',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        function updateCostChart(data) {
            const ctx = document.getElementById('costChart').getContext('2d');

            if (charts.cost) {
                charts.cost.destroy();
            }

            charts.cost = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.daily_data?.map(d => new Date(d.date).toLocaleDateString()) || [],
                    datasets: [{
                        label: 'Cost',
                        data: data.daily_data?.map(d => d.cost) || [],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true
                    }, {
                        label: 'Savings',
                        data: data.daily_data?.map(d => d.savings) || [],
                        borderColor: '#22c55e',
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        function toggleAutoRefresh() {
            const toggle = document.getElementById('autoRefreshToggle');
            const indicator = document.getElementById('liveIndicator');

            isAutoRefresh = !isAutoRefresh;

            if (isAutoRefresh) {
                toggle.classList.add('active');
                indicator.style.display = 'inline-block';
                autoRefreshInterval = setInterval(refreshAll, 30000); // 30 seconds
            } else {
                toggle.classList.remove('active');
                indicator.style.display = 'none';
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                }
            }
        }

        function updateLiveIndicator() {
            const indicator = document.getElementById('liveIndicator');
            if (isAutoRefresh) {
                indicator.style.animation = 'none';
                setTimeout(() => {
                    indicator.style.animation = 'pulse 2s infinite';
                }, 10);
            }
        }
    </script>
</body>
</html>
    """
    return template

# API Endpoints
@app.route("/api/system-status")
async def system_status():
    """Get current system status"""
    deepseek_health = deepseek_client.get_health_status()

    # Get today's metrics
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    handoff_analytics = db.get_handoff_analytics(today_start.isoformat(), today_end.isoformat())

    return jsonify({
        'deepseek': deepseek_health,
        'active_sessions': 0,  # TODO: Implement active session counting
        'handoffs_today': handoff_analytics.get('total_handoffs', 0),
        'subagents_spawned': 0,  # TODO: Implement subagent counting
        'savings_today': handoff_analytics.get('total_savings', 0)
    })

@app.route("/api/handoff-analytics")
async def handoff_analytics():
    """Get handoff analytics data"""
    analytics = db.get_handoff_analytics()
    return jsonify(analytics)

@app.route("/api/subagent-analytics")
async def subagent_analytics():
    """Get subagent usage analytics"""
    analytics = subagent_tracker.get_agent_usage_analytics()
    return jsonify(analytics)

@app.route("/api/cost-analytics")
async def cost_analytics():
    """Get cost optimization analytics"""
    # Placeholder implementation
    return jsonify({
        'monthly_cost': 15.50,
        'monthly_savings': 185.20,
        'optimization_rate': 92.3,
        'daily_data': [
            {'date': '2025-01-13', 'cost': 0.85, 'savings': 8.20},
            {'date': '2025-01-14', 'cost': 1.20, 'savings': 12.50},
            {'date': '2025-01-15', 'cost': 0.95, 'savings': 15.80}
        ]
    })

@app.route("/api/performance-metrics")
async def performance_metrics():
    """Get system performance metrics"""
    deepseek_health = deepseek_client.get_health_status()

    return jsonify({
        'avg_response_time': 1.8,
        'deepseek_response_time': deepseek_health.get('response_time', 0),
        'uptime': 99.2,
        'error_rate': 2.1
    })

@app.route("/api/recent-activity")
async def recent_activity():
    """Get recent orchestration activity with pagination"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit

        # Get paginated activity data from database
        activity_data = db.get_recent_activity(limit=limit, offset=offset)

        return jsonify({
            'activities': activity_data['activities'],
            'pagination': activity_data['pagination'],
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/project-grouped-activity")
async def project_grouped_activity():
    """Get activity grouped by project with expandable details"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit

        # Get project-grouped activity data from database
        project_data = db.get_project_grouped_activity(limit=limit, offset=offset)

        return jsonify({
            'projects': project_data['projects'],
            'pagination': project_data['pagination'],
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error fetching project-grouped activity: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/account-transition-analysis")
async def account_transition_analysis():
    """Get Max-to-Pro account transition analysis"""
    try:
        # Get transition projection
        projection = db.get_account_transition_projection()

        # Get recent account analysis data
        recent_analysis = db.get_claude_account_analysis(period_type='daily', limit=30)

        return jsonify({
            'transition_projection': projection,
            'historical_analysis': recent_analysis,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Error getting account transition analysis: {e}")
        return jsonify({'error': str(e)}), 500

# Track new session endpoint
@app.route("/api/track/session", methods=['POST'])
async def track_session():
    """Track new orchestration session"""
    data = await request.get_json()

    session_id = db.create_session(
        session_id=data['session_id'],
        project_name=data.get('project_name'),
        task_description=data.get('task_description'),
        metadata=data.get('metadata')
    )

    return jsonify({'session_id': session_id, 'status': 'success'})

# Track handoff endpoint
@app.route("/api/track/handoff", methods=['POST'])
async def track_handoff():
    """Track model handoff event"""
    data = await request.get_json()

    handoff_id = handoff_monitor.track_handoff(
        session_id=data['session_id'],
        task_description=data['task_description'],
        task_type=data.get('task_type', 'general'),
        decision=None,  # Would be provided if decision was made
        actual_model=data.get('actual_model')
    )

    return jsonify({'handoff_id': handoff_id, 'status': 'success'})

# Track subagent endpoint
@app.route("/api/track/subagent", methods=['POST'])
async def track_subagent():
    """Track subagent invocation"""
    data = await request.get_json()

    invocation_id = subagent_tracker.track_invocation(
        session_id=data['session_id'],
        invocation=data['invocation'],  # SubagentInvocation object
        parent_agent=data.get('parent_agent')
    )

    return jsonify({'invocation_id': invocation_id, 'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)