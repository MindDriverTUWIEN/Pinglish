# Builds dist\Pinglish-<version>.msix for the Microsoft Store from dist\Pinglish
# (the PyInstaller folder that build.ps1 makes first).
#   .\installer\build_msix.ps1 -Version 1.05
# Needs: the Windows 10/11 SDK (makeappx.exe, makepri.exe) and the project's .venv.
# The package is not signed: the Store signs it. Package identity: installer\msix\identity.json.
param([string]$Version = "1.04")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$appDir = Join-Path $root "dist\Pinglish"
if (-not (Test-Path (Join-Path $appDir "Pinglish.exe"))) {
    throw "dist\Pinglish\Pinglish.exe not found. Run .\installer\build.ps1 first."
}

# Newest SDK tools for x64.
$sdkBin = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
$toolDir = Get-ChildItem $sdkBin -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^10\.' -and (Test-Path (Join-Path $_.FullName "x64\makeappx.exe")) } |
    Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
if (-not $toolDir) { throw "Windows SDK (makeappx.exe) not found under $sdkBin" }
$makeappx = Join-Path $toolDir.FullName "x64\makeappx.exe"
$makepri = Join-Path $toolDir.FullName "x64\makepri.exe"

# Store versions have four numbers and must end in .0: 1.05 -> 1.5.0.0
$nums = @($Version.Split(".") | ForEach-Object { [int]$_ })
while ($nums.Count -lt 3) { $nums += 0 }
$msixVersion = "{0}.{1}.{2}.0" -f $nums[0], $nums[1], $nums[2]

$identity = Get-Content (Join-Path $PSScriptRoot "msix\identity.json") -Raw | ConvertFrom-Json
function Escape-Xml([string]$text) { [System.Security.SecurityElement]::Escape($text) }

$work = Join-Path $root "build\msix"
$layout = Join-Path $work "layout"
$priRoot = Join-Path $work "pri"
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Path $layout, $priRoot | Out-Null

Write-Host "1/4 Copying the app..." -ForegroundColor Cyan
Copy-Item (Join-Path $appDir "*") $layout -Recurse
# The .exe installer writes pinglish.ini; the package never contains one.
Remove-Item (Join-Path $layout "pinglish.ini") -ErrorAction SilentlyContinue

Write-Host "2/4 Drawing tiles and icons..." -ForegroundColor Cyan
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
& $python (Join-Path $PSScriptRoot "msix\make_assets.py") (Join-Path $priRoot "Assets")
if ($LASTEXITCODE -ne 0) { throw "make_assets.py failed" }
Copy-Item (Join-Path $priRoot "Assets") $layout -Recurse

$manifest = (Get-Content (Join-Path $PSScriptRoot "msix\AppxManifest.template.xml") -Raw).
    Replace("@@NAME@@", (Escape-Xml $identity.name)).
    Replace("@@PUBLISHER@@", (Escape-Xml $identity.publisher)).
    Replace("@@PUBLISHER_DISPLAY_NAME@@", (Escape-Xml $identity.publisherDisplayName)).
    Replace("@@DISPLAY_NAME@@", (Escape-Xml $identity.displayName)).
    Replace("@@VERSION@@", $msixVersion)
if ($manifest -match "@@") { throw "AppxManifest still has an unfilled @@ value" }
$manifestPath = Join-Path $layout "AppxManifest.xml"
[System.IO.File]::WriteAllText($manifestPath, $manifest, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "3/4 Indexing images (resources.pri)..." -ForegroundColor Cyan
# Only the Assets folder is indexed, so the app's own files are not listed as resources.
$priConfig = Join-Path $work "priconfig.xml"
& $makepri createconfig /cf $priConfig /dq en-US /pv 10.0.0 /o | Out-Null
if ($LASTEXITCODE -ne 0) { throw "makepri createconfig failed" }
& $makepri new /pr $priRoot /cf $priConfig /mn $manifestPath /of (Join-Path $layout "resources.pri") /o | Out-Null
if ($LASTEXITCODE -ne 0) { throw "makepri new failed" }

Write-Host "4/4 Packing the MSIX..." -ForegroundColor Cyan
$out = Join-Path $root "dist\Pinglish-$Version.msix"
# makeappx also checks the manifest against Microsoft's schema.
& $makeappx pack /d $layout /p $out /o
if ($LASTEXITCODE -ne 0) { throw "makeappx pack failed" }

$hash = (Get-FileHash $out -Algorithm SHA256).Hash
$kind = if ($identity.store) { "Store identity" } else { "TEST identity (not accepted by the Store yet)" }
Write-Host "`nDone: $out" -ForegroundColor Green
Write-Host ("Version {0}, {1}, {2:N1} MB, SHA256 {3}" -f $msixVersion, $kind, ((Get-Item $out).Length / 1MB), $hash)
