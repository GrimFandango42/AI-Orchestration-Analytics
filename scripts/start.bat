@echo off
echo =====================================
echo AI Orchestration Analytics Launcher
echo =====================================

cd /d "%~dp0\.."

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "requirements.txt" (
    echo Creating requirements.txt...
    echo quart^>^=0.19.0 > requirements.txt
    echo quart-cors^>^=0.6.0 >> requirements.txt
    echo sqlite3 >> requirements.txt
    echo requests^>^=2.28.0 >> requirements.txt
)

echo Installing dependencies...
pip install -q -r requirements.txt

:: Create data directories
if not exist "data" mkdir data
if not exist "data\logs" mkdir data\logs
if not exist "data\backups" mkdir data\backups

:: Launch the system
echo.
echo Starting AI Orchestration Analytics...
echo Dashboard will be available at: http://localhost:8000
echo.

python src\launch.py

pause