@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   EGX Data Engine - Run All Tasks Now
echo ============================================
echo.

echo [1/4] Running Website Sync...
call run_website_sync.bat
echo.

echo [2/4] Running Mubasher Sync...
call run_mubasher_sync.bat
echo.

echo [3/4] Running Market Update...
call run_market_update.bat
echo.

echo [4/4] Running AI Batch Analysis...
call run_ai_batch.bat
echo.

echo ============================================
echo   ✅ All tasks completed!
echo ============================================
pause
