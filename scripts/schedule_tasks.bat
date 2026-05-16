@echo off
chcp 65001 >nul
echo ============================================
echo   EGX Data Engine - Windows Task Scheduler
echo ============================================
echo.

REM Get script directory
cd /d "%~dp0"

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ يجب تشغيل هذا الملف كـ Administrator
    echo Right click → Run as administrator
    pause
    exit /b 1
)

echo [1/4] Creating AI Analysis Task...
schtasks /Create /F /TN "EGX_AI_Batch_Analysis" ^
    /TR "%~dp0run_ai_batch.bat" ^
    /SC HOURLY ^
    /ST 00:00 ^
    /RU "%USERNAME%" ^
    /RL HIGHEST ^
    /DESC "EGX AI Batch Analysis - Runs every hour" >nul 2>&1
if %errorlevel%==0 (
    echo     ✅ AI Analysis Task Created (Hourly)
) else (
    echo     ⚠️  Task may already exist
)

echo [2/4] Creating Mubasher Sync Task...
schtasks /Create /F /TN "EGX_Mubasher_Sync" ^
    /TR "%~dp0run_mubasher_sync.bat" ^
    /SC DAILY ^
    /ST 09:00 ^
    /RU "%USERNAME%" ^
    /RL HIGHEST ^
    /DESC "EGX Mubasher Sync - Runs daily at 9 AM" >nul 2>&1
if %errorlevel%==0 (
    echo     ✅ Mubasher Sync Task Created (Daily 9AM)
) else (
    echo     ⚠️  Task may already exist
)

echo [3/4] Creating Website Sync Task...
schtasks /Create /F /TN "EGX_Website_Sync" ^
    /TR "%~dp0run_website_sync.bat" ^
    /SC DAILY ^
    /ST 08:30 ^
    /RU "%USERNAME%" ^
    /RL HIGHEST ^
    /DESC "EGX Website Sync - Runs daily at 8:30 AM" >nul 2>&1
if %errorlevel%==0 (
    echo     ✅ Website Sync Task Created (Daily 8:30AM)
) else (
    echo     ⚠️  Task may already exist
)

echo [4/4] Creating Market Data Update Task...
schtasks /Create /F /TN "EGX_Market_Data_Update" ^
    /TR "%~dp0run_market_update.bat" ^
    /SC DAILY ^
    /ST 10:00 ^
    /RU "%USERNAME%" ^
    /RL HIGHEST ^
    /DESC "EGX Market Data Update - Runs daily at 10 AM" >nul 2>&1
if %errorlevel%==0 (
    echo     ✅ Market Data Update Task Created (Daily 10AM)
) else (
    echo     ⚠️  Task may already exist
)

echo.
echo ============================================
echo   ✅ All Tasks Created Successfully!
echo ============================================
echo.
echo To view tasks: schtasks /Query /TN "EGX_*"
echo To delete all:  delete_tasks.bat
echo To run now:     run_all_tasks.bat
echo.
pause
