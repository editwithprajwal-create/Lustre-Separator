@echo off
title Lustre Separator - Remove Auto Start On Boot
color 0e
cls
echo ==============================================================================
echo        LUSTRE SEPARATOR - REMOVE AUTO START ON BOOT
echo ==============================================================================
echo.
echo Removing automatic startup on PC boot...
echo.

set STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Lustre_Web_Server.vbs
if exist "%STARTUP_VBS%" (
    del /f /q "%STARTUP_VBS%"
    echo [OK] Removed from Windows Startup folder.
)

schtasks /delete /tn "LustreWebServerAutoBoot" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Removed Windows Scheduled Task.
)

echo.
echo [DONE] Auto Start on PC boot has been completely removed.
echo.
pause
