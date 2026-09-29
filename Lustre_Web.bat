@echo off
title Lustre Separator - Web Server
cd /d "%~dp0"
echo Starting Lustre Separator Web Studio on http://localhost:5050 ...
where py >nul 2>nul
if %errorlevel% equ 0 (
    py web_server.py
) else (
    python web_server.py
)
pause
