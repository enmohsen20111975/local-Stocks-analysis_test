@echo off
echo Deleting all EGX Market Update tasks...
schtasks /delete /tn "EGX_Market_Update_0930" /f >nul 2>&1
schtasks /delete /tn "EGX_Market_Update_1030" /f >nul 2>&1
schtasks /delete /tn "EGX_Market_Update_1130" /f >nul 2>&1
schtasks /delete /tn "EGX_Market_Update_1230" /f >nul 2>&1
schtasks /delete /tn "EGX_Market_Update_1330" /f >nul 2>&1
schtasks /delete /tn "EGX_Market_Update_1430" /f >nul 2>&1
echo All tasks deleted.
pause
