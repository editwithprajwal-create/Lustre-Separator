@echo off
title Lustre Separator - Web Server
cd /d "%~dp0"
echo =========================================================
echo    ✨ LUSTRE SEPARATOR - LOCAL WEB STUDIO LAUNCHER
echo =========================================================
echo.
echo Starting web server on http://localhost:5050 ...
echo (Keep this window open while using the tool)
echo.

set "PY_CMD="
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    ) else if exist "C:\Users\PublicAawaj\AppData\Local\Programs\Python\Python314\python.exe" (
        set "PY_CMD=C:\Users\PublicAawaj\AppData\Local\Programs\Python\Python314\python.exe"
    )
)

if "%PY_CMD%"=="" (
    echo [X] Python was not found in PATH.
    echo Please install Python 3 or add it to your system PATH.
    pause
    exit /b 1
)

start "" http://localhost:5050
"%PY_CMD%" web_server.py 5050
pause
