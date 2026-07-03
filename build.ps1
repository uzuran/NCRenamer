#Requires -Version 5.1
# NCRenamer v0.2.0 — PowerShell build script
# Usage (from Windows PowerShell):  .\build.ps1
# Usage (from WSL):                  ./build_wsl.sh

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  ============================================================"
Write-Host "   NCRenamer v0.2.0 - Windows Build"
Write-Host "  ============================================================"
Write-Host ""

# ── verify Python ─────────────────────────────────────────────────────────────
try {
    $pyver = & python --version 2>&1
    Write-Host "  Python: $pyver"
} catch {
    Write-Error "Python not found. Install Python 3.12+ for Windows and add it to PATH."
    exit 1
}

# ── install / upgrade build tools ────────────────────────────────────────────
Write-Host ""
Write-Host "  [1/4] Installing dependencies..."
& python -m pip install --quiet --upgrade pip
& python -m pip install --quiet -r requirements.txt
& python -m pip install --quiet pyinstaller
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }

# ── clean previous output ─────────────────────────────────────────────────────
Write-Host "  [2/4] Cleaning previous build..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist"  }

# ── build ─────────────────────────────────────────────────────────────────────
Write-Host "  [3/4] Running PyInstaller..."
Write-Host ""
& python -m PyInstaller NCRenamer.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit 1 }

# ── copy table file next to exe ───────────────────────────────────────────────
Write-Host "  [4/5] Copying CNCs\laser.xls next to exe..."
$cncsDir = Join-Path $PSScriptRoot "dist\CNCs"
if (-not (Test-Path $cncsDir)) { New-Item -ItemType Directory -Path $cncsDir | Out-Null }
$src = Join-Path $PSScriptRoot "CNCs\laser.xls"
if (Test-Path $src) {
    Copy-Item $src $cncsDir -Force
    Write-Host "        Copied: CNCs\laser.xls"
} else {
    Write-Host "        WARNING: CNCs\laser.xls not found - copy it manually next to the exe."
}

# ── report ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  [5/5] Done."
Write-Host ""
Write-Host "  Output:  $PSScriptRoot\dist\NCRenamer.exe"
Write-Host "  Table:   $PSScriptRoot\dist\CNCs\laser.xls"
Write-Host ""
Write-Host "  ============================================================"
Write-Host "   Build successful!"
Write-Host "  ============================================================"
Write-Host ""
