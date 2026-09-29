@echo off
title Lustre Separator - Stop Background Service
color 0c
cls
echo ==============================================================================
echo        LUSTRE SEPARATOR - STOP BACKGROUND SERVICE
echo ==============================================================================
echo.
echo Stopping Web Server on port 5050...
echo.

python -c "import web_server; web_server.free_port(5050); print('Port 5050 freed.')"

echo.
echo [OK] Background Web Service stopped successfully!
echo.
timeout /t 3
