@echo off
REM EGX Python Engine - Windows Run Script
REM =======================================

echo =======================================
echo    EGX Python Analysis Engine
echo        Version 1.3.0
echo =======================================
echo.

REM Get script directory
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo [OK] Dependencies installed

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs

REM Set environment variables
set PYTHONPATH=%cd%

REM Create .env if not exists
if not exist ".env" (
    echo Creating default .env file...
    (
        echo # EGX Python Engine Configuration
        echo APP_NAME=EGX Analysis Engine
        echo APP_VERSION=1.3.0
        echo DEBUG=false
        echo HOST=0.0.0.0
        echo PORT=8010
        echo REQUIRE_API_KEY=false
        echo API_KEY=
    ) > .env
)

echo.
echo =========================================
echo   Starting EGXPy Bridge API Server
echo =========================================
echo   Host: 0.0.0.0
echo   Port: 8010
echo   API Docs: http://localhost:8010/docs
echo.

REM Run the server
python unified_backend.py

pause
