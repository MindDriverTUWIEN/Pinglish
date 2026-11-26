# Build a standalone Finglish Windows desktop app using Flet
# Run from PowerShell after activating the venv:
#   .\.venv\Scripts\Activate.ps1
#   .\build_windows.ps1

param(
    [string]$Name = "Finglish",
    [string]$Icon = "assets/icon.png"
)

Write-Host "Building $Name for Windows..." -ForegroundColor Cyan

flet build windows `
    --name $Name `
    --icon $Icon `
    --product $Name `
    --company "Local Tools" `
    --version "0.1.0" `
    --description "Offline Finglish / Pinglish to Persian converter"

Write-Host "`nBuild finished. Check the build/ folder." -ForegroundColor Green
Write-Host "You can zip the output folder and distribute it." -ForegroundColor Yellow
