# Builds dist\Pinglish\Pinglish.exe (PyInstaller) and dist\Pinglish-Setup-<version>.exe (Inno Setup).
# Run from anywhere:  .\installer\build.ps1
# Needs: the project's .venv with requirements + pyinstaller, and Inno Setup 6 or 7.
param([string]$Version = "1.02")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pyinstaller = Join-Path $root ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyinstaller)) {
    throw "PyInstaller not found. Run: .\.venv\Scripts\python.exe -m pip install pyinstaller"
}

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup (ISCC.exe) not found. Install it from https://jrsoftware.org/isdl.php" }

Write-Host "1/2 Building Pinglish.exe with PyInstaller..." -ForegroundColor Cyan
$env:PINGLISH_VERSION = $Version
& $pyinstaller --noconfirm --clean --log-level WARN --distpath dist --workpath build\pyinstaller installer\pinglish.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "2/2 Building the installer with Inno Setup..." -ForegroundColor Cyan
& $iscc /Q "/DAppVersion=$Version" installer\pinglish.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

$setup = Join-Path $root "dist\Pinglish-Setup-$Version.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash
Write-Host "`nDone: $setup" -ForegroundColor Green
Write-Host ("Size: {0:N1} MB   SHA256: {1}" -f ((Get-Item $setup).Length / 1MB), $hash)
