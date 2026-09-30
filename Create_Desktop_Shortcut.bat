@echo off
title Create Desktop Shortcut for Lustre Studio
cd /d "%~dp0"

python -c "import os, sys, winshell; from win32com.client import Dispatch; desktop = winshell.desktop(); path = os.path.join(desktop, 'Lustre Studio.lnk'); target = os.path.join(os.getcwd(), 'Lustre_Web.bat'); icon = os.path.join(os.getcwd(), 'logo.ico'); shell = Dispatch('WScript.Shell'); s = shell.CreateShortCut(path); s.Targetpath = target; s.WorkingDirectory = os.getcwd(); s.IconLocation = icon; s.save(); print('Desktop shortcut created successfully!')" 2>nul
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "$w = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $w.CreateShortcut((Join-Path $d 'Lustre Studio.lnk')); $s.TargetPath = (Join-Path $pwd.Path 'Lustre_Web.bat'); $s.WorkingDirectory = $pwd.Path; $ico = (Join-Path $pwd.Path 'logo.ico'); if (Test-Path $ico) { $s.IconLocation = $ico }; $s.Save(); Write-Host 'Desktop Shortcut Created Successfully!'"
)

echo.
echo [OK] Done! You can now launch Lustre Studio directly from your Desktop anytime!
