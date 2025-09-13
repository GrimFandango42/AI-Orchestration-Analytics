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
from datetime import datetime, timedelta
from typing import Dict, List, Any

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

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
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
            <h3 class="card-title">Recent Orchestration Activity</h3>
            <div class="table-container">
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
        </div>
    </div>

    <script>
        let charts = {};
        let autoRefreshInterval = null;
        let isAutoRefresh = false;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            refreshAll();
        });

        async function refreshAll() {
            try {
                await Promise.all([
                    loadSystemStatus(),
                    loadHandoffAnalytics(),
                    loadSubagentAnalytics(),
                    loadCostAnalytics(),
                    loadPerformanceMetrics(),
                    loadRecentActivity()
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
                    <span class="status-value ${data.deepseek.available ? 'status-online' : 'status-offline'}">
                        ${data.deepseek.available ? 'ONLINE' : 'OFFLINE'}
                    </span>
                    <label>DeepSeek Status</label>
                </div>
                <div class="status-item">
                    <span class="status-value">${data.active_sessions || 0}</span>
                    <label>Active Sessions</label>
                </div>
                <div class="status-item">
                    <span class="status-value">${data.handoffs_today || 0}</span>
                    <label>Handoffs Today</label>
                </div>
                <div class="status-item">
                    <span class="status-value">${data.subagents_spawned || 0}</span>
                    <label>Subagents Spawned</label>
                </div>
                <div class="status-item">
                    <span class="status-value status-online">$${(data.savings_today || 0).toFixed(2)}</span>
                    <label>Savings Today</label>
                </div>
            `;
        }

        async function loadHandoffAnalytics() {
            const response = await fetch('/api/handoff-analytics');
            const data = await response.json();

            const metrics = document.getElementById('handoffMetrics');
            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Total Handoffs</span>
                    <span class="metric-value">${data.total_handoffs || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">DeepSeek Usage</span>
                    <span class="metric-value model-deepseek">${((data.deepseek_handoffs / Math.max(data.total_handoffs, 1)) * 100).toFixed(1)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Success Rate</span>
                    <span class="metric-value success">${(data.success_rate || 0).toFixed(1)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Confidence</span>
                    <span class="metric-value">${(data.avg_confidence || 0).toFixed(2)}</span>
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

            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Unique Agents Used</span>
                    <span class="metric-value">${data.patterns?.unique_agents_used || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Invocations</span>
                    <span class="metric-value">${data.patterns?.total_invocations || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Most Used Agent</span>
                    <span class="metric-value">${topAgent?.agent_name || 'None'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Success Rate</span>
                    <span class="metric-value success">${topAgent ? topAgent.success_rate.toFixed(1) : 0}%</span>
                </div>
            `;

            // Update subagent chart
            updateSubagentChart(data);
        }

        async function loadCostAnalytics() {
            const response = await fetch('/api/cost-analytics');
            const data = await response.json();

            const metrics = document.getElementById('costMetrics');
            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Monthly Cost</span>
                    <span class="metric-value">$${(data.monthly_cost || 0).toFixed(2)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Monthly Savings</span>
                    <span class="metric-value status-online">$${(data.monthly_savings || 0).toFixed(2)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Optimization Rate</span>
                    <span class="metric-value">${(data.optimization_rate || 0).toFixed(1)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Projected Annual</span>
                    <span class="metric-value status-online">$${((data.monthly_savings || 0) * 12).toFixed(0)}</span>
                </div>
            `;

            // Update cost chart
            updateCostChart(data);
        }

        async function loadPerformanceMetrics() {
            const response = await fetch('/api/performance-metrics');
            const data = await response.json();

            const metrics = document.getElementById('performanceMetrics');
            metrics.innerHTML = `
                <div class="metric">
                    <span class="metric-label">Avg Response Time</span>
                    <span class="metric-value">${(data.avg_response_time || 0).toFixed(2)}s</span>
                </div>
                <div class="metric">
                    <span class="metric-label">DeepSeek Response</span>
                    <span class="metric-value">${(data.deepseek_response_time || 0).toFixed(2)}s</span>
                </div>
                <div class="metric">
                    <span class="metric-label">System Uptime</span>
                    <span class="metric-value success">${(data.uptime || 0).toFixed(1)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Error Rate</span>
                    <span class="metric-value ${data.error_rate > 5 ? 'error' : 'success'}">${(data.error_rate || 0).toFixed(1)}%</span>
                </div>
            `;
        }

        async function loadRecentActivity() {
            const response = await fetch('/api/recent-activity');
            const data = await response.json();

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
    """Get recent orchestration activity"""
    # Mock data for now - would be replaced with real database queries
    activities = [
        {
            'timestamp': datetime.now().isoformat(),
            'session_id': 'sess_12345',
            'event_type': 'handoff',
            'model_or_agent': 'deepseek',
            'description': 'Code implementation task routed to DeepSeek',
            'status': 'success',
            'cost': 0.0
        },
        {
            'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
            'session_id': 'sess_12344',
            'event_type': 'subagent',
            'model_or_agent': 'api-testing-specialist',
            'description': 'API testing specialist invoked',
            'status': 'success',
            'cost': 0.025
        }
    ]

    return jsonify({'activities': activities})

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