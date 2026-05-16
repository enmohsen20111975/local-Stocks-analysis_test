@echo off
title EGX Backend Server
cd /d "%~dp0"
echo =========================================
echo   EGX Unified Backend v3.2.0
echo =========================================
echo.
echo Starting server on http://localhost:8010
echo.
echo DO NOT CLOSE THIS WINDOW
echo.
.venv\Scripts\python.exe unified_backend.py
pause
