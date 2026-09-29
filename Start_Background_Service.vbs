' ==============================================================================
' Lustre Separator - Silent Background Web Service Launcher
' Runs web_server.py silently in background without any console or popup window
' ==============================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
fallbackDir = "D:\prajwal\Z      Tools\CAPTION AND HASTAG WITH CONENT SEPERATION"

If fso.FileExists(currentDir & "\web_server.py") Then
    projectDir = currentDir
ElseIf fso.FileExists(fallbackDir & "\web_server.py") Then
    projectDir = fallbackDir
Else
    WScript.Quit 1
End If

pythonPath = "C:\Users\PublicAawaj\AppData\Local\Programs\Python\Python314\python.exe"
If Not fso.FileExists(pythonPath) Then
    pythonPath = "python.exe"
End If

' Run completely hidden with window style 0 (no console window appears)
cmd = """" & pythonPath & """ """ & projectDir & "\web_server.py"" 5050"

WshShell.CurrentDirectory = projectDir
WshShell.Run cmd, 0, False
