# textDark build script (ASCII only on purpose, see README).
# Usage (from the project folder):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\build.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step([string]$Title, [scriptblock]$Action) {
    Write-Host "==> $Title" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Title (exit code $LASTEXITCODE)"
    }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Invoke-Step "Create virtual environment" { py -3 -m venv .venv }
}
$Py = Join-Path $Root ".venv\Scripts\python.exe"

Invoke-Step "Upgrade pip" { & $Py -m pip install --upgrade pip }
Invoke-Step "Install dependencies" { & $Py -m pip install -r requirements.txt pyinstaller }

$IconArgs = @()
$DataArgs = @()
if (Test-Path "logo.png") {
    & $Py "scripts\make_icon.py"
    if (($LASTEXITCODE -eq 0) -and (Test-Path "logo.ico")) {
        $IconArgs = @("--icon", "logo.ico")
    } else {
        Write-Host "Could not create logo.ico, building without EXE icon" -ForegroundColor Yellow
    }
    $DataArgs = @("--add-data", "logo.png;.")
} else {
    Write-Host "logo.png not found: building without icon" -ForegroundColor Yellow
}

if (Test-Path "dist\textDark.exe") { Remove-Item "dist\textDark.exe" -Force }

Invoke-Step "Build EXE with PyInstaller" {
    & $Py -m PyInstaller --noconfirm --clean --onefile --windowed --name textDark @IconArgs @DataArgs main.py
}

Write-Host ""
Write-Host "Done: dist\textDark.exe" -ForegroundColor Green
