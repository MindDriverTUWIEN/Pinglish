<#
.SYNOPSIS
    Creates a Desktop shortcut for Finglish.

.DESCRIPTION
    This script creates (or updates) a desktop shortcut that launches Finglish
    using the hidden launcher (no console window). It uses the proper icon and sets
    the working directory correctly.

    The global hotkey inside the app is Strg + D (changeable in code).

    You can run this script anytime if you move the Finglish folder or want
    to recreate the shortcut.
#>

$ErrorActionPreference = 'Stop'

# Get the directory where this script lives (the Finglish project folder)
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Paths for the clean hidden launcher (no console window)
$Launcher   = Join-Path $ProjectDir "launch-hidden.vbs"
$IconFile   = Join-Path $ProjectDir "assets\icon.ico"
$PythonExe  = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$IconScript = Join-Path $ProjectDir "assets\generate_icons.py"
$Desktop    = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Finglish.lnk"

if (-not (Test-Path $Launcher)) {
    Write-Host "ERROR: Could not find launch-hidden.vbs in $ProjectDir" -ForegroundColor Red
    Write-Host "Make sure you are running this script from the Finglish project folder." -ForegroundColor Yellow
    pause
    exit 1
}

# Regenerate high-quality multi-resolution icon before updating the shortcut.
if ((Test-Path $PythonExe) -and (Test-Path $IconScript)) {
    Write-Host "Regenerating high-quality icon assets..." -ForegroundColor Cyan
    & $PythonExe $IconScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Icon generation failed; using existing icon.ico if present." -ForegroundColor Yellow
    }
} else {
    Write-Host "WARNING: Could not regenerate icons (python or script missing)." -ForegroundColor Yellow
}

Write-Host "Creating Finglish desktop shortcut (clean hidden mode - no console)." -ForegroundColor Cyan
Write-Host "  Project: $ProjectDir"
Write-Host "  Launcher: $Launcher  (uses pythonw.exe + VBS for no window)"
Write-Host "  Icon:     $IconFile"
Write-Host "  Desktop shortcut: $ShortcutPath"
Write-Host "  Hotkey inside app: Strg + D"

# Create the shortcut using WScript.Shell (COM)
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath       = $Launcher
$Shortcut.WorkingDirectory = $ProjectDir
# Use absolute path so Windows always resolves the freshest .ico file.
$Shortcut.IconLocation     = "$(Resolve-Path $IconFile),0"
$Shortcut.Description      = "Finglish - Offline Finglish / Pinglish to Persian (Farsi) converter"
$Shortcut.WindowStyle      = 1   # Normal window (the VBS itself is hidden)

# Optional: You can set a hotkey here if you want (example below is commented)
# $Shortcut.Hotkey = "CTRL+ALT+F"

$Shortcut.Save()

# Release the COM object
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host ""
Write-Host "Success! Desktop shortcut created:" -ForegroundColor Green
Write-Host "  $ShortcutPath" -ForegroundColor White
Write-Host ""
Write-Host "You can now double-click the 'Finglish' icon on your Desktop." -ForegroundColor Gray
Write-Host "Tip: Right-click the shortcut → Properties to change the icon or add a keyboard shortcut." -ForegroundColor DarkGray

# Pause only when run interactively (not when piped / non-interactive)
if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
    Read-Host "Press Enter to close this window"
}
