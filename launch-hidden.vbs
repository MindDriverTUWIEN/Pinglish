' launch-hidden.vbs
' Silently launches the Pinglish app without showing any console or PowerShell window.
' This is used by the desktop shortcut.
' Global hotkey inside app: Strg + D
'
' You can also double-click this file directly.
' If the app still fails to appear, check data\finglish_launch.log in the project folder.

Option Explicit

Dim fso, WshShell
Dim scriptDir, projectDir
Dim pythonwPath, mainPyPath
Dim cmd

On Error Resume Next

Set fso = CreateObject("Scripting.FileSystemObject")

' Get the folder where this .vbs file is located (should be the project root)
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = scriptDir

' Paths (relative to this script)
pythonwPath = fso.BuildPath(projectDir, ".venv\Scripts\pythonw.exe")
mainPyPath  = fso.BuildPath(projectDir, "main.py")

' Check if the files exist
If Not fso.FileExists(pythonwPath) Then
    MsgBox "Konnte pythonw.exe nicht finden." & vbCrLf & _
           "Erwartet: " & pythonwPath & vbCrLf & vbCrLf & _
           "Bitte Virtual Environment prüfen (run.bat einmal ausführen zum Setup).", _
           vbCritical, "Pinglish"
    WScript.Quit 1
End If

If Not fso.FileExists(mainPyPath) Then
    MsgBox "Konnte main.py nicht finden." & vbCrLf & _
           "Erwartet: " & mainPyPath, _
           vbCritical, "Pinglish"
    WScript.Quit 1
End If

' Build the command line with proper quoting
cmd = """" & pythonwPath & """ """ & mainPyPath & """"

' Run it completely hidden (window style 0 = hidden, False = don't wait)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = projectDir   ' Ensure correct working dir for relative paths and Flet
WshShell.Run cmd, 0, False

If Err.Number <> 0 Then
    MsgBox "Fehler beim Starten von Pinglish: " & Err.Description, vbCritical, "Pinglish"
End If

' Clean up
Set WshShell = Nothing
Set fso = Nothing
