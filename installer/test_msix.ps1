# Smoke test for dist\Pinglish-<version>.msix on a Windows machine (used by CI).
# It signs a COPY of the package with a throwaway certificate (the Store signs
# the real one), installs it, starts Pinglish, checks that it runs as a packaged
# app, then removes the package and the certificate again.
#   .\installer\test_msix.ps1 -Version 1.05
# Needs administrator rights (to trust the throwaway certificate).
param([string]$Version = "1.05")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$msix = Join-Path $root "dist\Pinglish-$Version.msix"
if (-not (Test-Path $msix)) { throw "$msix not found. Run .\installer\build_msix.ps1 first." }

$identity = Get-Content (Join-Path $PSScriptRoot "msix\identity.json") -Raw | ConvertFrom-Json
$work = Join-Path $root "build\msix-test"
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Path $work | Out-Null

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.*\x64\signtool.exe" |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $signtool) { throw "signtool.exe not found" }

$cert = $null
$trusted = $null
$failed = $false
try {
    Write-Host "Signing a test copy..." -ForegroundColor Cyan
    $cert = New-SelfSignedCertificate -Type Custom -Subject $identity.publisher `
        -KeyUsage DigitalSignature -FriendlyName "Pinglish MSIX test (temporary)" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    $cer = Join-Path $work "test.cer"
    Export-Certificate -Cert $cert -FilePath $cer | Out-Null
    $trusted = Import-Certificate -FilePath $cer -CertStoreLocation "Cert:\LocalMachine\TrustedPeople"
    $testMsix = Join-Path $work "Pinglish-test.msix"
    Copy-Item $msix $testMsix
    & $signtool.FullName sign /fd SHA256 /sha1 $cert.Thumbprint /s My $testMsix
    if ($LASTEXITCODE -ne 0) { throw "signtool failed" }

    Write-Host "Installing..." -ForegroundColor Cyan
    Add-AppxPackage -Path $testMsix
    $pkg = Get-AppxPackage -Name $identity.name
    if (-not $pkg) { throw "Package not installed" }
    Write-Host "Installed $($pkg.PackageFullName)"

    Write-Host "Starting Pinglish..." -ForegroundColor Cyan
    $aumid = "$($pkg.PackageFamilyName)!Pinglish"
    Start-Process "explorer.exe" "shell:AppsFolder\$aumid"
    $log = $null
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Packages\$($pkg.PackageFamilyName)\LocalCache\Local\Pinglish\finglish_launch.log"),
        (Join-Path $env:LOCALAPPDATA "Pinglish\finglish_launch.log")
    )
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        $log = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($log -and (Select-String -Path $log -Pattern "main\(\) setup|Tray thread started" -Quiet)) { break }
    }
    if (-not $log) { throw "Pinglish wrote no log: it did not start" }
    Write-Host "`n--- $log ---"
    Get-Content $log | Select-Object -Last 40
    Write-Host "---"

    $running = Get-Process -Name "Pinglish" -ErrorAction SilentlyContinue
    if (-not $running) { throw "Pinglish.exe is not running" }
    if (-not (Select-String -Path $log -Pattern ([regex]::Escape("Packaged (MSIX): $aumid")) -Quiet)) {
        throw "Pinglish did not detect its package identity ($aumid)"
    }
    if (-not (Select-String -Path $log -Pattern "main\(\) entered" -Quiet)) {
        throw "The Pinglish window (Flet) did not connect"
    }

    Write-Host "`nSecond launch must not start a second copy..." -ForegroundColor Cyan
    $before = @(Get-Process -Name "Pinglish").Count
    Start-Process "explorer.exe" "shell:AppsFolder\$aumid"
    Start-Sleep -Seconds 8
    $after = @(Get-Process -Name "Pinglish" -ErrorAction SilentlyContinue).Count
    if ($after -gt $before) { throw "A second Pinglish started ($before -> $after processes)" }
    Write-Host "OK: still $after Pinglish process(es)"

    Write-Host "`nMSIX smoke test passed." -ForegroundColor Green
}
catch {
    $failed = $true
    Write-Host "MSIX smoke test FAILED: $_" -ForegroundColor Red
}
finally {
    Get-Process -Name "Pinglish", "flet" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Get-AppxPackage -Name $identity.name | Remove-AppxPackage -ErrorAction SilentlyContinue
    if ($trusted) { Remove-Item "Cert:\LocalMachine\TrustedPeople\$($trusted.Thumbprint)" -ErrorAction SilentlyContinue }
    if ($cert) { Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -ErrorAction SilentlyContinue }
}
if ($failed) { exit 1 }
