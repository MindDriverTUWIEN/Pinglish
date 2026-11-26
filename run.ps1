# Finglish Launcher (PowerShell)
# You can right-click this file and choose "Run with PowerShell" or create a shortcut to it.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Starting Pinglish..." -ForegroundColor Cyan

# Activate venv
$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Host "Virtual environment not found at .\.venv\Scripts\Activate.ps1" -ForegroundColor Red
    Write-Host "Please run the setup steps first (see README.md)." -ForegroundColor Yellow
    pause
    exit 1
}

# Run the app
python main.py

Write-Host ""
Write-Host "Pinglish has exited." -ForegroundColor Gray
Read-Host "Press Enter to close this window"
