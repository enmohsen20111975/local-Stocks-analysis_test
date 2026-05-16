@echo off
chcp 65001 >nul
title EGX Market Data Scheduler
cd /d "%~dp0"

echo ==========================================
echo   EGX Market Hours Scheduler
echo   9:30 AM - 2:30 PM (Sun-Thu)
echo   Every hour: Data Sync + Analysis + Push
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create logs directory
if not exist logs mkdir logs

echo [INFO] Starting scheduler daemon...
echo [INFO] Press Ctrl+C to stop
echo.

python market_scheduler.py --daemon

echo.
echo Scheduler stopped.
pause
