@echo off
REM AI Orchestration Analytics - Development Mode with Hot Reload
REM ============================================================

title AI Orchestration Analytics - Development Mode

echo.
echo ============================================================
echo AI ORCHESTRATION ANALYTICS - DEVELOPMENT MODE
echo ============================================================
echo Hot reload system will automatically restart server on changes
echo Dashboard: http://localhost:8000
echo Press Ctrl+C to stop
echo ============================================================
echo.

REM Change to project directory
cd /d "%~dp0.."

REM Install development dependencies if needed
python -m pip install watchdog psutil --quiet

REM Start hot reload system
python src/development/hot_reload.py

echo.
echo Development session ended.
pause