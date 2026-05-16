@echo off
chcp 65001 >nul
echo ============================================
echo   EGX Data Engine - Delete All Tasks
echo ============================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ يجب تشغيل هذا الملف كـ Administrator
    pause
    exit /b 1
)

echo Deleting tasks...
schtasks /Delete /F /TN "EGX_AI_Batch_Analysis" >nul 2>&1
schtasks /Delete /F /TN "EGX_Mubasher_Sync" >nul 2>&1
schtasks /Delete /F /TN "EGX_Website_Sync" >nul 2>&1
schtasks /Delete /F /TN "EGX_Market_Data_Update" >nul 2>&1

echo ✅ All tasks deleted.
pause
