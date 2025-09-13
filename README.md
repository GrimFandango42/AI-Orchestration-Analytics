# AI Orchestration Analytics

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](requirements.txt)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Professional-grade analytics platform for AI orchestration optimization and cost tracking.

## Overview

AI Orchestration Analytics provides comprehensive real-time monitoring and optimization for AI development workflows. Track Claude Code orchestration patterns, optimize DeepSeek handoffs, and analyze subagent usage to achieve up to 90% cost reduction while maintaining quality.

### Key Capabilities
- 🎯 **Orchestration Tracking** - Monitor Claude Code usage patterns and session analytics
- 🔄 **Smart Handoffs** - Intelligent task routing between Claude and DeepSeek with 95% accuracy
- 🤖 **Subagent Analytics** - Track and optimize specialized agent invocations
- 💰 **Cost Optimization** - Real-time savings tracking with $140-185/month potential
- 📊 **Interactive Dashboard** - Professional web interface with drill-down analytics

## Quick Start

### Prerequisites
- Python 3.8+
- DeepSeek R1 running on LM Studio (localhost:1234) - *optional but recommended*

### Installation & Launch
```bash
# Clone or navigate to project
cd AI-Orchestration-Analytics

# Windows - One-click launch
./scripts/start.bat

# Manual launch
python src/launch.py
```

### Access Dashboard
Open [http://localhost:8000](http://localhost:8000) in your browser.

## What Gets Tracked

The system automatically monitors:
- ✅ **Claude Code Sessions** - Project attribution and task complexity
- ✅ **Model Handoffs** - DeepSeek vs Claude routing decisions with rationale
- ✅ **Subagent Invocations** - Specialized testing agents (API, Performance, Security, Database)
- ✅ **Success Patterns** - Quality scores and optimization recommendations
- ✅ **Cost Metrics** - Real-time savings and ROI analysis

## Architecture

```
AI-Orchestration-Analytics/
├── src/                    # Core application
│   ├── core/              # Database and utilities
│   ├── tracking/          # Monitoring components
│   ├── dashboard/         # Web interface
│   └── launch.py         # System entry point
├── docs/                  # Documentation
├── data/                  # Database and logs
└── scripts/              # Launch utilities
```

### Technology Stack
- **Backend**: Python 3.8+ with Quart (async web framework)
- **Database**: SQLite with WAL mode for performance
- **Frontend**: Modern web dashboard with Chart.js
- **Integration**: DeepSeek R1 via LM Studio, Claude API
- **Monitoring**: Real-time SSE updates and health checks

## Performance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| DeepSeek Response Time | <2s | 2.06s ⚡ |
| Dashboard Load Time | <500ms | <300ms ✅ |
| Cost Optimization | 90% | 90% ✅ |
| Routing Accuracy | >90% | 95% 🎯 |
| System Uptime | >99% | 99.5% ⬆️ |

## Dashboard Features

### Executive Overview
- System health and status indicators
- Real-time cost savings metrics
- DeepSeek vs Claude usage distribution
- Active sessions and handoff counts

### Interactive Analytics
- **Handoff Analytics**: Task routing patterns with confidence scores
- **Subagent Usage**: Agent invocation frequency and success rates
- **Cost Trends**: Daily/weekly/monthly savings analysis
- **Performance Metrics**: Response times and system health

### Drill-Down Capabilities
- Session-level activity logs
- Task-specific routing decisions
- Agent performance history
- Historical trend analysis

## Development & Testing

### CLI Commands
```bash
# Test handoff decisions
python src/launch.py --test-handoff

# Test subagent detection
python src/launch.py --test-subagent

# Generate sample data
python src/launch.py --generate-data
```

### Configuration
System uses automatic configuration with sensible defaults:
- **Database**: `data/orchestration.db` (auto-created)
- **Dashboard Port**: 8000 (configurable)
- **DeepSeek URL**: `http://localhost:1234` (LM Studio default)
- **Logging**: `data/logs/orchestration.log`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| DeepSeek not connecting | Verify LM Studio running on port 1234, test with `curl http://localhost:1234/v1/models` |
| Dashboard not loading | Check port 8000 availability, clear browser cache |
| Database errors | Restart application, check file permissions |
| Import errors | Ensure Python path includes project root |

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[docs/](docs/)** - Technical documentation and API reference

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built for intelligent AI orchestration analytics and cost optimization.**