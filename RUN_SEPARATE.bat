@echo off
title Lustre Video Separator - Direct Cut Mode
color 0b
cd /d "%~dp0"
echo ===================================================
echo     🎬 LUSTRE VIDEO SEPARATOR (DIRECT CUT / MOVE MODE)
echo ===================================================
echo.
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -u video_separator.py
) else (
    python -u video_separator.py
)
echo.
pause
