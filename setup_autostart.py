import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def main():
    print("=" * 64)
    print("✨ Lustre Separator - Auto Start on PC Boot Installer")
    print("=" * 64)

    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")

    startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)

    project_dir = Path(__file__).resolve().parent
    vbs_dest = startup_dir / "Lustre_Web_Server.vbs"

    python_exe = Path(sys.executable).resolve()

    # Generate dedicated startup VBS script with absolute project path
    vbs_content = f'''\' ==============================================================================
\' Lustre Separator - Auto-Boot Launcher for Windows Startup
\' Created automatically: runs silently in background on PC boot / logon
\' ==============================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = "{str(project_dir)}"
pythonPath = "{str(python_exe)}"

If Not fso.FileExists(pythonPath) Then
    pythonPath = "python.exe"
End If

serverScript = projectDir & "\\web_server.py"

If fso.FileExists(serverScript) Then
    WshShell.CurrentDirectory = projectDir
    ' Run python silently with 0 window style (invisible in background)
    cmd = """" & pythonPath & """ """ & serverScript & """ 5050"
    WshShell.Run cmd, 0, False
End If
'''

    with open(vbs_dest, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    print(f"✅ [1/3] Installed into Windows Startup Folder:\n   {vbs_dest}")

    # Register Task Scheduler for 100% reliable launch on logon
    sch_cmd = [
        "schtasks", "/create",
        "/tn", "LustreWebServerAutoBoot",
        "/tr", f'wscript.exe "{vbs_dest}"',
        "/sc", "onlogon",
        "/f"
    ]
    try:
        res = subprocess.run(sch_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("✅ [2/3] Registered Windows Scheduled Task (LustreWebServerAutoBoot)")
        else:
            print(f"ℹ️ Scheduled task notice: {res.stderr.strip() or res.stdout.strip()}")
    except Exception as e:
        print(f"ℹ️ Scheduled task notice: {e}")

    # Start service right now via VBS launcher
    print("🚀 Launching background web service now...")
    try:
        subprocess.Popen(["wscript.exe", str(vbs_dest)])
        print("✅ [3/3] Background web service started silently!")
    except Exception as e:
        print(f"❌ Launch error: {e}")

    # Test HTTP server with polling
    import urllib.request
    print("⏳ Verifying server on http://localhost:5050 ...")
    connected = False
    for _ in range(10):
        time.sleep(1.0)
        try:
            with urllib.request.urlopen("http://127.0.0.1:5050/api/status", timeout=2) as res:
                if res.status == 200:
                    connected = True
                    break
        except Exception:
            pass

    if connected:
        print("\n" + "=" * 64)
        print("🎉 SUCCESS! Web Studio is running at: http://localhost:5050")
        print("📌 STATUS: AUTO-START ON BOOT IS ENABLED!")
        print("   (Whenever PC turns on or restarts, this server starts automatically!)")
        print("=" * 64)
        return 0
    else:
        print("\n⚠️ Note: Web service is starting up. Please refresh http://localhost:5050 in your browser.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
