@echo off
chcp 65001 >nul
title Setup Windows Task Scheduler - EGX Market Updates
cd /d "%~dp0"

echo ==========================================
echo   Setup Windows Task Scheduler
echo   EGX Market Data Updates
echo   9:30 AM - 2:30 PM (Sun-Thu)
echo ==========================================
echo.

set "TASK_NAME=EGX_Market_Update"
set "SCRIPT_PATH=%CD%\market_scheduler.py"
set "PYTHON_PATH=python"

REM Delete old tasks if exist
schtasks /delete /tn "%TASK_NAME%_0930" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1030" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1130" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1230" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1330" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1430" /f >nul 2>&1

echo [INFO] Creating scheduled tasks...
echo.

REM 09:30 AM - Full pipeline with morning report
schtasks /create /tn "%TASK_NAME%_0930" /tr "%PYTHON_PATH% %SCRIPT_PATH% --now" /sc weekly /d SUN,MON,TUE,WED,THU /st 09:30 /f >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to create 09:30 task. Run as Administrator.
    pause
    exit /b 1
)
echo [OK] 09:30 AM - Full Pipeline + Morning Report

REM 10:30 AM - Hourly update
schtasks /create /tn "%TASK_NAME%_1030" /tr "%PYTHON_PATH% %SCRIPT_PATH% --hourly" /sc weekly /d SUN,MON,TUE,WED,THU /st 10:30 /f >nul 2>&1
echo [OK] 10:30 AM - Hourly Update

REM 11:30 AM - Hourly update
schtasks /create /tn "%TASK_NAME%_1130" /tr "%PYTHON_PATH% %SCRIPT_PATH% --hourly" /sc weekly /d SUN,MON,TUE,WED,THU /st 11:30 /f >nul 2>&1
echo [OK] 11:30 AM - Hourly Update

REM 12:30 PM - Hourly update
schtasks /create /tn "%TASK_NAME%_1230" /tr "%PYTHON_PATH% %SCRIPT_PATH% --hourly" /sc weekly /d SUN,MON,TUE,WED,THU /st 12:30 /f >nul 2>&1
echo [OK] 12:30 PM - Hourly Update

REM 13:30 PM - Hourly update
schtasks /create /tn "%TASK_NAME%_1330" /tr "%PYTHON_PATH% %SCRIPT_PATH% --hourly" /sc weekly /d SUN,MON,TUE,WED,THU /st 13:30 /f >nul 2>&1
echo [OK] 01:30 PM - Hourly Update

REM 14:30 PM - Full pipeline with final report
schtasks /create /tn "%TASK_NAME%_1430" /tr "%PYTHON_PATH% %SCRIPT_PATH% --now" /sc weekly /d SUN,MON,TUE,WED,THU /st 14:30 /f >nul 2>&1
echo [OK] 02:30 PM - Full Pipeline + Final Report

echo.
echo ==========================================
echo   All tasks created successfully!
echo.
echo   Schedule (Sun-Thu):
echo     09:30 - Full Pipeline + Morning Report
echo     10:30 - Hourly Update
echo     11:30 - Hourly Update
echo     12:30 - Hourly Update
echo     13:30 - Hourly Update
echo     14:30 - Full Pipeline + Final Report
echo.
echo   To view tasks: schtasks /query /fo LIST
echo   To delete: setup_windows_tasks_delete.bat
echo ==========================================
pause
