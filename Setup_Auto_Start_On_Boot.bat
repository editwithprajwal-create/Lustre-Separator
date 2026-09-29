@echo off
title Lustre Separator - Auto Start On PC Boot Setup
cd /d "%~dp0"
python setup_autostart.py
if %errorlevel% neq 0 (
    py setup_autostart.py
)
echo.
pause
